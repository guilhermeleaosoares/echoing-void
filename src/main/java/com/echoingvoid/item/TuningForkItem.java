package com.echoingvoid.item;

import com.echoingvoid.block.HollowHorizonPortalBlock;
import com.echoingvoid.registry.ModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gameevent.GameEvent;

/**
 * Struck against phonolite, the fork runs a frequency check: it looks for a closed rectangle of
 * phonolite bricks around the block you hit and, if the note comes back clean, fills the opening
 * with a Hollow Horizon portal. Off-key frames get a flat thud and a puff of note particles, so a
 * miss still tells you the fork worked and the wall did not.
 *
 * <p>Fire cannot do this job - {@code BaseFireBlock} only ignites in the Overworld and the Nether -
 * and vanilla's {@code PortalShape} fills with {@code minecraft:nether_portal} and nothing else, so
 * the scan and the fill are both done here.
 *
 * <p>The fork is also the key to the Acoustic Lock Box. That conversation belongs to the block, and
 * the block already gets first refusal on a right-click, so clicking a lock box simply passes.
 */
public class TuningForkItem extends Item {
    /** Interior bounds of a workable frame, in blocks: 2x3 at the smallest, 4x5 at the largest. */
    private static final int MIN_WIDTH = 2;
    private static final int MAX_WIDTH = 4;
    private static final int MIN_HEIGHT = 3;
    private static final int MAX_HEIGHT = 5;

    /** Tell clients about the new portal cells but do not re-run their shape checks. */
    private static final int PORTAL_FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE;

    private static final Direction.Axis[] PLANES = {Direction.Axis.X, Direction.Axis.Z};
    private static final Direction[] X_PLANE = {Direction.EAST, Direction.WEST, Direction.UP, Direction.DOWN};
    private static final Direction[] Z_PLANE = {Direction.SOUTH, Direction.NORTH, Direction.UP, Direction.DOWN};

    public TuningForkItem(final Item.Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult useOn(final UseOnContext context) {
        Level level = context.getLevel();
        BlockPos clicked = context.getClickedPos();
        BlockState clickedState = level.getBlockState(clicked);

        // The lock box handles the fork itself; leave the interaction to it.
        if (clickedState.is(ModBlocks.ACOUSTIC_LOCK_BOX.get())) {
            return InteractionResult.PASS;
        }

        if (!clickedState.is(ModBlocks.PHONOLITE_BRICKS.get())) {
            return InteractionResult.PASS;
        }

        if (!(level instanceof ServerLevel serverLevel)) {
            return InteractionResult.SUCCESS;
        }

        // Two cursors serve the whole interaction - the scan, the ring check and the fill.
        BlockPos.MutableBlockPos walker = new BlockPos.MutableBlockPos();
        BlockPos.MutableBlockPos probe = new BlockPos.MutableBlockPos();

        Player player = context.getPlayer();
        Frame frame = findFrame(serverLevel, clicked, walker, probe);
        if (frame == null) {
            playOffKey(serverLevel, clicked);
            return InteractionResult.CONSUME;
        }

        int filled = fill(serverLevel, frame, probe);
        if (filled == 0) {
            // The frame was already resonating. Acknowledge it quietly rather than pretending.
            serverLevel.playSound(null, clicked.getX() + 0.5, clicked.getY() + 0.5, clicked.getZ() + 0.5,
                    SoundEvents.NOTE_BLOCK_BELL, SoundSource.BLOCKS, 0.4F, 1.4F);
            return InteractionResult.CONSUME;
        }

        playRisingChime(serverLevel, frame.bottomLeft());
        serverLevel.gameEvent(player, GameEvent.BLOCK_PLACE, frame.bottomLeft());
        if (player != null) {
            // Opening a way costs the fork something; tuning a lock box does not.
            context.getItemInHand().hurtAndBreak(1, player, context.getHand());
        }

        return InteractionResult.SUCCESS;
    }

    // ---------------------------------------------------------------- geometry

    /**
     * A frame that passed the check. {@code bottomLeft} is the interior cell nearest the negative
     * end of {@code right}, sitting directly on the bottom course of bricks.
     */
    private record Frame(BlockPos bottomLeft, Direction.Axis axis, Direction right, int width, int height) {}

    /**
     * Looks for a complete frame that the clicked brick is part of, trying both horizontal planes.
     * Each of the clicked block's in-plane neighbours is offered as a seed for the interior, which
     * is what lets you strike any edge brick rather than one particular one.
     */
    private static Frame findFrame(
            final ServerLevel level,
            final BlockPos clicked,
            final BlockPos.MutableBlockPos walker,
            final BlockPos.MutableBlockPos probe
    ) {
        for (Direction.Axis axis : PLANES) {
            for (Direction seedDir : axis == Direction.Axis.X ? X_PLANE : Z_PLANE) {
                walker.setWithOffset(clicked, seedDir);
                if (!isCavity(level.getBlockState(walker))) {
                    continue;
                }

                Frame frame = resolveFrame(level, walker, probe, axis);
                if (frame != null && touchesFrame(frame, clicked)) {
                    return frame;
                }
            }
        }

        return null;
    }

    /**
     * Walks out from a known interior cell to the bottom-left corner, then measures the opening and
     * checks every brick of the ring. Returns null the moment anything is out of true.
     *
     * <p>Both cursors are scratch space and are left somewhere arbitrary on return.
     */
    private static Frame resolveFrame(
            final ServerLevel level,
            final BlockPos.MutableBlockPos seed,
            final BlockPos.MutableBlockPos cursor,
            final Direction.Axis axis
    ) {
        Direction right = Direction.get(Direction.AxisDirection.POSITIVE, axis);
        Direction left = right.getOpposite();

        // Drop to the floor of the opening.
        int minY = Math.max(level.getMinY(), seed.getY() - MAX_HEIGHT);
        while (seed.getY() > minY) {
            seed.move(Direction.DOWN);
            if (!isCavity(level.getBlockState(seed))) {
                seed.move(Direction.UP);
                break;
            }
        }

        // Slide to the left-hand edge of the opening.
        boolean foundEdge = false;
        for (int step = 0; step <= MAX_WIDTH; step++) {
            seed.move(left);
            if (!isCavity(level.getBlockState(seed))) {
                seed.move(right);
                foundEdge = true;
                break;
            }
        }

        if (!foundEdge) {
            return null;
        }

        BlockPos bottomLeft = seed.immutable();

        int width = 0;
        for (int u = 0; u <= MAX_WIDTH; u++) {
            cell(cursor, bottomLeft, right, u, 0);
            if (isCavity(level.getBlockState(cursor))) {
                continue;
            }

            if (!isFrame(level.getBlockState(cursor))) {
                return null;
            }

            width = u;
            break;
        }

        if (width < MIN_WIDTH || width > MAX_WIDTH) {
            return null;
        }

        int height = 0;
        for (int v = 0; v <= MAX_HEIGHT; v++) {
            int cavityCells = 0;
            int frameCells = 0;
            for (int u = 0; u < width; u++) {
                cell(cursor, bottomLeft, right, u, v);
                BlockState state = level.getBlockState(cursor);
                if (isCavity(state)) {
                    cavityCells++;
                } else if (isFrame(state)) {
                    frameCells++;
                }
            }

            if (cavityCells == width) {
                continue;
            }

            // The first row that is not open must be the lintel, whole and unbroken.
            if (frameCells != width) {
                return null;
            }

            height = v;
            break;
        }

        if (height < MIN_HEIGHT || height > MAX_HEIGHT) {
            return null;
        }

        // Bottom course.
        for (int u = 0; u < width; u++) {
            cell(cursor, bottomLeft, right, u, -1);
            if (!isFrame(level.getBlockState(cursor))) {
                return null;
            }
        }

        // Both uprights.
        for (int v = 0; v < height; v++) {
            cell(cursor, bottomLeft, right, -1, v);
            if (!isFrame(level.getBlockState(cursor))) {
                return null;
            }

            cell(cursor, bottomLeft, right, width, v);
            if (!isFrame(level.getBlockState(cursor))) {
                return null;
            }
        }

        return new Frame(bottomLeft, axis, right, width, height);
    }

    /** True when {@code pos} sits on the ring of the frame rather than inside or away from it. */
    private static boolean touchesFrame(final Frame frame, final BlockPos pos) {
        BlockPos bottomLeft = frame.bottomLeft();
        Direction right = frame.right();

        // Anything out of the portal's own plane cannot be part of this frame.
        if (right.getStepX() != 0 && pos.getZ() != bottomLeft.getZ()) {
            return false;
        }

        if (right.getStepZ() != 0 && pos.getX() != bottomLeft.getX()) {
            return false;
        }

        int u = right.getStepX() != 0
                ? (pos.getX() - bottomLeft.getX()) * right.getStepX()
                : (pos.getZ() - bottomLeft.getZ()) * right.getStepZ();
        int v = pos.getY() - bottomLeft.getY();

        boolean inBox = u >= -1 && u <= frame.width() && v >= -1 && v <= frame.height();
        boolean onRing = u == -1 || u == frame.width() || v == -1 || v == frame.height();
        return inBox && onRing;
    }

    /** Fills the opening and reports how many cells actually changed. */
    private static int fill(final ServerLevel level, final Frame frame, final BlockPos.MutableBlockPos cursor) {
        BlockState portalState = ModBlocks.HOLLOW_HORIZON_PORTAL.get().defaultBlockState()
                .setValue(HollowHorizonPortalBlock.AXIS, frame.axis());
        int placed = 0;

        for (int v = 0; v < frame.height(); v++) {
            for (int u = 0; u < frame.width(); u++) {
                cell(cursor, frame.bottomLeft(), frame.right(), u, v);
                if (level.getBlockState(cursor).isAir()) {
                    level.setBlock(cursor, portalState, PORTAL_FLAGS);
                    placed++;
                }
            }
        }

        return placed;
    }

    private static void cell(final BlockPos.MutableBlockPos cursor, final BlockPos bottomLeft, final Direction right, final int u, final int v) {
        cursor.set(bottomLeft.getX() + right.getStepX() * u, bottomLeft.getY() + v, bottomLeft.getZ() + right.getStepZ() * u);
    }

    /** Air, or a cell of a portal that has already been lit and is being topped up. */
    private static boolean isCavity(final BlockState state) {
        return state.isAir() || state.is(ModBlocks.HOLLOW_HORIZON_PORTAL.get());
    }

    private static boolean isFrame(final BlockState state) {
        return state.is(ModBlocks.PHONOLITE_BRICKS.get());
    }

    // ------------------------------------------------------------------ sound

    /** The frame takes the note: amethyst resonance under a bell, both pitched up. */
    private static void playRisingChime(final ServerLevel level, final BlockPos pos) {
        double x = pos.getX() + 0.5;
        double y = pos.getY() + 0.5;
        double z = pos.getZ() + 0.5;
        level.playSound(null, pos, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.BLOCKS, 1.0F, 1.4F);
        level.playSound(null, x, y, z, SoundEvents.NOTE_BLOCK_BELL, SoundSource.BLOCKS, 0.8F, 1.9F);
        level.playSound(null, pos, SoundEvents.PORTAL_TRIGGER, SoundSource.BLOCKS, 0.5F, 1.6F);
    }

    /** No frame, or a broken one: a dull bass note and a couple of notes hanging in the air. */
    private static void playOffKey(final ServerLevel level, final BlockPos pos) {
        double x = pos.getX() + 0.5;
        double y = pos.getY() + 1.1;
        double z = pos.getZ() + 0.5;
        level.playSound(null, x, y, z, SoundEvents.NOTE_BLOCK_BASS, SoundSource.BLOCKS, 0.7F, 0.6F);
        level.playSound(null, pos, SoundEvents.AMETHYST_BLOCK_HIT, SoundSource.BLOCKS, 0.5F, 0.5F);
        level.sendParticles(ParticleTypes.NOTE, x, y, z, 2, 0.25, 0.1, 0.25, 0.0);
    }
}

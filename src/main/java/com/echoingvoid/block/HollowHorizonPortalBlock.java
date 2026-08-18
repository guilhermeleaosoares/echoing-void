package com.echoingvoid.block;

import com.echoingvoid.registry.ModBlocks;
import com.echoingvoid.worldgen.HollowHorizonTeleporter;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.InsideBlockEffectApplier;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.ScheduledTickAccess;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Portal;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import java.util.Map;

/**
 * The standing wave that fills a lit phonolite frame and carries you to the Hollow Horizon.
 *
 * <p>The surface has no collision and only a faint glow of its own; it is the frame around it that
 * you see. Standing in it for a moment - long enough for the note to settle - moves you between the
 * Overworld and {@code echoing_void:the_hollow_horizon}. The dwell and the cooldown are not tracked
 * here: implementing {@link Portal} hands both to vanilla's {@code PortalProcessor}, which already
 * lives on the entity and costs nothing per tick.
 *
 * <p>Lighting is done by the tuning fork, not by fire - {@code BaseFireBlock} only ignites in the
 * Overworld and the Nether, so a naked flame will never open one of these.
 */
public class HollowHorizonPortalBlock extends Block implements Portal {
    public static final MapCodec<HollowHorizonPortalBlock> CODEC = simpleCodec(HollowHorizonPortalBlock::new);

    /** Which horizontal plane the sheet stands in, exactly as a nether portal declares it. */
    public static final EnumProperty<Direction.Axis> AXIS = BlockStateProperties.HORIZONTAL_AXIS;

    /** How long a player must stand in the wave before it takes them, in ticks. */
    private static final int PLAYER_DWELL_TICKS = 30;

    /** Bismuth cyan, the dimension's cold accent. Packed RGB, as 26.2 dust takes an int. */
    private static final DustParticleOptions BISMUTH_MOTE =
            new DustParticleOptions(0x00E5FF, 1.0F);

    /** The magenta harmonic that runs under the cyan. */
    private static final DustParticleOptions ARCANE_MOTE =
            new DustParticleOptions(0xFF007F, 0.8F);

    private static final Map<Direction.Axis, VoxelShape> SHAPES =
            Shapes.rotateHorizontalAxis(Block.column(4.0, 16.0, 0.0, 16.0));

    public HollowHorizonPortalBlock(final BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(AXIS, Direction.Axis.X));
    }

    @Override
    protected MapCodec<? extends Block> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(final StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(AXIS);
    }

    @Override
    protected VoxelShape getShape(final BlockState state, final BlockGetter level, final BlockPos pos, final CollisionContext context) {
        return SHAPES.get(state.getValue(AXIS));
    }

    // ------------------------------------------------------------------ travel

    @Override
    protected void entityInside(
            final BlockState state,
            final Level level,
            final BlockPos pos,
            final Entity entity,
            final InsideBlockEffectApplier effectApplier,
            final boolean isPrecise
    ) {
        // No timer of our own and no allocation: the entity already carries a PortalProcessor that
        // counts the dwell, decays when you step out, and respects the entity's portal cooldown.
        if (entity.canUsePortal(false)) {
            entity.setAsInsidePortal(this, pos);
        }
    }

    @Override
    public int getPortalTransitionTime(final ServerLevel level, final Entity entity) {
        return entity instanceof Player ? PLAYER_DWELL_TICKS : 0;
    }

    @Override
    public Portal.Transition getLocalTransition() {
        return Portal.Transition.CONFUSION;
    }

    @Override
    public TeleportTransition getPortalDestination(final ServerLevel currentLevel, final Entity entity, final BlockPos portalEntryPos) {
        return HollowHorizonTeleporter.destinationFor(currentLevel, entity, portalEntryPos);
    }

    // ------------------------------------------------------------- upkeep

    /**
     * Collapses the sheet when its frame is opened. Each cell only checks the four neighbours that
     * lie in its own plane, so breaking one brick turns the cell beside it to air, which in turn
     * fails the same test for the next cell along - the whole surface unravels from one break.
     */
    @Override
    protected BlockState updateShape(
            final BlockState state,
            final LevelReader level,
            final ScheduledTickAccess ticks,
            final BlockPos pos,
            final Direction directionToNeighbour,
            final BlockPos neighbourPos,
            final BlockState neighbourState,
            final RandomSource random
    ) {
        Direction.Axis axis = state.getValue(AXIS);
        Direction.Axis neighbourAxis = directionToNeighbour.getAxis();
        boolean inPlane = neighbourAxis == Direction.Axis.Y || neighbourAxis == axis;
        if (inPlane && !neighbourState.is(this) && !neighbourState.is(ModBlocks.PHONOLITE_BRICKS.get())) {
            return Blocks.AIR.defaultBlockState();
        }

        return super.updateShape(state, level, ticks, pos, directionToNeighbour, neighbourPos, neighbourState, random);
    }

    @Override
    protected BlockState rotate(final BlockState state, final Rotation rotation) {
        return switch (rotation) {
            case CLOCKWISE_90, COUNTERCLOCKWISE_90 -> switch (state.getValue(AXIS)) {
                case X -> state.setValue(AXIS, Direction.Axis.Z);
                case Z -> state.setValue(AXIS, Direction.Axis.X);
                default -> state;
            };
            default -> state;
        };
    }

    /** Picking the surface should give you nothing; the frame is the buildable part. */
    @Override
    protected ItemStack getCloneItemStack(final LevelReader level, final BlockPos pos, final BlockState state, final boolean includeData) {
        return ItemStack.EMPTY;
    }

    // ------------------------------------------------------------------ client

    @Override
    public void animateTick(final BlockState state, final Level level, final BlockPos pos, final RandomSource random) {
        // Client-only; the server path above never reaches here. Two particles a tick keeps the
        // surface alive without the particle storm a nether portal produces.
        if (random.nextInt(140) == 0) {
            level.playLocalSound(pos, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.BLOCKS,
                    0.35F, random.nextFloat() * 0.3F + 0.7F, false);
        }

        // Deliberately NOT ParticleTypes.PORTAL: the nether portal's purple swirl reads as
        // "this is a nether portal" and drags the wrong dimension's identity along with it.
        // A standing acoustic wave should shed colour from its own palette instead - bismuth
        // cyan motes drifting upward, with the occasional magenta harmonic.
        for (int i = 0; i < 2; i++) {
            double x = pos.getX() + random.nextDouble();
            double y = pos.getY() + random.nextDouble();
            double z = pos.getZ() + random.nextDouble();
            double drift = (random.nextDouble() - 0.5) * 0.12;
            level.addParticle(BISMUTH_MOTE, x, y, z, drift, random.nextDouble() * 0.06, drift);
        }

        if (random.nextInt(5) == 0) {
            level.addParticle(ARCANE_MOTE,
                    pos.getX() + random.nextDouble(),
                    pos.getY() + random.nextDouble(),
                    pos.getZ() + random.nextDouble(),
                    0.0, random.nextDouble() * 0.04, 0.0);
        }

        // A slow rising spark every so often, so the surface has depth rather than a flat fizz.
        if (random.nextInt(12) == 0) {
            level.addParticle(ParticleTypes.END_ROD,
                    pos.getX() + random.nextDouble(),
                    pos.getY() + random.nextDouble(),
                    pos.getZ() + random.nextDouble(),
                    0.0, 0.015, 0.0);
        }
    }
}

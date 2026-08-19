package com.echoingvoid.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * The Harmonic Pickaxe - stone answers to rhythm rather than to force.
 *
 * <p>The pickaxe remembers how long ago the wielder last broke a block. Land two breaks in a
 * row close to the ten-tick beat and the third one resonates: the 3x3 plane facing the miner
 * shatters along its acoustic fault lines and drops normally. Break arrhythmically and it is
 * an ordinary, if quick, pickaxe.
 *
 * <p>Only blocks of comparable hardness give way, and only ones this pickaxe could have
 * harvested anyway - the tool cheats the block count, never the tier gate.
 *
 * <p>PLAYER: "none of the new pickaxe effects work." They did not - not because the rhythm
 * logic was wrong, but because it lived in {@code Item#mineBlock}, and {@code
 * ServerPlayerGameMode#destroyBlock} only calls that for a player whose {@code
 * preventsBlockDrops()} is false. A Creative player's is true, so the method returns before
 * {@code itemStack.mineBlock(...)} is ever reached - the single most likely way anyone would
 * first try a new tool. {@code ForgeHooks.onBlockBreakEvent}, a few lines earlier in the same
 * method, fires {@link net.minecraftforge.event.level.BlockEvent.BreakEvent} unconditionally,
 * survival or creative, so the trigger now lives on that event instead (wired in
 * {@code CombatEvents}) and {@code mineBlock} is no longer overridden here at all - keeping
 * both would have double-counted every survival break, since both used to fire for one.
 */
public class HarmonicPickaxeItem extends Item {

    /** The tempo the tool is tuned to, in ticks between breaks. */
    private static final int BEAT_TICKS = 10;

    /** How far off the beat a break may land and still count. */
    private static final int BEAT_TOLERANCE = 3;

    /** Consecutive on-tempo intervals needed before the plane shatters. */
    private static final int STREAK_TO_SHATTER = 2;

    /** Beyond this many ticks the player has clearly stopped mining; the phrase restarts. */
    private static final int PHRASE_TIMEOUT = 60;

    /** Neighbours may be at most this much harder than the struck block. */
    private static final float HARDNESS_TOLERANCE = 1.5F;

    /**
     * Swing rhythm per player. Keyed by UUID and pruned when the player logs out - this is
     * never iterated, only looked up for the one player who just mined something.
     */
    private static final Map<UUID, Beat> RHYTHM = new HashMap<>();

    /** Reused cursor for the eight neighbours. The server breaks blocks on one thread. */
    private static final BlockPos.MutableBlockPos CURSOR = new BlockPos.MutableBlockPos();

    /** Guards against a shattered block feeding back into this hook. */
    private static boolean shattering;

    public HarmonicPickaxeItem(Item.Properties properties) {
        super(properties);
    }

    /**
     * Called from {@code CombatEvents} on {@link net.minecraftforge.event.level.BlockEvent.BreakEvent},
     * once per real block break, survival or creative alike - see the class javadoc for why
     * this is not {@code Item#mineBlock} any more.
     */
    public void onBlockBroken(ItemStack stack, ServerLevel level, BlockState state, BlockPos pos, Player player) {
        if (shattering) {
            return;
        }

        Beat beat = RHYTHM.get(player.getUUID());
        if (beat == null) {
            beat = new Beat();
            RHYTHM.put(player.getUUID(), beat);
            beat.lastBreakTick = player.tickCount;
            return;
        }

        int interval = player.tickCount - beat.lastBreakTick;
        beat.lastBreakTick = player.tickCount;

        if (interval > PHRASE_TIMEOUT) {
            beat.streak = 0;
            return;
        }

        if (Math.abs(interval - BEAT_TICKS) <= BEAT_TOLERANCE) {
            beat.streak++;
        } else {
            beat.streak = 0;
            return;
        }

        if (beat.streak >= STREAK_TO_SHATTER) {
            beat.streak = 0;
            shatter(level, player, stack, state, pos);
        }
    }

    /**
     * The fault-plane rectangle extends {@code widthLo..widthHi} (inclusive) along the plane's
     * horizontal axis and {@code heightLo..heightHi} along its vertical axis, centred on the
     * struck block. The base tool is a symmetric 3x3, {@code -1..1} on both. PLAYER, on the
     * Knell upgrade: "the area break of the knell pickaxe is amplified... 4x5, 5 wide 4 tall" -
     * see {@link KnellPickaxeItem}, which widens only the horizontal pair.
     *
     * <p>These two pairs only both have a real meaning when the fault plane is vertical - i.e.
     * the miner struck a wall. Striking a floor or ceiling makes the fault plane horizontal,
     * which has no vertical axis in it at all, so {@link #shatter} applies the width pair to
     * both plane axes in that case rather than leaving "height" undefined; a floor/ceiling
     * shatter is square at the wide dimension instead of a true rectangle.
     */
    protected int widthLo() {
        return -1;
    }

    protected int widthHi() {
        return 1;
    }

    protected int heightLo() {
        return -1;
    }

    protected int heightHi() {
        return 1;
    }

    /**
     * Breaks the blocks around {@code pos} in the plane the miner is facing. The struck block
     * itself is left to the vanilla break that called us.
     */
    private void shatter(ServerLevel level, Player player, ItemStack stack, BlockState struck, BlockPos pos) {
        float baseHardness = struck.getDestroySpeed(level, pos);
        if (baseHardness < 0.0F) {
            return;
        }
        float hardnessCap = baseHardness * HARDNESS_TOLERANCE + 0.5F;

        // The fault plane is perpendicular to the face being mined, so it is spanned by the two
        // axes the look direction is weakest on.
        Direction face = Direction.getApproximateNearest(player.getLookAngle());
        int broken = 0;
        int wLo = widthLo();
        int wHi = widthHi();
        int hLo = heightLo();
        int hHi = heightHi();

        // Which offset pair drives `a` and which drives `b` depends on which way the miner is
        // facing - see the width/height javadoc above for why the Y case uses the width pair
        // twice instead of an undefined height.
        int aLo, aHi, bLo, bHi;
        switch (face.getAxis()) {
            case X -> { aLo = hLo; aHi = hHi; bLo = wLo; bHi = wHi; } // a=Y(height), b=Z(width)
            case Z -> { aLo = wLo; aHi = wHi; bLo = hLo; bHi = hHi; } // a=X(width), b=Y(height)
            default -> { aLo = wLo; aHi = wHi; bLo = wLo; bHi = wHi; } // Y: floor/ceiling
        }

        shattering = true;
        try {
            for (int a = aLo; a <= aHi; a++) {
                for (int b = bLo; b <= bHi; b++) {
                    if (a == 0 && b == 0) {
                        continue;
                    }
                    switch (face.getAxis()) {
                        case X -> CURSOR.setWithOffset(pos, 0, a, b);
                        case Y -> CURSOR.setWithOffset(pos, a, 0, b);
                        case Z -> CURSOR.setWithOffset(pos, a, b, 0);
                    }

                    BlockState neighbour = level.getBlockState(CURSOR);
                    if (neighbour.isAir()) {
                        continue;
                    }
                    float hardness = neighbour.getDestroySpeed(level, CURSOR);
                    if (hardness < 0.0F || hardness > hardnessCap) {
                        continue;
                    }
                    if (!stack.isCorrectToolForDrops(neighbour)) {
                        continue;
                    }

                    // destroyBlock keeps the position around for loot and particles, so hand it
                    // an immutable copy rather than the shared cursor.
                    if (level.destroyBlock(CURSOR.immutable(), true, player)) {
                        broken++;
                    }
                }
            }
        } finally {
            shattering = false;
        }

        if (broken > 0) {
            stack.hurtAndBreak(broken, player, EquipmentSlot.MAINHAND);
            level.playSound(null, pos, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.BLOCKS, 0.8F, 1.4F);
        }
    }

    /** Drops a player's rhythm when they leave, so the map never outgrows the online roster. */
    public static void forget(UUID playerId) {
        RHYTHM.remove(playerId);
    }

    /** Mutable so the common path is a map lookup and two field writes, with no allocation. */
    private static final class Beat {
        int lastBreakTick;
        int streak;
    }
}

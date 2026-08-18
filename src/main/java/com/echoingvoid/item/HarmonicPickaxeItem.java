package com.echoingvoid.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
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

    @Override
    public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity owner) {
        boolean handled = super.mineBlock(stack, level, state, pos, owner);
        if (shattering || !(level instanceof ServerLevel serverLevel) || !(owner instanceof Player player)) {
            return handled;
        }

        Beat beat = RHYTHM.get(player.getUUID());
        if (beat == null) {
            beat = new Beat();
            RHYTHM.put(player.getUUID(), beat);
            beat.lastBreakTick = player.tickCount;
            return handled;
        }

        int interval = player.tickCount - beat.lastBreakTick;
        beat.lastBreakTick = player.tickCount;

        if (interval > PHRASE_TIMEOUT) {
            beat.streak = 0;
            return handled;
        }

        if (Math.abs(interval - BEAT_TICKS) <= BEAT_TOLERANCE) {
            beat.streak++;
        } else {
            beat.streak = 0;
            return handled;
        }

        if (beat.streak >= STREAK_TO_SHATTER) {
            beat.streak = 0;
            shatter(serverLevel, player, stack, state, pos);
        }
        return handled;
    }

    /**
     * The plane extends {@code loOffset..hiOffset} (inclusive) along both axes of the fault
     * plane, centred on the struck block. 3x3 (the base tool) is {@code -1..1}; the Knell
     * pickaxe overrides this to {@code -1..2} for a 4x4 plane, which has no exact centre, so it
     * is biased one step towards positive rather than symmetric - the simplest choice that still
     * reads as "wider" rather than "shifted" once the eight-to-fifteen blocks are gone.
     */
    protected int loOffset() {
        return -1;
    }

    protected int hiOffset() {
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
        int lo = loOffset();
        int hi = hiOffset();

        shattering = true;
        try {
            for (int a = lo; a <= hi; a++) {
                for (int b = lo; b <= hi; b++) {
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

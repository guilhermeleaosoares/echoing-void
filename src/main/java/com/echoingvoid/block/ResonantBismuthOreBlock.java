package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Resonant Bismuth Ore - the crystal seam that the whole tech tree hangs off.
 *
 * <p>Shard drops come from the loot table. What this class adds is the tell: step on a seam and it
 * answers with a short spark of vibration, which is how a player learns the ore is acoustically live
 * before they ever craft a tuning fork.
 *
 * <p>The particle burst is gated on the entity having crossed into a new block this tick. Without
 * that gate {@code stepOn} fires every tick a mob is grounded and a single sheep standing on a vein
 * would push a particle packet to every nearby player sixty times a second.
 */
public class ResonantBismuthOreBlock extends Block {
    private static final int MIN_XP = 2;
    private static final int MAX_XP = 5;
    private static final int PARTICLE_COUNT = 3;

    public ResonantBismuthOreBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public int getExpDrop(BlockState state, LevelReader level, RandomSource randomSource, BlockPos pos, int fortuneLevel, int silkTouchLevel) {
        return silkTouchLevel == 0 ? Mth.nextInt(randomSource, MIN_XP, MAX_XP) : 0;
    }

    @Override
    public void stepOn(Level level, BlockPos pos, BlockState onState, Entity entity) {
        if (level instanceof ServerLevel serverLevel && hasEnteredNewColumn(entity, pos)) {
            // Level#addParticle is a no-op on the server, so the burst has to be sent explicitly.
            serverLevel.sendParticles(
                ParticleTypes.ELECTRIC_SPARK,
                pos.getX() + 0.5,
                pos.getY() + 1.0,
                pos.getZ() + 0.5,
                PARTICLE_COUNT,
                0.25,
                0.05,
                0.25,
                0.02
            );
        }

        super.stepOn(level, pos, onState, entity);
    }

    /**
     * True only on the tick an entity walks from one block column into another. {@code xOld}/
     * {@code zOld} hold the position at the start of the tick, so comparing their block coordinates
     * against the stepped-on block tells us whether a boundary was just crossed.
     */
    private static boolean hasEnteredNewColumn(Entity entity, BlockPos pos) {
        return Mth.floor(entity.xOld) != pos.getX() || Mth.floor(entity.zOld) != pos.getZ();
    }
}

package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Calcified Resonance Leaves - the crystal canopy of a Hollow Horizon tuning tree.
 *
 * <p>Deliberately a plain {@link Block} rather than {@code LeavesBlock}: in 26.2 {@code LeavesBlock}
 * is abstract, carries a distance/persistence decay state machine this canopy does not want, and
 * would force a codec implementation for no gain. Bismuth seedling drops come from the loot table.
 *
 * <p>All this class adds is atmosphere: an occasional chime and a mote drifting out of the
 * underside. Everything here runs inside {@link #animateTick}, which the client calls for blocks
 * near the camera - the server never executes a line of it.
 */
public class CalcifiedResonanceLeavesBlock extends Block {
    /** One in this many display ticks produces a rustle. Roughly one every few seconds per block. */
    private static final int RUSTLE_CHANCE = 90;

    public CalcifiedResonanceLeavesBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (random.nextInt(RUSTLE_CHANCE) != 0) {
            return;
        }

        double x = pos.getX() + random.nextDouble();
        double y = pos.getY() - 0.05;
        double z = pos.getZ() + random.nextDouble();

        // A mote shed from the underside, falling slowly - the canopy shedding its resonance.
        level.addParticle(ParticleTypes.ELECTRIC_SPARK, x, y, z, 0.0, -0.02, 0.0);

        // Quiet, and pitched high, so a whole canopy reads as a shimmer rather than a chorus.
        level.playLocalSound(
            pos,
            SoundEvents.AMETHYST_BLOCK_CHIME,
            SoundSource.BLOCKS,
            0.2F,
            0.8F + random.nextFloat() * 0.6F,
            false
        );
    }
}

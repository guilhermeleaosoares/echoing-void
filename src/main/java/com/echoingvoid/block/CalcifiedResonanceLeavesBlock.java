package com.echoingvoid.block;

import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Calcified Resonance Leaves - the crystal canopy of a Hollow Horizon tuning tree.
 *
 * <p>PLAYER: "all the leaves from all the trees in the echoing void dimention should decay like
 * naturally generated overworld leaves, so when the connected log blocks are harvested and
 * destroyed, the leaves start decomposing. individually placed leaf blocks placed by the player
 * should never decay."
 *
 * <p>This was a plain {@code Block}, on the reasoning that {@code LeavesBlock} "carries a
 * distance/persistence decay state machine this canopy does not want". It wants it now, and
 * inheriting it is what makes both halves of the request true at once rather than approximated:
 * {@code DISTANCE} counts hops to the nearest {@code #minecraft:logs} block and decay fires at 7,
 * and {@code getStateForPlacement} marks anything a player places {@code PERSISTENT}, which
 * {@code decaying()} then refuses to remove. Bismuth seedling drops still come from the loot table.
 *
 * <p>Everything else here is atmosphere: an occasional chime, and a spark drifting out of the
 * underside as the canopy sheds its resonance. Both run inside display ticks the client calls for
 * blocks near the camera - the server never executes a line of them.
 */
public class CalcifiedResonanceLeavesBlock extends LeavesBlock {
    public static final MapCodec<CalcifiedResonanceLeavesBlock> CODEC =
            simpleCodec(CalcifiedResonanceLeavesBlock::new);

    /** One in this many display ticks produces a rustle. Roughly one every few seconds per block. */
    private static final int RUSTLE_CHANCE = 90;

    /** How often {@code LeavesBlock} sheds a falling spark, on its own schedule. */
    private static final float SPARK_FALL_CHANCE = 0.01F;

    public CalcifiedResonanceLeavesBlock(BlockBehaviour.Properties properties) {
        super(SPARK_FALL_CHANCE, properties);
    }

    @Override
    public MapCodec<CalcifiedResonanceLeavesBlock> codec() {
        return CODEC;
    }

    /** The falling-leaf particle {@code LeavesBlock} requires - a shed spark, for this canopy. */
    @Override
    protected void spawnFallingLeavesParticle(Level level, BlockPos pos, RandomSource random) {
        level.addParticle(
                ParticleTypes.ELECTRIC_SPARK,
                pos.getX() + random.nextDouble(),
                pos.getY() - 0.05,
                pos.getZ() + random.nextDouble(),
                0.0, -0.02, 0.0);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        // LeavesBlock's own animateTick drives spawnFallingLeavesParticle above.
        super.animateTick(state, level, pos, random);
        if (random.nextInt(RUSTLE_CHANCE) != 0) {
            return;
        }

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

package com.echoingvoid.block;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The coloured canopies of the Hollow Horizon: Amber Resonance Leaves and Violet Resonance Leaves.
 *
 * <p>Gameplay intent: three canopy hues (these two plus the older Calcified Resonance Leaves) so a
 * grove reads as foliage by colour rather than by transparency alone, and so a player can tell one
 * grove from another at draw distance. Each canopy emits a little light, which is what makes a
 * treeline legible against dark stone.
 *
 * <p>PLAYER: "all the leaves from all the trees in the echoing void dimention should decay like
 * naturally generated overworld leaves, so when the connected log blocks are harvested and
 * destroyed, the leaves start decomposing. individually placed leaf blocks placed by the player
 * should never decay."
 *
 * <p>This was a plain {@link Block} on the reasoning that {@code LeavesBlock} is abstract in 26.2
 * and "drags in the distance/persistence decay state machine these mineral canopies do not want".
 * That state machine is precisely what is wanted now, and extending {@code LeavesBlock} answers
 * both halves of the request without reimplementing either: {@code DISTANCE} counts hops to the
 * nearest {@code #minecraft:logs} block and decay fires at 7, while {@code getStateForPlacement}
 * sets {@code PERSISTENT} on anything a player places and {@code decaying()} refuses to touch a
 * persistent block. Our logs are already in {@code #minecraft:logs}, so the distance search finds
 * them with nothing further to declare.
 *
 * <p>The mote colour is per-instance so both canopies share this one class and differ only in the
 * hue they shed, matching the hue of their own texture. It doubles as this block's falling-leaf
 * particle, the one member {@code LeavesBlock} leaves abstract.
 */
public class ResonanceLeavesBlock extends LeavesBlock {
    public static final MapCodec<ResonanceLeavesBlock> CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    Codec.INT.fieldOf("mote_color").forGetter(block -> block.moteColor),
                    propertiesCodec()
            ).apply(i, ResonanceLeavesBlock::new));

    /** One in this many display ticks rustles. Roughly one event every few seconds per block. */
    private static final int RUSTLE_CHANCE = 110;

    /** How often {@code LeavesBlock} sheds a falling mote, on its own schedule. */
    private static final float MOTE_FALL_CHANCE = 0.01F;

    private final int moteColor;

    public ResonanceLeavesBlock(int moteColor, BlockBehaviour.Properties properties) {
        super(MOTE_FALL_CHANCE, properties);
        this.moteColor = moteColor;
    }

    /** The falling-leaf particle {@code LeavesBlock} requires, in this canopy's own hue. */
    @Override
    protected void spawnFallingLeavesParticle(Level level, BlockPos pos, RandomSource random) {
        level.addParticle(
                new DustParticleOptions(this.moteColor, 0.9F),
                pos.getX() + random.nextDouble(),
                pos.getY() - 0.05,
                pos.getZ() + random.nextDouble(),
                0.0, -0.02, 0.0);
    }

    @Override
    public MapCodec<ResonanceLeavesBlock> codec() {
        return CODEC;
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        // LeavesBlock's own animateTick drives spawnFallingLeavesParticle above.
        super.animateTick(state, level, pos, random);
        if (random.nextInt(RUSTLE_CHANCE) != 0) {
            return;
        }

        // Quiet and high, so a whole canopy reads as a shimmer rather than a chorus.
        level.playLocalSound(
            pos,
            SoundEvents.AMETHYST_BLOCK_CHIME,
            SoundSource.BLOCKS,
            0.16F,
            0.9F + random.nextFloat() * 0.7F,
            false
        );
    }
}

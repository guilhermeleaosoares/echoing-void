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
import net.minecraft.world.level.block.Block;
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
 * <p>Deliberately a plain {@link Block} rather than {@code LeavesBlock}, for the same reason
 * {@link CalcifiedResonanceLeavesBlock} is: in 26.2 {@code LeavesBlock} is abstract, drags in the
 * distance/persistence decay state machine these mineral canopies do not want, and would force a
 * codec and a falling-leaf particle implementation for no gain. Seedling drops come from the loot
 * table instead.
 *
 * <p>The mote colour is per-instance so both canopies share this one class and differ only in the
 * hue they shed, matching the hue of their own texture.
 */
public class ResonanceLeavesBlock extends Block {
    public static final MapCodec<ResonanceLeavesBlock> CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    Codec.INT.fieldOf("mote_color").forGetter(block -> block.moteColor),
                    propertiesCodec()
            ).apply(i, ResonanceLeavesBlock::new));

    /** One in this many display ticks rustles. Roughly one event every few seconds per block. */
    private static final int RUSTLE_CHANCE = 110;

    private final int moteColor;

    public ResonanceLeavesBlock(int moteColor, BlockBehaviour.Properties properties) {
        super(properties);
        this.moteColor = moteColor;
    }

    @Override
    public MapCodec<ResonanceLeavesBlock> codec() {
        return CODEC;
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (random.nextInt(RUSTLE_CHANCE) != 0) {
            return;
        }

        double x = pos.getX() + random.nextDouble();
        double y = pos.getY() - 0.05;
        double z = pos.getZ() + random.nextDouble();

        // A mote shed from the underside, falling slowly, tinted to this canopy's own hue.
        level.addParticle(new DustParticleOptions(this.moteColor, 0.9F), x, y, z, 0.0, -0.02, 0.0);

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

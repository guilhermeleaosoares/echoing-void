package com.echoingvoid.fluid;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.InsideBlockEffectApplier;
import net.minecraft.world.entity.InsideBlockEffectType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.FluidState;
import net.minecraftforge.fluids.ForgeFlowingFluid;
import org.jspecify.annotations.Nullable;

/**
 * The flowing behaviour of {@link HushwaterFluidType}.
 *
 * <p>Only the sensory half lives here. Everything numeric - spread distance, drop-off and tick
 * rate - is passed in through {@link ForgeFlowingFluid.Properties} by
 * {@code com.echoingvoid.registry.ModFluids}, and the healing lives in
 * {@code com.echoingvoid.event.FluidEvents}. What is left is the ambience and the one behaviour
 * that has to be here: putting a burning entity out, which is the fluid's own
 * {@code canExtinguish} contract rather than something an event can see.
 */
public abstract class HushwaterFluid extends ForgeFlowingFluid {

    protected HushwaterFluid(Properties properties) {
        super(properties);
    }

    @Override
    public void animateTick(final Level level, final BlockPos pos, final FluidState fluidState,
                            final RandomSource random) {
        // Same shape as WaterFluid: a rare ambient note from a settled body, motes from a
        // moving one. The sound is the sculk shrieker's soft cousin rather than water's
        // gurgle, because this fluid is meant to read as quiet, not wet.
        if (!fluidState.isSource() && !fluidState.getValue(FALLING)) {
            if (random.nextInt(96) == 0) {
                level.playLocalSound(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5,
                        SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.AMBIENT,
                        random.nextFloat() * 0.15F + 0.15F,
                        random.nextFloat() * 0.4F + 0.6F, false);
            }
        } else if (random.nextInt(12) == 0) {
            level.addParticle(ParticleTypes.GLOW,
                    pos.getX() + random.nextDouble(),
                    pos.getY() + random.nextDouble(),
                    pos.getZ() + random.nextDouble(),
                    0.0, 0.0, 0.0);
        }
    }

    @Override
    public @Nullable ParticleOptions getDripParticle() {
        return ParticleTypes.DRIPPING_DRIPSTONE_WATER;
    }

    @Override
    protected void entityInside(final Level level, final BlockPos pos, final Entity entity,
                                final InsideBlockEffectApplier effectApplier) {
        effectApplier.apply(InsideBlockEffectType.EXTINGUISH);
    }

    public static final class Flowing extends HushwaterFluid {
        public Flowing(Properties properties) {
            super(properties);
            registerDefaultState(getStateDefinition().any().setValue(LEVEL, 7));
        }

        @Override
        protected void createFluidStateDefinition(final StateDefinition.Builder<Fluid, FluidState> builder) {
            super.createFluidStateDefinition(builder);
            builder.add(LEVEL);
        }

        @Override
        public int getAmount(final FluidState state) {
            return state.getValue(LEVEL);
        }

        @Override
        public boolean isSource(final FluidState state) {
            return false;
        }
    }

    public static final class Source extends HushwaterFluid {
        public Source(Properties properties) {
            super(properties);
        }

        @Override
        public int getAmount(final FluidState state) {
            return 8;
        }

        @Override
        public boolean isSource(final FluidState state) {
            return true;
        }
    }
}

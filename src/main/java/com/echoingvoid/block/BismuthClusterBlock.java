package com.echoingvoid.block;

import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.AmethystClusterBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Bismuth Cluster - a cyan crystal spray that grows off any surface, floor, wall or ceiling.
 *
 * <p>Gameplay intent: a directional, non-full-cube light source, so caves and chasms get lit
 * geometry that is not just another glowing cube. Walking into a cluster chimes, which gives the
 * player an audio cue that they have found a Resonant Bismuth deposit even in the dark.
 *
 * <p>Extends {@link AmethystClusterBlock} for its facing/waterlogging state, its rotated collision
 * shapes and its survival rule (it drops when the face it grew on is broken). Height and width are
 * fixed here rather than exposed, so a plain {@code simpleCodec} suffices - the cluster only ever
 * exists at one size.
 */
public class BismuthClusterBlock extends AmethystClusterBlock {
    /**
     * Typed to the superclass, not to this class: {@code AmethystClusterBlock.codec()} is declared
     * as {@code MapCodec<AmethystClusterBlock>}, and generics are invariant, so a narrower return
     * type would not be a legal override.
     */
    public static final MapCodec<AmethystClusterBlock> CODEC = simpleCodec(BismuthClusterBlock::new);

    /** Pixels of the 16-unit block the spray stands proud of its surface. */
    private static final float HEIGHT = 7.0F;

    /** Pixels wide the spray is, centred on its face. */
    private static final float WIDTH = 3.0F;

    /** Colour of the motes it sheds, taken from the bismuth family's bright tone. */
    private static final int MOTE_COLOR = 0x00E5FF;

    /** One in this many display ticks emits a mote. */
    private static final int MOTE_CHANCE = 40;

    public BismuthClusterBlock(BlockBehaviour.Properties properties) {
        super(HEIGHT, WIDTH, properties);
    }

    @Override
    public MapCodec<AmethystClusterBlock> codec() {
        return CODEC;
    }

    /** Stepping on a spray of crystal rings it. Server-side so every nearby player hears it. */
    @Override
    public void stepOn(Level level, BlockPos pos, BlockState onState, Entity entity) {
        if (!level.isClientSide()) {
            level.playSound(
                null,
                pos,
                SoundEvents.AMETHYST_BLOCK_CHIME,
                SoundSource.BLOCKS,
                0.6F,
                1.1F + level.getRandom().nextFloat() * 0.5F
            );
        }

        super.stepOn(level, pos, onState, entity);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (random.nextInt(MOTE_CHANCE) != 0) {
            return;
        }

        double x = pos.getX() + 0.2 + random.nextDouble() * 0.6;
        double y = pos.getY() + 0.2 + random.nextDouble() * 0.6;
        double z = pos.getZ() + 0.2 + random.nextDouble() * 0.6;

        level.addParticle(new DustParticleOptions(MOTE_COLOR, 0.8F), x, y, z, 0.0, 0.01, 0.0);
    }
}

package com.echoingvoid.block;

import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.AmethystBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Humming Crystal - the emissive violet mass that grows through the deep strata.
 *
 * <p>Gameplay intent: the deep bands of the dimension were unlit and unnavigable, so this is the
 * natural light source down there. It reads as a landmark from across a cavern, which is what makes
 * the lower world traversable without the player carrying a stack of torches.
 *
 * <p>Extends {@link AmethystBlock} purely for its behaviour, not its material: that base class
 * chimes when a projectile strikes it, which is exactly the reaction a resonant crystal should have
 * and is free to inherit. The light level, hardness and translucency all come from the properties
 * passed by the registry.
 */
public class HummingCrystalBlock extends AmethystBlock {
    public static final MapCodec<HummingCrystalBlock> CODEC = simpleCodec(HummingCrystalBlock::new);

    /** Colour of the motes it sheds, taken from the arcane family's bright tone. */
    private static final int MOTE_COLOR = 0xFF007F;

    /** One in this many display ticks emits a mote. Sparse, so a vein glitters rather than smokes. */
    private static final int MOTE_CHANCE = 60;

    public HummingCrystalBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<HummingCrystalBlock> codec() {
        return CODEC;
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (random.nextInt(MOTE_CHANCE) != 0) {
            return;
        }

        // Sit the mote just outside a random face so it is visible against the block, not inside it.
        double x = pos.getX() - 0.1 + random.nextDouble() * 1.2;
        double y = pos.getY() - 0.1 + random.nextDouble() * 1.2;
        double z = pos.getZ() - 0.1 + random.nextDouble() * 1.2;

        level.addParticle(new DustParticleOptions(MOTE_COLOR, 1.0F), x, y, z, 0.0, 0.005, 0.0);
    }
}

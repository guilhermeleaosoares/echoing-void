package com.echoingvoid.block;

import com.echoingvoid.EchoingVoid;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.TagKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.VegetationBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * The small cross-model growths that carpet the floor of the Hollow Horizon - Echo Sprout, Chime
 * Grass and Crystal Bloom.
 *
 * <p>Gameplay intent: ground clutter is the cheapest way to stop a stone floor reading as a
 * texture swatch, so these are meant to be scattered densely and broken instantly. They cost the
 * player nothing to walk through and drop themselves, which keeps them decorative rather than a
 * resource.
 *
 * <p>Each instance carries its own mote colour so a grove of sprouts sheds cyan and a bloom sheds
 * magenta from the same class. Motes are only shed by growths that actually emit light, so Chime
 * Grass stays quiet while the glowing ones shimmer.
 *
 * <p>Placement rules come from {@link VegetationBlock}, which asks {@link #mayPlaceOn}. Vanilla's
 * answer is the overworld dirt family, which no block in this dimension belongs to, so the check is
 * widened with our own {@link #SUPPORTS_VOID_VEGETATION} tag. That tag is data, not code, so the
 * worldgen datapack can add a stone to it without a recompile.
 */
public class VoidPlantBlock extends VegetationBlock {
    public static final MapCodec<VoidPlantBlock> CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    Codec.INT.fieldOf("mote_color").forGetter(block -> block.moteColor),
                    propertiesCodec()
            ).apply(i, VoidPlantBlock::new));

    /** Blocks these growths will stand on. Populated by {@code tools/gen_terrain_tags.py}. */
    public static final TagKey<Block> SUPPORTS_VOID_VEGETATION =
            TagKey.create(Registries.BLOCK, EchoingVoid.id("supports_void_vegetation"));

    /** Same footprint vanilla gives short grass: narrow, and shorter than a full block. */
    private static final VoxelShape SHAPE = Block.column(12.0, 0.0, 13.0);

    /** One in this many display ticks sheds a mote, so a dense patch reads as a slow shimmer. */
    private static final int MOTE_CHANCE = 120;

    private final int moteColor;

    public VoidPlantBlock(int moteColor, BlockBehaviour.Properties properties) {
        super(properties);
        this.moteColor = moteColor;
    }

    @Override
    public MapCodec<VoidPlantBlock> codec() {
        return CODEC;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPE;
    }

    @Override
    protected boolean mayPlaceOn(BlockState state, BlockGetter level, BlockPos pos) {
        return state.is(SUPPORTS_VOID_VEGETATION) || super.mayPlaceOn(state, level, pos);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (state.getLightEmission() == 0 || random.nextInt(MOTE_CHANCE) != 0) {
            return;
        }

        double x = pos.getX() + 0.3 + random.nextDouble() * 0.4;
        double y = pos.getY() + 0.4 + random.nextDouble() * 0.5;
        double z = pos.getZ() + 0.3 + random.nextDouble() * 0.4;

        // Drifting upward and very slowly - the growth is exhaling, not sparking.
        level.addParticle(new DustParticleOptions(this.moteColor, 0.7F), x, y, z, 0.0, 0.01, 0.0);
    }
}

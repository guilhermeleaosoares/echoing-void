package com.echoingvoid.block;

import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * A crop of the Hollow Horizon: Resonant Wheat, Chime Root or Void Tuber.
 *
 * <p>Two differences from vanilla's {@link CropBlock}, and no others - the growth curve, the age
 * property and the bonemeal behaviour are all inherited unchanged, because a player who has farmed
 * before should not have to relearn anything:
 *
 * <ol>
 *   <li>{@link #mayPlaceOn} accepts {@link VoidFarmlandBlock} and nothing else. Forge's
 *       {@code Block#canSustainPlant} tests {@code plantable instanceof VegetationBlock &&
 *       veg.mayPlaceOn(...)} BEFORE any of its tag fallbacks, so this one method is the whole
 *       answer to "where will this grow" - a void crop cannot be planted on vanilla farmland, on
 *       dirt, or on untilled moss.
 *   <li>The seed item is a constructor argument rather than hard-coded to
 *       {@code Items.WHEAT_SEEDS}, so middle-clicking a crop in creative yields the right seed.
 *       It is held as a {@link ResourceKey} rather than as an {@code Item}, because a crop block
 *       is built during BLOCK registration and its seed item does not exist yet at that moment.
 * </ol>
 */
public class VoidCropBlock extends CropBlock {
    public static final MapCodec<VoidCropBlock> CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    ResourceKey.codec(Registries.ITEM).fieldOf("seed").forGetter(b -> b.seed),
                    propertiesCodec()
            ).apply(i, VoidCropBlock::new));

    private final ResourceKey<Item> seed;

    @Override
    public MapCodec<VoidCropBlock> codec() {
        return CODEC;
    }

    public VoidCropBlock(ResourceKey<Item> seed, BlockBehaviour.Properties properties) {
        super(properties);
        this.seed = seed;
    }

    @Override
    protected boolean mayPlaceOn(BlockState state, BlockGetter level, BlockPos pos) {
        return state.getBlock() instanceof VoidFarmlandBlock;
    }

    /**
     * The exclusivity rule, stated once and for both paths.
     *
     * <p>{@link #mayPlaceOn} alone is NOT enough, and finding that out cost a
     * test run. It governs the PLACEMENT path only. Once a crop is standing,
     * {@code VegetationBlock#canSurvive} takes the other branch of its own
     * {@code if} and asks the SOIL instead - {@code canSustainPlant} - and
     * Forge's default for that walks a chain of fallbacks. Ours reaches
     * {@code PlantType.CROP -> state.is(BlockTags.GROWS_CROPS)}, and vanilla
     * farmland is in that tag. So a void crop dropped on vanilla farmland by
     * any means other than the item survived there quite happily.
     *
     * <p>Answering here settles both paths at once, and says the rule in the
     * one place a reader will look for it.
     */
    @Override
    protected boolean canSurvive(BlockState state, LevelReader level, BlockPos pos) {
        return hasSufficientLight(level, pos)
                && level.getBlockState(pos.below()).getBlock() instanceof VoidFarmlandBlock;
    }

    @Override
    protected ItemLike getBaseSeedId() {
        // Resolved against the frozen registry at call time. Returning the block itself when the
        // lookup fails matches vanilla's own fallback in StemBlock#getCloneItemStack and keeps a
        // half-registered state from throwing on a pick-block.
        return net.minecraft.core.registries.BuiltInRegistries.ITEM.getOptional(this.seed)
                .orElse(this.asItem());
    }

    @Override
    protected ItemStack getCloneItemStack(LevelReader level, BlockPos pos, BlockState state,
                                          boolean includeData) {
        return new ItemStack(this.getBaseSeedId());
    }
}

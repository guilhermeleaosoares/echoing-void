package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.StemBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The Echo Gourd's stem: vanilla's {@link StemBlock} with the soil rule tightened.
 *
 * <p>Vanilla's own rule is {@code state.is(stemSupportBlocks) || state.getBlock() instanceof
 * FarmlandBlock}, and that second clause is the leak - it lets the gourd take on ordinary farmland
 * however carefully the tag is written. Worse, once the stem is standing, survival stops going
 * through {@code mayPlaceOn} at all and goes through Forge's {@code canSustainPlant}, which falls
 * through to {@code PlantType.CROP -> BlockTags.GROWS_CROPS} - and vanilla farmland is in that tag.
 *
 * <p>Both holes are closed by answering both questions here. See
 * {@link VoidCropBlock#canSurvive} for the same fix on the three ordinary crops.
 */
public class VoidStemBlock extends StemBlock {

    public VoidStemBlock(ResourceKey<Block> fruit, ResourceKey<Block> attachedStem,
                         ResourceKey<Item> seed, TagKey<Block> stemSupportBlocks,
                         TagKey<Block> fruitSupportBlocks, BlockBehaviour.Properties properties) {
        super(fruit, attachedStem, seed, stemSupportBlocks, fruitSupportBlocks, properties);
    }

    @Override
    protected boolean mayPlaceOn(BlockState state, BlockGetter level, BlockPos pos) {
        return state.getBlock() instanceof VoidFarmlandBlock;
    }

    @Override
    protected boolean canSurvive(BlockState state, LevelReader level, BlockPos pos) {
        return level.getBlockState(pos.below()).getBlock() instanceof VoidFarmlandBlock;
    }
}

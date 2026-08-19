package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.AttachedStemBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The bent stem left behind once a gourd has set. Same soil rule as {@link VoidStemBlock}, for the
 * same reason: a stem that has already fruited must not be able to sit on ground the stem it grew
 * from could never have taken on.
 */
public class VoidAttachedStemBlock extends AttachedStemBlock {

    public VoidAttachedStemBlock(ResourceKey<Block> stem, ResourceKey<Block> fruit,
                                 ResourceKey<Item> seed, TagKey<Block> supportBlocks,
                                 BlockBehaviour.Properties properties) {
        super(stem, fruit, seed, supportBlocks, properties);
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

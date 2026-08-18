package com.echoingvoid.block;

import com.echoingvoid.registry.ModBlocks;
import com.mojang.serialization.MapCodec;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.ToolAction;
import net.minecraftforge.common.ToolActions;
import org.jspecify.annotations.Nullable;

/**
 * Petrified Tuning Wood - the trunk of a Hollow Horizon tuning tree, mineral all the way through.
 *
 * <p>Stripping it with an axe exposes the resonant core
 * ({@code ModBlocks.STRIPPED_PETRIFIED_TUNING_WOOD}) and keeps the pillar's axis, so a horizontal
 * beam stays horizontal.
 *
 * <p>Vanilla's {@code AxeItem.STRIPPABLES} is an immutable map built at class-init, so a mod cannot
 * add to it. Forge's route is {@link #getToolModifiedState}: {@code AxeItem#useOn} asks the block
 * what it becomes before falling back to the vanilla table, and handles placing the state, playing
 * the strip sound and damaging the axe itself. All this method has to do is answer the question.
 */
public class PetrifiedTuningWoodBlock extends RotatedPillarBlock {
    public static final MapCodec<PetrifiedTuningWoodBlock> CODEC = simpleCodec(PetrifiedTuningWoodBlock::new);

    public PetrifiedTuningWoodBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<PetrifiedTuningWoodBlock> codec() {
        return CODEC;
    }

    @Override
    public @Nullable BlockState getToolModifiedState(BlockState state, UseOnContext context, ToolAction toolAction, boolean simulate) {
        if (ToolActions.AXE_STRIP.equals(toolAction) && context.getItemInHand().canPerformAction(toolAction)) {
            return ModBlocks.STRIPPED_PETRIFIED_TUNING_WOOD.get()
                    .defaultBlockState()
                    .setValue(AXIS, state.getValue(AXIS));
        }

        return super.getToolModifiedState(state, context, toolAction, simulate);
    }
}

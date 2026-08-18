package com.echoingvoid.block;

import com.echoingvoid.registry.ModBlockFamilies;
import com.mojang.serialization.MapCodec;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.ToolAction;
import net.minecraftforge.common.ToolActions;
import org.jspecify.annotations.Nullable;

/**
 * Any axis-aligned timber in a block family that an axe can strip: the logs of the two new woods,
 * and the six-sided bark variants of all four.
 *
 * <p>Gameplay intent: a wood the player cannot strip is a wood with half the palette. Every trunk
 * and bark block in the mod answers an axe the same way, so the habit learned on oak transfers.
 *
 * <p>This exists as one class rather than a subclass per timber because the only thing that varies
 * is which block the strip produces, and that is data. {@link ModBlockFamilies#strippedForm(Block)}
 * holds the mapping; both directions of the family table are declared in one place there, so a new
 * wood needs no new Java.
 *
 * <p>Vanilla's {@code AxeItem.STRIPPABLES} is an immutable map built at class-init, so a mod cannot
 * add to it. Forge's route is {@link #getToolModifiedState}: {@code AxeItem#useOn} asks the block
 * what it becomes before falling back to the vanilla table, and handles placing the state, playing
 * the strip sound and damaging the axe itself. All this method has to do is answer the question.
 * That contract, and the axis-preserving {@code setValue(AXIS, ...)}, match the two hand-written
 * trunks that predate this class ({@link PetrifiedTuningWoodBlock}, {@link HummingStemBlock}).
 */
public class ResonantLogBlock extends RotatedPillarBlock {
    public static final MapCodec<ResonantLogBlock> CODEC = simpleCodec(ResonantLogBlock::new);

    public ResonantLogBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<ResonantLogBlock> codec() {
        return CODEC;
    }

    @Override
    public @Nullable BlockState getToolModifiedState(BlockState state, UseOnContext context, ToolAction toolAction, boolean simulate) {
        if (ToolActions.AXE_STRIP.equals(toolAction) && context.getItemInHand().canPerformAction(toolAction)) {
            Block stripped = ModBlockFamilies.strippedForm(this);
            if (stripped != null) {
                return stripped.defaultBlockState().setValue(AXIS, state.getValue(AXIS));
            }
        }

        return super.getToolModifiedState(state, context, toolAction, simulate);
    }
}

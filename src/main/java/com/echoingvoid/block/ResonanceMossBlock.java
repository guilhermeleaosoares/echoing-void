package com.echoingvoid.block;

import net.minecraft.core.Direction;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.ToolAction;
import net.minecraftforge.common.ToolActions;
import org.jspecify.annotations.Nullable;

/**
 * The dimension's ground cover, with one behaviour added: a hoe cuts it into
 * {@link VoidFarmlandBlock}.
 *
 * <p>Vanilla's tilling table ({@code HoeItem.TILLABLES}) is patched out by Forge and is not
 * extensible, so the block is asked instead: {@code HoeItem#useOn} calls
 * {@code state.getToolModifiedState(context, ToolActions.HOE_TILL, false)} and does whatever comes
 * back. Answering here rather than through {@code BlockEvent.BlockToolModificationEvent} keeps the
 * rule beside the block it belongs to, and means nothing has to be registered or unregistered for
 * it to work.
 *
 * <p>The {@code simulate} flag is honoured: it is Forge asking "would this work" without wanting
 * the world touched. Since answering costs nothing but a state lookup, both cases return the same
 * thing and neither writes.
 */
public class ResonanceMossBlock extends Block {

    public ResonanceMossBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public @Nullable BlockState getToolModifiedState(BlockState state, UseOnContext context,
                                                     ToolAction toolAction, boolean simulate) {
        if (ToolActions.HOE_TILL == toolAction) {
            // Vanilla's own rule for grass and dirt: you cannot till a block from below, and you
            // cannot till one with something sitting on it.
            if (context.getClickedFace() != Direction.DOWN
                    && context.getLevel().getBlockState(context.getClickedPos().above()).isAir()) {
                return VoidFarmlandBlock.tilled();
            }
            return null;
        }
        return super.getToolModifiedState(state, context, toolAction, simulate);
    }
}

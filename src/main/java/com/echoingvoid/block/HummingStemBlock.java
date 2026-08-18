package com.echoingvoid.block;

import com.echoingvoid.registry.ModTerrainBlocks;
import com.mojang.serialization.MapCodec;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.ToolAction;
import net.minecraftforge.common.ToolActions;
import org.jspecify.annotations.Nullable;

/**
 * Humming Stem - the violet trunk of the deeper groves, a second wood type alongside Petrified
 * Tuning Wood.
 *
 * <p>Gameplay intent: one trunk colour made every grove in the dimension look like the same tree.
 * This gives the arcane band its own timber so a violet canopy sits on a violet trunk, and gives
 * players a second building wood in a hue nothing else in the mod occupies.
 *
 * <p>Stripping it with an axe exposes {@code ModTerrainBlocks.STRIPPED_HUMMING_STEM} and preserves
 * the pillar axis, so a horizontal beam stays horizontal.
 *
 * <p>Vanilla's {@code AxeItem.STRIPPABLES} is an immutable map built at class-init, so a mod cannot
 * add to it. Forge's route is {@link #getToolModifiedState}: {@code AxeItem#useOn} asks the block
 * what it becomes before falling back to the vanilla table, and handles placing the state, playing
 * the strip sound and damaging the axe itself.
 */
public class HummingStemBlock extends RotatedPillarBlock {
    public static final MapCodec<HummingStemBlock> CODEC = simpleCodec(HummingStemBlock::new);

    public HummingStemBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<HummingStemBlock> codec() {
        return CODEC;
    }

    @Override
    public @Nullable BlockState getToolModifiedState(BlockState state, UseOnContext context, ToolAction toolAction, boolean simulate) {
        if (ToolActions.AXE_STRIP.equals(toolAction) && context.getItemInHand().canPerformAction(toolAction)) {
            return ModTerrainBlocks.STRIPPED_HUMMING_STEM.get()
                    .defaultBlockState()
                    .setValue(AXIS, state.getValue(AXIS));
        }

        return super.getToolModifiedState(state, context, toolAction, simulate);
    }
}

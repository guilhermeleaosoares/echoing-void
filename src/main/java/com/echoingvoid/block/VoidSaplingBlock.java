package com.echoingvoid.block;

import com.echoingvoid.registry.ModCrops;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.SaplingBlock;
import net.minecraft.world.level.block.grower.TreeGrower;
import net.minecraft.world.level.block.state.BlockState;

/**
 * A sapling for one of the four void trees.
 *
 * <p>PLAYER: "deprecate the bismuth seedling, and replace it with saplings for every different void
 * tree type."
 *
 * <p>The Bismuth Seedling was never a sapling. It was registered as a plain {@code Item} - it could
 * not be planted, and every one of the four canopies dropped the same one, so a player who felled
 * an Amber Bough and an Echo Ash got the same souvenir from both and could grow neither. These are
 * real {@link SaplingBlock}s, one per tree, each wired to that tree's own grove feature.
 *
 * <p>The only behaviour that differs from vanilla's is where one will take root.
 * {@code VegetationBlock.mayPlaceOn} accepts {@code #supports_vegetation} - dirt, grass, podzol,
 * moss, mud - which is an Overworld list and contains nothing this dimension has. Rather than push
 * Resonance Moss into that vanilla tag, where it would silently start accepting every plant in the
 * game, the ground this mod grows things on is added HERE and vanilla's list is kept as well. So a
 * void sapling takes on Resonance Moss and on void farmland, and also on ordinary dirt if a player
 * carries one home - which they can, the same way the crops travel.
 */
public class VoidSaplingBlock extends SaplingBlock {

    public static final MapCodec<VoidSaplingBlock> CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                            TreeGrower.CODEC.fieldOf("tree").forGetter(b -> b.grower),
                            propertiesCodec())
                    .apply(i, VoidSaplingBlock::new));

    /**
     * A second reference to the grower the superclass already holds.
     *
     * <p>{@code SaplingBlock.treeGrower} is private and its codec getter reaches it directly, so a
     * subclass with its own codec has no way to read it back. One field is cheaper than reflection
     * and cannot drift, because both are set from the same constructor argument.
     */
    private final TreeGrower grower;

    public VoidSaplingBlock(TreeGrower grower, Properties properties) {
        super(grower, properties);
        this.grower = grower;
    }

    @Override
    public MapCodec<? extends SaplingBlock> codec() {
        return CODEC;
    }

    @Override
    protected boolean mayPlaceOn(BlockState state, BlockGetter level, BlockPos pos) {
        return state.is(ModCrops.VOID_STEM_FRUIT_SOIL) || super.mayPlaceOn(state, level, pos);
    }
}

package com.echoingvoid.block;

import com.echoingvoid.registry.ModCrops;
import com.echoingvoid.registry.ModTerrainBlocks;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.ScheduledTickAccess;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.gameevent.GameEvent;
import net.minecraft.world.level.pathfinder.PathComputationType;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.minecraftforge.common.IPlantable;
import org.jspecify.annotations.Nullable;

/**
 * Resonance Moss cut open with a hoe. The Hollow Horizon's only tillable soil.
 *
 * <p>THE POINT OF THIS CLASS IS WHAT IT DOES NOT EXTEND. It is a plain
 * {@link Block}, deliberately not vanilla's {@code FarmlandBlock}, and that single fact is what
 * makes the void crops exclusive to it in both directions:
 *
 * <ul>
 *   <li>Vanilla crops cannot grow here. {@code CropBlock#mayPlaceOn} asks
 *       {@code state.getBlock() instanceof FarmlandBlock}, which is false, and Forge's fallback in
 *       {@code Block#canSustainPlant} then asks {@code state.is(BlockTags.GROWS_CROPS)}, which this
 *       block is deliberately not in. Wheat, carrots, potatoes and melons all refuse it.
 *   <li>Void crops cannot grow anywhere else. That one takes TWO overrides, not one:
 *       {@code mayPlaceOn} governs placement, and {@code canSurvive} governs standing, because a
 *       planted crop's survival goes through Forge's {@code canSustainPlant} instead - which falls
 *       through to {@code BlockTags.GROWS_CROPS}, a tag vanilla farmland is in. See
 *       {@link VoidCropBlock#canSurvive}.
 * </ul>
 *
 * <p>Everything else is vanilla farmland's behaviour with two substitutions: it dries back to
 * {@link ModTerrainBlocks#RESONANCE_MOSS} rather than to dirt, and it is watered by hushwater as
 * well as by water, which falls out of {@code HushwaterFluidType}'s {@code canHydrate(true)} -
 * {@code canBeHydrated} routes the question to the fluid, so no code here names the fluid at all.
 */
public class VoidFarmlandBlock extends Block {
    public static final MapCodec<VoidFarmlandBlock> CODEC = simpleCodec(VoidFarmlandBlock::new);

    public static final IntegerProperty MOISTURE = BlockStateProperties.MOISTURE;
    public static final int MAX_MOISTURE = 7;

    /** One pixel short of a full cube, exactly as vanilla farmland, so a crop sits in the dip. */
    private static final VoxelShape SHAPE = Block.column(16.0, 0.0, 15.0);

    /** Vanilla's radius: four blocks out and one up. */
    private static final int WATER_RANGE = 4;

    @Override
    public MapCodec<VoidFarmlandBlock> codec() {
        return CODEC;
    }

    public VoidFarmlandBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(MOISTURE, 0));
    }

    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks,
                                     BlockPos pos, Direction directionToNeighbour, BlockPos neighbourPos,
                                     BlockState neighbourState, RandomSource random) {
        if (directionToNeighbour == Direction.UP && !state.canSurvive(level, pos)) {
            ticks.scheduleTick(pos, this, 1);
        }
        return super.updateShape(state, level, ticks, pos, directionToNeighbour, neighbourPos,
                neighbourState, random);
    }

    @Override
    protected boolean canSurvive(BlockState state, LevelReader level, BlockPos pos) {
        BlockState above = level.getBlockState(pos.above());
        return !above.isSolid() || shouldMaintain(level, pos);
    }

    /**
     * Placing tilled soil where it could not survive gives plain moss instead, which is what
     * vanilla does with dirt. Without this, a farmland block item placed under an overhang would
     * flicker into existence and revert on its first tick.
     */
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return !this.defaultBlockState().canSurvive(context.getLevel(), context.getClickedPos())
                ? ModTerrainBlocks.RESONANCE_MOSS.get().defaultBlockState()
                : super.getStateForPlacement(context);
    }

    @Override
    protected boolean useShapeForLightOcclusion(BlockState state) {
        return true;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPE;
    }

    @Override
    protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if (!state.canSurvive(level, pos)) {
            turnToMoss(null, state, level, pos);
        }
    }

    @Override
    protected void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        int moisture = state.getValue(MOISTURE);
        if (!isNearWater(level, pos)) {
            if (moisture > 0) {
                level.setBlock(pos, state.setValue(MOISTURE, moisture - 1), 2);
            } else if (!shouldMaintain(level, pos)) {
                turnToMoss(null, state, level, pos);
            }
        } else if (moisture < MAX_MOISTURE) {
            level.setBlock(pos, state.setValue(MOISTURE, MAX_MOISTURE), 2);
        }
    }

    /**
     * Damp soil grows crops three times as fast. Vanilla expresses this through
     * {@code Block#isFertile}, whose default implementation tests for {@code FarmlandBlock} - which
     * this block is not, on purpose - so without this override a hydrated void field would grow at
     * exactly the same rate as a parched one and the moisture value would be decorative.
     */
    @Override
    public boolean isFertile(BlockState state, BlockGetter level, BlockPos pos) {
        return state.getValue(MOISTURE) > 0;
    }

    public static void turnToMoss(@Nullable Entity sourceEntity, BlockState state, Level level, BlockPos pos) {
        BlockState newState = pushEntitiesUp(state,
                ModTerrainBlocks.RESONANCE_MOSS.get().defaultBlockState(), level, pos);
        level.setBlockAndUpdate(pos, newState);
        level.gameEvent(GameEvent.BLOCK_CHANGE, pos, GameEvent.Context.of(sourceEntity, newState));
    }

    /** Soil under a living plant does not dry out, however far the water is. */
    private static boolean shouldMaintain(BlockGetter level, BlockPos pos) {
        BlockState plant = level.getBlockState(pos.above());
        BlockState self = level.getBlockState(pos);
        if (plant.getBlock() instanceof IPlantable plantable
                && self.canSustainPlant(level, pos, Direction.UP, plantable)) {
            return true;
        }
        return plant.is(BlockTags.MAINTAINS_FARMLAND);
    }

    /**
     * Any fluid that says it can hydrate, within vanilla's 9x2x9 box.
     *
     * <p>{@code canBeHydrated} hands the question to the FLUID rather than answering it here, so
     * hushwater waters a field because its fluid type sets {@code canHydrate(true)}, and ordinary
     * water still does too. A hard-coded test for our own fluid would have quietly broken the
     * second case.
     */
    private static boolean isNearWater(LevelReader level, BlockPos pos) {
        BlockState state = level.getBlockState(pos);
        for (BlockPos probe : BlockPos.betweenClosed(
                pos.offset(-WATER_RANGE, 0, -WATER_RANGE),
                pos.offset(WATER_RANGE, 1, WATER_RANGE))) {
            FluidState fluid = level.getFluidState(probe);
            // The emptiness test is NOT redundant, and leaving it out is what
            // made a field in the middle of a dry plain sit at moisture 7 for
            // ever and never revert to moss. canBeHydrated hands the question
            // to the fluid, and asking the EMPTY fluid whether it hydrates
            // answers yes in this build - so every one of the 162 probe
            // positions reported water and no void farmland ever dried out.
            // Vanilla's FarmBlock omits this check; this block cannot.
            if (!fluid.isEmpty() && state.canBeHydrated(level, pos, fluid, probe)) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(MOISTURE);
    }

    @Override
    protected boolean isPathfindable(BlockState state, PathComputationType type) {
        return false;
    }

    /** True for the block a hoe should turn into this one. Used by {@link ResonanceMossBlock}. */
    public static BlockState tilled() {
        return ModCrops.VOID_FARMLAND.get().defaultBlockState();
    }
}

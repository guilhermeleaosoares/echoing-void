package com.echoingvoid.block;

import com.echoingvoid.registry.ModBlocks;
import com.echoingvoid.registry.ModNewEntities;
import com.mojang.serialization.MapCodec;
import net.minecraft.advancements.triggers.CriteriaTriggers;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.pattern.BlockInWorld;
import net.minecraft.world.level.block.state.pattern.BlockPattern;
import net.minecraft.world.level.block.state.pattern.BlockPatternBuilder;
import net.minecraft.world.level.block.state.predicate.BlockStatePredicate;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import org.jspecify.annotations.Nullable;

/**
 * PLAYER: "the outpost could have a village iron golem equivalent creature that spawns naturally
 * in inhabited outposts, or can be naturally built with a carved pumpkin head and body structure
 * different but similar to that of an iron golem."
 *
 * <p>Mirrors {@link net.minecraft.world.level.block.CarvedPumpkinBlock} exactly - a
 * {@link BlockPattern} checked in {@link #onPlace} the instant the mask goes down - with a
 * deliberately different body shape rather than reusing the golem's own T-shaped cross:
 *
 * <pre>
 *   ~^~   mask (this block, any facing)
 *   ~#~   neck
 *   ###   torso
 *   #~#   two separate legs, a gap of air between them
 * </pre>
 *
 * where {@code #} is {@link net.minecraft.world.level.block.Block Block of Null-Iron} and
 * {@code ~} must be air. Iron golems fuse into one wide-armed block at the middle row; this
 * guardian's arms hang from the shoulders instead (see {@code build_tuners_protector} in
 * {@code tools/gen_new_creature_geo.py}), so the body it is built from splits at the legs
 * instead of spreading at the arms - different silhouette, same ritual.
 */
public class TunersMaskBlock extends HorizontalDirectionalBlock {
    public static final MapCodec<TunersMaskBlock> CODEC = simpleCodec(TunersMaskBlock::new);
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;

    private @Nullable BlockPattern protectorBase;
    private @Nullable BlockPattern protectorFull;

    public TunersMaskBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH));
    }

    @Override
    public MapCodec<? extends TunersMaskBlock> codec() {
        return CODEC;
    }

    @Override
    protected void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston) {
        if (!oldState.is(state.getBlock())) {
            this.trySpawnProtector(level, pos);
        }
    }

    /** Whether the body alone (no mask yet) is already in place under {@code topPos}. */
    public boolean canSpawnProtector(LevelReader level, BlockPos topPos) {
        return this.getOrCreateProtectorBase().find(level, topPos) != null;
    }

    private void trySpawnProtector(Level level, BlockPos topPos) {
        BlockPattern.BlockPatternMatch match = this.getOrCreateProtectorFull().find(level, topPos);
        if (match == null) {
            return;
        }
        Entity protector = ModNewEntities.TUNERS_PROTECTOR.get().create(level, EntitySpawnReason.TRIGGERED);
        if (protector == null) {
            return;
        }
        spawnProtectorInWorld(level, match, protector, match.getBlock(1, 3, 0).getPos());
    }

    private static void spawnProtectorInWorld(Level level, BlockPattern.BlockPatternMatch match, Entity protector,
            BlockPos spawnPos) {
        clearPatternBlocks(level, match);
        protector.snapTo(spawnPos.getX() + 0.5, spawnPos.getY() + 0.05, spawnPos.getZ() + 0.5, 0.0F, 0.0F);
        level.addFreshEntity(protector);

        for (ServerPlayer player : level.getEntitiesOfClass(ServerPlayer.class, protector.getBoundingBox().inflate(5.0))) {
            CriteriaTriggers.SUMMONED_ENTITY.trigger(player, protector);
        }

        updatePatternBlocks(level, match);
    }

    private static void clearPatternBlocks(Level level, BlockPattern.BlockPatternMatch match) {
        for (int x = 0; x < match.getWidth(); x++) {
            for (int y = 0; y < match.getHeight(); y++) {
                BlockInWorld block = match.getBlock(x, y, 0);
                level.setBlock(block.getPos(), Blocks.AIR.defaultBlockState(), 2);
                level.levelEvent(2001, block.getPos(), Block.getId(block.getState()));
            }
        }
    }

    private static void updatePatternBlocks(Level level, BlockPattern.BlockPatternMatch match) {
        for (int x = 0; x < match.getWidth(); x++) {
            for (int y = 0; y < match.getHeight(); y++) {
                BlockInWorld block = match.getBlock(x, y, 0);
                level.updateNeighborsAt(block.getPos(), Blocks.AIR);
            }
        }
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite());
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING);
    }

    private BlockPattern getOrCreateProtectorBase() {
        if (this.protectorBase == null) {
            this.protectorBase = BlockPatternBuilder.start()
                    .aisle("~#~", "###", "#~#")
                    .where('#', BlockInWorld.hasState(BlockStatePredicate.forBlock(ModBlocks.NULL_IRON_BLOCK.get())))
                    .where('~', BlockInWorld.hasState(BlockBehaviour.BlockStateBase::isAir))
                    .build();
        }
        return this.protectorBase;
    }

    private BlockPattern getOrCreateProtectorFull() {
        if (this.protectorFull == null) {
            this.protectorFull = BlockPatternBuilder.start()
                    .aisle("~^~", "~#~", "###", "#~#")
                    .where('^', BlockInWorld.hasState(state -> state.getBlock() instanceof TunersMaskBlock))
                    .where('#', BlockInWorld.hasState(BlockStatePredicate.forBlock(ModBlocks.NULL_IRON_BLOCK.get())))
                    .where('~', BlockInWorld.hasState(BlockBehaviour.BlockStateBase::isAir))
                    .build();
        }
        return this.protectorFull;
    }
}

package com.echoingvoid.block;

import com.echoingvoid.block.entity.FrequencySiphonBlockEntity;
import com.echoingvoid.registry.ModBlockEntities;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import org.jspecify.annotations.Nullable;

/**
 * The Frequency Siphon block - a comparator source driven by what the world sounds like.
 *
 * <p>All of the listening lives in {@link FrequencySiphonBlockEntity}; this class is the wiring.
 * Note that the ticker is handed out for the server only: the vibration state machine and the decay
 * ramp are both authoritative server state, and running either client-side would desynchronise the
 * redstone reading for no benefit.
 *
 * <p>Output is analogue rather than a direct signal, so it is read with a comparator - one siphon
 * feeding a comparator gives a 1..15 reading of the loudest thing that happened nearby in the last
 * two seconds.
 */
public class FrequencySiphonBlock extends BaseEntityBlock {
    public static final MapCodec<FrequencySiphonBlock> CODEC = simpleCodec(FrequencySiphonBlock::new);

    public FrequencySiphonBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<? extends BaseEntityBlock> codec() {
        return CODEC;
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos worldPosition, BlockState blockState) {
        return new FrequencySiphonBlockEntity(worldPosition, blockState);
    }

    @Override
    public <T extends BlockEntity> @Nullable BlockEntityTicker<T> getTicker(Level level, BlockState blockState, BlockEntityType<T> type) {
        if (level.isClientSide()) {
            return null;
        }

        return createTickerHelper(
            type,
            ModBlockEntities.FREQUENCY_SIPHON.get(),
            (tickLevel, pos, state, siphon) -> FrequencySiphonBlockEntity.serverTick(tickLevel, pos, state, siphon)
        );
    }

    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos, Direction direction) {
        return level.getBlockEntity(pos) instanceof FrequencySiphonBlockEntity siphon ? siphon.getRedstoneSignal() : 0;
    }
}

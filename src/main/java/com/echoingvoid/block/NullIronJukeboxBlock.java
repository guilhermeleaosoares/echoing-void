package com.echoingvoid.block;

import com.echoingvoid.block.entity.NullIronJukeboxBlockEntity;
import com.echoingvoid.registry.ModEffects;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.stats.Stats;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.TypedEntityData;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.gameevent.GameEvent;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;

/**
 * A jukebox cast in null-iron, with a bismuth resonator ring on its lid.
 *
 * <p>The three Harmonic Tuning Discs had nowhere to be played. This is where. It behaves exactly
 * like the vanilla jukebox - right-click with a disc to start it, right-click empty-handed to eject
 * it, break it and the disc comes back - and it accepts any disc at all, not only ours, because a
 * player who has carried a jukebox this far should not have to keep a second one for their vanilla
 * records.
 *
 * <p>It is a separate block rather than a retexture because vanilla's insertion path
 * ({@code JukeboxPlayable#tryInsertIntoJukebox}) tests {@code state.is(Blocks.JUKEBOX)} and would
 * refuse anything else; the short copy of that logic in {@link #useItemOn} is the whole reason this
 * class exists.
 *
 * <p>Which track a disc plays is data, not code: the disc item carries a
 * {@code minecraft:jukebox_playable} component naming an entry in the {@code jukebox_song} registry,
 * and that entry names the sound event and the length. See
 * {@code data/echoing_void/jukebox_song/} for ours.
 */
public class NullIronJukeboxBlock extends BaseEntityBlock {
    public static final MapCodec<NullIronJukeboxBlock> CODEC = simpleCodec(NullIronJukeboxBlock::new);

    /** Whether a disc is loaded. Drives the ticker and the redstone signal, not the model. */
    public static final BooleanProperty HAS_RECORD = BlockStateProperties.HAS_RECORD;

    public NullIronJukeboxBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HAS_RECORD, false));
    }

    @Override
    protected MapCodec<? extends BaseEntityBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<net.minecraft.world.level.block.Block, BlockState> builder) {
        builder.add(HAS_RECORD);
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos worldPosition, BlockState blockState) {
        return new NullIronJukeboxBlockEntity(worldPosition, blockState);
    }

    /** A jukebox picked up with its disc still inside keeps it; restore the state flag to match. */
    @Override
    public void setPlacedBy(Level level, BlockPos pos, BlockState state, @Nullable LivingEntity by, ItemStack itemStack) {
        super.setPlacedBy(level, pos, state, by, itemStack);
        TypedEntityData<BlockEntityType<?>> data = itemStack.get(DataComponents.BLOCK_ENTITY_DATA);
        if (data != null && data.contains("RecordItem")) {
            level.setBlock(pos, state.setValue(HAS_RECORD, true), 2);
        }
    }

    // ---------------------------------------------------------- interaction

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        if (state.getValue(HAS_RECORD) && level.getBlockEntity(pos) instanceof NullIronJukeboxBlockEntity jukebox) {
            jukebox.popOutTheItem();
            return InteractionResult.SUCCESS;
        }

        return InteractionResult.PASS;
    }

    @Override
    protected InteractionResult useItemOn(
        ItemStack itemStack,
        BlockState state,
        Level level,
        BlockPos pos,
        Player player,
        InteractionHand hand,
        BlockHitResult hitResult
    ) {
        if (state.getValue(HAS_RECORD)) {
            // Full: fall through to the empty-hand path above, which ejects what is already in.
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        // The component is what makes an item a disc; the item class is irrelevant, so this accepts
        // any mod's disc as well as ours and vanilla's.
        if (!itemStack.has(DataComponents.JUKEBOX_PLAYABLE)) {
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        if (!level.isClientSide()) {
            ItemStack inserted = itemStack.consumeAndReturn(1, player);
            if (level.getBlockEntity(pos) instanceof NullIronJukeboxBlockEntity jukebox) {
                jukebox.setTheItem(inserted);
                level.gameEvent(GameEvent.BLOCK_CHANGE, pos, GameEvent.Context.of(player, state));
            }

            player.awardStat(Stats.PLAY_RECORD);
        }

        return InteractionResult.SUCCESS;
    }

    @Override
    protected void affectNeighborsAfterRemoval(BlockState state, ServerLevel level, BlockPos pos, boolean movedByPiston) {
        Containers.updateNeighboursAfterDestroy(state, level, pos);
    }

    // ------------------------------------------------------------- redstone

    @Override
    public boolean isSignalSource(BlockState state) {
        return true;
    }

    /** Full strength while a track is running, nothing once it ends - the same as vanilla's. */
    @Override
    protected int ownSignal(BlockState state, BlockGetter level, BlockPos pos) {
        return level.getBlockEntity(pos) instanceof NullIronJukeboxBlockEntity jukebox
                && jukebox.getSongPlayer().isPlaying() ? 15 : 0;
    }

    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos, Direction direction) {
        return level.getBlockEntity(pos) instanceof NullIronJukeboxBlockEntity jukebox ? jukebox.getComparatorOutput() : 0;
    }

    // --------------------------------------------------------------- ticking

    /**
     * Only ticks while a disc is loaded. An empty jukebox has nothing to count, so it costs the
     * server nothing to have a room full of them.
     */
    @Override
    public <T extends BlockEntity> @Nullable BlockEntityTicker<T> getTicker(Level level, BlockState blockState, BlockEntityType<T> type) {
        return blockState.getValue(HAS_RECORD)
                ? createTickerHelper(type, ModEffects.NULL_IRON_JUKEBOX_ENTITY.get(), NullIronJukeboxBlockEntity::tick)
                : null;
    }
}

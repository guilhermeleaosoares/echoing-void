package com.echoingvoid.block.entity;

import com.echoingvoid.block.NullIronJukeboxBlock;
import com.echoingvoid.registry.ModEffects;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.Container;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.JukeboxSong;
import net.minecraft.world.item.JukeboxSongPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gameevent.GameEvent;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.ticks.ContainerSingleItem;

import java.util.Optional;

/**
 * The single disc slot inside a Null-Iron Jukebox, and the player that runs the track.
 *
 * <p>This is a parallel of {@code JukeboxBlockEntity} rather than a subclass of it. Vanilla's block
 * entity hard-codes {@code BlockEntityTypes.JUKEBOX} in its constructor, and a block entity whose
 * type does not list the block it is sitting on is dropped on the next chunk load - so a jukebox in
 * a different block needs its own type, and therefore its own class.
 *
 * <p>The playback itself is vanilla's: {@link JukeboxSongPlayer} broadcasts level events 1010 and
 * 1011, which every client already listens for and answers by starting or stopping the track named
 * in the {@code jukebox_song} registry. Nothing in that path asks what block is at the position, so
 * our cabinet plays discs exactly the way the vanilla one does - including stopping the previous
 * track, the note particles, and the comparator reading.
 */
public class NullIronJukeboxBlockEntity extends BlockEntity implements ContainerSingleItem.BlockContainerSingleItem {
    /** Same tag names vanilla uses, so a jukebox converted between the two keeps its disc. */
    private static final String KEY_ITEM = "RecordItem";
    private static final String KEY_TICKS = "ticks_since_song_started";

    private ItemStack item = ItemStack.EMPTY;
    private final JukeboxSongPlayer songPlayer = new JukeboxSongPlayer(this::onSongChanged, this.getBlockPos());

    public NullIronJukeboxBlockEntity(BlockPos pos, BlockState state) {
        super(ModEffects.NULL_IRON_JUKEBOX_ENTITY.get(), pos, state);
    }

    public JukeboxSongPlayer getSongPlayer() {
        return this.songPlayer;
    }

    /** Ticked only while the block state says a disc is in - see the block's ticker. */
    public static void tick(Level level, BlockPos pos, BlockState state, NullIronJukeboxBlockEntity jukebox) {
        jukebox.songPlayer.tick(level, state);
    }

    /** Comparator output is a property of the song, not of the slot being occupied. */
    public int getComparatorOutput() {
        return JukeboxSong.fromStack(this.item).map(Holder::value).map(JukeboxSong::comparatorOutput).orElse(0);
    }

    private void onSongChanged() {
        this.level.updateNeighborsAt(this.getBlockPos(), this.getBlockState().getBlock());
        this.setChanged();
    }

    /** Spits the disc out onto the top of the cabinet and stops the track. */
    public void popOutTheItem() {
        if (this.level == null || this.level.isClientSide()) {
            return;
        }

        ItemStack held = this.getTheItem();
        if (held.isEmpty()) {
            return;
        }

        this.removeTheItem();
        Vec3 spawn = Vec3.atLowerCornerWithOffset(this.getBlockPos(), 0.5, 1.01, 0.5)
                .offsetRandomXZ(this.level.getRandom(), 0.7F);
        ItemEntity entity = new ItemEntity(this.level, spawn.x(), spawn.y(), spawn.z(), held.copy());
        entity.setDefaultPickUpDelay();
        this.level.addFreshEntity(entity);
        this.onSongChanged();
    }

    // ------------------------------------------------------------- container

    @Override
    public ItemStack getTheItem() {
        return this.item;
    }

    @Override
    public ItemStack splitTheItem(int count) {
        ItemStack taken = this.item;
        this.setTheItem(ItemStack.EMPTY);
        return taken;
    }

    @Override
    public void setTheItem(ItemStack itemStack) {
        this.item = itemStack;
        boolean inserted = !this.item.isEmpty();
        Optional<Holder<JukeboxSong>> song = JukeboxSong.fromStack(this.item);
        this.notifyItemChanged(inserted);
        if (inserted && song.isPresent()) {
            this.songPlayer.play(this.level, song.get());
        } else {
            this.songPlayer.stop(this.level, this.getBlockState());
        }
    }

    @Override
    public int getMaxStackSize() {
        return 1;
    }

    @Override
    public BlockEntity getContainerBlockEntity() {
        return this;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack itemStack) {
        return itemStack.has(DataComponents.JUKEBOX_PLAYABLE) && this.getItem(slot).isEmpty();
    }

    @Override
    public boolean canTakeItem(Container into, int slot, ItemStack itemStack) {
        return into.hasAnyMatching(ItemStack::isEmpty);
    }

    @Override
    public void preRemoveSideEffects(BlockPos pos, BlockState state) {
        this.popOutTheItem();
    }

    @Override
    public void setRemoved() {
        super.setRemoved();
        // Tell everyone in earshot the music has gone with the block, or a broken jukebox keeps
        // playing on the client until they reload the chunk.
        this.level.gameEvent(GameEvent.JUKEBOX_STOP_PLAY, this.getBlockPos(), GameEvent.Context.of(this.getBlockState()));
        this.level.levelEvent(1011, this.getBlockPos(), 0);
    }

    private void notifyItemChanged(boolean hasDisc) {
        if (this.level != null && this.level.getBlockState(this.getBlockPos()) == this.getBlockState()) {
            this.level.setBlock(this.getBlockPos(), this.getBlockState().setValue(NullIronJukeboxBlock.HAS_RECORD, hasDisc), 2);
            this.level.gameEvent(GameEvent.BLOCK_CHANGE, this.getBlockPos(), GameEvent.Context.of(this.getBlockState()));
        }
    }

    // ----------------------------------------------------------- persistence

    @Override
    protected void loadAdditional(ValueInput input) {
        super.loadAdditional(input);
        ItemStack loaded = input.read(KEY_ITEM, ItemStack.CODEC).orElse(ItemStack.EMPTY);
        if (!this.item.isEmpty() && !ItemStack.isSameItemSameComponents(loaded, this.item)) {
            this.songPlayer.stop(this.level, this.getBlockState());
        }

        this.item = loaded;
        // Resuming mid-track rather than from the beginning is what stops every jukebox in a chunk
        // restarting in unison when a player walks back into range.
        input.getLong(KEY_TICKS).ifPresent(elapsed ->
                JukeboxSong.fromStack(this.item).ifPresent(song -> this.songPlayer.setSongWithoutPlaying(song, elapsed)));
    }

    @Override
    protected void saveAdditional(ValueOutput output) {
        super.saveAdditional(output);
        if (!this.getTheItem().isEmpty()) {
            output.store(KEY_ITEM, ItemStack.CODEC, this.getTheItem());
        }

        if (this.songPlayer.getSong() != null) {
            output.putLong(KEY_TICKS, this.songPlayer.getTicksSinceSongStarted());
        }
    }
}

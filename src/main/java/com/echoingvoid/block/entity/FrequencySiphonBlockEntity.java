package com.echoingvoid.block.entity;

import com.echoingvoid.registry.ModBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.NoteBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gameevent.BlockPositionSource;
import net.minecraft.world.level.gameevent.GameEvent;
import net.minecraft.world.level.gameevent.GameEventListener;
import net.minecraft.world.level.gameevent.PositionSource;
import net.minecraft.world.level.gameevent.vibrations.VibrationSystem;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import org.jspecify.annotations.Nullable;

/**
 * The Frequency Siphon - a vibration tap that converts what it hears into analogue redstone.
 *
 * <p>This is the mod's answer to "no global entity polling". The siphon never looks for anything.
 * It implements {@link GameEventListener.Provider}, which is all the chunk needs to enrol it in the
 * game-event dispatcher, and the {@link VibrationSystem} machinery delivers a vibration to
 * {@code onReceiveVibration} only when one actually occurs inside the listener radius. There is no
 * entity scan, no {@code getEntitiesOfClass}, and no per-tick search of any kind.
 *
 * <p>Output strength comes from the vibration's <em>frequency</em> - the vanilla 1..15 table that
 * scores a footstep as 1 and a death as 15 - so a comparator on the siphon reads what kind of event
 * happened, not merely that something did. The reading then decays linearly back to zero over
 * {@link #DECAY_TICKS} ticks.
 *
 * <p>The tick loop allocates nothing: the decay is integer arithmetic on three fields, neighbours
 * are only notified on the ticks where the output actually changes, and the resonance relay reuses
 * the single {@link #scratch} mutable position instead of building a {@code BlockPos} per face.
 */
public class FrequencySiphonBlockEntity extends BlockEntity
        implements VibrationSystem, GameEventListener.Provider<VibrationSystem.Listener> {

    /** Same reach as a sculk sensor - familiar to anyone who has wired one up. */
    public static final int LISTENER_RADIUS = 8;

    /** Two seconds from a full 15 back down to silence. */
    public static final int DECAY_TICKS = 40;

    private static final String KEY_PEAK = "peak_signal";
    private static final String KEY_DECAY = "decay_ticks";
    private static final String KEY_LISTENER = "listener";

    private final VibrationSystem.User vibrationUser;
    private final VibrationSystem.Listener vibrationListener;
    private VibrationSystem.Data vibrationData;

    /**
     * Reused for every neighbour lookup this block entity performs. Block entities tick on the
     * server thread only, so a single instance per siphon is safe and keeps the tick allocation-free.
     */
    private final BlockPos.MutableBlockPos scratch = new BlockPos.MutableBlockPos();

    /** Strength of the vibration that started the current decay, 1..15. Zero when idle. */
    private int peakSignal;

    /** Ticks left in the current decay ramp. */
    private int decayTicks;

    /** Last value handed to the comparators, so neighbours are only poked when it moves. */
    private int broadcastSignal;

    public FrequencySiphonBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.FREQUENCY_SIPHON.get(), pos, state);
        this.vibrationUser = new SiphonVibrationUser(this.getBlockPos());
        this.vibrationData = new VibrationSystem.Data();
        this.vibrationListener = new VibrationSystem.Listener(this);
    }

    // ------------------------------------------------------------------ ticking

    /**
     * Server-side ticker. Pumps the vibration state machine (travel time, particle, delivery) and
     * then advances the decay ramp.
     */
    public static void serverTick(Level level, BlockPos pos, BlockState state, FrequencySiphonBlockEntity siphon) {
        VibrationSystem.Ticker.tick(level, siphon.vibrationData, siphon.vibrationUser);
        siphon.decayTick(level, pos, state);
    }

    private void decayTick(Level level, BlockPos pos, BlockState state) {
        if (this.decayTicks <= 0) {
            return;
        }

        this.decayTicks--;
        int current = this.getRedstoneSignal();
        if (current == this.broadcastSignal) {
            return;
        }

        this.broadcastSignal = current;
        level.updateNeighbourForOutputSignal(pos, state.getBlock());
        if (current == 0) {
            this.peakSignal = 0;
            this.setChanged();
        }
    }

    /** Current comparator output, 0..15. */
    public int getRedstoneSignal() {
        if (this.decayTicks <= 0 || this.peakSignal <= 0) {
            return 0;
        }

        return Mth.ceil(this.peakSignal * this.decayTicks / (float) DECAY_TICKS);
    }

    // ------------------------------------------------------------- vibrations

    @Override
    public VibrationSystem.Data getVibrationData() {
        return this.vibrationData;
    }

    @Override
    public VibrationSystem.User getVibrationUser() {
        return this.vibrationUser;
    }

    @Override
    public VibrationSystem.Listener getListener() {
        return this.vibrationListener;
    }

    /**
     * Passes the received frequency on to any resonators bolted to the siphon's faces, the way a
     * sculk sensor does, and chimes at the matching pitch. Uses {@link #scratch} rather than
     * {@code pos.relative(direction)} so the six-face sweep costs no allocations.
     */
    private void relayResonance(ServerLevel level, int frequency, @Nullable Entity sourceEntity) {
        for (Direction direction : Direction.values()) {
            this.scratch.setWithOffset(this.worldPosition, direction);
            BlockState neighbour = level.getBlockState(this.scratch);
            if (!neighbour.is(BlockTags.VIBRATION_RESONATORS)) {
                continue;
            }

            ResourceKey<GameEvent> resonance = VibrationSystem.getResonanceEventByFrequency(frequency);
            level.gameEvent(resonance, this.scratch, GameEvent.Context.of(sourceEntity, neighbour));
            level.playSound(
                null,
                this.scratch,
                SoundEvents.AMETHYST_BLOCK_RESONATE,
                SoundSource.BLOCKS,
                1.0F,
                NoteBlock.getPitchFromNote(frequency)
            );
        }
    }

    // ------------------------------------------------------------ persistence

    @Override
    protected void loadAdditional(ValueInput input) {
        super.loadAdditional(input);
        this.peakSignal = Mth.clamp(input.getIntOr(KEY_PEAK, 0), 0, 15);
        this.decayTicks = Mth.clamp(input.getIntOr(KEY_DECAY, 0), 0, DECAY_TICKS);
        this.broadcastSignal = this.getRedstoneSignal();
        this.vibrationData = input.read(KEY_LISTENER, VibrationSystem.Data.CODEC).orElseGet(VibrationSystem.Data::new);
    }

    @Override
    protected void saveAdditional(ValueOutput output) {
        super.saveAdditional(output);
        output.putInt(KEY_PEAK, this.peakSignal);
        output.putInt(KEY_DECAY, this.decayTicks);
        output.store(KEY_LISTENER, VibrationSystem.Data.CODEC, this.vibrationData);
    }

    /**
     * The siphon's half of the vibration contract. Only the four abstract members are implemented;
     * {@code getListenableEvents} already defaults to the whole {@code VIBRATIONS} tag.
     */
    private class SiphonVibrationUser implements VibrationSystem.User {
        private final BlockPos blockPos;
        private final PositionSource positionSource;

        SiphonVibrationUser(BlockPos blockPos) {
            this.blockPos = blockPos;
            this.positionSource = new BlockPositionSource(blockPos);
        }

        @Override
        public int getListenerRadius() {
            return LISTENER_RADIUS;
        }

        @Override
        public PositionSource getPositionSource() {
            return this.positionSource;
        }

        @Override
        public boolean canReceiveVibration(ServerLevel level, BlockPos pos, Holder<GameEvent> event, GameEvent.@Nullable Context context) {
            // Ignore the siphon being placed or broken at its own position - it would hear itself.
            if (pos.equals(this.blockPos) && (event.is(GameEvent.BLOCK_DESTROY) || event.is(GameEvent.BLOCK_PLACE))) {
                return false;
            }

            return VibrationSystem.getGameEventFrequency(event) != 0;
        }

        @Override
        public void onReceiveVibration(
            ServerLevel level,
            BlockPos pos,
            Holder<GameEvent> event,
            @Nullable Entity sourceEntity,
            @Nullable Entity projectileOwner,
            float receivingDistance
        ) {
            int frequency = VibrationSystem.getGameEventFrequency(event);
            if (frequency == 0) {
                return;
            }

            FrequencySiphonBlockEntity siphon = FrequencySiphonBlockEntity.this;
            siphon.peakSignal = Mth.clamp(frequency, 1, 15);
            siphon.decayTicks = DECAY_TICKS;
            siphon.broadcastSignal = siphon.peakSignal;
            level.updateNeighbourForOutputSignal(this.blockPos, siphon.getBlockState().getBlock());
            siphon.relayResonance(level, frequency, sourceEntity);
            siphon.setChanged();
        }

        @Override
        public boolean canTriggerAvoidVibration() {
            return true;
        }

        @Override
        public boolean requiresAdjacentChunksToBeTicking() {
            return true;
        }

        @Override
        public void onDataChanged() {
            FrequencySiphonBlockEntity.this.setChanged();
        }
    }
}

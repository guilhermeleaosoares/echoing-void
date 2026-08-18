package com.echoingvoid.block.entity;

import com.echoingvoid.registry.ModBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.NonNullList;
import net.minecraft.util.Mth;
import net.minecraft.world.ContainerHelper;
import net.minecraft.world.Containers;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.NoteBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;

/**
 * State for an Acoustic Lock Box - the Sound Vault safe.
 *
 * <p>The box has four tines, one per horizontal face, each with its own pitch. Its combination is a
 * four-note run over those tines, derived from the block's own coordinates rather than rolled at
 * random: the same box in the same place always has the same combination, across reloads and across
 * a fresh world generated from the same seed. Nothing about the combination is written to disk, so
 * it cannot drift, and a player cannot read it out of the chunk file either.
 *
 * <p>What <em>is</em> persisted is how far through the combination the player has got and whether
 * the box has already been opened, alongside the contents waiting inside it.
 */
public class AcousticLockBoxBlockEntity extends BlockEntity {
    /** Notes in the combination. */
    public static final int SEQUENCE_LENGTH = 4;

    /** Slots in the vault. */
    public static final int CONTAINER_SIZE = 9;

    /**
     * The pitch of each tine, as two-octave note numbers for {@code NoteBlock#getPitchFromNote}.
     * Spread wide enough that two tines are never mistaken for each other by ear.
     */
    private static final int[] TINE_NOTES = {0, 5, 9, 14};

    private static final String KEY_PROGRESS = "progress";
    private static final String KEY_UNLOCKED = "unlocked";

    private final NonNullList<ItemStack> contents = NonNullList.withSize(CONTAINER_SIZE, ItemStack.EMPTY);

    /** Derived from the position at construction; never saved, never re-rolled. */
    private final int[] combination;

    private int progress;
    private boolean unlocked;

    public AcousticLockBoxBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.ACOUSTIC_LOCK_BOX.get(), pos, state);
        this.combination = derive(pos);
    }

    // -------------------------------------------------------------- the lock

    public boolean isUnlocked() {
        return this.unlocked;
    }

    /** How many notes of the combination are currently held, 0..{@link #SEQUENCE_LENGTH}. */
    public int getProgress() {
        return this.progress;
    }

    /** Which tine a face belongs to, 0..3, or -1 for the top and bottom faces. */
    public static int tineFor(Direction face) {
        return face.getAxis().isHorizontal() ? face.get2DDataValue() : -1;
    }

    /** The pitch a tine sounds when struck. */
    public static float pitchFor(int tine) {
        return NoteBlock.getPitchFromNote(TINE_NOTES[tine]);
    }

    /**
     * Registers a strike on {@code tine}.
     *
     * @return {@code true} if that note continued the combination, {@code false} if it was wrong and
     *         the sequence has been reset to the beginning
     */
    public boolean strike(int tine) {
        if (this.unlocked) {
            return false;
        }

        // Defensive: a complete run should always have been opened, but a hand-edited chunk could
        // reload a box sitting on the last note.
        if (this.progress >= SEQUENCE_LENGTH) {
            this.progress = 0;
        }

        if (this.combination[this.progress] != tine) {
            this.progress = 0;
            this.setChanged();
            return false;
        }

        this.progress++;
        this.setChanged();
        return true;
    }

    /** True once {@link #strike} has taken the progress counter to the end of the combination. */
    public boolean isComplete() {
        return !this.unlocked && this.progress >= SEQUENCE_LENGTH;
    }

    /**
     * Opens the box: marks it unlocked and spills whatever it was holding. Safe to call twice; the
     * second call finds an empty box and does nothing.
     */
    public void open(Level level) {
        if (this.unlocked) {
            return;
        }

        this.unlocked = true;
        this.progress = SEQUENCE_LENGTH;
        Containers.dropContents(level, this.worldPosition, this.contents);
        this.contents.clear();
        this.setChanged();
    }

    // ------------------------------------------------------------- contents

    /** Used by structure generation to stock a vault before a player ever finds it. */
    public NonNullList<ItemStack> getContents() {
        return this.contents;
    }

    public void setItem(int slot, ItemStack itemStack) {
        this.contents.set(slot, itemStack);
        this.setChanged();
    }

    // ---------------------------------------------------------- combination

    /**
     * The four tines to strike, in order. Mixed from the block coordinates with the same hash
     * vanilla uses for positional randomness, so neighbouring boxes do not share a combination.
     */
    private static int[] derive(BlockPos pos) {
        long seed = Mth.getSeed(pos);
        int[] notes = new int[SEQUENCE_LENGTH];
        for (int i = 0; i < SEQUENCE_LENGTH; i++) {
            // Take two bits per note from well-separated parts of the hash.
            notes[i] = (int) (seed >>> (13 * i + 7)) & 3;
        }

        return notes;
    }

    // ----------------------------------------------------------- persistence

    @Override
    protected void loadAdditional(ValueInput input) {
        super.loadAdditional(input);
        this.progress = Mth.clamp(input.getIntOr(KEY_PROGRESS, 0), 0, SEQUENCE_LENGTH);
        this.unlocked = input.getBooleanOr(KEY_UNLOCKED, false);
        this.contents.clear();
        ContainerHelper.loadAllItems(input, this.contents);
    }

    @Override
    protected void saveAdditional(ValueOutput output) {
        super.saveAdditional(output);
        output.putInt(KEY_PROGRESS, this.progress);
        output.putBoolean(KEY_UNLOCKED, this.unlocked);
        ContainerHelper.saveAllItems(output, this.contents);
    }
}

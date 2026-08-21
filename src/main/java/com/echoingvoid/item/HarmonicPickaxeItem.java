package com.echoingvoid.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * The Harmonic Pickaxe - stone answers to rhythm rather than to force.
 *
 * <p>The pickaxe watches the gaps between the wielder's breaks. Mine five blocks at a steady
 * rhythm - any rhythm - and the plane facing the miner starts shattering along its acoustic
 * fault lines, and keeps shattering on every further block that holds the beat. Break
 * arrhythmically and it is an ordinary, if quick, pickaxe.
 *
 * <p>Everything mined with a pickaxe gives way - stone, ore, metal, whatever the plane catches -
 * so long as this pickaxe could have harvested it anyway. The tool cheats the block count, never
 * the tier gate, and every block it takes drops through the tool, so Silk Touch and Fortune reach
 * the whole plane rather than only the block struck by hand.
 *
 * <h2>Why this did not work, twice</h2>
 *
 * <p>PLAYER: "the pickaxes still seem to not be working", after an earlier round that only
 * fixed half of it. Two separate causes, and the second one is mine to own.
 *
 * <p><b>One: Creative never reached the hook.</b> The trigger used to live in {@code
 * Item#mineBlock}, and {@code ServerPlayerGameMode#destroyBlock} only calls that for a player
 * whose {@code preventsBlockDrops()} is false. A Creative player's is true, so the method
 * returns before {@code itemStack.mineBlock(...)} is ever reached - the single most likely way
 * anyone would first try a new tool. {@code ForgeHooks.onBlockBreakEvent}, a few lines earlier
 * in that same method, fires {@link net.minecraftforge.event.level.BlockEvent.BreakEvent}
 * unconditionally, survival or creative, so the trigger lives on that event now (wired in
 * {@code CombatEvents}) and {@code mineBlock} is not overridden here at all - keeping both
 * would have double-counted every survival break.
 *
 * <p><b>Two: the tempo was impossible to hit, and should never have been there.</b> The
 * player asked, in as many words, for the trigger to have "no absolute time clause" and to key
 * off five blocks at a consistent cadence within 33% variance. What was actually implemented
 * was {@code |interval - 10| <= 3} - a hard requirement to break a block every ten ticks,
 * give or take three. That is an absolute time clause, it is the exact thing that was ruled
 * out, and almost nothing a player naturally does lands in it: Creative insta-breaking runs
 * far faster than a ten-tick gap, and survival mining times vary with hardness and tool. So
 * even once the event fired, the window virtually never opened. I had previously marked this
 * item complete on the claim that no absolute-time clause remained, which was simply wrong.
 * The rule the player asked for is what is implemented above now.
 */
public class HarmonicPickaxeItem extends Item {

    /**
     * Blocks that must land on a consistent cadence before the plane starts shattering.
     *
     * <p>PLAYER, stating the rule: "make it without an absolute time clause, just say that if 5
     * blocks are mined at a similar time per block and similar cadance within 33% variance in the
     * cadance, the effect starts taking effect." Five blocks is four intervals: the first sets the
     * cadence and the next three have to match it.
     */
    private static final int BLOCKS_TO_ARM = 5;

    /** How far an interval may stray from the running cadence and still count, as a fraction. */
    private static final double CADENCE_VARIANCE = 0.33;

    /**
     * How much of each in-cadence interval folds back into the running reference.
     *
     * <p>Without this the cadence is pinned to whatever the very first interval happened to be,
     * and a rhythm that drifts even slightly - which every human one does - walks out of the
     * variance window and drops the phrase. Half-weighting lets the reference follow the player.
     */
    private static final double CADENCE_SMOOTHING = 0.5;

    /**
     * The one time-based bound left, and deliberately not a tempo.
     *
     * <p>The rule above has no required speed: any rhythm qualifies as long as it is *consistent*,
     * which is the whole point of the player's "without an absolute time clause". This constant
     * only ends a phrase that has plainly stopped - thirty seconds between blocks is not a rhythm
     * anyone is holding - so that a break now and a break next week cannot be read as a cadence.
     */
    private static final int PHRASE_TIMEOUT = 600;


    /**
     * Swing rhythm per player. Keyed by UUID and pruned when the player logs out - this is
     * never iterated, only looked up for the one player who just mined something.
     */
    private static final Map<UUID, Beat> RHYTHM = new HashMap<>();

    /** Reused cursor for the eight neighbours. The server breaks blocks on one thread. */
    private static final BlockPos.MutableBlockPos CURSOR = new BlockPos.MutableBlockPos();

    /** Guards against a shattered block feeding back into this hook. */
    private static boolean shattering;

    public HarmonicPickaxeItem(Item.Properties properties) {
        super(properties);
    }

    /**
     * Called from {@code CombatEvents} on {@link net.minecraftforge.event.level.BlockEvent.BreakEvent},
     * once per real block break, survival or creative alike - see the class javadoc for why
     * this is not {@code Item#mineBlock} any more.
     */
    public void onBlockBroken(ItemStack stack, ServerLevel level, BlockState state, BlockPos pos, Player player) {
        if (shattering) {
            return;
        }

        // Server game time rather than player.tickCount: monotonic, shared by every player, and
        // unaffected by anything that resets an entity's own counter.
        long now = level.getGameTime();
        Beat beat = RHYTHM.get(player.getUUID());
        if (beat == null) {
            beat = new Beat();
            RHYTHM.put(player.getUUID(), beat);
            beat.restart(now);
            return;
        }

        long interval = now - beat.lastBreak;
        beat.lastBreak = now;

        // Two blocks gone inside one tick is not a second beat - leave the phrase untouched
        // rather than letting a zero-length interval either reset it or define the cadence.
        if (interval <= 0) {
            return;
        }

        if (interval > PHRASE_TIMEOUT) {
            beat.restart(now);
            return;
        }

        // The first interval of a phrase sets the cadence. No tempo is required of it: whatever
        // speed the player is mining at becomes the speed they have to keep.
        if (beat.cadence <= 0.0) {
            beat.cadence = interval;
            beat.blocks = 2;
            return;
        }

        if (Math.abs(interval - beat.cadence) > beat.cadence * CADENCE_VARIANCE) {
            // Off the rhythm. This block is not a failure so much as the start of a new phrase -
            // it is the first block of whatever the player does next.
            beat.restart(now);
            return;
        }

        beat.cadence += (interval - beat.cadence) * CADENCE_SMOOTHING;
        beat.blocks++;

        // PLAYER: "as soon as it breaks the first 3x3, every new block it breaks that stays in
        // the same cadence breaks 3x3 again, so not block block 3x3 block 3x3 block 3x3, but
        // instead block block 3x3 3x3 3x3 3x3 etc". So the counter is NOT reset here: once the
        // phrase is long enough, it stays armed and every further in-cadence break shatters,
        // until the rhythm itself breaks and restart() takes it back to one.
        if (beat.blocks >= BLOCKS_TO_ARM) {
            shatter(level, player, stack, state, pos);
        }
    }

    /**
     * The fault-plane rectangle extends {@code widthLo..widthHi} (inclusive) along the plane's
     * horizontal axis and {@code heightLo..heightHi} along its vertical axis, centred on the
     * struck block. The base tool is a symmetric 3x3, {@code -1..1} on both. PLAYER, on the
     * Knell upgrade: "the area break of the knell pickaxe is amplified... 4x5, 5 wide 4 tall" -
     * see {@link KnellPickaxeItem}, which widens only the horizontal pair.
     *
     * <p>These two pairs only both have a real meaning when the fault plane is vertical - i.e.
     * the miner struck a wall. Striking a floor or ceiling makes the fault plane horizontal,
     * which has no vertical axis in it at all, so {@link #shatter} applies the width pair to
     * both plane axes in that case rather than leaving "height" undefined; a floor/ceiling
     * shatter is square at the wide dimension instead of a true rectangle.
     */
    protected int widthLo() {
        return -1;
    }

    protected int widthHi() {
        return 1;
    }

    protected int heightLo() {
        return -1;
    }

    protected int heightHi() {
        return 1;
    }

    /**
     * Breaks the blocks around {@code pos} in the plane the miner is facing. The struck block
     * itself is left to the vanilla break that called us.
     */
    private void shatter(ServerLevel level, Player player, ItemStack stack, BlockState struck, BlockPos pos) {
        if (struck.getDestroySpeed(level, pos) < 0.0F) {
            return;
        }

        // The fault plane is perpendicular to the face being mined, so it is spanned by the two
        // axes the look direction is weakest on.
        Direction face = Direction.getApproximateNearest(player.getLookAngle());
        int broken = 0;
        int wLo = widthLo();
        int wHi = widthHi();
        int hLo = heightLo();
        int hHi = heightHi();

        // Which offset pair drives `a` and which drives `b` depends on which way the miner is
        // facing - see the width/height javadoc above for why the Y case uses the width pair
        // twice instead of an undefined height.
        int aLo, aHi, bLo, bHi;
        switch (face.getAxis()) {
            case X -> { aLo = hLo; aHi = hHi; bLo = wLo; bHi = wHi; } // a=Y(height), b=Z(width)
            case Z -> { aLo = wLo; aHi = wHi; bLo = hLo; bHi = hHi; } // a=X(width), b=Y(height)
            default -> { aLo = wLo; aHi = wHi; bLo = wLo; bHi = wHi; } // Y: floor/ceiling
        }

        shattering = true;
        try {
            for (int a = aLo; a <= aHi; a++) {
                for (int b = bLo; b <= bHi; b++) {
                    if (a == 0 && b == 0) {
                        continue;
                    }
                    switch (face.getAxis()) {
                        case X -> CURSOR.setWithOffset(pos, 0, a, b);
                        case Y -> CURSOR.setWithOffset(pos, a, 0, b);
                        case Z -> CURSOR.setWithOffset(pos, a, b, 0);
                    }

                    BlockState neighbour = level.getBlockState(CURSOR);
                    if (neighbour.isAir()) {
                        continue;
                    }
                    // PLAYER: "if im using the harmonic pickaxe mining normal overworld stone,
                    // and there is a vein of diorite, it will do 3x3 for stone but leave the
                    // diorite intact even if its within the 3x3 area. this should be no more,
                    // the pickaxe effect should apply in all stone blocks, so all blocks that
                    // are mined with pickaxes (dirt and sand arent included for example)".
                    //
                    // The old gate was a HARDNESS SIMILARITY test against the struck block,
                    // which is exactly what left the diorite standing: diorite and stone have
                    // different destroy speeds, so a plane opened on stone excluded it. The
                    // class of block is what matters, not how closely its hardness matches, so
                    // the test is now simply "is this mined with a pickaxe" - which admits every
                    // stone, ore and metal block while still excluding dirt, sand and gravel.
                    if (!neighbour.is(BlockTags.MINEABLE_WITH_PICKAXE)) {
                        continue;
                    }
                    if (neighbour.getDestroySpeed(level, CURSOR) < 0.0F) {
                        continue;   // unbreakable, e.g. bedrock
                    }

                    // The tier gate stays: the tool cheats the block count, never the tier.
                    if (!stack.isCorrectToolForDrops(neighbour)) {
                        continue;
                    }

                    if (breakWithTool(level, player, stack, neighbour, CURSOR.immutable())) {
                        broken++;
                    }
                }
            }
        } finally {
            shattering = false;
        }

        if (broken > 0) {
            stack.hurtAndBreak(broken, player, EquipmentSlot.MAINHAND);
            level.playSound(null, pos, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.BLOCKS, 0.8F, 1.4F);
        }
    }

    /**
     * Breaks one shattered block as though the player had mined it with this pickaxe.
     *
     * <p>PLAYER: "silk touch makes sure that if i mine a 3x3 of solid stone, it doesnt drop the
     * block i actually mined as silk touch so it drops stone but all 8 others arent affected and
     * drop stone, this should not be the case, i mine a 3x3 of all stone, silk touch is applied
     * to all the 9 stone, so i get 9 stone instead of 1 stone and 8 cobblestone. fortune for
     * example, applies if an ore block is caught and mined wihtin the 3x3 area."
     *
     * <p>The old code called {@code level.destroyBlock(pos, true, player)}. That drops the
     * block's <em>default</em> loot: it knows who broke the block but not what they broke it
     * with, so the loot context carries no tool and every enchantment on the pickaxe is simply
     * absent. Silk Touch and Fortune are properties of the tool, so they applied to the one
     * block vanilla broke and to none of the ones we broke - which is precisely the split the
     * player describes.
     *
     * <p>This instead walks the same sequence {@code ServerPlayerGameMode#destroyBlock} does,
     * with {@code stack} threaded through: {@code playerWillDestroy}, remove, {@code destroy},
     * then {@code playerDestroy}, which calls {@code dropResources(..., tool)} and builds a loot
     * context that includes the tool. Every enchantment on the pickaxe therefore applies to
     * every block in the plane, exactly as it does to the one struck by hand.
     *
     * <p>{@code spawnAfterBreak} is called separately for experience because
     * {@code Block#playerDestroy} passes {@code dropXp = false} - Forge moved XP out of it and
     * into the game-mode patch, so a shatter that did not do this would silently eat the
     * experience from every ore it broke.
     */
    private static boolean breakWithTool(
            ServerLevel level, Player player, ItemStack stack, BlockState state, BlockPos pos) {
        BlockEntity blockEntity = state.hasBlockEntity() ? level.getBlockEntity(pos) : null;
        boolean canHarvest = state.canHarvestBlock(level, pos, player);

        state.getBlock().playerWillDestroy(level, pos, state, player);
        if (!level.removeBlock(pos, false)) {
            return false;
        }
        state.getBlock().destroy(level, pos, state);

        if (canHarvest) {
            // The copy matters: playerDestroy can consume or damage what it is handed, and this
            // stack is the pickaxe still in the player's hand.
            state.getBlock().playerDestroy(level, player, pos, state, blockEntity, stack.copy());
            state.spawnAfterBreak(level, pos, stack, true);
        }
        return true;
    }

    /** Drops a player's rhythm when they leave, so the map never outgrows the online roster. */
    public static void forget(UUID playerId) {
        RHYTHM.remove(playerId);
    }

    /** Mutable so the common path is a map lookup and two field writes, with no allocation. */
    private static final class Beat {
        /** Game time of the most recent break. */
        long lastBreak;

        /** The rhythm being held, in ticks, or 0 when the phrase has no cadence yet. */
        double cadence;

        /** Blocks in the current phrase, counting the one that started it. */
        int blocks;

        /** Begin a fresh phrase at {@code now}, with this break as its first block. */
        void restart(long now) {
            this.lastBreak = now;
            this.cadence = 0.0;
            this.blocks = 1;
        }
    }
}

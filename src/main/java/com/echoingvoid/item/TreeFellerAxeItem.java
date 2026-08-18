package com.echoingvoid.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.AxeItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ToolMaterial;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.Set;

/**
 * PLAYER: "the resonance axe chops down an entire tree by chopping down the lower log if its a
 * single trunk tree, or the lower 4 logs if its a large tree" - and for the Knell upgrade,
 * "the axe chopping down any tree by chopping just one log of it down."
 *
 * <p>Shared felling logic for both tiers. {@link #requiresBase()} is the one thing that
 * differs: the Harmonic axe only triggers when the block actually broken is a base log (nothing
 * of the same log type directly beneath it, or - for a 2x2 "large" trunk - it is one of the
 * four ground-level logs in that cluster); the Knell axe drops that requirement and fells from
 * any log in the tree, anywhere up the trunk.
 *
 * <p>Once triggered, the whole connected log cluster is found by a bounded flood fill (6-connected
 * through blocks in the {@code minecraft:logs} tag matching the struck block's log family) and
 * broken in one pass, each drop going through the normal loot table exactly as if chopped by hand -
 * this cheats the player's swings, never the drop table.
 */
public abstract class TreeFellerAxeItem extends AxeItem {

    /** Hard ceiling on one felling, so a log farm someone forgot to trim cannot spike a tick. */
    private static final int MAX_LOGS = 128;

    /** Guards against a felled log's own break feeding back into this hook. */
    private static boolean felling;

    public TreeFellerAxeItem(ToolMaterial material, float attackDamageBaseline, float attackSpeedBaseline,
                              Item.Properties properties) {
        super(material, attackDamageBaseline, attackSpeedBaseline, properties);
    }

    /** Harmonic requires the base log; Knell fells from anywhere in the tree. */
    protected abstract boolean requiresBase();

    @Override
    public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity owner) {
        boolean handled = super.mineBlock(stack, level, state, pos, owner);
        if (felling || !(level instanceof ServerLevel serverLevel) || !(owner instanceof Player player)) {
            return handled;
        }
        if (!state.is(BlockTags.LOGS)) {
            return handled;
        }
        if (requiresBase() && !isBaseLog(serverLevel, state, pos)) {
            return handled;
        }
        fell(serverLevel, player, stack, state, pos);
        return handled;
    }

    /**
     * True if nothing of the same log family sits directly under {@code pos} - a single-trunk
     * tree's own base - or if {@code pos} is one of the four ground logs of a 2x2 "large" trunk
     * (each of those four also has no log of the same family beneath it, so the same single check
     * covers both shapes without needing to special-case the cluster width).
     */
    private static boolean isBaseLog(ServerLevel level, BlockState state, BlockPos pos) {
        BlockState below = level.getBlockState(pos.below());
        return !sameLogFamily(state, below);
    }

    /** Same registry id: a family is exactly one log block plus its own stripped/bark forms are
     * NOT folded in here on purpose - stripping breaks the chain by design, not felling logic. */
    private static boolean sameLogFamily(BlockState a, BlockState b) {
        return BuiltInRegistries.BLOCK.getKey(a.getBlock()).equals(BuiltInRegistries.BLOCK.getKey(b.getBlock()));
    }

    private static void fell(ServerLevel level, Player player, ItemStack stack, BlockState origin, BlockPos start) {
        Set<BlockPos> found = new HashSet<>();
        Deque<BlockPos> queue = new ArrayDeque<>();
        found.add(start.immutable());
        queue.add(start.immutable());

        while (!queue.isEmpty() && found.size() < MAX_LOGS) {
            BlockPos cur = queue.poll();
            for (Direction dir : Direction.values()) {
                BlockPos next = cur.relative(dir);
                if (found.contains(next)) {
                    continue;
                }
                BlockState state = level.getBlockState(next);
                if (!state.is(BlockTags.LOGS) || !sameLogFamily(origin, state)) {
                    continue;
                }
                found.add(next);
                queue.add(next);
                if (found.size() >= MAX_LOGS) {
                    break;
                }
            }
        }

        felling = true;
        int broken = 0;
        try {
            for (BlockPos p : found) {
                if (p.equals(start)) {
                    continue; // the struck log itself is left to the vanilla break that called us
                }
                if (level.destroyBlock(p, true, player)) {
                    broken++;
                }
            }
        } finally {
            felling = false;
        }

        if (broken > 0) {
            stack.hurtAndBreak(broken, player, EquipmentSlot.MAINHAND);
        }
    }
}

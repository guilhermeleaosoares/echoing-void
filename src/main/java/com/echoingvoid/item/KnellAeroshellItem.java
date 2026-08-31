package com.echoingvoid.item;

import com.echoingvoid.registry.ModComponents;
import com.echoingvoid.registry.ModKnell;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.TooltipDisplay;

import java.util.function.Consumer;

/**
 * The Knell Aeroshell: a Knell chestplate and an elytra in one item, wearing out separately.
 *
 * <p>PLAYER: "the knell aeroshell should have two different durability bars. 1 for wings, 1 for the
 * chestplate. they degrade seperately... if the chestplate durability runs out, the user is left
 * with just wings at the durability they were already out. if the wings durability runs out, the
 * user is left with just the regular chestplate, with its durability the same."
 *
 * <h2>Two pools, one item</h2>
 *
 * <p>The PLATE uses the stack's ordinary {@link DataComponents#DAMAGE}, so everything that already
 * knows how to damage or repair armour keeps working untouched - taking a hit, an anvil and a knell
 * ingot, Unbreaking, Mending. The WINGS use {@link ModComponents#WING_DAMAGE}, a second counter that
 * only this class and the anvil handler read.
 *
 * <p>Which pool a given point of wear comes out of is decided by {@link #damageItem}: while the
 * wearer is gliding it is the wings that are taking the strain, and everything else is the plate.
 * That rule is worth stating because it has a visible edge case - an arrow that hits you mid-flight
 * wears the wings rather than the plate. The alternative was distinguishing vanilla's own
 * once-a-second glide tick from combat damage, which is not something the hook is told, and a rule
 * a player can predict beats one that is technically finer but invisible.
 *
 * <h2>Neither pool destroys the item</h2>
 *
 * <p>Running a pool out splits the Aeroshell rather than breaking it, which is the point of the
 * feature. Both pools are therefore clamped one point short of their maximum, and {@link
 * #inventoryTick} performs the split the moment either reaches that floor:
 *
 * <ul>
 *   <li>plate spent -> a plain {@link Items#ELYTRA}, carrying the wings' remaining wear
 *   <li>wings spent -> a plain Knell chestplate, carrying the plate's remaining wear
 * </ul>
 *
 * <p>Both go through {@code transmuteCopy}, so enchantments, a custom name and any banked charge
 * survive the split. A player who wears one until it gives out is left holding half of what they
 * built, not a hole in their inventory.
 */
public class KnellAeroshellItem extends KnellArmorItem {

    /**
     * The wings hold exactly what a vanilla elytra holds.
     *
     * <p>Not a number picked for balance: an exhausted Aeroshell becomes a real elytra carrying this
     * counter across as its damage value, so the two pools have to measure the same thing on the
     * same scale or the split would silently heal or wreck the wings.
     */
    public static final int WING_MAX = 432;

    public KnellAeroshellItem(Properties properties) {
        super(properties);
    }

    // ------------------------------------------------------------------ the wing pool

    public static boolean isAeroshell(ItemStack stack) {
        return stack.getItem() instanceof KnellAeroshellItem;
    }

    public static int wingDamage(ItemStack stack) {
        return Mth.clamp(stack.getOrDefault(ModComponents.WING_DAMAGE.get(), 0), 0, WING_MAX);
    }

    /** Remaining wing durability, for a tooltip or a bar. */
    public static int wingsLeft(ItemStack stack) {
        return WING_MAX - wingDamage(stack);
    }

    /**
     * Adds wear to the wings, stopping one point short of the maximum.
     *
     * <p>The stop is what lets {@link #inventoryTick} split the item instead of vanilla destroying
     * it, and it costs the player exactly one point of flight out of 432.
     */
    public static void wearWings(ItemStack stack, int amount) {
        stack.set(ModComponents.WING_DAMAGE.get(),
                Math.min(WING_MAX - 1, wingDamage(stack) + Math.max(0, amount)));
    }

    /** Mends the wings. Used by the anvil handler and by Mending. */
    public static void repairWings(ItemStack stack, int amount) {
        stack.set(ModComponents.WING_DAMAGE.get(), Math.max(0, wingDamage(stack) - Math.max(0, amount)));
    }

    public static boolean wingsSpent(ItemStack stack) {
        return wingDamage(stack) >= WING_MAX - 1;
    }

    public static boolean plateSpent(ItemStack stack) {
        return stack.getDamageValue() >= stack.getMaxDamage() - 1;
    }

    // ------------------------------------------------------------------ wear routing

    /**
     * Sends this point of wear to whichever half is bearing the load, and never lets either half
     * break the item.
     */
    @Override
    public int damageItem(ItemStack stack, int damage, ServerLevel level,
                          ServerPlayer player, boolean canBreak, Consumer<Item> onBroken) {
        if (player != null && player.isFallFlying()) {
            wearWings(stack, damage);
            return 0;
        }
        // Clamp rather than allow the break: vanilla would delete the stack, and the whole
        // point is that an exhausted plate leaves the wings behind.
        int headroom = Math.max(0, stack.getMaxDamage() - 1 - stack.getDamageValue());
        return Math.min(damage, headroom);
    }

    /**
     * Splits the item the moment either half gives out.
     *
     * <p>Done here rather than in {@link #damageItem} because an {@code ItemStack} cannot change
     * which {@code Item} it is - the stack has to be REPLACED, which means reaching the slot that
     * holds it. {@code EntityEquipment.tick} calls this for every worn piece each tick with the
     * slot in hand, which is exactly what that needs.
     */
    @Override
    public void inventoryTick(ItemStack stack, ServerLevel level, Entity owner, EquipmentSlot slot) {
        super.inventoryTick(stack, level, owner, slot);
        if (slot == null || !(owner instanceof LivingEntity wearer)) {
            return;
        }

        if (plateSpent(stack)) {
            // The plate is gone; the wings are not. transmuteCopy carries enchantments and the
            // name across, and the wing counter becomes the elytra's own damage - the two pools
            // are the same size precisely so this is a straight copy rather than a rescale.
            ItemStack wings = stack.transmuteCopy(Items.ELYTRA);
            wings.remove(ModComponents.WING_DAMAGE.get());
            wings.setDamageValue(wingDamage(stack));
            wearer.setItemSlot(slot, wings);
            return;
        }

        if (wingsSpent(stack)) {
            ItemStack plate = stack.transmuteCopy(ModKnell.RESONANT_CHESTPLATE.get());
            plate.remove(ModComponents.WING_DAMAGE.get());
            plate.setDamageValue(stack.getDamageValue());
            wearer.setItemSlot(slot, plate);
        }
    }

    // ------------------------------------------------------------------ readouts

    // No isBarVisible override any more. Item's default is stack.isDamaged(), which is
    // exactly what was asked for: "the durability bar only shows from 943 durability below."
    // Forcing it true showed an empty-looking bar on a brand new Aeroshell, which is not what
    // any other piece of armour in the game does.
    //
    // The wings get their own bar one row beneath vanilla's, drawn by AeroshellBarDecorator -
    // a slot hosts only one built-in bar.

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display,
                                Consumer<Component> lines, TooltipFlag flag) {
        super.appendHoverText(stack, context, display, lines, flag);
        // Two bars are cryptic without a key. This says which is which, and in the bars' own
        // colours, so the tooltip and the slot agree at a glance.
        lines.accept(Component.translatable("tooltip.echoing_void.aeroshell_plate",
                        stack.getMaxDamage() - stack.getDamageValue(), stack.getMaxDamage())
                .withStyle(ChatFormatting.GRAY));
        lines.accept(Component.translatable("tooltip.echoing_void.aeroshell_wings",
                        wingsLeft(stack), WING_MAX)
                .withStyle(ChatFormatting.LIGHT_PURPLE));
    }
}

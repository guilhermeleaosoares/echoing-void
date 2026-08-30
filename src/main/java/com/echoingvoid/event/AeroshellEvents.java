package com.echoingvoid.event;

import com.echoingvoid.item.KnellAeroshellItem;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraftforge.event.AnvilUpdateEvent;
import net.minecraftforge.event.entity.player.PlayerXpEvent;

/**
 * The two ways the Aeroshell's WING pool gets mended.
 *
 * <p>The plate half needs nothing here. It uses the stack's ordinary damage value, so an anvil and a
 * knell ingot already repair it through {@code KnellMaterials.REPAIRS_RESONANT_ARMOR}, and Mending
 * already finds it. Only the second pool - which nothing in the game knows about - needs wiring.
 *
 * <p>PLAYER: "a mending enchantment heals both durability bars. knell ingots on an anvil repair the
 * armor, phantom membranes repair the wings part of the aeroshell."
 */
public final class AeroshellEvents {
    private AeroshellEvents() {}

    /** One membrane mends this much of the wing pool - a quarter, as vanilla repairs a quarter. */
    private static final int MEMBRANE_REPAIR = KnellAeroshellItem.WING_MAX / 4;

    /** Durability restored per point of experience, matching vanilla Mending's rate. */
    private static final int MENDING_PER_XP = 2;

    public static void register() {
        AnvilUpdateEvent.BUS.addListener(AeroshellEvents::onAnvil);
        PlayerXpEvent.PickupXp.BUS.addListener(AeroshellEvents::onPickupXp);
    }

    /**
     * Phantom membranes mend the wings on an anvil.
     *
     * <p>Vanilla's own repair path can only ever see the stack's damage value, so without this an
     * Aeroshell with shredded wings and a perfect plate would show no repair at all - the anvil
     * would look at a full-durability item and offer nothing.
     */
    private static void onAnvil(AnvilUpdateEvent event) {
        ItemStack left = event.getLeft();
        ItemStack right = event.getRight();
        if (!KnellAeroshellItem.isAeroshell(left) || !right.is(Items.PHANTOM_MEMBRANE)) {
            return;
        }
        if (KnellAeroshellItem.wingDamage(left) <= 0) {
            return;
        }

        // Spend only as many membranes as the damage actually needs, the way vanilla stops
        // consuming ingots once an item is whole.
        int needed = Math.min(right.getCount(),
                (KnellAeroshellItem.wingDamage(left) + MEMBRANE_REPAIR - 1) / MEMBRANE_REPAIR);

        ItemStack out = left.copy();
        KnellAeroshellItem.repairWings(out, needed * MEMBRANE_REPAIR);
        event.setOutput(out);
        event.setMaterialCost(needed);
        event.setCost(needed);
    }

    /**
     * Mending mends the wings too.
     *
     * <p>Vanilla's repair runs off {@code DataComponents.DAMAGE} and cannot see the wing pool, so
     * this listens for the same orb and mends the wings at the same rate.
     *
     * <p>It does NOT take that experience away from vanilla's repair, and that is deliberate rather
     * than an oversight: {@code ExperienceOrb.setValue} is private, so the orb cannot be reduced
     * from here, and the choice was between Mending maintaining both halves of the Aeroshell or
     * only ever one of them. The player asked for "a mending enchantment heals both durability
     * bars", which is the first. The practical effect is that Mending is efficient on an Aeroshell
     * - one orb can serve both pools - and that reads as a reward for having built the thing.
     */
    private static void onPickupXp(PlayerXpEvent.PickupXp event) {
        if (!(event.getEntity() instanceof Player player)) {
            return;
        }
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        if (!KnellAeroshellItem.isAeroshell(chest) || KnellAeroshellItem.wingDamage(chest) <= 0) {
            return;
        }
        if (EnchantmentHelper.getItemEnchantmentLevel(
                player.level().registryAccess()
                        .lookupOrThrow(net.minecraft.core.registries.Registries.ENCHANTMENT)
                        .getOrThrow(Enchantments.MENDING),
                chest) <= 0) {
            return;
        }
        KnellAeroshellItem.repairWings(chest, event.getOrb().getValue() * MENDING_PER_XP);
    }
}

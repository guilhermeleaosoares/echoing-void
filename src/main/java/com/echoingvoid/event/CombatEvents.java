package com.echoingvoid.event;

import com.echoingvoid.item.AeroStrideGreavesItem;
import com.echoingvoid.item.ResonanceArmorItem;
import com.echoingvoid.item.SonicLanceItem;
import com.echoingvoid.item.VoidGlassRapierItem;
import com.echoingvoid.registry.ModComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingFallEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.CriticalHitEvent;

/**
 * Combat wiring for the gear suite. Everything here is reactive: no listener walks a level's
 * entity list, and each one leaves in its first few lines when its item is not in play.
 *
 * <p>The Void-Glass Rapier's armour bypass is the only stateful piece. Vanilla runs
 * {@code LivingHurtEvent} before armour absorption and {@code LivingDamageEvent} after it,
 * back to back inside {@code LivingEntity#actuallyHurt} on the server thread, so the
 * pre-armour figure is stashed in the first and used to undo half the mitigation in the
 * second. That avoids re-dealing damage, which would fight the invulnerability timer.
 */
public final class CombatEvents {
    private CombatEvents() {}

    /** Target of the melee swing currently in flight, if it was made with a rapier. */
    private static Entity armedRapierTarget;

    /** Victim whose armour mitigation is due to be partly refunded. */
    private static LivingEntity pendingBypassTarget;

    /** That victim's damage figure before armour and enchantment absorption. */
    private static float pendingBypassPreArmour;

    public static void register() {
        AttackEntityEvent.BUS.addListener(CombatEvents::onAttackEntity);
        LivingHurtEvent.BUS.addListener(CombatEvents::onLivingHurt);
        LivingDamageEvent.BUS.addListener(CombatEvents::onLivingDamage);
        CriticalHitEvent.BUS.addListener(CombatEvents::onCriticalHit);
        LivingFallEvent.BUS.addListener(CombatEvents::onLivingFall);
    }

    // ------------------------------------------------------------- rapier arming

    /**
     * Fires at the very start of {@code Player#attack}. Arms the armour bypass for exactly
     * this target so that a rapier's effect cannot leak onto damage the player did not deal
     * with the blade.
     */
    private static void onAttackEntity(AttackEntityEvent event) {
        if (!VoidGlassRapierItem.isRapier(event.getEntity().getMainHandItem())) {
            armedRapierTarget = null;
            return;
        }
        armedRapierTarget = event.getTarget();
    }

    // -------------------------------------------------------- pre-mitigation hook

    private static void onLivingHurt(LivingHurtEvent event) {
        LivingEntity victim = event.getEntity();
        DamageSource source = event.getSource();

        // A previous hit that never reached the damage phase would otherwise pin its victim in
        // this field; any later damage anywhere clears it.
        pendingBypassTarget = null;

        // Rapier: remember what the blow was worth before the target's plate ate any of it.
        if (victim == armedRapierTarget
                && source.isDirect()
                && source.getEntity() instanceof Player attacker
                && VoidGlassRapierItem.isRapier(attacker.getMainHandItem())) {
            pendingBypassTarget = victim;
            pendingBypassPreArmour = event.getAmount();
            armedRapierTarget = null;
        }

        if (!(victim instanceof Player player)) {
            return;
        }

        // Sonic Lance: a held lance drinks incoming projectile impact instead of letting it land.
        if (source.is(DamageTypeTags.IS_PROJECTILE)) {
            ItemStack lance = heldLance(player);
            if (!lance.isEmpty()) {
                float absorbed = event.getAmount() * 0.35F;
                ModComponents.addCharge(lance, Math.round(absorbed * SonicLanceItem.CHARGE_PER_DAMAGE));
                event.setAmount(event.getAmount() - absorbed);
            }
        }

        // Resonance: the plates take a slice off the top before armour is even consulted.
        ItemStack resonator = ResonanceArmorItem.resonator(player);
        if (resonator.isEmpty()) {
            return;
        }
        float mitigation = ResonanceArmorItem.isFullSet(player)
                ? ResonanceArmorItem.SET_MITIGATION
                : ResonanceArmorItem.PIECE_MITIGATION;
        event.setAmount(event.getAmount() * (1.0F - mitigation));
    }

    // ------------------------------------------------------- post-mitigation hook

    private static void onLivingDamage(LivingDamageEvent event) {
        LivingEntity victim = event.getEntity();

        // Rapier: hand back half of whatever the target's armour absorbed.
        if (victim == pendingBypassTarget) {
            event.setAmount(VoidGlassRapierItem.bypassArmour(pendingBypassPreArmour, event.getAmount()));
            pendingBypassTarget = null;
        }

        if (!(victim instanceof Player player)) {
            return;
        }

        // Resonance: bank a share of what actually got through, ready to be thrown back.
        ItemStack resonator = ResonanceArmorItem.resonator(player);
        if (resonator.isEmpty()) {
            return;
        }
        ModComponents.storeDamage(resonator, event.getAmount() * ResonanceArmorItem.BANK_RATE);
    }

    // ---------------------------------------------------------------- critical hit

    private static void onCriticalHit(CriticalHitEvent event) {
        Player attacker = event.getEntity();
        if (!VoidGlassRapierItem.isRapier(attacker.getMainHandItem())) {
            return;
        }
        if (event.getResult().isDenied()) {
            return;
        }
        if (!event.isVanillaCritical() && !event.getResult().isAllowed()) {
            return;
        }
        if (!(attacker.level() instanceof ServerLevel)) {
            return;
        }
        VoidGlassRapierItem.veil(attacker);
    }

    // ------------------------------------------------------------------- landing

    private static void onLivingFall(LivingFallEvent event) {
        LivingEntity faller = event.getEntity();
        if (!AeroStrideGreavesItem.isWorn(faller)) {
            return;
        }

        double distance = event.getDistance();
        event.setDistance(0.0);
        event.setDamageMultiplier(0.0F);

        if (AeroStrideGreavesItem.shouldDrift(distance) && faller.level() instanceof ServerLevel level) {
            AeroStrideGreavesItem.openDriftZone(level, faller);
        }
    }

    // --------------------------------------------------------------------- helper

    /**
     * The lance in one of the player's hands, if there is one with room left. Only the two
     * hands are checked - a lance buried in the pack is not braced against anything.
     */
    private static ItemStack heldLance(Player player) {
        ItemStack main = player.getMainHandItem();
        if (SonicLanceItem.canAbsorb(main)) {
            return main;
        }
        ItemStack off = player.getOffhandItem();
        return SonicLanceItem.canAbsorb(off) ? off : ItemStack.EMPTY;
    }
}

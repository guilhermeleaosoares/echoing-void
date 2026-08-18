package com.echoingvoid.item;

import com.echoingvoid.registry.ModComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.function.Predicate;

/**
 * Resonance Armour - a null-iron shell strung with bismuth resonators.
 *
 * <p>Every hit the wearer takes is partly stored rather than spent: the chestplate keeps a
 * running total of banked kinetic damage (capped at {@link ModComponents#MAX_STORED_DAMAGE}),
 * and while the full four-piece set is worn the plates also shave a little off each blow.
 *
 * <p>Double-tap crouch and the resonators dump everything at once - a concussive ring that
 * throws nearby hostiles off the wearer and does a fraction of the banked total as damage.
 * The bank is emptied whether or not anything was standing close enough to be hit; the release
 * is the point, not the kill.
 *
 * <p>One class backs all four pieces; which slot a given stack occupies is decided by the
 * {@code humanoidArmor} properties the registry hands to the constructor.
 */
public class ResonanceArmorItem extends Item {

    /** Fraction of incoming damage the chestplate alone absorbs outright. */
    public static final float PIECE_MITIGATION = 0.08F;

    /** Fraction absorbed when all four plates are resonating together. */
    public static final float SET_MITIGATION = 0.20F;

    /** Fraction of the damage taken that is banked rather than lost. */
    public static final float BANK_RATE = 0.5F;

    /** Nothing releases below this much banked damage - it would only waste the charge. */
    public static final float MIN_RELEASE = 4.0F;

    private static final double SHOCKWAVE_RADIUS = 6.0;
    private static final float DAMAGE_RETURN = 0.4F;
    private static final double MIN_KNOCKBACK = 0.6;
    private static final double MAX_KNOCKBACK = 2.2;

    /** Non-capturing, so the broad-phase query reuses one singleton predicate. */
    private static final Predicate<Entity> HOSTILE =
            entity -> entity instanceof Enemy && entity.isAlive() && !entity.isSpectator();

    public ResonanceArmorItem(Item.Properties properties) {
        super(properties);
    }

    /** True when the stack is any Resonance piece. */
    public static boolean isPiece(ItemStack stack) {
        return !stack.isEmpty() && stack.getItem() instanceof ResonanceArmorItem;
    }

    /** All four plates present. Four slot reads, no allocation. */
    public static boolean isFullSet(LivingEntity wearer) {
        return isPiece(wearer.getItemBySlot(EquipmentSlot.HEAD))
                && isPiece(wearer.getItemBySlot(EquipmentSlot.CHEST))
                && isPiece(wearer.getItemBySlot(EquipmentSlot.LEGS))
                && isPiece(wearer.getItemBySlot(EquipmentSlot.FEET));
    }

    /**
     * The chestplate is where the charge lives, because it is the piece a player is most
     * likely to be wearing and the one the resonators are wired to.
     *
     * @return the worn Resonance chestplate, or {@link ItemStack#EMPTY} if there is none
     */
    public static ItemStack resonator(LivingEntity wearer) {
        ItemStack chest = wearer.getItemBySlot(EquipmentSlot.CHEST);
        return isPiece(chest) ? chest : ItemStack.EMPTY;
    }

    /**
     * Empties the bank into a ring of force centred on the wearer.
     *
     * @return true if a shockwave actually went off
     */
    public static boolean releaseShockwave(ServerLevel level, Player wearer) {
        ItemStack chest = resonator(wearer);
        if (chest.isEmpty() || ModComponents.getStoredDamage(chest) < MIN_RELEASE) {
            return false;
        }

        float stored = ModComponents.drainStoredDamage(chest);
        float fraction = Math.min(1.0F, stored / ModComponents.MAX_STORED_DAMAGE);
        float damage = stored * DAMAGE_RETURN;
        double knockback = MIN_KNOCKBACK + (MAX_KNOCKBACK - MIN_KNOCKBACK) * fraction;

        double px = wearer.getX();
        double py = wearer.getY();
        double pz = wearer.getZ();

        // One-shot path behind a double-tap, so a single query box here is fine; nothing in
        // the loop below allocates.
        AABB ring = new AABB(px - SHOCKWAVE_RADIUS, py - SHOCKWAVE_RADIUS, pz - SHOCKWAVE_RADIUS,
                px + SHOCKWAVE_RADIUS, py + SHOCKWAVE_RADIUS, pz + SHOCKWAVE_RADIUS);
        List<Entity> caught = level.getEntities(wearer, ring, HOSTILE);

        DamageSource source = level.damageSources().sonicBoom(wearer);
        double radiusSq = SHOCKWAVE_RADIUS * SHOCKWAVE_RADIUS;

        for (int i = 0; i < caught.size(); i++) {
            Entity entity = caught.get(i);
            double dx = entity.getX() - px;
            double dz = entity.getZ() - pz;
            double dy = entity.getY() - py;
            double distSq = dx * dx + dy * dy + dz * dz;
            if (distSq > radiusSq) {
                continue;
            }

            // Falls off with distance so the ring reads as a wave rather than a box.
            double falloff = 1.0 - Math.sqrt(distSq) / SHOCKWAVE_RADIUS;
            entity.hurtServer(level, source, (float) (damage * falloff));
            if (entity instanceof LivingEntity living) {
                // knockback pushes away from (xd, zd): pass the wearer-to-target vector negated.
                living.knockback(knockback * falloff, -dx, -dz, source, damage, false);
            }
        }

        level.sendParticles(ParticleTypes.SONIC_BOOM, px, py + 1.0, pz, 6, 0.4, 0.2, 0.4, 0.0);
        level.playSound(null, px, py, pz, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS,
                1.0F, 1.2F - fraction * 0.4F);
        return true;
    }
}

package com.echoingvoid.item;

import com.echoingvoid.registry.ModComponents;
import net.minecraft.core.particles.ParticleOptions;
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
 * running total of banked kinetic damage, and while the full four-piece set is worn the plates
 * also shave a little off each blow.
 *
 * <p>Double-tap crouch and the resonators dump everything at once - a concussive ring that
 * throws nearby hostiles off the wearer and does a fraction of the banked total as damage.
 * The bank is emptied whether or not anything was standing close enough to be hit; the release
 * is the point, not the kill.
 *
 * <p>One class backs all four pieces; which slot a given stack occupies is decided by the
 * {@code humanoidArmor} properties the registry hands to the constructor.
 *
 * <h2>Tiers</h2>
 *
 * <p>{@link KnellArmorItem} is the tier above and subclasses this, so every figure the ability
 * is built from is an overridable method rather than a constant. The tier in force is always
 * read off the <em>chestplate</em>, because that is where the charge physically lives - which
 * also settles what a mixed set does without anyone needing to invent a rule for it. Wear a
 * Knell chestplate under three Resonance plates and the bank is Knell's: the resonator is the
 * part that decides, the other three only complete the circuit.
 */
public class ResonanceArmorItem extends Item {

    // ------------------------------------------------------------------ tuning
    // Overridable rather than constant, so a tier above can amplify the ability without a
    // second copy of the logic below. Every figure read from a worn piece goes through these.

    /** Fraction of incoming damage the chestplate alone absorbs outright. */
    public float pieceMitigation() {
        return 0.08F;
    }

    /** Fraction absorbed when all four plates are resonating together. */
    public float setMitigation() {
        return 0.20F;
    }

    /** Fraction of the damage taken that is banked rather than lost. */
    public float bankRate() {
        return 0.5F;
    }

    /** Nothing releases below this much banked damage - it would only waste the charge. */
    public float minRelease() {
        return 4.0F;
    }

    /** Most the resonators will hold. Past this a hit is still absorbed, but not stored. */
    public float bankCapacity() {
        return 60.0F;
    }

    /** How far the released ring reaches. */
    public double shockwaveRadius() {
        return 6.0;
    }

    /** Share of the banked total the ring deals as damage at its centre. */
    public float damageReturn() {
        return 0.4F;
    }

    /** Knockback from a barely-charged bank. */
    public double minKnockback() {
        return 0.6;
    }

    /** Knockback from a full one. */
    public double maxKnockback() {
        return 2.2;
    }

    /**
     * What the release throws off.
     *
     * <p>Overridable because the tier above wants its own colour, and this is the awkward part:
     * {@link ParticleTypes#SONIC_BOOM} is a fixed sprite with no tint field, so "the same particle
     * in another colour" is not a thing the engine offers. {@link KnellArmorItem} substitutes
     * coloured dust and raises the count to carry comparable visual weight - same position, same
     * spread, same moment, different particle.
     */
    protected ParticleOptions releaseParticle() {
        return ParticleTypes.SONIC_BOOM;
    }

    /** How many of {@link #releaseParticle()} to emit. Scales with how small the particle is. */
    protected int releaseParticleCount() {
        return 6;
    }

    /** Non-capturing, so the broad-phase query reuses one singleton predicate. */
    private static final Predicate<Entity> HOSTILE =
            entity -> entity instanceof Enemy && entity.isAlive() && !entity.isSpectator();

    public ResonanceArmorItem(Item.Properties properties) {
        super(properties);
    }

    /** True when the stack is a resonating piece of either tier. */
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
     * @return the worn chestplate of either tier, or {@link ItemStack#EMPTY} if there is none
     */
    public static ItemStack resonator(LivingEntity wearer) {
        ItemStack chest = wearer.getItemBySlot(EquipmentSlot.CHEST);
        return isPiece(chest) ? chest : ItemStack.EMPTY;
    }

    /** The tuning in force for a wearer, read off the chestplate, or null if none is worn. */
    public static ResonanceArmorItem tierOf(LivingEntity wearer) {
        ItemStack chest = wearer.getItemBySlot(EquipmentSlot.CHEST);
        return chest.getItem() instanceof ResonanceArmorItem tier ? tier : null;
    }

    /**
     * Fraction of an incoming blow the plates take off the top, before armour is consulted.
     *
     * @return zero when nothing is worn, so a caller can apply it unconditionally
     */
    public static float mitigationFor(LivingEntity wearer) {
        ResonanceArmorItem tier = tierOf(wearer);
        if (tier == null) {
            return 0.0F;
        }
        return isFullSet(wearer) ? tier.setMitigation() : tier.pieceMitigation();
    }

    /**
     * Banks a share of damage the wearer actually took, at the resonator's own rate and cap.
     *
     * <p>The rate is the armour's rather than the caller's: being hit is not a choice, and the
     * set exists to reward standing your ground.
     */
    public static void bankIncoming(LivingEntity wearer, float damageTaken) {
        ResonanceArmorItem tier = tierOf(wearer);
        if (tier != null) {
            bankAmount(wearer, damageTaken * tier.bankRate());
        }
    }

    /**
     * Banks an amount the caller has already scaled - the sword pays its own, lower rate - still
     * respecting whatever the worn resonator can hold.
     */
    public static void bankAmount(LivingEntity wearer, float amount) {
        ResonanceArmorItem tier = tierOf(wearer);
        if (tier == null) {
            return;
        }
        ModComponents.storeDamage(wearer.getItemBySlot(EquipmentSlot.CHEST), amount,
                tier.bankCapacity());
    }

    /**
     * Empties the bank into a ring of force centred on the wearer.
     *
     * @return true if a shockwave actually went off
     */
    public static boolean releaseShockwave(ServerLevel level, Player wearer) {
        ResonanceArmorItem tier = tierOf(wearer);
        if (tier == null) {
            return false;
        }
        ItemStack chest = wearer.getItemBySlot(EquipmentSlot.CHEST);
        if (ModComponents.getStoredDamage(chest) < tier.minRelease()) {
            return false;
        }

        float stored = ModComponents.drainStoredDamage(chest);
        float fraction = Math.min(1.0F, stored / tier.bankCapacity());
        float damage = stored * tier.damageReturn();
        double radius = tier.shockwaveRadius();
        double knockback = tier.minKnockback()
                + (tier.maxKnockback() - tier.minKnockback()) * fraction;

        double px = wearer.getX();
        double py = wearer.getY();
        double pz = wearer.getZ();

        // One-shot path behind a double-tap, so a single query box here is fine; nothing in
        // the loop below allocates.
        AABB ring = new AABB(px - radius, py - radius, pz - radius,
                px + radius, py + radius, pz + radius);
        List<Entity> caught = level.getEntities(wearer, ring, HOSTILE);

        DamageSource source = level.damageSources().sonicBoom(wearer);
        double radiusSq = radius * radius;

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
            double falloff = 1.0 - Math.sqrt(distSq) / radius;
            entity.hurtServer(level, source, (float) (damage * falloff));
            if (entity instanceof LivingEntity living) {
                // knockback pushes away from (xd, zd): pass the wearer-to-target vector negated.
                living.knockback(knockback * falloff, -dx, -dz, source, damage, false);
            }
        }

        level.sendParticles(tier.releaseParticle(), px, py + 1.0, pz,
                tier.releaseParticleCount(), 0.4, 0.2, 0.4, 0.0);
        level.playSound(null, px, py, pz, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS,
                1.0F, 1.2F - fraction * 0.4F);
        return true;
    }
}

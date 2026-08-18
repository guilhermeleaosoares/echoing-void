package com.echoingvoid.item;

import com.echoingvoid.registry.ModComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;

/**
 * The Resonance Sword: the half of the Resonance set that was missing.
 *
 * <p>The armour banks a share of the damage it takes and dumps it as a shockwave on a
 * double-crouch, which makes the set purely reactive - you have to be losing a fight to charge it.
 * This sword feeds the same bank from dealing damage, so the loop closes: hit things, bank charge,
 * release it into the crowd, keep hitting.
 *
 * <p>PLAYER: "have an attack for the resonance sword like a noise thing that throws off mobs like
 * the warden for a certain time within a certain radius." A right-click discharge, on a cooldown so
 * it cannot be spammed as free crowd control: a burst of sound that disorients every hostile mob in
 * range - Slowness and Darkness, the same "can no longer fight straight" combination the Warden's
 * own sonic boom leaves a survivor with - and knocks them back off the swing.
 *
 * <p>Otherwise unremarkable without the armour. There is no self-buff, no bonus damage on a normal
 * hit; the passive half is a synergy piece and a player who has not built the set gains nothing
 * from carrying it for that. That is what keeps it distinct from the Sonic Lance (a crowd and
 * anti-ranged answer) and the Void-Glass Rapier (a single-target armour bypass), rather than being
 * a third sword with different numbers.
 */
public class HarmonicSwordItem extends Item {

    /** Blocks the wearer's own hostile-adjacent mobs at close range, tuned for a room, not a field. */
    protected int sonicRadius() {
        return 6;
    }

    /** How long the disoriented mobs stay that way. */
    protected int sonicDurationTicks() {
        return 100; // 5 seconds
    }

    /** Between discharges - short enough to use often, long enough that it is a tool, not a toggle. */
    private static final int COOLDOWN_TICKS = 140;

    /**
     * Share of the damage dealt that lands in the bank.
     *
     * <p>Lower than the armour's {@link ResonanceArmorItem#BANK_RATE} on purpose: a player chooses
     * when to attack and cannot choose when to be hit, so paying the same rate for the safer
     * action would make standing your ground the strictly worse way to charge - which is the
     * behaviour the set exists to reward.
     */
    public static final float BANK_RATE = 0.30F;

    public HarmonicSwordItem(Properties properties) {
        super(properties);
    }

    /**
     * Right-click: discharge the sonic burst. Fails cleanly (PASS, no cooldown spent) if already on
     * cooldown, so an impatient extra click costs nothing.
     */
    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (player.getCooldowns().isOnCooldown(stack)) {
            return InteractionResult.PASS;
        }
        if (level instanceof ServerLevel serverLevel) {
            discharge(serverLevel, player);
        }
        player.getCooldowns().addCooldown(stack, COOLDOWN_TICKS);
        level.playSound(null, player.blockPosition(), SoundEvents.SCULK_SHRIEKER_SHRIEK,
                SoundSource.PLAYERS, 1.0F, 0.8F);
        return InteractionResult.CONSUME;
    }

    /** Everything hostile within {@link #sonicRadius()} is disoriented and pushed off the player. */
    private void discharge(ServerLevel level, Player player) {
        double radius = sonicRadius();
        AABB area = player.getBoundingBox().inflate(radius);
        int duration = sonicDurationTicks();
        for (LivingEntity target : level.getEntitiesOfClass(LivingEntity.class, area,
                e -> e instanceof Enemy && e.isAlive())) {
            target.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, duration, 2));
            target.addEffect(new MobEffectInstance(MobEffects.DARKNESS, duration, 0));

            // A push directly away from the player, flattened to horizontal so it reads as being
            // thrown off rather than launched - vertical knockback would just look like fall damage
            // bait on uneven ground.
            double dx = target.getX() - player.getX();
            double dz = target.getZ() - player.getZ();
            double dist = Math.max(0.5, Math.sqrt(dx * dx + dz * dz));
            target.push((dx / dist) * 0.6, 0.1, (dz / dist) * 0.6);
        }
    }

    /**
     * Called after the sword has actually hurt something. Banks a share into the chestplate.
     *
     * <p>Server-side only, and a no-op when the wearer has no resonator: the component lives on
     * the chestplate, so with no chestplate there is nowhere to put the charge and nothing to
     * release it from.
     */
    @Override
    public void hurtEnemy(ItemStack stack, LivingEntity target, LivingEntity attacker) {
        super.hurtEnemy(stack, target, attacker);
        if (!(attacker.level() instanceof ServerLevel)) {
            return;
        }
        ItemStack resonator = ResonanceArmorItem.resonator(attacker);
        if (resonator.isEmpty()) {
            return;
        }
        // Scale off the sword's own attack damage rather than the damage actually dealt: the
        // post-hit hook is not told how much got through armour, and reading the target's health
        // delta here would credit the swing for another source's damage in the same tick.
        ModComponents.storeDamage(resonator, attackDamage(stack) * BANK_RATE);
    }

    /**
     * Baseline passed to {@code Item.Properties.sword(...)} at registration.
     *
     * <p>Kept here rather than only at the call site because the bank is computed from it, and
     * the two drifting apart would silently mis-scale the charge. 26.2 builds the sword's
     * ATTACK_DAMAGE modifier as {@code attackDamageBaseline + material.attackDamageBonus()}
     * (ToolMaterial.createSwordAttributes), so that sum is what a swing is worth.
     */
    public static final float ATTACK_BASELINE = 3.0F;

    /** What this sword swings for, matching the attribute the game builds from the same parts. */
    private static float attackDamage(ItemStack stack) {
        return ATTACK_BASELINE + ModToolMaterials.RESONANT_BISMUTH.attackDamageBonus();
    }
}

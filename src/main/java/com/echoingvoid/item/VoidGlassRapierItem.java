package com.echoingvoid.item;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/**
 * The Void-Glass Rapier - a blade thin enough to find the gaps in plate.
 *
 * <p>Half of whatever the target's armour would have stopped is given back, so the rapier
 * scales with how heavily armoured its victim is rather than with raw attack power. That is
 * done by comparing the pre-armour and post-armour figures across
 * {@code LivingHurtEvent} and {@code LivingDamageEvent} and restoring half the difference -
 * no second damage application, no invulnerability-frame games, no bespoke damage type.
 *
 * <p>Land a critical strike and the wielder briefly goes out of phase with the world:
 * three seconds of invisibility to break off and reposition.
 */
public class VoidGlassRapierItem extends Item {

    /** Fraction of the target's armour mitigation that the blade slips past. */
    public static final float ARMOUR_BYPASS = 0.5F;

    /** Duration of the post-critical veil, in ticks. */
    private static final int VEIL_TICKS = 60;

    public VoidGlassRapierItem(Item.Properties properties) {
        super(properties);
    }

    /** True when the stack is a rapier. Cheap enough to be the first line of every listener. */
    public static boolean isRapier(ItemStack stack) {
        return !stack.isEmpty() && stack.getItem() instanceof VoidGlassRapierItem;
    }

    /**
     * Rebuilds the damage figure with half of the armour mitigation undone.
     *
     * @param preArmour the amount seen before armour and enchantment absorption
     * @param mitigated the final amount after absorption
     * @return the amount to apply instead - never less than {@code mitigated}
     */
    public static float bypassArmour(float preArmour, float mitigated) {
        float absorbed = preArmour - mitigated;
        if (absorbed <= 0.0F) {
            return mitigated;
        }
        return mitigated + absorbed * ARMOUR_BYPASS;
    }

    /** Drops the attacker out of sight for a moment after a critical strike. */
    public static void veil(Player attacker) {
        attacker.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, VEIL_TICKS, 0, true, false), attacker);
        if (attacker.level() instanceof ServerLevel level) {
            level.playSound(null, attacker.getX(), attacker.getY(), attacker.getZ(),
                    SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 0.7F, 1.8F);
        }
    }
}

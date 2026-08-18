package com.echoingvoid.item;

import com.echoingvoid.registry.ModComponents;
import net.minecraft.ChatFormatting;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.TooltipDisplay;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.function.Consumer;
import java.util.function.Predicate;

/**
 * The Sonic Lance - a null-iron shaft that eats the momentum of anything thrown at it.
 *
 * <p>Arrows, tridents, fireballs and the like do not simply hurt the bearer: the lance drinks
 * the impact and stores it (see {@code CombatEvents}, which feeds
 * {@link ModComponents#addCharge}). Right-click with a charged lance and the stored energy
 * leaves as a single piercing shockwave along the line of sight, hitting everything in a
 * narrow cylinder and shoving it away.
 *
 * <p>The discharge does exactly one broad-phase entity query over the whole ray and then
 * filters by perpendicular distance with plain doubles, so nothing is allocated per candidate.
 */
public class SonicLanceItem extends Item {

    /** Below this the lance only hums; there is not enough stored energy to fire. */
    public static final int MIN_DISCHARGE_CHARGE = 20;

    /** Charge granted per point of projectile damage absorbed. */
    public static final int CHARGE_PER_DAMAGE = 6;

    private static final double MIN_RANGE = 4.0;
    private static final double MAX_RANGE = 14.0;
    private static final double BEAM_RADIUS = 1.25;

    private static final float MIN_DAMAGE = 4.0F;
    private static final float MAX_DAMAGE = 13.0F;
    private static final double KNOCKBACK = 1.4;

    private static final int COOLDOWN_TICKS = 40;

    /** Non-capturing, so this is a singleton and the broad-phase query allocates no lambda. */
    private static final Predicate<Entity> SHOCKWAVE_TARGET =
            entity -> entity instanceof LivingEntity && entity.isAlive() && !entity.isSpectator();

    public SonicLanceItem(Item.Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        int charge = ModComponents.getCharge(stack);
        if (charge < MIN_DISCHARGE_CHARGE) {
            return super.use(level, player, hand);
        }

        if (level instanceof ServerLevel serverLevel) {
            discharge(serverLevel, player, stack, charge);
        }
        // Swing on the client regardless so the discharge reads as one motion.
        return InteractionResult.SUCCESS;
    }

    private static void discharge(ServerLevel level, Player player, ItemStack stack, int charge) {
        float fraction = Math.min(1.0F, (float) charge / ModComponents.MAX_CHARGE);
        double range = MIN_RANGE + (MAX_RANGE - MIN_RANGE) * fraction;
        float damage = MIN_DAMAGE + (MAX_DAMAGE - MIN_DAMAGE) * fraction;

        Vec3 origin = player.getEyePosition();
        Vec3 look = player.getLookAngle();
        double ox = origin.x;
        double oy = origin.y;
        double oz = origin.z;
        double dx = look.x;
        double dy = look.y;
        double dz = look.z;

        // One broad-phase box covering the whole beam, one query, no per-entity boxes.
        AABB sweep = new AABB(ox, oy, oz, ox + dx * range, oy + dy * range, oz + dz * range)
                .inflate(BEAM_RADIUS);
        List<Entity> candidates = level.getEntities(player, sweep, SHOCKWAVE_TARGET);

        DamageSource source = level.damageSources().sonicBoom(player);
        double radiusSq = BEAM_RADIUS * BEAM_RADIUS;

        for (int i = 0; i < candidates.size(); i++) {
            Entity entity = candidates.get(i);
            double rx = entity.getX() - ox;
            double ry = entity.getY() + entity.getBbHeight() * 0.5 - oy;
            double rz = entity.getZ() - oz;

            // Project onto the beam axis; reject anything behind the player or past the tip.
            double along = rx * dx + ry * dy + rz * dz;
            if (along < 0.0 || along > range) {
                continue;
            }
            double px = rx - dx * along;
            double py = ry - dy * along;
            double pz = rz - dz * along;
            if (px * px + py * py + pz * pz > radiusSq) {
                continue;
            }

            entity.hurtServer(level, source, damage);
            if (entity instanceof LivingEntity living) {
                // knockback pushes away from (xd, zd), so negate the beam direction.
                living.knockback(KNOCKBACK * fraction + 0.4, -dx, -dz, source, damage, false);
            }
        }

        drawBeam(level, ox, oy, oz, dx, dy, dz, range);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 1.4F, 0.8F + fraction * 0.4F);

        ModComponents.clearCharge(stack);
        stack.hurtAndBreak(2, player, EquipmentSlot.MAINHAND);
        player.getCooldowns().addCooldown(stack, COOLDOWN_TICKS);
    }

    /** Steps along the beam in whole blocks; all doubles, nothing allocated in the loop. */
    private static void drawBeam(ServerLevel level, double ox, double oy, double oz,
                                 double dx, double dy, double dz, double range) {
        int steps = (int) range;
        for (int step = 1; step <= steps; step++) {
            level.sendParticles(ParticleTypes.SONIC_BOOM,
                    ox + dx * step, oy + dy * step, oz + dz * step,
                    1, 0.0, 0.0, 0.0, 0.0);
        }
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display,
                                Consumer<Component> builder, TooltipFlag tooltipFlag) {
        int percent = ModComponents.getCharge(stack) * 100 / ModComponents.MAX_CHARGE;
        builder.accept(Component.translatable("tooltip.echoing_void.sonic_lance.charge", percent)
                .withStyle(percent >= 20 ? ChatFormatting.AQUA : ChatFormatting.DARK_GRAY));
    }

    /** True when this stack is a lance with room for more absorbed impact. */
    public static boolean canAbsorb(ItemStack stack) {
        return stack.getItem() instanceof SonicLanceItem
                && ModComponents.getCharge(stack) < ModComponents.MAX_CHARGE;
    }
}

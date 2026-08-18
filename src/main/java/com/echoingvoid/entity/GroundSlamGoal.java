package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.phys.AABB;

import java.util.EnumSet;
import java.util.List;

/**
 * The Strata Golem's signature move: it plants itself, raises its mass, and brings it down.
 *
 * <p>The move is deliberately slow and loud. {@link #WINDUP_TICKS} of climbing dust and a rising
 * tone give the player well over a second to leave the ring, and the golem cannot move while it
 * winds up, so backing off always works. That is what lets the damage be high without the hit
 * feeling cheap - it is avoidable, and visibly so.
 *
 * <p>The impact is a single bounded {@code getEntities} query over one box, run on the one tick
 * the slam lands. Nothing here scans the world per tick.
 */
class GroundSlamGoal extends Goal {
    /** How close the target must be before the golem commits. */
    private static final double TRIGGER_RANGE = 7.0;

    /** Reach at impact. Slightly wider than the trigger, so edging back barely is not enough. */
    private static final double IMPACT_RADIUS = 6.5;

    private static final int WINDUP_TICKS = 25;
    private static final int COOLDOWN_TICKS = 160;
    private static final float IMPACT_DAMAGE = 9.0F;

    private final StrataGolemEntity golem;
    private int windup;
    private int cooldown;

    GroundSlamGoal(StrataGolemEntity golem) {
        this.golem = golem;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (this.cooldown > 0) {
            this.cooldown--;
            return false;
        }
        LivingEntity target = this.golem.getTarget();
        return target != null
                && target.isAlive()
                && this.golem.onGround()
                && this.golem.distanceToSqr(target) <= TRIGGER_RANGE * TRIGGER_RANGE;
    }

    @Override
    public boolean canContinueToUse() {
        return this.windup > 0 && this.golem.getTarget() != null;
    }

    @Override
    public void start() {
        this.windup = WINDUP_TICKS;
        this.golem.getNavigation().stop();
        if (this.golem.level() instanceof ServerLevel level) {
            level.playSound(null, this.golem.getX(), this.golem.getY(), this.golem.getZ(),
                    SoundEvents.IRON_GOLEM_ATTACK, SoundSource.HOSTILE, 1.6F, 0.5F);
        }
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        LivingEntity target = this.golem.getTarget();
        if (target != null) {
            this.golem.getLookControl().setLookAt(target, 30.0F, 30.0F);
        }
        this.golem.getNavigation().stop();

        if (--this.windup > 0) {
            this.telegraph();
            return;
        }

        this.impact();
        // An enraged golem re-arms the slam far sooner, which is what stops "back off and wait it
        // out" from being a complete answer to the second half of the fight.
        this.cooldown = this.golem.isEnraged()
                ? Math.round(COOLDOWN_TICKS * StrataGolemEntity.RAGE_SLAM_COOLDOWN_SCALE)
                : COOLDOWN_TICKS;
    }

    /** Dust climbing the golem, so the wind-up is readable from across a cavern. */
    private void telegraph() {
        if (!(this.golem.level() instanceof ServerLevel level)) {
            return;
        }
        double progress = 1.0 - (double) this.windup / WINDUP_TICKS;
        level.sendParticles(ParticleTypes.CRIT,
                this.golem.getX(), this.golem.getY() + 0.4 + progress * 2.0, this.golem.getZ(),
                4, 0.8, 0.2, 0.8, 0.02);
        if (this.windup % 6 == 0) {
            level.playSound(null, this.golem.getX(), this.golem.getY(), this.golem.getZ(),
                    SoundEvents.DEEPSLATE_STEP, SoundSource.HOSTILE,
                    1.0F, 0.6F + (float) progress * 0.6F);
        }
    }

    /** The landing: one bounded query, damage and knockback radiating from the golem. */
    private void impact() {
        if (!(this.golem.level() instanceof ServerLevel level)) {
            return;
        }

        double ox = this.golem.getX();
        double oy = this.golem.getY();
        double oz = this.golem.getZ();

        level.playSound(null, ox, oy, oz, SoundEvents.GENERIC_EXPLODE.value(),
                SoundSource.HOSTILE, 1.8F, 0.55F);
        level.sendParticles(ParticleTypes.EXPLOSION, ox, oy + 0.2, oz, 6, 1.6, 0.1, 1.6, 0.0);

        // Draw the ring at its true radius, so the reach is legible after the fact.
        for (int step = 0; step < 40; step++) {
            double angle = step * (Math.PI * 2.0 / 40.0);
            level.sendParticles(ParticleTypes.CRIT,
                    ox + Math.cos(angle) * IMPACT_RADIUS,
                    oy + 0.2,
                    oz + Math.sin(angle) * IMPACT_RADIUS,
                    2, 0.1, 0.05, 0.1, 0.03);
        }

        DamageSource source = this.golem.damageSources().mobAttack(this.golem);
        AABB ring = this.golem.getBoundingBox().inflate(IMPACT_RADIUS, 3.0, IMPACT_RADIUS);
        List<Entity> hit = level.getEntities(this.golem, ring,
                e -> e instanceof LivingEntity living && living.isAlive() && !living.isSpectator());

        double radiusSq = IMPACT_RADIUS * IMPACT_RADIUS;
        for (int i = 0; i < hit.size(); i++) {
            Entity entity = hit.get(i);
            double rx = entity.getX() - ox;
            double rz = entity.getZ() - oz;
            double distSq = rx * rx + rz * rz;
            if (distSq > radiusSq) {
                continue;
            }

            // Full force at the golem's feet, tapering to a third at the rim.
            float falloff = 1.0F - (float) (Math.sqrt(distSq) / IMPACT_RADIUS) * 0.66F;
            entity.hurtServer(level, source, IMPACT_DAMAGE * falloff);
            if (entity instanceof LivingEntity living) {
                living.knockback(1.4 * falloff + 0.3, -rx, -rz, source,
                        IMPACT_DAMAGE * falloff, false);
            }
        }
    }

    @Override
    public void stop() {
        this.windup = 0;
    }
}

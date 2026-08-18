package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;

import java.util.EnumSet;

/**
 * The Echo Weaver's signature move: it spits a resonant snare at whatever it is hunting.
 *
 * <p>The weaver is fragile and fast, and it wants the player pinned underneath it rather than
 * chasing them. The snare therefore does almost no damage - it slows heavily and blinds briefly,
 * which buys the weaver the seconds it needs to close from a ceiling.
 *
 * <p>Like the golem's slam this is telegraphed: the weaver rears and its crests flare for
 * {@link #WINDUP_TICKS} before anything lands, so an attentive player can break line of sight.
 * The goal only touches its single target - there is no area query and no world scan.
 */
class EnsnareGoal extends Goal {
    /** The weaver will not bother spitting from further out than this. */
    private static final double RANGE = 10.0;

    /** Too close and it simply bites instead; the snare is for keeping distance honest. */
    private static final double MIN_RANGE = 2.5;

    private static final int WINDUP_TICKS = 16;
    private static final int COOLDOWN_TICKS = 140;
    private static final int SNARE_DURATION = 90;
    private static final float SNARE_DAMAGE = 1.0F;

    /**
     * Odds that a snare also blinds. Blinding on every hit is oppressive - against two weavers a
     * player never sees the fight at all - so the slow is the reliable part of the move and the
     * blind is an occasional punish you can ride out.
     */
    private static final float BLIND_CHANCE = 0.25F;

    /** Short enough to recover from, long enough to matter. */
    private static final int BLIND_DURATION = 30;

    private final EchoWeaverEntity weaver;
    private int windup;
    private int cooldown;

    EnsnareGoal(EchoWeaverEntity weaver) {
        this.weaver = weaver;
        this.setFlags(EnumSet.of(Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (this.cooldown > 0) {
            this.cooldown--;
            return false;
        }
        LivingEntity target = this.weaver.getTarget();
        if (target == null || !target.isAlive()) {
            return false;
        }
        double distSq = this.weaver.distanceToSqr(target);
        return distSq <= RANGE * RANGE
                && distSq >= MIN_RANGE * MIN_RANGE
                && this.weaver.getSensing().hasLineOfSight(target);
    }

    @Override
    public boolean canContinueToUse() {
        return this.windup > 0 && this.weaver.getTarget() != null;
    }

    @Override
    public void start() {
        this.windup = WINDUP_TICKS;
        if (this.weaver.level() instanceof ServerLevel level) {
            level.playSound(null, this.weaver.getX(), this.weaver.getY(), this.weaver.getZ(),
                    SoundEvents.SCULK_CLICKING, SoundSource.HOSTILE, 1.2F, 1.4F);
        }
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        LivingEntity target = this.weaver.getTarget();
        if (target == null) {
            return;
        }
        this.weaver.getLookControl().setLookAt(target, 30.0F, 30.0F);

        if (--this.windup > 0) {
            if (this.weaver.level() instanceof ServerLevel level) {
                // Crests flaring: the tell that a snare is coming.
                level.sendParticles(ParticleTypes.SCULK_CHARGE_POP,
                        this.weaver.getX(), this.weaver.getEyeY() + 0.3, this.weaver.getZ(),
                        2, 0.3, 0.2, 0.3, 0.01);
            }
            return;
        }

        this.fire(target);
        this.cooldown = COOLDOWN_TICKS;
    }

    /** Lands the snare on the one target, drawing the strand so the hit is legible. */
    private void fire(LivingEntity target) {
        if (!(this.weaver.level() instanceof ServerLevel level)) {
            return;
        }

        double sx = this.weaver.getX();
        double sy = this.weaver.getEyeY();
        double sz = this.weaver.getZ();
        double tx = target.getX();
        double ty = target.getY() + target.getBbHeight() * 0.5;
        double tz = target.getZ();

        // A strand of motes from the weaver to the target, so the player can see who hit them.
        for (int i = 0; i <= 12; i++) {
            double t = i / 12.0;
            level.sendParticles(ParticleTypes.SCULK_SOUL,
                    sx + (tx - sx) * t, sy + (ty - sy) * t, sz + (tz - sz) * t,
                    1, 0.02, 0.02, 0.02, 0.0);
        }

        level.playSound(null, tx, ty, tz, SoundEvents.SCULK_SHRIEKER_SHRIEK,
                SoundSource.HOSTILE, 0.9F, 1.6F);

        target.hurtServer(level, this.weaver.damageSources().mobAttack(this.weaver), SNARE_DAMAGE);
        target.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, SNARE_DURATION, 2), this.weaver);
        if (this.weaver.getRandom().nextFloat() < BLIND_CHANCE) {
            target.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, BLIND_DURATION, 0), this.weaver);
        }
    }

    @Override
    public void stop() {
        this.windup = 0;
    }
}

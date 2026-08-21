package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.phys.Vec3;

import java.util.EnumSet;

/**
 * The Tuner Shade's ranged attack, and the footwork that goes with it.
 *
 * <p>The shade holds a band: it walks in when the target drifts past {@value #IDEAL_MAX} blocks and
 * backs off inside {@value #IDEAL_MIN}, and stands still in between so the cast can land. Movement
 * is re-pathed on a {@value #PATH_INTERVAL}-tick timer rather than every tick, because a caster
 * that re-plans its route sixty times a second reads as jittery and costs far more than it buys.
 *
 * <p>The cast is telegraphed the same way everything else in this dimension is: {@value #CAST_TICKS}
 * ticks of the resonator ring winding up, a rising tone, and a tightening ring of motes at the
 * shade's chest. Breaking line of sight during the wind-up drops the whole charge. When it does
 * release, the bolt is aimed at where the target is standing at that instant and travels, so
 * sidestepping after the release is also a clean dodge.
 *
 * <p>Only one bolt is ever in the air. That is what keeps a pair of shades survivable: they have to
 * take turns, and the gaps are where the player closes the distance.
 */
class ResonanceBoltGoal<T extends net.minecraft.world.entity.Mob & BoltCaster> extends Goal {
    /** Closer than this and the shade gives ground instead of casting. */
    private static final double IDEAL_MIN = 6.0;

    /** Further than this and it closes; a bolt fired from the edge of render distance is wasted. */
    private static final double IDEAL_MAX = 15.0;

    /** Hard cut-off: past here the shade stops trying to fight at all. */
    private static final double GIVE_UP_RANGE = 30.0;

    private static final int PATH_INTERVAL = 12;
    private static final int CAST_TICKS = 26;
    private static final int CAST_COOLDOWN = 45;

    private final T shade;
    private int repath;
    private int cooldown;
    private int charge;

    ResonanceBoltGoal(T shade) {
        this.shade = shade;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        LivingEntity target = this.shade.getTarget();
        return target != null
                && target.isAlive()
                && this.shade.distanceToSqr(target) <= GIVE_UP_RANGE * GIVE_UP_RANGE;
    }

    @Override
    public boolean canContinueToUse() {
        return this.canUse();
    }

    @Override
    public void start() {
        // Half a cooldown on engage, so a shade that has just noticed you does not open with a
        // bolt before you have seen it.
        this.cooldown = CAST_COOLDOWN / 2;
        this.charge = 0;
        this.repath = 0;
    }

    @Override
    public void stop() {
        this.charge = 0;
        this.shade.getNavigation().stop();
        this.shade.setAggressive(false);
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        LivingEntity target = this.shade.getTarget();
        if (target == null) {
            return;
        }

        this.shade.getLookControl().setLookAt(target, 30.0F, 30.0F);
        this.holdRange(target);

        if (this.cooldown > 0) {
            this.cooldown--;
            return;
        }
        if (this.shade.hasBoltInFlight()) {
            return;
        }

        boolean canSee = this.shade.getSensing().hasLineOfSight(target);
        if (!canSee) {
            this.charge = 0;
            this.shade.setAggressive(false);
            return;
        }

        this.shade.setAggressive(true);
        if (++this.charge < CAST_TICKS) {
            if (this.shade.level() instanceof ServerLevel level) {
                this.castTell(level);
            }
            return;
        }

        this.charge = 0;
        this.cooldown = CAST_COOLDOWN;
        if (this.shade.level() instanceof ServerLevel level) {
            this.shade.fireBolt(level, target);
        }
    }

    /** Walk in, back off, or stand still - whichever keeps the target inside the casting band. */
    private void holdRange(LivingEntity target) {
        if (--this.repath > 0) {
            return;
        }

        this.repath = this.adjustedTickDelay(PATH_INTERVAL);
        double distSq = this.shade.distanceToSqr(target);

        if (distSq > IDEAL_MAX * IDEAL_MAX) {
            this.shade.getNavigation().moveTo(target, 1.0);
            return;
        }

        if (distSq < IDEAL_MIN * IDEAL_MIN) {
            // Give ground along the line away from the target. Short steps: this is spacing, and
            // the blink is what handles anything that actually gets close.
            double dx = this.shade.getX() - target.getX();
            double dz = this.shade.getZ() - target.getZ();
            double length = Math.sqrt(dx * dx + dz * dz);
            if (length > 1.0E-4) {
                this.shade.getNavigation().moveTo(
                        this.shade.getX() + dx / length * 4.0,
                        this.shade.getY(),
                        this.shade.getZ() + dz / length * 4.0,
                        1.1);
            }
            return;
        }

        this.shade.getNavigation().stop();
    }

    /** The wind-up: a ring of motes contracting into the resonator, on a tone that climbs with it. */
    private void castTell(ServerLevel level) {
        Vec3 ring = this.shade.resonatorPosition();
        double progress = (double) this.charge / CAST_TICKS;
        double radius = 1.6 * (1.0 - progress) + 0.25;

        for (int i = 0; i < 8; i++) {
            double angle = i * (Math.PI * 2.0 / 8.0) + progress * 4.0;
            level.sendParticles(ParticleTypes.SCULK_SOUL,
                    ring.x + Math.cos(angle) * radius,
                    ring.y + Math.sin(angle * 2.0) * radius * 0.4,
                    ring.z + Math.sin(angle) * radius,
                    1, 0.0, 0.0, 0.0, 0.0);
        }

        if (this.charge % 6 == 0) {
            level.playSound(null, ring.x, ring.y, ring.z, SoundEvents.WARDEN_SONIC_CHARGE,
                    SoundSource.HOSTILE, 0.45F, 1.1F + (float) progress * 0.8F);
        }
    }
}

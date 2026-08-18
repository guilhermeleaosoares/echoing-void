package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;

import java.util.EnumSet;

/**
 * What the Echo Weaver does when it is losing: it goes up.
 *
 * <p>The weaver is built to attack from overhead and it is fragile, so a wounded one breaking off
 * and climbing out of reach is the behaviour the animal already implies. Below
 * {@value #RETREAT_HEALTH_FRACTION} of its health it stops fighting entirely, finds a ceiling near
 * where it is standing, clings there, and knits itself back together at
 * {@value #HEAL_PER_INTERVAL} health every {@value #HEAL_INTERVAL} ticks. Once it is back above
 * {@value #RECOVER_HEALTH_FRACTION} it drops on whoever is underneath.
 *
 * <p>That gives the fight a shape it did not have. A player who chips at a weaver and then backs off
 * to heal comes back to a weaver at full health on the roof; a player who commits and kills it while
 * it is climbing never sees the second half of the fight. The retreat is loud, slow and visible -
 * the weaver has to cross open ground to reach a wall - so the window to punish it is real.
 *
 * <p>Ceiling candidates go through {@link EchoWeaverEntity#hasCeilingAnchor}, so the probes share
 * the weaver's existing cache with its ambush goal and a wounded weaver circling the same room
 * re-tests almost nothing.
 */
class CeilingRetreatGoal extends Goal {
    /** Below this fraction of max health the weaver breaks off. */
    private static final float RETREAT_HEALTH_FRACTION = 0.35F;

    /** Above this fraction it comes back down. Deliberately well short of full. */
    private static final float RECOVER_HEALTH_FRACTION = 0.7F;

    /** Hard cap on time spent hiding, so a weaver that cannot find a roof is not stuck forever. */
    private static final int MAX_RETREAT_TICKS = 400;

    /**
     * How long a weaver that spent the whole window without reaching a ceiling gives up for.
     *
     * <p>The trigger is a health threshold, so without a lockout a wounded weaver in open terrain
     * would run out the timer, re-qualify on the very next tick and never fight again. With it, a
     * weaver that has nowhere to hide turns and finishes the fight on the floor.
     */
    private static final int GIVE_UP_LOCKOUT = 300;

    private static final int HEAL_INTERVAL = 10;
    private static final float HEAL_PER_INTERVAL = 0.5F;

    private static final int REPATH_INTERVAL = 20;

    /** Interleaved x/z offsets searched around the weaver's own column, nearest first. */
    private static final int[] OFFSETS = {
            0, 0, 2, 0, -2, 0, 0, 2, 0, -2,
            3, 3, -3, 3, 3, -3, -3, -3,
            6, 0, -6, 0, 0, 6, 0, -6,
    };

    private final EchoWeaverEntity weaver;
    private final double speedModifier;

    private int nextProbe;
    private int elapsed;
    private int healTimer;
    private int lockout;

    CeilingRetreatGoal(EchoWeaverEntity weaver, double speedModifier) {
        this.weaver = weaver;
        this.speedModifier = speedModifier;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (this.lockout > 0) {
            this.lockout--;
            return false;
        }

        return this.weaver.getHealth() < this.weaver.getMaxHealth() * RETREAT_HEALTH_FRACTION;
    }

    @Override
    public boolean canContinueToUse() {
        return this.elapsed < MAX_RETREAT_TICKS
                && this.weaver.getHealth() < this.weaver.getMaxHealth() * RECOVER_HEALTH_FRACTION;
    }

    @Override
    public void start() {
        this.nextProbe = 0;
        this.elapsed = 0;
        this.healTimer = 0;
        this.weaver.setRetreating(true);

        if (this.weaver.level() instanceof ServerLevel level) {
            level.playSound(null, this.weaver.getX(), this.weaver.getY(), this.weaver.getZ(),
                    SoundEvents.SCULK_SHRIEKER_SHRIEK, SoundSource.HOSTILE, 1.1F, 1.7F);
        }
    }

    @Override
    public void stop() {
        // Only the timeout locks it out. A weaver that stopped because it healed past the recovery
        // threshold has done what the goal is for and should be free to use it again.
        this.lockout = this.elapsed >= MAX_RETREAT_TICKS ? GIVE_UP_LOCKOUT : 0;
        this.weaver.setRetreating(false);
        this.weaver.getNavigation().stop();
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        this.elapsed++;

        // Keep facing whatever it ran from. A weaver hanging with its back turned looks broken, and
        // the player needs to be able to see it watching them.
        LivingEntity target = this.weaver.getTarget();
        if (target != null) {
            this.weaver.getLookControl().setLookAt(target, 30.0F, 30.0F);
        }

        if (this.weaver.onClimbable()) {
            this.hangAndKnit();
            return;
        }

        if (--this.nextProbe > 0) {
            return;
        }

        this.nextProbe = this.adjustedTickDelay(REPATH_INTERVAL);
        int baseX = this.weaver.getBlockX();
        int baseY = this.weaver.getBlockY();
        int baseZ = this.weaver.getBlockZ();
        for (int i = 0; i < OFFSETS.length; i += 2) {
            int x = baseX + OFFSETS[i];
            int z = baseZ + OFFSETS[i + 1];
            if (this.weaver.hasCeilingAnchor(x, baseY, z)) {
                this.weaver.getNavigation().moveTo(x + 0.5, baseY, z + 0.5, this.speedModifier);
                return;
            }
        }
    }

    /** On the wall: stop moving, hold on, and repair. */
    private void hangAndKnit() {
        this.weaver.getNavigation().stop();

        if (++this.healTimer < HEAL_INTERVAL) {
            return;
        }

        this.healTimer = 0;
        this.weaver.heal(HEAL_PER_INTERVAL);
        if (this.weaver.level() instanceof ServerLevel level) {
            // Strands being spun back over the wound; the same motes the snare is drawn with, so it
            // reads as the weaver's own material rather than as a generic heal effect.
            level.sendParticles(ParticleTypes.SCULK_SOUL,
                    this.weaver.getX(), this.weaver.getY(0.6), this.weaver.getZ(),
                    3, 0.4, 0.3, 0.4, 0.01);
        }
    }
}

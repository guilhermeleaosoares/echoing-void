package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.FlyingMoveControl;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomFlyingGoal;
import net.minecraft.world.entity.ai.navigation.FlyingPathNavigation;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.EnumSet;
import java.util.List;

/**
 * The one thing in the Hollow Horizon that is not trying to kill you.
 *
 * <p>A chime mote is a drifting lantern-creature: neutral, fragile, and entirely passive. It exists
 * so the dimension has ambient life in it, and so a player crossing an empty chasm has something to
 * look at that is not a threat.
 *
 * <p>It has one behaviour a player can learn. A mote can hear a Tuning Fork, and a player carrying
 * one in either hand collects a small escort of them - see {@link AttuneToForkGoal}. Put the fork
 * away and they wander off again. That is the whole contract, and it is deliberately free: the
 * escort costs nothing and gives nothing but light and company.
 *
 * <p>The second behaviour is the cost of breaking it. Hitting a mote startles the whole cloud: the
 * struck mote calls, every mote inside {@value #ALARM_RADIUS} blocks scatters for
 * {@value #STARTLE_TICKS} ticks, and none of them will attune while they are frightened. The alarm
 * is one bounded {@code getEntitiesOfClass} on the tick the blow lands, never a per-tick scan.
 */
public class ChimeMoteEntity extends PathfinderMob {
    /** How far a struck mote's alarm carries, in blocks. */
    private static final double ALARM_RADIUS = 12.0;

    /** How long a startled mote refuses to settle or follow. */
    private static final int STARTLE_TICKS = 120;

    /** Amplitude in blocks per tick of the idle vertical drift. */
    private static final double BOB_STRENGTH = 0.004;

    /** Radians per tick of the bob cycle. */
    private static final float BOB_RATE = 0.11F;

    /**
     * Ticks remaining on the scatter response. Server-only: the client never needs to know, because
     * the behaviour it drives is movement, which is already replicated.
     */
    private int startled;

    public ChimeMoteEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        // hoversInPlace: a mote with nowhere to be must hang, not sink.
        this.moveControl = new FlyingMoveControl<ChimeMoteEntity>(this, 20, true);
        this.xpReward = 1;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return PathfinderMob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 6.0)
                .add(Attributes.MOVEMENT_SPEED, 0.2)
                .add(Attributes.FLYING_SPEED, 0.5)
                .add(Attributes.FOLLOW_RANGE, 20.0);
    }

    @Override
    protected void registerGoals() {
        // Scatter outranks everything: a frightened mote does not follow anyone.
        this.goalSelector.addGoal(1, new ChimeMoteEntity.ScatterGoal(this));
        this.goalSelector.addGoal(2, new AttuneToForkGoal(this));
        this.goalSelector.addGoal(5, new WaterAvoidingRandomFlyingGoal(this, 1.0));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
        // No target selector at all. The mote never acquires a target, so nothing it does can
        // escalate into a fight, however hard it is provoked.
    }

    @Override
    protected PathNavigation createNavigation(Level level) {
        FlyingPathNavigation navigation = new FlyingPathNavigation(this, level);
        navigation.setCanOpenDoors(false);
        navigation.setCanFloat(true);
        return navigation;
    }

    @Override
    public void tick() {
        // Reasserted every tick: the move control clears it whenever it has no destination.
        this.setNoGravity(true);
        super.tick();
    }

    @Override
    public void aiStep() {
        super.aiStep();
        if (this.level().isClientSide()) {
            return;
        }

        if (this.startled > 0) {
            this.startled--;
        }

        // Offset by entity id so a cloud of motes does not bob in lockstep.
        float phase = (this.tickCount + this.getId() * 7) * BOB_RATE;
        Vec3 movement = this.getDeltaMovement();
        this.setDeltaMovement(movement.x, movement.y + Mth.sin(phase) * BOB_STRENGTH, movement.z);

        // A slow drip of light, so a mote is visible before it is in render range of its own model.
        if (this.tickCount % 6 == 0 && this.level() instanceof ServerLevel level) {
            level.sendParticles(ParticleTypes.END_ROD,
                    this.getX(), this.getY(0.5), this.getZ(), 1, 0.1, 0.1, 0.1, 0.0);
        }
    }

    /** Whether the mote is currently fleeing rather than drifting or following. */
    public boolean isStartled() {
        return this.startled > 0;
    }

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
        boolean hurt = super.hurtServer(level, source, damage);
        if (hurt) {
            this.raiseAlarm(level);
        }

        return hurt;
    }

    /**
     * Startles this mote and every other one nearby.
     *
     * <p>One bounded query over a box the size of the alarm, run only on the tick something
     * actually landed a hit. The point of the alarm is that a player who swats one mote loses the
     * whole cloud, which is the only consequence the creature has and so has to be visible.
     */
    private void raiseAlarm(ServerLevel level) {
        this.startled = STARTLE_TICKS;

        AABB earshot = this.getBoundingBox().inflate(ALARM_RADIUS);
        List<ChimeMoteEntity> heard = level.getEntitiesOfClass(ChimeMoteEntity.class, earshot,
                mote -> mote != this && mote.isAlive() && !mote.isStartled());
        for (int i = 0; i < heard.size(); i++) {
            heard.get(i).startled = STARTLE_TICKS;
        }

        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.NEUTRAL, 1.4F, 1.9F);
        level.sendParticles(ParticleTypes.END_ROD,
                this.getX(), this.getY(0.5), this.getZ(), 12, 0.3, 0.3, 0.3, 0.06);
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean causeFallDamage(double distance, float multiplier, DamageSource source) {
        return false;
    }

    @Override
    public int getAmbientSoundInterval() {
        return 160;
    }

    @Override
    protected SoundEvent getAmbientSound() {
        return SoundEvents.AMETHYST_BLOCK_CHIME;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.AMETHYST_CLUSTER_BREAK;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.AMETHYST_CLUSTER_BREAK;
    }

    @Override
    protected float getSoundVolume() {
        return 0.25F;
    }

    /**
     * The flight response: put distance between the mote and whatever frightened it.
     *
     * <p>There is no pathfinding here on purpose. A mote that has been hit should leave immediately
     * and in a straight line rather than spend a tick asking the navigator for a route, so this
     * steers the flying move control directly, away from the nearest player and slightly upward -
     * up is where a lantern goes, and it is also out of melee reach.
     */
    private static class ScatterGoal extends Goal {
        /** How far ahead the mote aims when fleeing. Re-aimed continuously as it moves. */
        private static final double FLEE_DISTANCE = 8.0;

        /** The mote only bothers avoiding a player it can actually see coming. */
        private static final double THREAT_RANGE = 16.0;

        private final ChimeMoteEntity mote;

        ScatterGoal(ChimeMoteEntity mote) {
            this.mote = mote;
            this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
        }

        @Override
        public boolean canUse() {
            return this.mote.isStartled();
        }

        @Override
        public boolean canContinueToUse() {
            return this.mote.isStartled();
        }

        @Override
        public void stop() {
            this.mote.getNavigation().stop();
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void tick() {
            Player threat = this.mote.level().getNearestPlayer(this.mote, THREAT_RANGE);
            double dx;
            double dz;
            if (threat != null) {
                dx = this.mote.getX() - threat.getX();
                dz = this.mote.getZ() - threat.getZ();
            } else {
                // Nothing in sight any more; keep drifting the way it was already going so the
                // cloud disperses instead of hanging in place waiting out the timer.
                Vec3 movement = this.mote.getDeltaMovement();
                dx = movement.x;
                dz = movement.z;
            }

            double length = Math.sqrt(dx * dx + dz * dz);
            if (length < 1.0E-4) {
                // Directly overhead, or standing still: pick a direction off the entity id so a
                // cloud in this state fans out rather than all choosing the same escape.
                float angle = this.mote.getId() * 0.7F;
                dx = Mth.cos(angle);
                dz = Mth.sin(angle);
                length = 1.0;
            }

            this.mote.getMoveControl().setWantedPosition(
                    this.mote.getX() + dx / length * FLEE_DISTANCE,
                    this.mote.getY() + 2.5,
                    this.mote.getZ() + dz / length * FLEE_DISTANCE,
                    1.6);
        }
    }
}

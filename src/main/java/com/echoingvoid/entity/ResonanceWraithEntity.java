package com.echoingvoid.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.FlyingMoveControl;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomFlyingGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.ai.navigation.FlyingPathNavigation;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

import java.util.EnumSet;

/**
 * A drifting, incorporeal thing that attacks with sound rather than force.
 *
 * <p>The wraith ignores gravity and paths through open air, so terrain neither blocks it nor
 * shelters you: it comes over walls and down shafts in a straight line. It is correspondingly
 * fragile, with no armour and little health.
 *
 * <p>Its attack is a short-range resonant burst rather than a swing. The burst does modest damage
 * but leaves the victim slowed and momentarily deafened - darkness plus slowness - which is the
 * real threat, because it lands while other things in the dimension are still approaching. The
 * burst has its own cooldown, so a lone wraith is survivable and a pair is not.
 *
 * <p>It is also barely there. A landed hit knocks the wraith out of phase for
 * {@value #PHASE_TICKS} ticks: it stops being drawn, stops being hittable, and drifts away from
 * whatever struck it before snapping back into the world. That turns a fight against something with
 * sixteen health into a timing problem - swinging into a phased wraith is a wasted swing, and the
 * player has to wait for it to resolve before committing. The {@value #PHASE_COOLDOWN}-tick lockout
 * caps it at well under a third of the fight, so it can never become a stalemate.
 */
public class ResonanceWraithEntity extends Monster {
    /** Amplitude in blocks per tick of the idle vertical drift. */
    private static final double BOB_STRENGTH = 0.006;

    /** Radians per tick of the bob cycle; roughly one rise-and-fall every four seconds. */
    private static final float BOB_RATE = 0.08F;

    /** How long a wraith stays out of phase after being hit. */
    private static final int PHASE_TICKS = 30;

    /** Ticks before it can phase again, measured from the moment it phases out. */
    private static final int PHASE_COOLDOWN = 110;

    /** Blocks per tick it slides away from its attacker while phased. */
    private static final double PHASE_DRIFT = 0.16;

    private int phaseTicks;
    private int phaseCooldown;

    /** Unit vector away from whatever last hit it, held for the duration of the phase. */
    private double phaseDriftX;
    private double phaseDriftZ;

    public ResonanceWraithEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        // hoversInPlace: the wraith must not drop out of the air when it has nowhere to be.
        this.moveControl = new FlyingMoveControl<ResonanceWraithEntity>(this, 20, true);
        this.xpReward = 10;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 16.0)
                .add(Attributes.MOVEMENT_SPEED, 0.24)
                .add(Attributes.FLYING_SPEED, 0.6)
                .add(Attributes.ATTACK_DAMAGE, 3.0)
                .add(Attributes.FOLLOW_RANGE, 32.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(1, new ResonanceWraithEntity.ResonantBurstGoal(this));
        this.goalSelector.addGoal(5, new WaterAvoidingRandomFlyingGoal(this, 0.8));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 12.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    protected PathNavigation createNavigation(Level level) {
        FlyingPathNavigation navigation = new FlyingPathNavigation(this, level);
        navigation.setCanOpenDoors(false);
        navigation.setCanFloat(true);
        navigation.setRequiredPathLength(48.0F);
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

        // Offset by entity id so a group of wraiths does not bob in lockstep.
        float phase = (this.tickCount + this.getId() * 11) * BOB_RATE;
        Vec3 movement = this.getDeltaMovement();
        this.setDeltaMovement(movement.x, movement.y + Mth.sin(phase) * BOB_STRENGTH, movement.z);

        if (this.phaseCooldown > 0) {
            this.phaseCooldown--;
        }
        if (this.phaseTicks > 0) {
            this.tickPhase();
        }

        // Driven from the phase state every tick rather than set once at each end of it.
        // LivingEntity rewrites the invisibility flag from the effect list whenever effects change,
        // and the flag is not part of the entity's save data, so a wraith that was hit with a
        // potion mid-phase - or reloaded during one - would otherwise be stranded either visible or
        // permanently unseen.
        boolean hidden = this.phaseTicks > 0;
        if (this.isInvisible() != hidden) {
            this.setInvisible(hidden);
        }
    }

    /** Whether the wraith is currently out of phase, and so neither drawn nor hittable. */
    public boolean isPhased() {
        return this.phaseTicks > 0;
    }

    private void tickPhase() {
        // Drift, rather than teleport. The wraith reappears a couple of blocks off where it was
        // struck, which is enough to break a combo without making it impossible to follow.
        Vec3 movement = this.getDeltaMovement();
        this.setDeltaMovement(
                movement.x + this.phaseDriftX * PHASE_DRIFT,
                movement.y,
                movement.z + this.phaseDriftZ * PHASE_DRIFT);

        if (--this.phaseTicks > 0) {
            return;
        }

        if (this.level() instanceof ServerLevel level) {
            level.sendParticles(ParticleTypes.SCULK_SOUL,
                    this.getX(), this.getY(0.6), this.getZ(), 14, 0.5, 0.4, 0.5, 0.02);
            level.playSound(null, this.getX(), this.getY(), this.getZ(),
                    SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.HOSTILE, 1.0F, 0.7F);
        }
    }

    /**
     * Drops the wraith out of phase, sliding away from whatever hit it.
     *
     * <p>Announced at both ends: a ring of motes as it goes and another as it comes back, so a
     * player who has learnt the tell knows exactly how long their swing is going to be wasted for
     * and roughly where it is going to resolve.
     */
    private void beginPhase(ServerLevel level, Entity from) {
        this.phaseTicks = PHASE_TICKS;
        this.phaseCooldown = PHASE_COOLDOWN;
        this.setInvisible(true);

        double dx = from != null ? this.getX() - from.getX() : 0.0;
        double dz = from != null ? this.getZ() - from.getZ() : 0.0;
        double length = Math.sqrt(dx * dx + dz * dz);
        if (length < 1.0E-4) {
            // Nothing to run from, or it is standing inside the attacker: keep the heading it has.
            float yaw = this.getYRot() * ((float) Math.PI / 180.0F);
            this.phaseDriftX = -Mth.sin(yaw);
            this.phaseDriftZ = Mth.cos(yaw);
        } else {
            this.phaseDriftX = dx / length;
            this.phaseDriftZ = dz / length;
        }

        level.sendParticles(ParticleTypes.REVERSE_PORTAL,
                this.getX(), this.getY(0.6), this.getZ(), 20, 0.4, 0.5, 0.4, 0.04);
        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                SoundEvents.WARDEN_SONIC_CHARGE, SoundSource.HOSTILE, 0.9F, 2.0F);
    }

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
        // Out of phase there is nothing in that space to hit. Only /kill and the void get through,
        // so the state can never leave a wraith unkillable.
        if (this.isPhased()
                && !source.is(DamageTypeTags.BYPASSES_INVULNERABILITY)
                && !source.isCreativePlayer()) {
            return false;
        }

        boolean hurt = super.hurtServer(level, source, damage);
        if (hurt && this.isAlive() && this.phaseCooldown <= 0) {
            this.beginPhase(level, source.getEntity());
        }

        return hurt;
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
    protected SoundEvent getAmbientSound() {
        return SoundEvents.AMBIENT_CAVE.value();
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.ALLAY_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.ALLAY_DEATH;
    }

    /**
     * Closes to burst range and fires a short resonant pulse on a cooldown.
     *
     * <p>Movement is driven through the flying move control directly rather than the path finder:
     * the wraith has nothing to path around, and steering straight at the target's eyes is both
     * cheaper and closer to how it should read.
     */
    private static class ResonantBurstGoal extends Goal {
        /** Squared distance inside which the burst can be fired. */
        private static final double BURST_RANGE_SQR = 16.0;

        /** Ticks between bursts. */
        /** Wind-up before a burst releases, in ticks. Long enough to break line of sight. */
        private static final int CHARGE_TICKS = 22;
        private static final int BURST_COOLDOWN = 70;

        /** Ticks of slowness and darkness applied on a hit. */
        private static final int DEAFEN_DURATION = 60;

        /** Odds a burst also blinds. Never guaranteed - see the balance rules in expansion.json. */
        private static final float DARKNESS_CHANCE = 0.33F;

        /** Short enough to fight through rather than be stunlocked by. */
        private static final int DARKNESS_DURATION = 30;

        private final ResonanceWraithEntity wraith;
        private int cooldown;
        /** Ticks of wind-up accumulated toward the current burst. */
        private int charge;

        ResonantBurstGoal(ResonanceWraithEntity wraith) {
            this.wraith = wraith;
            this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
        }

        @Override
        public boolean canUse() {
            LivingEntity target = this.wraith.getTarget();
            return target != null && target.isAlive();
        }

        @Override
        public boolean canContinueToUse() {
            return this.canUse();
        }

        @Override
        public void start() {
            this.cooldown = BURST_COOLDOWN / 2;
            this.charge = 0;
        }

        @Override
        public void stop() {
            this.wraith.setAggressive(false);
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void tick() {
            LivingEntity target = this.wraith.getTarget();
            if (target == null) {
                return;
            }

            if (this.wraith.isPhased()) {
                // Out of phase the wraith cannot act on the world at all. Dropping the charge here
                // rather than pausing it means a hit landed mid-wind-up genuinely interrupts the
                // burst, which is the only reward for hitting a wraith that is about to fire.
                this.charge = 0;
                return;
            }

            Vec3 eyes = target.getEyePosition();
            this.wraith.getLookControl().setLookAt(target, 30.0F, 30.0F);
            this.wraith.getMoveControl().setWantedPosition(eyes.x, eyes.y, eyes.z, 1.0);
            this.wraith.setAggressive(true);

            if (this.cooldown > 0) {
                this.cooldown--;
                return;
            }

            boolean inRange = this.wraith.distanceToSqr(target) <= BURST_RANGE_SQR
                    && this.wraith.getSensing().hasLineOfSight(target);
            if (!inRange) {
                // Losing the target mid-charge drops the charge; the wraith has to start again.
                this.charge = 0;
                return;
            }

            // The burst is charged, not instant. The player gets CHARGE_TICKS of a rising tone
            // and a tightening ring of motes before anything lands, which is the difference
            // between a readable attack and being hit by a debuff out of nowhere.
            if (++this.charge < CHARGE_TICKS) {
                this.chargeTell(getServerLevel(this.wraith.level()));
                return;
            }

            this.burst(getServerLevel(this.wraith.level()), target);
            this.charge = 0;
            this.cooldown = BURST_COOLDOWN;
        }

        /** A ring of motes contracting toward the core, plus a tone that climbs with the charge. */
        private void chargeTell(ServerLevel level) {
            double progress = (double) this.charge / CHARGE_TICKS;
            double radius = 2.4 * (1.0 - progress) + 0.35;
            double cx = this.wraith.getX();
            double cy = this.wraith.getY(0.6);
            double cz = this.wraith.getZ();

            for (int i = 0; i < 10; i++) {
                double angle = i * (Math.PI * 2.0 / 10.0) + progress * 3.0;
                level.sendParticles(ParticleTypes.SCULK_SOUL,
                        cx + Math.cos(angle) * radius, cy, cz + Math.sin(angle) * radius,
                        1, 0.0, 0.0, 0.0, 0.0);
            }

            if (this.charge % 5 == 0) {
                level.playSound(null, cx, cy, cz, SoundEvents.WARDEN_SONIC_CHARGE,
                        SoundSource.HOSTILE, 0.5F, 0.8F + (float) progress * 0.9F);
            }
        }

        private void burst(ServerLevel level, LivingEntity target) {
            float damage = (float) this.wraith.getAttributeValue(Attributes.ATTACK_DAMAGE);
            if (target.hurtServer(level, this.wraith.damageSources().mobAttack(this.wraith), damage)) {
                // The slow is the reliable half of the move - it is what the charge-up telegraphs
                // and what the player plays around. Blinding on every burst is not a difficulty
                // curve, it is just not being able to see the fight, so the darkness is an
                // occasional punish and it is short.
                target.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, DEAFEN_DURATION, 1), this.wraith);
                if (this.wraith.getRandom().nextFloat() < DARKNESS_CHANCE) {
                    target.addEffect(new MobEffectInstance(MobEffects.DARKNESS, DARKNESS_DURATION, 0), this.wraith);
                }
            }

            level.playSound(null, this.wraith.getX(), this.wraith.getY(), this.wraith.getZ(),
                    SoundEvents.WARDEN_SONIC_BOOM, SoundSource.HOSTILE, 1.4F, 1.2F);

            // An expanding ring, drawn in three shells so it reads as a wave leaving the core
            // rather than as a single burst of dust.
            double cx = this.wraith.getX();
            double cy = this.wraith.getY(0.6);
            double cz = this.wraith.getZ();
            for (int shell = 1; shell <= 3; shell++) {
                double radius = shell * 1.1;
                int points = 12 + shell * 6;
                for (int i = 0; i < points; i++) {
                    double angle = i * (Math.PI * 2.0 / points);
                    level.sendParticles(ParticleTypes.SONIC_BOOM,
                            cx + Math.cos(angle) * radius, cy, cz + Math.sin(angle) * radius,
                            1, 0.0, 0.0, 0.0, 0.0);
                }
            }
        }
    }
}

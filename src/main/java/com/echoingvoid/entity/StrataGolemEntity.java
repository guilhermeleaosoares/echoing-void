package com.echoingvoid.entity;

import com.echoingvoid.registry.ModItems;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import net.minecraft.core.BlockPos;

/**
 * A slow, heavy, territorial guardian built out of the strata it sleeps in.
 *
 * <p>The golem trades mobility for staying power: it has far more health and armour than anything
 * else in the dimension, shrugs off knockback, and hits very hard on a long swing timer. Fighting
 * it is a question of whether you can out-last the wind-up, not whether you can out-damage it.
 *
 * <p>Its back carries three crystal spire clusters. A heavy blow knocks one off: the golem drops a
 * resonance shard, loses part of its armour and damage, and speeds up slightly. So the fight gets
 * faster and cheaper the longer it runs, and stripping all three is the visible progress bar. The
 * remaining count is synched so the renderer can hide the shed clusters.
 *
 * <p>At half health it turns. The golem roars, gains most of the pace it never had, hits hard enough
 * to shove, and slams on a much shorter cooldown - see {@link #enrage}. The change is permanent and
 * it is loud, so the player gets a clear warning that the tactic that carried the first half of the
 * fight is about to stop working.
 */
public class StrataGolemEntity extends Monster {
    private static final EntityDataAccessor<Integer> DATA_SPIRE_CLUSTERS =
            SynchedEntityData.defineId(StrataGolemEntity.class, EntityDataSerializers.INT);

    /** Synched so the client can see the state the golem is in without inferring it from health. */
    private static final EntityDataAccessor<Boolean> DATA_ENRAGED =
            SynchedEntityData.defineId(StrataGolemEntity.class, EntityDataSerializers.BOOLEAN);

    /** Clusters present on a fresh golem. The model has one bone group per cluster. */
    public static final int MAX_SPIRE_CLUSTERS = 3;

    /** Incoming damage (pre-armour) that counts as a "heavy blow" and shears a cluster off. */
    private static final float SHED_DAMAGE_THRESHOLD = 6.0F;

    /** Ticks between swings with all clusters intact. */
    private static final int BASE_ATTACK_INTERVAL = 44;

    /** Ticks shaved off the swing timer per cluster already lost. */
    private static final int ATTACK_INTERVAL_PER_CLUSTER = 7;

    private static final double SPEED_GAIN_PER_CLUSTER = 0.02;
    private static final double DAMAGE_LOSS_PER_CLUSTER = 3.0;
    private static final double ARMOR_LOSS_PER_CLUSTER = 2.0;

    /** Fraction of max health at which the golem stops being a wall and starts being a threat. */
    private static final float RAGE_HEALTH_FRACTION = 0.5F;

    /** One-off attribute gains at the rage threshold. */
    private static final double RAGE_SPEED_GAIN = 0.09;
    private static final double RAGE_KNOCKBACK_GAIN = 0.7;

    /** Ticks shaved off the swing timer while enraged, on top of the per-cluster reduction. */
    private static final int RAGE_ATTACK_INTERVAL_BONUS = 8;

    /** Fraction of its slam cooldown an enraged golem pays. */
    public static final float RAGE_SLAM_COOLDOWN_SCALE = 0.6F;

    private static final String TAG_SPIRE_CLUSTERS = "spire_clusters";
    private static final String TAG_ENRAGED = "enraged";

    public StrataGolemEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 20;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 140.0)
                .add(Attributes.MOVEMENT_SPEED, 0.17)
                .add(Attributes.ATTACK_DAMAGE, 16.0)
                .add(Attributes.ATTACK_KNOCKBACK, 1.5)
                .add(Attributes.ARMOR, 14.0)
                .add(Attributes.ARMOR_TOUGHNESS, 4.0)
                .add(Attributes.KNOCKBACK_RESISTANCE, 0.9)
                .add(Attributes.FOLLOW_RANGE, 24.0)
                .add(Attributes.STEP_HEIGHT, 1.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(1, new FloatGoal(this));
        this.goalSelector.addGoal(2, new GroundSlamGoal(this));
        this.goalSelector.addGoal(3, new StrataGolemEntity.SlamAttackGoal(this));
        this.goalSelector.addGoal(5, new WaterAvoidingRandomStrollGoal(this, 0.6));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 10.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder entityData) {
        super.defineSynchedData(entityData);
        entityData.define(DATA_SPIRE_CLUSTERS, MAX_SPIRE_CLUSTERS);
        entityData.define(DATA_ENRAGED, false);
    }

    /**
     * Whether the golem has crossed its rage threshold.
     *
     * <p>One-way: a golem that has been pushed past half health does not calm down again, however
     * long the player disengages for. The second half of the fight is a different fight.
     */
    public boolean isEnraged() {
        return this.entityData.get(DATA_ENRAGED);
    }

    /** How many crystal spire clusters are still attached, from {@value #MAX_SPIRE_CLUSTERS} down to 0. */
    public int getSpireClusters() {
        return this.entityData.get(DATA_SPIRE_CLUSTERS);
    }

    public void setSpireClusters(int clusters) {
        this.entityData.set(DATA_SPIRE_CLUSTERS, Math.clamp(clusters, 0, MAX_SPIRE_CLUSTERS));
    }

    /** Swing interval in ticks, shortening as the golem sheds weight and again once it is enraged. */
    public int getAttackIntervalTicks() {
        int lost = MAX_SPIRE_CLUSTERS - this.getSpireClusters();
        int interval = BASE_ATTACK_INTERVAL - lost * ATTACK_INTERVAL_PER_CLUSTER;
        return this.isEnraged() ? interval - RAGE_ATTACK_INTERVAL_BONUS : interval;
    }

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
        boolean hurt = super.hurtServer(level, source, damage);
        if (!hurt || !this.isAlive()) {
            return hurt;
        }

        // Measured on the incoming figure rather than the post-armour one, so the trigger is "that
        // was a real hit" from the attacker's point of view and does not drift as armour is lost.
        if (damage >= SHED_DAMAGE_THRESHOLD && this.getSpireClusters() > 0) {
            this.shedSpireCluster(level);
        }

        // Checked after the shed, so the blow that takes the last cluster can also be the blow that
        // tips it over the threshold.
        if (!this.isEnraged() && this.getHealth() < this.getMaxHealth() * RAGE_HEALTH_FRACTION) {
            this.enrage(level);
        }

        return hurt;
    }

    /**
     * The second half of the golem fight.
     *
     * <p>Everything the first half taught the player stops being true. It moves at close to walking
     * pace instead of a shuffle, swings appreciably faster, and hits hard enough to move you, so
     * out-lasting the wind-up by backing off - which is the whole answer to a fresh golem - no
     * longer works on its own. The slam cooldown drops too; see {@link GroundSlamGoal}.
     *
     * <p>It is announced properly. A golem crossing the threshold roars, throws its crystal light
     * out in a ring, and stays visibly lit from then on, because a boss-weight creature changing its
     * rules silently is how a fight becomes unfair rather than harder.
     */
    private void enrage(ServerLevel level) {
        this.entityData.set(DATA_ENRAGED, true);
        adjustBase(this.getAttribute(Attributes.MOVEMENT_SPEED), RAGE_SPEED_GAIN, 0.0, 0.4);
        adjustBase(this.getAttribute(Attributes.ATTACK_KNOCKBACK), RAGE_KNOCKBACK_GAIN, 0.0, 5.0);

        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                SoundEvents.WARDEN_ROAR, SoundSource.HOSTILE, 2.0F, 0.55F);
        level.sendParticles(ParticleTypes.SONIC_BOOM,
                this.getX(), this.getY(0.8), this.getZ(), 1, 0.0, 0.0, 0.0, 0.0);
        for (int step = 0; step < 32; step++) {
            double angle = step * (Math.PI * 2.0 / 32.0);
            level.sendParticles(ParticleTypes.CRIT,
                    this.getX() + Math.cos(angle) * 2.2,
                    this.getY(0.5),
                    this.getZ() + Math.sin(angle) * 2.2,
                    2, 0.05, 0.4, 0.05, 0.08);
        }
    }

    /**
     * Knocks one cluster off: drops a shard, and rebalances the golem towards fast-and-brittle.
     */
    private void shedSpireCluster(ServerLevel level) {
        this.setSpireClusters(this.getSpireClusters() - 1);

        this.spawnAtLocation(level, ModItems.RESONANCE_SHARD.get());
        adjustBase(this.getAttribute(Attributes.MOVEMENT_SPEED), SPEED_GAIN_PER_CLUSTER, 0.0, 0.4);
        adjustBase(this.getAttribute(Attributes.ATTACK_DAMAGE), -DAMAGE_LOSS_PER_CLUSTER, 3.0, 64.0);
        adjustBase(this.getAttribute(Attributes.ARMOR), -ARMOR_LOSS_PER_CLUSTER, 0.0, 30.0);

        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.HOSTILE, 1.2F, 0.7F);
        level.sendParticles(ParticleTypes.CRIT,
                this.getX(), this.getY(0.75), this.getZ(),
                18, 0.4, 0.3, 0.4, 0.05);
    }

    private static void adjustBase(AttributeInstance attribute, double delta, double min, double max) {
        if (attribute != null) {
            attribute.setBaseValue(Math.clamp(attribute.getBaseValue() + delta, min, max));
        }
    }

    @Override
    protected void addAdditionalSaveData(ValueOutput output) {
        super.addAdditionalSaveData(output);
        output.putInt(TAG_SPIRE_CLUSTERS, this.getSpireClusters());
        output.putBoolean(TAG_ENRAGED, this.isEnraged());
    }

    @Override
    protected void readAdditionalSaveData(ValueInput input) {
        super.readAdditionalSaveData(input);
        this.setSpireClusters(input.getIntOr(TAG_SPIRE_CLUSTERS, MAX_SPIRE_CLUSTERS));
        // The attribute gains are saved with the entity's own attribute data, so only the flag has
        // to be restored here - re-applying them would stack them on every reload.
        this.entityData.set(DATA_ENRAGED, input.getBooleanOr(TAG_ENRAGED, false));
    }

    @Override
    public int getAmbientSoundInterval() {
        // It is meant to read as dormant rock; a chime every ten seconds or so is plenty.
        return 200;
    }

    @Override
    protected SoundEvent getAmbientSound() {
        return SoundEvents.AMETHYST_BLOCK_RESONATE;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.IRON_GOLEM_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.IRON_GOLEM_DEATH;
    }

    @Override
    protected void playStepSound(BlockPos pos, BlockState state) {
        this.playSound(SoundEvents.DEEPSLATE_STEP, 1.0F, 0.6F);
    }

    /**
     * Melee on the golem's own timer.
     *
     * <p>{@link MeleeAttackGoal} keeps its cooldown private and fixed at one second, which is far
     * too fast for this creature, so the swing gate is re-imposed here on top of the vanilla one.
     */
    private static class SlamAttackGoal extends MeleeAttackGoal {
        private final StrataGolemEntity golem;
        private int cooldown;

        SlamAttackGoal(StrataGolemEntity golem) {
            super(golem, 1.0, true);
            this.golem = golem;
        }

        @Override
        public void start() {
            super.start();
            this.cooldown = 0;
        }

        @Override
        protected void checkAndPerformAttack(LivingEntity target) {
            if (this.cooldown > 0) {
                this.cooldown--;
                return;
            }

            // Only spend the cooldown on a swing that actually lands the attempt.
            if (this.canPerformAttack(target)) {
                super.checkAndPerformAttack(target);
                this.cooldown = this.golem.getAttackIntervalTicks();
            }
        }
    }
}

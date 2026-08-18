package com.echoingvoid.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
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
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * An armoured digger that fights from underneath the floor.
 *
 * <p>The burrower is the dimension's answer to standing still. It dives into the rock when it is
 * hurt or when its quarry is too far off to charge, travels underground where nothing can touch it,
 * and comes up somewhere the player is not looking - by preference directly behind them. Surfacing
 * is an attack in itself: the eruption throws everything around it into the air.
 *
 * <p>The counterplay is entirely about the ground. The creature itself is not drawn while it is
 * under the floor, but it is never hidden: it throws up a continuous plume of the rock it is chewing
 * through, at the surface directly above itself, and the plume tracks it exactly. A player watching
 * the floor always knows where it is and can simply walk off the line. A player watching the horizon
 * gets hit in the back.
 *
 * <p>It is also on a hard clock. {@value #MAX_BURROW_TICKS} ticks underground and it must surface
 * wherever it is, so the creature can never disengage permanently, and the dive and the eruption
 * both take long enough ({@value #SUBMERGE_TICKS} and {@value #EMERGE_TICKS} ticks) to be punished
 * by anyone standing next to it when they start.
 */
public class StrataBurrowerEntity extends Monster {
    /** Out in the open, fighting normally. */
    public static final byte STATE_SURFACED = 0;

    /** Digging in. Still solid, still hittable - this is the punish window. */
    public static final byte STATE_SUBMERGING = 1;

    /** Under the floor. Untouchable, but throwing up a plume that says exactly where it is. */
    public static final byte STATE_BURROWED = 2;

    /** Coming up. The eruption has already fired; this is the recovery. */
    public static final byte STATE_EMERGING = 3;

    private static final int SUBMERGE_TICKS = 16;
    private static final int EMERGE_TICKS = 14;

    /** Hard ceiling on time spent underground. It always has to come back. */
    private static final int MAX_BURROW_TICKS = 130;

    /** Ticks before it is willing to dive again, measured from the moment it surfaces. */
    private static final int DIVE_COOLDOWN = 150;

    /** Blocks per tick underground. Faster than it walks - that is what the dive buys it. */
    private static final double BURROW_SPEED = 0.28;

    /** How far behind the target it aims to come up. */
    private static final double AMBUSH_BEHIND = 3.0;

    /** Horizontal distance from its destination at which it decides it has arrived. */
    private static final double ARRIVAL_RANGE = 2.0;

    /** Beyond this a surfaced burrower would rather tunnel than walk. */
    private static final double AMBUSH_TRIGGER_RANGE = 12.0;

    private static final float ERUPT_DAMAGE = 7.0F;
    private static final double ERUPT_RADIUS = 3.4;

    /** How far up the plume looks for the surface above the creature. */
    private static final int PLUME_PROBE_HEIGHT = 8;

    /**
     * Ticks before a burrower that found nowhere to come up tries again.
     *
     * <p>Needed because the arrival test is a distance, not an event: a creature parked on its
     * destination under a solid ceiling would otherwise re-run the whole emergence search every
     * tick and never move.
     */
    private static final int SURFACE_RETRY_TICKS = 20;

    private static final String TAG_STATE = "burrow_state";
    private static final String TAG_STATE_TICKS = "burrow_state_ticks";
    private static final String TAG_DIVE_COOLDOWN = "burrow_dive_cooldown";

    private byte burrowState = STATE_SURFACED;
    private int stateTicks;
    private int diveCooldown;
    private int surfaceRetry;

    private double destX;
    private double destZ;

    /** Reused by the plume probe and the emergence search, so neither allocates per tick. */
    private final BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();

    /**
     * The plume's particle option, cached against the block state it was built from. A burrower
     * crossing a body of one rock type allocates exactly one of these for the whole dive.
     */
    private BlockState plumeState;
    private BlockParticleOption plumeParticle;

    public StrataBurrowerEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 14;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 54.0)
                .add(Attributes.MOVEMENT_SPEED, 0.26)
                .add(Attributes.ATTACK_DAMAGE, 8.0)
                .add(Attributes.ATTACK_KNOCKBACK, 0.6)
                .add(Attributes.ARMOR, 8.0)
                .add(Attributes.ARMOR_TOUGHNESS, 2.0)
                .add(Attributes.KNOCKBACK_RESISTANCE, 0.6)
                .add(Attributes.FOLLOW_RANGE, 30.0)
                .add(Attributes.STEP_HEIGHT, 1.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(1, new FloatGoal(this));
        // Holds the movement lock for the whole dive, so nothing tries to path a creature that is
        // currently inside a wall.
        this.goalSelector.addGoal(2, new BurrowAmbushGoal(this));
        this.goalSelector.addGoal(4, new MeleeAttackGoal(this, 1.0, true));
        this.goalSelector.addGoal(6, new WaterAvoidingRandomStrollGoal(this, 0.7));
        this.goalSelector.addGoal(7, new LookAtPlayerGoal(this, Player.class, 10.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    // ----------------------------------------------------------------- state

    public byte getBurrowState() {
        return this.burrowState;
    }

    /** True whenever the creature is under the floor and cannot be reached. */
    public boolean isUnderground() {
        return this.burrowState == STATE_BURROWED;
    }

    /** True for the whole dive-through-surface cycle, including both transitions. */
    public boolean isDigging() {
        return this.burrowState != STATE_SURFACED;
    }

    public boolean isDiveReady() {
        return this.diveCooldown <= 0 && this.burrowState == STATE_SURFACED;
    }

    /**
     * Whether a surfaced burrower would rather tunnel to its quarry than walk at it.
     *
     * <p>Only worth it from a distance: a dive costs {@value #SUBMERGE_TICKS} ticks of standing
     * still, which anything already next to it will make it regret.
     */
    public boolean wantsToAmbush() {
        LivingEntity target = this.getTarget();
        return target != null
                && target.isAlive()
                && this.isDiveReady()
                && this.onGround()
                && this.distanceToSqr(target) > AMBUSH_TRIGGER_RANGE * AMBUSH_TRIGGER_RANGE;
    }

    /** Starts the dig-in. Safe to call from a goal or from taking a hit; a no-op if already digging. */
    public void beginDive() {
        if (this.isDigging() || !(this.level() instanceof ServerLevel level)) {
            return;
        }

        this.burrowState = STATE_SUBMERGING;
        this.stateTicks = 0;
        this.surfaceRetry = 0;
        this.aimAtAmbushPoint();
        this.getNavigation().stop();

        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                SoundEvents.SNIFFER_DIGGING, SoundSource.HOSTILE, 1.3F, 0.6F);
    }

    /** Recomputes where it wants to come up: a few blocks behind whatever it is hunting. */
    private void aimAtAmbushPoint() {
        LivingEntity target = this.getTarget();
        if (target == null) {
            this.destX = this.getX();
            this.destZ = this.getZ();
            return;
        }

        Vec3 look = target.getLookAngle();
        double lx = look.x;
        double lz = look.z;
        double length = Math.sqrt(lx * lx + lz * lz);
        if (length < 1.0E-4) {
            // Looking straight up or down: fall back to the line it is already on.
            this.destX = target.getX();
            this.destZ = target.getZ();
            return;
        }

        this.destX = target.getX() - lx / length * AMBUSH_BEHIND;
        this.destZ = target.getZ() - lz / length * AMBUSH_BEHIND;
    }

    @Override
    protected void customServerAiStep(ServerLevel level) {
        super.customServerAiStep(level);
        if (this.diveCooldown > 0) {
            this.diveCooldown--;
        }

        this.stateTicks++;
        switch (this.burrowState) {
            case STATE_SUBMERGING -> this.tickSubmerging(level);
            case STATE_BURROWED -> this.tickBurrowed(level);
            case STATE_EMERGING -> this.tickEmerging();
            default -> { }
        }

        // Both reasserted from the state every tick rather than only on transitions, so a reload, a
        // teleport or another mod moving the entity can never leave it phased through the world or
        // permanently unseen. Under the floor it is not drawn at all: the plume is the tell, and a
        // model half-buried in rock would only render as a mess of z-fighting.
        boolean under = this.burrowState == STATE_BURROWED;
        this.noPhysics = under;
        if (this.isInvisible() != under) {
            this.setInvisible(under);
        }
    }

    private void tickSubmerging(ServerLevel level) {
        this.getNavigation().stop();
        this.spray(level, this.getY(), 3);

        if (this.stateTicks % 4 == 0) {
            level.playSound(null, this.getX(), this.getY(), this.getZ(),
                    SoundEvents.DEEPSLATE_BREAK, SoundSource.HOSTILE, 0.8F, 0.5F);
        }

        if (this.stateTicks >= SUBMERGE_TICKS) {
            this.burrowState = STATE_BURROWED;
            this.stateTicks = 0;
            this.setNoGravity(true);
            this.noPhysics = true;
        }
    }

    /**
     * Underground travel.
     *
     * <p>Steered by hand rather than by the path finder, because there is no path: the creature is
     * inside solid rock with {@code noPhysics} set and simply swims toward its destination. It
     * re-aims periodically so a target that walks away is still followed, and the plume above it
     * is emitted every other tick.
     */
    private void tickBurrowed(ServerLevel level) {
        this.getNavigation().stop();
        this.setNoGravity(true);

        if (this.stateTicks % 20 == 0) {
            this.aimAtAmbushPoint();
        }

        double dx = this.destX - this.getX();
        double dz = this.destZ - this.getZ();
        double flat = Math.sqrt(dx * dx + dz * dz);
        if (flat > 1.0E-4) {
            this.setDeltaMovement(dx / flat * BURROW_SPEED, 0.0, dz / flat * BURROW_SPEED);
            // Face the way it is tunnelling, so the plume and the creature agree about direction.
            this.setYRot((float) (Mth.atan2(dz, dx) * (180.0 / Math.PI)) - 90.0F);
            this.yBodyRot = this.getYRot();
        } else {
            this.setDeltaMovement(0.0, 0.0, 0.0);
        }

        if ((this.stateTicks & 1) == 0) {
            this.plume(level);
        }
        if (this.stateTicks % 12 == 0) {
            level.playSound(null, this.getX(), this.getY(), this.getZ(),
                    SoundEvents.SNIFFER_DIGGING, SoundSource.HOSTILE, 0.7F, 0.5F);
        }

        if (this.surfaceRetry > 0) {
            this.surfaceRetry--;
        } else if (flat <= ARRIVAL_RANGE || this.stateTicks >= MAX_BURROW_TICKS) {
            this.beginEmergence(level);
        }
    }

    /** The recovery after the eruption: it is above ground, visible and hittable, but rooted. */
    private void tickEmerging() {
        this.getNavigation().stop();

        if (this.stateTicks >= EMERGE_TICKS) {
            this.burrowState = STATE_SURFACED;
            this.stateTicks = 0;
            this.diveCooldown = DIVE_COOLDOWN;
            this.setNoGravity(false);
            this.noPhysics = false;
        }
    }

    /**
     * Comes up, wherever it can. Tries the ambush point first, then straight up from where it
     * currently is, then the target's own position, and finally gives up and grants itself another
     * stretch of tunnelling rather than materialising inside a wall.
     */
    private void beginEmergence(ServerLevel level) {
        this.noPhysics = false;
        if (this.surfaceAt(Mth.floor(this.destX), Mth.floor(this.destZ))
                || this.surfaceAt(this.getBlockX(), this.getBlockZ())
                || this.surfaceAtTarget()) {
            this.burrowState = STATE_EMERGING;
            this.stateTicks = 0;
            this.setNoGravity(false);
            // Drop the tunnelling velocity: it was aimed at a destination the creature has now
            // arrived at, and carrying it through the teleport would slide it back off the spot.
            this.setDeltaMovement(Vec3.ZERO);
            this.erupt(level);
            return;
        }

        // Nowhere to come up: solid ceiling, or a chunk that is not loaded. Stay under, pick a new
        // aim point and wait out the retry, rather than re-running the whole search every tick for
        // as long as the creature happens to be sitting on an unusable destination.
        this.noPhysics = true;
        this.surfaceRetry = SURFACE_RETRY_TICKS;
        this.aimAtAmbushPoint();
    }

    /** Looks for standing room in the column at (x, z), near the creature's current depth. */
    private boolean surfaceAt(int x, int z) {
        int startY = this.getBlockY() + PLUME_PROBE_HEIGHT;
        int endY = this.getBlockY() - 3;

        for (int y = startY; y >= endY; y--) {
            this.cursor.set(x, y - 1, z);
            if (!this.level().isLoaded(this.cursor)) {
                return false;
            }
            if (!this.level().getBlockState(this.cursor).blocksMotion()) {
                continue;
            }

            // randomTeleport re-tests the full hitbox against the world and reverts on failure, so
            // a floor that looks clear but is under an overhang costs only the attempt.
            if (this.randomTeleport(x + 0.5, y, z + 0.5, false)) {
                return true;
            }
        }

        return false;
    }

    private boolean surfaceAtTarget() {
        LivingEntity target = this.getTarget();
        return target != null && this.surfaceAt(target.getBlockX(), target.getBlockZ());
    }

    /**
     * The ambush itself: everything standing on the ground it comes up through is thrown clear.
     *
     * <p>One bounded query on the one tick the eruption happens. The damage is modest for the
     * spectacle - the point is the knock-up and the surprise, not the number.
     */
    private void erupt(ServerLevel level) {
        double ox = this.getX();
        double oy = this.getY();
        double oz = this.getZ();

        level.playSound(null, ox, oy, oz, SoundEvents.GENERIC_EXPLODE.value(),
                SoundSource.HOSTILE, 1.4F, 0.7F);
        level.sendParticles(ParticleTypes.EXPLOSION, ox, oy + 0.3, oz, 4, 1.0, 0.1, 1.0, 0.0);
        this.spray(level, oy, 40);

        DamageSource source = this.damageSources().mobAttack(this);
        AABB ring = this.getBoundingBox().inflate(ERUPT_RADIUS, 2.0, ERUPT_RADIUS);
        List<Entity> caught = level.getEntities(this, ring,
                e -> e instanceof LivingEntity living && living.isAlive() && !living.isSpectator());

        for (int i = 0; i < caught.size(); i++) {
            Entity entity = caught.get(i);
            entity.hurtServer(level, source, ERUPT_DAMAGE);
            // Thrown up rather than out, so the hit is disorienting instead of a free escape.
            entity.setDeltaMovement(entity.getDeltaMovement().add(
                    (entity.getX() - ox) * 0.12, 0.62, (entity.getZ() - oz) * 0.12));
            entity.hurtMarked = true;
        }
    }

    // ----------------------------------------------------------------- plume

    /**
     * The tell. Finds the surface directly above the creature and throws rock out of it.
     *
     * <p>A bounded upward walk of at most {@value #PLUME_PROBE_HEIGHT} blocks through one column,
     * every other tick, reusing a single mutable position. If there is no opening within that
     * distance the burrower is too deep to give itself away, which is the correct answer: it is
     * also too deep to surface on you without warning.
     */
    private void plume(ServerLevel level) {
        int x = this.getBlockX();
        int z = this.getBlockZ();
        int baseY = this.getBlockY();

        for (int dy = 0; dy <= PLUME_PROBE_HEIGHT; dy++) {
            this.cursor.set(x, baseY + dy, z);
            if (!level.isLoaded(this.cursor)) {
                return;
            }

            BlockState state = level.getBlockState(this.cursor);
            if (state.blocksMotion()) {
                continue;
            }

            this.spray(level, baseY + dy, 5);
            if ((this.stateTicks & 7) == 0) {
                level.playSound(null, x + 0.5, baseY + dy, z + 0.5,
                        SoundEvents.STONE_BREAK, SoundSource.HOSTILE, 0.7F, 0.6F);
            }
            return;
        }
    }

    /** Throws a burst of whatever rock the creature is currently inside. */
    private void spray(ServerLevel level, double y, int count) {
        this.cursor.set(this.getBlockX(), this.getBlockY(), this.getBlockZ());
        BlockState inside = level.getBlockState(this.cursor);
        if (inside.isAir()) {
            this.cursor.set(this.getBlockX(), this.getBlockY() - 1, this.getBlockZ());
            inside = level.getBlockState(this.cursor);
        }

        if (inside != this.plumeState) {
            this.plumeState = inside;
            this.plumeParticle = new BlockParticleOption(ParticleTypes.BLOCK, inside);
        }
        if (inside.isAir()) {
            return;
        }

        level.sendParticles(this.plumeParticle,
                this.getX(), y + 0.1, this.getZ(), count, 0.45, 0.1, 0.45, 0.18);
    }

    // ---------------------------------------------------------------- damage

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
        // Nothing reaches it underground. Not invulnerability for its own sake - it is inside solid
        // rock, and the player's answer is to hit it during the dive or the eruption instead.
        if (this.isUnderground()
                && !source.is(DamageTypeTags.BYPASSES_INVULNERABILITY)
                && !source.isCreativePlayer()) {
            return false;
        }

        boolean hurt = super.hurtServer(level, source, damage);
        if (hurt && this.isAlive() && this.isDiveReady() && source.getEntity() != null) {
            // Hurt on the surface: go under, and come back up behind whoever did it.
            this.beginDive();
        }

        return hurt;
    }

    @Override
    public boolean causeFallDamage(double distance, float multiplier, DamageSource source) {
        return false;
    }

    @Override
    protected void addAdditionalSaveData(ValueOutput output) {
        super.addAdditionalSaveData(output);
        output.putByte(TAG_STATE, this.burrowState);
        output.putInt(TAG_STATE_TICKS, this.stateTicks);
        output.putInt(TAG_DIVE_COOLDOWN, this.diveCooldown);
    }

    @Override
    protected void readAdditionalSaveData(ValueInput input) {
        super.readAdditionalSaveData(input);
        this.burrowState = input.getByteOr(TAG_STATE, STATE_SURFACED);
        this.stateTicks = input.getIntOr(TAG_STATE_TICKS, 0);
        this.diveCooldown = input.getIntOr(TAG_DIVE_COOLDOWN, 0);
        this.noPhysics = this.burrowState == STATE_BURROWED;
        this.setInvisible(this.noPhysics);
    }

    @Override
    public int getAmbientSoundInterval() {
        return 180;
    }

    @Override
    protected SoundEvent getAmbientSound() {
        return SoundEvents.DEEPSLATE_BREAK;
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
        this.playSound(SoundEvents.DEEPSLATE_STEP, 0.7F, 0.7F);
    }
}

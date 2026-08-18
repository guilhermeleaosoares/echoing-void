package com.echoingvoid.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * A humanoid caster that refuses to be in melee range.
 *
 * <p>The shade fires resonance bolts from a distance and blinks away the moment anything closes on
 * it. The bolts travel - they are not hitscan - so they can be strafed, and the blink is the thing
 * the fight is actually about: a shade in the open is nearly impossible to reach, and a shade with
 * a wall behind it is a caster with 26 health and no armour.
 *
 * <p>That is the whole counterplay, and it is deliberately spatial rather than reflex-based. Every
 * blink destination is validated the same way: a bounded probe for a floor, then
 * {@link #randomTeleport} for collision and liquids. If nothing on the candidate list passes, the
 * shade simply does not blink. Backing one into a corridor, a doorway or the underside of an island
 * takes its escape away, and it is on the player to notice that.
 *
 * <p>The bolt in flight lives on this entity rather than in the goal that fired it, so losing the
 * target mid-flight - or dying - does not strand it. It is not a separate entity either: a bolt is
 * six doubles and a counter, ticked here, which costs a fraction of what an {@code EntityType} plus
 * a renderer plus tracking would.
 */
public class TunerShadeEntity extends Monster {
    // ------------------------------------------------------------------ bolt

    /** Blocks travelled per tick. Slow enough to sidestep at range, fast enough to punish standing. */
    private static final double BOLT_SPEED = 0.9;

    /** Ticks a bolt survives before dissipating; at {@link #BOLT_SPEED} that is about 40 blocks. */
    private static final int BOLT_LIFETIME = 45;

    /** How close to the bolt's line an entity has to be to be struck. */
    private static final double BOLT_RADIUS = 0.55;

    private static final float BOLT_DAMAGE = 5.0F;

    /** Ticks of slowness a bolt leaves behind. The shade wins by keeping you slow and far away. */
    private static final int BOLT_SLOW_TICKS = 70;

    private boolean boltActive;
    private double boltX;
    private double boltY;
    private double boltZ;
    private double boltVx;
    private double boltVy;
    private double boltVz;
    private int boltAge;

    /** Reused by the bolt's block test so a bolt in flight allocates no positions. */
    private final BlockPos.MutableBlockPos boltCursor = new BlockPos.MutableBlockPos();

    // ----------------------------------------------------------------- blink

    /**
     * Candidate destinations, as (distance, bearing) pairs measured from the direction directly
     * away from the threat. Fixed and static so choosing one allocates nothing, and ordered so the
     * shade prefers a long straight retreat and only sidesteps when that is blocked.
     */
    private static final double[] BLINK_CANDIDATES = {
            7.0, 0.0,
            7.0, 0.55,
            7.0, -0.55,
            9.5, 0.0,
            5.0, 1.15,
            5.0, -1.15,
            4.5, 2.1,
            4.5, -2.1,
    };

    /** How far above and below its own feet the shade will accept a landing. */
    private static final int BLINK_PROBE_UP = 2;
    private static final int BLINK_PROBE_DOWN = 4;

    /** Ticks between blinks. Short enough to feel slippery, long enough to be punished. */
    private static final int BLINK_COOLDOWN = 55;

    /**
     * Ticks before a shade that found nowhere to go tries again.
     *
     * <p>Without this a cornered shade would re-probe every candidate every tick and, because the
     * blink goal outranks the bolt goal, would spend the whole fight failing to escape instead of
     * turning and casting. Cornering it is supposed to make it fight, not make it inert.
     */
    private static final int BLINK_RETRY_COOLDOWN = 20;

    private int blinkCooldown;

    /** Reused by the landing probe. */
    private final BlockPos.MutableBlockPos blinkCursor = new BlockPos.MutableBlockPos();

    public TunerShadeEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 12;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 26.0)
                .add(Attributes.MOVEMENT_SPEED, 0.29)
                .add(Attributes.ATTACK_DAMAGE, 2.0)
                .add(Attributes.ARMOR, 1.0)
                .add(Attributes.FOLLOW_RANGE, 34.0)
                .add(Attributes.STEP_HEIGHT, 1.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(1, new FloatGoal(this));
        // Escape outranks casting: a shade that is being hit should be gone, not mid-wind-up.
        this.goalSelector.addGoal(2, new BlinkAwayGoal(this));
        this.goalSelector.addGoal(3, new ResonanceBoltGoal(this));
        this.goalSelector.addGoal(6, new WaterAvoidingRandomStrollGoal(this, 0.7));
        this.goalSelector.addGoal(7, new LookAtPlayerGoal(this, Player.class, 14.0F));
        this.goalSelector.addGoal(8, new RandomLookAroundGoal(this));
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    protected void customServerAiStep(ServerLevel level) {
        super.customServerAiStep(level);
        if (this.blinkCooldown > 0) {
            this.blinkCooldown--;
        }
        if (this.boltActive) {
            this.tickBolt(level);
        }
    }

    // ------------------------------------------------------------------ bolt

    /** Whether a bolt is currently in the air. The goal will not fire a second one over it. */
    public boolean hasBoltInFlight() {
        return this.boltActive;
    }

    /**
     * Launches a bolt from the shade's resonator at wherever the target is standing right now.
     *
     * <p>Deliberately not led: the bolt goes to where the target was at the instant the cast
     * completed, so walking sideways during the flight time is a complete dodge. The wind-up in
     * {@link ResonanceBoltGoal} is what tells the player when that window opens.
     */
    public void fireBolt(ServerLevel level, LivingEntity target) {
        double sx = this.getX();
        double sy = this.getEyeY() - 0.4;
        double sz = this.getZ();
        double dx = target.getX() - sx;
        double dy = target.getY(0.6) - sy;
        double dz = target.getZ() - sz;
        double length = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (length < 1.0E-4) {
            return;
        }

        this.boltX = sx;
        this.boltY = sy;
        this.boltZ = sz;
        this.boltVx = dx / length * BOLT_SPEED;
        this.boltVy = dy / length * BOLT_SPEED;
        this.boltVz = dz / length * BOLT_SPEED;
        this.boltAge = 0;
        this.boltActive = true;

        level.playSound(null, sx, sy, sz, SoundEvents.WARDEN_SONIC_BOOM,
                SoundSource.HOSTILE, 0.7F, 1.8F);
    }

    /**
     * Advances the bolt one tick and resolves whatever it meets.
     *
     * <p>One bounded {@code getEntitiesOfClass} per tick over the box the bolt swept this tick, not
     * one per sub-step and never a world scan. A tick's travel is well under a block, so the box is
     * tiny and usually empty.
     */
    private void tickBolt(ServerLevel level) {
        double nx = this.boltX + this.boltVx;
        double ny = this.boltY + this.boltVy;
        double nz = this.boltZ + this.boltVz;

        this.boltCursor.set(Mth.floor(nx), Mth.floor(ny), Mth.floor(nz));
        if (!level.isLoaded(this.boltCursor)) {
            this.boltActive = false;
            return;
        }

        BlockState state = level.getBlockState(this.boltCursor);
        if (state.blocksMotion()) {
            this.burstBolt(level, nx, ny, nz);
            return;
        }

        AABB swept = new AABB(this.boltX, this.boltY, this.boltZ, nx, ny, nz).inflate(BOLT_RADIUS);
        List<LivingEntity> struck = level.getEntitiesOfClass(LivingEntity.class, swept,
                candidate -> candidate != this
                        && candidate.isAlive()
                        && !candidate.isSpectator()
                        && !(candidate instanceof TunerShadeEntity));
        if (!struck.isEmpty()) {
            // Nearest to where the bolt started this tick, so a bolt passing through a crowd hits
            // the front of it rather than whichever entity the query happened to list first.
            LivingEntity nearest = struck.get(0);
            double best = nearest.distanceToSqr(this.boltX, this.boltY, this.boltZ);
            for (int i = 1; i < struck.size(); i++) {
                double distSq = struck.get(i).distanceToSqr(this.boltX, this.boltY, this.boltZ);
                if (distSq < best) {
                    best = distSq;
                    nearest = struck.get(i);
                }
            }

            this.hitWithBolt(level, nearest);
            this.burstBolt(level, nearest.getX(), nearest.getY(0.6), nearest.getZ());
            return;
        }

        this.boltX = nx;
        this.boltY = ny;
        this.boltZ = nz;

        level.sendParticles(ParticleTypes.SCULK_SOUL, nx, ny, nz, 1, 0.03, 0.03, 0.03, 0.0);
        if ((this.boltAge & 1) == 0) {
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK, nx, ny, nz, 1, 0.06, 0.06, 0.06, 0.01);
        }

        if (++this.boltAge >= BOLT_LIFETIME) {
            this.boltActive = false;
        }
    }

    private void hitWithBolt(ServerLevel level, LivingEntity victim) {
        if (victim.hurtServer(level, this.damageSources().indirectMagic(this, this), BOLT_DAMAGE)) {
            victim.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, BOLT_SLOW_TICKS, 1), this);
        }
    }

    /** Ends the bolt with a visible pop, so a miss is as legible as a hit. */
    private void burstBolt(ServerLevel level, double x, double y, double z) {
        this.boltActive = false;
        level.sendParticles(ParticleTypes.SCULK_CHARGE_POP, x, y, z, 10, 0.25, 0.25, 0.25, 0.05);
        level.playSound(null, x, y, z, SoundEvents.AMETHYST_BLOCK_CHIME,
                SoundSource.HOSTILE, 0.8F, 0.6F);
    }

    // ----------------------------------------------------------------- blink

    public boolean isBlinkReady() {
        return this.blinkCooldown <= 0;
    }

    /**
     * Tries every candidate destination in order and takes the first that works.
     *
     * <p>Returns false when none of them do, which is the entire point of the creature: a shade
     * that cannot find a floor to land on within a couple of blocks of its own feet, in open air,
     * is a shade that has to stand and fight. A failure still takes a short cooldown, so a cornered
     * shade spends most of its time casting and only occasionally tests the walls again.
     */
    public boolean tryBlinkAwayFrom(ServerLevel level, Entity threat) {
        double dx = this.getX() - threat.getX();
        double dz = this.getZ() - threat.getZ();
        double length = Math.sqrt(dx * dx + dz * dz);
        if (length < 1.0E-4) {
            // Standing inside the threat: any direction is away from it.
            dx = -Mth.sin(this.getYRot() * ((float) Math.PI / 180.0F));
            dz = Mth.cos(this.getYRot() * ((float) Math.PI / 180.0F));
            length = 1.0;
        }

        double ux = dx / length;
        double uz = dz / length;
        double fromX = this.getX();
        double fromY = this.getY();
        double fromZ = this.getZ();

        for (int i = 0; i < BLINK_CANDIDATES.length; i += 2) {
            double distance = BLINK_CANDIDATES[i];
            double bearing = BLINK_CANDIDATES[i + 1];
            double cos = Math.cos(bearing);
            double sin = Math.sin(bearing);
            double wantX = fromX + (ux * cos - uz * sin) * distance;
            double wantZ = fromZ + (ux * sin + uz * cos) * distance;

            int floorY = this.probeFloor(Mth.floor(wantX), Mth.floor(wantZ));
            if (floorY == Integer.MIN_VALUE) {
                continue;
            }

            // randomTeleport re-checks collision and liquids and reverts on failure, so a candidate
            // that passes the floor probe but lands inside geometry costs nothing but the attempt.
            if (this.randomTeleport(Mth.floor(wantX) + 0.5, floorY, Mth.floor(wantZ) + 0.5, false)) {
                this.blinkCooldown = BLINK_COOLDOWN;
                this.getNavigation().stop();
                this.announceBlink(level, fromX, fromY, fromZ);
                return true;
            }
        }

        this.blinkCooldown = BLINK_RETRY_COOLDOWN;
        return false;
    }

    /**
     * Finds standing room in the column at (x, z), within a few blocks of the shade's own feet.
     *
     * <p>The vertical bound is what stops a blink from being an escape hatch. Without it a shade on
     * a bridge over the void could drop out of a fight entirely, and cornering it would stop
     * meaning anything.
     *
     * @return the y to stand on, or {@link Integer#MIN_VALUE} if the column has no floor in range
     */
    private int probeFloor(int x, int z) {
        Level level = this.level();
        int startY = Mth.floor(this.getY()) + BLINK_PROBE_UP;
        int endY = startY - BLINK_PROBE_UP - BLINK_PROBE_DOWN;

        for (int y = startY; y >= endY; y--) {
            this.blinkCursor.set(x, y - 1, z);
            if (!level.isLoaded(this.blinkCursor)) {
                return Integer.MIN_VALUE;
            }
            if (!level.getBlockState(this.blinkCursor).blocksMotion()) {
                continue;
            }

            // Two blocks of headroom, because the shade is player-sized.
            this.blinkCursor.set(x, y, z);
            if (level.getBlockState(this.blinkCursor).blocksMotion()) {
                continue;
            }
            this.blinkCursor.set(x, y + 1, z);
            if (level.getBlockState(this.blinkCursor).blocksMotion()) {
                continue;
            }

            return y;
        }

        return Integer.MIN_VALUE;
    }

    /** Draws both ends of the blink, so the player can see where it went. */
    private void announceBlink(ServerLevel level, double fromX, double fromY, double fromZ) {
        level.sendParticles(ParticleTypes.REVERSE_PORTAL,
                fromX, fromY + 1.0, fromZ, 24, 0.3, 0.7, 0.3, 0.03);
        level.sendParticles(ParticleTypes.SCULK_SOUL,
                this.getX(), this.getY() + 1.0, this.getZ(), 16, 0.3, 0.7, 0.3, 0.02);
        level.playSound(null, fromX, fromY, fromZ, SoundEvents.ENDERMAN_TELEPORT,
                SoundSource.HOSTILE, 0.9F, 1.4F);
        level.playSound(null, this.getX(), this.getY(), this.getZ(), SoundEvents.ENDERMAN_TELEPORT,
                SoundSource.HOSTILE, 0.7F, 1.1F);
    }

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
        boolean hurt = super.hurtServer(level, source, damage);
        if (!hurt || !this.isAlive() || !this.isBlinkReady()) {
            return hurt;
        }

        // Blink out of a landed blow as well as away from an approach. Only from something with a
        // position to flee from - drowning or a status effect gives it nothing to run from.
        Entity attacker = source.getEntity();
        if (attacker != null && attacker != this) {
            this.tryBlinkAwayFrom(level, attacker);
        }

        return hurt;
    }

    /** The shade rides the wind of its own blink; it should never take fall damage from one. */
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

    @Override
    protected void playStepSound(BlockPos pos, BlockState state) {
        this.playSound(SoundEvents.WOOL_STEP, 0.2F, 0.8F);
    }

    /** Where the resonator ring sits, for anything that wants to draw from it. */
    public Vec3 resonatorPosition() {
        float yaw = this.getYRot() * ((float) Math.PI / 180.0F);
        return new Vec3(this.getX() - Mth.sin(yaw) * 0.55,
                this.getEyeY() - 0.45,
                this.getZ() + Mth.cos(yaw) * 0.55);
    }
}

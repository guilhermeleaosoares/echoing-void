package com.echoingvoid.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.function.Predicate;

/**
 * One resonance bolt in flight, owned by whoever cast it.
 *
 * <p>This is the Tuner Shade's projectile lifted out of {@link TunerShadeEntity} unchanged, so that
 * a second caster can use it without a second copy of the flight, collision and burst logic. PLAYER,
 * asking for exactly that second caster: "the tuner trader mobs should be neutral, not passive, like
 * piglings... they can attack with magic like the tuner shader mob, similar attacks to those, though
 * dealing 75% the damage of what a tuner shader would."
 *
 * <p>Duplicating the projectile would have been the quicker route and the wrong one - two copies of
 * a hit test drift, and the one nobody is looking at is the one that stops matching. Damage is a
 * constructor argument, which is the only thing the two casters actually differ on.
 *
 * <p>Not a real {@code Entity}: it is a few doubles ticked by its owner. That is what the original
 * did, and it is why a bolt costs nothing to have in the air - no entity registration, no tracking,
 * no save data. The trade-off is that a bolt dies with its caster, which reads correctly anyway.
 */
public final class ResonanceBolt {

    /** Blocks travelled per tick. */
    private static final double SPEED = 0.9;

    /** How close to the bolt's line an entity has to be to be struck. */
    private static final double RADIUS = 0.55;

    /** Ticks before a bolt that has hit nothing gives up. */
    private static final int LIFETIME = 60;

    /** Ticks of slowness a hit leaves behind - the caster wins by keeping you slow and far away. */
    private static final int SLOW_TICKS = 70;

    private final Mob owner;
    private final float damage;

    /**
     * What this bolt refuses to hit. Each caster passes its own kind, so a crowd of shades does not
     * shoot itself apart and a crowd of traders does not either.
     */
    private final Predicate<LivingEntity> friendly;

    private final BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();

    private boolean active;
    private double x;
    private double y;
    private double z;
    private double vx;
    private double vy;
    private double vz;
    private int age;

    public ResonanceBolt(Mob owner, float damage, Predicate<LivingEntity> friendly) {
        this.owner = owner;
        this.damage = damage;
        this.friendly = friendly;
    }

    /** Whether a bolt is currently in the air. A caster never fires a second one over the first. */
    public boolean inFlight() {
        return this.active;
    }

    /**
     * Launches from the caster's resonator at wherever the target is standing right now.
     *
     * <p>Deliberately not led: the bolt goes to where the target was at the instant the cast
     * completed, so walking sideways during the flight is a complete dodge. The wind-up in
     * {@link ResonanceBoltGoal} is what tells the player when that window opens.
     */
    public void fire(ServerLevel level, LivingEntity target) {
        double sx = this.owner.getX();
        double sy = this.owner.getEyeY() - 0.4;
        double sz = this.owner.getZ();
        double dx = target.getX() - sx;
        double dy = target.getY(0.6) - sy;
        double dz = target.getZ() - sz;
        double length = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (length < 1.0E-4) {
            return;
        }

        this.x = sx;
        this.y = sy;
        this.z = sz;
        this.vx = dx / length * SPEED;
        this.vy = dy / length * SPEED;
        this.vz = dz / length * SPEED;
        this.age = 0;
        this.active = true;

        level.playSound(null, sx, sy, sz, SoundEvents.WARDEN_SONIC_BOOM,
                SoundSource.HOSTILE, 0.7F, 1.8F);
    }

    /**
     * Advances one tick and resolves whatever it meets.
     *
     * <p>One bounded {@code getEntitiesOfClass} per tick over the box the bolt swept this tick, not
     * one per sub-step and never a world scan. A tick's travel is well under a block, so the box is
     * tiny and usually empty.
     */
    public void tick(ServerLevel level) {
        if (!this.active) {
            return;
        }

        double nx = this.x + this.vx;
        double ny = this.y + this.vy;
        double nz = this.z + this.vz;

        this.cursor.set(Mth.floor(nx), Mth.floor(ny), Mth.floor(nz));
        if (!level.isLoaded(this.cursor)) {
            this.active = false;
            return;
        }

        BlockState state = level.getBlockState(this.cursor);
        if (state.blocksMotion()) {
            this.burst(level, nx, ny, nz);
            return;
        }

        AABB swept = new AABB(this.x, this.y, this.z, nx, ny, nz).inflate(RADIUS);
        List<LivingEntity> struck = level.getEntitiesOfClass(LivingEntity.class, swept,
                candidate -> candidate != this.owner
                        && candidate.isAlive()
                        && !candidate.isSpectator()
                        && !this.friendly.test(candidate));
        if (!struck.isEmpty()) {
            // Nearest to where the bolt started this tick, so a bolt passing through a crowd hits
            // the front of it rather than whichever entity the query happened to list first.
            LivingEntity nearest = struck.get(0);
            double best = nearest.distanceToSqr(this.x, this.y, this.z);
            for (int i = 1; i < struck.size(); i++) {
                double distSq = struck.get(i).distanceToSqr(this.x, this.y, this.z);
                if (distSq < best) {
                    best = distSq;
                    nearest = struck.get(i);
                }
            }

            this.hit(level, nearest);
            this.burst(level, nearest.getX(), nearest.getY(0.6), nearest.getZ());
            return;
        }

        this.x = nx;
        this.y = ny;
        this.z = nz;

        level.sendParticles(ParticleTypes.SCULK_SOUL, nx, ny, nz, 1, 0.03, 0.03, 0.03, 0.0);
        if ((this.age & 1) == 0) {
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK, nx, ny, nz, 1, 0.06, 0.06, 0.06, 0.01);
        }

        if (++this.age >= LIFETIME) {
            this.active = false;
        }
    }

    private void hit(ServerLevel level, LivingEntity victim) {
        if (victim.hurtServer(level, this.owner.damageSources().indirectMagic(this.owner, this.owner),
                this.damage)) {
            victim.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, SLOW_TICKS, 1), this.owner);
        }
    }

    /** Ends the bolt with a visible pop, so a miss is as legible as a hit. */
    private void burst(ServerLevel level, double bx, double by, double bz) {
        this.active = false;
        level.sendParticles(ParticleTypes.SCULK_CHARGE_POP, bx, by, bz, 10, 0.25, 0.25, 0.25, 0.05);
        level.playSound(null, bx, by, bz, SoundEvents.AMETHYST_BLOCK_CHIME,
                SoundSource.HOSTILE, 0.8F, 0.6F);
    }
}

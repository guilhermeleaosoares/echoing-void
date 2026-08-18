package com.echoingvoid.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LeapAtTargetGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.ai.navigation.WallClimberNavigation;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.EnumSet;

/**
 * A ceiling-dwelling ambusher.
 *
 * <p>The weaver is fast and fragile: it wants to be over the player's head rather than in front of
 * them. It climbs walls the way a spider does, so it reaches ceilings by walking up whatever is
 * nearest, then holds position above its target until it can drop.
 *
 * <p>A badly hurt weaver stops fighting altogether and climbs out of reach to knit itself back
 * together - see {@link CeilingRetreatGoal}. So the ceiling is both where the fight starts and
 * where it goes if the player lets it, and a weaver that is allowed to reach a roof has to be
 * fought twice.
 *
 * <p>Finding somewhere to hang costs block lookups, and the weaver asks the same questions about
 * the same columns over and over as it circles a target - or as it runs for one. Those probes are
 * therefore cached and shared between both goals; see {@link #hasCeilingAnchor(int, int, int)}.
 */
public class EchoWeaverEntity extends Monster {
    private static final EntityDataAccessor<Byte> DATA_FLAGS_ID =
            SynchedEntityData.defineId(EchoWeaverEntity.class, EntityDataSerializers.BYTE);

    /** Bit 0 of {@link #DATA_FLAGS_ID}: the client needs this to lean the model into the surface. */
    private static final byte FLAG_CLIMBING = 1;

    /**
     * Bit 1 of {@link #DATA_FLAGS_ID}: the weaver has broken off and is heading for a ceiling.
     * Synched so the client can tell a fleeing weaver from a hunting one at a glance, and so
     * anything else that wants to know does not have to guess from its health bar.
     */
    private static final byte FLAG_RETREATING = 2;

    /**
     * Slots in the ceiling probe cache. Fixed at 64 so that the "slot in use" and "slot said yes"
     * sets each fit in a single long, which keeps a lookup to two bit tests and one array read.
     */
    private static final int CEILING_CACHE_SLOTS = 64;

    /**
     * Ticks before the whole cache is dropped. Blocks can be mined out from under a cached answer,
     * so entries are not kept indefinitely; three seconds is short enough that a stale anchor only
     * ever costs one wasted path attempt.
     */
    private static final int CEILING_CACHE_LIFETIME = 60;

    /** How far above a column the weaver will look for something to hang from. */
    private static final int CEILING_PROBE_HEIGHT = 8;

    /** 64-bit mixing constant (golden ratio), used to spread packed positions across the slots. */
    private static final long SLOT_MIX = 0x9E3779B97F4A7C15L;

    /** Packed {@link BlockPos} keys, one per slot. Only meaningful where {@link #ceilingLive} is set. */
    private final long[] ceilingKeys = new long[CEILING_CACHE_SLOTS];

    /** Bit i set when slot i holds an entry from the current cache generation. */
    private long ceilingLive;

    /** Bit i set when slot i's cached answer was "yes, there is a ceiling above this column". */
    private long ceilingAnchored;

    private int ceilingCacheAge;

    /** Reused for every probe so the per-tick path allocates nothing. */
    private final BlockPos.MutableBlockPos probeCursor = new BlockPos.MutableBlockPos();

    public EchoWeaverEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 8;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 20.0)
                .add(Attributes.MOVEMENT_SPEED, 0.36)
                .add(Attributes.ATTACK_DAMAGE, 5.0)
                .add(Attributes.ARMOR, 1.0)
                .add(Attributes.FOLLOW_RANGE, 28.0)
                .add(Attributes.STEP_HEIGHT, 1.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(1, new FloatGoal(this));
        // Above everything that attacks: a badly hurt weaver stops fighting and climbs out of
        // reach. Holding MOVE and LOOK is what silences the snare and the leap while it runs.
        this.goalSelector.addGoal(1, new CeilingRetreatGoal(this, 1.25));
        this.goalSelector.addGoal(2, new EnsnareGoal(this));
        this.goalSelector.addGoal(2, new LeapAtTargetGoal(this, 0.4F));
        // Above melee: while the target is still at range the weaver climbs to a perch instead of
        // walking at them. It yields to the melee goal as soon as it is close or on a wall.
        this.goalSelector.addGoal(3, new EchoWeaverEntity.CeilingAmbushGoal(this, 1.0));
        this.goalSelector.addGoal(4, new MeleeAttackGoal(this, 1.0, true));
        this.goalSelector.addGoal(6, new WaterAvoidingRandomStrollGoal(this, 0.8));
        this.goalSelector.addGoal(7, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    protected PathNavigation createNavigation(Level level) {
        return new WallClimberNavigation(this, level);
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder entityData) {
        super.defineSynchedData(entityData);
        entityData.define(DATA_FLAGS_ID, (byte) 0);
    }

    @Override
    public void tick() {
        super.tick();
        if (!this.level().isClientSide()) {
            this.setClimbing(this.horizontalCollision);
            this.ageCeilingCache();
        }
    }

    @Override
    public boolean onClimbable() {
        return this.isClimbing();
    }

    public boolean isClimbing() {
        return (this.entityData.get(DATA_FLAGS_ID) & FLAG_CLIMBING) != 0;
    }

    public void setClimbing(boolean climbing) {
        this.setFlag(FLAG_CLIMBING, climbing);
    }

    /** Whether the weaver has given up on the fight and is making for a ceiling. */
    public boolean isRetreating() {
        return (this.entityData.get(DATA_FLAGS_ID) & FLAG_RETREATING) != 0;
    }

    public void setRetreating(boolean retreating) {
        this.setFlag(FLAG_RETREATING, retreating);
    }

    private void setFlag(byte flag, boolean set) {
        byte flags = this.entityData.get(DATA_FLAGS_ID);
        byte updated = set ? (byte) (flags | flag) : (byte) (flags & ~flag);
        if (updated != flags) {
            this.entityData.set(DATA_FLAGS_ID, updated);
        }
    }

    /**
     * Whether the column at (x, z) has something the weaver could hang from within
     * {@value #CEILING_PROBE_HEIGHT} blocks of y.
     *
     * <p>Answers are memoised in a direct-mapped cache of {@value #CEILING_CACHE_SLOTS} slots keyed
     * by the packed block position. A slot holds exactly one entry: a colliding position simply
     * overwrites whatever was there, so there is no probing and no eviction bookkeeping. The whole
     * cache is invalidated wholesale every {@value #CEILING_CACHE_LIFETIME} ticks rather than
     * per-entry, which costs one field write instead of a sweep.
     */
    public boolean hasCeilingAnchor(int x, int y, int z) {
        long key = BlockPos.asLong(x, y, z);
        int slot = (int) ((key * SLOT_MIX) >>> 58);
        long bit = 1L << slot;
        if ((this.ceilingLive & bit) != 0L && this.ceilingKeys[slot] == key) {
            return (this.ceilingAnchored & bit) != 0L;
        }

        boolean anchored = this.probeCeiling(x, y, z);
        this.ceilingKeys[slot] = key;
        this.ceilingLive |= bit;
        if (anchored) {
            this.ceilingAnchored |= bit;
        } else {
            this.ceilingAnchored &= ~bit;
        }

        return anchored;
    }

    /** Walks the column upwards and reports whether the first block found presents a solid underside. */
    private boolean probeCeiling(int x, int y, int z) {
        Level level = this.level();
        for (int dy = 1; dy <= CEILING_PROBE_HEIGHT; dy++) {
            this.probeCursor.set(x, y + dy, z);
            // Never force a chunk load for a speculative perch.
            if (!level.isLoaded(this.probeCursor)) {
                return false;
            }

            BlockState state = level.getBlockState(this.probeCursor);
            if (!state.isAir()) {
                return state.isFaceSturdy(level, this.probeCursor, Direction.DOWN);
            }
        }

        return false;
    }

    private void ageCeilingCache() {
        if (++this.ceilingCacheAge >= CEILING_CACHE_LIFETIME) {
            this.ceilingCacheAge = 0;
            this.ceilingLive = 0L;
        }
    }

    @Override
    protected SoundEvent getAmbientSound() {
        return SoundEvents.SCULK_CLICKING;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.SPIDER_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.SPIDER_DEATH;
    }

    @Override
    protected void playStepSound(BlockPos pos, BlockState state) {
        this.playSound(SoundEvents.SPIDER_STEP, 0.12F, 1.4F);
    }

    /**
     * Moves the weaver to a ceiling anchored near its target, so it approaches from overhead.
     *
     * <p>Candidate columns are a fixed, deliberately small scatter around the target and are only
     * re-tested every {@value #REPATH_INTERVAL} ticks; every test goes through the weaver's ceiling
     * cache, so circling the same room re-probes almost nothing.
     */
    private static class CeilingAmbushGoal extends Goal {
        /** Interleaved x/z offsets from the target's column. Static so ticking allocates nothing. */
        private static final int[] OFFSETS = {0, 0, 2, 1, -2, -1, 1, -2, -1, 2, 4, 2, -4, -2, 2, -4, -2, 4};

        private static final int REPATH_INTERVAL = 30;

        /** Below this squared distance the melee goal should have the target instead. */
        private static final double ENGAGE_RANGE_SQR = 9.0;

        /** Above this squared distance it is worth climbing rather than walking in. */
        private static final double PERCH_RANGE_SQR = 16.0;

        private final EchoWeaverEntity weaver;
        private final double speedModifier;
        private int nextProbe;

        CeilingAmbushGoal(EchoWeaverEntity weaver, double speedModifier) {
            this.weaver = weaver;
            this.speedModifier = speedModifier;
            this.setFlags(EnumSet.of(Goal.Flag.MOVE));
        }

        @Override
        public boolean canUse() {
            LivingEntity target = this.weaver.getTarget();
            return target != null
                    && target.isAlive()
                    && !this.weaver.onClimbable()
                    && this.weaver.distanceToSqr(target) > PERCH_RANGE_SQR;
        }

        @Override
        public boolean canContinueToUse() {
            LivingEntity target = this.weaver.getTarget();
            return target != null
                    && target.isAlive()
                    && !this.weaver.onClimbable()
                    && this.weaver.distanceToSqr(target) > ENGAGE_RANGE_SQR;
        }

        @Override
        public void start() {
            this.nextProbe = 0;
        }

        @Override
        public void stop() {
            this.weaver.getNavigation().stop();
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void tick() {
            if (--this.nextProbe > 0) {
                return;
            }

            this.nextProbe = this.adjustedTickDelay(REPATH_INTERVAL);
            LivingEntity target = this.weaver.getTarget();
            if (target == null) {
                return;
            }

            int baseX = target.getBlockX();
            int baseY = target.getBlockY();
            int baseZ = target.getBlockZ();
            for (int i = 0; i < OFFSETS.length; i += 2) {
                int x = baseX + OFFSETS[i];
                int z = baseZ + OFFSETS[i + 1];
                if (this.weaver.hasCeilingAnchor(x, baseY, z)) {
                    this.weaver.getNavigation().moveTo(x + 0.5, baseY, z + 0.5, this.speedModifier);
                    return;
                }
            }
        }
    }
}

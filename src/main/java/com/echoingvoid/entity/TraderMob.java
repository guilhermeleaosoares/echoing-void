package com.echoingvoid.entity;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.registry.ModCrops;
import com.echoingvoid.registry.ModFluids;
import com.echoingvoid.registry.ModKnell;
import com.echoingvoid.registry.ModItems;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.stats.Stats;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.LookAtTradingPlayerGoal;
import net.minecraft.world.entity.ai.goal.PanicGoal;
import net.minecraft.world.entity.ai.goal.TradeWithPlayerGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.npc.villager.AbstractVillager;
import net.minecraft.world.entity.player.Player;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import org.jspecify.annotations.Nullable;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * PLAYER: "maybe the outpost and camp could have different varieties of neutral mobs that can
 * trade like villagers but attack when one is hit."
 *
 * <p>Extends {@link AbstractVillager} rather than reimplementing a merchant from scratch - the
 * trading GUI, the offer book, the whole {@code Merchant} interface come from vanilla for free,
 * and a player who has traded with a villager already knows how to trade with this one. What is
 * new is {@link #variety()}: two trade tables and two looks, one per settlement kind.
 *
 * <p>"Attack when one is hit" is taken literally rather than as "call for help" - {@link
 * #hurt(ServerLevel, DamageSource, float)} briefly retaliates against whoever struck it (a single
 * short-lived melee response, not a permanent grudge), which is also what tells the {@link
 * ProtectorMob} nearby to step in.
 */
public class TraderMob extends AbstractVillager {

    public enum Variety { OUTPOST, CAMP }

    private static final int RETALIATION_TICKS = 100; // 5 seconds of fighting back

    private Variety variety = Variety.OUTPOST;
    private int retaliationTimer;

    public TraderMob(EntityType<? extends TraderMob> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 20.0)
                .add(Attributes.MOVEMENT_SPEED, 0.5)
                .add(Attributes.ATTACK_DAMAGE, 2.0)
                .add(Attributes.FOLLOW_RANGE, 16.0);
    }

    public Variety variety() {
        return variety;
    }

    public void setVariety(Variety variety) {
        this.variety = variety;
    }

    /**
     * Naturally spawned traders come from {@code spawn_overrides} on the two settlement
     * structures (see {@code tools/gen_worldgen.py}), which is one weighted spawn list per
     * structure but still the same registered entity type - so the variety has to be worked out
     * here, from which structure the spawn position actually falls inside, rather than being
     * baked into two separate entity types. Defaults to {@link Variety#OUTPOST}, which is also
     * correct for anything spawned outside either structure (a spawn egg, a summon command).
     */
    @Override
    public @Nullable SpawnGroupData finalizeSpawn(ServerLevelAccessor level, DifficultyInstance difficulty,
            EntitySpawnReason spawnReason, @Nullable SpawnGroupData groupData) {
        // A trader placed as part of a structure already knows what it is: the
        // template states its Variety. Bail out before the lookup below.
        //
        // This is not just an optimisation. SinglePoolElement.getSettings calls
        // setFinalizeEntities(true), so once the settlements carried their own
        // inhabitants this method started running inside ChunkStatus.FEATURES on
        // the worldgen thread, with `level` a WorldGenRegion. The lookup goes
        // through ServerLevel.structureManager(), whose getStructureAt does
        // getChunk(..., STRUCTURE_REFERENCES) - and off the main thread
        // ServerChunkCache turns that into a supplyAsync(...).join() back onto
        // the main thread, i.e. a synchronous cross-thread chunk request issued
        // from within chunk generation. Vanilla never does this: every
        // generation step passes structureManager().forWorldGenRegion(region)
        // instead, and WorldGenRegion exposes no structure manager of its own.
        if (spawnReason == EntitySpawnReason.STRUCTURE) {
            return super.finalizeSpawn(level, difficulty, spawnReason, groupData);
        }
        Structure encampment = level.getLevel().structureManager().registryAccess()
                .lookupOrThrow(Registries.STRUCTURE)
                .getValue(ResourceKey.create(Registries.STRUCTURE, EchoingVoid.id("tuner_encampment")));
        if (encampment != null
                && level.getLevel().structureManager().getStructureAt(this.blockPosition(), encampment).isValid()) {
            this.variety = Variety.CAMP;
        }
        return super.finalizeSpawn(level, difficulty, spawnReason, groupData);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new TradeWithPlayerGoal(this));
        this.goalSelector.addGoal(1, new PanicGoal(this, 0.5));
        this.goalSelector.addGoal(2, new LookAtTradingPlayerGoal(this));
        this.goalSelector.addGoal(3, new WaterAvoidingRandomStrollGoal(this, 0.4));
        this.goalSelector.addGoal(4, new LookAtPlayerGoal(this, Player.class, 8.0F));
        // Retaliates against whatever last hurt it - see hurt() below, which is what actually
        // sets a target; this goal only decides how the mob fights once one exists.
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
    }

    @Override
    public boolean hurtServer(ServerLevel level, DamageSource source, float amount) {
        boolean hurt = super.hurtServer(level, source, amount);
        if (hurt && source.getEntity() instanceof LivingEntity attacker) {
            this.retaliationTimer = RETALIATION_TICKS;
            this.setLastHurtByMob(attacker);
        }
        return hurt;
    }

    @Override
    public void aiStep() {
        super.aiStep();
        if (retaliationTimer > 0) {
            retaliationTimer--;
        }
        if (!this.level().isClientSide()) {
            restockIfDue();
        }
    }

    /** True while the trader is still willing to fight back - what {@link ProtectorMob} watches. */
    public boolean isRetaliating() {
        return retaliationTimer > 0;
    }

    @Override
    public @Nullable AgeableMob getBreedOffspring(ServerLevel level, AgeableMob partner) {
        return null;
    }

    /** There is a real level now, so the trading screen should show its bar. */
    @Override
    public boolean showProgressBar() {
        return true;
    }

    @Override
    public int getVillagerXp() {
        return this.tradeXp;
    }

    @Override
    public void overrideXp(int xp) {
        this.tradeXp = xp;
    }

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand) {
        ItemStack itemStack = player.getItemInHand(hand);
        if (!itemStack.is(Items.VILLAGER_SPAWN_EGG) && this.isAlive() && !this.isTrading()) {
            if (hand == InteractionHand.MAIN_HAND) {
                player.awardStat(Stats.TALKED_TO_VILLAGER);
            }
            if (!this.level().isClientSide()) {
                if (this.getOffers().isEmpty()) {
                    return InteractionResult.CONSUME;
                }
                this.setTradingPlayer(player);
                this.openTradingScreen(player, this.getDisplayName(), 1);
            }
            return InteractionResult.SUCCESS;
        }
        return super.mobInteract(player, hand);
    }

    /**
     * PLAYER: "make sure that the trader trades can level up as they are traded with more like
     * normal villagers, and their trades are normalised every time."
     *
     * <p>Tier tables, one per level per variety. Trading fills the XP bar; crossing a threshold
     * unlocks the next tier's offers, which are appended so earlier ones stay available - the
     * same shape as a villager's career. Thresholds are vanilla's own
     * ({@code VillagerData.NEXT_LEVEL_XP_THRESHOLDS} = 0/10/70/150/250) rather than invented
     * numbers, so a player who knows how long a villager takes to max out already knows how long
     * this takes.
     */
    private static final int[] LEVEL_XP = {0, 10, 70, 150, 250};
    private static final int MAX_LEVEL = 5;

    /** Vanilla restocks twice a day; this is the same interval, in ticks. */
    private static final int RESTOCK_INTERVAL = 12000;

    private int tradeLevel = 1;
    private int tradeXp;
    private long lastRestock;

    public int tradeLevel() {
        return tradeLevel;
    }

    /**
     * One possible offer. A factory rather than an instance, because a {@link MerchantOffer}
     * carries its own uses counter - handing the same object to two traders would have them
     * share a stock level.
     */
    @FunctionalInterface
    private interface Trade {
        MerchantOffer create(RandomSource random);
    }

    /** How many offers each level contributes, drawn without replacement from that level's pool. */
    private static final int OFFERS_PER_LEVEL = 2;

    /**
     * Every trade a Tuner can know, indexed by the level that unlocks it.
     *
     * <p>PLAYER: "instead of discrete jobs tuners do a bit of everything that is needed, they
     * dont need seperate roles and stations, but their trades do need to be randomised. though
     * they are progressive and traders can level up as we trade more with them, they have the
     * same base trades and as they evolve the trades are also the same. add more varied,
     * echoing void related trades, make it interesting."
     *
     * <p>Two things follow from that, and both are departures from what was here before.
     *
     * <p><b>No roles.</b> The old table branched on {@link Variety}, so an outpost Tuner and a
     * camp Tuner were effectively two professions with two fixed stock lists. There is one pool
     * now and every Tuner draws from all of it - a tuning society where everyone does a bit of
     * whatever is needed, which is what the player described. Variety still exists and still
     * decides where a Tuner spawns and how it behaves; it just no longer dictates what it sells.
     *
     * <p><b>Randomised.</b> Each level offers far more trades than a trader will ever show, and
     * each trader draws {@link #OFFERS_PER_LEVEL} of them at random when it reaches that level.
     * Two Tuners standing side by side at level 3 now stock different things, and finding a
     * trader who happens to sell Knell is worth something. The draw happens once, when the level
     * is reached, and the resulting offers are persisted by the Merchant save - so a trader's
     * stock is stable for that trader forever, which is what makes it worth remembering one.
     *
     * <p>The pool leans on this dimension's own goods rather than on emeralds for everything:
     * hushwater, tuning discs, seeds, void food, phonolite and the Knell line all appear, and
     * several trades buy the player's surplus rather than selling to them.
     */
    private static final List<List<Trade>> TRADE_POOL = List.of(
            // ---- level 1: a stranger who has just arrived can afford these ----
            List.of(
                    r -> sell(Items.EMERALD, 6, ModItems.RESONANCE_SHARD.get(), 3, 12, 5),
                    r -> buy(ModItems.VOID_GLASS_SHARD.get(), 6, Items.EMERALD, 4, 12, 2),
                    r -> sell(Items.EMERALD, 5, ModCrops.RESONANT_BREAD.get(), 4, 16, 3),
                    r -> sell(Items.EMERALD, 3, ModCrops.RESONANT_WHEAT_SEEDS.get(), 6, 16, 2),
                    r -> sell(Items.EMERALD, 4, ModCrops.CHIME_ROOT.get(), 5, 16, 2),
                    r -> buy(ModItems.BISMUTH_SEEDLING.get(), 3, Items.EMERALD, 2, 12, 2),
                    r -> sell(Items.EMERALD, 4, ModItems.RAW_PHONOLITE_ITEM.get(), 8, 12, 3)),

            // ---- level 2: the tools of getting about the place ----
            List.of(
                    r -> sell(Items.EMERALD, 12, ModFluids.HUSHWATER_BUCKET.get(), 1, 8, 8),
                    r -> sell(Items.EMERALD, 10, ModCrops.ECHO_GOURD_SEEDS.get(), 3, 12, 5),
                    r -> buy(ModCrops.RESONANT_GRAIN.get(), 14, Items.EMERALD, 3, 12, 4),
                    r -> sell(Items.EMERALD, 20, Items.IRON_INGOT, 4, 8, 10),
                    r -> buy(ModItems.RESONANCE_SHARD.get(), 12, Items.EMERALD, 5, 10, 5),
                    r -> sell(Items.EMERALD, 8, ModItems.PHONOLITE_BRICKS_ITEM.get(), 8, 12, 4),
                    r -> sell(Items.EMERALD, 14, ModCrops.VOID_TUBER.get(), 6, 10, 5)),

            // ---- level 3: the first things worth crossing over for ----
            List.of(
                    r -> sell(ModItems.RESONANCE_SHARD.get(), 8, ModItems.NULL_IRON_INGOT.get(), 1, 6, 12),
                    r -> sell(Items.EMERALD, 14, ModItems.BISMUTH_SEEDLING.get(), 2, 8, 8),
                    r -> sell(Items.EMERALD, 18, ModCrops.HUMMING_TART.get(), 1, 6, 10),
                    r -> sell(Items.EMERALD, 16, ModItems.VOID_GLASS_ITEM.get(), 4, 8, 8),
                    r -> buy(ModCrops.ECHO_GOURD_SLICE.get(), 12, Items.EMERALD, 3, 10, 6),
                    r -> sell(Items.EMERALD, 22, ModItems.TUNING_FORK.get(), 1, 4, 12),
                    r -> sell(Items.EMERALD, 20, ModItems.FREQUENCY_SIPHON_ITEM.get(), 1, 5, 10)),

            // ---- level 4: a Tuner who trusts you opens the good cupboard ----
            List.of(
                    r -> sell(Items.EMERALD, 26, ModItems.NULL_IRON_INGOT.get(), 2, 5, 15),
                    r -> sell(Items.EMERALD, 30, ModItems.HARMONIC_TUNING_DISC_ALPHA.get(), 1, 2, 18),
                    r -> sell(Items.EMERALD, 30, ModItems.HARMONIC_TUNING_DISC_BETA.get(), 1, 2, 18),
                    r -> sell(Items.EMERALD, 30, ModItems.HARMONIC_TUNING_DISC_GAMMA.get(), 1, 2, 18),
                    r -> sell(Items.EMERALD, 28, ModItems.INVERSION_ANVIL_ITEM.get(), 1, 3, 16),
                    r -> buy(ModItems.NULL_IRON_INGOT.get(), 2, Items.EMERALD, 18, 6, 12)),

            // ---- level 5: the endgame counter ----
            List.of(
                    // The mask is a settlement's last word: trade one all the way up and you
                    // can buy the means to build its own guardian.
                    r -> sell(Items.EMERALD, 40, ModItems.TUNERS_MASK_ITEM.get(), 1, 3, 20),
                    r -> sell(Items.EMERALD, 36, ModKnell.RESONANCE_TEMPLATE.get(), 1, 3, 20),
                    r -> sell(Items.EMERALD, 44, ModKnell.KNELL_INGOT.get(), 1, 2, 22),
                    r -> sell(ModItems.NULL_IRON_INGOT.get(), 6, ModKnell.RAW_KNELL.get(), 1, 3, 20),
                    r -> sell(Items.EMERALD, 34, ModItems.ACOUSTIC_LOCK_BOX_ITEM.get(), 1, 3, 18)));

    /** The player pays {@code cost} and receives {@code result}. */
    private static MerchantOffer sell(net.minecraft.world.item.Item cost, int costCount,
                                      net.minecraft.world.item.Item result, int resultCount,
                                      int maxUses, int xp) {
        return new MerchantOffer(new ItemCost(cost, costCount),
                new ItemStack(result, resultCount), maxUses, xp, 0.05F);
    }

    /** Reads the same as {@link #sell}; named separately so the pool says which way it runs. */
    private static MerchantOffer buy(net.minecraft.world.item.Item cost, int costCount,
                                     net.minecraft.world.item.Item result, int resultCount,
                                     int maxUses, int xp) {
        return sell(cost, costCount, result, resultCount, maxUses, xp);
    }

    /** Offers unlocked at exactly {@code level}, appended when that level is reached. */
    private void addTier(MerchantOffers offers, int level) {
        if (level < 1 || level > TRADE_POOL.size()) {
            return;
        }
        List<Trade> pool = TRADE_POOL.get(level - 1);
        RandomSource random = this.getRandom();

        // Without replacement: a trader must never be shown the same offer twice, and shuffling
        // a copy is the only way to guarantee that when the draw is bigger than one.
        List<Trade> shuffled = new ArrayList<>(pool);
        Collections.shuffle(shuffled, new java.util.Random(random.nextLong()));
        for (int i = 0; i < Math.min(OFFERS_PER_LEVEL, shuffled.size()); i++) {
            offers.add(shuffled.get(i).create(random));
        }
    }

    @Override
    protected void updateTrades(ServerLevel level) {
        if (this.getOffers().isEmpty()) {
            addTier(this.getOffers(), 1);
        }
    }

    /**
     * Trading pays the player in XP orbs as before, and pays the trader in trade XP. Crossing a
     * threshold unlocks the next tier immediately, so the new stock appears in the open screen.
     */
    @Override
    protected void rewardTradeXp(MerchantOffer offer) {
        if (offer.shouldRewardExp()) {
            int popXp = 2 + this.random.nextInt(3);
            this.level().addFreshEntity(new ExperienceOrb(this.level(), this.getX(), this.getY() + 0.5, this.getZ(), popXp));
        }
        this.tradeXp += offer.getXp();
        while (tradeLevel < MAX_LEVEL && tradeXp >= LEVEL_XP[tradeLevel]) {
            tradeLevel++;
            addTier(this.getOffers(), tradeLevel);
            this.level().broadcastEntityEvent(this, (byte) 14); // the villager level-up particles
        }
    }

    @Override
    public boolean canRestock() {
        return true;
    }

    /**
     * "their trades are normalised every time" - every offer's use count goes back to zero on a
     * restock, so a sold-out trader becomes tradeable again rather than being spent forever.
     * Driven off game time rather than an internal counter so it also works for a trader that was
     * unloaded for a while.
     */
    private void restockIfDue() {
        long now = this.level().getGameTime();
        if (now - lastRestock < RESTOCK_INTERVAL) {
            return;
        }
        lastRestock = now;
        for (MerchantOffer offer : this.getOffers()) {
            offer.resetUses();
        }
    }

    @Override
    public boolean removeWhenFarAway(double distSqr) {
        return false;
    }

    @Override
    protected SoundEvent getAmbientSound() {
        return this.isTrading() ? SoundEvents.VILLAGER_TRADE : SoundEvents.VILLAGER_AMBIENT;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.VILLAGER_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.VILLAGER_DEATH;
    }

    @Override
    protected SoundEvent getTradeUpdatedSound(boolean validTrade) {
        return validTrade ? SoundEvents.VILLAGER_YES : SoundEvents.VILLAGER_NO;
    }

    @Override
    public SoundEvent getNotifyTradeSound() {
        return SoundEvents.VILLAGER_YES;
    }

    @Override
    protected void addAdditionalSaveData(ValueOutput output) {
        super.addAdditionalSaveData(output);
        output.putString("Variety", variety.name());
        output.putInt("TradeLevel", tradeLevel);
        output.putInt("TradeXp", tradeXp);
        output.putLong("LastRestock", lastRestock);
    }

    @Override
    protected void readAdditionalSaveData(ValueInput input) {
        super.readAdditionalSaveData(input);
        this.tradeLevel = Math.clamp(input.getIntOr("TradeLevel", 1), 1, MAX_LEVEL);
        this.tradeXp = Math.max(0, input.getIntOr("TradeXp", 0));
        this.lastRestock = input.getLongOr("LastRestock", 0L);
        this.variety = input.getString("Variety")
                .map(name -> {
                    try {
                        return Variety.valueOf(name);
                    } catch (IllegalArgumentException e) {
                        return Variety.OUTPOST;
                    }
                })
                .orElse(Variety.OUTPOST);
    }
}

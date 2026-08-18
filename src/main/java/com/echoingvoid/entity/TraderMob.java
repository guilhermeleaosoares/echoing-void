package com.echoingvoid.entity;

import com.echoingvoid.EchoingVoid;
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

    /** Offers unlocked at exactly {@code level}, appended when that level is reached. */
    private void addTier(MerchantOffers offers, int level) {
        switch (variety) {
            case OUTPOST -> {
                switch (level) {
                    case 1 -> {
                        offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 6),
                                new ItemStack(ModItems.RESONANCE_SHARD.get(), 3), 12, 5, 0.05F));
                        offers.add(new MerchantOffer(new ItemCost(ModItems.VOID_GLASS_SHARD.get(), 6),
                                new ItemStack(Items.EMERALD, 4), 12, 2, 0.05F));
                    }
                    case 2 -> {
                        offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 20),
                                new ItemStack(Items.IRON_INGOT, 4), 8, 10, 0.05F));
                        offers.add(new MerchantOffer(new ItemCost(ModItems.RESONANCE_SHARD.get(), 12),
                                new ItemStack(Items.EMERALD, 5), 10, 5, 0.05F));
                    }
                    case 3 -> {
                        offers.add(new MerchantOffer(new ItemCost(ModItems.RESONANCE_SHARD.get(), 8),
                                new ItemStack(ModItems.NULL_IRON_INGOT.get(), 1), 6, 12, 0.05F));
                        offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 14),
                                new ItemStack(ModItems.BISMUTH_SEEDLING.get(), 2), 8, 8, 0.05F));
                    }
                    case 4 -> offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 26),
                            new ItemStack(ModItems.NULL_IRON_INGOT.get(), 2), 5, 15, 0.05F));
                    // The mask is the outpost's endgame stock: a player who has traded a
                    // settlement all the way up can buy the means to build its guardian.
                    case 5 -> offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 40),
                            new ItemStack(ModItems.TUNERS_MASK_ITEM.get(), 1), 3, 20, 0.05F));
                    default -> { }
                }
            }
            case CAMP -> {
                switch (level) {
                    case 1 -> {
                        offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 4),
                                new ItemStack(Items.COOKED_BEEF, 6), 16, 3, 0.05F));
                        offers.add(new MerchantOffer(new ItemCost(ModItems.BISMUTH_SEEDLING.get(), 3),
                                new ItemStack(Items.EMERALD, 2), 12, 2, 0.05F));
                    }
                    case 2 -> {
                        offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 10),
                                new ItemStack(Items.ARROW, 16), 12, 5, 0.05F));
                        offers.add(new MerchantOffer(new ItemCost(ModItems.RESONANCE_SHARD.get(), 4),
                                new ItemStack(Items.TORCH, 8), 12, 4, 0.05F));
                    }
                    case 3 -> offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 12),
                            new ItemStack(ModItems.RESONANCE_SHARD.get(), 5), 10, 8, 0.05F));
                    case 4 -> offers.add(new MerchantOffer(new ItemCost(ModItems.RESONANCE_SHARD.get(), 10),
                            new ItemStack(Items.EMERALD, 4), 8, 10, 0.05F));
                    case 5 -> offers.add(new MerchantOffer(new ItemCost(Items.EMERALD, 18),
                            new ItemStack(ModItems.VOID_GLASS_SHARD.get(), 4), 6, 15, 0.05F));
                    default -> { }
                }
            }
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

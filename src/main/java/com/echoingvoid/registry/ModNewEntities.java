package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.entity.ChimeMoteEntity;
import com.echoingvoid.entity.DroneAurochEntity;
import com.echoingvoid.entity.ThrumBoarEntity;
import com.echoingvoid.entity.ProtectorMob;
import com.echoingvoid.entity.StrataBurrowerEntity;
import com.echoingvoid.entity.TraderMob;
import com.echoingvoid.entity.TunerShadeEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.SpawnPlacementTypes;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.event.entity.SpawnPlacementRegisterEvent;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/**
 * The three creatures added in the expansion round.
 *
 * <p>They live in their own {@link DeferredRegister} rather than in {@link ModEntities} so the
 * original three keep a file nobody else has reason to touch. Two registers against the same
 * registry is legal and ordinary in Forge; the only thing that has to stay in step is that both are
 * handed the mod bus from the mod constructor.
 *
 * <p>Between them they cover the three roles the dimension was missing: something neutral to look at
 * ({@code chime_mote}), something that fights at range and refuses to be cornered
 * ({@code tuner_shade}), and something that attacks from a direction the player is not watching
 * ({@code strata_burrower}).
 *
 * <p>{@code tuner_trader} and {@code tuners_protector} joined them for the settlement round -
 * a merchant for the outpost and camp, and a guardian only the outpost gets. Both use
 * {@link MobCategory#CREATURE} rather than the {@code MISC} category vanilla villagers and iron
 * golems use, specifically so they participate in {@link net.minecraft.world.level.NaturalSpawner}
 * at all - {@code MISC} is excluded from every periodic spawn pass, which is exactly why real
 * villagers and golems only ever appear via structure placement or village logic. Reaching them
 * only at a structure, without a bespoke placement system of our own, is what the two settlement
 * structures' {@code spawn_overrides} are for - see {@code tools/gen_worldgen.py}.
 */
public final class ModNewEntities {
    private ModNewEntities() {}

    public static final DeferredRegister<EntityType<?>> ENTITIES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, EchoingVoid.MODID);

    /**
     * Ambient, neutral, and the only friendly thing down there. Registered under
     * {@link MobCategory#AMBIENT} so it shares the bat's spawn budget rather than competing with
     * the hostile cap - a cave full of motes must never mean a cave with no monsters in it.
     */
    public static final RegistryObject<EntityType<ChimeMoteEntity>> CHIME_MOTE =
            ENTITIES.register("chime_mote", () -> EntityType.Builder
                    .of(ChimeMoteEntity::new, MobCategory.AMBIENT)
                    .sized(0.7F, 0.9F)
                    .eyeHeight(0.55F)
                    .clientTrackingRange(8)
                    .build(ENTITIES.key("chime_mote")));

    /** A ranged caster that blinks out of melee. Player-sized, so cornering it reads correctly. */
    public static final RegistryObject<EntityType<TunerShadeEntity>> TUNER_SHADE =
            ENTITIES.register("tuner_shade", () -> EntityType.Builder
                    .of(TunerShadeEntity::new, MobCategory.MONSTER)
                    .sized(0.7F, 1.95F)
                    .eyeHeight(1.62F)
                    .clientTrackingRange(10)
                    .notInPeaceful()
                    .build(ENTITIES.key("tuner_shade")));

    /**
     * Long and low: the hitbox is wide enough that the creature cannot hide behind a one-block
     * pillar once it is above ground, which is the fair half of an ambusher.
     */
    public static final RegistryObject<EntityType<StrataBurrowerEntity>> STRATA_BURROWER =
            ENTITIES.register("strata_burrower", () -> EntityType.Builder
                    .of(StrataBurrowerEntity::new, MobCategory.MONSTER)
                    .sized(2.0F, 1.2F)
                    .eyeHeight(0.9F)
                    .clientTrackingRange(10)
                    .notInPeaceful()
                    .build(ENTITIES.key("strata_burrower")));

    /**
     * Villager-sized, so it reads as "a person" rather than a monster at a glance - the whole
     * point of the trade relationship.
     */
    public static final RegistryObject<EntityType<TraderMob>> TUNER_TRADER =
            ENTITIES.register("tuner_trader", () -> EntityType.Builder
                    .of(TraderMob::new, MobCategory.CREATURE)
                    .sized(0.6F, 1.95F)
                    .eyeHeight(1.62F)
                    .clientTrackingRange(10)
                    .build(ENTITIES.key("tuner_trader")));

    /**
     * Iron-golem-shaped - the silhouette the player is meant to recognise as "the thing that
     * keeps this place safe" from across the outpost.
     *
     * <p>Measured off the mesh rather than guessed: {@code build_tuners_protector} spans 38
     * model units tall and 22 wide, which is 2.38 x 1.38 blocks. The first pass registered
     * 2.9 tall, leaving half a block of invisible hitbox standing above the creature's head -
     * arrows would stop in mid-air over it. Vanilla's own iron golem matches its mesh the same
     * way (1.4 x 2.7), so the box is rounded to the mesh, not the other way round.
     */
    public static final RegistryObject<EntityType<ProtectorMob>> TUNERS_PROTECTOR =
            ENTITIES.register("tuners_protector", () -> EntityType.Builder
                    .of(ProtectorMob::new, MobCategory.CREATURE)
                    .sized(1.4F, 2.4F)
                    .eyeHeight(2.1F)
                    .clientTrackingRange(10)
                    .build(ENTITIES.key("tuners_protector")));

    /**
     * PLAYER: "add two mobs, equivilent to overworld cows and pigs, passive mobs that can be
     * killed for their meat."
     *
     * <p>{@link MobCategory#CREATURE}, like every vanilla farm animal - that is what puts them on
     * the passive spawn budget and the daylight spawn cycle rather than making them compete with
     * this dimension's monsters. Sized off their vanilla counterparts so a player reads the pair
     * the same way they read a cow beside a pig: the auroch is the big slow one.
     */
    public static final RegistryObject<EntityType<DroneAurochEntity>> DRONE_AUROCH =
            ENTITIES.register("drone_auroch", () -> EntityType.Builder
                    .of(DroneAurochEntity::new, MobCategory.CREATURE)
                    .sized(0.9F, 1.4F)
                    .eyeHeight(1.3F)
                    .clientTrackingRange(10)
                    .build(ENTITIES.key("drone_auroch")));

    /** The quicker, smaller half of the pair - a pig to the auroch's cow. */
    public static final RegistryObject<EntityType<ThrumBoarEntity>> THRUM_BOAR =
            ENTITIES.register("thrum_boar", () -> EntityType.Builder
                    .of(ThrumBoarEntity::new, MobCategory.CREATURE)
                    .sized(0.9F, 0.9F)
                    .eyeHeight(0.8F)
                    .clientTrackingRange(10)
                    .build(ENTITIES.key("thrum_boar")));

    private static void onAttributes(EntityAttributeCreationEvent event) {
        event.put(CHIME_MOTE.get(), ChimeMoteEntity.createAttributes().build());
        event.put(TUNER_SHADE.get(), TunerShadeEntity.createAttributes().build());
        event.put(STRATA_BURROWER.get(), StrataBurrowerEntity.createAttributes().build());
        event.put(TUNER_TRADER.get(), TraderMob.createAttributes().build());
        event.put(TUNERS_PROTECTOR.get(), ProtectorMob.createAttributes().build());
        event.put(DRONE_AUROCH.get(), DroneAurochEntity.createAttributes().build());
        event.put(THRUM_BOAR.get(), ThrumBoarEntity.createAttributes().build());
    }

    private static void onSpawnPlacements(SpawnPlacementRegisterEvent event) {
        // The mote flies, so it has no ground rule of its own - but it still has to appear over a
        // block that allows spawning, or a cloud of them turns up inside the terrain.
        event.register(CHIME_MOTE.get(), SpawnPlacementTypes.NO_RESTRICTIONS,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Mob::checkMobSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        event.register(TUNER_SHADE.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Monster::checkMonsterSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        event.register(STRATA_BURROWER.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Monster::checkMonsterSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        // Neither trader nor protector is a Monster subtype, so checkMonsterSpawnRules (which
        // needs one) is not an option here - checkMobSpawnRules is the same light-independent,
        // any-Mob rule chime_mote uses above, and that is all a peaceful settlement dweller needs.
        event.register(TUNER_TRADER.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Mob::checkMobSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        event.register(TUNERS_PROTECTOR.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Mob::checkMobSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        // Farm animals stand on the ground, on this dimension's own surfaces.
        //
        // NOT Animal::checkAnimalSpawnRules, and the difference is the whole reason a herd
        // appears at all. That method is:
        //
        //     state(pos.below()).is(ANIMALS_SPAWNABLE_ON) && getRawBrightness(pos, 0) > 8
        //
        // The block half is satisfied by gen_tags.py adding
        // #echoing_void:hollow_horizon_natural_ground to the vanilla tag. The LIGHT half is not,
        // and cannot be: the Hollow Horizon is a deliberately dim dimension - ambient_light 0.14
        // under an end-like fixed sky - so demanding Overworld daylight would leave the surface
        // permanently below the threshold and no animal would ever pass placement. A brightness
        // rule written for a world with a sun does not transfer to one without.
        //
        // The block test is kept in full, because that is what stops a herd spawning inside the
        // rock of a floating island or out over the void.
        // Written out per entity rather than shared: SpawnPredicate is invariant in its type
        // parameter, so one SpawnPredicate<Mob> will not satisfy register(EntityType<DroneAuroch>).
        event.register(DRONE_AUROCH.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                (type, level, reason, pos, random) ->
                        level.getBlockState(pos.below()).is(BlockTags.ANIMALS_SPAWNABLE_ON),
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        event.register(THRUM_BOAR.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                (type, level, reason, pos, random) ->
                        level.getBlockState(pos.below()).is(BlockTags.ANIMALS_SPAWNABLE_ON),
                SpawnPlacementRegisterEvent.Operation.REPLACE);
    }

    public static void register(BusGroup modBus) {
        ENTITIES.register(modBus);
        EntityAttributeCreationEvent.BUS.addListener(ModNewEntities::onAttributes);
        SpawnPlacementRegisterEvent.BUS.addListener(ModNewEntities::onSpawnPlacements);
    }
}

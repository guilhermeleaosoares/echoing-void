package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.entity.EchoWeaverEntity;
import com.echoingvoid.entity.ResonanceWraithEntity;
import com.echoingvoid.entity.StrataGolemEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
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
 * The three things that live in the Hollow Horizon.
 *
 * <p>Attributes are supplied through {@link EntityAttributeCreationEvent}, which fires after
 * registration and before common setup, and natural spawning is opened up through
 * {@link SpawnPlacementRegisterEvent}. Without the latter the biome's spawner list is inert -
 * the weighted entries exist but nothing ever passes placement.
 */
public final class ModEntities {
    private ModEntities() {}

    public static final DeferredRegister<EntityType<?>> ENTITIES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, EchoingVoid.MODID);

    /** Fast, fragile, and happiest on a ceiling. */
    public static final RegistryObject<EntityType<EchoWeaverEntity>> ECHO_WEAVER =
            ENTITIES.register("echo_weaver", () -> EntityType.Builder
                    .of(EchoWeaverEntity::new, MobCategory.MONSTER)
                    .sized(2.6F, 1.5F)
                    .eyeHeight(1.1F)
                    .clientTrackingRange(8)
                    .notInPeaceful()
                    .build(ENTITIES.key("echo_weaver")));

    /** Slow, enormously tough, and shedding crystal as it goes. */
    public static final RegistryObject<EntityType<StrataGolemEntity>> STRATA_GOLEM =
            ENTITIES.register("strata_golem", () -> EntityType.Builder
                    .of(StrataGolemEntity::new, MobCategory.MONSTER)
                    .sized(2.0F, 3.6F)
                    .eyeHeight(3.0F)
                    .clientTrackingRange(10)
                    .notInPeaceful()
                    .build(ENTITIES.key("strata_golem")));

    /** Barely there, and it attacks with sound rather than weight. */
    public static final RegistryObject<EntityType<ResonanceWraithEntity>> RESONANCE_WRAITH =
            ENTITIES.register("resonance_wraith", () -> EntityType.Builder
                    .of(ResonanceWraithEntity::new, MobCategory.MONSTER)
                    .sized(2.2F, 1.4F)
                    .eyeHeight(0.9F)
                    .clientTrackingRange(8)
                    .notInPeaceful()
                    .build(ENTITIES.key("resonance_wraith")));

    private static void onAttributes(EntityAttributeCreationEvent event) {
        event.put(ECHO_WEAVER.get(), EchoWeaverEntity.createAttributes().build());
        event.put(STRATA_GOLEM.get(), StrataGolemEntity.createAttributes().build());
        event.put(RESONANCE_WRAITH.get(), ResonanceWraithEntity.createAttributes().build());
    }

    private static void onSpawnPlacements(SpawnPlacementRegisterEvent event) {
        event.register(ECHO_WEAVER.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Monster::checkMonsterSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        event.register(STRATA_GOLEM.get(), SpawnPlacementTypes.ON_GROUND,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Monster::checkMonsterSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
        // The wraith drifts, so it has no ground requirement and ignores light.
        event.register(RESONANCE_WRAITH.get(), SpawnPlacementTypes.NO_RESTRICTIONS,
                Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                Monster::checkAnyLightMonsterSpawnRules,
                SpawnPlacementRegisterEvent.Operation.REPLACE);
    }

    public static void register(BusGroup modBus) {
        ENTITIES.register(modBus);
        EntityAttributeCreationEvent.BUS.addListener(ModEntities::onAttributes);
        SpawnPlacementRegisterEvent.BUS.addListener(ModEntities::onSpawnPlacements);
    }
}

package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.entity.AcousticLockBoxBlockEntity;
import com.echoingvoid.block.entity.FrequencySiphonBlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.Set;

/**
 * Block entity types.
 *
 * <p>{@code BlockEntityType.Builder} no longer exists in 26.2 - the type is constructed directly
 * from a factory and the set of blocks it is valid for.
 */
public final class ModBlockEntities {
    private ModBlockEntities() {}

    public static final DeferredRegister<BlockEntityType<?>> BLOCK_ENTITIES =
            DeferredRegister.create(ForgeRegistries.BLOCK_ENTITY_TYPES, EchoingVoid.MODID);

    /** Listens for vibrations and reports their frequency as an analog redstone signal. */
    public static final RegistryObject<BlockEntityType<FrequencySiphonBlockEntity>> FREQUENCY_SIPHON =
            BLOCK_ENTITIES.register("frequency_siphon",
                    () -> new BlockEntityType<>(FrequencySiphonBlockEntity::new,
                            Set.of(ModBlocks.FREQUENCY_SIPHON.get())));

    /** Holds the pitch sequence that opens the vault. */
    public static final RegistryObject<BlockEntityType<AcousticLockBoxBlockEntity>> ACOUSTIC_LOCK_BOX =
            BLOCK_ENTITIES.register("acoustic_lock_box",
                    () -> new BlockEntityType<>(AcousticLockBoxBlockEntity::new,
                            Set.of(ModBlocks.ACOUSTIC_LOCK_BOX.get())));

    public static void register(BusGroup modBus) {
        BLOCK_ENTITIES.register(modBus);
    }
}

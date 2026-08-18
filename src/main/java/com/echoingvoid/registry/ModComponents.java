package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.util.ExtraCodecs;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

/**
 * Custom data components - the 26.2 replacement for item NBT.
 *
 * <p>These carry the per-stack state the gear needs: the Sonic Lance's absorbed charge and
 * the Resonance set's banked kinetic damage.
 *
 * <p>Note the registry key: {@code ForgeRegistries} has no DATA_COMPONENT_TYPES entry, so this
 * must go through the vanilla {@link Registries#DATA_COMPONENT_TYPE}.
 */
public final class ModComponents {
    private ModComponents() {}

    public static final DeferredRegister<DataComponentType<?>> COMPONENTS =
            DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, EchoingVoid.MODID);

    /** Charge absorbed by the Sonic Lance, 0..MAX_CHARGE. */
    public static final RegistryObject<DataComponentType<Integer>> SONIC_CHARGE =
            COMPONENTS.register("sonic_charge", () -> DataComponentType.<Integer>builder()
                    .persistent(ExtraCodecs.NON_NEGATIVE_INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    /** Kinetic damage stored by the Resonance armour set, released as a shockwave. */
    public static final RegistryObject<DataComponentType<Float>> STORED_DAMAGE =
            COMPONENTS.register("stored_damage", () -> DataComponentType.<Float>builder()
                    .persistent(Codec.FLOAT)
                    .networkSynchronized(ByteBufCodecs.FLOAT)
                    .build());

    public static final int MAX_CHARGE = 100;
    public static final float MAX_STORED_DAMAGE = 60.0F;

    // ------------------------------------------------------------------ helpers

    public static int getCharge(ItemStack stack) {
        return stack.getOrDefault(SONIC_CHARGE.get(), 0);
    }

    public static void addCharge(ItemStack stack, int delta) {
        stack.update(SONIC_CHARGE.get(), 0, c -> Math.max(0, Math.min(MAX_CHARGE, c + delta)));
    }

    public static void clearCharge(ItemStack stack) {
        stack.set(SONIC_CHARGE.get(), 0);
    }

    public static float getStoredDamage(ItemStack stack) {
        return stack.getOrDefault(STORED_DAMAGE.get(), 0.0F);
    }

    public static void storeDamage(ItemStack stack, float amount) {
        float current = getStoredDamage(stack);
        stack.set(STORED_DAMAGE.get(), Math.min(MAX_STORED_DAMAGE, current + Math.max(0.0F, amount)));
    }

    /** Reads and clears the banked damage in one step. */
    public static float drainStoredDamage(ItemStack stack) {
        float stored = getStoredDamage(stack);
        stack.set(STORED_DAMAGE.get(), 0.0F);
        return stored;
    }

    public static void register(BusGroup modBus) {
        COMPONENTS.register(modBus);
    }
}

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
 * the Resonance and Knell sets' banked kinetic damage.
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

    /** Kinetic damage stored by a resonating armour set, released as a shockwave. */
    public static final RegistryObject<DataComponentType<Float>> STORED_DAMAGE =
            COMPONENTS.register("stored_damage", () -> DataComponentType.<Float>builder()
                    .persistent(Codec.FLOAT)
                    .networkSynchronized(ByteBufCodecs.FLOAT)
                    .build());

    /**
     * Wear on the Knell Aeroshell's WINGS, kept apart from the stack's ordinary
     * {@code DataComponents.DAMAGE}, which is the plate.
     *
     * <p>PLAYER: "the knell aeroshell should have two different durability bars. 1 for wings, 1 for
     * the chestplate. they degrade seperately." An item has exactly one vanilla damage value, so
     * the second pool has to live somewhere - here. See {@code KnellAeroshellItem}.
     */
    public static final RegistryObject<DataComponentType<Integer>> WING_DAMAGE =
            COMPONENTS.register("wing_damage", () -> DataComponentType.<Integer>builder()
                    .persistent(ExtraCodecs.NON_NEGATIVE_INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    public static final int MAX_CHARGE = 100;

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

    /**
     * Adds to the banked total, held under a cap the CALLER supplies.
     *
     * <p>The cap used to be a constant here, which quietly made it impossible for a second
     * armour tier to hold more than the first. It belongs to the armour, not to the component -
     * see {@code ResonanceArmorItem.bankCapacity()} - so it is passed in.
     */
    public static void storeDamage(ItemStack stack, float amount, float cap) {
        float current = getStoredDamage(stack);
        stack.set(STORED_DAMAGE.get(), Math.min(cap, current + Math.max(0.0F, amount)));
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

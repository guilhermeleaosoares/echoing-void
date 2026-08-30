package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.inventory.IntegratorMenu;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.flag.FeatureFlags;
import net.minecraft.world.inventory.MenuType;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

/**
 * Menu types - the mod's first, and so far only.
 *
 * <p>The Knell Integrator used to borrow {@code MenuType.SMITHING} so that the client would build
 * the stock {@code SmithingScreen} for it. That was the cheapest way to get a working screen and it
 * is no longer enough: the station has its own recipe type now, and its own look, so it needs a
 * type of its own for the client to hang a screen on.
 *
 * <p>As with {@link ModRecipes} and {@link ModComponents}, {@code ForgeRegistries} has no entry for
 * menus, so this goes through the vanilla {@link Registries#MENU} key.
 */
public final class ModMenus {
    private ModMenus() {}

    public static final DeferredRegister<MenuType<?>> MENUS =
            DeferredRegister.create(Registries.MENU, EchoingVoid.MODID);

    /**
     * The two-argument constructor is the one the client calls when the server tells it to open
     * this menu; the server side uses the three-argument form with a real
     * {@code ContainerLevelAccess} so that closing the screen returns the input items.
     */
    public static final RegistryObject<MenuType<IntegratorMenu>> KNELL_INTEGRATOR =
            MENUS.register("knell_integrator",
                    () -> new MenuType<>(IntegratorMenu::new, FeatureFlags.VANILLA_SET));

    public static void register(BusGroup modBus) {
        MENUS.register(modBus);
    }
}

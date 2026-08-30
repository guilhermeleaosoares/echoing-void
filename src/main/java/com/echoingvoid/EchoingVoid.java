package com.echoingvoid;

import com.echoingvoid.client.EchoingVoidClient;
import com.echoingvoid.client.VoidTravelOverlay;
import com.echoingvoid.event.AeroshellEvents;
import com.echoingvoid.event.CombatEvents;
import com.echoingvoid.event.FluidEvents;
import com.echoingvoid.event.PlayerTickEvents;
import com.echoingvoid.registry.ModBlockEntities;
import com.echoingvoid.registry.ModBlockFamilies;
import com.echoingvoid.registry.ModBlocks;
import com.echoingvoid.registry.ModNewEntities;
import com.echoingvoid.registry.ModKnell;
import com.echoingvoid.registry.ModComponents;
import com.echoingvoid.registry.ModCreativeTabs;
import com.echoingvoid.registry.ModCrops;
import com.echoingvoid.registry.ModMenus;
import com.echoingvoid.registry.ModRecipes;
import com.echoingvoid.registry.ModTrees;
import com.echoingvoid.registry.ModEffects;
import com.echoingvoid.registry.ModHostOres;
import com.echoingvoid.registry.ModEntities;
import com.echoingvoid.registry.ModFluids;
import com.echoingvoid.registry.ModItems;
import com.echoingvoid.registry.ModTerrainBlocks;
import com.mojang.logging.LogUtils;
import net.minecraft.resources.Identifier;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import org.slf4j.Logger;

/**
 * The Echoing Void - a resonance/acoustics themed dimension mod.
 *
 * <p>Targets Minecraft 26.2 on Forge 26.2-65.1.1 (Java 25).
 *
 * <p>Registration order matters: block entity types name the blocks they are valid for, and the
 * creative tab enumerates the items, so blocks and items are registered before either.
 */
@Mod(EchoingVoid.MODID)
public final class EchoingVoid {
    public static final String MODID = "echoing_void";
    public static final Logger LOGGER = LogUtils.getLogger();

    public EchoingVoid(FMLJavaModLoadingContext context) {
        var modBus = context.getModBusGroup();

        ModEntities.register(modBus);
        ModBlocks.register(modBus);
        ModTerrainBlocks.register(modBus);
        ModHostOres.register(modBus);
        // Wood and stone families consume the logs the terrain registry declares,
        // so they come after it and before the item registry.
        ModBlockFamilies.register(modBus);
        ModKnell.register(modBus);
        // Hushwater. Registered after the blocks it flows over and before the item
        // registry, because its bucket is an item and its liquid form is a block.
        ModFluids.register(modBus);
        // Farming. After ModFluids because void farmland is watered by hushwater,
        // and after ModTerrainBlocks because it is tilled out of resonance moss.
        ModCrops.register(modBus);
        ModTrees.register(modBus);
        ModNewEntities.register(modBus);
        // Structure processors - the ground-support legs that stop pieces floating.
        com.echoingvoid.worldgen.ModProcessors.register(modBus);
        ModItems.register(modBus);
        ModBlockEntities.register(modBus);
        ModComponents.register(modBus);
        ModRecipes.register(modBus);
        ModMenus.register(modBus);
        ModEffects.register(modBus);
        ModCreativeTabs.register(modBus);

        // No-op on a dedicated server; it checks the dist before touching client classes.
        EchoingVoidClient.register(modBus);
        // Replaces the nether portal's purple screen tint with the void effect,
        // for our portal only. Dist-guarded no-op on a dedicated server.
        VoidTravelOverlay.register();

        // Game-bus listeners. These are EventBus 7 static buses, not an IEventBus instance.
        CombatEvents.register();
        AeroshellEvents.register();
        PlayerTickEvents.register();
        FluidEvents.register();

        LOGGER.info("The Echoing Void is listening.");
    }

    /** Namespaced identifier helper. */
    public static Identifier id(String path) {
        return Identifier.fromNamespaceAndPath(MODID, path);
    }
}

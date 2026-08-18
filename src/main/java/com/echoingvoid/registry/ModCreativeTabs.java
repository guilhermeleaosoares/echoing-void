package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

import java.util.function.Consumer;

/**
 * The mod's creative tabs.
 *
 * <p>Split in two rather than piled into one. With thirty-odd blocks already and the stone and
 * wood families still to land, a single tab becomes an undifferentiated wall of icons that is
 * slower to search than the vanilla tabs it sits beside. Blocks and gear are the split a player
 * actually thinks in: "what am I building with" versus "what am I carrying".
 *
 * <p>Items are sorted by what they ARE - anything that places a block goes to the block tab, and
 * everything else to the gear tab - so new registrations land in the right place automatically
 * rather than needing a list kept in step by hand.
 */
public final class ModCreativeTabs {
    private ModCreativeTabs() {}

    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, EchoingVoid.MODID);

    /** Terrain, building blocks, plants, machines - everything that goes in the world. */
    public static final RegistryObject<CreativeModeTab> BLOCKS_TAB = TABS.register("echoing_void_blocks",
            () -> CreativeModeTab.builder()
                    .withTabsBefore(CreativeModeTabs.COMBAT)
                    .title(Component.translatable("itemGroup.echoing_void_blocks"))
                    .icon(() -> ModBlocks.PHONOLITE_BRICKS.get().asItem().getDefaultInstance())
                    .displayItems((params, output) -> forEachRegistered(output, true))
                    .build());

    /** Materials, tools, weapons, armour, discs, spawn eggs. */
    public static final RegistryObject<CreativeModeTab> GEAR_TAB = TABS.register("echoing_void_gear",
            () -> CreativeModeTab.builder()
                    .withTabsBefore(CreativeModeTabs.COMBAT)
                    .title(Component.translatable("itemGroup.echoing_void_gear"))
                    .icon(() -> ModItems.HARMONIC_PICKAXE.get().getDefaultInstance())
                    .displayItems((params, output) -> forEachRegistered(output, false))
                    .build());

    /**
     * Walks every item this mod registers and emits the ones matching the requested kind.
     *
     * @param wantBlocks true for the block tab, false for the gear tab
     */
    private static void forEachRegistered(CreativeModeTab.Output output, boolean wantBlocks) {
        Consumer<RegistryObject<Item>> emit = entry -> {
            Item item = entry.get();
            if (item instanceof BlockItem == wantBlocks) {
                output.accept(item);
            }
        };
        ModItems.tabOrder().forEach(emit);
        ModTerrainBlocks.tabOrder().forEach(emit);
        ModEffects.tabOrder().forEach(emit);
        ModHostOres.tabOrder().forEach(emit);
    }

    public static void register(BusGroup modBus) {
        TABS.register(modBus);
    }
}

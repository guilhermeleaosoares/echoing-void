package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.NullIronOreBlock;
import com.echoingvoid.block.ResonanceLeavesBlock;
import com.echoingvoid.block.ResonantBismuthOreBlock;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * The host-matched ore variants, plus the fourth leaf colour.
 *
 * <p>An ore has to look like the rock it is embedded in. The Overworld variants are drawn on
 * vanilla stone and deepslate, and these are the Hollow Horizon counterparts cut into Phonolite,
 * so the same resource reads correctly wherever it is found rather than carrying its home rock
 * around with it. The naming follows vanilla, where the unprefixed id is the stone one and the
 * host is named only when it differs.
 *
 * <p>Ashen Resonance Leaves live here rather than with the other terrain blocks purely because
 * they arrived in the same round as Echo Ash, the pale wood they belong to.
 */
public final class ModHostOres {
    private ModHostOres() {}

    /** Matches the pale bone hue of the chalk family. */
    private static final int MOTE_ASHEN = 0xC9D3E2;

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);
    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ------------------------------------------------------------------ ores

    /** Resonant Bismuth as it appears in the Hollow Horizon, cut into Phonolite. */
    public static final RegistryObject<Block> PHONOLITE_RESONANT_BISMUTH_ORE =
            BLOCKS.register("phonolite_resonant_bismuth_ore",
                    () -> new ResonantBismuthOreBlock(props("phonolite_resonant_bismuth_ore")
                            .mapColor(MapColor.DEEPSLATE)
                            .strength(4.5F, 3.0F)
                            .sound(SoundType.BASALT)
                            .lightLevel(state -> 3)
                            .requiresCorrectToolForDrops()));

    /** Null-Iron in deepslate: the Overworld's deep band. Tougher than the stone variant. */
    public static final RegistryObject<Block> DEEPSLATE_NULL_IRON_ORE =
            BLOCKS.register("deepslate_null_iron_ore",
                    () -> new NullIronOreBlock(props("deepslate_null_iron_ore")
                            .mapColor(MapColor.COLOR_BLACK)
                            .strength(5.5F, 6.0F)
                            .sound(SoundType.DEEPSLATE)
                            .requiresCorrectToolForDrops()));

    /** Null-Iron as it appears in the Hollow Horizon. */
    public static final RegistryObject<Block> PHONOLITE_NULL_IRON_ORE =
            BLOCKS.register("phonolite_null_iron_ore",
                    () -> new NullIronOreBlock(props("phonolite_null_iron_ore")
                            .mapColor(MapColor.COLOR_BLACK)
                            .strength(5.0F, 6.0F)
                            .sound(SoundType.ANCIENT_DEBRIS)
                            .requiresCorrectToolForDrops()));

    // ---------------------------------------------------------------- canopy

    /** The Echo Ash canopy: the pale fourth hue against teal, gold and violet. */
    public static final RegistryObject<Block> ASHEN_RESONANCE_LEAVES =
            BLOCKS.register("ashen_resonance_leaves",
                    () -> new ResonanceLeavesBlock(MOTE_ASHEN, props("ashen_resonance_leaves")
                            .mapColor(MapColor.QUARTZ)
                            .strength(0.4F, 0.2F)
                            .sound(SoundType.AZALEA_LEAVES)
                            .lightLevel(state -> 2)
                            .noOcclusion()));

    // ----------------------------------------------------------- block items

    public static final RegistryObject<Item> PHONOLITE_RESONANT_BISMUTH_ORE_ITEM =
            blockItem("phonolite_resonant_bismuth_ore", PHONOLITE_RESONANT_BISMUTH_ORE);
    public static final RegistryObject<Item> DEEPSLATE_NULL_IRON_ORE_ITEM =
            blockItem("deepslate_null_iron_ore", DEEPSLATE_NULL_IRON_ORE);
    public static final RegistryObject<Item> PHONOLITE_NULL_IRON_ORE_ITEM =
            blockItem("phonolite_null_iron_ore", PHONOLITE_NULL_IRON_ORE);
    public static final RegistryObject<Item> ASHEN_RESONANCE_LEAVES_ITEM =
            blockItem("ashen_resonance_leaves", ASHEN_RESONANCE_LEAVES);

    // ---------------------------------------------------------------- helpers

    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    private static RegistryObject<Item> blockItem(String name, Supplier<? extends Block> block) {
        RegistryObject<Item> item = ITEMS.register(name,
                () -> new BlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name))
                        .useBlockDescriptionPrefix()));
        TAB_ORDER.add(item);
        return item;
    }

    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

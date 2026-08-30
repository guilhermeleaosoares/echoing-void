package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.VoidSaplingBlock;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.grower.TreeGrower;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * One sapling per void tree.
 *
 * <p>PLAYER: "deprecate the bismuth seedling, and replace it with saplings for every different void
 * tree type."
 *
 * <p>The Bismuth Seedling was a plain {@code Item} - unplantable - and all four canopies dropped it,
 * so felling an Amber Bough and an Echo Ash gave the same souvenir and grew neither. Each canopy now
 * drops its own sapling, and each sapling grows the tree it fell from:
 *
 * <table border="1">
 *   <caption>The four trees</caption>
 *   <tr><th>sapling</th><th>canopy it drops from</th><th>grows</th></tr>
 *   <tr><td>petrified_tuning_sapling</td><td>calcified_resonance_leaves</td><td>petrified_grove</td></tr>
 *   <tr><td>echo_ash_sapling</td><td>ashen_resonance_leaves</td><td>echo_ash_grove</td></tr>
 *   <tr><td>amber_bough_sapling</td><td>amber_resonance_leaves</td><td>amber_bough_grove</td></tr>
 *   <tr><td>humming_sapling</td><td>violet_resonance_leaves</td><td>humming_grove</td></tr>
 * </table>
 *
 * <p>Each grower points at the GROVE feature rather than at one of the three shapes beneath it.
 * A grove is a {@code random_selector} over slim, branched and giant, so a planted sapling has the
 * same spread of outcomes as a naturally generated tree instead of always producing the smallest.
 */
public final class ModTrees {
    private ModTrees() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ---------------------------------------------------------------- growers
    // TreeGrower registers itself into a static name->grower map on construction, and its
    // CODEC resolves through that map - so these names are the ids the blockstate files
    // round-trip through and must stay stable.

    private static ResourceKey<ConfiguredFeature<?, ?>> grove(String name) {
        return ResourceKey.create(Registries.CONFIGURED_FEATURE, EchoingVoid.id(name));
    }

    private static TreeGrower grower(String name, String feature) {
        return new TreeGrower(EchoingVoid.MODID + ":" + name,
                Optional.empty(), Optional.of(grove(feature)), Optional.empty());
    }

    public static final TreeGrower PETRIFIED_TUNING =
            grower("petrified_tuning", "petrified_grove");
    public static final TreeGrower ECHO_ASH = grower("echo_ash", "echo_ash_grove");
    public static final TreeGrower AMBER_BOUGH = grower("amber_bough", "amber_bough_grove");
    public static final TreeGrower HUMMING = grower("humming", "humming_grove");

    // --------------------------------------------------------------- saplings

    public static final RegistryObject<Block> PETRIFIED_TUNING_SAPLING =
            sapling("petrified_tuning_sapling", PETRIFIED_TUNING, MapColor.COLOR_LIGHT_GRAY);
    public static final RegistryObject<Block> ECHO_ASH_SAPLING =
            sapling("echo_ash_sapling", ECHO_ASH, MapColor.COLOR_GRAY);
    public static final RegistryObject<Block> AMBER_BOUGH_SAPLING =
            sapling("amber_bough_sapling", AMBER_BOUGH, MapColor.GOLD);
    public static final RegistryObject<Block> HUMMING_SAPLING =
            sapling("humming_sapling", HUMMING, MapColor.COLOR_PURPLE);

    public static final RegistryObject<Item> PETRIFIED_TUNING_SAPLING_ITEM =
            blockItem("petrified_tuning_sapling", PETRIFIED_TUNING_SAPLING);
    public static final RegistryObject<Item> ECHO_ASH_SAPLING_ITEM =
            blockItem("echo_ash_sapling", ECHO_ASH_SAPLING);
    public static final RegistryObject<Item> AMBER_BOUGH_SAPLING_ITEM =
            blockItem("amber_bough_sapling", AMBER_BOUGH_SAPLING);
    public static final RegistryObject<Item> HUMMING_SAPLING_ITEM =
            blockItem("humming_sapling", HUMMING_SAPLING);

    // ---------------------------------------------------------------- helpers

    /** Vanilla sapling properties: no collision, instant break, random-ticked so it can grow. */
    private static RegistryObject<Block> sapling(String name, TreeGrower grower, MapColor colour) {
        return BLOCKS.register(name, () -> new VoidSaplingBlock(grower,
                BlockBehaviour.Properties.of()
                        .setId(BLOCKS.key(name))
                        .mapColor(colour)
                        .noCollision()
                        .randomTicks()
                        .instabreak()
                        .sound(SoundType.GRASS)
                        .pushReaction(PushReaction.DESTROY)));
    }

    private static RegistryObject<Item> blockItem(String name, RegistryObject<Block> block) {
        RegistryObject<Item> item = ITEMS.register(name,
                () -> new BlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name))
                        .useBlockDescriptionPrefix()));
        TAB_ORDER.add(item);
        return item;
    }

    /** Read by ModCreativeTabs, in the order declared above. */
    public static List<RegistryObject<Item>> tabOrder() {
        return List.copyOf(TAB_ORDER);
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

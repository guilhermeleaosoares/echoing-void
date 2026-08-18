package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.BismuthClusterBlock;
import com.echoingvoid.block.HummingCrystalBlock;
import com.echoingvoid.block.HummingStemBlock;
import com.echoingvoid.block.ResonanceLeavesBlock;
import com.echoingvoid.block.VoidPlantBlock;
import net.minecraft.util.ColorRGBA;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.ColoredFallingBlock;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.properties.NoteBlockInstrument;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * The eighteen environment blocks that give the Hollow Horizon its terrain.
 *
 * <p>Gameplay intent, and the reason this class exists at all: the dimension shipped built from
 * three near-black blocks, which made it unreadable to navigate and dull to look at. The set here
 * is sized against the Nether's roughly twenty-five surface blocks and is organised so that
 * <em>altitude is legible from colour alone</em> - pale Resonant Chalk in the highlands, blue-grey
 * Echo Slate through the middle, warm Amber Strata below that, and the old near-black Raw Phonolite
 * only at depth, where Humming Crystal lights it. On top of that spine sit two opposed ground
 * covers, three canopy hues, a second timber, two crystal light sources and three cross-model
 * growths, so no two neighbouring surfaces read as the same material.
 *
 * <p>Every hardness, blast resistance, mining tool and light level here is taken verbatim from
 * {@code docs/spec/art_direction.json}. As in {@link ModBlocks}, mining tool and tier are expressed
 * through block tags rather than Java - 26.2 has no API for either, so the code contributes only
 * {@code requiresCorrectToolForDrops()} and {@code tools/gen_terrain_tags.py} decides the rest.
 *
 * <p>This class keeps its own {@link DeferredRegister} pair rather than extending {@link ModBlocks}
 * so the terrain set can be generated, reviewed and regenerated without touching the hand-written
 * headline blocks. Both registers target the same Forge registries under the same namespace, which
 * Forge supports; ids simply must not collide.
 */
public final class ModTerrainBlocks {
    private ModTerrainBlocks() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    /** Block items in the order the creative tab should list them. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ------------------------------------------------------------ mote colours
    // Taken straight from the palette in art_direction.json so a block's particles
    // match the hue of its own texture.

    private static final int MOTE_BISMUTH = 0x3FD0E0;
    private static final int MOTE_ARCANE = 0xB14A9E;
    private static final int MOTE_AMBER = 0xE8C87A;

    // ------------------------------------------------------------------ strata
    // The value spine of the dimension, lightest at the top of the world down to
    // darkest at the bottom.

    /** Hardness 1.5 / Blast 6.0 | Pickaxe | CALCITE | the pale highland stone. */
    public static final RegistryObject<Block> RESONANT_CHALK = BLOCKS.register("resonant_chalk",
            () -> new Block(props("resonant_chalk")
                    .mapColor(MapColor.CLAY)
                    .strength(1.5F, 6.0F)
                    .sound(SoundType.CALCITE)
                    .requiresCorrectToolForDrops()));

    /** Hardness 3.0 / Blast 6.0 | Pickaxe | DEEPSLATE | blue-grey transition band. */
    public static final RegistryObject<Block> ECHO_SLATE = BLOCKS.register("echo_slate",
            () -> new Block(props("echo_slate")
                    .mapColor(MapColor.TERRACOTTA_LIGHT_BLUE)
                    .strength(3.0F, 6.0F)
                    .sound(SoundType.DEEPSLATE)
                    .requiresCorrectToolForDrops()));

    /** Hardness 2.5 / Blast 6.0 | Pickaxe | TUFF | the one warm band in the terrain. */
    public static final RegistryObject<Block> AMBER_STRATA = BLOCKS.register("amber_strata",
            () -> new Block(props("amber_strata")
                    .mapColor(MapColor.TERRACOTTA_ORANGE)
                    .strength(2.5F, 6.0F)
                    .sound(SoundType.TUFF)
                    .requiresCorrectToolForDrops()));

    /**
     * Hardness 1.5 / Blast 1.0 | Pickaxe | AMETHYST | Light 11 | lights the deep strata.
     *
     * <p>Left fully occluding despite art_direction.json marking it translucent: the shipped
     * sprite has no transparent or partially transparent pixel in it, so treating it as
     * see-through would cost a sorted transparency pass and a hole in the light occlusion map to
     * render something pixel-identical to the solid version. Its presence comes from the emissive
     * palette and light level 11 instead.
     */
    public static final RegistryObject<Block> HUMMING_CRYSTAL = BLOCKS.register("humming_crystal",
            () -> new HummingCrystalBlock(props("humming_crystal")
                    .mapColor(MapColor.COLOR_MAGENTA)
                    .strength(1.5F, 1.0F)
                    .sound(SoundType.AMETHYST)
                    .lightLevel(state -> 11)
                    .requiresCorrectToolForDrops()));

    // ------------------------------------------------------------ worked stone

    /** Hardness 2.0 / Blast 6.0 | Pickaxe | CALCITE | Tuner outpost walls. */
    public static final RegistryObject<Block> CHALK_BRICKS = BLOCKS.register("chalk_bricks",
            () -> new Block(props("chalk_bricks")
                    .mapColor(MapColor.CLAY)
                    .strength(2.0F, 6.0F)
                    .sound(SoundType.CALCITE)
                    .requiresCorrectToolForDrops()));

    /** Hardness 5.0 / Blast 6.0 | Pickaxe (Diamond) | BASALT | worked form of Raw Phonolite. */
    public static final RegistryObject<Block> POLISHED_PHONOLITE = BLOCKS.register("polished_phonolite",
            () -> new Block(props("polished_phonolite")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(5.0F, 6.0F)
                    .sound(SoundType.BASALT)
                    .requiresCorrectToolForDrops()));

    // ----------------------------------------------------------- loose ground

    /**
     * Hardness 0.5 / Blast 0.5 | Shovel | SAND | falls under gravity.
     *
     * <p>Uses vanilla's {@link ColoredFallingBlock} directly: the only thing a sand-like block adds
     * over {@code FallingBlock} is the colour of its falling-dust particle, and that is a
     * constructor argument, not behaviour worth subclassing for.
     */
    public static final RegistryObject<Block> CHIME_SAND = BLOCKS.register("chime_sand",
            () -> new ColoredFallingBlock(new ColorRGBA(0xFFC9D3E2), props("chime_sand")
                    .mapColor(MapColor.QUARTZ)
                    .instrument(NoteBlockInstrument.SNARE)
                    .strength(0.5F, 0.5F)
                    .sound(SoundType.SAND)));

    // ----------------------------------------------------------- ground cover
    // Two covers in opposing hues. One material over the whole surface is what made
    // the old build read as a single grey mass.

    /** Hardness 0.4 / Blast 0.4 | Hoe | MOSS | Light 4 | marks walkable, lit ground. */
    public static final RegistryObject<Block> RESONANCE_MOSS = BLOCKS.register("resonance_moss",
            () -> new Block(props("resonance_moss")
                    .mapColor(MapColor.WARPED_NYLIUM)
                    .strength(0.4F, 0.4F)
                    .sound(SoundType.MOSS)
                    .lightLevel(state -> 4)));

    /** Hardness 0.4 / Blast 0.4 | Hoe | MOSS | Light 2 | the warm counterpart to the moss. */
    public static final RegistryObject<Block> AMBER_LICHEN = BLOCKS.register("amber_lichen",
            () -> new Block(props("amber_lichen")
                    .mapColor(MapColor.COLOR_ORANGE)
                    .strength(0.4F, 0.4F)
                    .sound(SoundType.MOSS)
                    .lightLevel(state -> 2)));

    // ------------------------------------------------------------------- wood

    /** Hardness 3.0 / Blast 3.0 | Axe | NETHER_WOOD | strippable violet timber. */
    public static final RegistryObject<Block> HUMMING_STEM = BLOCKS.register("humming_stem",
            () -> new HummingStemBlock(props("humming_stem")
                    .mapColor(MapColor.TERRACOTTA_PURPLE)
                    .strength(3.0F, 3.0F)
                    .sound(SoundType.NETHER_WOOD)));

    /** Stripped form produced by an axe. */
    public static final RegistryObject<Block> STRIPPED_HUMMING_STEM = BLOCKS.register("stripped_humming_stem",
            () -> new RotatedPillarBlock(props("stripped_humming_stem")
                    .mapColor(MapColor.TERRACOTTA_MAGENTA)
                    .strength(3.0F, 3.0F)
                    .sound(SoundType.NETHER_WOOD)));

    // ----------------------------------------------------------------- canopy
    // Three leaf hues across the mod (these two plus Calcified Resonance Leaves in
    // ModBlocks) so a grove is told apart by colour, not by transparency.

    /** Hardness 0.4 / Blast 0.2 | Shears / Hoe | AZALEA_LEAVES | Light 3 | gold canopy. */
    public static final RegistryObject<Block> AMBER_RESONANCE_LEAVES = BLOCKS.register("amber_resonance_leaves",
            () -> new ResonanceLeavesBlock(MOTE_AMBER, props("amber_resonance_leaves")
                    .mapColor(MapColor.GOLD)
                    .strength(0.4F, 0.2F)
                    .sound(SoundType.AZALEA_LEAVES)
                    .lightLevel(state -> 3)
                    .noOcclusion()));

    /** Hardness 0.4 / Blast 0.2 | Shears / Hoe | AZALEA_LEAVES | Light 5 | the rarest canopy. */
    public static final RegistryObject<Block> VIOLET_RESONANCE_LEAVES = BLOCKS.register("violet_resonance_leaves",
            () -> new ResonanceLeavesBlock(MOTE_ARCANE, props("violet_resonance_leaves")
                    .mapColor(MapColor.COLOR_PURPLE)
                    .strength(0.4F, 0.2F)
                    .sound(SoundType.AZALEA_LEAVES)
                    .lightLevel(state -> 5)
                    .noOcclusion()));

    // ----------------------------------------------------------------- crystal

    /** Hardness 1.5 / Blast 1.0 | Pickaxe | AMETHYST_CLUSTER | Light 7 | directional, waterloggable. */
    public static final RegistryObject<Block> BISMUTH_CLUSTER = BLOCKS.register("bismuth_cluster",
            () -> new BismuthClusterBlock(props("bismuth_cluster")
                    .mapColor(MapColor.COLOR_CYAN)
                    .strength(1.5F, 1.0F)
                    .sound(SoundType.AMETHYST_CLUSTER)
                    .lightLevel(state -> 7)
                    .noOcclusion()));

    /** Hardness 3.5 / Blast 3.5 | Pickaxe | LANTERN | Light 15 | the craftable light source. */
    public static final RegistryObject<Block> HARMONIC_LANTERN = BLOCKS.register("harmonic_lantern",
            () -> new Block(props("harmonic_lantern")
                    .mapColor(MapColor.COLOR_LIGHT_BLUE)
                    .strength(3.5F, 3.5F)
                    .sound(SoundType.LANTERN)
                    .lightLevel(state -> 15)));

    // ------------------------------------------------------------ ground cover
    // Cross-model growths. Instant-break, no collision, and displaced by a random
    // XZ offset so a dense patch does not sit on a visible grid.

    /** Instant break | GRASS | Light 3 | glowing teal sprout, scattered over mossy ground. */
    public static final RegistryObject<Block> ECHO_SPROUT = BLOCKS.register("echo_sprout",
            () -> new VoidPlantBlock(MOTE_BISMUTH, plantProps("echo_sprout")
                    .mapColor(MapColor.COLOR_CYAN)
                    .lightLevel(state -> 3)));

    /** Instant break | GRASS | pale cyan wisps that catch the light. */
    public static final RegistryObject<Block> CHIME_GRASS = BLOCKS.register("chime_grass",
            () -> new VoidPlantBlock(MOTE_BISMUTH, plantProps("chime_grass")
                    .mapColor(MapColor.COLOR_LIGHT_BLUE)));

    /** Instant break | GRASS | Light 4 | the magenta flower-analogue. */
    public static final RegistryObject<Block> CRYSTAL_BLOOM = BLOCKS.register("crystal_bloom",
            () -> new VoidPlantBlock(MOTE_ARCANE, plantProps("crystal_bloom")
                    .mapColor(MapColor.COLOR_MAGENTA)
                    .lightLevel(state -> 4)));

    // ------------------------------------------------------------- block items
    // Registration order here is creative-tab order: the stone spine first, then
    // worked stone, loose ground, cover, timber, canopy, light, and clutter last.

    public static final RegistryObject<Item> RESONANT_CHALK_ITEM = blockItem("resonant_chalk", RESONANT_CHALK);
    public static final RegistryObject<Item> ECHO_SLATE_ITEM = blockItem("echo_slate", ECHO_SLATE);
    public static final RegistryObject<Item> AMBER_STRATA_ITEM = blockItem("amber_strata", AMBER_STRATA);
    public static final RegistryObject<Item> HUMMING_CRYSTAL_ITEM = blockItem("humming_crystal", HUMMING_CRYSTAL);
    public static final RegistryObject<Item> CHALK_BRICKS_ITEM = blockItem("chalk_bricks", CHALK_BRICKS);
    public static final RegistryObject<Item> POLISHED_PHONOLITE_ITEM = blockItem("polished_phonolite", POLISHED_PHONOLITE);
    public static final RegistryObject<Item> CHIME_SAND_ITEM = blockItem("chime_sand", CHIME_SAND);
    public static final RegistryObject<Item> RESONANCE_MOSS_ITEM = blockItem("resonance_moss", RESONANCE_MOSS);
    public static final RegistryObject<Item> AMBER_LICHEN_ITEM = blockItem("amber_lichen", AMBER_LICHEN);
    public static final RegistryObject<Item> HUMMING_STEM_ITEM = blockItem("humming_stem", HUMMING_STEM);
    public static final RegistryObject<Item> STRIPPED_HUMMING_STEM_ITEM = blockItem("stripped_humming_stem", STRIPPED_HUMMING_STEM);
    public static final RegistryObject<Item> AMBER_RESONANCE_LEAVES_ITEM = blockItem("amber_resonance_leaves", AMBER_RESONANCE_LEAVES);
    public static final RegistryObject<Item> VIOLET_RESONANCE_LEAVES_ITEM = blockItem("violet_resonance_leaves", VIOLET_RESONANCE_LEAVES);
    public static final RegistryObject<Item> BISMUTH_CLUSTER_ITEM = blockItem("bismuth_cluster", BISMUTH_CLUSTER);
    public static final RegistryObject<Item> HARMONIC_LANTERN_ITEM = blockItem("harmonic_lantern", HARMONIC_LANTERN);
    public static final RegistryObject<Item> ECHO_SPROUT_ITEM = blockItem("echo_sprout", ECHO_SPROUT);
    public static final RegistryObject<Item> CHIME_GRASS_ITEM = blockItem("chime_grass", CHIME_GRASS);
    public static final RegistryObject<Item> CRYSTAL_BLOOM_ITEM = blockItem("crystal_bloom", CRYSTAL_BLOOM);

    // ---------------------------------------------------------------- helpers

    /** Shared starting point: every block must carry its own registry id in 26.2. */
    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    /**
     * The shape every cross-model growth shares, copied from vanilla short grass: replaceable so
     * the player can build straight through a patch, no collision, instant break, destroyed rather
     * than dragged by pistons, and randomly offset in XZ so a field does not look tiled.
     */
    private static BlockBehaviour.Properties plantProps(String name) {
        return props(name)
                .replaceable()
                .noCollision()
                .instabreak()
                .sound(SoundType.GRASS)
                .offsetType(BlockBehaviour.OffsetType.XZ)
                .pushReaction(PushReaction.DESTROY);
    }

    /** The item form of a block, tracked for the creative tab. */
    private static RegistryObject<Item> blockItem(String name, Supplier<? extends Block> block) {
        RegistryObject<Item> item = ITEMS.register(name,
                () -> new BlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name))));
        TAB_ORDER.add(item);
        return item;
    }

    /** Every terrain block item, in the order the creative tab should show them. */
    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

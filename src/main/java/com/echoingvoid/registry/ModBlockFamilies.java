package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.ResonantLogBlock;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.DoubleHighBlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.DoorBlock;
import net.minecraft.world.level.block.FenceBlock;
import net.minecraft.world.level.block.FenceGateBlock;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.TrapDoorBlock;
import net.minecraft.world.level.block.WallBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockSetType;
import net.minecraft.world.level.block.state.properties.WoodType;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import org.jspecify.annotations.Nullable;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The full vanilla block family for every stone and every wood the mod ships: 21 stone variants and
 * 40 new wood variants, 61 blocks.
 *
 * <p>Gameplay intent, and the whole reason this class exists: a building material a player cannot
 * cut into a slab, a stair or a wall is a material they will not build with. The dimension shipped
 * with full cubes only, which is why its structures read as boxes and why players stopped using its
 * stone the moment they got home. Seven stones now cut to slab / stairs / wall, and four woods carry
 * the complete set - log, stripped log, bark, stripped bark, planks, slab, stairs, fence, fence gate,
 * door, trapdoor - so a Tuner outpost can be built with the same vocabulary as a vanilla village.
 *
 * <h2>What is registered here and what is not</h2>
 * Petrified Tuning Wood and Humming Stem already exist as trunks, in {@link ModBlocks} and
 * {@link ModTerrainBlocks} respectively, along with their stripped forms. Those four blocks are
 * referenced, never re-registered. Everything else in all four woods is new here, as are all 21
 * stone variants. The seven stone bases themselves also live in the two older registries.
 *
 * <h2>Registration order is load-bearing</h2>
 * {@link StairBlock} takes a concrete {@code BlockState} for the block it is cut from - vanilla
 * passes {@code OAK_PLANKS.defaultBlockState()} - so a stair's supplier has to be able to resolve
 * its base block while the block registry event is being handled. Forge's {@code DeferredRegister}
 * calls each entry's supplier and then immediately rebinds that entry's {@code RegistryObject},
 * walking its entries in insertion order, so:
 *
 * <ul>
 *   <li>within this class, every planks block is declared above the slab and stairs cut from it;</li>
 *   <li>across classes, {@code ModBlockFamilies.register} must run AFTER {@code ModBlocks.register}
 *       and {@code ModTerrainBlocks.register} in {@code EchoingVoid}, because the seven stone bases
 *       and the two existing trunks live there.</li>
 * </ul>
 *
 * <p>Mining tool and tier are not expressed in Java in 26.2 and are not expressed here. As in the
 * two older registries the code contributes only {@code requiresCorrectToolForDrops()} on stone;
 * {@code tools/gen_family_tags.py} decides tool, tier, and the vanilla behaviour tags that make
 * fences connect and doors open. Nothing here sets {@code .instrument(...)} either, matching the
 * existing files rather than vanilla, so the note-block sound of our blocks stays uniform.
 */
public final class ModBlockFamilies {
    private ModBlockFamilies() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    /** Block items in the order the creative tab should list them. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    private static final List<StoneFamily> STONE_FAMILIES = new ArrayList<>();
    private static final List<WoodFamily> WOOD_FAMILIES = new ArrayList<>();

    /** Trunk or bark block -> what an axe turns it into. Resolved to blocks lazily, see below. */
    private static final Map<RegistryObject<Block>, RegistryObject<Block>> STRIPPING = new LinkedHashMap<>();

    /** The block-keyed view of {@link #STRIPPING}, built on first strip. See {@link #strippedForm}. */
    private static volatile @Nullable Map<Block, Block> strippingByBlock;

    // ------------------------------------------------------- block set types
    // BlockSetType and WoodType are plain records held in a static string-keyed map, not registry
    // entries: BlockSetType.register / WoodType.register just put into that map, so they are safe
    // to call from this class's static init and must happen before any door, trapdoor or fence gate
    // is constructed - which is exactly what field order gives us. The names are namespaced so they
    // cannot collide with vanilla's or another mod's.
    //
    // The BlockSetType is what actually decides whether a door opens by hand and which sound it
    // makes; the DoorBlock and TrapDoorBlock constructors overwrite whatever sound the properties
    // carried with type.soundType(). The wooden default constructor gives canOpenByHand = true,
    // which is what we want for all four woods.

    private static final BlockSetType PETRIFIED_TUNING_SET =
            BlockSetType.register(new BlockSetType(EchoingVoid.MODID + ":petrified_tuning"));

    private static final BlockSetType ECHO_ASH_SET =
            BlockSetType.register(new BlockSetType(EchoingVoid.MODID + ":echo_ash"));

    private static final BlockSetType AMBER_BOUGH_SET =
            BlockSetType.register(new BlockSetType(EchoingVoid.MODID + ":amber_bough"));

    /**
     * Humming timber sounds like the Nether woods rather than oak, matching the {@code NETHER_WOOD}
     * sound type its stem already uses. Spelled out in full because the one-argument constructor
     * hard-codes the oak sound set.
     */
    private static final BlockSetType HUMMING_SET = BlockSetType.register(new BlockSetType(
            EchoingVoid.MODID + ":humming",
            true,
            true,
            true,
            BlockSetType.PressurePlateSensitivity.EVERYTHING,
            SoundType.NETHER_WOOD,
            SoundEvents.NETHER_WOOD_DOOR_CLOSE,
            SoundEvents.NETHER_WOOD_DOOR_OPEN,
            SoundEvents.NETHER_WOOD_TRAPDOOR_CLOSE,
            SoundEvents.NETHER_WOOD_TRAPDOOR_OPEN,
            SoundEvents.NETHER_WOOD_PRESSURE_PLATE_CLICK_OFF,
            SoundEvents.NETHER_WOOD_PRESSURE_PLATE_CLICK_ON,
            SoundEvents.NETHER_WOOD_BUTTON_CLICK_OFF,
            SoundEvents.NETHER_WOOD_BUTTON_CLICK_ON));

    private static final WoodType PETRIFIED_TUNING_WOOD_TYPE =
            WoodType.register(new WoodType(EchoingVoid.MODID + ":petrified_tuning", PETRIFIED_TUNING_SET));

    private static final WoodType ECHO_ASH_WOOD_TYPE =
            WoodType.register(new WoodType(EchoingVoid.MODID + ":echo_ash", ECHO_ASH_SET));

    private static final WoodType AMBER_BOUGH_WOOD_TYPE =
            WoodType.register(new WoodType(EchoingVoid.MODID + ":amber_bough", AMBER_BOUGH_SET));

    private static final WoodType HUMMING_WOOD_TYPE = WoodType.register(new WoodType(
            EchoingVoid.MODID + ":humming",
            HUMMING_SET,
            SoundType.NETHER_WOOD,
            SoundType.NETHER_WOOD_HANGING_SIGN,
            SoundEvents.NETHER_WOOD_FENCE_GATE_CLOSE,
            SoundEvents.NETHER_WOOD_FENCE_GATE_OPEN));

    // --------------------------------------------------------- stone families
    // Hardness, blast resistance, map colour and sound are copied from each base block's own
    // registration so a cut variant is never cheaper or louder than the block it came from.
    // Brick bases follow vanilla's singularising convention - stone_bricks cuts to
    // stone_brick_slab - so phonolite_bricks gives phonolite_brick_slab, not phonolite_bricks_slab.

    /** Hardness 5.0 / Blast 6.0 | BASALT | the dark base stone of the deep strata. */
    public static final StoneFamily RAW_PHONOLITE = stoneFamily("raw_phonolite",
            ModBlocks.RAW_PHONOLITE, MapColor.DEEPSLATE, 5.0F, 6.0F, SoundType.BASALT);

    /** Hardness 5.0 / Blast 6.0 | BASALT | worked dark stone, the outpost floor material. */
    public static final StoneFamily POLISHED_PHONOLITE = stoneFamily("polished_phonolite",
            ModTerrainBlocks.POLISHED_PHONOLITE, MapColor.DEEPSLATE, 5.0F, 6.0F, SoundType.BASALT);

    /** Hardness 5.5 / Blast 6.0 | STONE | the portal frame block, and the hardest thing we cut. */
    public static final StoneFamily PHONOLITE_BRICK = stoneFamily("phonolite_brick",
            ModBlocks.PHONOLITE_BRICKS, MapColor.DEEPSLATE, 5.5F, 6.0F, SoundType.STONE);

    /** Hardness 1.5 / Blast 6.0 | CALCITE | pale highland stone, ungated so it is cheap to build with. */
    public static final StoneFamily RESONANT_CHALK = stoneFamily("resonant_chalk",
            ModTerrainBlocks.RESONANT_CHALK, MapColor.CLAY, 1.5F, 6.0F, SoundType.CALCITE);

    /** Hardness 2.0 / Blast 6.0 | CALCITE | worked chalk, what the Tuner outposts are made of. */
    public static final StoneFamily CHALK_BRICK = stoneFamily("chalk_brick",
            ModTerrainBlocks.CHALK_BRICKS, MapColor.CLAY, 2.0F, 6.0F, SoundType.CALCITE);

    /** Hardness 3.0 / Blast 6.0 | DEEPSLATE | the blue-grey middle band. */
    public static final StoneFamily ECHO_SLATE = stoneFamily("echo_slate",
            ModTerrainBlocks.ECHO_SLATE, MapColor.TERRACOTTA_LIGHT_BLUE, 3.0F, 6.0F, SoundType.DEEPSLATE);

    /** Hardness 2.5 / Blast 6.0 | TUFF | the one warm stone, and the only warm trim available. */
    public static final StoneFamily AMBER_STRATA = stoneFamily("amber_strata",
            ModTerrainBlocks.AMBER_STRATA, MapColor.TERRACOTTA_ORANGE, 2.5F, 6.0F, SoundType.TUFF);

    // --------------------------------------------------------------- new logs
    // The two new woods need their trunks before their families can be built, so they are declared
    // here rather than inside the family helper. Both use ResonantLogBlock, which reads the
    // STRIPPING table that woodFamily fills in; the stripped forms are plain pillars, because
    // nothing strips further.

    private static final RegistryObject<Block> ECHO_ASH_LOG =
            strippableLog("echo_ash_log", MapColor.TERRACOTTA_WHITE, SoundType.WOOD);
    private static final RegistryObject<Block> STRIPPED_ECHO_ASH_LOG =
            barePillar("stripped_echo_ash_log", MapColor.QUARTZ, SoundType.WOOD);

    private static final RegistryObject<Block> AMBER_BOUGH_LOG =
            strippableLog("amber_bough_log", MapColor.TERRACOTTA_ORANGE, SoundType.WOOD);
    private static final RegistryObject<Block> STRIPPED_AMBER_BOUGH_LOG =
            barePillar("stripped_amber_bough_log", MapColor.GOLD, SoundType.WOOD);

    // The trunks are declared above the family helper, so they miss the blockItem() pass that
    // runs inside it. Without these four the logs exist in the world but cannot be picked up,
    // and their loot tables fail to load against a block-only id.
    private static final RegistryObject<Item> ECHO_ASH_LOG_ITEM =
            blockItem("echo_ash_log", ECHO_ASH_LOG);
    private static final RegistryObject<Item> STRIPPED_ECHO_ASH_LOG_ITEM =
            blockItem("stripped_echo_ash_log", STRIPPED_ECHO_ASH_LOG);
    private static final RegistryObject<Item> AMBER_BOUGH_LOG_ITEM =
            blockItem("amber_bough_log", AMBER_BOUGH_LOG);
    private static final RegistryObject<Item> STRIPPED_AMBER_BOUGH_LOG_ITEM =
            blockItem("stripped_amber_bough_log", STRIPPED_AMBER_BOUGH_LOG);

    // ---------------------------------------------------------- wood families
    // Trunk strength stays at the 3.0 / 3.0 the two existing trunks use, above vanilla's 2.0,
    // because every timber in this dimension is mineralised. Planks and everything cut from them
    // take vanilla's 2.0 / 3.0, and doors and trapdoors vanilla's 3.0.
    //
    // None of these call ignitedByLava(). The existing two trunks do not either, and the reason is
    // the fiction: this timber is petrified and crystalline, not living wood. Keeping that
    // consistent across the whole family matters more than matching oak, because a player who
    // learns "the groves here do not burn" from a log should not be surprised by a fence.

    /** The existing dark mineral timber. Trunk and stripped trunk come from {@link ModBlocks}. */
    public static final WoodFamily PETRIFIED_TUNING = woodFamily("petrified_tuning",
            PETRIFIED_TUNING_WOOD_TYPE, SoundType.WOOD,
            MapColor.DEEPSLATE, MapColor.DEEPSLATE, MapColor.DEEPSLATE,
            ModBlocks.PETRIFIED_TUNING_WOOD, ModBlocks.STRIPPED_PETRIFIED_TUNING_WOOD,
            "petrified_tuning_bark", "stripped_petrified_tuning_bark");

    /** The existing violet timber. Stem and stripped stem come from {@link ModTerrainBlocks}. */
    public static final WoodFamily HUMMING = woodFamily("humming",
            HUMMING_WOOD_TYPE, SoundType.NETHER_WOOD,
            MapColor.TERRACOTTA_PURPLE, MapColor.TERRACOTTA_MAGENTA, MapColor.TERRACOTTA_PURPLE,
            ModTerrainBlocks.HUMMING_STEM, ModTerrainBlocks.STRIPPED_HUMMING_STEM,
            "humming_hyphae", "stripped_humming_hyphae");

    /** New pale bone-white wood, the timber of the Chalk Reaches groves. */
    public static final WoodFamily ECHO_ASH = woodFamily("echo_ash",
            ECHO_ASH_WOOD_TYPE, SoundType.WOOD,
            MapColor.TERRACOTTA_WHITE, MapColor.QUARTZ, MapColor.QUARTZ,
            ECHO_ASH_LOG, STRIPPED_ECHO_ASH_LOG,
            "echo_ash_wood", "stripped_echo_ash_wood");

    /** New warm wood, the timber of the Resonant Plains groves. */
    public static final WoodFamily AMBER_BOUGH = woodFamily("amber_bough",
            AMBER_BOUGH_WOOD_TYPE, SoundType.WOOD,
            MapColor.TERRACOTTA_ORANGE, MapColor.GOLD, MapColor.COLOR_ORANGE,
            AMBER_BOUGH_LOG, STRIPPED_AMBER_BOUGH_LOG,
            "amber_bough_wood", "stripped_amber_bough_wood");

    // ------------------------------------------------------------------ shape

    /**
     * One stone cut three ways.
     *
     * @param prefix the id prefix its variants share, e.g. {@code chalk_brick}
     * @param base   the full cube the variants are cut from, owned by another registry class
     * @param slab   the half-height variant
     * @param stairs the stepped variant
     * @param wall   the connecting wall variant
     */
    public record StoneFamily(
            String prefix,
            RegistryObject<Block> base,
            RegistryObject<Block> slab,
            RegistryObject<Block> stairs,
            RegistryObject<Block> wall) {}

    /**
     * One wood, complete.
     *
     * <p>{@code log} and {@code strippedLog} may be blocks this class did not register - for the two
     * woods that predate it they point into {@link ModBlocks} and {@link ModTerrainBlocks} - so
     * anything walking a family to place blocks gets the same shape for all four either way.
     *
     * @param id           the id prefix the cut variants share, e.g. {@code amber_bough}
     * @param woodType     the sound and behaviour set shared by this wood's gate, door and trapdoor
     * @param log          the trunk, bark on four sides and rings on the ends
     * @param strippedLog  the trunk with the bark taken off
     * @param wood         the bark-on-all-six-sides variant
     * @param strippedWood the stripped bark-on-all-six-sides variant
     * @param planks       the base building block the rest of the family is cut from
     * @param slab         the half-height variant
     * @param stairs       the stepped variant
     * @param fence        the fence, which connects only through the vanilla fence tags
     * @param fenceGate    the openable gap in a fence
     * @param door         the two-block-tall door
     * @param trapdoor     the one-block door in a floor or ceiling
     */
    public record WoodFamily(
            String id,
            WoodType woodType,
            RegistryObject<Block> log,
            RegistryObject<Block> strippedLog,
            RegistryObject<Block> wood,
            RegistryObject<Block> strippedWood,
            RegistryObject<Block> planks,
            RegistryObject<Block> slab,
            RegistryObject<Block> stairs,
            RegistryObject<Block> fence,
            RegistryObject<Block> fenceGate,
            RegistryObject<Block> door,
            RegistryObject<Block> trapdoor) {}

    // ---------------------------------------------------------------- builders

    private static StoneFamily stoneFamily(String prefix, RegistryObject<Block> base,
                                           MapColor color, float hardness, float blast, SoundType sound) {
        String slabId = prefix + "_slab";
        String stairsId = prefix + "_stairs";
        String wallId = prefix + "_wall";

        RegistryObject<Block> slab = BLOCKS.register(slabId,
                () -> new SlabBlock(stoneProps(slabId, color, hardness, blast, sound)));
        RegistryObject<Block> stairs = BLOCKS.register(stairsId,
                () -> new StairBlock(baseState(base),
                        stoneProps(stairsId, color, hardness, blast, sound)));
        // forceSolidOn matches vanilla walls: a wall is not a full cube but still supports torches
        // and stops a mob spawning on top of it being treated as a non-solid perch.
        RegistryObject<Block> wall = BLOCKS.register(wallId,
                () -> new WallBlock(stoneProps(wallId, color, hardness, blast, sound).forceSolidOn()));

        blockItem(slabId, slab);
        blockItem(stairsId, stairs);
        blockItem(wallId, wall);

        StoneFamily family = new StoneFamily(prefix, base, slab, stairs, wall);
        STONE_FAMILIES.add(family);
        return family;
    }

    private static WoodFamily woodFamily(String id, WoodType woodType, SoundType sound,
                                         MapColor barkColor, MapColor coreColor, MapColor planksColor,
                                         RegistryObject<Block> log, RegistryObject<Block> strippedLog,
                                         String barkId, String strippedBarkId) {
        BlockSetType setType = woodType.setType();

        String planksId = id + "_planks";
        String slabId = id + "_slab";
        String stairsId = id + "_stairs";
        String fenceId = id + "_fence";
        String gateId = id + "_fence_gate";
        String doorId = id + "_door";
        String trapdoorId = id + "_trapdoor";

        RegistryObject<Block> bark = strippableLog(barkId, barkColor, sound);
        RegistryObject<Block> strippedBark = barePillar(strippedBarkId, coreColor, sound);

        // Declared before the stairs, whose supplier resolves it during registration.
        RegistryObject<Block> planks = BLOCKS.register(planksId,
                () -> new Block(woodProps(planksId, planksColor, 2.0F, 3.0F, sound)));

        RegistryObject<Block> slab = BLOCKS.register(slabId,
                () -> new SlabBlock(woodProps(slabId, planksColor, 2.0F, 3.0F, sound)));
        RegistryObject<Block> stairs = BLOCKS.register(stairsId,
                () -> new StairBlock(baseState(planks),
                        woodProps(stairsId, planksColor, 2.0F, 3.0F, sound)));
        RegistryObject<Block> fence = BLOCKS.register(fenceId,
                () -> new FenceBlock(woodProps(fenceId, planksColor, 2.0F, 3.0F, sound).forceSolidOn()));
        RegistryObject<Block> gate = BLOCKS.register(gateId,
                () -> new FenceGateBlock(woodType,
                        woodProps(gateId, planksColor, 2.0F, 3.0F, sound).forceSolidOn()));

        // A door is two blocks tall and a piston must break it rather than shear it in half, hence
        // pushReaction DESTROY. noOcclusion because the model is a 3-pixel slab, not a cube.
        RegistryObject<Block> door = BLOCKS.register(doorId,
                () -> new DoorBlock(setType, woodProps(doorId, planksColor, 3.0F, 3.0F, sound)
                        .noOcclusion()
                        .pushReaction(PushReaction.DESTROY)));

        // isValidSpawn false is vanilla's: a closed trapdoor is a full-width surface and would
        // otherwise be a legal mob-spawning floor over an open shaft.
        RegistryObject<Block> trapdoor = BLOCKS.register(trapdoorId,
                () -> new TrapDoorBlock(setType, woodProps(trapdoorId, planksColor, 3.0F, 3.0F, sound)
                        .noOcclusion()
                        .isValidSpawn((state, level, pos, entityType) -> false)));

        // Tab order within a wood: raw timber, then planks, then everything cut from planks.
        blockItem(barkId, bark);
        blockItem(strippedBarkId, strippedBark);
        blockItem(planksId, planks);
        blockItem(slabId, slab);
        blockItem(stairsId, stairs);
        blockItem(fenceId, fence);
        blockItem(gateId, gate);
        doorItem(doorId, door);
        blockItem(trapdoorId, trapdoor);

        // The trunk pair is recorded even for the two woods whose trunk has its own hand-written
        // stripping override, so this table stays a complete description of the family.
        STRIPPING.put(log, strippedLog);
        STRIPPING.put(bark, strippedBark);

        WoodFamily family = new WoodFamily(id, woodType, log, strippedLog, bark, strippedBark,
                planks, slab, stairs, fence, gate, door, trapdoor);
        WOOD_FAMILIES.add(family);
        return family;
    }

    // ----------------------------------------------------------------- pieces

    /** An axis pillar an axe can strip; what it becomes is read from {@link #STRIPPING}. */
    private static RegistryObject<Block> strippableLog(String name, MapColor color, SoundType sound) {
        return BLOCKS.register(name,
                () -> new ResonantLogBlock(woodProps(name, color, 3.0F, 3.0F, sound)));
    }

    /** An axis pillar with nothing left to strip. */
    private static RegistryObject<Block> barePillar(String name, MapColor color, SoundType sound) {
        return BLOCKS.register(name,
                () -> new RotatedPillarBlock(woodProps(name, color, 3.0F, 3.0F, sound)));
    }

    // ---------------------------------------------------------------- helpers

    /**
     * The state a stair is cut from, resolved while the block registry event is running.
     *
     * <p>This is the one place the class depends on registration order, so it says so rather than
     * letting Forge throw a bare "Registry Object not present". If it ever fires, the fix is in
     * {@code EchoingVoid}, not here.
     */
    private static BlockState baseState(RegistryObject<Block> base) {
        if (!base.isPresent()) {
            throw new IllegalStateException(base.getId() + " is not registered yet. "
                    + "ModBlockFamilies.register(modBus) must be called after ModBlocks.register "
                    + "and ModTerrainBlocks.register in EchoingVoid.");
        }
        return base.get().defaultBlockState();
    }

    /** Shared starting point: every block must carry its own registry id in 26.2. */
    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    private static BlockBehaviour.Properties stoneProps(String name, MapColor color,
                                                        float hardness, float blast, SoundType sound) {
        return props(name)
                .mapColor(color)
                .strength(hardness, blast)
                .sound(sound)
                .requiresCorrectToolForDrops();
    }

    private static BlockBehaviour.Properties woodProps(String name, MapColor color,
                                                       float hardness, float blast, SoundType sound) {
        return props(name)
                .mapColor(color)
                .strength(hardness, blast)
                .sound(sound);
    }

    /** The item form of a block, tracked for the creative tab. */
    private static RegistryObject<Item> blockItem(String name, RegistryObject<Block> block) {
        RegistryObject<Item> item = ITEMS.register(name,
                () -> new BlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name))));
        TAB_ORDER.add(item);
        return item;
    }

    /**
     * The item form of a door.
     *
     * <p>Doors need {@link DoubleHighBlockItem} rather than a plain {@code BlockItem}: it clears the
     * block above the click before placing, which is what lets a door go in against a replaceable
     * block such as tall grass instead of silently failing.
     */
    private static RegistryObject<Item> doorItem(String name, RegistryObject<Block> block) {
        RegistryObject<Item> item = ITEMS.register(name,
                () -> new DoubleHighBlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name))));
        TAB_ORDER.add(item);
        return item;
    }

    // ------------------------------------------------------------- public API

    /**
     * What an axe turns {@code log} into, or null if it is not a trunk or bark block of ours.
     *
     * <p>Called from {@link ResonantLogBlock}. The block-keyed view is built on first use rather
     * than at class-init because the blocks it maps do not exist until the registry event has run.
     */
    public static @Nullable Block strippedForm(Block log) {
        Map<Block, Block> resolved = strippingByBlock;
        if (resolved == null) {
            resolved = new IdentityHashMap<>(STRIPPING.size());
            for (Map.Entry<RegistryObject<Block>, RegistryObject<Block>> entry : STRIPPING.entrySet()) {
                resolved.put(entry.getKey().get(), entry.getValue().get());
            }
            strippingByBlock = resolved;
        }
        return resolved.get(log);
    }

    /** The seven stone families, in creative-tab order. */
    public static List<StoneFamily> stoneFamilies() {
        return Collections.unmodifiableList(STONE_FAMILIES);
    }

    /** The four wood families, in creative-tab order. */
    public static List<WoodFamily> woodFamilies() {
        return Collections.unmodifiableList(WOOD_FAMILIES);
    }

    /** Every family block item, in the order the creative tab should show them. */
    public static List<RegistryObject<Item>> tabOrder() {
        return Collections.unmodifiableList(TAB_ORDER);
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

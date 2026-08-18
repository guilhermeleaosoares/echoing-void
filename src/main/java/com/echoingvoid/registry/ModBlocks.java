package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.AcousticLockBoxBlock;
import com.echoingvoid.block.CalcifiedResonanceLeavesBlock;
import com.echoingvoid.block.FrequencySiphonBlock;
import com.echoingvoid.block.HollowHorizonPortalBlock;
import com.echoingvoid.block.InversionAnvilBlock;
import com.echoingvoid.block.NullIronBlock;
import com.echoingvoid.block.NullIronOreBlock;
import com.echoingvoid.block.PetrifiedTuningWoodBlock;
import com.echoingvoid.block.ResonantBismuthOreBlock;
import com.echoingvoid.block.TunersMaskBlock;
import com.echoingvoid.block.VoidGlassBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/**
 * The twelve headline blocks of The Echoing Void, plus the stripped-log support block and the
 * portal surface.
 *
 * <p>Every hardness / blast resistance / sound / light value here is taken verbatim from the
 * block matrix in the design brief ({@code docs/spec/mod_spec.json}). Mining tool and tier are
 * expressed through block tags, because 26.2 has no Java API for either - the code contributes
 * only {@code requiresCorrectToolForDrops()} and the datapack decides the rest.
 */
public final class ModBlocks {
    private ModBlocks() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    // ---------------------------------------------------------------- ores

    /** Hardness 4.5 / Blast 3.0 | Pickaxe (Diamond) | AMETHYST | Light 3 | drops 1-3 shards. */
    public static final RegistryObject<Block> RESONANT_BISMUTH_ORE = BLOCKS.register("resonant_bismuth_ore",
            () -> new ResonantBismuthOreBlock(props("resonant_bismuth_ore")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(4.5F, 3.0F)
                    .sound(SoundType.AMETHYST)
                    .lightLevel(state -> 3)
                    .requiresCorrectToolForDrops()));

    /** Hardness 6.0 / Blast 4.0 | Pickaxe (Diamond) | DEEPSLATE | Light 3. */
    public static final RegistryObject<Block> DEEPSLATE_RESONANT_BISMUTH_ORE = BLOCKS.register("deepslate_resonant_bismuth_ore",
            () -> new ResonantBismuthOreBlock(props("deepslate_resonant_bismuth_ore")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(6.0F, 4.0F)
                    .sound(SoundType.DEEPSLATE)
                    .lightLevel(state -> 3)
                    .requiresCorrectToolForDrops()));

    /** Hardness 5.0 / Blast 6.0 | Pickaxe (Netherite) | ANCIENT_DEBRIS | absorbs light. */
    public static final RegistryObject<Block> NULL_IRON_ORE = BLOCKS.register("null_iron_ore",
            () -> new NullIronOreBlock(props("null_iron_ore")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(5.0F, 6.0F)
                    .sound(SoundType.ANCIENT_DEBRIS)
                    .requiresCorrectToolForDrops()));

    // ------------------------------------------------------------ stone set

    /** Hardness 5.0 / Blast 6.0 | Pickaxe (Diamond) | BASALT | volcanic slate base. */
    public static final RegistryObject<Block> RAW_PHONOLITE = BLOCKS.register("raw_phonolite",
            () -> new Block(props("raw_phonolite")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(5.0F, 6.0F)
                    .sound(SoundType.BASALT)
                    .requiresCorrectToolForDrops()));

    /** Hardness 5.5 / Blast 6.0 | Pickaxe (Diamond) | STONE | portal frame block. */
    public static final RegistryObject<Block> PHONOLITE_BRICKS = BLOCKS.register("phonolite_bricks",
            () -> new Block(props("phonolite_bricks")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(5.5F, 6.0F)
                    .sound(SoundType.STONE)
                    .requiresCorrectToolForDrops()));

    /** Hardness 8.0 / Blast 12.0 | Pickaxe (Netherite) | NETHERITE_BLOCK | eats nearby blasts. */
    public static final RegistryObject<Block> NULL_IRON_BLOCK = BLOCKS.register("null_iron_block",
            () -> new NullIronBlock(props("null_iron_block")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(8.0F, 12.0F)
                    .sound(SoundType.NETHERITE_BLOCK)
                    .requiresCorrectToolForDrops()));

    // ----------------------------------------------------------- transparent

    /** Hardness 0.8 / Blast 0.5 | Silk Touch | GLASS | negates fall damage, zero-g walk surface. */
    public static final RegistryObject<Block> VOID_GLASS = BLOCKS.register("void_glass",
            () -> new VoidGlassBlock(props("void_glass")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(0.8F, 0.5F)
                    .sound(SoundType.GLASS)
                    .noOcclusion()));

    /** Hardness 0.4 / Blast 0.2 | Shears / Hoe | AZALEA_LEAVES | Light 6 | drops seedlings. */
    public static final RegistryObject<Block> CALCIFIED_RESONANCE_LEAVES = BLOCKS.register("calcified_resonance_leaves",
            () -> new CalcifiedResonanceLeavesBlock(props("calcified_resonance_leaves")
                    .mapColor(MapColor.COLOR_CYAN)
                    .strength(0.4F, 0.2F)
                    .sound(SoundType.AZALEA_LEAVES)
                    .lightLevel(state -> 6)
                    .noOcclusion()));

    // ------------------------------------------------------------------ wood

    /** Hardness 3.0 / Blast 3.0 | Axe (Iron+) | WOOD | Hollow Horizon trunk, strippable. */
    public static final RegistryObject<Block> PETRIFIED_TUNING_WOOD = BLOCKS.register("petrified_tuning_wood",
            () -> new PetrifiedTuningWoodBlock(props("petrified_tuning_wood")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(3.0F, 3.0F)
                    .sound(SoundType.WOOD)));

    /** Stripped form produced by an axe. */
    public static final RegistryObject<Block> STRIPPED_PETRIFIED_TUNING_WOOD = BLOCKS.register("stripped_petrified_tuning_wood",
            () -> new RotatedPillarBlock(props("stripped_petrified_tuning_wood")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(3.0F, 3.0F)
                    .sound(SoundType.WOOD)));

    // -------------------------------------------------------------- machines

    /** Hardness 3.5 / Blast 4.0 | Pickaxe (Iron) | COPPER | Light 1 | vibrations -> redstone 1-15. */
    public static final RegistryObject<Block> FREQUENCY_SIPHON = BLOCKS.register("frequency_siphon",
            () -> new FrequencySiphonBlock(props("frequency_siphon")
                    .mapColor(MapColor.COLOR_CYAN)
                    .strength(3.5F, 4.0F)
                    .sound(SoundType.COPPER)
                    .lightLevel(state -> 1)
                    .requiresCorrectToolForDrops()));

    /** Hardness 6.0 / Blast 1200.0 | Pickaxe (Diamond) | ANVIL | Light 2 | uncrafts by durability. */
    public static final RegistryObject<Block> INVERSION_ANVIL = BLOCKS.register("inversion_anvil",
            () -> new InversionAnvilBlock(props("inversion_anvil")
                    .mapColor(MapColor.METAL)
                    .strength(6.0F, 1200.0F)
                    .sound(SoundType.ANVIL)
                    .lightLevel(state -> 2)
                    .requiresCorrectToolForDrops()));

    /** Hardness 50.0 / Blast 1200.0 | unbreakable by hand | METAL | pitch-sequence vault. */
    public static final RegistryObject<Block> ACOUSTIC_LOCK_BOX = BLOCKS.register("acoustic_lock_box",
            () -> new AcousticLockBoxBlock(props("acoustic_lock_box")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(50.0F, 1200.0F)
                    .sound(SoundType.METAL)
                    .requiresCorrectToolForDrops()));

    /**
     * Hardness 8.0 / Blast 12.0 | Pickaxe (Netherite) | NETHERITE_BLOCK - same figures as
     * {@link #NULL_IRON_BLOCK}, deliberately: this is that block with a face carved into it, not
     * a separate material. Placed on a null-iron body it builds a {@code tuners_protector} - see
     * {@link TunersMaskBlock}.
     */
    public static final RegistryObject<Block> TUNERS_MASK = BLOCKS.register("tuners_mask",
            () -> new TunersMaskBlock(props("tuners_mask")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(8.0F, 12.0F)
                    .sound(SoundType.NETHERITE_BLOCK)
                    .requiresCorrectToolForDrops()));

    // ------------------------------------------------------------- the portal

    /**
     * The standing wave inside a lit Phonolite frame. Indestructible, no collision, faint glow -
     * the same shape of properties vanilla gives its own portal, minus the fire ignition.
     */
    public static final RegistryObject<Block> HOLLOW_HORIZON_PORTAL = BLOCKS.register("hollow_horizon_portal",
            () -> new HollowHorizonPortalBlock(props("hollow_horizon_portal")
                    .mapColor(MapColor.COLOR_CYAN)
                    .noCollision()
                    .noLootTable()
                    .strength(-1.0F)
                    .sound(SoundType.GLASS)
                    .lightLevel(state -> 11)
                    .pushReaction(PushReaction.BLOCK)));

    /** Shared starting point: every block must carry its own registry id in 26.2. */
    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
    }
}

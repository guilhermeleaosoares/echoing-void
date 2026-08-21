package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.item.AeroStrideGreavesItem;
import com.echoingvoid.item.HarmonicAxeItem;
import com.echoingvoid.item.HarmonicPickaxeItem;
import com.echoingvoid.item.ModToolMaterials;
import com.echoingvoid.item.ResonanceArmorItem;
import com.echoingvoid.item.HarmonicSwordItem;
import com.echoingvoid.item.SonicLanceItem;
import com.echoingvoid.item.TuningForkItem;
import com.echoingvoid.item.VoidGlassRapierItem;
import net.minecraft.world.item.AxeItem;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.HoeItem;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.ShovelItem;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraft.world.item.equipment.ArmorType;
import net.minecraft.world.level.block.Block;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/** Materials, block items, and (later) the tool/weapon/armor suite. */
public final class ModItems {
    private ModItems() {}

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    /** Everything registered here, in registration order, for creative-tab population. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ------------------------------------------------------------- materials

    public static final RegistryObject<Item> RESONANCE_SHARD = simple("resonance_shard");
    public static final RegistryObject<Item> RAW_NULL_IRON = simple("raw_null_iron");
    public static final RegistryObject<Item> NULL_IRON_INGOT = simple("null_iron_ingot");
    public static final RegistryObject<Item> VOID_GLASS_SHARD = simple("void_glass_shard");
    public static final RegistryObject<Item> BISMUTH_SEEDLING = simple("bismuth_seedling");

    // The discs are playable records. In 26.2 that is a data component naming a jukebox_song
    // registry entry rather than anything hard-coded, so these work in a vanilla jukebox and
    // vanilla records work in the Null-Iron Jukebox - both fall out of the component.

    /** Plays in a jukebox; the component names the track, the datapack defines it. */
    public static final RegistryObject<Item> HARMONIC_TUNING_DISC_ALPHA = track(ITEMS.register("harmonic_tuning_disc_alpha",
            () -> new Item(props("harmonic_tuning_disc_alpha")
                    .stacksTo(1)
                    .rarity(Rarity.RARE)
                    .jukeboxPlayable(ModEffects.SONG_HARMONIC_ALPHA))));

    public static final RegistryObject<Item> HARMONIC_TUNING_DISC_BETA = track(ITEMS.register("harmonic_tuning_disc_beta",
            () -> new Item(props("harmonic_tuning_disc_beta")
                    .stacksTo(1)
                    .rarity(Rarity.RARE)
                    .jukeboxPlayable(ModEffects.SONG_HARMONIC_BETA))));

    public static final RegistryObject<Item> HARMONIC_TUNING_DISC_GAMMA = track(ITEMS.register("harmonic_tuning_disc_gamma",
            () -> new Item(props("harmonic_tuning_disc_gamma")
                    .stacksTo(1)
                    .rarity(Rarity.RARE)
                    .jukeboxPlayable(ModEffects.SONG_HARMONIC_GAMMA))));

    // ------------------------------------------------------------ block items

    public static final RegistryObject<Item> RESONANT_BISMUTH_ORE_ITEM = blockItem("resonant_bismuth_ore", ModBlocks.RESONANT_BISMUTH_ORE);
    public static final RegistryObject<Item> DEEPSLATE_RESONANT_BISMUTH_ORE_ITEM = blockItem("deepslate_resonant_bismuth_ore", ModBlocks.DEEPSLATE_RESONANT_BISMUTH_ORE);
    public static final RegistryObject<Item> RAW_PHONOLITE_ITEM = blockItem("raw_phonolite", ModBlocks.RAW_PHONOLITE);
    public static final RegistryObject<Item> PHONOLITE_BRICKS_ITEM = blockItem("phonolite_bricks", ModBlocks.PHONOLITE_BRICKS);
    public static final RegistryObject<Item> VOID_GLASS_ITEM = blockItem("void_glass", ModBlocks.VOID_GLASS);
    public static final RegistryObject<Item> NULL_IRON_ORE_ITEM = blockItem("null_iron_ore", ModBlocks.NULL_IRON_ORE);
    public static final RegistryObject<Item> NULL_IRON_BLOCK_ITEM = blockItem("null_iron_block", ModBlocks.NULL_IRON_BLOCK);
    public static final RegistryObject<Item> PETRIFIED_TUNING_WOOD_ITEM = blockItem("petrified_tuning_wood", ModBlocks.PETRIFIED_TUNING_WOOD);
    public static final RegistryObject<Item> STRIPPED_PETRIFIED_TUNING_WOOD_ITEM = blockItem("stripped_petrified_tuning_wood", ModBlocks.STRIPPED_PETRIFIED_TUNING_WOOD);
    public static final RegistryObject<Item> CALCIFIED_RESONANCE_LEAVES_ITEM = blockItem("calcified_resonance_leaves", ModBlocks.CALCIFIED_RESONANCE_LEAVES);
    public static final RegistryObject<Item> FREQUENCY_SIPHON_ITEM = blockItem("frequency_siphon", ModBlocks.FREQUENCY_SIPHON);
    public static final RegistryObject<Item> INVERSION_ANVIL_ITEM = blockItem("inversion_anvil", ModBlocks.INVERSION_ANVIL);
    public static final RegistryObject<Item> ACOUSTIC_LOCK_BOX_ITEM = blockItem("acoustic_lock_box", ModBlocks.ACOUSTIC_LOCK_BOX);
    public static final RegistryObject<Item> TUNERS_MASK_ITEM = blockItem("tuners_mask", ModBlocks.TUNERS_MASK);

    // ------------------------------------------------------------ spawn eggs

    // 26.2 spawn eggs are plain SpawnEggItems whose entity comes from the
    // spawnEgg(...) property. ENTITY_TYPE is created before ITEM in
    // BuiltInRegistries, so the types are resolvable by the time these build.

    public static final RegistryObject<Item> ECHO_WEAVER_SPAWN_EGG = track(ITEMS.register("echo_weaver_spawn_egg",
            () -> new SpawnEggItem(props("echo_weaver_spawn_egg")
                    .spawnEgg(ModEntities.ECHO_WEAVER.get()))));

    public static final RegistryObject<Item> STRATA_GOLEM_SPAWN_EGG = track(ITEMS.register("strata_golem_spawn_egg",
            () -> new SpawnEggItem(props("strata_golem_spawn_egg")
                    .spawnEgg(ModEntities.STRATA_GOLEM.get()))));

    public static final RegistryObject<Item> RESONANCE_WRAITH_SPAWN_EGG = track(ITEMS.register("resonance_wraith_spawn_egg",
            () -> new SpawnEggItem(props("resonance_wraith_spawn_egg")
                    .spawnEgg(ModEntities.RESONANCE_WRAITH.get()))));

    // The expansion three. Same shape as above, but their types come from
    // ModNewEntities, which the mod constructor registers ahead of this class for
    // exactly this reason - spawnEgg(...) resolves the EntityType eagerly.

    public static final RegistryObject<Item> CHIME_MOTE_SPAWN_EGG = track(ITEMS.register("chime_mote_spawn_egg",
            () -> new SpawnEggItem(props("chime_mote_spawn_egg")
                    .spawnEgg(ModNewEntities.CHIME_MOTE.get()))));

    public static final RegistryObject<Item> TUNER_SHADE_SPAWN_EGG = track(ITEMS.register("tuner_shade_spawn_egg",
            () -> new SpawnEggItem(props("tuner_shade_spawn_egg")
                    .spawnEgg(ModNewEntities.TUNER_SHADE.get()))));

    public static final RegistryObject<Item> STRATA_BURROWER_SPAWN_EGG = track(ITEMS.register("strata_burrower_spawn_egg",
            () -> new SpawnEggItem(props("strata_burrower_spawn_egg")
                    .spawnEgg(ModNewEntities.STRATA_BURROWER.get()))));

    public static final RegistryObject<Item> TUNER_TRADER_SPAWN_EGG = track(ITEMS.register("tuner_trader_spawn_egg",
            () -> new SpawnEggItem(props("tuner_trader_spawn_egg")
                    .spawnEgg(ModNewEntities.TUNER_TRADER.get()))));

    public static final RegistryObject<Item> TUNERS_PROTECTOR_SPAWN_EGG = track(ITEMS.register("tuners_protector_spawn_egg",
            () -> new SpawnEggItem(props("tuners_protector_spawn_egg")
                    .spawnEgg(ModNewEntities.TUNERS_PROTECTOR.get()))));

    public static final RegistryObject<Item> DRONE_AUROCH_SPAWN_EGG = track(ITEMS.register("drone_auroch_spawn_egg",
            () -> new SpawnEggItem(props("drone_auroch_spawn_egg")
                    .spawnEgg(ModNewEntities.DRONE_AUROCH.get()))));

    public static final RegistryObject<Item> THRUM_BOAR_SPAWN_EGG = track(ITEMS.register("thrum_boar_spawn_egg",
            () -> new SpawnEggItem(props("thrum_boar_spawn_egg")
                    .spawnEgg(ModNewEntities.THRUM_BOAR.get()))));

    // ------------------------------------------------------------------ meat
    //
    // PLAYER: "passive mobs that can be killed for their meat, but dont make it like chops or
    // steak, for one of them call it (something echoing void related) loin, and then something
    // echoing void related ribs."
    //
    // Vanilla's beef and porkchop figures, raw and cooked, so the cooking step is worth taking by
    // the same margin a player already knows. Deliberately NO status effects on these: the void
    // CROPS carry the navigation effects (see ModCrops), and meat that also did would leave the
    // farm with nothing to be uniquely good at.

    /** Raw beef's figures. */
    private static final FoodProperties RAW_MEAT_FOOD =
            new FoodProperties.Builder().nutrition(3).saturationModifier(0.3F).build();

    /** Cooked beef's figures - the reason to bother with a furnace. */
    private static final FoodProperties SEARED_MEAT_FOOD =
            new FoodProperties.Builder().nutrition(8).saturationModifier(0.8F).build();

    public static final RegistryObject<Item> DRONE_LOIN = track(ITEMS.register("drone_loin",
            () -> new Item(props("drone_loin").food(RAW_MEAT_FOOD))));

    public static final RegistryObject<Item> SEARED_DRONE_LOIN = track(ITEMS.register("seared_drone_loin",
            () -> new Item(props("seared_drone_loin").food(SEARED_MEAT_FOOD))));

    public static final RegistryObject<Item> THRUM_RIBS = track(ITEMS.register("thrum_ribs",
            () -> new Item(props("thrum_ribs").food(RAW_MEAT_FOOD))));

    public static final RegistryObject<Item> SEARED_THRUM_RIBS = track(ITEMS.register("seared_thrum_ribs",
            () -> new Item(props("seared_thrum_ribs").food(SEARED_MEAT_FOOD))));

    // ------------------------------------------------------------------ gear

    /** Struck against a Phonolite frame, it opens the way to the Hollow Horizon. */
    public static final RegistryObject<Item> TUNING_FORK = track(ITEMS.register("tuning_fork",
            () -> new TuningForkItem(props("tuning_fork").durability(128))));

    /** Mined blocks shatter in a 3x3 plane when swung on tempo. */
    public static final RegistryObject<Item> HARMONIC_PICKAXE = track(ITEMS.register("harmonic_pickaxe",
            () -> new HarmonicPickaxeItem(props("harmonic_pickaxe")
                    .pickaxe(ModToolMaterials.RESONANT_BISMUTH, 1.0F, -2.8F))));

    /** Absorbs incoming projectile damage as charge, discharges a piercing shockwave. */
    public static final RegistryObject<Item> SONIC_LANCE = track(ITEMS.register("sonic_lance",
            () -> new SonicLanceItem(props("sonic_lance")
                    .sword(ModToolMaterials.NULL_IRON, 3.0F, -3.2F)
                    .rarity(Rarity.RARE))));

    /** Bypasses half of armour; critical strikes buy a moment of invisibility. */
    public static final RegistryObject<Item> VOID_GLASS_RAPIER = track(ITEMS.register("void_glass_rapier",
            () -> new VoidGlassRapierItem(props("void_glass_rapier")
                    .sword(ModToolMaterials.VOID_GLASS, 2.0F, -1.8F)
                    .rarity(Rarity.RARE))));

    public static final RegistryObject<Item> RESONANCE_HELMET = track(ITEMS.register("resonance_helmet",
            () -> new ResonanceArmorItem(props("resonance_helmet")
                    .humanoidArmor(ModToolMaterials.RESONANCE, ArmorType.HELMET))));

    public static final RegistryObject<Item> RESONANCE_CHESTPLATE = track(ITEMS.register("resonance_chestplate",
            () -> new ResonanceArmorItem(props("resonance_chestplate")
                    .humanoidArmor(ModToolMaterials.RESONANCE, ArmorType.CHESTPLATE))));

    public static final RegistryObject<Item> RESONANCE_LEGGINGS = track(ITEMS.register("resonance_leggings",
            () -> new ResonanceArmorItem(props("resonance_leggings")
                    .humanoidArmor(ModToolMaterials.RESONANCE, ArmorType.LEGGINGS))));

    public static final RegistryObject<Item> RESONANCE_BOOTS = track(ITEMS.register("resonance_boots",
            () -> new ResonanceArmorItem(props("resonance_boots")
                    .humanoidArmor(ModToolMaterials.RESONANCE, ArmorType.BOOTS))));

    // ------------------------------------------------ the Resonance toolset
    //
    // The Knell tier upgrades from Resonance rather than from netherite, so every
    // Knell piece needs a Resonance piece to come from. The armour already
    // existed; these four are the rest of the set. The pickaxe slot is filled by
    // the Harmonic Pickaxe, which is already resonant bismuth and keeps its
    // rhythm mechanic rather than being duplicated by a plain one.
    //
    // Swords and pickaxes fold into Item.Properties in 26.2, but axes, shovels
    // and hoes still need their own classes - stripping, path-making and tilling
    // live in those classes' useOn, so a plain Item with .axe(...) can fight but
    // cannot strip a log.

    /** Feeds the Resonance armour's kinetic bank on hit, closing the set's loop. */
    public static final RegistryObject<Item> HARMONIC_SWORD = track(ITEMS.register("harmonic_sword",
            () -> new HarmonicSwordItem(props("harmonic_sword")
                    .sword(ModToolMaterials.RESONANT_BISMUTH,
                            HarmonicSwordItem.ATTACK_BASELINE, -2.4F))));

    /** Fells a whole single-trunk tree - or a 2x2 large trunk - struck at its base. */
    public static final RegistryObject<Item> HARMONIC_AXE = track(ITEMS.register("harmonic_axe",
            () -> new HarmonicAxeItem(ModToolMaterials.RESONANT_BISMUTH, 5.0F, -3.0F,
                    props("harmonic_axe"))));

    public static final RegistryObject<Item> HARMONIC_SHOVEL = track(ITEMS.register("harmonic_shovel",
            () -> new ShovelItem(ModToolMaterials.RESONANT_BISMUTH, 1.5F, -3.0F,
                    props("harmonic_shovel"))));

    public static final RegistryObject<Item> HARMONIC_HOE = track(ITEMS.register("harmonic_hoe",
            () -> new HoeItem(ModToolMaterials.RESONANT_BISMUTH, -2.0F, 0.0F,
                    props("harmonic_hoe"))));

    /** Worn on the feet: no fall damage, a drift on landing, and wall-running. */
    public static final RegistryObject<Item> AERO_STRIDE_GREAVES = track(ITEMS.register("aero_stride_greaves",
            () -> new AeroStrideGreavesItem(props("aero_stride_greaves")
                    .humanoidArmor(ModToolMaterials.AERO_STRIDE, ArmorType.BOOTS))));

    // ---------------------------------------------------------------- helpers

    /** A plain material item. */
    private static RegistryObject<Item> simple(String name) {
        return track(ITEMS.register(name, () -> new Item(props(name))));
    }

    /** The item form of a block. */
    private static RegistryObject<Item> blockItem(String name, Supplier<? extends Block> block) {
        return track(ITEMS.register(name, () -> new BlockItem(block.get(), props(name))));
    }

    /** Every item must carry its own registry id in 26.2. */
    public static Item.Properties props(String name) {
        return new Item.Properties().setId(ITEMS.key(name));
    }

    private static RegistryObject<Item> track(RegistryObject<Item> item) {
        TAB_ORDER.add(item);
        return item;
    }

    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        ITEMS.register(modBus);
    }
}

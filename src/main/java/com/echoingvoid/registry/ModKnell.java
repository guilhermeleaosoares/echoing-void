package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.KnellIntegratorBlock;
import com.echoingvoid.item.KnellArmorItem;
import net.minecraft.core.component.DataComponents;
import net.minecraft.util.Unit;
import com.echoingvoid.item.KnellAxeItem;
import com.echoingvoid.item.KnellPickaxeItem;
import com.echoingvoid.item.KnellSwordItem;
import com.echoingvoid.item.KnellMaterials;
import net.minecraft.world.item.AxeItem;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.HoeItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.ShovelItem;
import net.minecraft.world.item.equipment.ArmorType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.DropExperienceBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.util.valueproviders.UniformInt;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * Knell - the tier above netherite, and the station that applies it.
 *
 * <p>Gameplay intent: depth alone cannot gate a tier above netherite, because the player has
 * already been to the bottom of the world by then. Knell is gated on <em>place</em> instead. It
 * exists only in the Hollow Horizon, only below y 34, only in raw phonolite, and only a netherite
 * pickaxe drops it - so reaching it means the portal, the dimension, and a full netherite kit
 * first. There is deliberately no knell sword recipe: the ingot cannot be crafted into anything
 * you wear or swing, it can only be integrated onto finished netherite gear at a Resonance
 * Integrator, which keeps the entire vanilla ladder on the critical path rather than beside it.
 *
 * <p>The ore is very rare on purpose - two veins of two blocks per chunk, per
 * {@code docs/spec/expansion.json} - so a full resonant set is a project rather than an afternoon.
 *
 * <p>As in {@link ModBlocks} and {@link ModTerrainBlocks}, mining tool and tier are expressed
 * through block tags, because 26.2 has no Java API for either. The code contributes only
 * {@code requiresCorrectToolForDrops()}; {@code tools/gen_knell_data.py} writes the tags that
 * decide the rest. This class keeps its own {@link DeferredRegister} pair for the same reason
 * {@link ModTerrainBlocks} does: the tier can be regenerated and reviewed without touching the
 * hand-written blocks either side of it.
 */
public final class ModKnell {
    private ModKnell() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    /** Everything registered here, in the order the creative tab should list it. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ------------------------------------------------------------------ ore

    /**
     * Hardness 9.0 / Blast 12.0 | Pickaxe (Netherite) | ANCIENT_DEBRIS | Light 4 | drops raw
     * knell.
     *
     * <p>The faint glow is a findability affordance rather than a light source: at light 4 a vein
     * is a dim ember in an unlit shaft, visible if you are looking and invisible if you are not,
     * which is what makes searching for it feel like prospecting instead of like reading a map.
     *
     * <p>Uses vanilla {@link DropExperienceBlock} so the ore pays experience on break the way every
     * other ore in the game does; the drop itself comes from the loot table.
     */
    public static final RegistryObject<Block> KNELL_ORE = BLOCKS.register("knell_ore",
            () -> new DropExperienceBlock(UniformInt.of(4, 9), props("knell_ore")
                    .mapColor(MapColor.DEEPSLATE)
                    .strength(9.0F, 12.0F)
                    .sound(SoundType.ANCIENT_DEBRIS)
                    .lightLevel(state -> 4)
                    .requiresCorrectToolForDrops()));

    // --------------------------------------------------------------- storage

    /**
     * Hardness 55.0 / Blast 1200.0 | Pickaxe (Netherite) | NETHERITE_BLOCK | Light 10.
     *
     * <p>Above the netherite block on every axis the netherite block is defined by, and strongly
     * emissive, because nine ingots of the rarest material in the mod should be something a player
     * builds a room around rather than a slab they hide in a chest.
     */
    public static final RegistryObject<Block> KNELL_BLOCK = BLOCKS.register("knell_block",
            () -> new Block(props("knell_block")
                    .mapColor(MapColor.QUARTZ)
                    .strength(55.0F, 1200.0F)
                    .sound(SoundType.NETHERITE_BLOCK)
                    .lightLevel(state -> 10)
                    .requiresCorrectToolForDrops()));

    // --------------------------------------------------------------- station

    /**
     * Hardness 6.0 / Blast 1200.0 | Pickaxe (Diamond) | NETHERITE_BLOCK | Light 7.
     *
     * <p>Blast resistance matches the Inversion Anvil's: a station a player has spent a knell
     * ingot on should survive a creeper walking into it. Only diamond tier to break, so it can be
     * picked up and moved once built - gating retrieval behind netherite would punish rearranging
     * a base.
     */
    public static final RegistryObject<Block> RESONANCE_INTEGRATOR = BLOCKS.register("knell_integrator",
            () -> new KnellIntegratorBlock(props("knell_integrator")
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(6.0F, 1200.0F)
                    .sound(SoundType.NETHERITE_BLOCK)
                    .lightLevel(state -> 7)
                    .noOcclusion()
                    .requiresCorrectToolForDrops()));

    // ------------------------------------------------------------- materials

    /** What the ore drops. Smelts to an ingot; nothing else consumes it. */
    public static final RegistryObject<Item> RAW_KNELL = simple("raw_knell");

    /** The addition slot of every integration recipe, and the repair material for the gear. */
    public static final RegistryObject<Item> KNELL_INGOT = simple("knell_ingot");

    /**
     * The template slot. Craftable rather than structure loot on purpose: the tier is already
     * gated by the dimension and by the ore's rarity, and hiding a second mandatory key inside a
     * structure would make the whole ladder hostage to worldgen.
     */
    public static final RegistryObject<Item> RESONANCE_TEMPLATE = simple("knell_template");

    // ----------------------------------------------------------- block items

    public static final RegistryObject<Item> KNELL_ORE_ITEM = blockItem("knell_ore", KNELL_ORE);
    public static final RegistryObject<Item> KNELL_BLOCK_ITEM = blockItem("knell_block", KNELL_BLOCK);
    public static final RegistryObject<Item> RESONANCE_INTEGRATOR_ITEM = blockItem("knell_integrator", RESONANCE_INTEGRATOR);

    // ------------------------------------------------------------------ gear
    // Attack damage and swing speed baselines are netherite's, verbatim, so the
    // only thing that changes between a netherite tool and its resonant form is
    // the material - which is exactly what the smithing upgrade claims to do.
    // 26.2 folds swords, pickaxes and armour into Item.Properties, but axes,
    // shovels and hoes still need their own classes: stripping, path-making and
    // tilling live in those classes' useOn, and a plain Item with .axe(...) can
    // fight but cannot strip a log.

    /** The Harmonic Sword's sonic discharge, amplified: longer, wider - see KnellSwordItem. */
    public static final RegistryObject<Item> RESONANT_SWORD = tool("knell_sword",
            () -> new KnellSwordItem(gearProps("knell_sword").sword(KnellMaterials.KNELL, 3.0F, -2.4F)));

    /** The Harmonic Pickaxe's rhythm-shatter, amplified to a 5-wide x 4-tall plane - see KnellPickaxeItem. */
    public static final RegistryObject<Item> RESONANT_PICKAXE = tool("knell_pickaxe",
            () -> new KnellPickaxeItem(gearProps("knell_pickaxe").pickaxe(KnellMaterials.KNELL, 1.0F, -2.8F)));

    /** Fells any tree from any log, no base requirement - see KnellAxeItem. */
    public static final RegistryObject<Item> RESONANT_AXE = tool("knell_axe",
            () -> new KnellAxeItem(KnellMaterials.KNELL, 5.0F, -3.0F, gearProps("knell_axe")));

    public static final RegistryObject<Item> RESONANT_SHOVEL = tool("knell_shovel",
            () -> new ShovelItem(KnellMaterials.KNELL, 1.5F, -3.0F, gearProps("knell_shovel")));

    public static final RegistryObject<Item> RESONANT_HOE = tool("knell_hoe",
            () -> new HoeItem(KnellMaterials.KNELL, -4.0F, 0.0F, gearProps("knell_hoe")));

    /**
     * The template that lets an elytra be integrated, and the one piece of knell kit that is not
     * made of the same stuff as the rest.
     *
     * <p>PLAYER: "this would require an especially crafted template that is crafted using knell
     * rather than null iron and resonance shards, so it is harder to obtain but gives players a
     * reason to seek knell sets."
     *
     * <p>So where {@code knell_template} is four resonance shards around a null-iron ingot -
     * materials a player already has before they reach this dimension's floor - this one is four
     * knell ingots around an elytra membrane. Knell is the rarest ore in the mod, bottom-biased and
     * confined to raw phonolite, and the recipe yields ONE where the ordinary template yields two.
     * A player who wants to fly in armour has to go and mine for it.
     */
    public static final RegistryObject<Item> ELYTRA_TEMPLATE = simple("knell_elytra_template");

    public static final RegistryObject<Item> RESONANT_HELMET = armor("knell_helmet", ArmorType.HELMET);
    public static final RegistryObject<Item> RESONANT_CHESTPLATE = armor("knell_chestplate", ArmorType.CHESTPLATE);
    public static final RegistryObject<Item> RESONANT_LEGGINGS = armor("knell_leggings", ArmorType.LEGGINGS);
    public static final RegistryObject<Item> RESONANT_BOOTS = armor("knell_boots", ArmorType.BOOTS);

    /**
     * A Knell chestplate with an elytra folded into it.
     *
     * <p>PLAYER: "i want an elytra template, that makes, only the knell chestplate, be able to
     * integrate with an elytra... so players get the benefits of an elytra and extra protection
     * from the armor."
     *
     * <p>It is a {@link KnellArmorItem} like the plate it was made from, so it banks and releases
     * exactly as before - 65% of every hit, up to 100, out through a 9-block ring. The armour
     * figures are {@link KnellMaterials#RESONANT_AERO}, which is {@code RESONANT} to the last
     * digit; nothing is traded away for the wings.
     *
     * <p>{@link DataComponents#GLIDER} is the whole of the flight. {@code LivingEntity.canGlideUsing}
     * asks only whether the stack carries it, whether the slot matches the item's own
     * {@code EQUIPPABLE} slot, and whether the item is about to break - so a chestplate holding it
     * glides on exactly the terms an elytra does.
     *
     * <p>One consequence worth knowing rather than discovering: gliding costs durability.
     * {@code LivingEntity.tickFallFlying} spends one point per twenty ticks of flight, and here that
     * comes out of the same pool the armour is protecting you with. Flying wears your chestplate.
     * That is the trade the single item makes, and it is why the plain Knell chestplate is still
     * worth keeping for a fight you expect to be long.
     */
    public static final RegistryObject<Item> AEROSHELL = track(ITEMS.register("knell_aeroshell",
            () -> new KnellArmorItem(gearProps("knell_aeroshell")
                    .humanoidArmor(KnellMaterials.RESONANT_AERO, ArmorType.CHESTPLATE)
                    .component(DataComponents.GLIDER, Unit.INSTANCE))));

    // ---------------------------------------------------------------- helpers

    /** Shared starting point: every block must carry its own registry id in 26.2. */
    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    /**
     * The two things every piece of resonant gear shares: it does not burn, exactly as netherite
     * does not, and it announces itself as end-game in the tooltip.
     */
    private static Item.Properties gearProps(String name) {
        return new Item.Properties()
                .setId(ITEMS.key(name))
                .fireResistant()
                .rarity(Rarity.RARE);
    }

    /** A plain material item. */
    private static RegistryObject<Item> simple(String name) {
        return track(ITEMS.register(name,
                () -> new Item(new Item.Properties().setId(ITEMS.key(name)).rarity(Rarity.RARE))));
    }

    /** The item form of a block. */
    private static RegistryObject<Item> blockItem(String name, Supplier<? extends Block> block) {
        return track(ITEMS.register(name,
                () -> new BlockItem(block.get(), new Item.Properties().setId(ITEMS.key(name)))));
    }

    /** A tool or weapon, which supplies its own item class. */
    private static RegistryObject<Item> tool(String name, Supplier<Item> factory) {
        return track(ITEMS.register(name, factory));
    }

    /**
     * One of the four humanoid armour slots.
     *
     * <p>{@link KnellArmorItem}, not a plain {@code Item}: the plates carry the Resonance set's
     * kinetic bank and shockwave, amplified. Registering them as plain items is exactly what
     * PLAYER hit - the tier above silently had fewer abilities than the tier below it, because
     * nothing in the item, the model or the tooltip said otherwise.
     */
    private static RegistryObject<Item> armor(String name, ArmorType type) {
        return track(ITEMS.register(name,
                () -> new KnellArmorItem(gearProps(name).humanoidArmor(KnellMaterials.RESONANT, type))));
    }

    private static RegistryObject<Item> track(RegistryObject<Item> item) {
        TAB_ORDER.add(item);
        return item;
    }

    /** Every knell item, in the order the creative tab should show them. */
    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

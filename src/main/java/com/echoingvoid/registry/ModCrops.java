package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.VoidAttachedStemBlock;
import com.echoingvoid.block.VoidCropBlock;
import com.echoingvoid.block.VoidStemBlock;
import com.echoingvoid.block.VoidFarmlandBlock;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.TagKey;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.component.Consumable;
import net.minecraft.world.item.component.Consumables;
import net.minecraft.world.item.consume_effects.ApplyStatusEffectsConsumeEffect;
import net.minecraft.world.level.block.AttachedStemBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.StemBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Farming in the Hollow Horizon: the tilled soil, four crops, their seeds and Resonant Bread.
 *
 * <p>The set mirrors vanilla's so nothing has to be relearned - a grain, a root, a tuber and a
 * gourd - but none of it interoperates with vanilla's, in either direction. That exclusivity is
 * enforced entirely by {@link VoidFarmlandBlock} not being a {@code FarmlandBlock}; see its
 * javadoc for the mechanism. The only place it needs help is the two stem blocks, whose support
 * test is a block TAG rather than an {@code instanceof}, hence {@link #VOID_SOIL}.
 *
 * <p>The seeds are plain {@link BlockItem}s with {@code useItemDescriptionPrefix()}, which is how
 * 26.2 spells what used to be {@code ItemNameBlockItem}: the stack is named
 * {@code item.echoing_void.<id>} rather than taking the crop block's name, so "Chime Root" is not
 * displayed as "Chime Roots" in the hand.
 *
 * <p>Registration order inside this class matters in one place only: {@link #ECHO_GOURD_STEM}
 * names its fruit, its attached form and its seed by {@link ResourceKey}, never by object, because
 * all three are registered around it and two of them are in a different registry entirely.
 */
public final class ModCrops {
    private ModCrops() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    /**
     * The soil the stems accept. A one-block tag rather than an {@code instanceof} because
     * {@link StemBlock} and {@link AttachedStemBlock} take a {@code TagKey<Block>} and offer no
     * other hook - their support test is a codec field, not a method.
     */
    public static final TagKey<Block> VOID_SOIL =
            TagKey.create(Registries.BLOCK, EchoingVoid.id("void_farmland"));

    /**
     * What a grown gourd will settle ON, as opposed to what its stem grows FROM.
     *
     * <p>These are two different questions and vanilla asks them with two different tags.
     * {@code StemBlock} takes {@code stemSupportBlocks} and {@code fruitSupportBlocks}
     * separately, and melon passes {@code #supports_crops} (farmland alone) for the first and
     * {@code #supports_stem_fruit} -> {@code #supports_vegetation} (dirt, grass, podzol, moss,
     * mud) for the second - which is exactly why a melon farm puts its stems on a tilled row and
     * lets the melons land on plain ground either side.
     *
     * <p>PLAYER: "does the echo gourd grow on normal moss or only tilled? i dont mean the seeds,
     * the plant grows fine, im talking about the block fruit?" Only tilled, because
     * {@link #ECHO_GOURD_STEM} was handing {@link #VOID_SOIL} to both slots - the one tag that
     * existed, rather than a decision that gourds should be stricter than melons. This is the
     * missing half.
     */
    public static final TagKey<Block> VOID_STEM_FRUIT_SOIL =
            TagKey.create(Registries.BLOCK, EchoingVoid.id("void_stem_fruit_soil"));

    // ------------------------------------------------------------- item keys
    // Named before the items exist. A crop block is built during BLOCK registration and has to
    // name its seed then; an Item reference at that point would be null.

    private static final ResourceKey<Item> K_WHEAT_SEEDS = itemKey("resonant_wheat_seeds");
    private static final ResourceKey<Item> K_CHIME_ROOT = itemKey("chime_root");
    private static final ResourceKey<Item> K_VOID_TUBER = itemKey("void_tuber");
    private static final ResourceKey<Item> K_GOURD_SEEDS = itemKey("echo_gourd_seeds");

    private static final ResourceKey<Block> K_ECHO_GOURD = blockKey("echo_gourd");
    private static final ResourceKey<Block> K_GOURD_STEM = blockKey("echo_gourd_stem");
    private static final ResourceKey<Block> K_ATTACHED_STEM = blockKey("attached_echo_gourd_stem");

    // ------------------------------------------------------------------ soil

    /**
     * Hardness 0.6 / Blast 0.6 | Shovel-ish | GRAVEL - one step harder than the moss it comes
     * from, exactly as vanilla farmland is one step harder than dirt.
     */
    public static final RegistryObject<Block> VOID_FARMLAND = BLOCKS.register("void_farmland",
            () -> new VoidFarmlandBlock(props("void_farmland")
                    .mapColor(MapColor.WARPED_NYLIUM)
                    .strength(0.6F, 0.6F)
                    .sound(SoundType.GRAVEL)
                    .randomTicks()));

    // ----------------------------------------------------------------- crops

    public static final RegistryObject<Block> RESONANT_WHEAT = BLOCKS.register("resonant_wheat",
            () -> new VoidCropBlock(K_WHEAT_SEEDS, cropProps("resonant_wheat", MapColor.COLOR_CYAN)));

    public static final RegistryObject<Block> CHIME_ROOTS = BLOCKS.register("chime_roots",
            () -> new VoidCropBlock(K_CHIME_ROOT, cropProps("chime_roots", MapColor.COLOR_LIGHT_BLUE)));

    public static final RegistryObject<Block> VOID_TUBERS = BLOCKS.register("void_tubers",
            () -> new VoidCropBlock(K_VOID_TUBER, cropProps("void_tubers", MapColor.COLOR_PURPLE)));

    // ----------------------------------------------------------- the gourd

    /**
     * Hardness 1.0 / Blast 1.0 | Axe | WOOD - vanilla pumpkin's figures. It generates in patches
     * on the Resonant Plains and is the one crop a player meets before they own a hoe.
     *
     * <p>PLAYER: "when the echo gourd is pushed by a piston, just like a melon, it is broken and
     * drops the gourd slices." Vanilla's melon does exactly that, and for exactly this reason -
     * {@code Blocks.MELON} carries {@code pushReaction(PushReaction.DESTROY)}, and the piston's
     * own destroy pass calls {@code dropResources} before clearing the block
     * (PistonBaseBlock.moveBlocks), so the loot table runs and the slices fall. That is what makes
     * the classic piston-harvest farm work, and without the flag the gourd was simply shoved a
     * block along instead, which is not a farm.
     *
     * <p>Nothing else was missing: the stems have had DESTROY all along through
     * {@link #cropProps}, and the loot table already pays 3-7 slices with Fortune, capped at 9.
     */
    public static final RegistryObject<Block> ECHO_GOURD = BLOCKS.register("echo_gourd",
            () -> new Block(props("echo_gourd")
                    .mapColor(MapColor.COLOR_CYAN)
                    .strength(1.0F, 1.0F)
                    .sound(SoundType.WOOD)
                    .pushReaction(PushReaction.DESTROY)
                    .lightLevel(state -> 5)));

    public static final RegistryObject<Block> ECHO_GOURD_STEM = BLOCKS.register("echo_gourd_stem",
            () -> new VoidStemBlock(K_ECHO_GOURD, K_ATTACHED_STEM, K_GOURD_SEEDS,
                    VOID_SOIL, VOID_STEM_FRUIT_SOIL,
                    cropProps("echo_gourd_stem", MapColor.COLOR_CYAN)));

    /**
     * The bent stem that appears once a gourd has grown beside it.
     *
     * <p>Argument order is {@code (stem, fruit, seed, support, properties)} - note that the CODEC
     * declares fruit before stem while the constructor takes stem first. Swapping them compiles
     * cleanly and produces a stem that never reconnects to its own fruit.
     */
    public static final RegistryObject<Block> ATTACHED_ECHO_GOURD_STEM =
            BLOCKS.register("attached_echo_gourd_stem",
                    () -> new VoidAttachedStemBlock(K_GOURD_STEM, K_ECHO_GOURD, K_GOURD_SEEDS,
                            VOID_SOIL, cropProps("attached_echo_gourd_stem", MapColor.COLOR_CYAN)));

    // ----------------------------------------------------------------- foods

    /** Carrot's figures. */
    private static final FoodProperties CHIME_ROOT_FOOD =
            new FoodProperties.Builder().nutrition(3).saturationModifier(0.6F).build();

    /** Potato's figures - a filler crop, not a meal. */
    private static final FoodProperties VOID_TUBER_FOOD =
            new FoodProperties.Builder().nutrition(1).saturationModifier(0.3F).build();

    /** One better than bread, because it costs a dimension to make. */
    private static final FoodProperties RESONANT_BREAD_FOOD =
            new FoodProperties.Builder().nutrition(6).saturationModifier(0.6F).build();

    /**
     * Absorption is the effect that reads as this dimension: a standing wave held around the
     * eater that soaks a few hits and then collapses. Ninety seconds of two extra hearts, plus a
     * five-second mend so a bite in a fight is worth taking.
     */
    private static final Consumable RESONANT_BREAD_EFFECT = Consumables.defaultFood()
            .onConsume(new ApplyStatusEffectsConsumeEffect(List.of(
                    new MobEffectInstance(MobEffects.ABSORPTION, 1800, 0),
                    new MobEffectInstance(MobEffects.REGENERATION, 100, 0))))
            .build();

    /** One slice of a gourd, on melon-slice figures. */
    private static final FoodProperties ECHO_GOURD_SLICE_FOOD =
            new FoodProperties.Builder().nutrition(2).saturationModifier(0.3F).build();

    /** Pumpkin pie's figures. The best meal in the mod, and the most work to make. */
    private static final FoodProperties HUMMING_TART_FOOD =
            new FoodProperties.Builder().nutrition(8).saturationModifier(0.6F).build();

    // PLAYER: "all void foods shoudl have an effect, not just the resonant bread, so chime roots
    // echo gourd foods and the other pink tube things, they should all have different special
    // effects that help navigate the echoing void."
    //
    // So each one answers a different hazard of the dimension rather than being a different
    // number of hearts, and no two overlap:
    //
    //   chime root    the dark            - it is a dimension of black rock under a dead sky
    //   void tuber    the gaps            - islands are far apart and the fall is the whole map
    //   gourd slice   the crossing        - being quick over an exposed span is the difference
    //   humming tart  all three, longer   - the meal you eat before setting out, not during

    /** Night vision: the root hums, and a player who has eaten one hears the dark. */
    private static final Consumable CHIME_ROOT_EFFECT = Consumables.defaultFood()
            .onConsume(new ApplyStatusEffectsConsumeEffect(List.of(
                    new MobEffectInstance(MobEffects.NIGHT_VISION, 900, 0))))
            .build();

    /** Jump boost and slow falling: the tuber is what makes island-hopping survivable. */
    private static final Consumable VOID_TUBER_EFFECT = Consumables.defaultFood()
            .onConsume(new ApplyStatusEffectsConsumeEffect(List.of(
                    new MobEffectInstance(MobEffects.JUMP_BOOST, 600, 0),
                    new MobEffectInstance(MobEffects.SLOW_FALLING, 300, 0))))
            .build();

    /** Speed: a slice is a quick thing to eat and a quick thing to be. */
    private static final Consumable ECHO_GOURD_SLICE_EFFECT = Consumables.defaultFood()
            .onConsume(new ApplyStatusEffectsConsumeEffect(List.of(
                    new MobEffectInstance(MobEffects.SPEED, 900, 0))))
            .build();

    /**
     * The expedition meal: every navigation effect at once and for longer, plus the standing wave
     * the bread gives. Expensive - a whole gourd, grain, and a hushwater bucket's worth of work.
     */
    private static final Consumable HUMMING_TART_EFFECT = Consumables.defaultFood()
            .onConsume(new ApplyStatusEffectsConsumeEffect(List.of(
                    new MobEffectInstance(MobEffects.NIGHT_VISION, 2400, 0),
                    new MobEffectInstance(MobEffects.SLOW_FALLING, 1200, 0),
                    new MobEffectInstance(MobEffects.SPEED, 1800, 0),
                    new MobEffectInstance(MobEffects.ABSORPTION, 1800, 1))))
            .build();

    // ----------------------------------------------------------------- items

    public static final RegistryObject<Item> RESONANT_WHEAT_SEEDS =
            seed("resonant_wheat_seeds", RESONANT_WHEAT);

    /** The harvest. Not edible on its own, exactly like wheat - it is the bread ingredient. */
    public static final RegistryObject<Item> RESONANT_GRAIN = track(ITEMS.register("resonant_grain",
            () -> new Item(itemProps("resonant_grain"))));

    public static final RegistryObject<Item> CHIME_ROOT = track(ITEMS.register("chime_root",
            () -> new BlockItem(CHIME_ROOTS.get(), itemProps("chime_root")
                    .useItemDescriptionPrefix()
                    .food(CHIME_ROOT_FOOD, CHIME_ROOT_EFFECT))));

    public static final RegistryObject<Item> VOID_TUBER = track(ITEMS.register("void_tuber",
            () -> new BlockItem(VOID_TUBERS.get(), itemProps("void_tuber")
                    .useItemDescriptionPrefix()
                    .food(VOID_TUBER_FOOD, VOID_TUBER_EFFECT))));

    public static final RegistryObject<Item> ECHO_GOURD_SEEDS =
            seed("echo_gourd_seeds", ECHO_GOURD_STEM);

    public static final RegistryObject<Item> ECHO_GOURD_ITEM = track(ITEMS.register("echo_gourd",
            () -> new BlockItem(ECHO_GOURD.get(), itemProps("echo_gourd"))));

    public static final RegistryObject<Item> VOID_FARMLAND_ITEM = track(ITEMS.register("void_farmland",
            () -> new BlockItem(VOID_FARMLAND.get(), itemProps("void_farmland"))));

    public static final RegistryObject<Item> RESONANT_BREAD = track(ITEMS.register("resonant_bread",
            () -> new Item(itemProps("resonant_bread")
                    .food(RESONANT_BREAD_FOOD, RESONANT_BREAD_EFFECT))));

    /**
     * PLAYER: "the resonance gourds should be able to be consumed, so it can drop slices like a
     * watermelon, and these slices can be crafted back into blocks, or into a humming tart."
     *
     * <p>So the gourd behaves like a melon: breaking the block drops slices (loot table), a slice
     * is food, and nine slices go back into a gourd. A plain {@code Item}, not a {@code BlockItem}
     * - a slice is not placeable, which is exactly what separates it from the whole gourd.
     */
    public static final RegistryObject<Item> ECHO_GOURD_SLICE = track(ITEMS.register("echo_gourd_slice",
            () -> new Item(itemProps("echo_gourd_slice")
                    .food(ECHO_GOURD_SLICE_FOOD, ECHO_GOURD_SLICE_EFFECT))));

    /** This dimension's pumpkin pie, and the best thing in it to eat before a long crossing. */
    public static final RegistryObject<Item> HUMMING_TART = track(ITEMS.register("humming_tart",
            () -> new Item(itemProps("humming_tart")
                    .food(HUMMING_TART_FOOD, HUMMING_TART_EFFECT))));

    // --------------------------------------------------------------- helpers

    private static ResourceKey<Item> itemKey(String name) {
        return ResourceKey.create(Registries.ITEM, EchoingVoid.id(name));
    }

    private static ResourceKey<Block> blockKey(String name) {
        return ResourceKey.create(Registries.BLOCK, EchoingVoid.id(name));
    }

    private static BlockBehaviour.Properties props(String name) {
        return BlockBehaviour.Properties.of().setId(BLOCKS.key(name));
    }

    /**
     * The shape every crop and stem shares, copied from vanilla wheat: no collision, instant
     * break, random-ticked so it can grow, destroyed rather than dragged by pistons, and
     * {@code noOcclusion} so the cross model does not black out the block beside it.
     */
    private static BlockBehaviour.Properties cropProps(String name, MapColor colour) {
        return props(name)
                .mapColor(colour)
                .noCollision()
                .randomTicks()
                .instabreak()
                .sound(SoundType.CROP)
                .noOcclusion()
                .pushReaction(PushReaction.DESTROY);
    }

    private static Item.Properties itemProps(String name) {
        return new Item.Properties().setId(ITEMS.key(name));
    }

    /** A seed: the crop's block item, named after the item rather than after the block. */
    private static RegistryObject<Item> seed(String name, RegistryObject<Block> crop) {
        return track(ITEMS.register(name,
                () -> new BlockItem(crop.get(), itemProps(name).useItemDescriptionPrefix())));
    }

    private static RegistryObject<Item> track(RegistryObject<Item> item) {
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

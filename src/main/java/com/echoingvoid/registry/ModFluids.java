package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.fluid.HushwaterFluid;
import com.echoingvoid.fluid.HushwaterFluidType;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.FlowingFluid;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.fluids.FluidType;
import net.minecraftforge.fluids.ForgeFlowingFluid;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Hushwater: the fluid type, its source and flowing forms, the liquid block they paint, and the
 * bucket that carries it.
 *
 * <p>The five registrations are mutually recursive - the fluid names its block, the block names
 * the fluid, the bucket names the fluid and the fluid names the bucket - which is exactly why
 * every field here is a {@link RegistryObject} and every reference is a supplier. Forge's
 * {@link ForgeFlowingFluid.Properties} takes suppliers for the same reason; passing a resolved
 * value would force one of the four to exist before the others.
 *
 * <p>Flow numbers, and why:
 *
 * <ul>
 *   <li>{@code tickRate 12} - water is 5, lava 30. Hushwater visibly crawls.
 *   <li>{@code levelDecreasePerBlock 1} - the same as water, so a source still reaches seven
 *       blocks. This is deliberate against the "thicker than water" instinct: a stream that dies
 *       after three blocks cannot fall off an island and reach the ground, and reaching the
 *       ground is the whole point of the waterfalls.
 *   <li>{@code slopeFindDistance 3} - between water's 4 and lava's 2. It hunts for a drop, but
 *       less far, so a spill goes over the nearest edge rather than snaking to the best one.
 * </ul>
 */
public final class ModFluids {
    private ModFluids() {}

    public static final DeferredRegister<FluidType> FLUID_TYPES =
            DeferredRegister.create(ForgeRegistries.FLUID_TYPES, EchoingVoid.MODID);

    public static final DeferredRegister<Fluid> FLUIDS =
            DeferredRegister.create(ForgeRegistries.FLUIDS, EchoingVoid.MODID);

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    /** Items registered here, for {@code ModCreativeTabs} to walk. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    public static final RegistryObject<FluidType> HUSHWATER_TYPE =
            FLUID_TYPES.register("hushwater", HushwaterFluidType::new);

    public static final RegistryObject<FlowingFluid> HUSHWATER =
            FLUIDS.register("hushwater", () -> new HushwaterFluid.Source(properties()));

    public static final RegistryObject<FlowingFluid> FLOWING_HUSHWATER =
            FLUIDS.register("flowing_hushwater", () -> new HushwaterFluid.Flowing(properties()));

    /**
     * The block form. {@code SoundType.EMPTY} and {@code noLootTable()} match vanilla water:
     * a liquid block is never broken by hand and never drops anything.
     */
    public static final RegistryObject<LiquidBlock> HUSHWATER_BLOCK = BLOCKS.register("hushwater",
            () -> new LiquidBlock(HUSHWATER::get, BlockBehaviour.Properties.of()
                    .setId(BLOCKS.key("hushwater"))
                    .mapColor(MapColor.COLOR_CYAN)
                    .replaceable()
                    .noCollision()
                    .strength(100.0F)
                    .pushReaction(PushReaction.DESTROY)
                    .noLootTable()
                    .liquid()
                    .lightLevel(state -> 6)
                    .sound(SoundType.EMPTY)));

    public static final RegistryObject<Item> HUSHWATER_BUCKET = track(ITEMS.register("hushwater_bucket",
            () -> new BucketItem(HUSHWATER::get, new Item.Properties()
                    .setId(ITEMS.key("hushwater_bucket"))
                    .craftRemainder(net.minecraft.world.item.Items.BUCKET)
                    .stacksTo(1))));

    private static ForgeFlowingFluid.Properties properties() {
        return new ForgeFlowingFluid.Properties(HUSHWATER_TYPE, HUSHWATER, FLOWING_HUSHWATER)
                .block(HUSHWATER_BLOCK)
                .bucket(HUSHWATER_BUCKET)
                .slopeFindDistance(3)
                .levelDecreasePerBlock(1)
                .tickRate(12)
                .explosionResistance(100.0F);
    }

    private static RegistryObject<Item> track(RegistryObject<Item> item) {
        TAB_ORDER.add(item);
        return item;
    }

    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        FLUID_TYPES.register(modBus);
        FLUIDS.register(modBus);
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}

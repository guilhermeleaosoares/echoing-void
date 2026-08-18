package com.echoingvoid.block;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.registry.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import org.jspecify.annotations.Nullable;

import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/**
 * The Inversion Anvil - an anvil that runs the crafting grid backwards.
 *
 * <p>Right-click the anvil holding a damaged tool, weapon or piece of armour and it is taken apart:
 * the item is consumed and its raw materials come back, scaled by how much durability was left.
 * A pristine tool returns most of what went into it; something one hit from breaking returns
 * nothing but the noise. The ratio comes straight from the item's {@code DataComponents.DAMAGE} and
 * {@code DataComponents.MAX_DAMAGE} (read through {@code ItemStack#getDamageValue} and
 * {@code #getMaxDamage}), so it works for any damageable item without a per-item rule.
 *
 * <p>The yield table only covers cases where the answer is obvious - the five vanilla tool and
 * armour families - plus everything from this mod, which comes back as resonance shards. Anything
 * else is refused rather than guessed at: the anvil simply does not take it.
 *
 * <p>The anvil never damages what the player is holding. It either consumes the item outright or
 * declines to act.
 */
public class InversionAnvilBlock extends Block {
    /** Fraction of the theoretical worth an uncrafted item returns; the rest is lost to the process. */
    private static final float RECOVERY = 0.8F;

    /** Nuggets to an ingot - also the resolution the yield is computed at. */
    private static final int NUGGETS_PER_UNIT = 9;

    /** Shards returned for a pristine piece of this mod's own gear. */
    private static final int MOD_GEAR_WORTH = 4;

    /**
     * Which way the anvil faces. The model is a real anvil silhouette rather than a cube, so it
     * has a long axis and has to be oriented, exactly as vanilla's anvil is.
     */
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;

    /** The anvil outline, box for box from vanilla: base, waist, lip and horn. */
    private static final Map<Direction.Axis, VoxelShape> SHAPES = Shapes.rotateHorizontalAxis(
            Shapes.or(
                    Block.column(12.0, 0.0, 4.0),
                    Block.column(8.0, 10.0, 4.0, 5.0),
                    Block.column(4.0, 8.0, 5.0, 10.0),
                    Block.column(10.0, 16.0, 10.0, 16.0)));

    public InversionAnvilBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        // Clockwise from the placer's facing, so the anvil sits across you as vanilla's does.
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getClockWise());
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(FACING, rotation.rotate(state.getValue(FACING)));
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPES.get(state.getValue(FACING).getAxis());
    }

    @Override
    protected InteractionResult useItemOn(
        ItemStack itemStack,
        BlockState state,
        Level level,
        BlockPos pos,
        Player player,
        InteractionHand hand,
        BlockHitResult hitResult
    ) {
        if (!itemStack.isDamageableItem()) {
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        Salvage salvage = salvageFor(itemStack);
        if (salvage == null) {
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        if (level instanceof ServerLevel serverLevel) {
            float remaining = remainingDurability(itemStack);
            itemStack.consume(1, player);
            dropSalvage(serverLevel, pos, hitResult, salvage, remaining);

            serverLevel.playSound(null, pos, SoundEvents.ANVIL_USE, SoundSource.BLOCKS, 0.8F, 0.6F);
            serverLevel.sendParticles(
                ParticleTypes.ELECTRIC_SPARK,
                pos.getX() + 0.5,
                pos.getY() + 1.05,
                pos.getZ() + 0.5,
                8,
                0.3,
                0.1,
                0.3,
                0.05
            );
        }

        return InteractionResult.SUCCESS;
    }

    /** 1.0 for an untouched item, 0.0 for one on its last point of durability. */
    private static float remainingDurability(ItemStack stack) {
        int maxDamage = stack.getMaxDamage();
        if (maxDamage <= 0) {
            return 0.0F;
        }

        return Mth.clamp((maxDamage - stack.getDamageValue()) / (float) maxDamage, 0.0F, 1.0F);
    }

    private static void dropSalvage(ServerLevel level, BlockPos pos, BlockHitResult hitResult, Salvage salvage, float remaining) {
        // Work in ninths so a part-worn item can pay out in nuggets where the material has them.
        int ninths = Mth.floor(remaining * RECOVERY * salvage.worth() * NUGGETS_PER_UNIT);
        int units = ninths / NUGGETS_PER_UNIT;
        if (units > 0) {
            Block.popResourceFromFace(level, pos, hitResult.getDirection(), new ItemStack(salvage.unit(), units));
        }

        Item fraction = salvage.fraction();
        if (fraction != null) {
            int remainder = ninths % NUGGETS_PER_UNIT;
            if (remainder > 0) {
                Block.popResourceFromFace(level, pos, hitResult.getDirection(), new ItemStack(fraction, remainder));
            }
        }
    }

    private static @Nullable Salvage salvageFor(ItemStack stack) {
        Salvage vanilla = SalvageTable.BY_ITEM.get(stack.getItem());
        if (vanilla != null) {
            return vanilla;
        }

        // Anything forged in the Echoing Void goes back to the shards it was grown from.
        Identifier id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if (id != null && EchoingVoid.MODID.equals(id.getNamespace())) {
            return new Salvage(ModItems.RESONANCE_SHARD.get(), null, MOD_GEAR_WORTH);
        }

        return null;
    }

    /**
     * What a piece of gear is made of.
     *
     * @param unit     the ingot or gem the item is built from
     * @param fraction the ninth-of-a-unit form, where the material has one; null otherwise
     * @param worth    units in a pristine example, taken from the vanilla crafting recipe
     */
    private record Salvage(Item unit, @Nullable Item fraction, int worth) {}

    /**
     * Held in a nested class so the table is built the first time the anvil is used, long after the
     * item registry has finished bootstrapping - never during it.
     */
    private static final class SalvageTable {
        private static final Map<Item, Salvage> BY_ITEM = build();

        private static Map<Item, Salvage> build() {
            Map<Item, Salvage> map = new IdentityHashMap<>();

            family(map, Items.IRON_INGOT, Items.IRON_NUGGET,
                    Items.IRON_SWORD, Items.IRON_PICKAXE, Items.IRON_AXE, Items.IRON_SHOVEL, Items.IRON_HOE,
                    Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS);

            family(map, Items.GOLD_INGOT, Items.GOLD_NUGGET,
                    Items.GOLDEN_SWORD, Items.GOLDEN_PICKAXE, Items.GOLDEN_AXE, Items.GOLDEN_SHOVEL, Items.GOLDEN_HOE,
                    Items.GOLDEN_HELMET, Items.GOLDEN_CHESTPLATE, Items.GOLDEN_LEGGINGS, Items.GOLDEN_BOOTS);

            family(map, Items.DIAMOND, null,
                    Items.DIAMOND_SWORD, Items.DIAMOND_PICKAXE, Items.DIAMOND_AXE, Items.DIAMOND_SHOVEL, Items.DIAMOND_HOE,
                    Items.DIAMOND_HELMET, Items.DIAMOND_CHESTPLATE, Items.DIAMOND_LEGGINGS, Items.DIAMOND_BOOTS);

            family(map, Items.COPPER_INGOT, null,
                    Items.COPPER_SWORD, Items.COPPER_PICKAXE, Items.COPPER_AXE, Items.COPPER_SHOVEL, Items.COPPER_HOE,
                    Items.COPPER_HELMET, Items.COPPER_CHESTPLATE, Items.COPPER_LEGGINGS, Items.COPPER_BOOTS);

            // Netherite gear is diamond gear plus a single ingot, so only that ingot comes back -
            // returning a diamond set's worth of netherite would be a duplication bug, not a feature.
            List<Item> netherite = List.of(
                    Items.NETHERITE_SWORD, Items.NETHERITE_PICKAXE, Items.NETHERITE_AXE, Items.NETHERITE_SHOVEL, Items.NETHERITE_HOE,
                    Items.NETHERITE_HELMET, Items.NETHERITE_CHESTPLATE, Items.NETHERITE_LEGGINGS, Items.NETHERITE_BOOTS);
            for (Item gear : netherite) {
                map.put(gear, new Salvage(Items.NETHERITE_INGOT, null, 1));
            }

            return Map.copyOf(map);
        }

        /** Worths below are the vanilla recipe costs for one material family. */
        private static void family(
            Map<Item, Salvage> map,
            Item unit,
            @Nullable Item fraction,
            Item sword, Item pickaxe, Item axe, Item shovel, Item hoe,
            Item helmet, Item chestplate, Item leggings, Item boots
        ) {
            map.put(sword, new Salvage(unit, fraction, 2));
            map.put(pickaxe, new Salvage(unit, fraction, 3));
            map.put(axe, new Salvage(unit, fraction, 3));
            map.put(shovel, new Salvage(unit, fraction, 1));
            map.put(hoe, new Salvage(unit, fraction, 2));
            map.put(helmet, new Salvage(unit, fraction, 5));
            map.put(chestplate, new Salvage(unit, fraction, 8));
            map.put(leggings, new Salvage(unit, fraction, 7));
            map.put(boots, new Salvage(unit, fraction, 4));
        }
    }
}

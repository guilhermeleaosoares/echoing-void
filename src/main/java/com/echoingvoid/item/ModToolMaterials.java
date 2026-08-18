package com.echoingvoid.item;

import com.echoingvoid.EchoingVoid;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ToolMaterial;
import net.minecraft.world.item.equipment.ArmorMaterial;
import net.minecraft.world.item.equipment.ArmorType;
import net.minecraft.world.item.equipment.EquipmentAsset;
import net.minecraft.world.item.equipment.EquipmentAssets;
import net.minecraft.world.level.block.Block;

import java.util.Map;

/**
 * The three tool alloys and two armour sets of The Echoing Void.
 *
 * <p>Each material is tuned to a distinct feel rather than to a linear power ladder:
 * bismuth is the quick, enchantable workhorse; void-glass is a glass cannon that shatters
 * quickly but swings and mines faster than anything else; null-iron is slow, brutal and
 * effectively permanent.
 *
 * <p>Both {@code incorrectBlocksForDrops} and the repair ingredients are tags, which is how
 * 26.2 expresses tier gating and repairability. The tag JSON lives in the datapack; only the
 * keys are declared here.
 */
public final class ModToolMaterials {
    private ModToolMaterials() {}

    // ------------------------------------------------------- tier gate tags

    /** Blocks a bismuth tool cannot harvest - the netherite-tier set. */
    public static final TagKey<Block> INCORRECT_FOR_BISMUTH_TOOL = blockTag("incorrect_for_bismuth_tool");

    /** Blocks a void-glass tool cannot harvest - it is a scalpel, not a quarry tool. */
    public static final TagKey<Block> INCORRECT_FOR_VOID_GLASS_TOOL = blockTag("incorrect_for_void_glass_tool");

    /** Blocks a null-iron tool cannot harvest - deliberately empty, it is the top of the ladder. */
    public static final TagKey<Block> INCORRECT_FOR_NULL_IRON_TOOL = blockTag("incorrect_for_null_iron_tool");

    // ------------------------------------------------------ repair item tags

    public static final TagKey<Item> BISMUTH_TOOL_MATERIALS = itemTag("bismuth_tool_materials");
    public static final TagKey<Item> VOID_GLASS_TOOL_MATERIALS = itemTag("void_glass_tool_materials");
    public static final TagKey<Item> NULL_IRON_TOOL_MATERIALS = itemTag("null_iron_tool_materials");
    public static final TagKey<Item> REPAIRS_RESONANCE = itemTag("repairs_resonance");
    public static final TagKey<Item> REPAIRS_AERO_STRIDE = itemTag("repairs_aero_stride");

    // ----------------------------------------------------------- tool alloys

    /**
     * Resonant bismuth: mines a shade faster than diamond, carries diamond-ish durability and
     * takes enchantments better than gold. The Harmonic Pickaxe is built on it.
     */
    public static final ToolMaterial RESONANT_BISMUTH = new ToolMaterial(
            INCORRECT_FOR_BISMUTH_TOOL, 1024, 9.0F, 2.5F, 22, BISMUTH_TOOL_MATERIALS);

    /**
     * Void-glass: the fastest material in the mod and by far the most fragile. The high
     * enchantment value and low attack bonus push it towards precision play - land the
     * critical, take the invisibility, disengage.
     */
    public static final ToolMaterial VOID_GLASS = new ToolMaterial(
            INCORRECT_FOR_VOID_GLASS_TOOL, 180, 13.0F, 2.0F, 26, VOID_GLASS_TOOL_MATERIALS);

    /**
     * Null-iron: sluggish to mine with, but it outlasts netherite and hits harder than
     * anything else. The Sonic Lance is forged from it.
     */
    public static final ToolMaterial NULL_IRON = new ToolMaterial(
            INCORRECT_FOR_NULL_IRON_TOOL, 2600, 5.0F, 5.0F, 8, NULL_IRON_TOOL_MATERIALS);

    // -------------------------------------------------------- equipment assets

    /**
     * Names {@code assets/echoing_void/equipment/resonance.json}, which in turn points at
     * {@code textures/entity/equipment/humanoid/resonance.png} and the matching
     * {@code humanoid_leggings} layer.
     */
    public static final ResourceKey<EquipmentAsset> RESONANCE_ASSET =
            ResourceKey.create(EquipmentAssets.ROOT_ID, EchoingVoid.id("resonance"));

    /** Names {@code assets/echoing_void/equipment/aero_stride.json} (humanoid layer only). */
    public static final ResourceKey<EquipmentAsset> AERO_STRIDE_ASSET =
            ResourceKey.create(EquipmentAssets.ROOT_ID, EchoingVoid.id("aero_stride"));

    // --------------------------------------------------------- armour sets

    /**
     * Resonance Armour: a null-iron shell with bismuth resonators. Heavy protection and a
     * little knockback resistance, because the set is meant to be stood in and absorbed with
     * rather than dodged in.
     */
    public static final ArmorMaterial RESONANCE = new ArmorMaterial(
            34,
            Map.of(
                    ArmorType.HELMET, 3,
                    ArmorType.CHESTPLATE, 8,
                    ArmorType.LEGGINGS, 6,
                    ArmorType.BOOTS, 3),
            12,
            SoundEvents.ARMOR_EQUIP_NETHERITE,
            2.5F,
            0.05F,
            REPAIRS_RESONANCE,
            RESONANCE_ASSET);

    /**
     * Aero-Stride Greaves: worn on the feet. Very little armour value - the payoff is the
     * movement, not the mitigation - but it enchants extremely well.
     */
    public static final ArmorMaterial AERO_STRIDE = new ArmorMaterial(
            22,
            Map.of(
                    ArmorType.BOOTS, 3,
                    ArmorType.LEGGINGS, 5),
            24,
            SoundEvents.ARMOR_EQUIP_CHAIN,
            0.0F,
            0.0F,
            REPAIRS_AERO_STRIDE,
            AERO_STRIDE_ASSET);

    // ---------------------------------------------------------------- helpers

    private static TagKey<Block> blockTag(String path) {
        return TagKey.create(Registries.BLOCK, EchoingVoid.id(path));
    }

    private static TagKey<Item> itemTag(String path) {
        return TagKey.create(Registries.ITEM, EchoingVoid.id(path));
    }
}

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
 * Knell - the one material in the mod that sits above netherite.
 *
 * <p>Gameplay intent: netherite is the end of the vanilla ladder, so a tier above it has to be
 * earned somewhere netherite cannot take you. Knell is Hollow Horizon only, in the deepest
 * strata, behind a netherite pickaxe, and it is never crafted into gear directly - it is integrated
 * onto finished netherite gear at a Knell Integrator, exactly as netherite upgrades diamond.
 * That keeps the whole vanilla progression intact and makes this the last rung rather than a
 * parallel one.
 *
 * <p>Every number here is netherite's, moved by the amount {@code docs/spec/expansion.json}
 * specifies under {@code new_tier.gear.above_netherite}, and the vanilla side of each comparison was
 * read out of {@code ToolMaterial.NETHERITE} and {@code ArmorMaterials.NETHERITE} in the 26.2
 * sources rather than recalled:
 *
 * <table>
 *   <caption>Knell against netherite</caption>
 *   <tr><th>stat</th><th>netherite</th><th>knell</th><th>rule</th></tr>
 *   <tr><td>tool durability</td><td>2031</td><td>3250</td><td>x1.6</td></tr>
 *   <tr><td>attack bonus</td><td>4.0</td><td>5.5</td><td>+1.5</td></tr>
 *   <tr><td>armour durability</td><td>37</td><td>59</td><td>x1.6</td></tr>
 *   <tr><td>toughness</td><td>3.0</td><td>5.0</td><td>+2</td></tr>
 *   <tr><td>knockback resist</td><td>0.1</td><td>0.2</td><td>+0.1</td></tr>
 *   <tr><td>enchantability</td><td>15</td><td>18</td><td>"slightly above"</td></tr>
 * </table>
 *
 * <p>Two things the spec does not name are decided here. Mining speed goes 9.0 to 10.0, because a
 * tier that mines no faster than the one below it does not feel like an upgrade in the hand, and
 * one full step is what separates each vanilla tier. Armour <em>points</em> are deliberately left
 * at netherite's 3/8/6/3: a full netherite set already fills the armour bar, so the spec puts the
 * whole armour increment into toughness and knockback resistance instead, and adding points on top
 * of that would push the set past what the bar can show for no readable benefit.
 *
 * <p>As in {@link ModToolMaterials}, the tier gate and the repair ingredients are tags. The JSON
 * lives in the datapack ({@code tools/gen_knell_data.py}); only the keys are declared here.
 */
public final class KnellMaterials {
    private KnellMaterials() {}

    // ------------------------------------------------------------ tier gate

    /**
     * Blocks a knell tool cannot harvest. Deliberately empty - knell is the top of the
     * ladder, so there is nothing left for it to fail at. The tag file still has to exist, because
     * {@link ToolMaterial} resolves it during item registration.
     */
    public static final TagKey<Block> INCORRECT_FOR_KNELL_TOOL = blockTag("incorrect_for_knell_tool");

    // ------------------------------------------------------ repair ingredients

    public static final TagKey<Item> KNELL_TOOL_MATERIALS = itemTag("knell_tool_materials");
    public static final TagKey<Item> REPAIRS_RESONANT_ARMOR = itemTag("repairs_resonant_armor");

    // ----------------------------------------------------------- the alloy

    /**
     * Netherite's profile with the spec's multipliers applied. The high durability is what the
     * player actually feels: an integrated tool is meant to be the last one they ever make, so it
     * outlasts a netherite tool by more than half again.
     */
    public static final ToolMaterial KNELL = new ToolMaterial(
            INCORRECT_FOR_KNELL_TOOL, 3250, 10.0F, 5.5F, 18, KNELL_TOOL_MATERIALS);

    // -------------------------------------------------------- equipment asset

    /**
     * Names {@code assets/echoing_void/equipment/knell.json}, which points at the worn layers
     * under {@code textures/entity/equipment/humanoid/knell.png} and its leggings and baby
     * companions.
     */
    /**
     * The Aeroshell's own worn-armour asset.
     *
     * <p>Identical to {@link #RESONANT_ASSET} in every layer a chestplate uses - it points at the
     * same {@code echoing_void:knell} sheet, so an Aeroshell looks like the Knell chestplate it was
     * made from - and adds a {@code wings} layer, which is what actually draws the elytra. That
     * layer is the whole reason a second asset exists: an equipment asset is where 26.2 declares
     * which layers an item renders, and a chestplate that glides but has no wings layer flies
     * invisibly.
     */
    public static final ResourceKey<EquipmentAsset> AEROSHELL_ASSET =
            ResourceKey.create(EquipmentAssets.ROOT_ID, EchoingVoid.id("knell_aeroshell"));

    public static final ResourceKey<EquipmentAsset> RESONANT_ASSET =
            ResourceKey.create(EquipmentAssets.ROOT_ID, EchoingVoid.id("knell"));

    // ------------------------------------------------------------- the armour

    /**
     * Resonant armour. The extra two points of toughness are the headline: toughness reduces the
     * bite big hits take out of the armour bar, so the set holds up against exactly the damage
     * spikes a netherite set stops being enough for. The extra knockback resistance is what lets a
     * player stand their ground against the Strata Golem's slam rather than being thrown off an
     * island by it.
     */
    public static final ArmorMaterial RESONANT = new ArmorMaterial(
            59,
            Map.of(
                    ArmorType.HELMET, 3,
                    ArmorType.CHESTPLATE, 8,
                    ArmorType.LEGGINGS, 6,
                    ArmorType.BOOTS, 3,
                    ArmorType.BODY, 19),
            18,
            SoundEvents.ARMOR_EQUIP_NETHERITE,
            5.0F,
            0.2F,
            REPAIRS_RESONANT_ARMOR,
            RESONANT_ASSET);

    /**
     * The Aeroshell's material: {@link #RESONANT} to the last digit, pointed at
     * {@link #AEROSHELL_ASSET}.
     *
     * <p>A copy exists only because an {@code ArmorMaterial} carries its equipment asset as a
     * field, so there is no way to keep one material and vary the asset per item. Every protection
     * figure, the toughness, the knockback resistance and the repair tag are deliberately the same:
     * an Aeroshell is a Knell chestplate that flies, not a different chestplate, and a player
     * trading protection for flight would have been a different feature from the one asked for.
     */
    public static final ArmorMaterial RESONANT_AERO = new ArmorMaterial(
            59,
            Map.of(
                    ArmorType.HELMET, 3,
                    ArmorType.CHESTPLATE, 8,
                    ArmorType.LEGGINGS, 6,
                    ArmorType.BOOTS, 3,
                    ArmorType.BODY, 19),
            18,
            SoundEvents.ARMOR_EQUIP_NETHERITE,
            5.0F,
            0.2F,
            REPAIRS_RESONANT_ARMOR,
            AEROSHELL_ASSET);

    // ---------------------------------------------------------------- helpers

    private static TagKey<Block> blockTag(String path) {
        return TagKey.create(Registries.BLOCK, EchoingVoid.id(path));
    }

    private static TagKey<Item> itemTag(String path) {
        return TagKey.create(Registries.ITEM, EchoingVoid.id(path));
    }
}

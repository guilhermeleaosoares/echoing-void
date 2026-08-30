"""
The Echoing Void - block and item tag generator.

Tags carry real mechanics in 26.2, not just bookkeeping:

  * mining tool and tier are expressed ONLY through tags. There is no Java API
    for harvest tool or harvest level any more - code contributes just
    `.requiresCorrectToolForDrops()` and the tags decide the rest.
  * a ToolMaterial's `incorrectBlocksForDrops` and a material's `repairItems` /
    `repairIngredient` are TagKeys. Without the tag file, repair silently matches
    nothing and the tier gate silently lets everything through.

Tier gating used here:
  diamond-tier blocks   -> minecraft:needs_diamond_tool
  netherite-tier blocks -> needs_diamond_tool AND incorrect_for_diamond_tool,
                           which leaves netherite as the only tool that works
                           (vanilla has no needs_netherite_tool tag)

Directory names are SINGULAR in 26.2: tags/block/, tags/item/.

Run:  python tools/gen_tags.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "main" / "resources" / "data"

written: list[str] = []


def tag(namespace: str, kind: str, name: str, values: list[str], replace: bool = False) -> None:
    path = DATA / namespace / "tags" / kind / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"replace": replace, "values": values}, indent=2) + "\n",
                    encoding="utf-8")
    written.append(str(path.relative_to(DATA)).replace("\\", "/"))


def b(name: str) -> str:
    return f"{NS}:{name}"


# ---------------------------------------------------------------------------

PICKAXE = [
    "resonant_bismuth_ore", "deepslate_resonant_bismuth_ore", "raw_phonolite",
    "phonolite_bricks", "null_iron_ore", "null_iron_block", "frequency_siphon",
    "inversion_anvil",
    "null_iron_jukebox",
    "tuners_mask",
]
AXE = ["petrified_tuning_wood", "stripped_petrified_tuning_wood"]
HOE = ["calcified_resonance_leaves"]
DIAMOND_TIER = [
    "resonant_bismuth_ore", "deepslate_resonant_bismuth_ore", "raw_phonolite",
    "phonolite_bricks", "inversion_anvil", "null_iron_ore", "null_iron_block",
    "tuners_mask",
]
IRON_TIER = ["frequency_siphon", "petrified_tuning_wood", "stripped_petrified_tuning_wood"]
# Same figures as null_iron_block (see ModBlocks.TUNERS_MASK) - same tool floor too.
NETHERITE_ONLY = ["null_iron_ore", "null_iron_block", "tuners_mask"]


def main() -> int:
    # ---- vanilla block tags: tool class and tier -------------------------
    tag("minecraft", "block", "mineable/pickaxe", [b(x) for x in PICKAXE])
    tag("minecraft", "block", "mineable/axe", [b(x) for x in AXE])
    tag("minecraft", "block", "mineable/hoe", [b(x) for x in HOE])
    tag("minecraft", "block", "needs_diamond_tool", [b(x) for x in DIAMOND_TIER])
    tag("minecraft", "block", "needs_iron_tool", [b(x) for x in IRON_TIER])
    # Null-Iron demands netherite: diamond is explicitly wrong for it, and
    # everything below diamond is already excluded by needs_diamond_tool.
    tag("minecraft", "block", "incorrect_for_diamond_tool", [b(x) for x in NETHERITE_ONLY])

    # ---- vanilla behaviour tags ------------------------------------------
    tag("minecraft", "block", "leaves", [b("calcified_resonance_leaves")])
    tag("minecraft", "block", "logs", [b(x) for x in AXE])

    # ---- our own block tags ----------------------------------------------
    tag(NS, "block", "phonolite_ore_replaceables", [b("raw_phonolite")])

    # blocks each of our tool materials CANNOT harvest, expressed by deferring
    # to the vanilla tier tags so we inherit future vanilla changes for free
    tag(NS, "block", "incorrect_for_bismuth_tool", ["#minecraft:incorrect_for_diamond_tool"])
    tag(NS, "block", "incorrect_for_void_glass_tool", ["#minecraft:incorrect_for_iron_tool"])
    tag(NS, "block", "incorrect_for_null_iron_tool", ["#minecraft:incorrect_for_netherite_tool"])

    # ---- item tags: what repairs what ------------------------------------
    tag(NS, "item", "bismuth_tool_materials", [b("resonance_shard")])
    tag(NS, "item", "void_glass_tool_materials", [b("void_glass_shard")])
    tag(NS, "item", "null_iron_tool_materials", [b("null_iron_ingot")])
    tag(NS, "item", "repairs_resonance", [b("null_iron_ingot"), b("resonance_shard")])
    tag(NS, "item", "repairs_aero_stride", [b("void_glass_shard"), b("resonance_shard")])

    # ---- armour slots, which is also what makes trims work ----------------
    # minecraft:trimmable_armor is the union of these four (verified against
    # the 26.2 tag files), so joining the slot tags is what lets a smithing
    # table put a trim on our armour - there is nothing else to declare, and
    # the trim sprites come from vanilla's own armor_trims atlas.
    tag("minecraft", "item", "head_armor",
        [b("resonance_helmet"), b("knell_helmet")])
    # PLAYER: "knell aeroshell should be able to take all chestplate enchantments. so
    # unbreaking, mending, protection."
    #
    # It could take NONE. Enchantability in 26.2 runs through these vanilla class tags -
    # #chest_armor is the only route into #enchantable/chest_armor (Protection, Blast
    # Protection, Thorns) and into #enchantable/durability (Unbreaking, Mending) - and the
    # Aeroshell was registered without being added to any of them. Exactly the bug the
    # Aero-Stride Greaves had when they sat in leg_armor instead of foot_armor: healthy
    # material, healthy enchantment value, and not one enchantment would apply.
    tag("minecraft", "item", "chest_armor",
        [b("resonance_chestplate"), b("knell_chestplate"), b("knell_aeroshell")])
    tag("minecraft", "item", "leg_armor",
        [b("resonance_leggings"), b("knell_leggings")])
    # The Aero-Stride Greaves are BOOTS, whatever the name suggests: ModItems
    # builds them with ArmorType.BOOTS, and AeroStrideGreavesItem.isWorn asks
    # for EquipmentSlot.FEET. They were listed under leg_armor, which put them
    # in the wrong enchantable class - #minecraft:foot_armor is the only route
    # into enchantable/foot_armor, and that gates Feather Falling, Depth
    # Strider, Frost Walker and Soul Speed. A boot whose entire purpose is
    # cancelling fall damage could not take Feather Falling. Found by an armour
    # stand refusing to equip them: "No targets accepted item into slot 101".
    tag("minecraft", "item", "foot_armor",
        [b("resonance_boots"), b("knell_boots"), b("aero_stride_greaves")])

    # ---- what farm animals will stand on -----------------------------------
    #
    # PLAYER: "do the new passive mobs spawn naturally? where and with what
    # frequency". The biome spawner entries and the SpawnPlacementRegisterEvent
    # registration were both in place and both INERT, because
    # Animal.checkAnimalSpawnRules ends in:
    #
    #     level.getBlockState(pos.below()).is(BlockTags.ANIMALS_SPAWNABLE_ON)
    #
    # and vanilla's animals_spawnable_on contains exactly one entry:
    # minecraft:grass_block. There is not one grass block in the Hollow
    # Horizon, so no auroch or boar could ever have spawned naturally however
    # good the weights looked.
    #
    # Adding this dimension's own ground to the vanilla tag is the fix, and it
    # is additive (replace: false), so the Overworld keeps grass and nothing
    # vanilla changes. The set is #hollow_horizon_natural_ground, which already
    # names exactly the surfaces a player walks on here.
    tag("minecraft", "block", "animals_spawnable_on",
        [f"#{NS}:hollow_horizon_natural_ground"])

    # ---- what a gourd will REST on, as against what a stem GROWS from ------
    #
    # PLAYER: "does the echo gourd grow on normal moss or only tilled? i dont mean the
    # seeds, the plant grows fine, im talking about the block fruit?"
    #
    # Only tilled, and that was an accident. Vanilla StemBlock takes TWO tags -
    # stemSupportBlocks and fruitSupportBlocks - and melon passes different ones for
    # each: #supports_crops (farmland alone) for the stem, and #supports_stem_fruit ->
    # #supports_vegetation (dirt, grass, podzol, moss, mud) for the fruit. That is why a
    # real melon farm has the stems on a tilled row and the melons landing on plain
    # ground either side.
    #
    # ModCrops passed VOID_SOIL into BOTH slots, so the gourd demanded tilled soil where
    # a melon does not. This tag is the second half of that pair: the stem still insists
    # on void farmland beneath itself, and the fruit will now settle on bare Resonance
    # Moss the way a melon settles on grass.
    tag(NS, "block", "void_stem_fruit_soil",
        [b("void_farmland"), b("resonance_moss")])

    # ---- tool and weapon classes, which is what makes ENCHANTING work ------
    #
    # PLAYER: "make sure all enchantments work as normal in all the new armors
    # tools and weapons." The armour above was already fine. Every tool and
    # weapon in the mod was NOT: not one of them appeared in a single vanilla
    # item tag, so none of them could take a single enchantment.
    #
    # Enchantability in 26.2 is tag-driven, and the chain runs through these
    # class tags rather than through the item's material or its enchantment
    # value (ours are all healthy - 22 bismuth, 26 void-glass, 18 knell, 8
    # null-iron). Checked against the 26.2 tag files:
    #
    #   enchantable/mining      -> #axes #pickaxes #shovels #hoes    (Efficiency,
    #                                                                Fortune, Silk Touch)
    #   enchantable/melee_weapon-> #swords #spears
    #   enchantable/sharp_weapon-> #enchantable/melee_weapon #axes   (Sharpness, Looting...)
    #   enchantable/weapon      -> #enchantable/sharp_weapon
    #   enchantable/durability  -> #swords #axes #pickaxes #shovels #hoes,
    #                              plus the four armour slots               (Unbreaking, Mending)
    #
    # So membership here is the whole fix - nothing needs an
    # echoing_void:enchantable/* tag of its own, and shipping one would not
    # have helped, because the enchantments' own supported_items point at
    # these vanilla class tags.
    #
    # The Rapier and the Lance are built with Item.Properties.sword(...) in
    # ModItems, so they are swords mechanically and belong in #swords with the
    # rest - a spear-flavoured lance that cannot take Unbreaking would be the
    # same bug wearing a different name.
    tag("minecraft", "item", "swords",
        [b("harmonic_sword"), b("knell_sword"),
         b("void_glass_rapier"), b("sonic_lance")])
    tag("minecraft", "item", "pickaxes",
        [b("harmonic_pickaxe"), b("knell_pickaxe")])
    tag("minecraft", "item", "axes",
        [b("harmonic_axe"), b("knell_axe")])
    tag("minecraft", "item", "shovels",
        [b("harmonic_shovel"), b("knell_shovel")])
    tag("minecraft", "item", "hoes",
        [b("harmonic_hoe"), b("knell_hoe")])

    print(f"generated {len(written)} tag files")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
The Echoing Void - every JSON the Knell tier needs.

Blockstates, block and item models, item model definitions, the equipment asset,
loot tables, block and item tags, recipes, and the advancement tab. Companion to
tools/gen_models.py, gen_loot_tables.py, gen_tags.py, gen_recipes.py and
gen_recipe_advancements.py, which own the earlier rounds; this script only ever
writes files belonging to the knell tier, so the set can be regenerated
without touching anything else.

  RUN ORDER: this script MERGES into the shared vanilla tag files and into
  lang/en_us.json rather than overwriting them, exactly as gen_terrain_tags.py
  does. Merging makes it idempotent and safe to re-run, but it cannot recover
  entries a whole-file writer has already stomped. Run gen_tags.py before this,
  never after.

Schemas were read out of the real 26.2 client jar rather than recalled:

  * integration recipes are echoing_void:integration with "template", "base",
    "addition" and "result" - the field names have NOT changed in 26.2, verified
    against data/minecraft/recipe/netherite_pickaxe_smithing.json, and the
    result is still an object of the {"id": ...} form
  * item model definitions live in assets/<ns>/items/<id>.json and wrap the
    model as {"model": {"type": "minecraft:model", "model": "..."}}
  * datapack directories are SINGULAR: loot_table/, recipe/, tags/block/,
    tags/item/, advancement/
  * advancement item predicates take an id, a #tag, or a list of ids
    (data/minecraft/advancement/adventure/lighten_up.json)

THE INTEGRATOR MODEL is authored here with explicit elements rather than a
cube_all, because the spec asks for something that reads as more advanced than
an anvil. Every face carries an explicit uv rectangle: the side sprite is an
atlas of horizontal zones (deck rim, chassis flank, corner cable) and leaving
the uv to be derived from element bounds would sample the wrong zone for at
least one element. The rectangles here match tools/gen_knell_textures.py's
layout, and the java VoxelShape in KnellIntegratorBlock matches the boxes.

Run:  python tools/gen_knell_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src" / "main" / "resources"
ASSETS = RES / "assets" / NS
DATA = RES / "data"

BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_MODELS = ASSETS / "models" / "item"
ITEM_DEFS = ASSETS / "items"
EQUIPMENT = ASSETS / "equipment"
LANG = ASSETS / "lang" / "en_us.json"

LOOT = DATA / NS / "loot_table"
RECIPE = DATA / NS / "recipe"
ADVANCEMENT = DATA / NS / "advancement"

written: list[str] = []
merged: list[str] = []


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(RES)).replace("\\", "/"))


# ===========================================================================
# The set
# ===========================================================================

BLOCKS = ["knell_ore", "knell_block", "knell_integrator"]

MATERIALS = ["raw_knell", "knell_ingot", "knell_template",
             # The elytra template is a material rather than gear: it is consumed by
             # an integration, exactly as knell_template is, and never worn.
             "knell_elytra_template"]

#: The five tools, then the four armour pieces. Order matters: it is the order
#: the smithing recipes, the advancement icons and the lang file all follow.
TOOLS = ["sword", "pickaxe", "axe", "shovel", "hoe"]
ARMOUR = ["helmet", "chestplate", "leggings", "boots"]
GEAR = [f"knell_{p}" for p in TOOLS + ARMOUR] + ["knell_aeroshell"]

NAMES = {
    "knell_ore": "Knell Ore",
    "knell_block": "Block of Knell",
    "knell_integrator": "Knell Integrator",
    "raw_knell": "Raw Knell",
    "knell_ingot": "Knell Ingot",
    "knell_template": "Knell Template",
    "knell_elytra_template": "Knell Elytra Template",
    "knell_aeroshell": "Knell Aeroshell",
    "knell_sword": "Knell Sword",
    "knell_pickaxe": "Knell Pickaxe",
    "knell_axe": "Knell Axe",
    "knell_shovel": "Knell Shovel",
    "knell_hoe": "Knell Hoe",
    "knell_helmet": "Knell Helmet",
    "knell_chestplate": "Knell Chestplate",
    "knell_leggings": "Knell Leggings",
    "knell_boots": "Knell Boots",
}


def item(name: str) -> str:
    return f"{NS}:{name}"


# ===========================================================================
# Models, blockstates and item definitions
# ===========================================================================

def cube_all(block: str) -> None:
    write(BLOCK_MODELS / f"{block}.json", {
        "parent": "minecraft:block/cube_all",
        "textures": {"all": f"{NS}:block/{block}"},
    })


def simple_state(block: str) -> None:
    write(BLOCKSTATES / f"{block}.json",
          {"variants": {"": {"model": f"{NS}:block/{block}"}}})


def block_item_def(name: str) -> None:
    write(ITEM_DEFS / f"{name}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:block/{name}"}})


def flat_item(name: str, parent: str = "minecraft:item/generated") -> None:
    write(ITEM_MODELS / f"{name}.json",
          {"parent": parent, "textures": {"layer0": f"{NS}:item/{name}"}})
    write(ITEM_DEFS / f"{name}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:item/{name}"}})


def face(texture: str, uv: list[int], cullface: str | None = None) -> dict:
    out: dict = {"uv": uv, "texture": texture}
    if cullface:
        out["cullface"] = cullface
    return out


def integrator_model() -> None:
    """A squat machine, not a cube.

    Reading bottom to top: four corner cable conduits, a chassis on top of them,
    a deck, and a bismuth resonator hoop standing proud with an emitter inside
    it. The boxes are the same seven the block's VoxelShape is built from, so
    what the player sees and what they collide with agree.
    """
    elements: list[dict] = []

    # 1. the chassis
    elements.append({
        "from": [2, 0, 2],
        "to": [14, 10, 14],
        "faces": {
            "down": face("#bottom", [2, 2, 14, 14], "down"),
            "up": face("#top", [2, 2, 14, 14]),
            "north": face("#side", [2, 6, 14, 16]),
            "south": face("#side", [2, 6, 14, 16]),
            "west": face("#side", [2, 6, 14, 16]),
            "east": face("#side", [2, 6, 14, 16]),
        },
    })

    # 2. the deck. No down face: it is flush against the chassis top.
    elements.append({
        "from": [3, 10, 3],
        "to": [13, 12, 13],
        "faces": {
            "up": face("#top", [3, 3, 13, 13]),
            "north": face("#side", [3, 4, 13, 6]),
            "south": face("#side", [3, 4, 13, 6]),
            "west": face("#side", [3, 4, 13, 6]),
            "east": face("#side", [3, 4, 13, 6]),
        },
    })

    # 3. the four corner conduits. Kept outside the chassis footprint rather
    # than sunk into it - overlapping boxes z-fight.
    for x0, z0 in ((0, 0), (14, 0), (0, 14), (14, 14)):
        elements.append({
            "from": [x0, 0, z0],
            "to": [x0 + 2, 9, z0 + 2],
            "faces": {
                "down": face("#side", [0, 0, 2, 2], "down"),
                "up": face("#side", [0, 0, 2, 2]),
                "north": face("#side", [0, 7, 2, 16]),
                "south": face("#side", [0, 7, 2, 16]),
                "west": face("#side", [0, 7, 2, 16]),
                "east": face("#side", [0, 7, 2, 16]),
            },
        })

    # 4. the resonator hoop: four one-pixel bars enclosing a 6x6 well.
    # The ring sprite is banded horizontally, so rows 1..3 are the bright cyan
    # a vertical bar wants and row 4 is the duller tone a top edge wants.
    long_side = face("#ring", [4, 1, 12, 4])
    long_top = face("#ring", [4, 4, 12, 5])
    end_cap = face("#ring", [0, 1, 1, 4])
    for x0, z0, x1, z1 in ((4, 4, 12, 5), (4, 11, 12, 12)):
        elements.append({
            "from": [x0, 12, z0],
            "to": [x1, 15, z1],
            "faces": {
                "down": long_top, "up": long_top,
                "north": long_side, "south": long_side,
                "west": end_cap, "east": end_cap,
            },
        })

    side_face = face("#ring", [5, 1, 11, 4])
    side_top = face("#ring", [0, 4, 1, 10])
    for x0, x1 in ((4, 5), (11, 12)):
        elements.append({
            "from": [x0, 12, 5],
            "to": [x1, 15, 11],
            "faces": {
                "down": side_top, "up": side_top,
                "west": side_face, "east": side_face,
                "north": end_cap, "south": end_cap,
            },
        })

    # 5. the emitter in the well, one pixel shy of the hoop's top so the hoop
    # visibly encircles something. shade:false so it reads as lit rather than as
    # one more piece of metal, which is the only cue that the hoop does work.
    emitter_side = face("#ring", [6, 2, 10, 4])
    elements.append({
        "from": [6, 12, 6],
        "to": [10, 14, 10],
        "shade": False,
        "faces": {
            "up": face("#ring", [6, 6, 10, 10]),
            "north": emitter_side, "south": emitter_side,
            "west": emitter_side, "east": emitter_side,
        },
    })

    write(BLOCK_MODELS / "knell_integrator.json", {
        "parent": "minecraft:block/block",
        "textures": {
            "particle": f"{NS}:block/knell_integrator_side",
            "side": f"{NS}:block/knell_integrator_side",
            "top": f"{NS}:block/knell_integrator_top",
            "bottom": f"{NS}:block/knell_integrator_bottom",
            "ring": f"{NS}:block/knell_integrator_ring",
        },
        "elements": elements,
    })


def gen_models() -> None:
    for block in ("knell_ore", "knell_block"):
        cube_all(block)
        simple_state(block)
        block_item_def(block)

    integrator_model()
    simple_state("knell_integrator")
    block_item_def("knell_integrator")

    for name in MATERIALS:
        flat_item(name)
    for piece in TOOLS:
        flat_item(f"knell_{piece}", parent="minecraft:item/handheld")
    for piece in ARMOUR:
        flat_item(f"knell_{piece}")
    flat_item("knell_elytra_template")
    flat_item("knell_aeroshell")


def gen_equipment_asset() -> None:
    """The worn-armour layers. Three of them, because 26.2 renders leggings from
    their own layer and baby mobs from theirs."""
    write(EQUIPMENT / "knell.json", {
        "layers": {
            "humanoid": [{"texture": f"{NS}:knell"}],
            "humanoid_baby": [{"texture": f"{NS}:knell"}],
            "humanoid_leggings": [{"texture": f"{NS}:knell"}],
        }
    })

    # The Aeroshell wears the same plate as the chestplate it was made from - same
    # humanoid sheet, deliberately - and adds the one layer that actually draws the
    # elytra. An equipment asset is where 26.2 declares which layers an item renders,
    # so a chestplate that carries DataComponents.GLIDER but has no `wings` layer
    # flies perfectly well and shows nothing on the player's back.
    #
    # No humanoid_leggings entry: this is a chest piece and that layer would never be
    # consulted. Vanilla's own elytra.json declares `wings` alone for the same reason.
    write(EQUIPMENT / "knell_aeroshell.json", {
        "layers": {
            "humanoid": [{"texture": f"{NS}:knell"}],
            "humanoid_baby": [{"texture": f"{NS}:knell"}],
            # PLAYER: "replace your custom wing assets for the default elytra assets."
            # minecraft:elytra with use_player_texture, byte for byte what vanilla's own
            # elytra.json declares - so a player's cape shows through on the Aeroshell
            # exactly as it does on an elytra, which a bespoke sheet could never do.
            "wings": [{"texture": "minecraft:elytra", "use_player_texture": True}],
        }
    })


# ===========================================================================
# Loot tables
#
# Fragments are byte-identical to the ones in gen_loot_tables.py and
# gen_terrain_loot.py, which were lifted from the real 26.2 vanilla tables.
# ===========================================================================

SILK_TOUCH = {
    "condition": "minecraft:match_tool",
    "predicate": {
        "predicates": {
            "minecraft:enchantments": [
                {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}
            ]
        }
    },
}
SURVIVES = {"condition": "minecraft:survives_explosion"}
DECAY = {"function": "minecraft:explosion_decay"}
ORE_FORTUNE = {
    "function": "minecraft:apply_bonus",
    "enchantment": "minecraft:fortune",
    "formula": "minecraft:ore_drops",
}


def block_table(block: str, pools: list[dict]) -> dict:
    return {"type": "minecraft:block", "pools": pools,
            "random_sequence": f"{NS}:blocks/{block}"}


def self_drop(block: str) -> None:
    write(LOOT / "blocks" / f"{block}.json", block_table(block, [{
        "rolls": 1.0,
        "conditions": [SURVIVES],
        "entries": [{"type": "minecraft:item", "name": item(block)}],
    }]))


def ore_table(block: str, drop: str) -> None:
    """Silk touch keeps the ore block; anything else yields the raw material,
    with the standard fortune curve every vanilla ore uses."""
    write(LOOT / "blocks" / f"{block}.json", block_table(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:alternatives",
            "children": [
                {"type": "minecraft:item", "name": item(block),
                 "conditions": [SILK_TOUCH]},
                {"type": "minecraft:item", "name": item(drop),
                 "functions": [ORE_FORTUNE, DECAY]},
            ],
        }],
    }]))


def gen_loot() -> None:
    ore_table("knell_ore", "raw_knell")
    self_drop("knell_block")
    self_drop("knell_integrator")


# ===========================================================================
# Tags
# ===========================================================================

def merge_tag(namespace: str, kind: str, name: str, values: list[str]) -> None:
    """Union `values` into a tag file, preserving anything already there."""
    path = DATA / namespace / "tags" / kind / f"{name}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        existing = list(data.get("values", []))
        replace = bool(data.get("replace", False))
        merged.append(f"{namespace}:{kind}/{name}")
    else:
        existing, replace = [], False
        written.append(str(path.relative_to(RES)).replace("\\", "/"))

    for value in values:
        if value not in existing:
            existing.append(value)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"replace": replace, "values": existing}, indent=2) + "\n",
                    encoding="utf-8")


def gen_tags() -> None:
    ore, storage, station = BLOCKS

    # Tool class. Everything in this tier is mined with a pickaxe.
    merge_tag("minecraft", "block", "mineable/pickaxe", [item(b) for b in BLOCKS])

    # Tier. There is no needs_netherite_tool tag in 26.2 - netherite gating is
    # expressed by putting a block in BOTH needs_diamond_tool, which vanilla
    # folds into the iron/stone/copper/gold/wood incorrect_for tags, AND
    # incorrect_for_diamond_tool, which is otherwise empty. That combination is
    # what leaves only netherite (and this mod's own top-tier alloys) able to
    # drop it, and it is exactly how null_iron_ore is already gated.
    merge_tag("minecraft", "block", "needs_diamond_tool", [item(b) for b in BLOCKS])
    merge_tag("minecraft", "block", "incorrect_for_diamond_tool", [item(ore), item(storage)])

    # The station is deliberately NOT in incorrect_for_diamond_tool: a player
    # who has built one should be able to pick it up and move it with the
    # pickaxe they already carry.
    assert item(station) not in (item(ore), item(storage))

    # Knell is the top of the ladder, so nothing is incorrect for it. The
    # file still has to exist - ToolMaterial resolves the tag during item
    # registration and a missing tag is a hard failure there, not a warning.
    merge_tag(NS, "block", "incorrect_for_knell_tool", [])

    merge_tag(NS, "item", "knell_tool_materials", [item("knell_ingot")])
    merge_tag(NS, "item", "repairs_resonant_armor", [item("knell_ingot")])

    # Named as a set so the advancement can ask "any resonant piece" in one
    # predicate instead of nine alternative criteria.
    merge_tag(NS, "item", "knell_gear", [item(g) for g in GEAR])


# ===========================================================================
# Recipes
# ===========================================================================

def cooking(name: str, kind: str, ingredient: str, result: str,
            xp: float, time: int, group: str) -> None:
    write(RECIPE / f"{name}.json", {
        "type": f"minecraft:{kind}",
        "category": "misc",
        "cookingtime": time,
        "experience": xp,
        "group": group,
        "ingredient": ingredient,
        "result": {"id": result},
    })


def shaped(name: str, pattern: list[str], key: dict, result: str,
           count: int = 1, category: str = "misc") -> None:
    data: dict = {
        "type": "minecraft:crafting_shaped",
        "category": category,
        "key": key,
        "pattern": pattern,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    write(RECIPE / f"{name}.json", data)


def shapeless(name: str, ingredients: list[str], result: str, count: int = 1,
              category: str = "misc") -> None:
    data: dict = {
        "type": "minecraft:crafting_shapeless",
        "category": category,
        "ingredients": ingredients,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    write(RECIPE / f"{name}.json", data)


# The Resonance piece each Knell piece is integrated onto. The ladder is
# RESONANCE -> KNELL and does not pass through netherite at all:
#
#   PLAYER: "instead of going from netherite to knell, you go from resonance to
#   knell. no need for a template for resonance, but you need knell templates to
#   integrate the resonance armor with knell."
#
# That shape is also the better one - it makes the mod's own mid-tier the
# mandatory stepping stone rather than an optional detour, so a player who
# ignores Resonance cannot reach Knell and nothing built on the way is wasted.
#
# The pickaxe is the one asymmetry: Resonance has no plain pickaxe because the
# Harmonic Pickaxe already fills that slot on the same material, so the Knell
# pickaxe is integrated onto it and its rhythm mechanic is what gets upgraded.
RESONANCE_BASE = {
    "sword": "harmonic_sword",
    "pickaxe": "harmonic_pickaxe",
    "axe": "harmonic_axe",
    "shovel": "harmonic_shovel",
    "hoe": "harmonic_hoe",
    "helmet": "resonance_helmet",
    "chestplate": "resonance_chestplate",
    "leggings": "resonance_leggings",
    "boots": "resonance_boots",
}


def smithing(piece: str) -> None:
    """One integration: Resonance piece + Knell Ingot + Knell Template.

    Field order and shape are vanilla's netherite upgrade, which is the point -
    the recipe book renders it in the same three slots and the player reads it
    without being taught anything new. Only the base differs, and that is the
    whole design: the thing being upgraded is our own mid-tier gear.

    THE TYPE IS NOT VANILLA'S, and that is the one thing here that matters.

    PLAYER: "the smithing table should be unable to make knell tools with the
    knell template, which it currently can, as this defeats the purpose of
    making the knell integrator."

    These were minecraft:smithing_transform, and a recipe's TYPE is what decides
    which station may run it - SmithingMenu.createResult asks for every recipe of
    RecipeType.SMITHING and never checks which block the menu was opened over. So
    every smithing table in the world could perform them and the Integrator, the
    station that is meant to gate the whole tier, was a decoration you could skip.

    Nothing hides a recipe from a menu that queries by type, so they have a type
    of their own now: echoing_void:integration, read only by IntegratorMenu. The
    schema is byte-for-byte identical - IntegrationRecipe reuses
    SmithingTransformRecipe's codecs verbatim - because behaving differently from
    a smithing upgrade was never the goal. Being performable somewhere else was.
    """
    write(RECIPE / f"knell_{piece}_smithing.json", {
        "type": f"{NS}:integration",
        "addition": item("knell_ingot"),
        "base": item(RESONANCE_BASE[piece]),
        "result": {"id": item(f"knell_{piece}")},
        "template": item("knell_template"),
    })


def gen_recipes() -> None:
    ingot = item("knell_ingot")
    raw = item("raw_knell")
    shard = item("resonance_shard")
    null_iron = item("null_iron_ingot")

    # Slow and hot, matching the null-iron smelt: knell resists the furnace.
    cooking("knell_ingot_from_smelting", "smelting", raw, ingot, 2.0, 400, "knell_ingot")
    cooking("knell_ingot_from_blasting", "blasting", raw, ingot, 2.0, 200, "knell_ingot")

    shaped("knell_block", ["###", "###", "###"], {"#": ingot},
           item("knell_block"), category="building")
    shapeless("knell_ingot_from_block", [item("knell_block")], ingot, 9)

    # The template is craftable rather than structure loot. The tier is already
    # gated by the dimension and by the ore's rarity; hiding a second mandatory
    # key inside a structure would make the whole ladder hostage to worldgen.
    shaped("knell_template", [" S ", "SNS", " S "],
           {"S": shard, "N": null_iron}, item("knell_template"), count=2)

    # ---- the elytra template, and why it is not made of the same stuff ------
    #
    # PLAYER: "i want an elytra template, that makes, only the knell chestplate, be
    # able to integrate with an elytra. this would require an especially crafted
    # template that is crafted using knell rather than null iron and resonance
    # shards, so it is harder to obtain but gives players a reason to seek knell
    # sets."
    #
    # Same silhouette as the ordinary template so it reads as one, but every
    # material is a tier up: four KNELL INGOTS where that recipe uses resonance
    # shards, around a phantom membrane rather than a null-iron ingot. Knell is the
    # rarest ore in the mod - bottom-biased, raw phonolite only, three blocks a vein
    # - so four ingots is a real expedition rather than a shopping trip.
    #
    # And it yields ONE, where knell_template yields two. A player who wants to fly
    # pays four knell ingots per pair of wings, every time.
    shaped("knell_elytra_template", [" K ", "KMK", " K "],
           {"K": ingot, "M": "minecraft:phantom_membrane"},
           item("knell_elytra_template"), count=1)

    # ---- the integration itself --------------------------------------------
    #
    # ONLY the knell chestplate, as asked - the base is that item and nothing else,
    # so a resonance chestplate, a netherite one or a bare elytra all leave the
    # result slot empty. And it is an echoing_void:integration recipe like every
    # other upgrade here, so it happens at the Integrator or not at all.
    #
    # IntegrationRecipe.assemble keeps the base's components, which matters more here
    # than anywhere else in this file: the chestplate you feed in carries its
    # enchantments, its name, its trim and whatever charge it had banked, and all of
    # that survives into the Aeroshell.
    write(RECIPE / "knell_aeroshell_integration.json", {
        "type": f"{NS}:integration",
        "addition": "minecraft:elytra",
        "base": item("knell_chestplate"),
        "result": {"id": item("knell_aeroshell")},
        "template": item("knell_elytra_template"),
    })

    # The station itself. It costs one knell ingot, so the order of
    # operations is find the ore, smelt one ingot, build the machine, then
    # spend the rest of the ore on gear.
    # The knell ingot is listed first in the key deliberately.
    # gen_recipe_advancements.py derives a recipe's unlock item as the first of
    # ours it finds while walking `key` in insertion order, so putting the ingot
    # there makes that script derive the same unlock this file writes below, and
    # the two generators stay byte-identical whichever runs last.
    shaped("knell_integrator", ["BRB", "NTN", "NNN"],
           {"R": ingot, "B": shard, "N": null_iron, "T": "minecraft:smithing_table"},
           item("knell_integrator"))

    for piece in TOOLS + ARMOUR:
        smithing(piece)


# ===========================================================================
# Advancements
#
# Two kinds. The recipe-unlock advancements are what put a recipe in the recipe
# book at all - without one the recipe exists and works but never appears - and
# they are written here in the exact shape gen_recipe_advancements.py derives,
# so whichever runs last produces the same bytes. The four display advancements
# are the tier's own small tab.
# ===========================================================================

RECIPE_CATEGORY = {"building": "building_blocks", "equipment": "combat",
                   "redstone": "redstone", "misc": "misc"}


def recipe_advancement(name: str, unlock_item: str, category: str) -> None:
    criterion = "has_" + unlock_item.split(":")[-1]
    write(ADVANCEMENT / "recipes" / RECIPE_CATEGORY[category] / f"{name}.json", {
        "parent": "minecraft:recipes/root",
        "criteria": {
            criterion: {
                "conditions": {"items": [{"items": unlock_item}]},
                "trigger": "minecraft:inventory_changed",
            },
            "has_the_recipe": {
                "conditions": {"recipe": f"{NS}:{name}"},
                "trigger": "minecraft:recipe_unlocked",
            },
        },
        "requirements": [["has_the_recipe", criterion]],
        "rewards": {"recipes": [f"{NS}:{name}"]},
    })


def display_advancement(path: str, parent: str | None, icon: str, key: str,
                        criteria: dict, requirements: list[list[str]],
                        frame: str | None = None, background: str | None = None,
                        experience: int | None = None) -> None:
    display: dict = {
        "icon": {"id": icon},
        "title": {"translate": f"advancements.{NS}.{key}.title"},
        "description": {"translate": f"advancements.{NS}.{key}.description"},
    }
    if frame:
        display["frame"] = frame
    if background:
        display["background"] = background
        display["show_toast"] = False
        display["announce_to_chat"] = False

    data: dict = {"criteria": criteria, "display": display,
                  "requirements": requirements}
    if parent:
        data["parent"] = parent
    if experience:
        data["rewards"] = {"experience": experience}
    write(ADVANCEMENT / f"{path}.json", data)


def has_items(*ids: str) -> dict:
    return {"conditions": {"items": [{"items": i} for i in ids]},
            "trigger": "minecraft:inventory_changed"}


def gen_advancements() -> None:
    # ---- recipe book unlocks ---------------------------------------------
    recipe_advancement("knell_ingot_from_smelting", item("raw_knell"), "misc")
    recipe_advancement("knell_ingot_from_blasting", item("raw_knell"), "misc")
    recipe_advancement("knell_block", item("knell_ingot"), "building")
    recipe_advancement("knell_ingot_from_block", item("knell_block"), "misc")
    recipe_advancement("knell_template", item("resonance_shard"), "misc")
    recipe_advancement("knell_integrator", item("knell_ingot"), "misc")

    # Smithing recipes get theirs by hand: gen_recipe_advancements.py derives an
    # unlock ingredient from "ingredient"/"key"/"ingredients", and a
    # smithing_transform has none of those, so it skips them silently. Without
    # these the nine upgrades would never show in the book.
    for piece in TOOLS + ARMOUR:
        recipe_advancement(f"knell_{piece}_smithing", item("knell_template"), "equipment")

    # Unlocked by the knell ingot, not by the template: a player holding knell can
    # see what it is for, which is the whole point of a recipe that exists to give
    # them a reason to go and mine it.
    recipe_advancement("knell_elytra_template", item("knell_ingot"), "equipment")
    recipe_advancement("knell_aeroshell_integration", item("knell_elytra_template"), "equipment")

    # ---- the tier's own tab ----------------------------------------------
    display_advancement(
        "knell/root", None, item("raw_knell"), "knell.root",
        {"raw_knell": has_items(item("raw_knell"))},
        [["raw_knell"]],
        background="minecraft:gui/advancements/backgrounds/stone")

    display_advancement(
        "knell/ingot", f"{NS}:knell/root", item("knell_ingot"), "knell.ingot",
        {"knell_ingot": has_items(item("knell_ingot"))},
        [["knell_ingot"]])

    display_advancement(
        "knell/integrator", f"{NS}:knell/ingot", item("knell_integrator"),
        "knell.integrator",
        {"integrator": has_items(item("knell_integrator"))},
        [["integrator"]])

    display_advancement(
        "knell/integrate", f"{NS}:knell/integrator", item("knell_pickaxe"),
        "knell.integrate",
        {"knell_gear": has_items(f"#{NS}:resonant_gear")},
        [["knell_gear"]], frame="goal", experience=50)

    display_advancement(
        "knell/full_set", f"{NS}:knell/integrate", item("knell_chestplate"),
        "knell.full_set",
        {"resonant_armour": has_items(*[item(f"knell_{p}") for p in ARMOUR])},
        [["resonant_armour"]], frame="challenge", experience=200)


# ===========================================================================
# Lang
# ===========================================================================

ADVANCEMENT_LANG = {
    "knell.root": ("Deeper Than Netherite",
                      "Mine knell ore in the deep strata of the Hollow Horizon"),
    "knell.ingot": ("A Purer Tone", "Smelt raw knell into an ingot"),
    "knell.integrator": ("Bench of the Last Rung", "Build a Knell Integrator"),
    "knell.integrate": ("Struck In Tune",
                           "Integrate knell onto a piece of netherite gear"),
    "knell.full_set": ("Standing Wave", "Own a full set of resonant armour"),
}


def gen_lang() -> None:
    """Merge our keys into the shared lang file.

    Additive on purpose. en_us.json is hand-maintained and shared with every
    other part of the mod, so this reads it, adds only keys that are missing,
    and writes it back - it never removes or rewrites an existing string.
    """
    entries: dict[str, str] = {}
    for name in BLOCKS:
        entries[f"block.{NS}.{name}"] = NAMES[name]
    for name in MATERIALS + GEAR:
        entries[f"item.{NS}.{name}"] = NAMES[name]
    entries[f"container.{NS}.knell_integrator"] = "Knell Integrator"
    # The Aeroshell carries two durability pools and a slot can only host one built-in bar,
    # so the second is drawn by a decorator. Two bars are cryptic without a key - these name
    # them, in the same colours the bars use.
    entries[f"tooltip.{NS}.aeroshell_plate"] = "Plate: %s / %s"
    entries[f"tooltip.{NS}.aeroshell_wings"] = "Wings: %s / %s"
    for key, (title, description) in ADVANCEMENT_LANG.items():
        entries[f"advancements.{NS}.{key}.title"] = title
        entries[f"advancements.{NS}.{key}.description"] = description

    existing: dict[str, str] = {}
    if LANG.exists():
        existing = json.loads(LANG.read_text(encoding="utf-8"))

    added = [k for k in entries if k not in existing]
    for key in added:
        existing[key] = entries[key]

    LANG.parent.mkdir(parents=True, exist_ok=True)
    LANG.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"lang: added {len(added)} key(s), left {len(existing) - len(added)} untouched")


# ===========================================================================

def main() -> int:
    for d in (BLOCKSTATES, BLOCK_MODELS, ITEM_MODELS, ITEM_DEFS, EQUIPMENT):
        d.mkdir(parents=True, exist_ok=True)

    gen_models()
    gen_equipment_asset()
    gen_loot()
    gen_tags()
    gen_recipes()
    gen_advancements()
    gen_lang()

    print(f"generated {len(written)} json file(s)")
    for w in written:
        print("  " + w)
    print(f"merged into {len(merged)} existing tag file(s)")
    for m in merged:
        print("  " + m)

    expected_existing = {
        "minecraft:block/mineable/pickaxe",
        "minecraft:block/needs_diamond_tool",
        "minecraft:block/incorrect_for_diamond_tool",
    }
    stomped = sorted(expected_existing - set(merged))
    if stomped:
        print("\nWARNING: these are owned by tools/gen_tags.py but did not exist.")
        print("Run gen_tags.py first, then re-run this script:")
        for name in stomped:
            print("  " + name)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

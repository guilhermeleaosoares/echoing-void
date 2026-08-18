"""
The Echoing Void - crafting and stonecutter recipes for the 61 block family variants,
plus the recipe unlock advancement each one needs.

Companion to gen_recipes.py, which owns the original blocks' recipes. This script
writes only the family set's files, so the two can be run in any order.

Schema is taken from the real 26.2 vanilla recipes in
C:\\Projects\\mcref-26.2\\clientjar\\data\\minecraft\\recipe\\: 26.2 writes ingredients
as bare ids ("ingredient": "minecraft:stone"), results as {"id": ..., "count": ...},
and recipe files live in data/<ns>/recipe/ (singular). Counts and patterns are
vanilla's, not invented:

  slab       ["###"]                       x6    oak_slab.json, stone_slab.json
  stairs     ["#  ", "## ", "###"]         x4    oak_stairs.json
  wall       ["###", "###"]                x6    stone_brick_wall.json
  planks     shapeless from #<wood>_logs   x4    oak_planks.json
  bark       ["##", "##"] from the log     x3    oak_wood.json
  fence      ["W#W", "W#W"] planks+stick   x3    oak_fence.json
  fence gate ["#W#", "#W#"] stick+planks   x1    oak_fence_gate.json
  door       ["##", "##", "##"]            x3    oak_door.json
  trapdoor   ["###", "###"]                x2    oak_trapdoor.json

The stonecutter gets every stone cut at vanilla's rates - a slab is the only cut worth
two - and additionally cuts each raw stone straight into its own worked family's
variants, the way vanilla cuts stone into stone_brick_slab. That is the difference
between a stonecutter being useful and being a novelty.

WHY THE ADVANCEMENTS ARE HERE. A recipe nobody grants never appears in the recipe
book. gen_recipe_advancements.py derives those from the recipe folder, but it runs
before this script in the asset pipeline, so this script emits its own using the
SAME functions imported from that module - not a copy of them. Run either script in
either order and the advancement files come out identical.

Run:  python tools/gen_family_recipes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from ev_families import (  # noqa: E402
    NS,
    STONE_FAMILIES,
    WOOD_FAMILIES,
    stone_cuts,
    wood_cuts,
)
from gen_recipe_advancements import category_of, ingredients_of, unlock_item  # noqa: E402

ROOT = TOOLS.parent
RECIPES = ROOT / "src" / "main" / "resources" / "data" / NS / "recipe"
ADVANCEMENTS = ROOT / "src" / "main" / "resources" / "data" / NS / "advancement" / "recipes"

recipes: dict[str, dict] = {}

STICK = "minecraft:stick"


def add(name: str, data: dict) -> None:
    if name in recipes:
        raise SystemExit(f"duplicate recipe id: {name}")
    recipes[name] = data


def block(name: str) -> str:
    return f"{NS}:{name}"


def shaped(name: str, pattern: list[str], key: dict[str, str], result: str,
           count: int, category: str, group: str) -> None:
    data: dict = {
        "type": "minecraft:crafting_shaped",
        "category": category,
        "group": group,
        "key": key,
        "pattern": pattern,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    add(name, data)


def shapeless(name: str, ingredients: list[str], result: str, count: int,
              category: str, group: str) -> None:
    data: dict = {
        "type": "minecraft:crafting_shapeless",
        "category": category,
        "group": group,
        "ingredients": ingredients,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    add(name, data)


def stonecutting(name: str, source: str, result: str, count: int) -> None:
    data: dict = {
        "type": "minecraft:stonecutting",
        "ingredient": source,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    add(name, data)


# ---------------------------------------------------------------------------
# the three cuts, in both the crafting grid and the stonecutter
# ---------------------------------------------------------------------------

def stone_recipes() -> None:
    #: A slab is the only cut worth two out of one block on the stonecutter.
    CUT_YIELD = (("slab", 2), ("stairs", 1), ("wall", 1))

    #: Extra stonecutter routes: a RAW rock also cuts straight into everything worked
    #: from it, as vanilla cuts plain stone into stone_brick_slab. Without these a
    #: player has to craft the intermediate block first, which is a chore rather than
    #: a recipe. Keyed by source base block, valued by the family prefixes it reaches.
    WORKED_FROM = {
        "raw_phonolite": ["polished_phonolite", "phonolite_brick"],
        "resonant_chalk": ["chalk_brick"],
    }

    by_prefix = {f["prefix"]: f for f in STONE_FAMILIES}

    for family in STONE_FAMILIES:
        cuts = stone_cuts(family)
        base = block(family["base"])

        shaped(cuts["slab"], ["###"], {"#": base}, block(cuts["slab"]), 6,
               "building", "echoing_void_stone_slab")
        shaped(cuts["stairs"], ["#  ", "## ", "###"], {"#": base}, block(cuts["stairs"]), 4,
               "building", "echoing_void_stone_stairs")
        shaped(cuts["wall"], ["###", "###"], {"#": base}, block(cuts["wall"]), 6,
               "building", "echoing_void_stone_wall")

        # Every stone cuts into its own three variants on the stonecutter.
        for variant, count in CUT_YIELD:
            stonecutting(f"{cuts[variant]}_stonecutting", base, block(cuts[variant]), count)

    for source_base, prefixes in WORKED_FROM.items():
        for prefix in prefixes:
            cuts = stone_cuts(by_prefix[prefix])
            for variant, count in CUT_YIELD:
                # Suffixed, because this is a second recipe producing an item that
                # already has one and two recipe files may not share an id.
                stonecutting(f"{cuts[variant]}_from_{source_base}_stonecutting",
                             block(source_base), block(cuts[variant]), count)


# ---------------------------------------------------------------------------
# a whole wood
# ---------------------------------------------------------------------------

def wood_recipes() -> None:
    for family in WOOD_FAMILIES:
        cuts = wood_cuts(family)
        planks = block(cuts["planks"])
        logs_tag = f"#{NS}:{family['id']}_logs"

        # Planks come from the wood's log TAG, so bark and stripped timber work too.
        shapeless(cuts["planks"], [logs_tag], planks, 4, "building", "echoing_void_planks")

        # Bark: four logs stacked give three all-bark blocks, and the stripped pair
        # mirrors it so a player can strip either before or after squaring the timber.
        shaped(family["wood"], ["##", "##"], {"#": block(family["log"])},
               block(family["wood"]), 3, "building", "echoing_void_bark")
        shaped(family["stripped_wood"], ["##", "##"], {"#": block(family["stripped_log"])},
               block(family["stripped_wood"]), 3, "building", "echoing_void_bark")

        shaped(cuts["slab"], ["###"], {"#": planks}, block(cuts["slab"]), 6,
               "building", "echoing_void_wooden_slab")
        shaped(cuts["stairs"], ["#  ", "## ", "###"], {"#": planks}, block(cuts["stairs"]), 4,
               "building", "echoing_void_wooden_stairs")
        shaped(cuts["fence"], ["W#W", "W#W"], {"#": STICK, "W": planks},
               block(cuts["fence"]), 3, "building", "echoing_void_wooden_fence")
        shaped(cuts["fence_gate"], ["#W#", "#W#"], {"#": STICK, "W": planks},
               block(cuts["fence_gate"]), 1, "redstone", "echoing_void_wooden_fence_gate")
        shaped(cuts["door"], ["##", "##", "##"], {"#": planks},
               block(cuts["door"]), 3, "redstone", "echoing_void_wooden_door")
        shaped(cuts["trapdoor"], ["###", "###"], {"#": planks},
               block(cuts["trapdoor"]), 2, "redstone", "echoing_void_wooden_trapdoor")


# ---------------------------------------------------------------------------

def unlock_for(recipe: dict) -> tuple[str | None, str | None]:
    """The ingredient that reveals a recipe, and the criterion name to hang it on.

    gen_recipe_advancements.unlock_item gives up when a recipe's only ingredient is a
    tag, which is every planks recipe here. Vanilla's own advancement for oak_planks
    shows the tag is a perfectly good criterion - an ItemPredicate's "items" field is a
    HolderSet and takes "#namespace:tag" directly - so fall back to it and use
    vanilla's own criterion name, has_logs.
    """
    item = unlock_item(recipe)
    if item is not None:
        # Spelled exactly as gen_recipe_advancements.py spells it, so that running
        # either script over the same recipe produces the same file.
        return item, "has_" + item.split(":")[-1].lstrip("#")

    for value in ingredients_of(recipe):
        if value.startswith("#"):
            path = value.lstrip("#").split(":")[-1]
            return value, "has_logs" if path.endswith("_logs") else f"has_{path}"

    return None, None


def write_all() -> tuple[int, list[str]]:
    RECIPES.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []

    for name, data in recipes.items():
        (RECIPES / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n",
                                              encoding="utf-8")

        item, criterion = unlock_for(data)
        if item is None:
            skipped.append(name)
            continue

        advancement = {
            "parent": "minecraft:recipes/root",
            "criteria": {
                criterion: {
                    "conditions": {"items": [{"items": item}]},
                    "trigger": "minecraft:inventory_changed",
                },
                "has_the_recipe": {
                    "conditions": {"recipe": f"{NS}:{name}"},
                    "trigger": "minecraft:recipe_unlocked",
                },
            },
            "requirements": [["has_the_recipe", criterion]],
            "rewards": {"recipes": [f"{NS}:{name}"]},
        }
        out = ADVANCEMENTS / category_of(data) / f"{name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(advancement, indent=2) + "\n", encoding="utf-8")

    return len(recipes), skipped


def main() -> int:
    stone_recipes()
    wood_recipes()
    count, skipped = write_all()

    print(f"generated {count} recipes and their unlock advancements")
    for name in sorted(recipes):
        print("  " + name)
    if skipped:
        print(f"no derivable unlock ingredient, advancement skipped: {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

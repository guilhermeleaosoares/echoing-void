"""
Recipe unlock advancements.

A recipe that nobody grants is invisible: the crafting-table recipe book only
shows recipes the player has unlocked, and unlocking happens through an
advancement carrying a `minecraft:recipe_unlocked` criterion and a
`rewards.recipes` entry. Without these files every recipe this mod adds exists
and works if you know the pattern, but never appears in the book - which is
exactly what the player reported.

Rather than hand-listing unlock conditions, this reads the generated recipes and
derives them: a recipe unlocks as soon as the player picks up one of its
ingredients, preferring one of ours over a vanilla one so the book fills in as
the player explores rather than the moment they mine iron.

Schema copied from vanilla advancement/recipes/building_blocks/diamond_block.json.

Run:  python tools/gen_recipe_advancements.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "src" / "main" / "resources" / "data" / NS / "recipe"
OUT = ROOT / "src" / "main" / "resources" / "data" / NS / "advancement" / "recipes"

written: list[str] = []


def ingredients_of(recipe: dict) -> list[str]:
    """Every item id a recipe consumes, in a stable order."""
    out: list[str] = []

    def add(value) -> None:
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            for v in value:
                add(v)
        elif isinstance(value, dict):
            for key in ("item", "id", "tag"):
                if key in value:
                    add(value[key])

    kind = recipe.get("type", "")
    if kind.endswith("crafting_shaped"):
        for value in (recipe.get("key") or {}).values():
            add(value)
    elif kind.endswith("crafting_shapeless"):
        add(recipe.get("ingredients"))
    else:
        add(recipe.get("ingredient"))
    return out


def unlock_item(recipe: dict) -> str | None:
    """Pick the ingredient that should reveal this recipe."""
    ours = [i for i in ingredients_of(recipe) if i.startswith(f"{NS}:")]
    if ours:
        return ours[0]
    others = [i for i in ingredients_of(recipe) if not i.startswith("#")]
    return others[0] if others else None


def category_of(recipe: dict) -> str:
    cat = recipe.get("category")
    if cat in ("building", "building_blocks"):
        return "building_blocks"
    if cat == "equipment":
        return "combat"
    if cat == "redstone":
        return "redstone"
    return "misc"


def main() -> int:
    if not RECIPES.is_dir():
        print(f"FAIL: no recipes at {RECIPES}")
        return 1

    skipped: list[str] = []
    for path in sorted(RECIPES.glob("*.json")):
        recipe = json.loads(path.read_text(encoding="utf-8"))
        name = path.stem
        item = unlock_item(recipe)
        if item is None:
            skipped.append(name)
            continue

        criterion = "has_" + item.split(":")[-1].lstrip("#")
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

        out_path = OUT / category_of(recipe) / f"{name}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(advancement, indent=2) + "\n", encoding="utf-8")
        written.append(f"{category_of(recipe)}/{name}")

    print(f"generated {len(written)} recipe advancements")
    for w in written:
        print("  " + w)
    if skipped:
        print(f"skipped (no derivable ingredient): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

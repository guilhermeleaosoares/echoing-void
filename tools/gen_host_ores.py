"""
Data for the host-matched ore variants and the fourth leaf colour.

These four blocks are registered in ModHostOres.java and need the usual set:
blockstate, model, item model definition, loot table, mining tags and a name.

The loot deliberately mirrors the existing variants rather than inventing new
numbers - a Phonolite bismuth vein drops the same 1-3 shards as a stone one,
because the host rock is a texture decision, not a balance one.

Run:  python tools/gen_host_ores.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src" / "main" / "resources"
ASSETS = RES / "assets" / NS
DATA = RES / "data"

written: list[str] = []


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(RES)).replace("\\", "/"))


SILK_TOUCH = {
    "condition": "minecraft:match_tool",
    "predicate": {"predicates": {"minecraft:enchantments": [
        {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}]}},
}
SHEARS = {"condition": "minecraft:match_tool", "predicate": {"items": "minecraft:shears"}}
SHEARS_OR_SILK = {"condition": "minecraft:any_of", "terms": [SHEARS, SILK_TOUCH]}
SURVIVES = {"condition": "minecraft:survives_explosion"}
DECAY = {"function": "minecraft:explosion_decay"}
ORE_FORTUNE = {"function": "minecraft:apply_bonus", "enchantment": "minecraft:fortune",
               "formula": "minecraft:ore_drops"}

# block -> (drop, count range or None)
ORES = {
    "phonolite_resonant_bismuth_ore": ("resonance_shard", (1, 3)),
    "deepslate_null_iron_ore": ("raw_null_iron", None),
    "phonolite_null_iron_ore": ("raw_null_iron", None),
}
LEAVES = {"ashen_resonance_leaves": "bismuth_seedling"}

NAMES = {
    "phonolite_resonant_bismuth_ore": "Phonolite Resonant Bismuth Ore",
    "deepslate_null_iron_ore": "Deepslate Null-Iron Ore",
    "phonolite_null_iron_ore": "Phonolite Null-Iron Ore",
    "ashen_resonance_leaves": "Ashen Resonance Leaves",
}


def visuals(block: str) -> None:
    write(ASSETS / "models" / "block" / f"{block}.json",
          {"parent": "minecraft:block/cube_all", "textures": {"all": f"{NS}:block/{block}"}})
    write(ASSETS / "blockstates" / f"{block}.json",
          {"variants": {"": {"model": f"{NS}:block/{block}"}}})
    write(ASSETS / "items" / f"{block}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:block/{block}"}})


def ore_loot(block: str, drop: str, count: tuple[int, int] | None) -> None:
    functions: list[dict] = []
    if count:
        functions.append({"function": "minecraft:set_count",
                          "count": {"type": "minecraft:uniform",
                                    "min": float(count[0]), "max": float(count[1])}})
    functions += [ORE_FORTUNE, DECAY]
    write(DATA / NS / "loot_table" / "blocks" / f"{block}.json", {
        "type": "minecraft:block",
        "random_sequence": f"{NS}:blocks/{block}",
        "pools": [{
            "rolls": 1.0,
            "entries": [{
                "type": "minecraft:alternatives",
                "children": [
                    {"type": "minecraft:item", "name": f"{NS}:{block}", "conditions": [SILK_TOUCH]},
                    {"type": "minecraft:item", "name": f"{NS}:{drop}", "functions": functions},
                ],
            }],
        }],
    })


def leaf_loot(block: str, sapling: str) -> None:
    write(DATA / NS / "loot_table" / "blocks" / f"{block}.json", {
        "type": "minecraft:block",
        "random_sequence": f"{NS}:blocks/{block}",
        "pools": [{
            "rolls": 1.0,
            "entries": [{
                "type": "minecraft:alternatives",
                "children": [
                    {"type": "minecraft:item", "name": f"{NS}:{block}",
                     "conditions": [SHEARS_OR_SILK]},
                    {"type": "minecraft:item", "name": f"{NS}:{sapling}",
                     "conditions": [SURVIVES, {"condition": "minecraft:table_bonus",
                                               "enchantment": "minecraft:fortune",
                                               "chances": [0.05, 0.0625, 0.083333336, 0.1]}]},
                ],
            }],
        }],
    })


def tags() -> None:
    """Merge into the vanilla tag files rather than overwriting them.

    gen_tags.py owns these same paths, so this reads what is already there and
    adds only what is missing - running the two in either order converges.
    """
    def merge(kind: str, name: str, values: list[str]) -> None:
        path = DATA / "minecraft" / "tags" / kind / f"{name}.json"
        existing: list[str] = []
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8")).get("values", [])
        merged = existing + [v for v in values if v not in existing]
        write(path, {"replace": False, "values": merged})

    ore_ids = [f"{NS}:{b}" for b in ORES]
    merge("block", "mineable/pickaxe", ore_ids)
    merge("block", "needs_diamond_tool", ore_ids)
    # Null-Iron demands netherite wherever it is found, host rock notwithstanding.
    merge("block", "incorrect_for_diamond_tool",
          [f"{NS}:deepslate_null_iron_ore", f"{NS}:phonolite_null_iron_ore"])
    merge("block", "mineable/hoe", [f"{NS}:ashen_resonance_leaves"])
    merge("block", "leaves", [f"{NS}:ashen_resonance_leaves"])


def lang() -> None:
    path = ASSETS / "lang" / "en_us.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for block, name in NAMES.items():
        key = f"block.{NS}.{block}"
        if key not in data:
            data[key] = name
            added += 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  lang: {added} name(s) added")


def main() -> int:
    for block, (drop, count) in ORES.items():
        visuals(block)
        ore_loot(block, drop, count)
    for block, sapling in LEAVES.items():
        visuals(block)
        leaf_loot(block, sapling)
    tags()
    lang()
    print(f"generated {len(written)} files for the host-matched ores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

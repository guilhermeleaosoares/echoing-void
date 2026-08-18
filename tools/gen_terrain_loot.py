"""
The Echoing Void - loot tables for the 18 new terrain blocks.

Companion to tools/gen_loot_tables.py, which owns the original blocks, the mob
tables and the structure chests. This script writes only the terrain set's files,
so the two can be run in any order.

Condition and function shapes are lifted verbatim from the real 26.2 vanilla
tables in C:\\Projects\\mcref-26.2\\clientjar\\data\\minecraft\\loot_table\\ and
kept byte-identical to the fragments already used in gen_loot_tables.py:

  * silk-touch predicate  -> match_tool / predicates / minecraft:enchantments
  * shears-or-silk        -> any_of over the two match_tool terms
  * leaf seedling chance  -> table_bonus with the vanilla four-step fortune curve
  * cluster drops         -> the nested alternatives from blocks/amethyst_cluster,
                             where a pickaxe yields the full four shards and a
                             bare hand yields two

In 26.2 a block's default table is <ns>:blocks/<id> in the `loot_table` registry,
so files land in data/<ns>/loot_table/blocks/<id>.json.

Run:  python tools/gen_terrain_loot.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
LOOT = ROOT / "src" / "main" / "resources" / "data" / NS / "loot_table"

written: list[str] = []


def write(rel: str, data: dict) -> None:
    path = LOOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(rel)


# --------------------------------------------------------------------------
# condition fragments - identical to gen_loot_tables.py
# --------------------------------------------------------------------------

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

SHEARS = {"condition": "minecraft:match_tool", "predicate": {"items": "minecraft:shears"}}
SHEARS_OR_SILK = {"condition": "minecraft:any_of", "terms": [SHEARS, SILK_TOUCH]}
SURVIVES = {"condition": "minecraft:survives_explosion"}
DECAY = {"function": "minecraft:explosion_decay"}
ORE_FORTUNE = {
    "function": "minecraft:apply_bonus",
    "enchantment": "minecraft:fortune",
    "formula": "minecraft:ore_drops",
}
# Vanilla gives clusters their full yield only to a pickaxe; anything else halves it.
PICKAXE = {
    "condition": "minecraft:match_tool",
    "predicate": {"items": "#minecraft:cluster_max_harvestables"},
}


def block_table(block: str, pools: list[dict]) -> dict:
    return {
        "type": "minecraft:block",
        "pools": pools,
        "random_sequence": f"{NS}:blocks/{block}",
    }


def self_drop(block: str) -> None:
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "conditions": [SURVIVES],
        "entries": [{"type": "minecraft:item", "name": f"{NS}:{block}"}],
    }]))


def leaves(block: str, seedling: str) -> None:
    """Shears or silk touch recover the block; otherwise a rare seedling."""
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:alternatives",
            "children": [
                {"type": "minecraft:item", "name": f"{NS}:{block}",
                 "conditions": [SHEARS_OR_SILK]},
                {"type": "minecraft:item", "name": f"{NS}:{seedling}",
                 "conditions": [
                     SURVIVES,
                     {"condition": "minecraft:table_bonus",
                      "enchantment": "minecraft:fortune",
                      "chances": [0.05, 0.0625, 0.083333336, 0.1]},
                 ]},
            ],
        }],
    }]))


def cluster(block: str, shard: str, max_count: float, hand_count: float) -> None:
    """Silk touch keeps the cluster intact; a pickaxe gets the full shard yield."""
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:alternatives",
            "children": [
                {"type": "minecraft:item", "name": f"{NS}:{block}",
                 "conditions": [SILK_TOUCH]},
                {
                    "type": "minecraft:alternatives",
                    "children": [
                        {"type": "minecraft:item", "name": f"{NS}:{shard}",
                         "conditions": [PICKAXE],
                         "functions": [
                             {"function": "minecraft:set_count", "count": max_count},
                             ORE_FORTUNE,
                         ]},
                        {"type": "minecraft:item", "name": f"{NS}:{shard}",
                         "functions": [
                             {"function": "minecraft:set_count", "count": hand_count},
                             DECAY,
                         ]},
                    ],
                },
            ],
        }],
    }]))


# --------------------------------------------------------------------------

#: Stones, worked stone, loose ground, cover, timber and the lantern all drop
#: themselves. Humming Crystal is in here rather than with the clusters on
#: purpose: it is the light source players are meant to be able to relocate.
SELF_DROP = [
    "resonant_chalk",
    "echo_slate",
    "amber_strata",
    "humming_crystal",
    "chalk_bricks",
    "polished_phonolite",
    "chime_sand",
    "resonance_moss",
    "amber_lichen",
    "humming_stem",
    "stripped_humming_stem",
    "harmonic_lantern",
    # Cross-model growths: instant break, straight self-drop, no shears needed.
    "echo_sprout",
    "chime_grass",
    "crystal_bloom",
]

#: Both new canopies seed the same Bismuth Seedling the existing canopy does, so
#: a player only has to learn one propagation item for the whole dimension.
LEAF_BLOCKS = ["amber_resonance_leaves", "violet_resonance_leaves"]


def main() -> int:
    for block in SELF_DROP:
        self_drop(block)

    for block in LEAF_BLOCKS:
        leaves(block, "bismuth_seedling")

    cluster("bismuth_cluster", "resonance_shard", 4.0, 2.0)

    print(f"generated {len(written)} loot tables")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

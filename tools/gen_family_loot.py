"""
The Echoing Void - loot tables for the 61 block family variants.

Companion to gen_loot_tables.py and gen_terrain_loot.py, which own the original
blocks and the terrain set. This script writes only the family set's files - in
particular it never touches the two trunks that predate it, whose tables already
exist - so the three can be run in any order.

Three shapes, all lifted from the real 26.2 vanilla tables in
C:\\Projects\\mcref-26.2\\clientjar\\data\\minecraft\\loot_table\\blocks\\:

  * self drop     blocks/oak_stairs.json - one pool, one item entry, guarded by
                  survives_explosion. Stairs, walls, fences, gates, trapdoors,
                  planks, logs and bark all use this and nothing else.
  * slab          blocks/oak_slab.json - THE ONE THAT IS NOT A SELF DROP. A double
                  slab is a single block holding two items, so its entry carries a
                  set_count of 2 conditional on type=double, plus explosion_decay
                  instead of a survives_explosion condition, so a blast on a double
                  slab can still drop one half. Getting this wrong is invisible until
                  a player mines a double slab and gets one slab back.
  * door          blocks/oak_door.json - a door occupies two block positions but is
                  one item, so the entry is conditional on half=lower and the upper
                  half drops nothing at all.

In 26.2 a block's default table is <ns>:blocks/<id> in the `loot_table` registry, so
files land in data/<ns>/loot_table/blocks/<id>.json.

Run:  python tools/gen_family_loot.py
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
    wood_pillars,
)

ROOT = TOOLS.parent
LOOT = ROOT / "src" / "main" / "resources" / "data" / NS / "loot_table"

written: list[str] = []

SURVIVES = {"condition": "minecraft:survives_explosion"}
DECAY = {"function": "minecraft:explosion_decay"}


def write(block: str, pools: list[dict]) -> None:
    path = LOOT / "blocks" / f"{block}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "type": "minecraft:block",
        "pools": pools,
        "random_sequence": f"{NS}:blocks/{block}",
    }, indent=2) + "\n", encoding="utf-8")
    written.append(f"blocks/{block}")


def state_condition(block: str, prop: str, value: str) -> dict:
    return {
        "block": f"{NS}:{block}",
        "condition": "minecraft:block_state_property",
        "properties": {prop: value},
    }


def self_drop(block: str) -> None:
    write(block, [{
        "rolls": 1.0,
        "conditions": [SURVIVES],
        "entries": [{"type": "minecraft:item", "name": f"{NS}:{block}"}],
    }])


def slab(block: str) -> None:
    """A double slab is two items in one block position."""
    write(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:item",
            "name": f"{NS}:{block}",
            "functions": [
                {
                    "function": "minecraft:set_count",
                    "count": 2.0,
                    "conditions": [state_condition(block, "type", "double")],
                },
                DECAY,
            ],
        }],
    }])


def door(block: str) -> None:
    """Two block positions, one item: only the lower half pays out."""
    write(block, [{
        "rolls": 1.0,
        "conditions": [SURVIVES],
        "entries": [{
            "type": "minecraft:item",
            "name": f"{NS}:{block}",
            "conditions": [state_condition(block, "half", "lower")],
        }],
    }])


def main() -> int:
    for family in STONE_FAMILIES:
        cuts = stone_cuts(family)
        slab(cuts["slab"])
        self_drop(cuts["stairs"])
        self_drop(cuts["wall"])

    for family in WOOD_FAMILIES:
        # new_only keeps us off the two trunk pairs that gen_loot_tables.py and
        # gen_terrain_loot.py already wrote tables for.
        for pillar in wood_pillars(family, new_only=True):
            self_drop(pillar)

        cuts = wood_cuts(family)
        self_drop(cuts["planks"])
        slab(cuts["slab"])
        self_drop(cuts["stairs"])
        self_drop(cuts["fence"])
        self_drop(cuts["fence_gate"])
        self_drop(cuts["trapdoor"])
        door(cuts["door"])

    print(f"generated {len(written)} loot tables")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

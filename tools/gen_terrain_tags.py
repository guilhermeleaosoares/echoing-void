"""
The Echoing Void - block tags for the 18 new terrain blocks.

Companion to tools/gen_tags.py, which owns the original blocks' tags and the
tool-material tags. Both scripts have to contribute to the SAME vanilla tag files
(mineable/pickaxe, leaves, logs and friends), and a resource pack can only hold
one file per path, so this script MERGES rather than overwrites: it reads whatever
is already at the path, unions our ids in, and writes the result back.

  RUN ORDER: python tools/gen_tags.py  &&  python tools/gen_terrain_tags.py

  Merging makes this script idempotent and safe to re-run, but it cannot recover
  entries that gen_tags.py has already stomped - gen_tags.py writes whole files.
  Run it first, always. The summary at the end says which files were merged into
  an existing one and which were created from nothing, so a wrong order is
  visible rather than silent.

Why tags at all: mining tool and tier carry real mechanics in 26.2 and have no
Java API. Code contributes only `.requiresCorrectToolForDrops()`; these files
decide which tool works and what tier it must be.

Tier choices for this set:
  * the four strata stones and Chalk Bricks are deliberately UNGATED (any
    pickaxe), because they are the blocks a player walks on from the moment they
    arrive and gating the ground behind diamond is what made the old dimension
    feel like a tunnelling chore
  * Polished Phonolite inherits needs_diamond_tool from the Raw Phonolite it is
    cut from, so the worked block is no cheaper than its source
  * Humming Crystal and Bismuth Cluster follow vanilla amethyst: pickaxe, no tier

Directory names are SINGULAR in 26.2: tags/block/, tags/item/.

Run:  python tools/gen_terrain_tags.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "main" / "resources" / "data"

merged: list[str] = []
created: list[str] = []


def merge_tag(namespace: str, kind: str, name: str, values: list[str]) -> None:
    """Union `values` into the tag file, preserving any entries already there."""
    path = DATA / namespace / "tags" / kind / f"{name}.json"

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        existing = list(data.get("values", []))
        replace = bool(data.get("replace", False))
        merged.append(f"{namespace}:{kind}/{name}")
    else:
        existing = []
        replace = False
        created.append(f"{namespace}:{kind}/{name}")

    for value in values:
        if value not in existing:
            existing.append(value)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"replace": replace, "values": existing}, indent=2) + "\n",
                    encoding="utf-8")


def b(name: str) -> str:
    return f"{NS}:{name}"


# ---------------------------------------------------------------------------
# the terrain set, grouped by how it is mined
# ---------------------------------------------------------------------------

STRATA = ["resonant_chalk", "echo_slate", "amber_strata"]
WORKED_STONE = ["chalk_bricks", "polished_phonolite"]
CRYSTAL = ["humming_crystal", "bismuth_cluster"]
GROUND_COVER = ["resonance_moss", "amber_lichen"]
LEAF_BLOCKS = ["amber_resonance_leaves", "violet_resonance_leaves"]
STEMS = ["humming_stem", "stripped_humming_stem"]
PLANTS = ["echo_sprout", "chime_grass", "crystal_bloom"]

PICKAXE = STRATA + WORKED_STONE + CRYSTAL + ["harmonic_lantern"]
AXE = STEMS
HOE = GROUND_COVER + LEAF_BLOCKS
SHOVEL = ["chime_sand"]
DIAMOND_TIER = ["polished_phonolite"]

#: What the cross-model growths will stand on. Vanilla's supports_vegetation is
#: the overworld dirt family, and nothing in this dimension belongs to it, so
#: VoidPlantBlock widens its placement check with this tag instead.
SUPPORTS_VOID_VEGETATION = STRATA + WORKED_STONE + GROUND_COVER + ["chime_sand", "raw_phonolite"]

#: The stone spine of the dimension, offered for worldgen rules that want to talk
#: about "the rock" without naming five blocks.
HOLLOW_HORIZON_STONES = STRATA + ["raw_phonolite"]


def main() -> int:
    # ---- vanilla block tags: tool class and tier -------------------------
    merge_tag("minecraft", "block", "mineable/pickaxe", [b(x) for x in PICKAXE])
    merge_tag("minecraft", "block", "mineable/axe", [b(x) for x in AXE])
    merge_tag("minecraft", "block", "mineable/hoe", [b(x) for x in HOE])
    merge_tag("minecraft", "block", "mineable/shovel", [b(x) for x in SHOVEL])
    merge_tag("minecraft", "block", "needs_diamond_tool", [b(x) for x in DIAMOND_TIER])

    # ---- vanilla behaviour tags ------------------------------------------
    # leaves: hoe/shears speed and the leaf behaviours vanilla hangs off this tag.
    merge_tag("minecraft", "block", "leaves", [b(x) for x in LEAF_BLOCKS])
    # logs: also pulls the stems into #minecraft:prevents_nearby_leaf_decay.
    merge_tag("minecraft", "block", "logs", [b(x) for x in STEMS])

    # ---- our own block tags ----------------------------------------------
    merge_tag(NS, "block", "supports_void_vegetation", [b(x) for x in SUPPORTS_VOID_VEGETATION])
    merge_tag(NS, "block", "hollow_horizon_stones", [b(x) for x in HOLLOW_HORIZON_STONES])

    print(f"merged into {len(merged)} existing tag file(s):")
    for name in merged:
        print("  " + name)
    print(f"created {len(created)} new tag file(s):")
    for name in created:
        print("  " + name)

    expected_existing = {
        "minecraft:block/mineable/pickaxe",
        "minecraft:block/mineable/axe",
        "minecraft:block/mineable/hoe",
        "minecraft:block/needs_diamond_tool",
        "minecraft:block/leaves",
        "minecraft:block/logs",
    }
    stomped = sorted(expected_existing.intersection(created))
    if stomped:
        print("\nWARNING: these are owned by tools/gen_tags.py but did not exist.")
        print("Run gen_tags.py first, then re-run this script:")
        for name in stomped:
            print("  " + name)
        return 1

    # Plants are instant-break and need no tool tag at all; listed here so the
    # set is accounted for rather than looking forgotten.
    assert len(PICKAXE) + len(AXE) + len(HOE) + len(SHOVEL) + len(PLANTS) == 18
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

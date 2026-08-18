"""
The Echoing Void - block and item tags for the 61 block family variants.

Companion to gen_tags.py (original blocks) and gen_terrain_tags.py (terrain set).
All three contribute to the SAME vanilla tag files, and a resource pack can hold only
one file per path, so this script MERGES: it reads whatever is already there, unions
our ids in, and writes the result back.

  RUN ORDER: gen_tags.py && gen_terrain_tags.py && gen_family_tags.py

  Merging makes this idempotent and safe to re-run, but it cannot recover entries a
  whole-file writer has already stomped. gen_tags.py writes whole files, so it must go
  first. The summary at the end names every file that was created rather than merged,
  which is what a wrong order looks like.

WHY THESE TAGS ARE NOT COSMETIC. Two thirds of the behaviour a player expects from
these blocks is carried by tags, not by the Java:

  * mineable/pickaxe, mineable/axe and needs_diamond_tool are the ONLY expression of
    mining tool and tier in 26.2. The stone cuts call requiresCorrectToolForDrops(),
    so without these files they drop nothing to any tool. The wood does not call it,
    so its mineable/axe entry buys mining SPEED rather than a gate.
  * #minecraft:fences and #minecraft:wooden_fences are what makes a fence connect.
    FenceBlock.isSameFence tests `state.is(FENCES) && state.is(WOODEN_FENCES) ==
    <this fence>.is(WOODEN_FENCES)` - so a fence outside the tags connects to nothing,
    not even to itself. Verified in the 26.2 source, not assumed.
  * #minecraft:walls is the same story for walls (WallBlock line 108), and fence gates
    connect to fences through `block instanceof FenceGateBlock` plus the gate's own
    facing, which needs no tag but does need the fence to be tagged.
  * the umbrella tags contain the wooden ones - #minecraft:slabs starts with
    "#minecraft:wooden_slabs", and doors, fences, stairs and trapdoors likewise - so a
    wooden piece is added ONLY to its wooden tag and inherits the umbrella. Adding it
    to both would be a duplicate entry, not a fix.
  * whether a door opens by hand is NOT a tag in 26.2: it is BlockSetType.canOpenByHand,
    set in ModBlockFamilies. The tags still matter for zombie door-breaking and for
    every datapack that talks about "doors".
  * #minecraft:logs pulls our timber into #minecraft:prevents_nearby_leaf_decay, which
    is what stops a grove's canopy rotting away around a player's build.

Our woods deliberately do NOT go in logs_that_burn: nothing in this dimension is
flammable, none of these blocks call ignitedByLava(), and the tag is a claim about
burning.

Directory names are SINGULAR in 26.2: tags/block/, tags/item/.

Run:  python tools/gen_family_tags.py
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


def both(name: str, values: list[str]) -> None:
    """Merge into the block tag and the item tag of the same name.

    BlockItemTags in 26.2 creates the pair from one id - PLANKS, SLABS, WOODEN_DOORS
    and the rest all exist in both registries under the same path - and the item half
    is what lets our planks stand in for oak in a vanilla recipe.
    """
    merge_tag("minecraft", "block", name, values)
    merge_tag("minecraft", "item", name, values)


def b(name: str) -> str:
    return f"{NS}:{name}"


# ---------------------------------------------------------------------------
# the family set, grouped by the tag it belongs in
# ---------------------------------------------------------------------------

STONE_SLABS = [stone_cuts(f)["slab"] for f in STONE_FAMILIES]
STONE_STAIRS = [stone_cuts(f)["stairs"] for f in STONE_FAMILIES]
STONE_WALLS = [stone_cuts(f)["wall"] for f in STONE_FAMILIES]
STONE_ALL = STONE_SLABS + STONE_STAIRS + STONE_WALLS

#: The cuts of the three stones that were already diamond-gated. Cutting a stone must
#: never make it cheaper to mine than the block it came from.
DIAMOND_CUTS = [cut
                for f in STONE_FAMILIES if f["tier"] == "diamond"
                for cut in stone_cuts(f).values()]

PLANKS = [wood_cuts(f)["planks"] for f in WOOD_FAMILIES]
WOODEN_SLABS = [wood_cuts(f)["slab"] for f in WOOD_FAMILIES]
WOODEN_STAIRS = [wood_cuts(f)["stairs"] for f in WOOD_FAMILIES]
WOODEN_FENCES = [wood_cuts(f)["fence"] for f in WOOD_FAMILIES]
FENCE_GATES = [wood_cuts(f)["fence_gate"] for f in WOOD_FAMILIES]
WOODEN_DOORS = [wood_cuts(f)["door"] for f in WOOD_FAMILIES]
WOODEN_TRAPDOORS = [wood_cuts(f)["trapdoor"] for f in WOOD_FAMILIES]

#: Trunks and bark. new_only skips the two trunk pairs the earlier generators already
#: put in #minecraft:logs, so we do not list them twice.
TIMBER = [p for f in WOOD_FAMILIES for p in wood_pillars(f, new_only=True)]

WOOD_ALL = (TIMBER + PLANKS + WOODEN_SLABS + WOODEN_STAIRS + WOODEN_FENCES
            + FENCE_GATES + WOODEN_DOORS + WOODEN_TRAPDOORS)


def main() -> int:
    # ---- tool class and tier ---------------------------------------------
    merge_tag("minecraft", "block", "mineable/pickaxe", [b(x) for x in STONE_ALL])
    merge_tag("minecraft", "block", "mineable/axe", [b(x) for x in WOOD_ALL])
    merge_tag("minecraft", "block", "needs_diamond_tool", [b(x) for x in DIAMOND_CUTS])

    # ---- shape tags: what a block behaves as -----------------------------
    # Stone cuts go straight into the umbrella tags; wooden ones go into the wooden
    # sub-tags the umbrellas already include.
    both("slabs", [b(x) for x in STONE_SLABS])
    both("stairs", [b(x) for x in STONE_STAIRS])
    both("walls", [b(x) for x in STONE_WALLS])

    both("planks", [b(x) for x in PLANKS])
    both("wooden_slabs", [b(x) for x in WOODEN_SLABS])
    both("wooden_stairs", [b(x) for x in WOODEN_STAIRS])
    both("wooden_fences", [b(x) for x in WOODEN_FENCES])
    both("fence_gates", [b(x) for x in FENCE_GATES])
    both("wooden_doors", [b(x) for x in WOODEN_DOORS])
    both("wooden_trapdoors", [b(x) for x in WOODEN_TRAPDOORS])
    both("logs", [b(x) for x in TIMBER])

    # ---- our own per-wood log tags ---------------------------------------
    # One tag per wood holding all four of its timbers, exactly as vanilla's
    # #minecraft:oak_logs holds oak_log, oak_wood and both stripped forms. This is what
    # the planks recipe takes as its ingredient, so a player can make planks out of
    # bark or stripped timber and not only out of a fresh trunk. These list the two
    # older trunks too: the tag describes the WOOD, not which generator registered it.
    for family in WOOD_FAMILIES:
        name = f"{family['id']}_logs"
        timbers = [b(x) for x in wood_pillars(family)]
        merge_tag(NS, "block", name, timbers)
        merge_tag(NS, "item", name, timbers)

    print(f"merged into {len(merged)} existing tag file(s):")
    for name in merged:
        print("  " + name)
    print(f"created {len(created)} new tag file(s):")
    for name in created:
        print("  " + name)

    expected_existing = {
        "minecraft:block/mineable/pickaxe",
        "minecraft:block/mineable/axe",
        "minecraft:block/needs_diamond_tool",
        "minecraft:block/logs",
    }
    stomped = sorted(expected_existing.intersection(created))
    if stomped:
        print("\nWARNING: these are owned by gen_tags.py / gen_terrain_tags.py but did not exist.")
        print("Run those first, then re-run this script:")
        for name in stomped:
            print("  " + name)
        return 1

    total = len(STONE_ALL) + len(WOOD_ALL)
    assert total == 61, f"expected 61 family blocks, tagged {total}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

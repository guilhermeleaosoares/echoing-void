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
    tag("minecraft", "item", "chest_armor",
        [b("resonance_chestplate"), b("knell_chestplate")])
    tag("minecraft", "item", "leg_armor",
        [b("resonance_leggings"), b("knell_leggings"), b("aero_stride_greaves")])
    tag("minecraft", "item", "foot_armor",
        [b("resonance_boots"), b("knell_boots")])

    print(f"generated {len(written)} tag files")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

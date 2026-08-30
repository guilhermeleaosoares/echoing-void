"""
The Echoing Void - the four void saplings: textures, models, loot, tags and names.

PLAYER: "deprecate the bismuth seedling, and replace it with saplings for every
different void tree type."

The Bismuth Seedling was a plain Item - unplantable - and all four canopies dropped
that same one, so felling an Amber Bough and an Echo Ash gave the same souvenir and
grew neither tree. One sapling per tree now, each wired in ModTrees to the grove
feature its own canopy came from:

    petrified_tuning_sapling  <- calcified_resonance_leaves  -> petrified_grove
    echo_ash_sapling          <- ashen_resonance_leaves      -> echo_ash_grove
    amber_bough_sapling       <- amber_resonance_leaves      -> amber_bough_grove
    humming_sapling           <- violet_resonance_leaves     -> humming_grove

Each sprite is drawn from its own tree's canopy and trunk colours, because four
saplings a player cannot tell apart in a hotbar would be barely better than one.

Run:  python tools/gen_tree_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import gen_item_textures as gi  # noqa: E402
from gen_item_textures import Sprite, poly, Material  # noqa: E402

NS = "echoing_void"
ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS
DATA = ROOT / "src" / "main" / "resources" / "data" / NS

BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_MODELS = ASSETS / "models" / "item"
ITEM_DEFS = ASSETS / "items"
BLOCK_TEX = ASSETS / "textures" / "block"
LANG = ASSETS / "lang" / "en_us.json"
LOOT = DATA / "loot_table" / "blocks"

written: list[str] = []


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ---------------------------------------------------------------------------
# The four trees. Palette entries come from docs/spec/art_direction.json, so the
# sprites stay inside the same budget verify_textures.py holds every other sheet to.
# ---------------------------------------------------------------------------

#: name, canopy material, trunk material, the leaf block it drops from
TREES = [
    ("petrified_tuning_sapling", "chalk", "phonolite", "calcified_resonance_leaves"),
    ("echo_ash_sapling", "phonolite", "null_iron", "ashen_resonance_leaves"),
    ("amber_bough_sapling", "amber", "amber_dark", "amber_bough_log"),
    ("humming_sapling", "arcane", "arcane_deep", "humming_stem"),
]

# Materials come from gen_item_textures rather than being redefined here. A Material is
# a ramp of blended palette entries, not a list of hex values, and a second definition of
# "amber" would drift from the one every other amber sprite in the mod already uses.
CANOPY = {
    "chalk": gi.PALE_BONE,
    "phonolite": gi.SLATE,
    "amber": gi.AMBER,
    "arcane": gi.ARCANE,
}
TRUNK = {
    "phonolite": gi.SLATE,
    "null_iron": gi.NULL_IRON,
    "amber_dark": gi.TUNING_WOOD,
    "arcane_deep": gi.NULL_IRON,
}


def make_petrified_tuning_sapling(canopy: Material, trunk: Material, seed: int = 7001) -> Sprite:
    """Narrow, upright, sparse, stony tuning-fork sapling."""
    sp = Sprite()
    
    stem_pts = {
        # Flared base sitting on y=15
        (7, 15), (8, 15), (9, 15),
        (7, 14), (8, 14),
        (7, 13), (8, 13),
        (7, 12), (8, 12),
        (6, 11), (7, 11), (8, 11),
        (6, 10), (7, 10), (8, 10), (9, 10),
        # Fork junction & left branch
        (6, 9), (7, 9), (8, 9),
        (5, 8), (6, 8),
        (5, 7), (6, 7),
        (5, 6), (6, 6),
        (5, 5), (6, 5),
        (5, 4),
        # Right branch (taller)
        (8, 8), (9, 8),
        (9, 7), (10, 7),
        (9, 6), (10, 6),
        (9, 5), (10, 5),
        (9, 4), (10, 4),
        (9, 3), (10, 3),
        (9, 2),
    }
    
    leaf_pts = {
        # Left fork cluster
        (4, 5), (4, 6), (4, 7),
        (3, 6), (3, 7),
        (4, 4), (5, 3), (6, 3), (7, 4),
        (5, 2), (6, 2), (7, 3),
        # Right fork cluster
        (8, 2), (8, 3), (8, 4),
        (10, 2), (11, 2), (11, 3), (11, 4), (12, 4),
        (9, 1), (10, 1),
        (10, 3), (11, 5), (10, 6), (11, 6),
        # Mid-canopy clusters
        (4, 8), (4, 9), (5, 9), (3, 8),
        (7, 6), (8, 6), (7, 7), (8, 7),
        (9, 9), (10, 8), (11, 8), (10, 9), (11, 9),
        # Lower tufts
        (4, 10), (5, 10), (5, 11), (4, 11),
        (9, 11), (10, 11), (10, 12),
    }
    leaf_pts -= stem_pts
    
    sp.paint(leaf_pts, canopy, 0.58, seed, spread=0.32, light=0.30)
    sp.paint(stem_pts, trunk, 0.42, seed + 13, spread=0.25, light=0.22)
    sp.outline()
    return sp


def make_echo_ash_sapling(canopy: Material, trunk: Material, seed: int = 7038) -> Sprite:
    """Drooping, wispy, weeping ash sapling with dark slate trunk."""
    sp = Sprite()
    
    stem_pts = {
        (6, 15), (7, 15), (8, 15),
        (7, 14), (8, 14),
        (6, 13), (7, 13), (8, 13),
        (6, 12), (7, 12),
        (6, 11), (7, 11),
        (6, 10), (7, 10),
        (7, 9), (8, 9),
        (7, 8), (8, 8),
        (8, 7), (9, 7),
        (8, 6), (9, 6),
        (8, 5),
    }
    
    leaf_pts = {
        # Top crown with wispy tips
        (8, 1), (9, 1),
        (7, 2), (8, 2), (9, 2), (10, 2),
        (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (11, 3),
        (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4),
        (4, 5), (5, 5), (6, 5), (7, 5), (10, 5), (11, 5), (12, 5),
        (4, 6), (5, 6), (6, 6), (7, 6), (10, 6), (11, 6),
        # Drooping tendrils on left side
        (3, 7), (4, 7), (5, 7), (6, 7),
        (3, 8), (4, 8), (5, 8),
        (2, 9), (3, 9), (4, 9), (5, 9),
        (2, 10), (3, 10), (4, 10),
        (2, 11), (3, 11),
        (3, 12),
        # Right side canopy
        (9, 8), (10, 8), (11, 8), (12, 8),
        (10, 9), (11, 9), (12, 9),
        (11, 10), (12, 10),
        (11, 11),
        # Center wisps
        (8, 10), (9, 10), (8, 11),
    }
    leaf_pts -= stem_pts
    
    sp.paint(leaf_pts, canopy, 0.54, seed, spread=0.36, light=0.30)
    sp.paint(stem_pts, trunk, 0.40, seed + 17, spread=0.24, light=0.20)
    sp.outline()
    return sp


def make_amber_bough_sapling(canopy: Material, trunk: Material, seed: int = 7075) -> Sprite:
    """Broad, full spreading amber bough sapling."""
    sp = Sprite()
    
    stem_pts = {
        (6, 15), (7, 15), (8, 15),
        (7, 14), (8, 14),
        (7, 13), (8, 13),
        (6, 12), (7, 12), (8, 12),
        (7, 11), (8, 11),
        (7, 10), (8, 10),
        (7, 9), (8, 9), (9, 9),
        (8, 8), (9, 8),
        (8, 7),
    }
    
    leaf_pts = {
        (5, 1), (9, 1), (10, 1),
        (4, 2), (5, 2), (6, 2), (8, 2), (9, 2), (10, 2), (11, 2),
        (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (11, 3), (12, 3),
        (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4), (13, 4),
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5), (11, 5), (12, 5), (13, 5), (14, 5),
        (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6), (12, 6), (13, 6),
        (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (10, 7), (11, 7), (12, 7), (13, 7),
        (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8), (10, 8), (11, 8), (12, 8), (13, 8),
        (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (10, 9), (11, 9), (12, 9),
        (3, 10), (4, 10), (5, 10), (10, 10), (11, 10),
        (4, 11), (5, 11), (10, 11),
        (4, 12), (5, 12),
    }
    leaf_pts.discard((7, 2))
    leaf_pts.discard((1, 5))
    leaf_pts -= stem_pts
    
    sp.paint(leaf_pts, canopy, 0.56, seed, spread=0.34, light=0.30)
    sp.paint(stem_pts, trunk, 0.44, seed + 19, spread=0.26, light=0.22)
    sp.outline()
    return sp


def make_humming_sapling(canopy: Material, trunk: Material, seed: int = 7112) -> Sprite:
    """Bulbous mushroom-like violet glowing sapling."""
    sp = Sprite()
    
    stem_pts = {
        (6, 15), (7, 15), (8, 15), (9, 15),
        (6, 14), (7, 14), (8, 14), (9, 14),
        (7, 13), (8, 13),
        (7, 12), (8, 12),
        (7, 11), (8, 11),
        (7, 10), (8, 10),
        (7, 9), (8, 9),
        (7, 8), (8, 8),
    }
    
    leaf_pts = {
        # Rounded domed top
        (6, 1), (7, 1), (8, 1),
        (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2),
        (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (11, 3),
        (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4),
        (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5), (11, 5), (12, 5), (13, 5),
        (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6), (12, 6), (13, 6),
        (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7), (10, 7), (11, 7), (12, 7), (13, 7),
        # Mushroom cap overhang rim
        (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (9, 8), (10, 8), (11, 8), (12, 8), (13, 8),
        (3, 9), (4, 9), (5, 9), (6, 9), (9, 9), (10, 9), (11, 9), (12, 9),
        (4, 10), (5, 10), (10, 10), (11, 10),
        (4, 11), (11, 11),
    }
    # Slight organic asymmetry
    leaf_pts.discard((2, 6))
    leaf_pts.discard((13, 8))
    leaf_pts -= stem_pts
    
    sp.paint(leaf_pts, canopy, 0.55, seed, spread=0.35, light=0.28)
    sp.paint(stem_pts, trunk, 0.40, seed + 23, spread=0.25, light=0.20)
    sp.outline()
    return sp


SAPLING_BUILDERS = {
    "petrified_tuning_sapling": make_petrified_tuning_sapling,
    "echo_ash_sapling": make_echo_ash_sapling,
    "amber_bough_sapling": make_amber_bough_sapling,
    "humming_sapling": make_humming_sapling,
}


def sapling_sprite(name: str, canopy: Material, trunk: Material, seed: int) -> Sprite:
    """Dispatches to the tree-specific sapling generator matching the tree it becomes."""
    builder = SAPLING_BUILDERS[name]
    return builder(canopy, trunk, seed)


# ---------------------------------------------------------------------------

def gen_textures() -> None:
    BLOCK_TEX.mkdir(parents=True, exist_ok=True)
    for i, (name, canopy, trunk, _) in enumerate(TREES):
        sprite = sapling_sprite(name, CANOPY[canopy], TRUNK[trunk], 7001 + i * 37)
        sprite.save(BLOCK_TEX / f"{name}.png")
        written.append(f"src/main/resources/assets/{NS}/textures/block/{name}.png")


def gen_models() -> None:
    for name, _, _, _ in TREES:
        # cross, the model every vanilla sapling uses - two intersecting quads.
        write(BLOCK_MODELS / f"{name}.json", {
            "parent": "minecraft:block/cross",
            "textures": {"cross": f"{NS}:block/{name}"},
        })
        write(BLOCKSTATES / f"{name}.json", {
            "variants": {"": {"model": f"{NS}:block/{name}"}},
        })
        # The item is the flat sprite, not the cross - same as vanilla.
        write(ITEM_MODELS / f"{name}.json", {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"{NS}:block/{name}"},
        })
        write(ITEM_DEFS / f"{name}.json", {
            "model": {"type": "minecraft:model", "model": f"{NS}:item/{name}"},
        })


def gen_loot() -> None:
    """A sapling drops itself, and survives an explosion."""
    for name, _, _, _ in TREES:
        write(LOOT / f"{name}.json", {
            "type": "minecraft:block",
            "pools": [{
                "rolls": 1.0,
                "conditions": [{"condition": "minecraft:survives_explosion"}],
                "entries": [{"type": "minecraft:item", "name": f"{NS}:{name}"}],
            }],
            "random_sequence": f"{NS}:blocks/{name}",
        })


def gen_tags() -> None:
    """#minecraft:saplings is what makes bone meal, composting and villagers work."""
    path = DATA.parent / "minecraft" / "tags" / "block" / "saplings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"replace": False, "values": [f"{NS}:{n}" for n, _, _, _ in TREES]},
        indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    ipath = DATA.parent / "minecraft" / "tags" / "item" / "saplings.json"
    ipath.parent.mkdir(parents=True, exist_ok=True)
    ipath.write_text(json.dumps(
        {"replace": False, "values": [f"{NS}:{n}" for n, _, _, _ in TREES]},
        indent=2) + "\n", encoding="utf-8")
    written.append(str(ipath.relative_to(ROOT)).replace("\\", "/"))


NAMES = {
    "petrified_tuning_sapling": "Petrified Tuning Sapling",
    "echo_ash_sapling": "Echo Ash Sapling",
    "amber_bough_sapling": "Amber Bough Sapling",
    "humming_sapling": "Humming Sapling",
}


def gen_lang() -> None:
    """Additive, like every other generator that touches the shared lang file."""
    existing = json.loads(LANG.read_text(encoding="utf-8")) if LANG.exists() else {}
    added = 0
    for name, title in NAMES.items():
        key = f"block.{NS}.{name}"
        if key not in existing:
            existing[key] = title
            added += 1
    LANG.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"lang: added {added} key(s)")


def main() -> int:
    gen_textures()
    gen_models()
    gen_loot()
    gen_tags()
    gen_lang()
    print(f"generated {len(written)} files for {len(TREES)} saplings")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

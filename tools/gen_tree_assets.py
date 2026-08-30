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
from gen_item_textures import Sprite, poly  # noqa: E402

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


def sapling_sprite(canopy: Material, trunk: Material, seed: int) -> Sprite:
    """A young tree: a slim stem with a rounded crown, the vanilla sapling read.

    Vanilla saplings are all the same shape and are told apart by colour alone, which is
    the right call here too - four different silhouettes would say "four different KINDS
    of thing" when they are four of the same thing.
    """
    sp = Sprite()

    crown = poly([(8.0, 1.5), (13.5, 5.0), (13.0, 9.5), (8.0, 12.0),
                  (3.0, 9.5), (2.5, 5.0)])
    sp.paint(crown, canopy, 0.56, seed, spread=0.34, light=0.30)

    # A couple of gaps punched through the canopy, so it reads as leaves rather than
    # as a solid blob at 16 pixels.
    for (x, y) in poly([(5.0, 6.0), (6.6, 7.4), (5.2, 8.4)]):
        sp.clear(x, y)
    for (x, y) in poly([(10.4, 4.6), (12.0, 6.0), (10.6, 7.0)]):
        sp.clear(x, y)

    stem = poly([(7.0, 11.0), (9.0, 11.0), (9.0, 15.0), (7.0, 15.0)])
    sp.paint(stem, trunk, 0.44, seed + 11, spread=0.26, light=0.22)

    sp.outline()
    return sp


# ---------------------------------------------------------------------------

def gen_textures() -> None:
    BLOCK_TEX.mkdir(parents=True, exist_ok=True)
    for i, (name, canopy, trunk, _) in enumerate(TREES):
        sprite = sapling_sprite(CANOPY[canopy], TRUNK[trunk], 7001 + i * 37)
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

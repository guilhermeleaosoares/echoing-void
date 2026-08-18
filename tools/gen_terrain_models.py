"""
The Echoing Void - blockstate / block model / item model JSON for the 18 new
terrain blocks from docs/spec/art_direction.json.

Companion to tools/gen_models.py, which owns the original headline blocks. This
script only ever writes files for the terrain set, so the two can be run in any
order without stepping on each other.

Every schema here was read out of the real Minecraft 26.2 client assets in
C:\\Projects\\mcref-26.2\\assets, not from memory:

  * item model definitions live in assets/<ns>/items/<id>.json and wrap the model
    as {"model": {"type": "minecraft:model", "model": "<ns>:block/<id>"}}
    (verified against items/amethyst_cluster.json and items/short_grass.json)
  * "render_type" no longer exists. Translucency is declared per-texture as
    {"force_translucent": true, "sprite": "<ns>:block/<id>"}
  * cutout foliage and cross plants just rely on the texture's own alpha
  * cross plants use parent minecraft:block/cross - NOT tinted_cross, because our
    growths carry their colour in the sprite rather than taking a biome tint
    (block/short_grass.json uses tinted_cross precisely because vanilla grass does)
  * a cluster is a cross model rotated by its facing property; the six variants
    below are the exact x/y rotations from blockstates/amethyst_cluster.json

TEXTURE CONTRACT - the sprites this script expects the texture generator to
produce under assets/echoing_void/textures/block/. Names are the block id, with
_side/_top suffixes only for the two pillars, matching the convention already set
by petrified_tuning_wood. Run with --list-textures to print them.

Run:  python tools/gen_terrain_models.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS

BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_MODELS = ASSETS / "models" / "item"
ITEM_DEFS = ASSETS / "items"
TEXTURES = ASSETS / "textures" / "block"

written: list[str] = []


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ---------------------------------------------------------------------------
# the block set
# ---------------------------------------------------------------------------

#: Opaque full cubes, one sprite each.
#:
#: Humming Crystal is here rather than in a translucent group despite
#: art_direction.json flagging it "translucent": true. The shipped sprite was
#: measured with Pillow and is 256/256 fully opaque pixels - no alpha at all - so
#: force_translucent would move it into the sorted transparency pass and cost
#: sorting work for a render that is pixel-identical to the opaque one. It gets
#: its presence from an emissive palette and light level 11 instead.
FULL_CUBES = [
    "resonant_chalk",
    "echo_slate",
    "amber_strata",
    "chalk_bricks",
    "polished_phonolite",
    "chime_sand",
    "humming_crystal",
    "amber_lichen",
    "harmonic_lantern",
]

#: Full cubes drawn translucent, declared per-texture with 26.2's force_translucent.
#: Empty for this set; kept because the helper below is the only correct way to
#: spell translucency in 26.2 and the next glassy terrain block will need it.
TRANSLUCENT_CUBES: list[str] = []

#: Nylium-style covers: a crust sprite on top, a crust-over-stone sprite on the
#: sides, and the host stone underneath. Resonance Moss ships a _side sprite whose
#: lower half measures (48, 53, 66) against raw_phonolite's (49, 54, 66), so the
#: artist drew the crust over Raw Phonolite and that is what belongs on the bottom
#: face. Amber Lichen ships no _side sprite and stays a plain cube.
COVERS = {
    "resonance_moss": {"top": "resonance_moss", "side": "resonance_moss_side",
                       "bottom": "raw_phonolite"},
}

#: Full cubes whose sprite has alpha holes; the cutout comes from the texture.
LEAF_CUBES = ["amber_resonance_leaves", "violet_resonance_leaves"]

#: Axis pillars, needing <id>_side and <id>_top.
PILLARS = ["humming_stem", "stripped_humming_stem"]

#: Cross-model growths, one sprite each.
CROSS_PLANTS = ["echo_sprout", "chime_grass", "crystal_bloom"]

#: Directional cross-model clusters, one sprite each.
CLUSTERS = ["bismuth_cluster"]


def required_textures() -> list[str]:
    """Every sprite this script's models reference, as a flat sorted list."""
    names = list(FULL_CUBES) + TRANSLUCENT_CUBES + LEAF_CUBES + CROSS_PLANTS + CLUSTERS
    for pillar in PILLARS:
        names += [f"{pillar}_side", f"{pillar}_top"]
    for faces in COVERS.values():
        names += list(faces.values())
    return sorted(set(names))


# ---------------------------------------------------------------------------
# schema helpers
# ---------------------------------------------------------------------------

def sprite(name: str, translucent: bool = False) -> dict | str:
    ref = f"{NS}:block/{name}"
    return {"force_translucent": True, "sprite": ref} if translucent else ref


def simple_state(block: str, model: str | None = None) -> None:
    write(BLOCKSTATES / f"{block}.json",
          {"variants": {"": {"model": f"{NS}:block/{model or block}"}}})


def pillar_state(block: str) -> None:
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "axis=x": {"model": f"{NS}:block/{block}_horizontal", "x": 90, "y": 90},
            "axis=y": {"model": f"{NS}:block/{block}"},
            "axis=z": {"model": f"{NS}:block/{block}_horizontal", "x": 90},
        }
    })


def cluster_state(block: str) -> None:
    """The six facings of a surface-growing cluster, per blockstates/amethyst_cluster.json.

    Waterlogged is deliberately absent: it does not change the model, and vanilla
    leaves it out of the variant keys for exactly that reason - any property not
    named in a key acts as a wildcard.
    """
    model = f"{NS}:block/{block}"
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "facing=down": {"model": model, "x": 180},
            "facing=east": {"model": model, "x": 90, "y": 90},
            "facing=north": {"model": model, "x": 90},
            "facing=south": {"model": model, "x": 90, "y": 180},
            "facing=up": {"model": model},
            "facing=west": {"model": model, "x": 90, "y": 270},
        }
    })


def cube_all(block: str, texture: str | None = None, translucent: bool = False) -> None:
    write(BLOCK_MODELS / f"{block}.json", {
        "parent": "minecraft:block/cube_all",
        "textures": {"all": sprite(texture or block, translucent)},
    })


def cube_column(block: str) -> None:
    textures = {"side": f"{NS}:block/{block}_side", "end": f"{NS}:block/{block}_top"}
    write(BLOCK_MODELS / f"{block}.json",
          {"parent": "minecraft:block/cube_column", "textures": textures})
    write(BLOCK_MODELS / f"{block}_horizontal.json",
          {"parent": "minecraft:block/cube_column_horizontal", "textures": textures})


def cube_bottom_top(block: str, top: str, side: str, bottom: str) -> None:
    write(BLOCK_MODELS / f"{block}.json", {
        "parent": "minecraft:block/cube_bottom_top",
        "textures": {
            "top": f"{NS}:block/{top}",
            "side": f"{NS}:block/{side}",
            "bottom": f"{NS}:block/{bottom}",
        },
    })


def cross(block: str) -> None:
    write(BLOCK_MODELS / f"{block}.json",
          {"parent": "minecraft:block/cross", "textures": {"cross": f"{NS}:block/{block}"}})


def block_item(item: str, model: str | None = None) -> None:
    """Item definition pointing straight at the block model - for anything cube-shaped."""
    write(ITEM_DEFS / f"{item}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:block/{model or item}"}})


def sprite_item(item: str) -> None:
    """Flat inventory sprite drawn from the BLOCK texture.

    Cross models look like a folded card in the hand, so vanilla gives grass and
    amethyst clusters a generated item model over their block sprite instead.
    """
    write(ITEM_MODELS / f"{item}.json",
          {"parent": "minecraft:item/generated", "textures": {"layer0": f"{NS}:block/{item}"}})
    write(ITEM_DEFS / f"{item}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:item/{item}"}})


# ---------------------------------------------------------------------------

def gen() -> None:
    for block in FULL_CUBES:
        cube_all(block)
        simple_state(block)
        block_item(block)

    for block in TRANSLUCENT_CUBES:
        cube_all(block, translucent=True)
        simple_state(block)
        block_item(block)

    for block, faces in COVERS.items():
        cube_bottom_top(block, faces["top"], faces["side"], faces["bottom"])
        simple_state(block)
        block_item(block)

    for block in LEAF_CUBES:
        cube_all(block)
        simple_state(block)
        block_item(block)

    for block in PILLARS:
        cube_column(block)
        pillar_state(block)
        block_item(block)

    for block in CROSS_PLANTS:
        cross(block)
        simple_state(block)
        sprite_item(block)

    for block in CLUSTERS:
        cross(block)
        cluster_state(block)
        sprite_item(block)


def report_missing_textures() -> int:
    missing = [t for t in required_textures() if not (TEXTURES / f"{t}.png").exists()]
    if missing:
        print(f"\nWARNING: {len(missing)} referenced sprite(s) not on disk yet:")
        for name in missing:
            print(f"  textures/block/{name}.png")
    return len(missing)


def main() -> int:
    if "--list-textures" in sys.argv:
        for name in required_textures():
            print(name)
        return 0

    for d in (BLOCKSTATES, BLOCK_MODELS, ITEM_MODELS, ITEM_DEFS):
        d.mkdir(parents=True, exist_ok=True)

    gen()
    print(f"generated {len(written)} json files")
    for w in written:
        print("  " + w)
    report_missing_textures()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

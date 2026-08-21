"""
The Echoing Void - blockstate / block model / item model JSON generator.

Every schema used here was read out of the real Minecraft 26.2 client assets in
C:\\Projects\\mcref-26.2\\assets, not from memory. Notable 26.2 specifics:

  * item model definitions live in assets/<ns>/items/<id>.json and wrap the model
    as {"model": {"type": "minecraft:model", "model": "<ns>:item/<id>"}}
  * "render_type" no longer exists. Translucency is declared per-texture as
    {"force_translucent": true, "sprite": "<ns>:block/<id>"} (see vanilla glass.json)
  * cutout foliage just uses cube_all and relies on the texture's alpha (azalea_leaves.json)

Run:  python tools/gen_models.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS

BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_MODELS = ASSETS / "models" / "item"
ITEM_DEFS = ASSETS / "items"

written: list[str] = []


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def simple_state(block: str, model: str | None = None) -> None:
    write(BLOCKSTATES / f"{block}.json",
          {"variants": {"": {"model": f"{NS}:block/{model or block}"}}})


def facing_state(block: str) -> None:
    """4-way horizontal facing, matching vanilla carved_pumpkin.json's mapping -
    the model's own north face is the front, so facing=north needs no rotation."""
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "facing=north": {"model": f"{NS}:block/{block}"},
            "facing=east": {"model": f"{NS}:block/{block}", "y": 90},
            "facing=south": {"model": f"{NS}:block/{block}", "y": 180},
            "facing=west": {"model": f"{NS}:block/{block}", "y": 270},
        }
    })


def pillar_state(block: str) -> None:
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "axis=x": {"model": f"{NS}:block/{block}_horizontal", "x": 90, "y": 90},
            "axis=y": {"model": f"{NS}:block/{block}"},
            "axis=z": {"model": f"{NS}:block/{block}_horizontal", "x": 90},
        }
    })


def cube_all(block: str, texture: str | None = None, translucent: bool = False) -> None:
    tex: dict | str = f"{NS}:block/{texture or block}"
    if translucent:
        tex = {"force_translucent": True, "sprite": tex}
    write(BLOCK_MODELS / f"{block}.json",
          {"parent": "minecraft:block/cube_all", "textures": {"all": tex}})


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


def cube_front(block: str, front: str, side: str, top: str) -> None:
    """A non-directional cube whose north face differs (vault door look)."""
    write(BLOCK_MODELS / f"{block}.json", {
        "parent": "minecraft:block/cube",
        "textures": {
            "particle": f"{NS}:block/{side}",
            "north": f"{NS}:block/{front}",
            "south": f"{NS}:block/{side}",
            "east": f"{NS}:block/{side}",
            "west": f"{NS}:block/{side}",
            "up": f"{NS}:block/{top}",
            "down": f"{NS}:block/{top}",
        },
    })


def block_item(item: str, model: str | None = None) -> None:
    write(ITEM_DEFS / f"{item}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:block/{model or item}"}})


def flat_item(item: str, parent: str = "minecraft:item/generated") -> None:
    write(ITEM_MODELS / f"{item}.json",
          {"parent": parent, "textures": {"layer0": f"{NS}:item/{item}"}})
    write(ITEM_DEFS / f"{item}.json",
          {"model": {"type": "minecraft:model", "model": f"{NS}:item/{item}"}})


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------

FULL_CUBES = [
    "resonant_bismuth_ore",
    "deepslate_resonant_bismuth_ore",
    "raw_phonolite",
    "phonolite_bricks",
    "null_iron_ore",
    "null_iron_block",
]

PILLARS = ["petrified_tuning_wood", "stripped_petrified_tuning_wood"]


def gen_blocks() -> None:
    for b in FULL_CUBES:
        cube_all(b)
        simple_state(b)
        block_item(b)

    # Void-Glass: translucent via the 26.2 per-texture force_translucent flag.
    cube_all("void_glass", translucent=True)
    simple_state("void_glass")
    block_item("void_glass")

    # Leaves: alpha cutout comes from the texture itself (matches azalea_leaves).
    cube_all("calcified_resonance_leaves")
    simple_state("calcified_resonance_leaves")
    block_item("calcified_resonance_leaves")

    for b in PILLARS:
        cube_column(b)
        pillar_state(b)
        block_item(b)

    cube_bottom_top("frequency_siphon", "frequency_siphon_top",
                    "frequency_siphon_side", "frequency_siphon_bottom")
    simple_state("frequency_siphon")
    block_item("frequency_siphon")

    # The anvil's model and blockstate are written by gen_effect_textures.py, which
    # gives it a real anvil silhouette instead of a cube. Only the item form is ours.
    block_item("inversion_anvil")

    cube_front("acoustic_lock_box", "acoustic_lock_box_front",
               "acoustic_lock_box_side", "acoustic_lock_box_top")
    simple_state("acoustic_lock_box")
    block_item("acoustic_lock_box")

    # The build trigger for tuners_protector - carved face on the front, plain
    # null_iron_block on every other face so a placed mask reads as "this
    # particular null-iron block", not a separate decorative item.
    cube_front("tuners_mask", "tuners_mask_front", "null_iron_block", "null_iron_block")
    facing_state("tuners_mask")
    block_item("tuners_mask")



# The portal models and blockstate live in gen_effect_textures.py: the surface is an
# animated texture now, and having two generators write the same files meant whichever
# ran last won - which silently reverted the animation to a static pane.

# ---------------------------------------------------------------------------
# items
# ---------------------------------------------------------------------------

MATERIALS = [
    "echo_weaver_spawn_egg",
    "strata_golem_spawn_egg",
    "resonance_wraith_spawn_egg",
    "chime_mote_spawn_egg",
    "tuner_shade_spawn_egg",
    "strata_burrower_spawn_egg",
    "tuner_trader_spawn_egg",
    "tuners_protector_spawn_egg",
    "drone_auroch_spawn_egg",
    "thrum_boar_spawn_egg",
    "drone_loin",
    "seared_drone_loin",
    "thrum_ribs",
    "seared_thrum_ribs",
    "resonance_shard",
    "raw_null_iron",
    "null_iron_ingot",
    "void_glass_shard",
    "bismuth_seedling",
    "harmonic_tuning_disc_alpha",
    "harmonic_tuning_disc_beta",
    "harmonic_tuning_disc_gamma",
]

HANDHELD = [
    "tuning_fork",
    "harmonic_pickaxe",
    "sonic_lance",
    "void_glass_rapier",
    "harmonic_sword",
    "harmonic_axe",
    "harmonic_shovel",
    "harmonic_hoe",
]

ARMOR = [
    "resonance_helmet",
    "resonance_chestplate",
    "resonance_leggings",
    "resonance_boots",
    "aero_stride_greaves",
]


def gen_items() -> None:
    for i in MATERIALS:
        flat_item(i)
    for i in HANDHELD:
        flat_item(i, parent="minecraft:item/handheld")
    for i in ARMOR:
        flat_item(i)


def main() -> int:
    for d in (BLOCKSTATES, BLOCK_MODELS, ITEM_MODELS, ITEM_DEFS):
        d.mkdir(parents=True, exist_ok=True)
    gen_blocks()
    gen_items()
    print(f"generated {len(written)} json files")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

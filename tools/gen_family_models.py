"""
The Echoing Void - blockstates, block models and item model definitions for every
block family variant: 21 stone cuts and 40 wood blocks.

Companion to gen_models.py (the original headline blocks) and gen_terrain_models.py
(the 18 terrain blocks). This script only ever writes files for the family set, and
it never touches the two trunks that predate it - see ev_families.owns_log - so the
three can be run in any order.

These files are generated rather than written by hand because a stairs blockstate is
40 variants and a door blockstate is 32, all of them mechanical rotations. Every
schema and every rotation below was read out of the real Minecraft 26.2 client assets
in C:\\Projects\\mcref-26.2\\assets, not from memory:

  * slab      blockstates/oak_slab.json - type=bottom/top/double, where double points
              at the model of the FULL BLOCK, not at a slab model
  * stairs    blockstates/oak_stairs.json - facing x half x shape, 40 variants.
              uvlock appears exactly when a rotation is applied and is omitted when
              both x and y are zero; that is reproduced here rather than always
              emitting it, so the output diffs cleanly against vanilla.
  * wall      blockstates/cobblestone_wall.json - multipart, "up" plus four
              connections each of which can be low or tall
  * fence     blockstates/oak_fence.json - multipart with an unconditional post
  * gate      blockstates/oak_fence_gate.json - facing x in_wall x open, uvlock always
  * trapdoor  blockstates/oak_trapdoor.json - facing x half x open, no uvlock, and the
              closed models ignore facing entirely
  * door      blockstates/oak_door.json - facing x half x hinge x open, 32 variants
  * bark      blockstates/oak_wood.json + models/block/oak_wood.json - a cube_column
              whose "end" is the trunk's SIDE sprite, so the block is bark all round

Item model definitions live in assets/<ns>/items/<id>.json and wrap a model as
{"model": {"type": "minecraft:model", "model": "..."}}. Most family pieces point at a
block model directly; fences and walls point at their _inventory model, a trapdoor at
its _bottom model, and a door at a flat generated item sprite - all verified against
the matching vanilla items/*.json.

TEXTURE CONTRACT - run with --list-textures to print every sprite these models
reference, and --missing-textures for just the ones not yet on disk. The stone cuts
and the two existing woods reuse sprites that already ship; the new sprites needed are
the two new woods' logs, all four woods' planks, and every door and trapdoor face.

Run:  python tools/gen_family_models.py
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
    bark_sprite,
    lang_entries,
    stone_cuts,
    wood_cuts,
)

ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS

BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_MODELS = ASSETS / "models" / "item"
ITEM_DEFS = ASSETS / "items"
BLOCK_TEXTURES = ASSETS / "textures" / "block"
ITEM_TEXTURES = ASSETS / "textures" / "item"
LANG = ASSETS / "lang" / "en_us.json"

written: list[str] = []
block_sprites: set[str] = set()
item_sprites: set[str] = set()


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


def block_tex(name: str) -> str:
    block_sprites.add(name)
    return f"{NS}:block/{name}"


def item_tex(name: str) -> str:
    item_sprites.add(name)
    return f"{NS}:item/{name}"


def model_ref(path: str) -> str:
    return f"{NS}:{path}"


def item_def(item: str, model_path: str) -> None:
    """assets/<ns>/items/<id>.json - what the inventory renders for this item."""
    write(ITEM_DEFS / f"{item}.json",
          {"model": {"type": "minecraft:model", "model": model_ref(model_path)}})


# ---------------------------------------------------------------------------
# rotation tables, transcribed from the vanilla blockstates
# ---------------------------------------------------------------------------

#: The y rotation each facing needs. Three different tables, because the three model
#: sets were authored pointing three different ways, and guessing one from another is
#: how a fence gate ends up facing sideways. Each is transcribed from its own vanilla
#: blockstate rather than derived:
#:   stairs and doors  - blockstates/oak_stairs.json, blockstates/oak_door.json
#:   fence gates       - blockstates/oak_fence_gate.json, authored facing south
#:   trapdoors         - blockstates/oak_trapdoor.json, authored facing north
FACING_Y = {"east": 0, "north": 270, "south": 90, "west": 180}

GATE_Y = {"south": 0, "west": 90, "north": 180, "east": 270}

TRAPDOOR_Y = {"north": 0, "east": 90, "south": 180, "west": 270}

FACINGS = ("east", "north", "south", "west")
DIRECTIONS = ("north", "east", "south", "west")

#: The y offset applied to a side model per horizontal direction, in multipart states.
SIDE_Y = {"north": 0, "east": 90, "south": 180, "west": 270}


def variant(model: str, x: int = 0, y: int = 0, uvlock: bool | None = None) -> dict:
    """One blockstate variant, omitting zero rotations the way vanilla does.

    uvlock defaults to "true when anything is rotated", which is the rule vanilla
    follows for stairs and walls. Pass it explicitly where a block breaks that rule -
    fence gates always set it, doors and trapdoors never do.
    """
    out: dict = {"model": model_ref(f"block/{model}")}
    lock = (x or y) if uvlock is None else uvlock
    if lock:
        out["uvlock"] = True
    if x:
        out["x"] = x
    if y:
        out["y"] = y
    return out


# ---------------------------------------------------------------------------
# the pieces
# ---------------------------------------------------------------------------

def slab(block: str, texture: str, double_model: str) -> None:
    """A slab, plus the full-block model its double state falls back to."""
    faces = {"bottom": block_tex(texture), "side": block_tex(texture), "top": block_tex(texture)}
    write(BLOCK_MODELS / f"{block}.json", {"parent": "minecraft:block/slab", "textures": faces})
    write(BLOCK_MODELS / f"{block}_top.json", {"parent": "minecraft:block/slab_top", "textures": faces})
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "type=bottom": {"model": model_ref(f"block/{block}")},
            "type=double": {"model": model_ref(f"block/{double_model}")},
            "type=top": {"model": model_ref(f"block/{block}_top")},
        }
    })
    item_def(block, f"block/{block}")


def stairs(block: str, texture: str) -> None:
    """Stairs: three models and the 40-variant state that rotates them."""
    faces = {"bottom": block_tex(texture), "side": block_tex(texture), "top": block_tex(texture)}
    write(BLOCK_MODELS / f"{block}.json", {"parent": "minecraft:block/stairs", "textures": faces})
    write(BLOCK_MODELS / f"{block}_inner.json",
          {"parent": "minecraft:block/inner_stairs", "textures": faces})
    write(BLOCK_MODELS / f"{block}_outer.json",
          {"parent": "minecraft:block/outer_stairs", "textures": faces})

    variants: dict[str, dict] = {}
    for facing in FACINGS:
        base_y = FACING_Y[facing]
        for half in ("bottom", "top"):
            x = 180 if half == "top" else 0
            for shape in ("inner_left", "inner_right", "outer_left", "outer_right", "straight"):
                if shape == "straight":
                    model, y = block, base_y
                else:
                    kind, side = shape.split("_")
                    model = f"{block}_{kind}"
                    # Flipping a stair to the top half mirrors it, which swaps which
                    # corner the left and right shapes turn towards - hence the
                    # opposite offsets for bottom and top.
                    if half == "bottom":
                        y = base_y - 90 if side == "left" else base_y
                    else:
                        y = base_y if side == "left" else base_y + 90
                key = f"facing={facing},half={half},shape={shape}"
                variants[key] = variant(model, x=x, y=y % 360)

    write(BLOCKSTATES / f"{block}.json", {"variants": variants})
    item_def(block, f"block/{block}")


def wall(block: str, texture: str) -> None:
    """A wall: post, low side, tall side, and an inventory model for the item."""
    faces = {"wall": block_tex(texture)}
    for suffix, parent in (
        ("_post", "minecraft:block/template_wall_post"),
        ("_side", "minecraft:block/template_wall_side"),
        ("_side_tall", "minecraft:block/template_wall_side_tall"),
        ("_inventory", "minecraft:block/wall_inventory"),
    ):
        write(BLOCK_MODELS / f"{block}{suffix}.json", {"parent": parent, "textures": faces})

    parts: list[dict] = [{"apply": variant(f"{block}_post", uvlock=False), "when": {"up": "true"}}]
    for height, suffix in (("low", "_side"), ("tall", "_side_tall")):
        for direction in DIRECTIONS:
            parts.append({
                "apply": variant(f"{block}{suffix}", y=SIDE_Y[direction], uvlock=True),
                "when": {direction: height},
            })

    write(BLOCKSTATES / f"{block}.json", {"multipart": parts})
    item_def(block, f"block/{block}_inventory")


def fence(block: str, texture: str) -> None:
    """A fence: an unconditional post plus one side per connected direction."""
    faces = {"texture": block_tex(texture)}
    for suffix, parent in (
        ("_post", "minecraft:block/fence_post"),
        ("_side", "minecraft:block/fence_side"),
        ("_inventory", "minecraft:block/fence_inventory"),
    ):
        write(BLOCK_MODELS / f"{block}{suffix}.json", {"parent": parent, "textures": faces})

    parts: list[dict] = [{"apply": variant(f"{block}_post", uvlock=False)}]
    for direction in DIRECTIONS:
        parts.append({
            "apply": variant(f"{block}_side", y=SIDE_Y[direction], uvlock=True),
            "when": {direction: "true"},
        })

    write(BLOCKSTATES / f"{block}.json", {"multipart": parts})
    item_def(block, f"block/{block}_inventory")


def fence_gate(block: str, texture: str) -> None:
    """A fence gate: four models over facing x in_wall x open."""
    faces = {"texture": block_tex(texture)}
    for suffix, parent in (
        ("", "minecraft:block/template_fence_gate"),
        ("_open", "minecraft:block/template_fence_gate_open"),
        ("_wall", "minecraft:block/template_fence_gate_wall"),
        ("_wall_open", "minecraft:block/template_fence_gate_wall_open"),
    ):
        write(BLOCK_MODELS / f"{block}{suffix}.json", {"parent": parent, "textures": faces})

    variants: dict[str, dict] = {}
    for facing in FACINGS:
        for in_wall in ("false", "true"):
            for is_open in ("false", "true"):
                suffix = "_wall" if in_wall == "true" else ""
                if is_open == "true":
                    suffix += "_open"
                key = f"facing={facing},in_wall={in_wall},open={is_open}"
                # A gate keeps uvlock even unrotated, matching vanilla: its post
                # texture must not spin with the frame.
                variants[key] = variant(f"{block}{suffix}", y=GATE_Y[facing], uvlock=True)

    write(BLOCKSTATES / f"{block}.json", {"variants": variants})
    item_def(block, f"block/{block}")


def trapdoor(block: str, texture: str) -> None:
    """A trapdoor: bottom, top and open, over facing x half x open."""
    faces = {"texture": block_tex(texture)}
    for suffix, parent in (
        ("_bottom", "minecraft:block/template_trapdoor_bottom"),
        ("_top", "minecraft:block/template_trapdoor_top"),
        ("_open", "minecraft:block/template_trapdoor_open"),
    ):
        write(BLOCK_MODELS / f"{block}{suffix}.json", {"parent": parent, "textures": faces})

    variants: dict[str, dict] = {}
    for facing in ("east", "north", "south", "west"):
        for half in ("bottom", "top"):
            for is_open in ("false", "true"):
                key = f"facing={facing},half={half},open={is_open}"
                if is_open == "true":
                    # Open, the flap stands up against one wall, so facing matters and
                    # half does not.
                    variants[key] = variant(f"{block}_open", y=TRAPDOOR_Y[facing], uvlock=False)
                else:
                    # Closed, it is a flat panel: the same model for every facing.
                    variants[key] = variant(f"{block}_{half}", uvlock=False)

    write(BLOCKSTATES / f"{block}.json", {"variants": variants})
    item_def(block, f"block/{block}_bottom")


def door(block: str) -> None:
    """A door: eight models over facing x half x hinge x open, 32 variants."""
    faces = {
        "bottom": block_tex(f"{block}_bottom"),
        "top": block_tex(f"{block}_top"),
    }
    for half in ("bottom", "top"):
        for hinge in ("left", "right"):
            for state in ("", "_open"):
                name = f"{half}_{hinge}{state}"
                write(BLOCK_MODELS / f"{block}_{name}.json",
                      {"parent": f"minecraft:block/door_{name}", "textures": faces})

    variants: dict[str, dict] = {}
    for facing in FACINGS:
        base_y = FACING_Y[facing]
        for half in ("lower", "upper"):
            model_half = "bottom" if half == "lower" else "top"
            for hinge in ("left", "right"):
                for is_open in ("false", "true"):
                    if is_open == "false":
                        model, y = f"{block}_{model_half}_{hinge}", base_y
                    else:
                        model = f"{block}_{model_half}_{hinge}_open"
                        # Opening swings the panel a quarter turn, and the two hinges
                        # swing opposite ways.
                        y = base_y + (90 if hinge == "left" else 270)
                    key = f"facing={facing},half={half},hinge={hinge},open={is_open}"
                    variants[key] = variant(model, y=y % 360, uvlock=False)

    write(BLOCKSTATES / f"{block}.json", {"variants": variants})

    # A door in the hand is a flat sprite, not a slice of the block.
    write(ITEM_MODELS / f"{block}.json",
          {"parent": "minecraft:item/generated", "textures": {"layer0": item_tex(block)}})
    item_def(block, f"item/{block}")


def cube_all(block: str, texture: str) -> None:
    faces = {"all": block_tex(texture)}
    write(BLOCK_MODELS / f"{block}.json", {"parent": "minecraft:block/cube_all", "textures": faces})
    write(BLOCKSTATES / f"{block}.json", {"variants": {"": {"model": model_ref(f"block/{block}")}}})
    item_def(block, f"block/{block}")


def pillar(block: str, side: str, end: str) -> None:
    """An axis-aligned column: one model, rotated by the axis property."""
    faces = {"end": block_tex(end), "side": block_tex(side)}
    write(BLOCK_MODELS / f"{block}.json",
          {"parent": "minecraft:block/cube_column", "textures": faces})
    write(BLOCK_MODELS / f"{block}_horizontal.json",
          {"parent": "minecraft:block/cube_column_horizontal", "textures": faces})
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "axis=x": {"model": model_ref(f"block/{block}_horizontal"), "x": 90, "y": 90},
            "axis=y": {"model": model_ref(f"block/{block}")},
            "axis=z": {"model": model_ref(f"block/{block}_horizontal"), "x": 90},
        }
    })
    item_def(block, f"block/{block}")


def bark(block: str, sprite: str) -> None:
    """Bark on all six faces.

    Vanilla's oak_wood is a plain cube_column whose "end" is the LOG'S SIDE sprite, so
    the end grain is replaced by more bark. Unlike a log it gets NO _horizontal model:
    blockstates/oak_wood.json rotates the one model for all three axes, because with
    the same sprite on every face there is no end grain that needs re-orienting. That
    is the difference between this and pillar() above, and it is deliberate.
    """
    faces = {"end": block_tex(sprite), "side": block_tex(sprite)}
    write(BLOCK_MODELS / f"{block}.json",
          {"parent": "minecraft:block/cube_column", "textures": faces})
    write(BLOCKSTATES / f"{block}.json", {
        "variants": {
            "axis=x": {"model": model_ref(f"block/{block}"), "x": 90, "y": 90},
            "axis=y": {"model": model_ref(f"block/{block}")},
            "axis=z": {"model": model_ref(f"block/{block}"), "x": 90},
        }
    })
    item_def(block, f"block/{block}")


# ---------------------------------------------------------------------------

def gen() -> None:
    for family in STONE_FAMILIES:
        cuts = stone_cuts(family)
        texture = family["base"]
        # A double slab renders as the full block it was cut from, which already has a
        # model from one of the earlier generators.
        slab(cuts["slab"], texture, double_model=family["base"])
        stairs(cuts["stairs"], texture)
        wall(cuts["wall"], texture)

    for family in WOOD_FAMILIES:
        cuts = wood_cuts(family)
        planks_texture = cuts["planks"]

        # The two new woods need their trunks; the two older ones already have models
        # from gen_models.py and gen_terrain_models.py and must not be regenerated.
        if family["owns_log"]:
            for trunk in (family["log"], family["stripped_log"]):
                pillar(trunk, side=f"{trunk}_side", end=f"{trunk}_top")

        bark(family["wood"], bark_sprite(family))
        bark(family["stripped_wood"], bark_sprite(family, stripped=True))

        cube_all(cuts["planks"], planks_texture)
        slab(cuts["slab"], planks_texture, double_model=cuts["planks"])
        stairs(cuts["stairs"], planks_texture)
        fence(cuts["fence"], planks_texture)
        fence_gate(cuts["fence_gate"], planks_texture)
        trapdoor(cuts["trapdoor"], cuts["trapdoor"])
        door(cuts["door"])


# ---------------------------------------------------------------------------

def merge_lang() -> int:
    """Add a name for every family block to en_us.json, without touching what is there.

    en_us.json is hand-maintained, so this is strictly additive: a key that already
    exists is left exactly as written, and the file's existing order is preserved with
    new keys appended. Without it all 61 blocks show up in the inventory as
    "block.echoing_void.chalk_brick_slab", and verify_resources.py fails them.
    """
    existing: dict[str, str] = {}
    if LANG.exists():
        existing = json.loads(LANG.read_text(encoding="utf-8"))

    added = {k: v for k, v in lang_entries().items() if k not in existing}
    if not added:
        return 0

    existing.update(added)
    LANG.parent.mkdir(parents=True, exist_ok=True)
    LANG.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(added)


def missing_textures() -> list[str]:
    missing = [f"textures/block/{n}.png" for n in sorted(block_sprites)
               if not (BLOCK_TEXTURES / f"{n}.png").exists()]
    missing += [f"textures/item/{n}.png" for n in sorted(item_sprites)
                if not (ITEM_TEXTURES / f"{n}.png").exists()]
    return missing


def main() -> int:
    for d in (BLOCKSTATES, BLOCK_MODELS, ITEM_MODELS, ITEM_DEFS):
        d.mkdir(parents=True, exist_ok=True)

    gen()

    if "--list-textures" in sys.argv:
        for name in sorted(block_sprites):
            print(f"block/{name}")
        for name in sorted(item_sprites):
            print(f"item/{name}")
        return 0

    missing = missing_textures()
    if "--missing-textures" in sys.argv:
        for name in missing:
            print(name)
        return 0

    added = merge_lang()
    print(f"generated {len(written)} json files, added {added} lang entries")
    for w in written:
        print("  " + w)
    if missing:
        print(f"\nWARNING: {len(missing)} referenced sprite(s) not on disk yet:")
        for name in missing:
            print("  " + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

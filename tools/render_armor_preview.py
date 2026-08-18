"""
Worn-armour preview: what each set actually looks like on a player.

The equipment sheets are painted into the UV rectangles the humanoid armour
meshes address, which makes them almost impossible to judge as flat images - a
64x32 sheet is six scattered rectangles per box. This composites them back onto
a front-facing player the way the game does, so a set can be looked at rather
than imagined.

The layout is vanilla's humanoid model, in player pixels:

    head        8 wide x 8 tall   at x 4,  y 0
    body        8 x 12            at x 4,  y 8
    arms        4 x 12            at x 0 and x 12, y 8
    legs        4 x 12            at x 4 and x 8,  y 20

and the armour comes from the two layers the game uses - layer 1 (helmet,
chestplate, boots) from textures/entity/equipment/humanoid/<asset>.png and
layer 2 (leggings) from humanoid_leggings/<asset>.png. Both are drawn over a
plain body so the armour is what the eye lands on.

This is a front orthographic view, not a game screenshot: it shows the paint,
not the lighting or the model's depth.

Run:  python tools/render_armor_preview.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

EQUIP = (ROOT / "src" / "main" / "resources" / "assets" / "echoing_void"
         / "textures" / "entity" / "equipment")
EQUIP_JSON = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "equipment"
ITEM = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "item"
OUT = ROOT / "build" / "texture_preview"

# Doll is 16 wide x 32 tall in player pixels.
DOLL_W, DOLL_H = 16, 32

# part -> (dest x, dest y, w, h, box u, box v, box w, box h, box d)
# The box numbers are vanilla's humanoid layout; the front face of a box unwraps
# to (u + d, v + d, w, h), which is the rect actually sampled below.
PARTS = [
    ("head",      4,  0, 8, 8,   0,  0, 8,  8, 8),
    ("body",      4,  8, 8, 12, 16, 16, 8, 12, 4),
    ("right_arm", 0,  8, 4, 12, 40, 16, 4, 12, 4),
    ("left_arm", 12,  8, 4, 12, 40, 16, 4, 12, 4),
    ("right_leg", 4, 20, 4, 12,  0, 16, 4, 12, 4),
    ("left_leg",  8, 20, 4, 12,  0, 16, 4, 12, 4),
]

# Which parts each equipped slot paints, and from which layer. This matters:
# the game draws only the parts belonging to slots the player is actually
# wearing, so compositing a whole sheet would show a boots-only set as a full
# suit. Layer 2 exists because leggings must not inflate the way the other
# pieces do, so it owns the lower body and the legs.
SLOT_PARTS = {
    "helmet":     (1, {"head"}),
    "chestplate": (1, {"body", "right_arm", "left_arm"}),
    "leggings":   (2, {"body", "right_leg", "left_leg"}),
    "boots":      (1, {"right_leg", "left_leg"}),
}

# What each set actually has. Aero-Stride is a single boots item, not a suit.
SETS = {
    "resonance": ("Resonance", ["helmet", "chestplate", "leggings", "boots"]),
    "knell": ("Knell", ["helmet", "chestplate", "leggings", "boots"]),
    "aero_stride": ("Aero-Stride (boots only)", ["boots"]),
}

SKIN = (150, 122, 96, 255)
SHIRT = (90, 100, 120, 255)
TROUSER = (60, 66, 84, 255)


def front_rect(u: int, v: int, w: int, h: int, d: int) -> tuple[int, int, int, int]:
    """The front ('north') face of a box in the standard cross unwrap."""
    return (u + d, v + d, w, h)


def side_rect(u: int, v: int, w: int, h: int, d: int) -> tuple[int, int, int, int]:
    """The right ('west') face - where anything drawn on the outside of a limb
    lives, which is the only place a wing or a shoulder sweep can be seen."""
    return (u, v + d, d, h)


# Side view. The player is 8 deep at the head and 4 at the body and limbs, so
# the doll is narrower and the parts overlap in x rather than sitting apart.
SIDE_PARTS = [
    ("head",      0,  0, 8, 8,   0,  0, 8,  8, 8),
    ("body",      2,  8, 4, 12, 16, 16, 8, 12, 4),
    ("right_arm", 2,  8, 4, 12, 40, 16, 4, 12, 4),
    ("right_leg", 2, 20, 4, 12,  0, 16, 4, 12, 4),
]
SIDE_W, SIDE_H = 8, 32

SIDE_SLOT_PARTS = {
    "helmet":     (1, {"head"}),
    "chestplate": (1, {"body", "right_arm"}),
    "leggings":   (2, {"body", "right_leg"}),
    "boots":      (1, {"right_leg"}),
}


def base_side() -> Image.Image:
    img = Image.new("RGBA", (SIDE_W, SIDE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 7, 7], fill=SKIN)
    d.rectangle([2, 8, 5, 19], fill=SHIRT)
    d.rectangle([2, 20, 5, 31], fill=TROUSER)
    return img


def wear_side(asset: str, slots: list[str]) -> Image.Image | None:
    """Side view - the only place anything drawn on the outside of a limb shows."""
    return _compose(asset, slots, SIDE_PARTS, SIDE_SLOT_PARTS, side_rect, base_side())


def base_doll() -> Image.Image:
    """A plain body to wear the armour, so bare skin reads as bare."""
    img = Image.new("RGBA", (DOLL_W, DOLL_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 0, 11, 7], fill=SKIN)          # head
    d.rectangle([4, 8, 11, 19], fill=SHIRT)        # body
    d.rectangle([0, 8, 3, 19], fill=SKIN)          # arms
    d.rectangle([12, 8, 15, 19], fill=SKIN)
    d.rectangle([4, 20, 11, 31], fill=TROUSER)     # legs
    return img


def layer_textures(asset: str) -> dict[int, list[Path]]:
    """Every texture each layer type declares, in draw order, from the JSON.

    This reads assets/echoing_void/equipment/<asset>.json rather than assuming
    the texture is named after the asset. 26.2 types the field as
    Map<LayerType, List<Layer>> - a layer type can carry several textures, and
    the later ones draw over the earlier ones. That is exactly how an overlay
    is expressed, and a renderer that guesses one path per asset silently drops
    every layer but the first.
    """
    meta = EQUIP_JSON / f"{asset}.json"
    out: dict[int, list[Path]] = {1: [], 2: []}
    if not meta.is_file():
        return out
    data = json.loads(meta.read_text(encoding="utf-8"))
    for key, layer in (("humanoid", 1), ("humanoid_leggings", 2)):
        for entry in data.get("layers", {}).get(key, []):
            tex = entry.get("texture", "")
            name = tex.split(":")[-1]
            folder = "humanoid" if layer == 1 else "humanoid_leggings"
            path = EQUIP / folder / f"{name}.png"
            if path.is_file():
                out[layer].append(path)
    return out


def _compose(asset: str, slots: list[str], parts, slot_parts,
             rect_fn, base: Image.Image) -> Image.Image | None:
    textures = layer_textures(asset)
    if not any(textures.values()):
        return None
    # Leggings sit under everything else, exactly as the game layers them.
    order = sorted(slots, key=lambda sl: 0 if sl == "leggings" else 1)
    doll = base
    for slot in order:
        layer, allowed = slot_parts[slot]
        for path in textures[layer]:
            sheet = Image.open(path).convert("RGBA")
            for name, dx, dy, dw, dh, u, v, bw, bh, bd in parts:
                if name not in allowed:
                    continue
                fx, fy, fw, fh = rect_fn(u, v, bw, bh, bd)
                if fx + fw > sheet.width or fy + fh > sheet.height:
                    continue
                face = sheet.crop((fx, fy, fx + fw, fy + fh))
                if name.startswith("left_"):
                    # The left limb samples the same rect mirrored, exactly as
                    # the game does - without this the plating runs the wrong
                    # way on one side and the set looks asymmetric when it is
                    # not.
                    face = face.transpose(Image.FLIP_LEFT_RIGHT)
                doll.alpha_composite(face, (dx, dy))
    return doll


def wear(asset: str, slots: list[str]) -> Image.Image | None:
    """Front view: every declared layer of every worn slot, in draw order."""
    return _compose(asset, slots, PARTS, SLOT_PARTS, front_rect, base_doll())


def label_strip(entries: list[tuple[str, Image.Image]], scale: int,
                pad: int = 14, label_h: int = 18) -> Image.Image:
    cw = max(e[1].width for e in entries) * scale + pad
    ch = max(e[1].height for e in entries) * scale + pad + label_h
    canvas = Image.new("RGBA", (cw * len(entries) + pad, ch + pad), (20, 22, 28, 255))
    d = ImageDraw.Draw(canvas)
    for i, (name, img) in enumerate(entries):
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        x = pad + i * cw
        y = pad + label_h
        canvas.alpha_composite(big, (x, y))
        d.text((x, y - 14), name, fill=(208, 216, 230, 255))
    return canvas


def item_row(names: list[str], scale: int = 6) -> Image.Image | None:
    entries = []
    for n in names:
        p = ITEM / f"{n}.png"
        if p.is_file():
            entries.append((n, Image.open(p).convert("RGBA")))
    if not entries:
        return None
    return label_strip(entries, scale)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    worn = []
    for asset, (label, slots) in SETS.items():
        img = wear(asset, slots)
        if img is None:
            print(f"  MISSING equipment sheets for {asset}")
            continue
        worn.append((label, img))
    if worn:
        out = OUT / "armor_on_player.png"
        label_strip(worn, scale=10).save(out)
        print(f"worn armour -> {out}")

    # Side view as well: anything drawn on the outside of a limb - the
    # Aero-Stride wings above all - is invisible from the front.
    sides = []
    for asset, (label, slots) in SETS.items():
        img = wear_side(asset, slots)
        if img is not None:
            sides.append((label + " (side)", img))
    if sides:
        out = OUT / "armor_on_player_side.png"
        label_strip(sides, scale=10).save(out)
        print(f"worn armour, side -> {out}")

    tools = item_row(["harmonic_sword", "harmonic_axe", "harmonic_shovel",
                      "harmonic_hoe", "harmonic_pickaxe"])
    if tools:
        out = OUT / "resonance_toolset.png"
        tools.save(out)
        print(f"toolset -> {out}")

    gear = item_row(["resonance_helmet", "resonance_chestplate",
                     "resonance_leggings", "resonance_boots",
                     "knell_helmet", "knell_chestplate",
                     "knell_leggings", "knell_boots"], scale=5)
    if gear:
        out = OUT / "armor_items.png"
        gear.save(out)
        print(f"armour items -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

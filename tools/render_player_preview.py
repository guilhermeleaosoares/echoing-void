"""
3D player-and-armour preview: a real isometric render of a humanoid wearing
each set, base layer and outer overlay both drawn from the actual equipment
sheets - not a flat paper-doll crop.

Reuses the projection, cube-face and painter's-algorithm math already proven
in render_geo_preview.py (the same technique that caught the Echo Weaver's
disconnected legs earlier this session) rather than reinventing it. What is
new here is per-texel face painting, adapted from render_structure_preview.py,
so armour detail - studs, plate courses, the Knell crest, the Aero-Stride
wingtip - survives into the render instead of being blurred into an average
face colour.

The body is a plain mannequin in Steve-like colouring (skin head and arms, a
teal shirt, blue-grey trousers), not a reproduction of any real skin texture -
armour is the point of this tool, not the character underneath it. Armour
cubes are the body's own boxes inflated by a fixed margin, exactly as vanilla
layers its armour models over the humanoid mesh, and every declared texture
layer for a slot (base, then any overlay) is composited in order, so an
overlay that only paints a few texels shows exactly where it does and nowhere
else.

Run:  python tools/render_player_preview.py
Output: build/model_preview/player_<set>.png and player_contact_sheet.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import render_geo_preview as rgp  # noqa: E402  - rotate/project/depth/cube_faces/face_uv

RES = ROOT / "src" / "main" / "resources"
EQUIP = RES / "assets" / "echoing_void" / "textures" / "entity" / "equipment"
EQUIP_JSON = RES / "assets" / "echoing_void" / "equipment"
OUT_DIR = ROOT / "build" / "model_preview"

# render_geo_preview's project() reads ITS OWN module-level CANVAS/SCALE
# (460 / 9.0), tuned for creature bones whose base sits near world y=0. This
# skeleton's legs run from y=-12 up to the head top at y=20 - reusing those
# constants unmodified anchored the whole character too low on the canvas and
# cropped the feet, which is exactly what the first render showed. This
# defines its own camera rather than trusting an import's globals to happen to
# fit a different skeleton's proportions.
CANVAS_W, CANVAS_H = 360, 460
SCALE = 10.5
COS30 = 0.8660254037844387
SIN30 = 0.5

# The vertical midpoint of the whole body (feet at y=-12, head top at y=20),
# mapped to a fixed screen row so the standing figure is centred with headroom
# for the helmet crest above and the boots below.
BODY_MID_Y = 4.0
MID_SCREEN_Y = CANVAS_H * 0.58


def project(p):
    """Isometric projection sized and anchored for this standing humanoid.

    Identical 30-degree transform to render_geo_preview.project() - the only
    change is which world point maps to which screen row, which is what
    actually determines whether the feet stay on-screen.
    """
    x, y, z = p
    sx = (x - z) * COS30
    sy = (x + z) * SIN30 - y
    mid_sy = 0.0 * SIN30 - BODY_MID_Y  # sy of the point (0, BODY_MID_Y, 0)
    return (CANVAS_W / 2 + sx * SCALE,
            MID_SCREEN_Y + (sy - mid_sy) * SCALE)


FACE_LIGHT = rgp.FACE_LIGHT  # up/north/east/south/west/down tints, unchanged


# ---------------------------------------------------------------------------
# The humanoid skeleton, in the same "1 unit = 1 texture pixel" convention the
# rest of the project's geometry uses. Matches the proportions the equipment
# sheets are already unwrapped for: legs and body 12 tall, head 8.
# ---------------------------------------------------------------------------

# name -> (origin, size, mirrored)
BODY = {
    "head":  ((-4, 12, -4), (8, 8, 8), False),
    "body":  ((-4, 0, -2), (8, 12, 4), False),
    "arm_r": ((-8, 0, -2), (4, 12, 4), False),
    "arm_l": ((4, 0, -2), (4, 12, 4), True),
    "leg_r": ((-4, -12, -2), (4, 12, 4), False),
    "leg_l": ((0, -12, -2), (4, 12, 4), True),
}

# Which body part each slot's armour covers, and the UV origin on a 64x32
# equipment sheet - the same numbers ADULT_HEAD/BODY/ARM/LEG use in
# gen_item_textures.py, so this samples the real sheets, not a re-derivation.
SLOT_PARTS = {
    "helmet":     (["head"], (0, 0, 8, 8, 8)),
    "chestplate": (["body", "arm_r", "arm_l"], None),  # body below, arms below
    "leggings":   (["body", "leg_r", "leg_l"], None),
    "boots":      (["leg_r", "leg_l"], None),
}
UV_HEAD = (0, 0, 8, 8, 8)
UV_BODY = (16, 16, 8, 12, 4)
UV_ARM = (40, 16, 4, 12, 4)
UV_LEG = (0, 16, 4, 12, 4)
PART_UV = {"head": UV_HEAD, "body": UV_BODY, "arm_r": UV_ARM, "arm_l": UV_ARM,
           "leg_r": UV_LEG, "leg_l": UV_LEG}

# Which cube each armour slot inflates. Chestplate covers the torso AND the
# upper arms in vanilla, leggings cover the torso AND the legs (the hip
# plate), so both slots touch "body" - inflate takes the larger of the two
# where they overlap, which chestplate-then-leggings draw order already gives.
SLOT_CUBES = {
    "helmet": ["head"],
    "chestplate": ["body", "arm_r", "arm_l"],
    "leggings": ["body", "leg_r", "leg_l"],
    "boots": ["leg_r", "leg_l"],
}
# World units the armour box grows over the body, in x/z (sideways) only.
# NOT in y: inflating vertically pushes an armour cube's top or bottom past
# where the neighbouring part begins - a chestplate 0.55 units taller than the
# torso pokes its top face up past the collar, where the head should occlude
# it but does not quite reach, and it renders as a floating diagonal slab
# right at the neckline. Vanilla's own armour models do not have this problem
# because each piece's geometry is hand-fitted to its neighbours; growing
# every axis by the same margin is the naive version of that, and the vertical
# axis is exactly the one where neighbouring parts already meet exactly with
# no margin to spare.
INFLATE_XZ = 0.55

SKIN = (150, 122, 96)
SHIRT = (58, 120, 118)
TROUSER = (64, 72, 96)
PART_COLOR = {"head": SKIN, "arm_r": SKIN, "arm_l": SKIN,
              "body": SHIRT, "leg_r": TROUSER, "leg_l": TROUSER}

SETS = {
    "resonance": ("Resonance", ["helmet", "chestplate", "leggings", "boots"]),
    "knell": ("Knell", ["helmet", "chestplate", "leggings", "boots"]),
    "aero_stride": ("Aero-Stride (boots only)", ["boots"]),
}


def layer_textures(asset: str) -> dict[str, list[Image.Image]]:
    """Every texture the equipment JSON declares for humanoid/humanoid_leggings,
    in draw order. Mirrors render_armor_preview.layer_textures - kept separate
    because this script projects in 3D rather than compositing flat crops."""
    meta = EQUIP_JSON / f"{asset}.json"
    out: dict[str, list[Image.Image]] = {"humanoid": [], "humanoid_leggings": []}
    if not meta.is_file():
        return out
    data = json.loads(meta.read_text(encoding="utf-8"))
    for key in out:
        for entry in data.get("layers", {}).get(key, []):
            name = entry.get("texture", "").split(":")[-1]
            path = EQUIP / ("humanoid" if key == "humanoid" else "humanoid_leggings") / f"{name}.png"
            if path.is_file():
                out[key].append(Image.open(path).convert("RGBA"))
    return out


def flat_faces(origin, size, color) -> list[tuple[float, list, tuple]]:
    """Six solid-colour faces for a plain mannequin part."""
    faces = rgp.cube_faces(origin, size)
    out = []
    for face, corners in faces.items():
        screen = [project(p) for p in corners]
        mid = sum(rgp.depth(p) for p in corners) / 4.0
        c = rgp.shade(color, FACE_LIGHT[face])
        out.append((mid, screen, c, None))  # None = flat fill, no per-texel paint
    return out


def uv_for(face: str, mirrored: bool, u: int, v: int, w: int, h: int, d: int) -> tuple[int, int, int, int]:
    """The UV rect for one cube face, mirrored east<->west for the left limb.

    Vanilla's ModelPart mirror flag swaps which side of the box a given UV
    rect maps to rather than flipping the whole sheet, so the shared arm/leg
    region reads correctly on both sides of the body. This reproduces exactly
    that swap: everywhere else the four side faces keep their own rect, but on
    a mirrored part "east" and "west" trade places.
    """
    rects = rgp.face_uv(u, v, (w, h, d))
    if mirrored and face in ("east", "west"):
        face = "west" if face == "east" else "east"
    return rects[face]


def face_quad_textured(img_layers: list[Image.Image], rect, quad, tint: float,
                        mirror_x: bool, out: Image.Image) -> None:
    """Paint one cube face texel-by-texel from one or more stacked textures.

    Layers are drawn in order (base, then any overlay) so a sparse overlay -
    the Aero-Stride wingtip is a handful of pixels on an otherwise transparent
    64x32 canvas - shows exactly where it paints and leaves the base showing
    everywhere else, the same compositing the game itself does.
    """
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = quad
    x0, y0, w, h = rect
    if w <= 0 or h <= 0:
        return
    draw = ImageDraw.Draw(out)
    ux, uy = (bx - ax) / w, (by - ay) / w
    vx, vy = (dx - ax) / h, (dy - ay) / h
    for ty in range(h):
        for tx in range(w):
            sx = x0 + (w - 1 - tx) if mirror_x else x0 + tx
            sy = y0 + ty
            color = None
            for layer in img_layers:
                if sx >= layer.width or sy >= layer.height:
                    continue
                px = layer.getpixel((sx, sy))
                if px[3] > 16:
                    color = px[:3]  # later (overlay) layers win where opaque
            if color is None:
                continue
            col = tuple(max(0, min(255, int(c * tint))) for c in color)
            x0s = ax + ux * tx + vx * ty
            y0s = ay + uy * tx + vy * ty
            draw.polygon([(x0s, y0s), (x0s + ux, y0s + uy),
                          (x0s + ux + vx, y0s + uy + vy),
                          (x0s + vx, y0s + vy)], fill=col + (255,))


def render_set(asset: str, slots: list[str]) -> Image.Image:
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (20, 22, 28, 255))

    covered = {p for s in slots for p in SLOT_CUBES.get(s, [])}

    # Pass 1: the mannequin, flat-shaded. Depth-sorted on its own so every
    # body part occludes correctly before armour is even considered.
    body_polys = []
    for name, (origin, size, mirrored) in BODY.items():
        body_polys += flat_faces(origin, size, PART_COLOR[name])
    body_polys.sort(key=lambda t: t[0])
    draw = ImageDraw.Draw(img)
    for _, screen, color, _ in body_polys:
        draw.polygon(screen, fill=color, outline=(0, 0, 0, 60))

    # Pass 2: armour. Each equipped slot's cubes are the body's own boxes
    # inflated outward, so their near faces sit at strictly larger world
    # coordinates than the body underneath - which is what makes painter's
    # algorithm put them on top without any special-cased draw order.
    armour_quads = []  # (depth, uv_rect, quad, tint, mirror_x, layers)
    for slot in slots:
        layers = layer_textures(asset)
        for part in SLOT_CUBES.get(slot, []):
            origin, size, mirrored = BODY[part]
            ox, oy, oz = origin
            sx, sy, sz = size
            iorigin = (ox - INFLATE_XZ, oy, oz - INFLATE_XZ)
            isize = (sx + 2 * INFLATE_XZ, sy, sz + 2 * INFLATE_XZ)
            u, v, w, h, d = PART_UV[part]
            faces = rgp.cube_faces(iorigin, isize)
            key = "humanoid_leggings" if slot == "leggings" else "humanoid"
            for face, corners in faces.items():
                screen = [project(p) for p in corners]
                mid = sum(rgp.depth(p) for p in corners) / 4.0
                rect = uv_for(face, mirrored, u, v, w, h, d)
                armour_quads.append((mid, rect, screen, FACE_LIGHT[face],
                                     mirrored and face in ("north", "south", "up", "down"),
                                     layers[key]))

    armour_quads.sort(key=lambda t: t[0])
    for _, rect, quad, tint, mirror_x, layers in armour_quads:
        if not layers:
            continue
        face_quad_textured(layers, rect, quad, tint, mirror_x, img)

    return img


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = []
    for asset, (label, slots) in SETS.items():
        img = render_set(asset, slots)
        d = ImageDraw.Draw(img)
        d.text((8, 8), label, fill=(210, 218, 232, 255))
        out = OUT_DIR / f"player_{asset}.png"
        img.save(out)
        images.append((label, img))
        print(f"rendered {out.relative_to(ROOT)}")

    sheet = Image.new("RGBA", (CANVAS_W * len(images), CANVAS_H), (20, 22, 28, 255))
    for i, (_, img) in enumerate(images):
        sheet.alpha_composite(img, (i * CANVAS_W, 0))
    out = OUT_DIR / "player_contact_sheet.png"
    sheet.save(out)
    print(f"rendered {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Offline preview renderer for the .geo.json creatures.

Minecraft will happily load a model whose bones are all in the wrong place, so
"the client booted" is not evidence that a creature looks like the thing it is
meant to be. This draws each model straight from its geometry - bone hierarchy,
pivots, rotations, box UVs sampled from the real entity texture - so the
silhouette can actually be looked at without launching the game.

It is a preview tool, not part of any gate: isometric projection, painter's
algorithm, flat per-face shading.

Run:  python tools/render_geo_preview.py
Output: build/model_preview/<creature>.png and contact_sheet.png
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
GEO_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "geo"
TEX_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "entity"
OUT_DIR = ROOT / "build" / "model_preview"

CANVAS = 460
SCALE = 9.0
BG = (22, 22, 26, 255)

# Relative brightness per face normal, so the box edges read without outlines.
FACE_LIGHT = {
    "up": 1.00,
    "north": 0.82,
    "east": 0.72,
    "south": 0.62,
    "west": 0.58,
    "down": 0.45,
}


# ---------------------------------------------------------------------------
# maths
# ---------------------------------------------------------------------------

def rotate(point, degrees):
    """Rotate a point about the origin, X then Y then Z."""
    x, y, z = point
    rx, ry, rz = (math.radians(d) for d in degrees)

    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy

    cy, sy = math.cos(ry), math.sin(ry)
    x, z = x * cy + z * sy, -x * sy + z * cy

    cy, sy = math.cos(rz), math.sin(rz)
    x, y = x * cy - y * sy, x * sy + y * cy

    return (x, y, z)


def bone_transform(point, bone, bones):
    """Apply this bone's rotation about its pivot, then every ancestor's."""
    chain = []
    cur = bone
    while cur is not None:
        chain.append(cur)
        cur = bones.get(cur.get("parent"))

    for b in chain:
        rot = b.get("rotation")
        if not rot or all(abs(r) < 1e-6 for r in rot):
            continue
        px, py, pz = b["pivot"]
        moved = rotate((point[0] - px, point[1] - py, point[2] - pz), rot)
        point = (moved[0] + px, moved[1] + py, moved[2] + pz)
    return point


def project(p):
    """Isometric projection. Bedrock is Y-up, so screen y is negated."""
    x, y, z = p
    sx = (x - z) * math.cos(math.radians(30))
    sy = (x + z) * math.sin(math.radians(30)) - y
    return (CANVAS / 2 + sx * SCALE, CANVAS * 0.72 + sy * SCALE)


def depth(p):
    return p[0] + p[1] + p[2]


# ---------------------------------------------------------------------------
# cube faces and UVs
# ---------------------------------------------------------------------------

def cube_faces(origin, size):
    x, y, z = origin
    w, h, d = size
    c = {
        "wnb": (x, y, z), "enb": (x + w, y, z),
        "wtb": (x, y + h, z), "etb": (x + w, y + h, z),
        "wnf": (x, y, z + d), "enf": (x + w, y, z + d),
        "wtf": (x, y + h, z + d), "etf": (x + w, y + h, z + d),
    }
    return {
        "up": (c["wtb"], c["etb"], c["etf"], c["wtf"]),
        "down": (c["wnf"], c["enf"], c["enb"], c["wnb"]),
        "north": (c["enb"], c["wnb"], c["wtb"], c["etb"]),
        "south": (c["wnf"], c["enf"], c["etf"], c["wtf"]),
        "west": (c["wnb"], c["wnf"], c["wtf"], c["wtb"]),
        "east": (c["enf"], c["enb"], c["etb"], c["etf"]),
    }


def face_uv(u, v, size):
    """Bedrock box unwrap: the standard cross layout."""
    w, h, d = (int(round(s)) for s in size)
    return {
        "up": (u + d, v, w, d),
        "down": (u + d + w, v, w, d),
        "west": (u, v + d, d, h),
        "north": (u + d, v + d, w, h),
        "east": (u + d + w, v + d, d, h),
        "south": (u + d + w + d, v + d, w, h),
    }


def sample(tex, rect, fallback):
    """Average the opaque pixels of a face's UV rect."""
    if tex is None:
        return fallback
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return fallback
    total = [0, 0, 0]
    n = 0
    px = tex.load()
    for j in range(max(0, y), min(tex.height, y + h)):
        for i in range(max(0, x), min(tex.width, x + w)):
            r, g, b, a = px[i, j]
            if a > 0:
                total[0] += r
                total[1] += g
                total[2] += b
                n += 1
    if n == 0:
        return fallback
    return (total[0] // n, total[1] // n, total[2] // n)


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color) + (255,)


# ---------------------------------------------------------------------------

def render(path: Path) -> Image.Image:
    data = json.loads(path.read_text(encoding="utf-8"))
    geo = data["minecraft:geometry"][0]
    bones = {b["name"]: b for b in geo["bones"]}

    name = path.name.replace(".geo.json", "")
    tex_path = TEX_DIR / f"{name}.png"
    tex = Image.open(tex_path).convert("RGBA") if tex_path.is_file() else None
    fallback = (120, 130, 145)

    polys = []
    for bone in geo["bones"]:
        for cube in bone.get("cubes", []) or []:
            faces = cube_faces(cube["origin"], cube["size"])
            uvs = face_uv(int(cube["uv"][0]), int(cube["uv"][1]), cube["size"])
            for face, corners in faces.items():
                world = [bone_transform(c, bone, bones) for c in corners]
                screen = [project(p) for p in world]
                mid = sum(depth(p) for p in world) / 4.0
                color = shade(sample(tex, uvs[face], fallback), FACE_LIGHT[face])
                polys.append((mid, screen, color))

    polys.sort(key=lambda t: t[0])

    img = Image.new("RGBA", (CANVAS, CANVAS), BG)
    draw = ImageDraw.Draw(img)
    for _, screen, color in polys:
        draw.polygon(screen, fill=color, outline=(0, 0, 0, 70))

    draw.text((8, 8), f"{name}  ({len(geo['bones'])} bones)", fill=(190, 200, 210, 255))
    return img


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(GEO_DIR.glob("*.geo.json"))
    if not files:
        print("no geo models found")
        return 1

    images = []
    for f in files:
        img = render(f)
        out = OUT_DIR / f.name.replace(".geo.json", ".png")
        img.save(out)
        images.append(img)
        print(f"rendered {out.relative_to(ROOT)}")

    sheet = Image.new("RGBA", (CANVAS * len(images), CANVAS), BG)
    for i, img in enumerate(images):
        sheet.alpha_composite(img, (i * CANVAS, 0))
    sheet.save(OUT_DIR / "contact_sheet.png")
    print(f"rendered {(OUT_DIR / 'contact_sheet.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

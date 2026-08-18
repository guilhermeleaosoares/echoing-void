"""
Offline isometric renderer for the jigsaw structure pieces.

Draws a .nbt template without launching the game, so a structure's shape can be
judged before spending a world load on it. The complaint that started this was
"looks like a 5 year old drew it - no flow, bridges lead to walls, flat roofs,
floating leaves and lanterns", and every one of those is a thing you can see in
a picture and cannot see in a JSON diff.

Each block is drawn as an isometric cube carrying its real 16x16 block
texture, one texel per screen pixel, so brick coursing, plank grain and ore
speckle all survive into the picture. Blocks are painted back-to-front in screen
order, which is what makes them occlude correctly.

Run:  python tools/render_structure_preview.py [structure_dir ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from ev_nbt import read_file  # noqa: E402

RES = ROOT / "src" / "main" / "resources"
STRUCT_DIR = RES / "data" / "echoing_void" / "structure"
BLOCK_TEX = RES / "assets" / "echoing_void" / "textures" / "block"
VANILLA_TEX = Path("C:/Projects/mcref-26.2/assets/assets/minecraft/textures/block")
OUT_DIR = ROOT / "build" / "structure_preview"

# Half-width and half-height of one cube's top face. A 2:1 ratio is the
# standard isometric cell and keeps the cubes reading as cubes.
HW, HH = 8, 4
LIFT = 9  # vertical screen distance between stacked blocks

_tex_cache = {}

# Blocks whose sprite is named nothing like the block, or lives outside
# textures/block entirely.
OVERRIDE = {
    "campfire": ("campfire_log_lit",),
    "soul_campfire": ("soul_campfire_log_lit", "campfire_log_lit"),
    "chest": ("oak_planks",),
    "trapped_chest": ("oak_planks",),
    "barrel": ("barrel_side",),
    "lantern": ("lantern",),
    "soul_lantern": ("soul_lantern",),
    "chain": ("chain",),
    "iron_bars": ("iron_bars",),
}

# Last resort for blocks that render from an entity model or a non-block sheet,
# so they still occupy space in the picture instead of leaving a hole.
FALLBACK = {
    "chest": (140, 100, 52),
    "trapped_chest": (140, 100, 52),
    "chain": (60, 64, 74),
}

AIR = ("air", "cave_air", "void_air", "structure_void")


def _load(root: Path, stem: str):
    path = root / (stem + ".png")
    if not path.is_file():
        return None
    img = Image.open(path).convert("RGBA")
    # Animated textures are a vertical strip of frames; only the first is
    # representative of the block at rest.
    if img.height > img.width:
        img = img.crop((0, 0, img.width, img.width))
    if img.width != 16:
        img = img.resize((16, 16), Image.NEAREST)
    if not any(px[3] > 32 for px in img.getdata()):
        return None
    return img


def texture(block_id: str):
    """The block's 16x16 sprite, or None for air and anything unresolvable.

    Returning the real sprite rather than an average colour is the whole point:
    at one texel per pixel the render shows the actual brick coursing, plank
    grain and ore speckle, so the picture can be judged as the build rather
    than as a massing study.
    """
    if block_id in _tex_cache:
        return _tex_cache[block_id]

    ns, _, name = block_id.partition(":")
    if not name:
        ns, name = "minecraft", ns
    name = name.split("[")[0]
    if name in AIR:
        _tex_cache[block_id] = None
        return None

    roots = [BLOCK_TEX] if ns == "echoing_void" else [VANILLA_TEX]

    if name in OVERRIDE:
        for root in roots:
            for stem in OVERRIDE[name]:
                img = _load(root, stem)
                if img is not None:
                    _tex_cache[block_id] = img
                    return img
        col = FALLBACK.get(name)
        img = Image.new("RGBA", (16, 16), col + (255,)) if col else None
        _tex_cache[block_id] = img
        return img

    stems = [name]
    for suffix in ("_stairs", "_slab", "_wall", "_fence_gate", "_fence"):
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            # _planks first: every wooden cut draws from its planks sprite.
            stems += [base + "_planks", base, base + "s", base + "_block"]
    if name.endswith("_door"):
        stems.append(name + "_bottom")
    stems += [name + "_side", name + "_top", name + "_front"]

    for root in roots:
        for stem in stems:
            img = _load(root, stem)
            if img is not None:
                _tex_cache[block_id] = img
                return img

    _tex_cache[block_id] = None
    return None


def shade(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(v * f))) for v in c)


# ---------------------------------------------------------------------------
# Block shapes
#
# Drawing every block as a full cube is what made the first pass of these
# renders look blocky and stepped: the outpost roofs are built from stairs and
# the observatory from slabs, and a cube renderer flattens all of that back
# into a staircase of boxes. Each shape below is a list of axis-aligned boxes
# in unit block coordinates, ((x0, y0, z0), (x1, y1, z1)), and the palette's
# own block state decides which one a block gets.
# ---------------------------------------------------------------------------

FULL = [((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))]


def slab_boxes(props):
    kind = (props or {}).get("type", "bottom")
    if kind == "double":
        return FULL
    if kind == "top":
        return [((0.0, 0.5, 0.0), (1.0, 1.0, 1.0))]
    return [((0.0, 0.0, 0.0), (1.0, 0.5, 1.0))]


def stair_boxes(props):
    """A slab plus the quarter step, placed by facing and half.

    Vanilla stairs also have inner/outer corner shapes; those are ignored here
    because at this scale the straight form reads the same and the corner cases
    would only add ways to be subtly wrong.
    """
    props = props or {}
    facing = props.get("facing", "north")
    top = props.get("half", "bottom") == "top"

    if top:
        base = ((0.0, 0.5, 0.0), (1.0, 1.0, 1.0))
        step_y = (0.0, 0.5)
    else:
        base = ((0.0, 0.0, 0.0), (1.0, 0.5, 1.0))
        step_y = (0.5, 1.0)

    # The step sits on the side the stair faces away from, which is the side a
    # player walks up towards.
    if facing == "north":
        span = ((0.0, 0.0), (1.0, 0.5))
    elif facing == "south":
        span = ((0.0, 0.5), (1.0, 1.0))
    elif facing == "west":
        span = ((0.0, 0.0), (0.5, 1.0))
    else:  # east
        span = ((0.5, 0.0), (1.0, 1.0))

    (x0, z0), (x1, z1) = span
    step = ((x0, step_y[0], z0), (x1, step_y[1], z1))
    return [base, step]


def post_boxes(width):
    h = width / 2.0
    return [((0.5 - h, 0.0, 0.5 - h), (0.5 + h, 1.0, 0.5 + h))]


def shape_for(name, props):
    """Boxes for one palette entry, from its id and block state."""
    bare = name.split(":")[-1]
    if bare.endswith("_slab"):
        return slab_boxes(props)
    if bare.endswith("_stairs"):
        return stair_boxes(props)
    if bare.endswith("_fence_gate"):
        return [((0.0, 0.3, 0.375), (1.0, 1.0, 0.625))]
    if bare.endswith("_fence"):
        return post_boxes(0.25)
    if bare.endswith("_wall"):
        return post_boxes(0.5)
    if bare.endswith("_pane") or bare == "iron_bars":
        return [((0.0, 0.0, 0.4375), (1.0, 1.0, 0.5625))]
    if bare.endswith(("_trapdoor",)):
        return [((0.0, 0.0, 0.0), (1.0, 0.1875, 1.0))]
    if bare.endswith("_door"):
        return [((0.0, 0.0, 0.0), (1.0, 1.0, 0.1875))]
    if bare in ("lantern", "soul_lantern"):
        return [((0.3125, 0.0, 0.3125), (0.6875, 0.5625, 0.6875))]
    if bare == "chain":
        return post_boxes(0.25)
    if bare in ("campfire", "soul_campfire"):
        return [((0.0, 0.0, 0.0), (1.0, 0.4375, 1.0))]
    if bare in ("chest", "trapped_chest"):
        return [((0.0625, 0.0, 0.0625), (0.9375, 0.875, 0.9375))]
    if bare.endswith("_torch") or bare == "torch":
        return [((0.4375, 0.0, 0.4375), (0.5625, 0.625, 0.5625))]
    return FULL


def face_quad(img, quad, tint, out):
    """Paste a 16x16 sprite into a parallelogram, one texel at a time.

    A cube face in this projection is a parallelogram, so a texel maps to a
    small parallelogram too. Drawing each as a filled polygon avoids the seams
    a per-pixel affine transform leaves at these sizes, and keeps the result
    crisp rather than resampled.
    """
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = quad
    d = ImageDraw.Draw(out)
    n = 16
    # Edge vectors of the quad: u along a->b, v along a->d.
    ux, uy = (bx - ax) / n, (by - ay) / n
    vx, vy = (dx - ax) / n, (dy - ay) / n
    for ty in range(n):
        for tx in range(n):
            px = img.getpixel((tx, ty))
            if px[3] <= 32:
                continue
            col = tuple(max(0, min(255, int(c * tint))) for c in px[:3])
            x0 = ax + ux * tx + vx * ty
            y0 = ay + uy * tx + vy * ty
            d.polygon([(x0, y0),
                       (x0 + ux, y0 + uy),
                       (x0 + ux + vx, y0 + uy + vy),
                       (x0 + vx, y0 + vy)], fill=col + (255,))


def draw_box(out, tex, ox, oy, px, py, pz, box):
    """Draw one axis-aligned sub-box of a block in the isometric projection.

    Coordinates inside the box are unit fractions of a block, so a slab is the
    same code as a full cube with a different y1. The three visible faces are
    tinted apart; without that the render collapses into a silhouette however
    good the textures are.
    """
    (bx0, by0, bz0), (bx1, by1, bz1) = box

    def screen(fx, fy, fz):
        wx, wy, wz = px + fx, py + fy, pz + fz
        return (ox + (wx - wz) * HW,
                oy + (wx + wz) * HH - wy * LIFT)

    # Top face: the y1 plane, seen from above.
    top = (screen(bx0, by1, bz0), screen(bx1, by1, bz0),
           screen(bx1, by1, bz1), screen(bx0, by1, bz1))
    # The +z face, which lands on the screen-left side of the cube.
    left = (screen(bx0, by1, bz1), screen(bx1, by1, bz1),
            screen(bx1, by0, bz1), screen(bx0, by0, bz1))
    # The +x face, on the screen-right side.
    right = (screen(bx1, by1, bz1), screen(bx1, by1, bz0),
             screen(bx1, by0, bz0), screen(bx1, by0, bz1))

    face_quad(tex, left, 0.62, out)
    face_quad(tex, right, 0.84, out)
    face_quad(tex, top, 1.14, out)


def render(nbt_path: Path):
    root = read_file(nbt_path)
    data = root.get("value", root)
    palette = data.get("palette") or []
    blocks = data.get("blocks") or []
    size = data.get("size") or [0, 0, 0]
    if not blocks:
        return None

    names = [p.get("Name", "minecraft:air") for p in palette]
    sprites = [texture(n) for n in names]
    shapes = [shape_for(p.get("Name", "minecraft:air"), p.get("Properties"))
              for p in palette]

    # A palette entry that resolves to no sprite is skipped when drawing, which
    # looks exactly like a gap in the build. Report them, so an unresolved
    # texture is never mistaken for a floating block.
    unresolved = sorted({n for n, t in zip(names, sprites)
                         if t is None and not any(n.endswith(a) for a in AIR)})
    if unresolved:
        print("    NOTE unresolved texture(s), drawn as gaps: " + ", ".join(unresolved))

    sx, sy, sz = (int(v) for v in size)

    width = (sx + sz) * HW + 32
    height = (sx + sz) * HH + sy * LIFT + 32
    img = Image.new("RGBA", (width, height), (18, 20, 26, 255))

    ox = sz * HW + 16
    oy = sy * LIFT + 16

    # Painter's algorithm: draw far blocks first. Larger x+z is nearer the
    # viewer, and within a column higher y is drawn later so it sits on top.
    def key(entry):
        px, py, pz = (int(v) for v in entry["pos"])
        return (px + pz, py, px)

    # Occlusion culling. Drawing is per-texel, so an interior block costs the
    # same 768 polygons as a visible one and is then painted over completely.
    # In this projection the camera sits toward +x, +y and +z, so exactly three
    # faces can ever be seen and a block with solid neighbours on all three is
    # invisible no matter what is drawn.
    #
    # Only FULL cubes count as occluders: a slab or a stair leaves a gap its
    # neighbour shows through, and treating one as solid would cull blocks that
    # are genuinely visible.
    solid = set()
    for e in blocks:
        st = int(e["state"])
        if st >= len(sprites) or sprites[st] is None:
            continue
        if shapes[st] is not FULL:
            continue
        solid.add((int(e["pos"][0]), int(e["pos"][1]), int(e["pos"][2])))

    def hidden(px, py, pz):
        return ((px + 1, py, pz) in solid
                and (px, py + 1, pz) in solid
                and (px, py, pz + 1) in solid)

    drawn = 0
    culled = 0
    for entry in sorted(blocks, key=key):
        state = int(entry["state"])
        tex = sprites[state] if state < len(sprites) else None
        if tex is None:
            continue
        px, py, pz = (int(v) for v in entry["pos"])
        if hidden(px, py, pz):
            culled += 1
            continue
        for box in shapes[state]:
            draw_box(img, tex, ox, oy, px, py, pz, box)
        drawn += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / (nbt_path.parent.name + "__" + nbt_path.stem + ".png")
    img.save(out)
    print("  %s/%s: %dx%dx%d, %d drawn (%d hidden), %d palette -> %s"
          % (nbt_path.parent.name, nbt_path.name, sx, sy, sz,
             drawn, culled, len(palette), out.name))
    return out


def sheet(images: list[Path], out: Path, columns: int = 3) -> None:
    """Tile the individual renders so a whole structure reads in one look."""
    if not images:
        return
    tiles = [Image.open(p).convert("RGBA") for p in images]
    cw = max(t.width for t in tiles) + 12
    ch = max(t.height for t in tiles) + 26
    rows = (len(tiles) + columns - 1) // columns
    canvas = Image.new("RGBA", (cw * columns, ch * rows), (12, 13, 17, 255))
    d = ImageDraw.Draw(canvas)
    for i, (tile, path) in enumerate(zip(tiles, images)):
        x = (i % columns) * cw + 6
        y = (i // columns) * ch + 20
        canvas.paste(tile, (x, y), tile)
        d.text((x, y - 14), path.stem.split("__")[-1], fill=(200, 210, 225, 255))
    canvas.save(out)
    print(f"contact sheet -> {out}")


def main() -> int:
    targets = sys.argv[1:]
    dirs = ([STRUCT_DIR / t for t in targets] if targets
            else sorted(p for p in STRUCT_DIR.iterdir() if p.is_dir()))
    for d in dirs:
        if not d.is_dir():
            print(f"  skip {d}: not a directory")
            continue
        print(f"{d.name}:")
        made = [r for r in (render(p) for p in sorted(d.glob("*.nbt"))) if r]
        sheet(made, OUT_DIR / f"{d.name}_sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

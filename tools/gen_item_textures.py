"""
The Echoing Void - item, tool, armour and equipment texture generator.

Rewritten from scratch after player feedback that the icons "look strange in
the hotbar" and read as abstract blobs. The old generator obeyed a 4-6 indexed
colour rule that has since been revoked; that rule is what made every sprite
flat and outline-less.

The conventions below were measured off the real 26.2 client assets
(assets/minecraft/textures/item/*.png) rather than recalled, and each is
reproduced here in our own palette with our own pixels. What is borrowed is
structure, not pixel data - nothing is traced or recoloured.

  * colour budget - vanilla 16x16 item sprites carry 7-11 distinct opaque
    colours (iron_ingot 8, amethyst_shard 7, iron_pickaxe 9, diamond_sword 11,
    iron_helmet 7, netherite_ingot 10). Every material here is a seven-step
    ramp and a sprite mixes two or three of them, landing in the same band.

  * two-tone outline - the single convention whose absence made the old icons
    wrong. Vanilla outlines a silhouette with TWO values of the item's own
    family: a mid-dark on edges facing the key light (up / left) and the
    family's darkest tone on edges facing away (down / right). iron_pickaxe
    uses #444444 against #181818; netherite_helmet #241F20 against #171111.
    Never pure black, and never absent.

  * key light - top-left on every sprite, via ev_palette.key_light_factor.

  * tool geometry - vanilla tools run bottom-left to top-right. The iron
    pickaxe handle is a three-pixel diagonal from (2,14) to (10,5) of which
    only the centre pixel is fill and the flanks are outline; its head is a
    two-pixel arc from (5,3) round to (14,11), roughly a third of the field.
    The diamond sword blade is a three-pixel diagonal from (5,10) to (15,0)
    with a perpendicular guard across rows 6-12 and a grip below it.

  * armour geometry - the four iron armour icons are the strongest readability
    convention in the game, so the span tables here stay close to the measured
    vanilla silhouettes (helmet dome plus cheek guards, chestplate with
    detached pauldrons, leggings splitting into two shafts at row 7, boots with
    an outward toe). All the identity comes from the paint, not the outline.

  * equipment sheets - the worn-armour layers are painted into the UV
    rectangles the armour meshes actually address. Those rectangles are derived
    here from the same box-unwrap arithmetic the game uses (see box_faces), so
    nothing is guessed and nothing is lifted from a vanilla sheet. Baby sheets
    are 64x64 because LayerDefinitions builds the baby armour meshes at 64x64.

Run:  python tools/gen_item_textures.py            regenerate every texture
      python tools/gen_item_textures.py --preview  also build the contact sheets
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from ev_vanilla_forms import levels as _lv  # noqa: F401
import ev_vanilla_forms as vf
from ev_palette import (  # noqa: E402
    RGBA,
    fbm,
    key_light_factor,
    mix,
    parse_hex,
    shift,
    unique_colors,
)

ROOT = TOOLS.parent
NS = "echoing_void"
TEX = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures"
ITEM_DIR = TEX / "item"
EQUIP = TEX / "entity" / "equipment"
PREVIEW_DIR = ROOT / "build" / "texture_preview"

SIZE = 16


# ---------------------------------------------------------------------------
# Palette
#
# Every colour in this file is built as shift(mix(anchor_a, anchor_b, k/16),
# s/16) from two anchors named in docs/spec/art_direction.json. That is exactly
# the continuum tools/verify_textures.py authorises, so palette adherence holds
# by construction rather than by inspection.
# ---------------------------------------------------------------------------

ANCHOR = {
    "void_black": "#0B0D12", "void_shadow": "#14161D",
    "ph_dark": "#1C1D21", "ph_mid": "#3B4252", "ph_light": "#4C566A", "ph_pale": "#6E7B94",
    "chalk_shadow": "#8794AB", "chalk_mid": "#A8B4C8", "chalk_light": "#C9D3E2",
    "chalk_hi": "#DCE3EE",
    "amber_dark": "#6B4E2A", "amber_mid": "#8A6A3C", "amber_light": "#C89B4A",
    "amber_hi": "#E8C87A",
    "bis_deep": "#0B7A8C", "bis_mid": "#3FD0E0", "bis_bright": "#00E5FF", "bis_gold": "#FFD700",
    "arc_deep": "#3A1D47", "arc_mid": "#5A2E6B", "arc_light": "#B14A9E", "arc_bright": "#FF007F",
    "ni_black": "#08080A", "ni_dark": "#1A1A24", "ni_mid": "#2A2A38",
    "vg_ink": "#0F0F14", "vg_blue": "#5E81AC", "ink": "#2B2D42",
}


def col(a: str, b: str, k: int = 0, s: int = 0) -> RGBA:
    """Blend anchor `a` toward anchor `b` by k/16, then shade by s/16.

    k and s are integers because the palette gate rebuilds its legal colour set
    on exactly that lattice; staying on it means no generated colour can drift
    off the art direction.
    """
    base = mix(parse_hex(ANCHOR[a])[:3] + (255,), parse_hex(ANCHOR[b])[:3] + (255,), k / 16.0)
    return shift(base, s / 16.0)


def luminance(c: RGBA) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


class Material:
    """A named ramp: two outline tones followed by a lit-surface ramp.

    colors[0] is the darkest tone, used on silhouette edges that face away from
    the key light; colors[1] is the lighter outline used on edges that face
    into it; colors[2:] is the surface ramp, dark to light. Splitting the
    outline in two is what gives an icon the rounded, lit look vanilla has
    instead of the sticker look a single flat outline produces.
    """

    def __init__(self, name: str, colors: list[RGBA]):
        self.name = name
        self.colors = colors
        for i in range(1, len(colors)):
            if luminance(colors[i]) <= luminance(colors[i - 1]):
                raise ValueError(f"{name}: ramp entry {i} is not brighter than {i - 1}")

    @property
    def dark(self) -> int:
        return 0

    @property
    def rim(self) -> int:
        return 1

    def tone(self, level: float) -> int:
        """Map a 0..1 surface level onto the interior part of the ramp."""
        level = max(0.0, min(1.0, level))
        lo, hi = 2, len(self.colors) - 1
        return lo + int(round(level * (hi - lo)))


NULL_IRON = Material("null_iron", [
    col("ni_black", "ni_black"),
    col("void_black", "ni_dark", 8),
    col("ni_dark", "ni_mid", 8),
    col("ni_mid", "ph_mid", 8),
    col("ph_mid", "ph_light", 6),
    col("ph_light", "ph_pale", 11),
    col("ph_pale", "chalk_mid", 8),
])

# Petrified tuning wood: the warm handle stock. Vanilla's single strongest tool
# convention is a warm handle against a cold head - iron_pickaxe pairs #896727
# wood with #D8D8D8 steel - and without it a dark head on a dark haft reads as
# one undifferentiated stick in the hotbar.
TUNING_WOOD = Material("tuning_wood", [
    col("amber_dark", "void_black", 10),
    col("amber_dark", "void_shadow", 4),
    col("amber_dark", "amber_dark"),
    col("amber_dark", "amber_mid", 10),
    col("amber_mid", "amber_light", 8),
    col("amber_light", "amber_hi", 7),
])

BISMUTH = Material("bismuth", [
    col("bis_deep", "void_black", 12),
    col("bis_deep", "void_black", 6),
    col("bis_deep", "bis_deep"),
    col("bis_deep", "bis_mid", 8),
    col("bis_mid", "bis_mid"),
    col("bis_bright", "bis_bright"),
    col("bis_mid", "chalk_hi", 11),
])

VOID_GLASS = Material("void_glass", [
    col("vg_ink", "ph_dark", 5),
    col("ph_dark", "ph_mid", 8),
    col("ph_mid", "vg_blue", 7),
    col("vg_blue", "vg_blue"),
    col("vg_blue", "chalk_light", 8),
    col("chalk_light", "chalk_light"),
    col("chalk_hi", "chalk_hi"),
])

SLATE = Material("slate", [
    col("ph_dark", "void_black", 8),
    col("ph_dark", "ph_dark"),
    col("ph_dark", "ph_mid", 9),
    col("ph_mid", "ph_mid"),
    col("ph_mid", "ph_light", 10),
    col("ph_light", "ph_pale", 9),
    col("ph_pale", "chalk_shadow", 10),
])

AMBER = Material("amber", [
    col("amber_dark", "void_black", 9),
    col("amber_dark", "void_shadow", 5),
    col("amber_dark", "amber_dark"),
    col("amber_dark", "amber_mid", 9),
    col("amber_mid", "amber_light", 9),
    col("amber_light", "amber_hi", 9),
    col("bis_gold", "bis_gold"),
])

ARCANE = Material("arcane", [
    col("arc_deep", "void_black", 9),
    col("arc_deep", "arc_deep"),
    col("arc_deep", "arc_mid", 10),
    col("arc_mid", "arc_light", 6),
    col("arc_light", "arc_light"),
    col("arc_bright", "chalk_light", 4),
    col("arc_light", "chalk_light", 10),
])

# Gold is the mod's specular note: one or two pixels on an item, never a fill.
GOLD = Material("gold", [
    col("amber_dark", "void_black", 8),
    col("amber_dark", "amber_mid", 8),
    col("amber_light", "amber_light"),
    col("bis_gold", "bis_gold"),
])


# ---------------------------------------------------------------------------
# Drawing surface
# ---------------------------------------------------------------------------

Point = tuple[float, float]
Mask = set[tuple[int, int]]


class Sprite:
    """A pixel canvas that remembers which material owns each pixel.

    Keeping the material association until export is what lets the outline pass
    darken each silhouette edge into the right family: a cyan crystal edge goes
    to deep teal, a null iron edge goes to near-black, and no sprite ends up
    ringed in a colour that belongs to something else.
    """

    def __init__(self, w: int = SIZE, h: int = SIZE):
        self.w, self.h = w, h
        self.cell: dict[tuple[int, int], tuple[Material, int]] = {}
        self.locked: set[tuple[int, int]] = set()

    def put(self, x: int, y: int, mat: Material, idx: int, lock: bool = False) -> None:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        self.cell[(x, y)] = (mat, max(0, min(len(mat.colors) - 1, idx)))
        if lock:
            self.locked.add((x, y))
        else:
            self.locked.discard((x, y))

    def clear(self, x: int, y: int) -> None:
        self.cell.pop((x, y), None)
        self.locked.discard((x, y))

    def opaque(self, x: int, y: int) -> bool:
        return (x, y) in self.cell

    def paint(self, mask: Mask, mat: Material, base: float, seed: int,
              spread: float = 0.30, light: float = 0.26) -> None:
        """Fill a mask with a lit, mottled surface in one material.

        `base` is the mid surface level; the top-left key light pushes it up by
        about `light` and the mottle adds plus or minus half `spread`, so no
        region is ever a flat fill.
        """
        for (x, y) in mask:
            n = fbm(x * 1.9, y * 1.9, seed, octaves=2)
            level = base + light * (key_light_factor(x, y, SIZE) / 1.4142) + spread * (n - 0.5)
            self.put(x, y, mat, mat.tone(level))

    def stamp(self, points, mat: Material, level: float, lock: bool = True) -> None:
        """Place explicit accent pixels at a fixed ramp level."""
        idx = mat.tone(level)
        for (x, y) in points:
            self.put(int(x), int(y), mat, idx, lock)

    def outline(self) -> None:
        """Apply the vanilla two-tone silhouette outline.

        An edge pixel whose open neighbours lie mostly down or right faces away
        from the key light and takes the family's darkest tone; one whose open
        neighbours lie mostly up or left takes the lighter outline tone. Ties go
        by position relative to the silhouette's centre, which is what vanilla
        does around the rounded bottom of an ingot.
        """
        edges: list[tuple[int, int, int]] = []
        for (x, y) in self.cell:
            if (x, y) in self.locked:
                continue
            openness = 0
            touched = False
            for dx, dy, w in ((1, 0, 1), (0, 1, 1), (-1, 0, -1), (0, -1, -1)):
                if not self.opaque(x + dx, y + dy):
                    openness += w
                    touched = True
            if touched:
                edges.append((x, y, openness))

        if not edges:
            return
        cx = sum(x for x, _, _ in edges) / len(edges)
        cy = sum(y for _, y, _ in edges) / len(edges)
        for x, y, openness in edges:
            mat, _ = self.cell[(x, y)]
            if openness > 0:
                idx = mat.dark
            elif openness < 0:
                idx = mat.rim
            else:
                idx = mat.dark if (x - cx) + (y - cy) > 0 else mat.rim
            self.cell[(x, y)] = (mat, idx)

    def image(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        px = img.load()
        for (x, y), (mat, idx) in self.cell.items():
            px[x, y] = mat.colors[idx]
        return img

    def save(self, path: Path) -> Image.Image:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = self.image()
        img.save(path, "PNG", optimize=True)
        return img


# ---------------------------------------------------------------------------
# Geometry helpers - all sample at pixel centres so shapes stay crisp
# ---------------------------------------------------------------------------

def spans(table: dict[int, list[tuple[int, int]]]) -> Mask:
    """Turn {row: [(x0, x1), ...]} into a pixel mask."""
    out: Mask = set()
    for y, runs in table.items():
        for x0, x1 in runs:
            for x in range(x0, x1 + 1):
                out.add((x, y))
    return out


def rect(x0: int, y0: int, w: int, h: int) -> Mask:
    return {(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)}


def poly(points: list[Point], w: int = SIZE, h: int = SIZE) -> Mask:
    """Even-odd polygon fill sampled at pixel centres."""
    out: Mask = set()
    n = len(points)
    for y in range(h):
        py = y + 0.5
        for x in range(w):
            px = x + 0.5
            inside = False
            j = n - 1
            for i in range(n):
                xi, yi = points[i]
                xj, yj = points[j]
                if (yi > py) != (yj > py):
                    xc = xi + (py - yi) * (xj - xi) / (yj - yi)
                    if px < xc:
                        inside = not inside
                j = i
            if inside:
                out.add((x, y))
    return out


def _seg_distance(px: float, py: float, a: Point, b: Point) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def stroke(path: list[Point], thickness: float, w: int = SIZE, h: int = SIZE) -> Mask:
    """Rasterise a polyline as a round-capped band of the given half-width."""
    out: Mask = set()
    for y in range(h):
        for x in range(w):
            px, py = x + 0.5, y + 0.5
            if any(_seg_distance(px, py, path[i], path[i + 1]) <= thickness
                   for i in range(len(path) - 1)):
                out.add((x, y))
    return out


def bezier(p0: Point, ctrl: Point, p1: Point, samples: int = 28) -> list[Point]:
    pts: list[Point] = []
    for i in range(samples + 1):
        t = i / samples
        u = 1 - t
        pts.append((u * u * p0[0] + 2 * u * t * ctrl[0] + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * ctrl[1] + t * t * p1[1]))
    return pts


def blob(cx: float, cy: float, radius: float, seed: int, wobble: float = 0.22) -> Mask:
    """An irregular rounded lump - the raw-ore silhouette language."""
    out: Mask = set()
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            ang = math.atan2(dy, dx)
            r = radius * (1.0
                          + wobble * math.sin(3 * ang + seed * 0.7)
                          + wobble * 0.55 * math.sin(5 * ang - seed * 1.3))
            if math.hypot(dx, dy) <= r:
                out.add((x, y))
    return out


def lozenge(cx: float, cy: float, half_len: float, half_wide: float,
            angle_deg: float, pow_len: float = 2.6, pow_wide: float = 1.8) -> Mask:
    """A crystal sliver: a superellipse rotated onto a diagonal axis.

    amethyst_shard is roughly sixteen pixels long and six across on a diagonal
    axis with a blunt point at each end; these exponents reproduce that taper.
    """
    out: Mask = set()
    ca = math.cos(math.radians(angle_deg))
    sa = math.sin(math.radians(angle_deg))
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            if (abs(u) / half_len) ** pow_len + (abs(v) / half_wide) ** pow_wide <= 1.0:
                out.add((x, y))
    return out


def axis_coords(cx: float, cy: float, angle_deg: float, mask: Mask):
    """Yield (x, y, u, v) - position along and across a crystal's long axis."""
    ca = math.cos(math.radians(angle_deg))
    sa = math.sin(math.radians(angle_deg))
    for (x, y) in mask:
        dx, dy = x + 0.5 - cx, y + 0.5 - cy
        yield x, y, dx * ca + dy * sa, -dx * sa + dy * ca


def egg_mask() -> Mask:
    """The classic spawn-egg oval: a superellipse with a tapered crown.

    Measured against creeper_spawn_egg, which spans x2-13 at the waist, x4-11
    three rows from the top and x5-10 at the very bottom.
    """
    out: Mask = set()
    for y in range(SIZE):
        for x in range(SIZE):
            nx = (x + 0.5 - 7.5) / 6.0
            ny = (y + 0.5 - 8.0) / 7.2
            if ny < 0:
                nx *= 1.0 + (-ny) * 0.35
            if abs(nx) ** 2.0 + abs(ny) ** 2.4 <= 1.0:
                out.add((x, y))
    return out


def facet_crystal(sp: Sprite, mask: Mask, mat: Material, cx: float, cy: float,
                  angle: float, seed: int, half_wide: float) -> None:
    """Paint a crystal as three flat facets meeting on a bright spine.

    Vanilla's amethyst shard is not shaded smoothly - it is three value bands
    with a one-pixel bright ridge between them, which is why it reads as
    faceted stone rather than a blurred pebble.
    """
    for x, y, _u, v in axis_coords(cx, cy, angle, mask):
        t = v / half_wide
        if t < -0.45:
            level = 0.80                      # facet turned into the key light
        elif t < 0.10:
            level = 1.00                      # the ridge itself
        elif t < 0.55:
            level = 0.55
        else:
            level = 0.26                      # facet turned away
        level += 0.10 * (fbm(x * 2.3, y * 2.3, seed, octaves=2) - 0.5)
        level += 0.10 * (key_light_factor(x, y, SIZE) / 1.4142)
        sp.put(x, y, mat, mat.tone(level))


# ---------------------------------------------------------------------------
# Material items
# ---------------------------------------------------------------------------

def resonance_shard() -> Sprite:
    """Cyan bismuth sliver - the mod's core crafting crystal."""
    sp = Sprite()
    cx, cy, ang = 7.6, 8.2, -38.0
    body = lozenge(cx, cy, 8.1, 3.2, ang)
    facet_crystal(sp, body, BISMUTH, cx, cy, ang, 4409, 3.2)
    for p in ((4, 12), (5, 13)):              # chipped corner, so it is not an oval
        sp.clear(*p)
    sp.outline()
    sp.stamp([(9, 5)], GOLD, 1.0)
    sp.stamp([(8, 6), (10, 4)], BISMUTH, 1.0)
    return sp


def void_glass_shard() -> Sprite:
    """A broken plate of void glass - straight fracture edges, pale and cold."""
    sp = Sprite()
    body = poly([(12.6, 1.4), (14.4, 6.2), (10.2, 13.4), (3.2, 12.0),
                 (5.4, 6.6), (9.0, 2.2)])
    for (x, y) in body:
        band_index = int(x * 0.7 + y * 0.9) % 3
        level = (0.88, 0.55, 0.26)[band_index]
        level += 0.14 * (key_light_factor(x, y, SIZE) / 1.4142)
        level += 0.08 * (fbm(x * 2.1, y * 2.1, 771, octaves=2) - 0.5)
        sp.put(x, y, VOID_GLASS, VOID_GLASS.tone(level))
    sp.outline()
    sp.stamp([(8, 4), (7, 5)], VOID_GLASS, 1.0)
    sp.stamp([(11, 9)], BISMUTH, 1.0)
    return sp


def raw_null_iron() -> Sprite:
    """An unsmelted lump, on vanilla's raw_iron silhouette.

    The shape and the internal light-to-dark structure are vanilla's, measured
    from the real sprite; only the material ramp is ours. Null iron is a low
    contrast material, so its levels are compressed into the upper half of the
    ramp - taking vanilla's full range would make it read as raw iron in a
    different hue rather than as its own metal.
    """
    sp = Sprite()
    # Wide range on purpose: vanilla's raw lumps read as clumped nuggets rather
    # than a smooth pebble, and that reading comes entirely from internal
    # contrast. Compressing the ramp here made it look like a flat grey stone.
    lv = vf.levels(vf.RAW, lo=0.14, hi=1.0)
    for (x, y), level in lv.items():
        # A little noise so the lump does not look like a recoloured stencil.
        level += 0.07 * (fbm(x * 2.4, y * 2.4, 8123, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    sp.outline()
    # Bismuth glinting out of the matrix, kept to the lit face.
    sp.stamp([(4, 4), (9, 10)], BISMUTH, 0.30)
    return sp


def null_iron_ingot() -> Sprite:
    """Smelted null iron, on vanilla's iron_ingot silhouette.

    iron_ingot.png is a rounded parallelogram with a bright top face, a
    one-pixel specular along the crease and a darker front face below and to
    the right. Reproducing that by hand got the idea but not the outline, so
    the form table is now the measured sprite and the ingot reads as an ingot
    at a glance. The bismuth mark struck into the top face is what makes it
    ours rather than a recoloured vanilla bar.
    """
    sp = Sprite()
    lv = vf.levels(vf.INGOT, lo=0.28, hi=1.0)
    for (x, y), level in lv.items():
        level += 0.09 * (fbm(x * 2.0, y * 2.0, 611, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    sp.outline()
    sp.stamp([(5, 6), (6, 6), (7, 7)], BISMUTH, 1.0)
    return sp


def bismuth_seedling() -> Sprite:
    """A seed crystal: a dark husk with two shoots already singing."""
    sp = Sprite()
    husk = {(x, y) for y in range(SIZE) for x in range(SIZE)
            if ((x + 0.5 - 7.6) / 3.4) ** 2 + ((y + 0.5 - 12.2) / 2.8) ** 2 <= 1.0}
    shoot_a = poly([(5.6, 1.6), (7.2, 3.2), (7.4, 11.0), (5.0, 11.0), (4.4, 4.2)])
    shoot_b = poly([(11.6, 4.6), (12.6, 6.4), (10.4, 11.4), (8.6, 10.6), (9.8, 6.2)])
    sp.paint(husk, NULL_IRON, 0.48, 4211, spread=0.45, light=0.30)
    facet_crystal(sp, shoot_a, BISMUTH, 5.9, 6.4, -8.0, 913, 1.7)
    facet_crystal(sp, shoot_b, BISMUTH, 10.5, 8.0, 22.0, 4471, 1.6)
    sp.outline()
    sp.stamp([(5, 2), (6, 3)], BISMUTH, 1.0)
    sp.stamp([(11, 5)], GOLD, 1.0)
    return sp


def tuning_disc(label: Material, body: Material, spiral: float, seed: int) -> Sprite:
    """A harmonic tuning disc.

    Built like a music disc: a full circle of grooves with a coloured centre
    label and a punched spindle hole. music_disc_cat is a radius-seven circle
    whose grooves alternate two greys, with a five-pixel label at the middle.
    """
    sp = Sprite()
    cx, cy, r = 7.5, 7.6, 6.7
    disc = {(x, y) for y in range(SIZE) for x in range(SIZE)
            if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= r}
    for (x, y) in disc:
        dx, dy = x + 0.5 - cx, y + 0.5 - cy
        rr = math.hypot(dx, dy)
        theta = math.atan2(dy, dx) / (2 * math.pi)
        groove = ((rr * spiral + theta) % 1.0) < 0.5
        level = 0.66 if groove else 0.30
        level += 0.20 * (key_light_factor(x, y, SIZE) / 1.4142)
        level += 0.08 * (fbm(x * 2.4, y * 2.4, seed, octaves=2) - 0.5)
        sp.put(x, y, body, body.tone(level))
    for (x, y) in disc:
        rr = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
        if rr <= 2.7:
            level = 0.95 if rr <= 1.8 else 0.50
            level += 0.10 * (key_light_factor(x, y, SIZE) / 1.4142)
            sp.put(x, y, label, label.tone(level))
    sp.outline()
    sp.put(7, 7, body, body.dark)                 # spindle hole
    return sp


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def tuning_fork() -> Sprite:
    """Two tines, a yoke and a stem - the portal frequency probe.

    Held upright rather than on the vanilla tool diagonal: at 16x16 a pair of
    diagonal tines turns to mush, and the upright silhouette is what makes a
    tuning fork read instantly. The tines are three pixels wide so the outline
    pass leaves a lit core between the two rim tones, exactly the way a vanilla
    tool handle is built.
    """
    sp = Sprite()
    tines = spans({
        2: [(5, 6), (9, 10)],
        3: [(4, 6), (9, 11)], 4: [(4, 6), (9, 11)], 5: [(4, 6), (9, 11)],
        6: [(4, 6), (9, 11)], 7: [(4, 6), (9, 11)], 8: [(4, 6), (9, 11)],
        9: [(4, 11)], 10: [(4, 11)],
    })
    stem = spans({11: [(6, 9)], 12: [(6, 9)], 13: [(6, 9)], 14: [(5, 10)]})
    sp.paint(tines, BISMUTH, 0.64, 2207, spread=0.30, light=0.30)
    sp.paint(stem, NULL_IRON, 0.58, 3307, spread=0.34, light=0.28)
    sp.outline()
    sp.stamp([(5, 3), (10, 3)], BISMUTH, 1.0)
    sp.stamp([(7, 9)], GOLD, 1.0)
    return sp


def harmonic_pickaxe() -> Sprite:
    """Pickaxe on the vanilla diagonal.

    Handle from (2,14) to (10,5) at three pixels across - centre fill, flanks
    outlined - and a two-pixel head arc from (5,3) round to (14,11), matching
    the mass iron_pickaxe.png gives its head.
    """
    sp = Sprite()
    handle = stroke([(2.4, 14.4), (10.4, 5.6)], 1.05)
    head = stroke(bezier((4.6, 3.6), (12.4, 2.0), (14.2, 10.8)), 1.05)
    sp.paint(handle, NULL_IRON, 0.58, 5501, spread=0.34, light=0.26)
    sp.paint(head - handle, BISMUTH, 0.62, 5507, spread=0.32, light=0.30)
    sp.outline()
    sp.stamp([(9, 5), (10, 6)], NULL_IRON, 1.0)   # lashing at the eye
    sp.stamp([(7, 3), (12, 3)], BISMUTH, 1.0)
    sp.stamp([(6, 3)], GOLD, 1.0)
    return sp


def sonic_lance() -> Sprite:
    """A polearm: long haft, resonator collar, leaf blade and a charge cell."""
    sp = Sprite()
    haft = stroke([(1.2, 15.0), (9.8, 6.2)], 1.05)
    blade = poly([(15.2, 0.4), (13.6, 4.6), (10.4, 7.0), (8.8, 5.6), (11.6, 2.2)])
    collar = spans({6: [(9, 11)], 7: [(8, 10)]})
    sp.paint(haft, NULL_IRON, 0.56, 6101, spread=0.34, light=0.26)
    sp.paint(blade - haft, VOID_GLASS, 0.64, 6113, spread=0.34, light=0.30)
    sp.paint(collar, BISMUTH, 0.68, 6121, spread=0.24, light=0.24)
    sp.outline()
    # charge gauge on the haft: two cyan cells rising to a gold pip when full
    sp.stamp([(4, 12), (5, 11)], BISMUTH, 1.0)
    sp.stamp([(6, 10)], GOLD, 1.0)
    sp.stamp([(13, 2), (12, 3)], VOID_GLASS, 1.0)
    return sp


# ---------------------------------------------------------------------------
# The Harmonic toolset
#
# These four exist because the Knell tier upgrades from Resonance rather than
# from netherite, so each Knell piece needs one of ours to come from. They are
# named for the Harmonic Pickaxe, which already filled the pickaxe slot on the
# same material, and they belong to the Resonance family: Harmonic gear is the
# pathway to Knell.
#
# The geometry is deliberately the same as the Knell set's, one notch calmer -
# same handle diagonal, same head masses, less flare on the outline. That is
# what makes an upgrade read as an upgrade: the player recognises the shape and
# sees it sharpen, rather than being handed an unrelated silhouette.
#
# The handle is NULL_IRON, dark, exactly as harmonic_pickaxe already draws it -
# a warm wooden haft here would break the one visual thing the set already had
# in common.
# ---------------------------------------------------------------------------

def _harmonic_tool(form, seed: int, sparks: list) -> Sprite:
    """One Harmonic tool: vanilla's measured form in our two materials.

    The head takes bismuth and the haft null-iron, which is the pairing
    harmonic_pickaxe already used and the reason the set reads as one family.
    """
    head, haft = vf.tool_levels(form)
    sp = Sprite()
    for (x, y), level in haft.items():
        level += 0.08 * (fbm(x * 2.1, y * 2.1, seed, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    for (x, y), level in head.items():
        level += 0.08 * (fbm(x * 2.1, y * 2.1, seed + 6, octaves=2) - 0.5)
        sp.put(x, y, BISMUTH, BISMUTH.tone(level))
    sp.outline()
    sp.stamp(sparks, GOLD, 1.0)
    return sp


def harmonic_sword() -> Sprite:
    """Vanilla's sword form: blade on the diagonal, guard, grip off the corner."""
    return _harmonic_tool(vf.SWORD, 7301, [(4, 11)])


def harmonic_axe() -> Sprite:
    """Vanilla's axe form - the bit shape is what makes an axe read as an axe."""
    return _harmonic_tool(vf.AXE, 7401, [(8, 2)])


def harmonic_shovel() -> Sprite:
    """Vanilla's shovel form: a spade blade square on the end of the haft."""
    return _harmonic_tool(vf.SHOVEL, 7501, [(11, 3)])


def harmonic_hoe() -> Sprite:
    """Vanilla's hoe form: a cross bar with the blade hanging off its far end.

    This is the one head that is not on the haft's diagonal, and that is
    exactly what tells a hoe from an axe at 16x16.
    """
    return _harmonic_tool(vf.HOE, 7601, [(7, 1)])


def void_glass_rapier() -> Sprite:
    """A slender thrusting sword: narrow blade, swept guard, dark grip.

    diamond_sword.png sets the language - blade on the (5,10) to (15,0)
    diagonal, guard perpendicular across rows 8-12, grip running off the
    bottom-left corner. The blade here is a pixel narrower so it reads as a
    rapier rather than a broadsword.
    """
    sp = Sprite()
    blade = stroke([(5.8, 9.8), (15.2, 0.6)], 0.95)
    guard = stroke([(2.6, 8.8), (7.2, 13.2)], 0.75)
    bow = stroke([(2.6, 8.8), (1.2, 11.4), (3.4, 13.6)], 0.55)
    grip = stroke([(0.8, 15.0), (4.2, 11.6)], 0.95)
    sp.paint(grip, NULL_IRON, 0.52, 7001, spread=0.34, light=0.26)
    sp.paint((guard | bow) - blade, BISMUTH, 0.60, 7013, spread=0.26, light=0.26)
    sp.paint(blade, VOID_GLASS, 0.70, 7019, spread=0.30, light=0.32)
    sp.outline()
    sp.stamp([(8, 7), (10, 5), (12, 3), (14, 1)], VOID_GLASS, 1.0)
    sp.stamp([(1, 14)], GOLD, 1.0)
    return sp


# ---------------------------------------------------------------------------
# Armour icons
#
# Silhouettes measured from iron_helmet / iron_chestplate / iron_leggings /
# iron_boots. They are the most recognisable shapes in the inventory, so the
# span tables stay close to vanilla and all the identity comes from the paint.
# ---------------------------------------------------------------------------

HELMET_SPANS = {
    3: [(5, 10)], 4: [(4, 11)], 5: [(3, 12)], 6: [(3, 12)], 7: [(3, 12)],
    8: [(3, 12)], 9: [(3, 12)], 10: [(3, 12)], 11: [(4, 5), (10, 11)],
}

CHESTPLATE_SPANS = {
    2: [(1, 5), (10, 14)], 3: [(1, 5), (10, 14)], 4: [(1, 6), (9, 14)],
    5: [(1, 14)], 6: [(1, 14)], 7: [(1, 14)],
    8: [(3, 12)], 9: [(3, 12)], 10: [(3, 12)], 11: [(3, 12)], 12: [(3, 12)],
    13: [(4, 11)], 14: [(5, 10)],
}

LEGGINGS_SPANS = {
    2: [(4, 11)], 3: [(3, 12)], 4: [(3, 12)], 5: [(3, 12)], 6: [(3, 12)],
    7: [(3, 6), (9, 12)], 8: [(3, 6), (9, 12)], 9: [(3, 6), (9, 12)],
    10: [(3, 6), (9, 12)], 11: [(3, 6), (9, 12)], 12: [(3, 6), (9, 12)],
    13: [(3, 6), (9, 12)],
}

BOOTS_SPANS = {
    3: [(4, 6), (9, 11)],
    4: [(3, 6), (9, 12)], 5: [(3, 6), (9, 12)], 6: [(3, 6), (9, 12)],
    7: [(3, 6), (9, 12)], 8: [(3, 6), (9, 12)],
    9: [(2, 6), (9, 13)], 10: [(1, 6), (9, 14)], 11: [(1, 6), (9, 14)],
    12: [(1, 4), (11, 14)],
}


def curved_band(put_fn, mask: Mask, mat: Material, row: int,
                lit: float = 0.94, curve: int = 2) -> None:
    """One horizontal plate course, arced by up to `curve` px at its centre.

    The single technique both the item icons and the worn equipment sheets use
    for "this reads as a plate seam, not a stripe or a scatter of noise" - a
    full-width, symmetric band that bows towards the middle. `put_fn(x, y)` is
    called for every texel the band actually lands on, and does whatever the
    caller needs (paint one tone, or a lit-row/shadow-row pair); the curve and
    row-selection math is shared so the icon and the worn sheet can never draw
    a different shape for what is meant to be the same seam.
    """
    xs = [x for (x, _) in mask]
    if not xs:
        return
    x_lo, x_hi = min(xs), max(xs)
    half = max(1, (x_hi - x_lo) / 2.0)
    centre = (x_lo + x_hi) / 2.0
    for x in range(x_lo, x_hi + 1):
        t = 1.0 - min(1.0, abs(x - centre) / half)
        y = row - round(curve * t * t)
        if (x, y) in mask:
            put_fn(x, y)


def _plate_icon(mask: Mask, mat: Material, seed: int, trim: list[tuple[int, int]],
                cavity: Mask | None = None, accent: "Material | None" = None,
                base: float = 0.62, spread: float = 0.22,
                bands: "list[int] | None" = None,
                horns: "list[tuple[int, int]] | None" = None,
                cutouts: "list[tuple[int, int]] | None" = None) -> Sprite:
    """The shared armour-icon painter.

    PLAYER: "look at how netherite armor differs... from diamond or iron in
    terms of shape... i want differentiation like that" - then, correcting the
    first pass at it: "the coloring looks like a jumbled mess, look at
    netherite, it looks like stacked, geometric armor plates, not randomness."

    Both readings of netherite are real, and the second is the dominant one:
    netherite_helmet.png IS pixel-identical in silhouette to diamond_helmet.png
    (vanilla never touches the outline) and its internal shading is a rougher,
    darker mottle than diamond's clean gradient - but "rougher" is not the same
    as "random", and an asymmetric noise-ranked scatter reads as a manufacturing
    defect, not a plate seam. `bands` is the fix: full-width horizontal courses
    at fixed rows, which is inherently left-right symmetric and reads as
    stacked plate the way the equipment sheets' own plates() does, rather than
    scattered flecks. `horns` places explicit, symmetric accent points -
    pairs, mirrored by the caller - and MAY extend past the vanilla silhouette
    (a genuine addition to the mask, outlined afterwards like any other edge)
    for a real horn rather than a notch. `cutouts` still punches real holes.
    """
    sp = Sprite()
    full_mask = set(mask) | set(horns or ())
    sp.paint(full_mask, mat, base, seed, spread=spread, light=0.30)
    if cavity:
        for (x, y) in cavity & mask:
            sp.put(x, y, mat, mat.tone(0.05))
    if bands:
        # See curved_band() at module scope - this is the SAME function the
        # worn equipment sheets call, so an icon and its worn form can never
        # draw the plate seam differently.
        for row in bands:
            curved_band(
                lambda x, y: sp.put(x, y, mat, mat.tone(0.94))
                if (not cavity or (x, y) not in cavity) else None,
                full_mask, mat, row)
    if horns:
        for (x, y) in horns:
            sp.put(x, y, mat, mat.tone(0.90))
    if cutouts:
        for (x, y) in cutouts:
            if (x, y) in full_mask:
                sp.clear(x, y)
    sp.outline()
    sp.stamp([(x, y) for (x, y) in trim if (x, y) in full_mask], accent or BISMUTH, 1.0)
    return sp


def resonance_helmet() -> Sprite:
    """Null iron dome: stacked plate courses, a vented ear guard cut clean
    through, and a pair of small horns swept back from the temples."""
    mask = spans(HELMET_SPANS)
    cavity = spans({9: [(5, 10)], 10: [(5, 10)]})
    # Horns curve IN toward the dome as they rise - base out at the temple,
    # tip hooking back over the brow - rather than a straight outward poke.
    sp = _plate_icon(mask, NULL_IRON, 9001,
                     [(5, 8), (6, 8), (9, 8), (10, 8)], cavity=cavity,
                     base=0.48, spread=0.22, bands=[7],
                     horns=[(3, 4), (3, 3), (12, 4), (12, 3)],
                     cutouts=[(3, 6), (12, 6)])
    sp.stamp([(7, 8), (8, 8)], BISMUTH, 0.50)
    sp.stamp([(5, 4), (6, 4)], NULL_IRON, 1.0)
    # The horns are the same material as the dome, so the outline pass reads
    # them as dark nubs rather than a feature - Knell's use HARMONIC for
    # exactly this reason. Recolouring after outline() keeps the shape but
    # gives it the set's own accent.
    # PLAYER: "you can make the resonance horns glow blue."
    sp.stamp([(3, 4), (3, 3), (12, 4), (12, 3)], BISMUTH, 1.0)
    return sp


def resonance_chestplate() -> Sprite:
    """Pauldrons, a chest resonator core, lit shoulder studs, two plate
    courses, and a vented gap at each collarbone cut clean through."""
    mask = spans(CHESTPLATE_SPANS)
    sp = _plate_icon(mask, NULL_IRON, 9013, [(7, 9), (8, 9), (7, 10), (8, 10)],
                     base=0.46, spread=0.22, bands=[5, 9],
                     cutouts=[(2, 3), (13, 3)])
    sp.stamp([(6, 9), (9, 9)], BISMUTH, 0.45)
    sp.stamp([(3, 3), (12, 3)], BISMUTH, 0.55)
    return sp


def resonance_leggings() -> Sprite:
    """A full run of stacked plate courses down each shaft, not one belt line."""
    mask = spans(LEGGINGS_SPANS)
    sp = _plate_icon(mask, NULL_IRON, 9027, [(4, 5), (5, 5), (10, 5), (11, 5)],
                     base=0.44, spread=0.20, bands=[5, 10])
    sp.stamp([(7, 5), (8, 5)], BISMUTH, 0.40)
    return sp


def resonance_boots() -> Sprite:
    """Stacked plate courses from ankle to toe, plus a small heel spur -
    matching the leggings' language rather than a single dark fill."""
    mask = spans(BOOTS_SPANS)
    sp = _plate_icon(mask, NULL_IRON, 9041, [(4, 7), (5, 7), (10, 7), (11, 7)],
                     base=0.42, spread=0.20, bands=[6, 9],
                     horns=[(0, 10), (15, 10)])
    sp.stamp([(3, 10), (12, 10)], BISMUTH, 0.40)
    return sp


def aero_stride_greaves() -> Sprite:
    """Pale void-glass boots with cyan drift vanes on the outer ankle."""
    sp = Sprite()
    mask = spans(BOOTS_SPANS)
    vanes = spans({5: [(1, 2), (13, 14)], 6: [(0, 1), (14, 15)]})
    sp.paint(mask, VOID_GLASS, 0.64, 9055, spread=0.36, light=0.32)
    sp.paint(vanes, BISMUTH, 0.74, 9059, spread=0.22, light=0.24)
    sp.outline()
    sp.stamp([(3, 11), (4, 11), (11, 11), (12, 11)], BISMUTH, 1.0)
    sp.stamp([(4, 5), (11, 5)], VOID_GLASS, 1.0)
    return sp


# ---------------------------------------------------------------------------
# Spawn eggs
# ---------------------------------------------------------------------------

def spawn_egg(mat: Material, spot: Material, seed: int) -> Sprite:
    """Egg silhouette, mottled shell, six spot clusters, two-tone outline."""
    sp = Sprite()
    shell = egg_mask()
    sp.paint(shell, mat, 0.68, seed, spread=0.34, light=0.34)
    interior = {(x, y) for (x, y) in shell
                if all((x + dx, y + dy) in shell
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    # deterministic spots: rank the interior by a noise field and take its peaks,
    # then keep them apart so they read as markings rather than a smear
    ranked = sorted(interior,
                    key=lambda p: -fbm(p[0] * 3.1, p[1] * 3.1, seed + 17, octaves=2))
    chosen: list[tuple[int, int]] = []
    for p in ranked:
        if len(chosen) >= 6:
            break
        if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) > 2 for q in chosen):
            chosen.append(p)
    for (x, y) in chosen:
        sp.put(x, y, spot, spot.tone(0.95))
        for dx, dy in ((1, 0), (0, 1)):
            if (x + dx, y + dy) in interior:
                sp.put(x + dx, y + dy, spot, spot.tone(0.55))
    sp.outline()
    return sp


EGGS: list[tuple[str, Material, Material, int]] = [
    # slate shell with cyan markings - the weaver spins acoustic silk
    ("echo_weaver_spawn_egg", SLATE, BISMUTH, 4801),
    # amber shell with gold markings - the golem is warm strata given legs
    ("strata_golem_spawn_egg", AMBER, GOLD, 9127),
    # violet shell with magenta markings - the wraith is arcane through
    ("resonance_wraith_spawn_egg", ARCANE, ARCANE, 3313),
    # The three below take their shell from the creature's body material and their
    # spots from whatever glows on it, so an egg is recognisable as the thing it
    # hatches without reading the tooltip.
    # null-iron cage around a hot bismuth core
    ("chime_mote_spawn_egg", NULL_IRON, BISMUTH, 6203),
    # arcane cloth, but cyan piping rather than the wraith's magenta, so the two
    # violet eggs are still tellable apart in a row of hotbar slots
    ("tuner_shade_spawn_egg", ARCANE, BISMUTH, 7717),
    # phonolite carapace with amber strata running through it
    ("strata_burrower_spawn_egg", SLATE, AMBER, 2459),
    # the trader's own colours: amber robe, gold satchel
    ("tuner_trader_spawn_egg", AMBER, GOLD, 4417),
    # the protector's own colours: stone-grey plate, null-iron forearms
    ("tuners_protector_spawn_egg", SLATE, NULL_IRON, 8801),
]


# ---------------------------------------------------------------------------
# Worn-armour equipment sheets
#
# A box added with CubeListBuilder.texOffs(u, v).addBox(..., w, h, d) unwraps
# into six rectangles in a fixed arrangement. Reproducing that arithmetic here
# means the painted regions are exactly the ones the armour meshes sample.
# ---------------------------------------------------------------------------

def box_faces(u: int, v: int, w: int, h: int, d: int) -> dict[str, tuple[int, int, int, int]]:
    return {
        "top": (u + d, v, w, d),
        "bottom": (u + d + w, v, w, d),
        "right": (u, v + d, d, h),
        "front": (u + d, v + d, w, h),
        "left": (u + d + w, v + d, d, h),
        "back": (u + d + w + d, v + d, w, h),
    }


def face_rect(face: tuple[int, int, int, int]) -> Mask:
    x0, y0, w, h = face
    return rect(x0, y0, w, h)


def band(face: tuple[int, int, int, int], row0: int, row1: int) -> Mask:
    """Rows row0..row1 of a face rectangle, clipped to the face."""
    x0, y0, w, h = face
    lo, hi = max(y0, row0), min(y0 + h - 1, row1)
    return {(x, y) for y in range(lo, hi + 1) for x in range(x0, x0 + w)}


ADULT_HEAD = box_faces(0, 0, 8, 8, 8)
ADULT_BODY = box_faces(16, 16, 8, 12, 4)
ADULT_ARM = box_faces(40, 16, 4, 12, 4)
ADULT_LEG = box_faces(0, 16, 4, 12, 4)


def adult_helmet_region() -> Mask:
    """Dome, ear guards and neck flare, with the face left open."""
    m = face_rect(ADULT_HEAD["top"])
    for key in ("right", "front", "left", "back"):
        m |= band(ADULT_HEAD[key], 8, 10)
    m |= band(ADULT_HEAD["right"], 11, 11)
    m |= band(ADULT_HEAD["left"], 11, 11)
    m |= band(ADULT_HEAD["back"], 11, 13)
    m |= {(x, 12) for x in range(0, 4)}            # right cheek guard
    m |= {(x, 12) for x in range(20, 24)}          # left cheek guard
    m |= {(8, 11), (11, 11), (12, 11), (15, 11)}   # brow edges and nose bridge
    m |= {(11, 12), (12, 12)}
    m |= {(x, 14) for x in range(26, 30)}          # neck guard
    return m


def adult_chest_region() -> Mask:
    m = face_rect(ADULT_BODY["top"])
    for key in ("right", "front", "left", "back"):
        m |= band(ADULT_BODY[key], 20, 28)
    m -= {(x, 20) for x in range(22, 26)}          # collar opening, front
    m -= {(x, 20) for x in range(34, 38)}          # collar opening, back
    m -= {(23, 21), (24, 21), (35, 21), (36, 21)}
    m |= face_rect(ADULT_ARM["top"])
    for key in ("right", "front", "left", "back"):
        m |= band(ADULT_ARM[key], 20, 24)
    return m


def adult_boot_region() -> Mask:
    m = face_rect(ADULT_LEG["bottom"])             # the sole
    for key in ("right", "front", "left", "back"):
        m |= band(ADULT_LEG[key], 26, 31)
    return m


def adult_leggings_regions() -> tuple[Mask, Mask]:
    hips = face_rect(ADULT_LEG["top"])
    for key in ("right", "front", "left", "back"):
        hips |= band(ADULT_LEG[key], 20, 28)
    skirt: Mask = set()
    for key in ("right", "front", "left", "back"):
        skirt |= band(ADULT_BODY[key], 27, 31)
    return hips, skirt


BABY_HEAD = box_faces(0, 0, 9, 8, 8)
BABY_BODY = box_faces(0, 17, 6, 5, 3)
BABY_LEFT_ARM = box_faces(30, 17, 2, 5, 3)
BABY_RIGHT_ARM = box_faces(30, 25, 2, 5, 3)
BABY_WAIST = box_faces(0, 36, 6, 2, 3)
BABY_RIGHT_LEG = box_faces(18, 17, 3, 4, 3)
BABY_LEFT_LEG = box_faces(18, 24, 3, 4, 3)
BABY_RIGHT_FOOT = box_faces(0, 25, 3, 1, 3)
BABY_LEFT_FOOT = box_faces(0, 29, 3, 1, 3)


def baby_regions() -> tuple[Mask, Mask, Mask]:
    """(helmet, chest, boots) masks on the 64x64 baby armour layout."""
    helm = face_rect(BABY_HEAD["top"])
    for key in ("right", "front", "left", "back"):
        helm |= band(BABY_HEAD[key], 8, 10)
    helm |= band(BABY_HEAD["right"], 11, 14)
    helm |= band(BABY_HEAD["left"], 11, 14)
    helm |= band(BABY_HEAD["back"], 11, 15)
    helm |= {(8, 11), (11, 11), (12, 11), (13, 11), (16, 11)}
    helm |= {(8, 12), (11, 12), (12, 12), (13, 12), (16, 12)}
    helm |= {(8, 13), (16, 13)}

    chest = face_rect(BABY_BODY["top"])
    for key in ("right", "front", "left", "back"):
        chest |= band(BABY_BODY[key], 20, 24)
    chest -= {(5, 20), (6, 20)}                    # collar opening
    for box in (BABY_LEFT_ARM, BABY_RIGHT_ARM):
        for key in ("top", "bottom", "right", "front", "left", "back"):
            chest |= face_rect(box[key])

    boots: Mask = set()
    for box in (BABY_RIGHT_LEG, BABY_LEFT_LEG, BABY_RIGHT_FOOT,
                BABY_LEFT_FOOT, BABY_WAIST):
        for key in ("top", "bottom", "right", "front", "left", "back"):
            boots |= face_rect(box[key])
    return helm, chest, boots


class Sheet:
    """A larger canvas that reuses Sprite's material bookkeeping."""

    def __init__(self, w: int, h: int):
        self.sp = Sprite(w, h)

    def plate(self, mask: Mask, mat: Material, seed: int, base: float = 0.58,
              spread: float = 0.14) -> None:
        """A clean base fill: gentle grain only, no per-cell bevel.

        PLAYER: "the chestplate leggings need a lot of work, they look like a
        jumbled mess, not the good contours you now have in the [icons]." The
        4-pixel checkerboard bevel this used to add - bright at every
        x%4==0/y%4==0, dark at every x%4==3/y%4==3 - tiled the SAME pattern
        across the whole limb regardless of where the actual plate edges are,
        which is a second, competing texture underneath the real bands and
        bevel() calls. The item icons never had that: they are a smooth base
        plus a few deliberate accent rows, which is why they read clean. This
        now matches that - low-amplitude grain, no manufactured checkerboard -
        and lets plates()/bevel() do all of the structural work, same as the
        icon side does with bands()/horns().
        """
        for (x, y) in mask:
            n = fbm(x * 1.3, y * 1.3, seed, octaves=2)
            self.sp.put(x, y, mat, mat.tone(base + spread * (n - 0.5)))

    def rivets(self, mask: Mask, mat: Material, seed: int, count: int = 20,
               min_spacing: int = 2) -> None:
        """Scatter `count` dark studs across `mask`, ranked by noise.

        `min_spacing` enforces a minimum gap between accepted rivets, greedily
        skipping a candidate that lands too close to one already placed. Without
        it, a plain top-K by noise score can cluster tightly wherever that
        seed's fbm happens to peak - found via the 3D player preview, which
        showed a torso's small 8x4 shoulder-top region strobed with rivets
        while the much larger front and back panels carried barely any,
        because the ranking was global across a mask that mixes very
        differently sized regions. Spacing makes the count actually mean an
        even scatter regardless of how the mask is shaped.
        """
        ranked = sorted(mask, key=lambda p: -fbm(p[0] * 4.7, p[1] * 4.7, seed, octaves=1))
        placed: list[tuple[int, int]] = []
        for p in ranked:
            if len(placed) >= count:
                break
            if any(abs(p[0] - q[0]) < min_spacing and abs(p[1] - q[1]) < min_spacing
                   for q in placed):
                continue
            placed.append(p)
        for p in placed:
            self.sp.put(p[0], p[1], mat, mat.dark)

    def trim(self, mask: Mask, mat: Material, level: float = 0.9) -> None:
        for (x, y) in mask:
            if self.sp.opaque(x, y):
                self.sp.put(x, y, mat, mat.tone(level))

    def plates(self, face: tuple[int, int, int, int], mat: Material,
               course: int = 6, lit: float = 0.94) -> None:
        """Horizontal plate courses across a face, gently arced.

        PLAYER: "your shading contrasts too much, and it does not match the
        inventory items... literally match the stuff from the item to the
        worn." This used to be its own implementation - the same curve math as
        the icons' bands, but ALSO a separate dark shadow row one pixel above
        every lit one, which the icons never had. That extra row is what made
        the worn sheets read as higher-contrast and different from the icon
        next to them. Now it calls curved_band() directly - the exact function
        the icons use - so a course here and a band on the matching icon are
        pixel-for-pixel the same technique, one bright row, no separate shadow.
        """
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        for i, y in enumerate(range(y0, y0 + h)):
            if i % course:
                continue
            curved_band(
                lambda x, yy: self.sp.put(x, yy, mat, mat.tone(lit))
                if self.sp.opaque(x, yy) else None,
                face_mask, mat, y)

    def bevel(self, face: tuple[int, int, int, int], mat: Material,
              level: float = 0.9, shade: float = 0.24) -> None:
        """A lit left edge and a shadowed right edge on one face.

        One column each side, not a repeat: it rounds the panel off so it reads
        as wrapping a limb instead of sitting flat on it.
        """
        x0, y0, w, h = face
        for y in range(y0, y0 + h):
            if self.sp.opaque(x0, y):
                self.sp.put(x0, y, mat, mat.tone(level))
            if w > 1 and self.sp.opaque(x0 + w - 1, y):
                self.sp.put(x0 + w - 1, y, mat, mat.tone(shade))

    def wing_shape(self, face, mat, accent, mirror=False):
        """A drawn wing silhouette, not a texture pattern.

        PLAYER: "try to draw on flat wings on the flying boot things." A
        diagonal barb fill at 4 texels wide reads as an argyle print, not a
        wing, no matter how the shading is tuned - there just is not enough
        room in a repeating pattern to carry a feather motif. A tapered SHAPE
        does read, the same way winged-boot pixel art everywhere else draws it:
        a broad base at the ankle narrowing to a point, one clean silhouette
        rather than fill. The leading edge is picked out in the accent colour
        so the shape stays legible once it is small and worn.
        """
        x0, y0, w, h = face
        widths = [w, w, max(1, w - 1), max(1, w - 2), max(1, w - 2), 1]
        for i, run in enumerate(widths):
            y = y0 + i
            if y >= y0 + h:
                break
            for j in range(run):
                x = x0 + (w - 1 - j) if mirror else x0 + j
                if not (x0 <= x < x0 + w):
                    continue
                leading = (j == 0)
                self.sp.put(x, y, accent if leading else mat,
                            (accent if leading else mat).tone(0.95 if leading else 0.40 + 0.05 * i))
        self.sp.outline()

    def studs(self, face: tuple[int, int, int, int], mat: Material,
              rows: tuple[int, ...], level: float = 1.0) -> None:
        """Bright pips along given rows of a face - rivet heads, catching light."""
        x0, y0, w, h = face
        for r in rows:
            y = y0 + r
            if not (y0 <= y < y0 + h):
                continue
            for x in range(x0, x0 + w, 2):
                if self.sp.opaque(x, y):
                    self.sp.put(x, y, mat, mat.tone(level))

    def save(self, path: Path) -> Image.Image:
        return self.sp.save(path)


def resonance_layer_1() -> Sheet:
    """Helmet, chestplate and boots on the adult 64x32 humanoid layout."""
    sh = Sheet(64, 32)
    helm, chest, boots = adult_helmet_region(), adult_chest_region(), adult_boot_region()
    sh.plate(helm, NULL_IRON, 3301, base=0.56)
    sh.plate(chest, NULL_IRON, 3307, base=0.60)
    sh.plate(boots, NULL_IRON, 3313, base=0.52)
    sh.rivets(chest, NULL_IRON, 3319, count=8, min_spacing=3)
    sh.rivets(helm, NULL_IRON, 3323, count=4, min_spacing=3)
    sh.trim(band(ADULT_HEAD["front"], 10, 10) | band(ADULT_HEAD["back"], 10, 10), BISMUTH)
    sh.trim({(x, 23) for x in range(20, 28)}, BISMUTH)
    sh.trim({(x, 23) for x in range(32, 40)}, BISMUTH)
    sh.trim({(x, 29) for x in range(0, 16)}, BISMUTH)
    # The horns on the item icon have no equivalent here - the worn model is
    # a fixed vanilla box, it cannot grow a spike - but leaving the worn
    # helmet without ANY matching mark is what made "the player look doesn't
    # match the inventory look" true. A bright accent at each temple, where
    # the icon's horn actually attaches, is the closest a flat texture gets.
    right_x0, right_y0, _, _ = ADULT_HEAD["right"]
    left_x0, left_y0, left_w, _ = ADULT_HEAD["left"]
    # PLAYER: "you could do a bit more than two pixels from the side" - three
    # rows now, and it wraps one texel onto the front face too so it reads as
    # the base of something rather than an isolated dot.
    sh.sp.stamp([(right_x0 + 6, right_y0 + 1), (right_x0 + 7, right_y0 + 1),
                 (right_x0 + 7, right_y0 + 2), (right_x0 + 7, right_y0 + 3)], BISMUTH, 1.0)
    sh.sp.stamp([(left_x0 + 1, left_y0 + 1), (left_x0, left_y0 + 1),
                 (left_x0, left_y0 + 2), (left_x0, left_y0 + 3)], BISMUTH, 1.0)
    # Depth pass: banded plate courses down the torso and arms, plus a bevel so
    # each panel rounds off at its edges.
    for key in ("right", "front", "left", "back"):
        sh.plates(ADULT_BODY[key], NULL_IRON, course=5)
        sh.plates(ADULT_ARM[key], NULL_IRON, course=6)

    # Chest sigil and shoulder caps, painted directly onto this one sheet -
    # no separate overlay layer. Deliberately sparse: a mark on the chest, a
    # bright cap on each shoulder, not a second garment's worth of detail.
    front = ADULT_BODY["front"]
    fx, fy = front[0], front[1]
    sigil = {(fx + 3, fy + 3), (fx + 4, fy + 3),
             (fx + 2, fy + 4), (fx + 5, fy + 4),
             (fx + 3, fy + 5), (fx + 4, fy + 5),
             (fx + 3, fy + 4), (fx + 4, fy + 4)}
    for (x, y) in sigil:
        sh.sp.put(x, y, BISMUTH, BISMUTH.tone(0.95))
    for key in ("right", "front", "left", "back"):
        for (x, y) in band(ADULT_ARM[key], 20, 21):
            sh.sp.put(x, y, BISMUTH, BISMUTH.tone(0.72 if y % 2 else 0.98))
    return sh


def resonance_layer_2() -> Sheet:
    """Leggings on the adult 64x32 humanoid_leggings layout.

    PLAYER: "the chestplate leggings need a lot of work, they look like a
    jumbled mess." This piece never got the plates()/bevel() pass the torso
    did - only the flat plate() fill, so once that lost its checkerboard it
    had nothing left to read as armour at all. Same treatment as the torso now.
    """
    sh = Sheet(64, 32)
    hips, skirt = adult_leggings_regions()
    sh.plate(hips, NULL_IRON, 3401, base=0.54)
    sh.plate(skirt, NULL_IRON, 3407, base=0.58)
    sh.rivets(hips | skirt, NULL_IRON, 3413, count=6, min_spacing=3)
    sh.trim({(x, 28) for x in range(16, 40)}, BISMUTH)
    sh.trim({(x, 21) for x in range(0, 16)}, BISMUTH)
    for key in ("right", "front", "left", "back"):
        sh.plates(ADULT_LEG[key], NULL_IRON, course=6)
        sh.plates(ADULT_BODY[key], NULL_IRON, course=2)  # the narrow hip flare
    return sh


def aero_stride_layer_1() -> Sheet:
    """Aero-Stride Greaves on the adult humanoid layout.

    Only the boot region can render for a feet-slot item, but the helmet and
    chest regions are painted too so the sheet stays valid if the set is ever
    extended - vanilla ships full sheets for partial sets for the same reason.

    Single sheet, no separate overlay layer: the wings are drawn straight onto
    this base texture as an actual tapered shape on each boot's outer face,
    rows 26-31 - vanilla's own boot span, so the silhouette in-game still reads
    as a boot and not a legging, with the wing as a decal on it rather than a
    second garment.
    """
    sh = Sheet(64, 32)
    helm, chest, boots = adult_helmet_region(), adult_chest_region(), adult_boot_region()
    sh.plate(helm, VOID_GLASS, 3501, base=0.58)
    sh.plate(chest, VOID_GLASS, 3507, base=0.60)
    sh.plate(boots, VOID_GLASS, 3511, base=0.66)
    sh.rivets(boots, VOID_GLASS, 3517, count=8, min_spacing=3)

    lx = ADULT_LEG["right"][0]
    rx, _, rw, _ = ADULT_LEG["left"]
    sh.wing_shape((lx, 26, ADULT_LEG["right"][2], 6), VOID_GLASS, BISMUTH, mirror=False)
    sh.wing_shape((rx, 26, rw, 6), VOID_GLASS, BISMUTH, mirror=True)
    return sh


def baby_sheet(mat: Material, seed: int) -> Sheet:
    """The 64x64 baby armour layout - a different unwrap, not a scaled copy."""
    sh = Sheet(64, 64)
    helm, chest, boots = baby_regions()
    # Higher spread throughout - bevel() (removed as redundant with the
    # bands elsewhere) used to be what gave this small, ~800-texel sheet
    # enough tonal variety on its own.
    sh.plate(helm, mat, seed + 1, base=0.56, spread=0.40)
    sh.plate(chest, mat, seed + 2, base=0.60, spread=0.40)
    sh.plate(boots, mat, seed + 3, base=0.54, spread=0.50)
    sh.rivets(chest, mat, seed + 4, count=6, min_spacing=3)
    sh.trim(band(BABY_HEAD["front"], 10, 10) | band(BABY_HEAD["back"], 10, 10), BISMUTH)
    sh.trim({(x, 23) for x in range(0, 18)}, BISMUTH)
    sh.trim({(x, 30) for x in range(18, 30)}, BISMUTH)
    # A bevelled edge on the chest and boot regions - the flattened plate()
    # alone does not carry enough contrast to clear the colour floor once the
    # rivet count drops, and a baby sheet has no bands()-style face table to
    # lean on instead.
    # bevel()'s edge highlight only touches a handful of pixels against 789
    # total opaque texels on this sheet, which was not enough to move the
    # dominant-colour gate off 88-89%. Explicit bright rows across each leg's
    # front face (matching the trim() rows chest/head already use) is what
    # the other regions rely on for contrast, and this piece had none.
    sh.trim({(x, 21) for x in range(18, 21)}, BISMUTH)
    sh.trim({(x, 28) for x in range(18, 21)}, BISMUTH)
    return sh


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ITEMS: list[tuple[str, object]] = [
    ("resonance_shard", resonance_shard),
    ("raw_null_iron", raw_null_iron),
    ("null_iron_ingot", null_iron_ingot),
    ("void_glass_shard", void_glass_shard),
    ("bismuth_seedling", bismuth_seedling),
    ("harmonic_tuning_disc_alpha", lambda: tuning_disc(BISMUTH, SLATE, 1.55, 8801)),
    ("harmonic_tuning_disc_beta", lambda: tuning_disc(ARCANE, SLATE, 1.15, 8807)),
    ("harmonic_tuning_disc_gamma", lambda: tuning_disc(GOLD, NULL_IRON, 1.85, 8819)),
    ("tuning_fork", tuning_fork),
    ("harmonic_pickaxe", harmonic_pickaxe),
    ("sonic_lance", sonic_lance),
    ("void_glass_rapier", void_glass_rapier),
    ("harmonic_sword", harmonic_sword),
    ("harmonic_axe", harmonic_axe),
    ("harmonic_shovel", harmonic_shovel),
    ("harmonic_hoe", harmonic_hoe),
    ("resonance_helmet", resonance_helmet),
    ("resonance_chestplate", resonance_chestplate),
    ("resonance_leggings", resonance_leggings),
    ("resonance_boots", resonance_boots),
    ("aero_stride_greaves", aero_stride_greaves),
]

EQUIPMENT_SHEETS = [
    ("humanoid/resonance.png", resonance_layer_1, (64, 32)),
    ("humanoid_leggings/resonance.png", resonance_layer_2, (64, 32)),
    ("humanoid/aero_stride.png", aero_stride_layer_1, (64, 32)),
    ("humanoid_baby/resonance.png", lambda: baby_sheet(NULL_IRON, 4600), (64, 64)),
    ("humanoid_baby/aero_stride.png", lambda: baby_sheet(VOID_GLASS, 4700), (64, 64)),
]


# ---------------------------------------------------------------------------
# Contact sheets - the visual self-review step
# ---------------------------------------------------------------------------

def _font():
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=13)
    except TypeError:                               # Pillow older than 10.1
        return ImageFont.load_default()


def contact_sheet(entries: list[tuple[str, Image.Image]], path: Path,
                  scale: int = 9, columns: int = 6) -> None:
    """Tile every sprite at nine times size on the inventory-slot grey.

    Judging a 16x16 icon in a file browser is useless; judging it against the
    grey it actually sits on in the hotbar is how readability problems surface.
    """
    from PIL import ImageDraw

    font = _font()
    pad, label_h = 8, 16
    cell_w = 16 * scale + pad * 2
    cell_h = 16 * scale + pad * 2 + label_h
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGBA", (cell_w * columns, cell_h * rows), (28, 30, 36, 255))
    draw = ImageDraw.Draw(sheet)

    for i, (name, img) in enumerate(entries):
        cx = (i % columns) * cell_w
        cy = (i // columns) * cell_h
        draw.rectangle([cx + pad - 2, cy + pad - 2,
                        cx + pad + 16 * scale + 1, cy + pad + 16 * scale + 1],
                       fill=(139, 139, 139, 255))
        big = img.convert("RGBA").resize((16 * scale, 16 * scale), Image.NEAREST)
        sheet.alpha_composite(big, (cx + pad, cy + pad))
        draw.text((cx + pad, cy + pad + 16 * scale + 3), name, font=font,
                  fill=(226, 231, 240, 255))

    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, "PNG")


def strip_sheet(entries: list[tuple[str, Image.Image]], path: Path, scale: int = 4) -> None:
    """Stack the 64-wide equipment layers so their UV regions can be eyeballed."""
    from PIL import ImageDraw

    font = _font()
    pad, label_h = 8, 16
    width = max(img.width for _, img in entries) * scale + pad * 2
    height = sum(img.height * scale + pad * 2 + label_h for _, img in entries)
    sheet = Image.new("RGBA", (width, height), (28, 30, 36, 255))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for name, img in entries:
        big = img.convert("RGBA").resize((img.width * scale, img.height * scale), Image.NEAREST)
        draw.rectangle([pad - 2, y + pad - 2, pad + big.width + 1, y + pad + big.height + 1],
                       fill=(139, 139, 139, 255))
        sheet.alpha_composite(big, (pad, y + pad))
        draw.text((pad, y + pad + big.height + 3), name, font=font, fill=(226, 231, 240, 255))
        y += big.height + pad * 2 + label_h
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, "PNG")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

MIN_COLOURS, MAX_COLOURS = 5, 16


def audit(img: Image.Image, expect: tuple[int, int] | None, floor: int = MIN_COLOURS) -> list[str]:
    problems: list[str] = []
    if expect and img.size != expect:
        problems.append(f"size {img.size[0]}x{img.size[1]}, expected {expect[0]}x{expect[1]}")
    n = len(unique_colors(img))
    if not (floor <= n <= MAX_COLOURS):
        problems.append(f"{n} colours, want {floor}-{MAX_COLOURS}")
    return problems


EQUIPMENT_ASSETS = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "equipment"

# asset -> {layer type: [texture names, draw order - later paints over earlier]}
#
# This is what makes the overlay sheets actually render: 26.2 types the field
# as Map<LayerType, List<Layer>>, so a layer type can carry more than one
# texture, and everything after the first is layered on top of it. A renderer
# or a hand-edited JSON that assumes one texture per type silently drops every
# layer past the first - which is what the base sheet plus its overlay would
# have hit if this stayed hand-written.
EQUIPMENT_ASSET_LAYERS = {
    # One texture per layer type. The wings and the chest sigil/pauldrons are
    # painted directly into these single sheets now rather than declared as a
    # second Layer entry - see resonance_layer_1()/aero_stride_layer_1().
    "resonance": {
        "humanoid": ["resonance"],
        "humanoid_baby": ["resonance"],
        "humanoid_leggings": ["resonance"],
    },
    "aero_stride": {
        "humanoid": ["aero_stride"],
        "humanoid_baby": ["aero_stride"],
    },
}


def write_equipment_assets() -> None:
    for asset, layers in EQUIPMENT_ASSET_LAYERS.items():
        data = {"layers": {
            layer_type: [{"texture": f"{NS}:{tex}"} for tex in textures]
            for layer_type, textures in layers.items()
        }}
        path = EQUIPMENT_ASSETS / f"{asset}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + chr(10), encoding="utf-8")
        print(f"  equipment asset: {asset}.json ({sum(len(v) for v in layers.values())} layer entries)")


def main() -> int:
    ITEM_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    gallery: list[tuple[str, Image.Image]] = []
    sheets: list[tuple[str, Image.Image]] = []

    print(f"{'texture':<34} {'size':<9} colours")
    for name, factory in ITEMS:
        img = factory().save(ITEM_DIR / f"{name}.png")
        gallery.append((name, img))
        problems = audit(img, (16, 16))
        print(f"{name:<34} {img.size[0]}x{img.size[1]:<6} {len(unique_colors(img))}"
              + ("  " + "; ".join(problems) if problems else ""))
        failures += [f"{name}: {p}" for p in problems]

    write_equipment_assets()

    for rel, factory, want in EQUIPMENT_SHEETS:
        img = factory().save(EQUIP / rel)
        sheets.append((rel, img))
        # An *_overlay sheet is an additive second layer, not a full garment - it
        # paints only the flair (wings, a sigil, shoulder caps) and leaves the
        # rest of the 64x32 canvas transparent, same idea as an entity *_glow
        # mask. The 5-colour floor exists to catch flat programmer art on a real
        # garment and does not transfer to a sparse overlay.
        floor = 2 if Path(rel).stem.endswith("_overlay") else MIN_COLOURS
        problems = audit(img, want, floor=floor)
        print(f"{rel:<34} {img.size[0]}x{img.size[1]:<6} {len(unique_colors(img))}"
              + ("  " + "; ".join(problems) if problems else ""))
        failures += [f"{rel}: {p}" for p in problems]

    if "--preview" in sys.argv:
        contact_sheet(gallery, PREVIEW_DIR / "items.png")
        strip_sheet(sheets, PREVIEW_DIR / "equipment.png")
        print(f"\ncontact sheets written to {PREVIEW_DIR}")

    print("\nNOTE: tools/asset_gen.py mirrors humanoid/*.png into humanoid_baby/ after")
    print("      this script runs. That copy is now wrong - baby armour meshes are built")
    print("      at 64x64 (LayerDefinitions.createRoots), and this script already writes")
    print("      correct 64x64 baby sheets. The mirror step should be removed.")

    if failures:
        print(f"\nFAILED with {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

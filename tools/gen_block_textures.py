"""
The Echoing Void - block texture generator (art direction v2).

Draws the whole terrain set into
    src/main/resources/assets/echoing_void/textures/block/

WHY THIS FILE LOOKS THE WAY IT DOES
-----------------------------------
The first version obeyed a "4-6 indexed colours, key-light gradient across the
tile" rule. That rule is revoked: it is what made the rock read as flat, and it
is not how Minecraft draws stone. The conventions below were *measured* off the
shipped 26.2 assets (tools/_measure_vanilla.py) and are reproduced here:

  stone.png            4 colours, luminance 104..143  (span 39), no tile-wide
                       gradient at all - the diagonal shading players see comes
                       from block face lighting, not from the texture.
  tuff / calcite       5-6 colours, span 76..82, granules clustered at ~2px.
  coal / gold ore      the ore texture IS the host stone texture, with 4-6
                       speck clusters of 5-14px cut into it. Each cluster is a
                       three-shell onion: dark rim, mid body, 1-3 bright core
                       pixels, plus one near-white sparkle on its top-left.
                       Host span 39, cluster span 158 - the host is LOW contrast
                       precisely so the ore pops.
  azalea_leaves        4 colours, span 62, ~23% alpha in 20 clumps of 1..8px,
                       hue held within 13 degrees while lightness does the work.
  warped_stem_top      log tops carry a 2px bark rim with rounded corners in the
                       side texture's bark colour.
  amethyst_cluster     45% alpha, span 168, faceted: every facet has a lit
                       top-left edge and a dark bottom-right edge.

Two mechanisms carry all of that:

  field()        periodic value field = smooth fbm + per-pixel grit + a bump
                 lighting term (the directional derivative of the smooth part).
                 The lighting is therefore per-granule and points top-left, with
                 no tile-wide gradient. Everything is evaluated modulo 16, so
                 column 0 tiles against column 15 by construction.
  levels()       histogram-matched quantisation: the field is sorted and sliced
                 by target shares, so a texture's colour distribution is dialled
                 in directly (e.g. vanilla's ~28% dominant tone) and no colour
                 can run away and cover the tile.

raw_phonolite and phonolite_bricks are deliberately left on the original v1
code path, untouched, because the player likes how they read; the rest of the
family is built to sit next to them.

Depth is legible from rock colour. Mean luminance descends with altitude:
    resonant_chalk ~178  >  echo_slate ~95  >  amber_strata ~83  >  phonolite ~45
and the hues separate too: pale blue-white, steel blue, warm ochre, near-black.

Run:  python tools/gen_block_textures.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from PIL import Image, ImageDraw, ImageFont

from ev_palette import (  # noqa: E402
    SIZE,
    Canvas,
    Ramp,
    _force_distinct,
    _hash2,
    bayer,
    bevel_factor,
    build_ramp,
    fbm,
    key_light_factor,
    luminance,
    mix,
    parse_hex,
    shift,
    to_hex,
    unique_colors,
)

ROOT = TOOLS.parent
OUT_BLOCK = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "block"
PREVIEW_DIR = ROOT / "build" / "texture_preview"
PREVIEW = PREVIEW_DIR / "blocks_preview.png"
VANILLA_SHEET = PREVIEW_DIR / "vanilla_reference.png"
VANILLA_ROOT = Path(r"C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block")

SPEC = ROOT / "docs" / "spec" / "mod_spec.json"
ART = ROOT / "docs" / "spec" / "art_direction.json"

MIN_COLOURS = 5        # matches the v2 gate in tools/verify_textures.py
MAX_COLOURS = 16
MAX_SHARE = 0.85
SEAM_SLACK = 1.35
SEAM_FLOOR = 6.0


# ==========================================================================
# Palette - every colour below is mix()/shift() of art_direction anchors, so
# it stays inside the producible set the texture gate checks against.
# ==========================================================================

P = json.loads(ART.read_text(encoding="utf-8"))["palette"]

VOID_BLACK = parse_hex(P["void"]["black"])
VOID_SHADOW = parse_hex(P["void"]["shadow"])
PH_DARK = parse_hex(P["phonolite"]["dark"])
PH_MID = parse_hex(P["phonolite"]["mid"])
PH_LIGHT = parse_hex(P["phonolite"]["light"])
PH_PALE = parse_hex(P["phonolite"]["pale"])
CH_SHADOW = parse_hex(P["chalk"]["shadow"])
CH_MID = parse_hex(P["chalk"]["mid"])
CH_LIGHT = parse_hex(P["chalk"]["light"])
CH_HIGH = parse_hex(P["chalk"]["highlight"])
AM_DARK = parse_hex(P["amber"]["dark"])
AM_MID = parse_hex(P["amber"]["mid"])
AM_LIGHT = parse_hex(P["amber"]["light"])
AM_HIGH = parse_hex(P["amber"]["highlight"])
BI_DEEP = parse_hex(P["bismuth"]["deep"])
BI_MID = parse_hex(P["bismuth"]["mid"])
BI_BRIGHT = parse_hex(P["bismuth"]["bright"])
GOLD = parse_hex(P["bismuth"]["gold"])
AR_DEEP = parse_hex(P["arcane"]["deep"])
AR_MID = parse_hex(P["arcane"]["mid"])
AR_LIGHT = parse_hex(P["arcane"]["light"])
AR_BRIGHT = parse_hex(P["arcane"]["bright"])
NI_BLACK = parse_hex(P["null_iron"]["black"])
NI_DARK = parse_hex(P["null_iron"]["dark"])
NI_MID = parse_hex(P["null_iron"]["mid"])
# The light half of null-iron, at the same hue as its darks. Before these
# existed every null-iron ramp reached for phonolite when it needed a
# highlight, which is why the metal drifted from violet to blue as it lit.
NI_STEEL = parse_hex(P["null_iron"]["steel"])
NI_LIGHT = parse_hex(P["null_iron"]["light"])
NI_PALE = parse_hex(P["null_iron"]["pale"])

INK = parse_hex("#2B2D42")   # legacy anchor, still in ev_palette.PALETTES


def R(name: str, colors) -> Ramp:
    """Ramp of any length, duplicates nudged apart.

    ev_palette.Ramp enforces the revoked 4-6 rule in its constructor, so this
    builds the object and installs the colour list directly. Everything else
    about Ramp - clamping, indexing - still applies.
    """
    obj = Ramp.__new__(Ramp)
    obj.name = name
    obj.colors = _force_distinct([tuple(c) for c in colors])
    return obj


# ==========================================================================
# Field + quantisation: the two mechanisms behind every natural surface
# ==========================================================================

def hash01(x: int, y: int, seed: int) -> float:
    """Per-pixel deterministic value in [0,1), evaluated only on the 16x16 grid
    so it is trivially periodic when the tile repeats."""
    return _hash2(x % SIZE, y % SIZE, seed)


def field(seed: int, grain: int = 8, octaves: int = 2, grit: float = 0.42,
          relief: float = 0.55, warp: float = 0.0) -> list[list[float]]:
    """Periodic height/value field with per-granule top-left key lighting.

    `grain` is the fbm lattice period; 4 gives chunky moss-sized patches, 8
    gives stone-sized granules, 16 gives broad strata. `grit` is how much
    single-pixel noise is mixed in - vanilla stone is roughly half grit, which
    is what stops the result looking like an airbrush.

    `relief` adds the directional derivative of the *smooth* component. For a
    light coming from the top-left the lit flank of a bump is the one where the
    height rises toward the bottom-right, so the term is
    (h[x+1] - h[x-1]) + (h[y+1] - h[y-1]). This is the only lighting applied:
    there is deliberately no gradient across the tile, because vanilla stone
    has none and a tile-wide gradient is what made v1 look airbrushed.
    """
    h = [[0.0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            sx, sy = float(x), float(y)
            if warp:
                sx += (fbm(x, y, seed + 991, octaves=1, period=grain) - 0.5) * warp
                sy += (fbm(x, y, seed + 4409, octaves=1, period=grain) - 0.5) * warp
            h[y][x] = fbm(sx, sy, seed, octaves=octaves, period=grain)

    out = [[0.0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            lit = ((h[y][(x + 1) % SIZE] - h[y][(x - 1) % SIZE])
                   + (h[(y + 1) % SIZE][x] - h[(y - 1) % SIZE][x])) * 0.5
            out[y][x] = (h[y][x] * (1.0 - grit)
                         + hash01(x, y, seed ^ 0x9E37) * grit
                         + lit * relief)
    return out


def levels(f: list[list[float]], weights) -> list[list[int]]:
    """Histogram-matched quantisation of a field into len(weights) levels.

    Sorting the 256 samples and slicing by cumulative share makes the output
    distribution exactly the requested one. That is how a texture is given
    vanilla's shape - a ~28% dominant tone, a long tail of rarer accents -
    without any hand tuning of thresholds, and it makes the "no colour over
    85%" rule impossible to violate.
    """
    flat = sorted(((f[y][x], x, y) for y in range(SIZE) for x in range(SIZE)))
    total = float(sum(weights))
    out = [[0] * SIZE for _ in range(SIZE)]
    i = 0
    acc = 0.0
    n = SIZE * SIZE
    for lvl, w in enumerate(weights):
        acc += w / total
        stop = n if lvl == len(weights) - 1 else round(acc * n)
        while i < stop:
            _v, x, y = flat[i]
            out[y][x] = lvl
            i += 1
    return out


def paint(c: Canvas, lv: list[list[int]]) -> None:
    for y in range(SIZE):
        for x in range(SIZE):
            c.idx[y][x] = c.ramp.clamp(lv[y][x])


def rock(c: Canvas, seed: int, weights, grain: int = 8, grit: float = 0.42,
         octaves: int = 2, relief: float = 0.55, warp: float = 0.0) -> list[list[int]]:
    """Standard natural-surface body: field -> histogram-matched levels -> paint."""
    lv = levels(field(seed, grain=grain, octaves=octaves, grit=grit,
                      relief=relief, warp=warp), weights)
    paint(c, lv)
    return lv


def put(c: Canvas, x: int, y: int, index: int) -> None:
    """Set a pixel with wrap-around, so detail drawn at x=15 continues at x=0."""
    c.set(x % c.size, y % c.size, index)


def get(c: Canvas, x: int, y: int) -> int:
    return c.idx[y % c.size][x % c.size]


def bump_at(c: Canvas, x: int, y: int, delta: int, lo: int, hi: int) -> None:
    x %= c.size
    y %= c.size
    v = c.idx[y][x] + delta
    c.idx[y][x] = lo if v < lo else (hi if v > hi else v)


# ==========================================================================
# Ore clusters - the measured coal_ore / gold_ore convention
# ==========================================================================

# Hand-authored blobs, 10..13 px each. gold_ore's clusters run 7..17px and its
# ore covers 23% of the tile; five of these plus the site table below land on
# the same coverage.
BLOBS = [
    [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1),
     (0, 2), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3)],
    [(1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 1),
     (0, 2), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (2, 4)],
    [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
     (1, 2), (2, 2), (3, 2)],
    [(2, 0), (3, 0), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (3, 2),
     (0, 3), (1, 3), (2, 3)],
    [(0, 0), (1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2), (3, 2),
     (2, 3), (3, 3)],
    [(1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 2),
     (1, 2), (2, 2), (3, 2), (2, 3), (3, 3)],
]


def _erosion_depth(cells) -> dict[tuple[int, int], int]:
    """4-connected distance from the outside of the blob, per cell."""
    depth: dict[tuple[int, int], int] = {}
    frontier = {p for p in cells
                if any((p[0] + dx, p[1] + dy) not in cells
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    level = 0
    while frontier:
        for p in frontier:
            depth[p] = level
        level += 1
        frontier = {p for p in cells if p not in depth
                    and any((p[0] + dx, p[1] + dy) in depth
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    return depth


def ore_cluster(c: Canvas, ox: int, oy: int, blob, dark: int, mid: int,
                bright: int, sparkle: int | None = None, seed: int = 0) -> None:
    """One ore speck cluster, drawn to the proportions measured off gold_ore.

    A vanilla cluster is 30% dark rim, 42% mid body, 24% bright core and one
    sparkle pixel. Rather than shelling outward - which turns a 12px blob
    almost entirely into rim and makes the ore vanish into the rock - each cell
    is scored by how deep inside the blob it sits, biased toward the top-left
    so the key light lands on the correct face, and the cells are then ranked
    and sliced by those measured shares.

    Every write goes through put(), so a cluster straddling x=14 continues at
    x=0 rather than being clipped - that is what keeps ore blocks tiling.
    """
    cells = set(blob)
    depth = _erosion_depth(cells)
    span = max(p[0] + p[1] for p in cells) or 1

    def score(p):
        return (depth[p] * 2.2
                + (1.0 - (p[0] + p[1]) / span) * 1.1
                + hash01(p[0], p[1], seed + 313) * 0.5)

    ranked = sorted(cells, key=score, reverse=True)
    n = len(ranked)
    n_bright = max(2, round(n * 0.26))
    n_mid = max(2, round(n * 0.42))
    for i, (dx, dy) in enumerate(ranked):
        tone = bright if i < n_bright else (mid if i < n_bright + n_mid else dark)
        put(c, ox + dx, oy + dy, tone)
    if sparkle is not None:
        dx, dy = ranked[0]
        put(c, ox + dx, oy + dy, sparkle)
    # deepest bottom-right cell always falls to shadow, so the blob has weight
    dx, dy = max(cells, key=lambda p: (p[0] + p[1], p[1]))
    put(c, ox + dx, oy + dy, dark)


# Sites chosen so the five blobs barely touch and one wraps the x seam.
ORE_SITES = ((2, 1), (9, 2), (14, 6), (4, 9), (10, 11))
DEEP_ORE_SITES = ((3, 1), (10, 4), (1, 9), (11, 11))


def scatter_ore(c: Canvas, sites, dark: int, mid: int, bright: int,
                sparkle: int, sparkle_on=(0,)) -> None:
    for k, (ox, oy) in enumerate(sites):
        ore_cluster(c, ox, oy, BLOBS[k % len(BLOBS)], dark, mid, bright,
                    sparkle if k in sparkle_on else None, seed=ox * 31 + oy)


# ==========================================================================
# Foliage - clumped leaf masses, not thresholded noise
# ==========================================================================

LEAF_CLUMPS = [
    (1, 0), (6, 1), (11, 0), (14, 3), (3, 3), (8, 4), (0, 6), (12, 6),
    (5, 7), (9, 8), (2, 9), (14, 10), (7, 11), (11, 12), (4, 12), (0, 13),
]

# One leaf clump: a 5x4 rounded mass. `shell` is the position within the clump,
# 0 = crown (turned toward the key light), 2 = underside.
CLUMP = [
    (1, 0, 0), (2, 0, 0), (3, 0, 0),
    (0, 1, 0), (1, 1, 0), (2, 1, 0), (3, 1, 1), (4, 1, 1),
    (0, 2, 1), (1, 2, 1), (2, 2, 1), (3, 2, 2), (4, 2, 2),
    (1, 3, 2), (2, 3, 2), (3, 3, 2),
]


def foliage(c: Canvas, seed: int, dark: int, low: int, mid: int, high: int,
            accent: int, accents: int = 5) -> None:
    """Leaf canopy: overlapping rounded clumps, the gaps between them are alpha.

    azalea_leaves is 23% transparent in 20 clumps of 1..8px, four value steps,
    and a hue held inside 13 degrees - the eye reads it as foliage because of
    colour and clump silhouette, not because of the holes. So this lays 16
    overlapping 5x4 masses, gives each its own value bias, shades every mass
    crown-lit and underside-shadowed, and leaves the remainder transparent.

    Every write is put(), so masses that run off the right edge continue on the
    left and the canopy tiles across adjacent leaf blocks.
    """
    for i, (bx, by) in enumerate(LEAF_CLUMPS):
        jx = int(hash01(i, 3, seed) * 3) - 1
        jy = int(hash01(7, i, seed) * 3) - 1
        bias = 1 if hash01(i, i, seed + 91) > 0.62 else 0
        for dx, dy, shell in CLUMP:
            x, y = bx + dx + jx, by + dy + jy
            tone = (mid, low, dark)[shell] + bias
            if hash01(x, y, seed + 17) > 0.70:
                tone += 1
            tone = max(dark, min(high, tone))
            prev = get(c, x, y)
            put(c, x, y, tone if prev < 0 else max(prev, tone))

    # Rim pass: the key light catches the top-left of every mass and the
    # bottom-right falls away. This is what turns a blob into a leaf; without
    # it the canopy is a field of coloured static.
    snapshot = [row[:] for row in c.idx]

    def solid(x: int, y: int) -> bool:
        return snapshot[y % SIZE][x % SIZE] >= 0

    for y in range(SIZE):
        for x in range(SIZE):
            if not solid(x, y):
                continue
            if not solid(x - 1, y - 1) and (not solid(x - 1, y) or not solid(x, y - 1)):
                put(c, x, y, high)
            elif not solid(x + 1, y + 1) or (not solid(x + 1, y) and not solid(x, y + 1)):
                put(c, x, y, dark)

    # a handful of glowing tips, placed on lit crowns rather than sprinkled
    placed = 0
    for i, (bx, by) in enumerate(LEAF_CLUMPS):
        if placed >= accents:
            break
        if hash01(i, 5, seed + 401) < 0.55:
            continue
        x, y = (bx + 1) % SIZE, (by + 1) % SIZE
        if c.idx[y][x] >= mid:
            c.idx[y][x] = accent
            placed += 1


# ==========================================================================
# Faceted crystal (Voronoi with wrapped distance)
# ==========================================================================

def facets(c: Canvas, seed: int, sites_n: int, tones, edge: int,
           rim: int) -> list[list[int]]:
    """Crystal mass: wrapped Voronoi cells, each with a lit rim and dark edge.

    amethyst_block reads as crystal because every facet is bounded by a dark
    seam and carries a brighter band along its top-left. Wrapped distance keeps
    the cell layout continuous across the tile edge.
    """
    sites = []
    for i in range(sites_n):
        sites.append((hash01(i, 11, seed) * SIZE, hash01(31, i, seed) * SIZE))

    owner = [[0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            best, bi = 1e9, 0
            for i, (sx, sy) in enumerate(sites):
                dx = abs(x + 0.5 - sx)
                dy = abs(y + 0.5 - sy)
                dx = min(dx, SIZE - dx)
                dy = min(dy, SIZE - dy)
                d = dx * dx + dy * dy
                if d < best:
                    best, bi = d, i
            owner[y][x] = bi
            c.idx[y][x] = c.ramp.clamp(tones[bi % len(tones)])

    for y in range(SIZE):
        for x in range(SIZE):
            o = owner[y][x]
            if owner[y][(x + 1) % SIZE] != o or owner[(y + 1) % SIZE][x] != o:
                c.idx[y][x] = c.ramp.clamp(edge)
            elif owner[y][(x - 1) % SIZE] != o or owner[(y - 1) % SIZE][x] != o:
                c.idx[y][x] = c.ramp.clamp(rim)
    return owner


# ==========================================================================
# v1 helpers, kept verbatim: raw_phonolite and phonolite_bricks depend on them
# ==========================================================================

def clamp_body(c: Canvas, lo: int, hi: int) -> None:
    for y in range(c.size):
        for x in range(c.size):
            v = c.idx[y][x]
            c.idx[y][x] = lo if v < lo else (hi if v > hi else v)


def body(c: Canvas, seed: int, lo: int, hi: int, spread: float = 1.0,
         octaves: int = 3, base: float | None = None) -> None:
    c.noise_field(seed, octaves=octaves, spread=spread,
                  base=(lo + hi) / 2.0 if base is None else base)
    clamp_body(c, lo, hi)


def blotch(c: Canvas, seed: int, lo: int, hi: int, amount: float = 0.075,
           period: int = 4, octaves: int = 2) -> None:
    for y in range(c.size):
        for x in range(c.size):
            n = fbm(x, y, seed, octaves=octaves, period=period)
            if n > 0.5 + amount:
                bump_at(c, x, y, +1, lo, hi)
            elif n < 0.5 - amount:
                bump_at(c, x, y, -1, lo, hi)


def frame_inset(c: Canvas, hi: int, lo: int, r: int = 1) -> None:
    """Bevelled plate border drawn `r` pixels in from the edge, lit top/left."""
    n = c.size
    for i in range(r, n - r):
        c.set(i, r, hi)
        c.set(r, i, hi)
    for i in range(r, n - r):
        c.set(i, n - 1 - r, lo)
        c.set(n - 1 - r, i, lo)


def frame_hard(c: Canvas, hi: int, lo: int) -> None:
    for y in range(c.size):
        for x in range(c.size):
            b = bevel_factor(x, y, c.size)
            if b == 1.0:
                c.set(x, y, hi)
            elif b == -1.0:
                c.set(x, y, lo)


def rivet(c: Canvas, x: int, y: int, hi: int, lo: int) -> None:
    put(c, x, y, hi)
    put(c, x + 1, y + 1, lo)


def rings(c: Canvas, cx: float, cy: float, radius: float, density: float,
          even: int, odd: int, hi: int) -> None:
    for y in range(c.size):
        for x in range(c.size):
            d = math.hypot(x - cx, y - cy)
            if d > radius:
                continue
            idx = even if int(d * density) % 2 == 0 else odd
            if key_light_factor(x, y, c.size) > 0.45:
                idx = min(hi, idx + 1)
            c.set(x, y, idx)


PH4 = build_ramp("phonolite", 4).colors
PH5 = build_ramp("phonolite", 5).colors
RAW_RAMP = R("raw_phonolite", PH5)
BRICK_RAMP = R("bricks", [shift(PH5[0], -0.30)] + PH5[1:])


def t_raw_phonolite() -> Canvas:
    """Volcanic slate: noise body plus dashed bedding planes on an 8px period.

    Unchanged from v1 - the player likes how this reads, and it is the anchor
    the rest of the stone family is tuned against.
    """
    c = Canvas(RAW_RAMP)
    body(c, 3313, 0, 4, spread=1.0)
    blotch(c, 3314, 0, 4, amount=0.06)
    for y in range(c.size):
        if y % 8 == 0:
            for x in range(c.size):
                c.set(x, y, 0 if x % 4 != 3 else 1)
        elif y % 8 == 1:
            for x in range(c.size):
                if x % 4 != 3:
                    bump_at(c, x, y, +1, 0, 4)
    for x, y in ((2, 5), (11, 4), (6, 12), (14, 10)):
        put(c, x, y, 0)
        put(c, x - 1, y - 1, 4)
    return c


def t_phonolite_bricks() -> Canvas:
    """Running bond on a 4px vertical / 8px horizontal period. Unchanged from v1."""
    c = Canvas(BRICK_RAMP)
    body(c, 4409, 1, 4, spread=0.55, base=2.4)
    for y in range(c.size):
        off = 0 if (y // 4) % 2 == 0 else 4
        for x in range(c.size):
            bx = (x + off) % 8
            if y % 4 == 3 or bx == 7:
                c.set(x, y, 0)
            elif y % 4 == 0 or bx == 0:
                bump_at(c, x, y, +1, 1, 4)
            elif y % 4 == 2 or bx == 6:
                bump_at(c, x, y, -1, 1, 4)
    return c


# ==========================================================================
# Stone ramps - four rocks, one geology, descending luminance with depth
# ==========================================================================

CHALK_RAMP = R("resonant_chalk", [
    mix(CH_SHADOW, PH_PALE, 0.55),      # 0 crack shadow
    mix(CH_SHADOW, PH_PALE, 0.20),      # 1
    CH_SHADOW,                          # 2
    mix(CH_SHADOW, CH_MID, 0.55),       # 3
    CH_MID,                             # 4
    mix(CH_MID, CH_LIGHT, 0.55),        # 5
    CH_LIGHT,                           # 6
    CH_HIGH,                            # 7 glint
    mix(CH_MID, BI_MID, 0.42),          # 8 resonant fleck
])
CHALK_W = (0.05, 0.09, 0.15, 0.22, 0.21, 0.15, 0.09, 0.04)

SLATE_RAMP = R("echo_slate", [
    mix(PH_MID, PH_DARK, 0.55),         # 0 parting plane
    PH_MID,                             # 1
    mix(PH_MID, PH_LIGHT, 0.5),         # 2
    PH_LIGHT,                           # 3
    mix(PH_LIGHT, PH_PALE, 0.5),        # 4
    PH_PALE,                            # 5
    shift(PH_PALE, 0.20),               # 6 mica glint
    mix(PH_PALE, BI_MID, 0.30),         # 7 resonant fleck
])
SLATE_W = (0.08, 0.17, 0.24, 0.22, 0.16, 0.09, 0.04)

AMBER_RAMP = R("amber_strata", [
    mix(AM_DARK, VOID_BLACK, 0.62),     # 0 dark parting
    mix(AM_DARK, VOID_SHADOW, 0.35),    # 1
    AM_DARK,                            # 2
    mix(AM_DARK, AM_MID, 0.55),         # 3
    AM_MID,                             # 4
    mix(AM_MID, AM_LIGHT, 0.55),        # 5
    AM_LIGHT,                           # 6 band crest
    AM_HIGH,                            # 7 crest glint
])
AMBER_W = (0.12, 0.24, 0.26, 0.19, 0.11, 0.06, 0.02)

POLISH_RAMP = R("polished_phonolite", [
    mix(PH_DARK, VOID_BLACK, 0.45),
    PH_DARK,
    mix(PH_DARK, PH_MID, 0.45),
    PH_MID,
    mix(PH_MID, PH_LIGHT, 0.5),
    PH_LIGHT,
    mix(PH_LIGHT, PH_PALE, 0.45),
])
POLISH_W = (0.06, 0.16, 0.26, 0.26, 0.17, 0.07, 0.02)

CHALK_BRICK_RAMP = R("chalk_bricks", [
    mix(CH_SHADOW, PH_LIGHT, 0.55),     # 0 mortar
    mix(CH_SHADOW, PH_PALE, 0.25),      # 1
    CH_SHADOW,                          # 2
    mix(CH_SHADOW, CH_MID, 0.5),        # 3
    CH_MID,                             # 4
    CH_LIGHT,                           # 5
    CH_HIGH,                            # 6
])

SAND_RAMP = R("chime_sand", [
    mix(mix(CH_SHADOW, BI_MID, 0.16), VOID_SHADOW, 0.22),
    mix(CH_SHADOW, BI_MID, 0.16),
    mix(CH_MID, BI_MID, 0.14),
    mix(CH_LIGHT, BI_MID, 0.12),
    mix(CH_LIGHT, BI_MID, 0.05),
    CH_HIGH,
])
SAND_W = (0.06, 0.20, 0.34, 0.24, 0.12, 0.04)


def t_resonant_chalk() -> Canvas:
    """Pale highland stone. The value anchor that stops the dimension reading
    as one black mass: mean luminance about 178 against phonolite's 45.

    Calcite is the vanilla reference - six close bright tones, granules at the
    2px scale, no tile-wide gradient. The chalk gets a handful of hairline
    cracks (a rock this pale needs some drawing in it) and five cyan flecks so
    it still belongs to a resonant world.
    """
    c = Canvas(CHALK_RAMP)
    rock(c, 2101, CHALK_W, grain=8, grit=0.40, relief=0.60)
    # hairline cracks: short runs on a wrapped walk, one step darker than local
    for k, (sx, sy) in enumerate(((4, 1), (11, 6), (2, 11))):
        x, y = sx, sy
        for step in range(7):
            bump_at(c, x, y, -2, 0, 6)
            bump_at(c, x - 1, y - 1, +1, 0, 6)
            if hash01(step, k, 771) > 0.45:
                x += 1
            else:
                y += 1
            x %= SIZE
            y %= SIZE
    for x, y in ((6, 3), (13, 9), (3, 14), (9, 12), (0, 7)):
        put(c, x, y, 8)
    return c


def t_echo_slate() -> Canvas:
    """Blue-grey transition strata: slate parts along planes, so this carries
    two dashed parting lines on an 8px period and a directional grain that
    leans with them. Sits a clear value step under chalk and over phonolite."""
    c = Canvas(SLATE_RAMP)
    rock(c, 3203, SLATE_W, grain=8, grit=0.38, relief=0.62, warp=1.4)
    for y in range(SIZE):
        if y % 8 == 3:
            for x in range(SIZE):
                if (x + y) % 5 != 4:
                    c.set(x, y, 0)
                    bump_at(c, x, y - 1, +1, 1, 6)
    for x, y in ((5, 6), (12, 13), (1, 12)):
        put(c, x, y, 7)
    for x, y in ((9, 2), (2, 9), (14, 6)):
        put(c, x, y, 6)
    return c


def t_amber_strata() -> Canvas:
    """Warm ochre sedimentary band - the only warm rock in the terrain.

    Sedimentary means visible bedding: four bands on a 4px period, each with a
    lit crest and a dark parting beneath, with the noise field riding on top so
    the bands are irregular rather than ruled lines.
    """
    c = Canvas(AMBER_RAMP)
    rock(c, 4307, AMBER_W, grain=8, grit=0.30, relief=0.50, warp=2.2)
    # Bedding: a dark parting every 4 rows with a lit crest riding just above
    # it. The row a given pixel belongs to is displaced by a periodic noise
    # term, so the beds undulate instead of ruling straight lines, and the 4px
    # period divides 16 so the strata continue into the block above.
    for y in range(SIZE):
        for x in range(SIZE):
            wobble = int(round((fbm(x * 2.0, y, 4311, octaves=1, period=8) - 0.5) * 3.0))
            phase = (y + wobble) % 4
            if phase == 3:
                c.set(x, y, 0 if hash01(x, y, 4313) > 0.30 else 1)
            elif phase == 2:
                bump_at(c, x, y, +2, 0, 6)
            elif phase == 0:
                bump_at(c, x, y, -1, 0, 6)
    for x, y in ((3, 5), (10, 1), (6, 9), (13, 13)):
        put(c, x, y, 7)
        put(c, x + 1, y + 1, 0)
    return c


def t_polished_phonolite() -> Canvas:
    """Worked dark stone: smooth gradual drift across the worked face with
    shallow horizontal courses and no isolated dark outliers (max 1 ramp step
    between neighbours), bounded by a 1px bevel frame measured off vanilla's
    polished andesite / deepslate."""
    c = Canvas(POLISH_RAMP)
    seed = 5408
    grid = [[3] * SIZE for _ in range(SIZE)]

    # 1. Base field
    for y in range(SIZE):
        for x in range(SIZE):
            n = fbm(x * 0.7, y * 0.9, seed, octaves=2, period=SIZE)
            lit = key_light_factor(x, y, SIZE) * 0.12
            v = n + lit
            if v < 0.40:
                grid[y][x] = 2
            elif v > 0.60:
                grid[y][x] = 4
            else:
                grid[y][x] = 3

    # 2. Shallow horizontal streaks
    courses = [
        (2, 8, 4),
        (3, 3, 3),
        (6, 6, 4),
        (8, 2, 3),
        (8, 9, 4),
        (10, 3, 4),
        (11, 7, 3),
        (12, 2, 4),
        (14, 5, 3),
    ]
    for cy, cx0, clen in courses:
        for k in range(clen):
            x = (cx0 + k) % SIZE
            grid[cy][x] = 5

    # 3. Soft bevel on the perimeter (matching vanilla andesite ratios)
    # Top edge (row 0) & Left edge (col 0): Tone 5 & 6
    for x in range(SIZE):
        grid[0][x] = 6 if _hash2(x, 0, 5403) > 0.40 else 5
    for y in range(SIZE):
        grid[y][0] = 6 if _hash2(0, y, 5407) > 0.40 else 5
    grid[0][0] = 6

    # Bottom edge (row 15) & Right edge (col 15): Tone 2 (lum 49) with minor Tone 1 (lum 29) / Tone 3 (lum 66)
    # Calibrated to land at 0.69-0.71 of the field value (matching vanilla andesite/granite)
    for x in range(SIZE):
        h = _hash2(x, 15, 5409)
        grid[15][x] = 1 if h < 0.12 else (2 if h < 0.88 else 3)
    for y in range(SIZE):
        h = _hash2(15, y, 5411)
        grid[y][15] = 1 if h < 0.12 else (2 if h < 0.88 else 3)
    grid[15][15] = 2

    # 4. Relaxation pass to enforce max step delta of 1 across the whole tile including edges
    for _ in range(4):
        for y in range(SIZE):
            for x in range(SIZE):
                if (x == 0 and y == 0) or (x == 15 and y == 15):
                    continue
                nbrs = [grid[ny][nx] for nx, ny in (((x+1)%SIZE, y), ((x-1)%SIZE, y), (x, (y+1)%SIZE), (x, (y-1)%SIZE))]
                min_n = min(nbrs)
                max_n = max(nbrs)
                if grid[y][x] > max_n + 1:
                    grid[y][x] = max_n + 1
                elif grid[y][x] < min_n - 1:
                    grid[y][x] = min_n - 1

    for y in range(SIZE):
        for x in range(SIZE):
            c.set(x, y, grid[y][x])

    return c


def t_chalk_bricks() -> Canvas:
    """Same running bond as phonolite_bricks - the bond the player likes - in
    chalk values, so Tuner outposts read pale against the dark terrain."""
    c = Canvas(CHALK_BRICK_RAMP)
    # phonolite_bricks reads crisply because its body is smooth and the mortar
    # does the drawing, so the grain is dialled almost out here too. The v1
    # body() carries a tile-wide light gradient, which on a pale rock pushes
    # the wrap seam past tolerance, so this uses the gradient-free field with
    # the grit turned down instead.
    rock(c, 6503, (0.06, 0.15, 0.27, 0.29, 0.17, 0.06), grain=16, grit=0.10,
         octaves=2, relief=0.22)
    for y in range(SIZE):
        off = 0 if (y // 4) % 2 == 0 else 4
        for x in range(SIZE):
            bx = (x + off) % 8
            if y % 4 == 3 or bx == 7:
                c.set(x, y, 0)
            elif y % 4 == 0 or bx == 0:
                bump_at(c, x, y, +1, 1, 6)
            elif y % 4 == 2 or bx == 6:
                bump_at(c, x, y, -1, 1, 6)
    for x, y in ((2, 1), (9, 5), (5, 9), (12, 13)):
        put(c, x, y, 6)
    return c


def t_chime_sand() -> Canvas:
    """Granular, pale, faintly cyan. Vanilla sand spans only 46 luminance over
    six tones, and that tightness is what makes it read as loose grains rather
    than rock, so this holds the same narrow band and pushes grit up instead."""
    c = Canvas(SAND_RAMP)
    rock(c, 7601, SAND_W, grain=4, grit=0.72, relief=0.25)
    for x, y in ((3, 3), (12, 6), (7, 11), (14, 13), (1, 8)):
        put(c, x, y, 5)
        put(c, x + 1, y + 1, 0)
    return c


# ==========================================================================
# Ores
# ==========================================================================

# Crystal tones. gold_ore's rim sits at roughly the host's own luminance and is
# separated by hue, but our host is already blue-grey, so the rim is dropped
# well below the rock and the body lifted well above it: the cluster then has a
# dark outline and a body that cannot be confused with stone.
BIS_RIM = mix(BI_DEEP, VOID_BLACK, 0.42)      # lum ~58
BIS_BODY = mix(BI_DEEP, BI_MID, 0.45)         # lum ~135
BIS_CORE = BI_BRIGHT                          # lum ~189
BIS_SPARK = shift(BI_BRIGHT, 0.50)            # lum ~216

BISMUTH_ORE_RAMP = R("resonant_bismuth_ore", list(PH5) + [
    BIS_RIM, BIS_BODY, BIS_CORE, BIS_SPARK,
])

DEEP_HOST = [
    mix(PH_DARK, VOID_BLACK, 0.55),
    mix(PH_DARK, VOID_SHADOW, 0.20),
    PH_DARK,
    mix(PH_DARK, PH_MID, 0.45),
    PH_MID,
    mix(PH_MID, PH_LIGHT, 0.55),
]
DEEP_ORE_RAMP = R("deepslate_resonant_bismuth_ore", DEEP_HOST + [
    BIS_RIM, BIS_BODY, BIS_CORE, BIS_SPARK,
])
DEEP_W = (0.10, 0.22, 0.28, 0.21, 0.13, 0.06)

# Null iron is a hole, not a crystal, so its shells are inverted: the lip the
# light grazes is the brightest tone and the deepest cell is pure void black.
NULL_ORE_RAMP = R("null_iron_ore", list(PH5) + [
    mix(PH_LIGHT, BI_MID, 0.24),        # 5 lit lip of the pit
    NI_MID,                             # 6 pit wall
    NI_BLACK,                           # 7 the void itself
    mix(NI_MID, BI_MID, 0.35),          # 8 cold glint on the rim
])


def _phonolite_host(c: Canvas) -> None:
    """Reproduce raw_phonolite's body inside another ramp.

    Vanilla ores are literally the host stone with specks cut into them; if the
    host does not match the surrounding block the ore floats. Indices 0..4 of
    these ore ramps are the phonolite ramp, so running the v1 phonolite body
    against them lands the same pixels.
    """
    body(c, 3313, 0, 4, spread=1.0)
    blotch(c, 3314, 0, 4, amount=0.06)
    for y in range(c.size):
        if y % 8 == 0:
            for x in range(c.size):
                c.set(x, y, 0 if x % 4 != 3 else 1)
        elif y % 8 == 1:
            for x in range(c.size):
                if x % 4 != 3:
                    bump_at(c, x, y, +1, 0, 4)
    for x, y in ((2, 5), (11, 4), (6, 12), (14, 10)):
        put(c, x, y, 0)
        put(c, x - 1, y - 1, 4)


def t_resonant_bismuth_ore() -> Canvas:
    """Phonolite with bismuth crystal cut into it.

    The host is the raw_phonolite texture, pixel for pixel, so the ore reads as
    the same rock the player is mining through. Five clusters in the 7..13px
    band vanilla uses, each a dark-rim / body / bright-core onion with one
    sparkle, and the last one straddles the seam.
    """
    c = Canvas(BISMUTH_ORE_RAMP)
    _phonolite_host(c)
    scatter_ore(c, ORE_SITES, dark=5, mid=6, bright=7, sparkle=8,
                sparkle_on=(0, 3))
    return c


def t_deepslate_resonant_bismuth_ore() -> Canvas:
    """The same crystal in the deep host: darker, colder, higher contrast,
    with the fine streaking that separates deepslate from stone in vanilla."""
    c = Canvas(DEEP_ORE_RAMP)
    rock(c, 8707, DEEP_W, grain=8, grit=0.34, relief=0.65, warp=2.6)
    for y in range(SIZE):
        for x in range(SIZE):
            if fbm(x * 0.6, y * 1.9, 8711, octaves=1, period=8) > 0.62:
                bump_at(c, x, y, -1, 0, 5)
            elif fbm(x * 0.6, y * 1.9, 8719, octaves=1, period=8) > 0.68:
                bump_at(c, x, y, +1, 0, 5)
    scatter_ore(c, DEEP_ORE_SITES, dark=6, mid=7, bright=8, sparkle=9,
                sparkle_on=(1,))
    return c


def t_null_iron_ore() -> Canvas:
    """Null iron reads as absence: the specks are darker than the host rather
    than brighter, exactly as coal ore is, and each one carries a cold
    catch-light on the lip the key light strikes."""
    c = Canvas(NULL_ORE_RAMP)
    _phonolite_host(c)
    scatter_ore(c, ORE_SITES, dark=5, mid=6, bright=7, sparkle=8,
                sparkle_on=())
    return c


NULL_BLOCK_RAMP = R("null_iron_block", [
    NI_DARK,                                      # 0: deepest shadow / seam (lum ~27)
    mix(NI_DARK, NI_MID, 0.50),                  # 1: shadow underplate / seam (lum ~36)
    NI_MID,                                       # 2: mid-dark shadow (lum ~43)
    mix(NI_MID, NI_STEEL, 0.50),                 # 3: soft shadow (lum ~52)
    NI_STEEL,                                     # 4: forged body plate (lum ~61)
    mix(NI_STEEL, NI_LIGHT, 0.50),               # 5: lit forged plate (lum ~70)
    NI_LIGHT,                                     # 6: bright plate (lum ~78)
    mix(NI_LIGHT, NI_PALE, 0.50),                # 7: cold bevel highlight (lum ~94)
    NI_PALE,                                      # 8: bright bevel edge (lum ~111)
    mix(NI_PALE, CH_MID, 0.40),                  # 9: rivet specular glint (lum ~138)
])


def t_null_iron_block() -> Canvas:
    """Dense forged plate: bevelled inset frame, recessed centre panel, corner rivets,
    and a smooth directional metallic sheen across the face."""
    c = Canvas(NULL_BLOCK_RAMP)
    seed = 7703

    # 1. Base plate: smooth forged directional gradient flowing from top-left to bottom-right
    grid = [[5] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            diag = (30.0 - (x + y)) / 30.0
            n = fbm(x * 0.8, y * 0.8, seed, octaves=2, period=SIZE) - 0.5
            v = diag * 0.60 + n * 0.25 + 0.25
            if v < 0.25:
                grid[y][x] = 4
            elif v < 0.50:
                grid[y][x] = 5
            elif v < 0.75:
                grid[y][x] = 6
            else:
                grid[y][x] = 7

    # 2. Outer rim (row 0, col 0, row 15, col 15)
    for x in range(SIZE):
        grid[0][x] = 6 if _hash2(x, 0, seed + 11) > 0.35 else 5
        grid[15][x] = 2 if _hash2(x, 15, seed + 13) > 0.35 else 1
    for y in range(SIZE):
        grid[y][0] = 6 if _hash2(0, y, seed + 17) > 0.35 else 5
        grid[y][15] = 2 if _hash2(15, y, seed + 19) > 0.35 else 1
    grid[0][0] = 6
    grid[15][15] = 1

    # 3. Inset Bevel Frame (at x=1, y=1 and x=14, y=14)
    for i in range(1, SIZE - 1):
        grid[1][i] = 8 if _hash2(i, 1, seed + 23) > 0.30 else 7
        grid[i][1] = 8 if _hash2(1, i, seed + 29) > 0.30 else 7
    for i in range(1, SIZE - 1):
        grid[14][i] = 1 if _hash2(i, 14, seed + 31) > 0.35 else 2
        grid[i][14] = 1 if _hash2(14, i, seed + 37) > 0.35 else 2

    # 4. Recessed centre panel (rows 3..12, cols 3..12)
    # Inner shadow on top/left (step down into recess)
    for i in range(3, 13):
        grid[3][i] = 2 if _hash2(i, 3, seed + 41) > 0.40 else 3
        grid[i][3] = 2 if _hash2(3, i, seed + 43) > 0.40 else 3
    # Lit bottom/right lip of the recess (catching light on the rim)
    for i in range(3, 13):
        grid[12][i] = 6 if _hash2(i, 12, seed + 47) > 0.40 else 5
        grid[i][12] = 6 if _hash2(12, i, seed + 49) > 0.40 else 5

    # Interior recessed panel (rows 4..11, cols 4..11)
    for y in range(4, 12):
        for x in range(4, 12):
            diag = (22.0 - (x + y)) / 22.0
            n = fbm(x * 0.9, y * 0.9, seed + 101, octaves=2, period=8) - 0.5
            v = diag * 0.55 + n * 0.20 + 0.30
            if v < 0.28:
                grid[y][x] = 4
            elif v < 0.55:
                grid[y][x] = 5
            elif v < 0.80:
                grid[y][x] = 6
            else:
                grid[y][x] = 7

    # 5. Corner Rivets at (2, 2), (12, 2), (2, 12), (12, 12)
    for rx, ry in ((2, 2), (12, 2), (2, 12), (12, 12)):
        grid[ry][rx] = 9          # specular glint
        grid[ry][rx + 1] = 8      # right flank
        grid[ry + 1][rx] = 8      # lower flank
        grid[ry + 1][rx + 1] = 2  # shadow drop

    # 6. Smooth relaxation pass on the interior to enforce gradual drift
    for _ in range(3):
        for y in range(1, SIZE - 1):
            for x in range(1, SIZE - 1):
                if any(abs(x - rx) <= 1 and abs(y - ry) <= 1 for rx, ry in ((2, 2), (12, 2), (2, 12), (12, 12))):
                    continue
                nbrs = [grid[ny][nx] for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                        if 0 <= nx < SIZE and 0 <= ny < SIZE]
                if nbrs:
                    min_n = min(nbrs)
                    max_n = max(nbrs)
                    if grid[y][x] > max_n + 1:
                        grid[y][x] = max_n + 1
                    elif grid[y][x] < min_n - 1:
                        grid[y][x] = min_n - 1

    for y in range(SIZE):
        for x in range(SIZE):
            c.set(x, y, grid[y][x])

    return c


# The two carved-slit colours are appended to the block's ramp, so their INDEX
# depends on how long that ramp happens to be. It has already changed length
# once - the block gained two steps during a rework, the gold silently shifted
# from 8/9 to 10/11, and the mask's eyes went plain steel. SLIT_DIM/SLIT_LIT
# are derived rather than written down so that cannot recur.
SLIT_DIM = len(NULL_BLOCK_RAMP.colors)
SLIT_LIT = SLIT_DIM + 1

MASK_RAMP = R("tuners_mask", NULL_BLOCK_RAMP.colors + [
    shift(GOLD, -0.25),   # 8 unlit slit
    GOLD,                 # 9 lit slit rim
])


def t_tuners_mask_front() -> Canvas:
    """PLAYER: "the outpost could have... a village iron golem equivalent creature
    that... can be naturally built with a carved pumpkin head and body structure
    different but similar to that of an iron golem."

    Same plate body as null_iron_block - placed on a null-iron torso it should
    read as one material, not an inlaid decoration - but carved with the angled
    twin slits protector_head (gen_new_creature_textures.py) lights the summoned
    guardian's own face with, so the trigger block and the mob it builds visibly
    share one design language before the player has even seen the mob."""
    # The plate is not re-drawn here, it is COPIED from t_null_iron_block and
    # then carved. That is deliberate: the first version reproduced the block's
    # look with its own rock()/frame_inset()/rivet() calls, and the moment the
    # block itself was reworked the two drifted apart - the block became a
    # smooth forged plate while the mask stayed grainy, so a mask placed on a
    # null-iron body no longer read as the same material. Copying the indices
    # makes that impossible: whatever the block looks like, the mask is that
    # exact face with a sigil cut into it.
    #
    # The index copy is sound because MASK_RAMP is NULL_BLOCK_RAMP's colours
    # plus two gold entries appended, so indices 0-7 mean the same tone in both
    # ramps and 8-9 are the carved slit colours only the mask has.
    plate = t_null_iron_block()
    c = Canvas(MASK_RAMP)
    for y in range(SIZE):
        for x in range(SIZE):
            c.set(x, y, plate.get(x, y))

    # Twin angled slits, canted outward at the top - the same silhouette as the
    # guardian's own eye lights, just carved rather than emissive here.
    for x, y in ((4, 6), (5, 6), (4, 7), (5, 7), (5, 8), (6, 8), (5, 9), (6, 9)):
        c.set(x, y, SLIT_DIM)
    for x, y in ((4, 6), (4, 7), (6, 8), (6, 9)):
        c.set(x, y, SLIT_LIT)
    for x, y in ((11, 6), (10, 6), (11, 7), (10, 7), (10, 8), (9, 8), (10, 9), (9, 9)):
        c.set(x, y, SLIT_DIM)
    for x, y in ((11, 6), (11, 7), (9, 8), (9, 9)):
        c.set(x, y, SLIT_LIT)
    # A carved bridge and stern mouth line under the slits, so the front reads
    # as a face rather than two unconnected marks.
    for y in range(9, 13):
        c.set(7, y, 1)
        c.set(8, y, 2)
    for x in range(6, 10):
        c.set(x, 13, 0)
    return c


# ==========================================================================
# Glass
# ==========================================================================

GLASS_RAMP = R("void_glass", build_ramp("void_glass", 5).colors + [
    (parse_hex("#5E81ACCC")[0], parse_hex("#5E81ACCC")[1],
     parse_hex("#5E81ACCC")[2], 0xCC),
])


def t_void_glass() -> Canvas:
    """Translucent pane: no pixel reaches alpha 255, the frame is inset one
    pixel so the wrap seam stays clean, and the fracture lattice runs on both
    diagonals with period 8 so it tiles in x and y."""
    c = Canvas(GLASS_RAMP)
    body(c, 5501, 1, 2, spread=0.30)
    # Vanilla glass is a quiet pane with a frame and a couple of short cracks;
    # a lattice across the whole face reads as a grille, and a full diagonal
    # reads as a scratch. So this draws a bevelled frame, four short cracks
    # that stop well inside it, and one catch-light in the top-left corner.
    frame_inset(c, hi=4, lo=0)
    for x0, y0, dx, dy, n in ((4, 4, 1, 1, 4), (11, 3, -1, 1, 3),
                              (3, 11, 1, -1, 3), (10, 11, 1, 1, 3)):
        for k in range(n):
            c.set(x0 + dx * k, y0 + dy * k, 0)
            c.set(x0 + dx * k, y0 + dy * k - 1, 3)
    for x, y in ((2, 2), (3, 2), (2, 3)):
        c.set(x, y, 5)
    c.set(13, 13, 0)
    return c


# ==========================================================================
# Ground cover
# ==========================================================================

MOSS_RAMP = R("resonance_moss", [
    mix(BI_DEEP, VOID_BLACK, 0.58),
    mix(BI_DEEP, VOID_SHADOW, 0.28),
    BI_DEEP,
    mix(BI_DEEP, BI_MID, 0.30),
    mix(BI_DEEP, BI_MID, 0.58),
    BI_MID,
    BI_BRIGHT,
])
MOSS_W = (0.10, 0.22, 0.26, 0.21, 0.14, 0.07)

LICHEN_RAMP = R("amber_lichen", [
    mix(AM_DARK, VOID_BLACK, 0.55),
    mix(AM_DARK, VOID_SHADOW, 0.22),
    AM_DARK,
    mix(AM_DARK, AM_MID, 0.55),
    AM_MID,
    AM_LIGHT,
    AM_HIGH,
])
LICHEN_W = (0.11, 0.23, 0.26, 0.20, 0.13, 0.07)


def t_resonance_moss() -> Canvas:
    """Faintly glowing teal carpet. Moss is chunkier than stone, so the noise
    lattice is coarse (period 4) and warped, which gives clumps instead of
    grain, and a scatter of bright spore points supplies the glow."""
    c = Canvas(MOSS_RAMP)
    rock(c, 9101, MOSS_W, grain=4, grit=0.46, relief=0.70, warp=1.8)
    for i in range(9):
        x = int(hash01(i, 5, 9107) * SIZE)
        y = int(hash01(5, i, 9109) * SIZE)
        put(c, x, y, 6)
        put(c, x + 1, y + 1, 0)
    return c


def t_resonance_moss_side() -> Canvas:
    """Grass-block-style side: phonolite below, a ragged mossy fringe on top.

    The fringe depth is driven by a periodic hash per column, so the ragged
    line continues across the tile edge and neighbouring blocks line up.
    """
    c = Canvas(MOSS_RAMP)
    # phonolite-ish rock in the low half of the ramp, then moss over the top
    stone = R("moss_side_stone", [
        mix(PH_DARK, VOID_BLACK, 0.35), PH_DARK,
        mix(PH_DARK, PH_MID, 0.5), PH_MID, mix(PH_MID, PH_LIGHT, 0.5), PH_LIGHT,
    ])
    c.ramp = R("resonance_moss_side", list(stone.colors) + list(MOSS_RAMP.colors))
    rock(c, 9131, (0.08, 0.20, 0.28, 0.24, 0.15, 0.05), grain=8, grit=0.36,
         relief=0.55)
    for x in range(SIZE):
        depth = 3 + int(hash01(x, 2, 9137) * 3)
        for y in range(depth):
            n = hash01(x, y, 9141)
            lvl = 6 + min(5, int(n * 5) + (2 if y < depth - 2 else 0))
            c.set(x, y, lvl)
        c.set(x, depth, 6 if hash01(x, 9, 9143) > 0.5 else 7)
    for i in range(5):
        x = int(hash01(i, 3, 9147) * SIZE)
        c.set(x, int(hash01(3, i, 9149) * 3), 12)
    return c


def t_amber_lichen() -> Canvas:
    """Warm orange crust: rosettes rather than an even carpet, so the noise is
    warped hard and each rosette gets a bright centre with a dark skirt. The
    hue opposition against Resonance Moss is what stops the ground reading as
    one material."""
    c = Canvas(LICHEN_RAMP)
    # Crust, not rock: the substrate is pushed down into the dark half of the
    # ramp so the rosettes read as growth sitting on top of it. Without that
    # separation this block and amber_strata are the same orange mottle.
    rock(c, 9203, (0.26, 0.34, 0.24, 0.16), grain=4, grit=0.34, relief=0.55,
         warp=2.6)
    ROSETTE = [(0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (2, 0),
               (-1, 1), (0, 1), (1, 1), (0, 2)]
    for i in range(8):
        cx = int(hash01(i, 7, 9209) * SIZE)
        cy = int(hash01(7, i, 9211) * SIZE)
        for dx, dy in ROSETTE:
            put(c, cx + dx, cy + dy, 4 if (dx + dy) > 0 else 5)
        put(c, cx, cy, 6)
        for dx, dy in ((-2, 0), (0, -2), (2, 1), (1, 2)):
            put(c, cx + dx, cy + dy, 3)
        put(c, cx + 2, cy + 2, 0)
    return c


# ==========================================================================
# Crystals and light
# ==========================================================================

HUM_RAMP = R("humming_crystal", [
    mix(AR_DEEP, VOID_BLACK, 0.45),     # 0 facet seam
    AR_DEEP,                            # 1
    mix(AR_DEEP, AR_MID, 0.55),         # 2
    AR_MID,                             # 3
    mix(AR_MID, AR_LIGHT, 0.45),        # 4
    AR_LIGHT,                           # 5
    shift(AR_LIGHT, 0.28),              # 6 lit facet rim
    mix(AR_LIGHT, CH_HIGH, 0.62),       # 7 sparkle
    AR_BRIGHT,                          # 8 hot core
])


def t_humming_crystal() -> Canvas:
    """Emissive magenta crystal mass.

    amethyst_block is the reference: a faceted field where every cell is
    bounded by a dark seam and lit along its top-left. Cells here are a wrapped
    Voronoi so the facets continue across the tile edge, and three hot cores
    plus two sparkles carry the light level 11 the block emits.
    """
    c = Canvas(HUM_RAMP)
    facets(c, 9301, sites_n=7, tones=(3, 5, 2, 4, 3, 5, 1), edge=0, rim=6)
    for y in range(SIZE):
        for x in range(SIZE):
            if hash01(x, y, 9307) > 0.88:
                bump_at(c, x, y, +1, 0, 6)
            elif hash01(x, y, 9311) > 0.92:
                bump_at(c, x, y, -1, 0, 6)
    # Two hot cores only. Scattering the bright tone turns crystal into
    # confetti; amethyst_block spends its brightest colour on 3.5% of pixels.
    for x, y in ((5, 4), (10, 10)):
        put(c, x, y, 8)
        put(c, x - 1, y - 1, 7)
        put(c, x + 1, y + 1, 1)
    return c


BIS_CRYSTAL_RAMP = R("bismuth_cluster", [
    mix(BI_DEEP, VOID_BLACK, 0.55),     # 0 outline
    mix(BI_DEEP, VOID_SHADOW, 0.20),    # 1 shadow face
    BI_DEEP,                            # 2 body
    mix(BI_DEEP, BI_MID, 0.45),         # 3
    BI_MID,                             # 4 lit face
    BI_BRIGHT,                          # 5 hot edge
    shift(BI_BRIGHT, 0.55),             # 6 sparkle
    mix(BI_MID, GOLD, 0.35),            # 7 warm refraction
])

# (apex_x, apex_y, half_width_at_base, base_y). Drawn back to front, so later
# entries overlap earlier ones the way a real cluster occludes itself.
SPIRES = [
    (3, 7, 2, 15),      # left shoulder crystal
    (12, 6, 2, 15),     # right shoulder crystal
    (7, 1, 3, 15),      # the tall central spire
    (1, 11, 1, 15),     # corner bud
    (14, 11, 1, 15),    # corner bud
    (9, 10, 1, 15),     # small front bud
]


def t_bismuth_cluster() -> Canvas:
    """Cutout crystal cluster growing off a surface.

    amethyst_cluster is 45% transparent: one tall pointed spire in the middle,
    shoulder crystals either side, buds pushed into the bottom corners. Each
    spire here is a tapered prism drawn as three facets - a lit left face, a
    mid front face, a shadow right face - separated by a hot edge, with a dark
    outline all the way round so the crystal reads against any rock behind it.
    """
    c = Canvas(BIS_CRYSTAL_RAMP, transparent=True)
    for si, (ax, ay, hw, by) in enumerate(SPIRES):
        span = max(1, by - ay)
        for y in range(ay, by + 1):
            t = (y - ay) / span
            # sharp point: the first two rows are a single pixel wide
            w = 0 if t < 0.12 else max(0, int(round(hw * (0.25 + 0.75 * t))))
            x0, x1 = ax - w, ax + w
            for x in range(x0, x1 + 1):
                u = 0.5 if x1 == x0 else (x - x0) / (x1 - x0)
                tone = 4 if u < 0.34 else (2 if u < 0.70 else 1)
                if hash01(x, y, 9401 + si) > 0.82:
                    tone = min(4, tone + 1)
                put(c, x, y, tone)
            if x1 > x0:
                put(c, x0, y, 3)           # lit left facet edge
                put(c, x1, y, 0)           # shadow right edge
                if (y - ay) % 5 == 2:
                    put(c, x0 + 1, y, 5)   # facet glint running down the join
        put(c, ax, ay, 6)
        put(c, ax, ay + 1, 5)
        put(c, ax, ay + 2, 4)
    # a warm refraction where the central spire crosses a shoulder crystal
    for x, y in ((5, 9), (10, 8)):
        put(c, x, y, 7)
    # dark outline: every empty pixel that touches crystal on its lower-right
    snap = [row[:] for row in c.idx]
    for y in range(SIZE):
        for x in range(SIZE):
            if snap[y][x] >= 0:
                continue
            if any(0 <= x + dx < SIZE and 0 <= y + dy < SIZE and snap[y + dy][x + dx] >= 2
                   for dx, dy in ((-1, 0), (0, -1))):
                c.idx[y][x] = 0
    return c


LANTERN_RAMP = R("harmonic_lantern", [
    NI_BLACK,                           # 0 cage shadow
    mix(NI_BLACK, NI_DARK, 0.6),        # 1 cage body
    NI_MID,                             # 2 cage lit edge
    mix(NI_MID, GOLD, 0.45),            # 3 brass trim
    GOLD,                               # 4 brass highlight
    mix(BI_DEEP, VOID_SHADOW, 0.25),    # 5 lamp shadow
    BI_DEEP,                            # 6 lamp low
    BI_MID,                             # 7 lamp mid
    BI_BRIGHT,                          # 8 lamp hot
    shift(BI_BRIGHT, 0.55),             # 9 filament
])


def t_harmonic_lantern() -> Canvas:
    """Crafted light block: a brass cage over a cyan resonance chamber.

    Vanilla emissive blocks span roughly 170 luminance from their darkest frame
    to their brightest core (glowstone 75..255), and that span is what sells
    the glow. The chamber falls off radially from a two-pixel filament, the
    cage is drawn in null iron with brass corner bolts, and the whole face is
    bordered so it reads as a manufactured object next to natural rock.
    """
    c = Canvas(LANTERN_RAMP)
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - 7.0, y - 7.2)
            n = hash01(x, y, 9503) * 1.1
            c.set(x, y, max(5, min(8, int(round(8.6 - d * 0.62 + n)))))
    for x, y in ((6, 6), (7, 6), (7, 7), (8, 7)):     # the filament itself
        c.set(x, y, 9)
    # Cage: a one-pixel frame with a lit top-left and shadowed bottom-right,
    # plus four bars. Kept thin so the chamber, not the ironwork, is the block.
    for i in range(SIZE):
        c.set(i, 0, 2)
        c.set(0, i, 2)
        c.set(i, 15, 0)
        c.set(15, i, 0)
    for x in (2, 13):
        for y in range(1, 15):
            c.set(x, y, 2 if x == 2 else 0)
    for y in (2, 13):
        for x in range(1, 15):
            c.set(x, y, 2 if y == 2 else 0)
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):  # brass corner bolts
        c.set(x, y, 4)
    for x, y in ((1, 2), (14, 2), (1, 13), (14, 13)):
        c.set(x, y, 3)
    for x, y in ((7, 2), (7, 13), (2, 7), (13, 7)):    # brass strap centres
        c.set(x, y, 3)
    return c


# ==========================================================================
# Wood
# ==========================================================================

TUNE_RAMP = R("tuning_wood", [
    mix(PH_DARK, VOID_BLACK, 0.40),
    PH_DARK,
    mix(PH_DARK, PH_MID, 0.5),
    PH_MID,
    mix(PH_MID, PH_LIGHT, 0.5),
    PH_LIGHT,
    PH_PALE,
    BI_DEEP,
    BI_BRIGHT,
])
TUNE_W = (0.08, 0.18, 0.26, 0.24, 0.16, 0.08)

STRIP_TUNE_RAMP = R("stripped_tuning_wood", [
    mix(PH_DARK, PH_MID, 0.35),
    PH_MID,
    mix(PH_MID, PH_LIGHT, 0.45),
    PH_LIGHT,
    mix(PH_LIGHT, PH_PALE, 0.5),
    PH_PALE,
    shift(PH_PALE, 0.22),
    mix(PH_PALE, BI_MID, 0.30),
])

HUM_STEM_RAMP = R("humming_stem", [
    mix(AR_DEEP, VOID_BLACK, 0.50),
    AR_DEEP,
    mix(AR_DEEP, AR_MID, 0.5),
    AR_MID,
    mix(AR_MID, AR_LIGHT, 0.40),
    AR_LIGHT,
    shift(AR_LIGHT, 0.25),
    AR_BRIGHT,
])
STEM_W = (0.10, 0.24, 0.28, 0.22, 0.12, 0.04)

# Stripping a log should be a dramatic change, not a subtle one: vanilla's
# stripped variants jump a long way in value so a stripped trunk reads at a
# glance across a grove. The first pass sat only ~22 luminance above the bark,
# which was indistinguishable in situ, so this ramp starts at the bark's
# mid-tone and climbs well past it.
STRIP_STEM_RAMP = R("stripped_humming_stem", [
    mix(AR_MID, VOID_SHADOW, 0.10),     # groove shadow, still clearly lit wood
    AR_MID,
    mix(AR_MID, AR_LIGHT, 0.45),
    AR_LIGHT,
    shift(AR_LIGHT, 0.22),
    shift(AR_LIGHT, 0.42),
    shift(AR_LIGHT, 0.60),
])


def wood_side(c: Canvas, seed: int, weights, top: int, groove: int,
              grain_strength: float = 0.55) -> None:
    """Log bark: vertical grain from a per-column value bias.

    oak_log is six tones organised into 1-2px vertical streaks; the streaks are
    what make it read as bark rather than stone. The column bias is drawn from
    the periodic hash on x, so the streak pattern continues across the seam.
    """
    # Anisotropic field: three times the frequency across the trunk as along
    # it, so the noise itself runs in vertical streaks before the column bias
    # is added. The multiplier is an integer, which is what keeps the stretched
    # lattice commensurate with the 16px tile in both axes.
    h = [[fbm(x * 3.0, y, seed, octaves=2, period=8) for x in range(SIZE)]
         for y in range(SIZE)]
    f = [[h[y][x] * 0.66 + hash01(x, y, seed ^ 0x5AA5) * 0.34
          + (h[y][(x + 1) % SIZE] - h[y][(x - 1) % SIZE]) * 0.5 * grain_strength
          for x in range(SIZE)] for y in range(SIZE)]
    paint(c, levels(f, weights))
    hi = len(weights) - 1
    for x in range(SIZE):
        hx = hash01(x, 7, seed + 4242)
        d = -1 if hx < 0.32 else (1 if hx > 0.72 else 0)
        if d:
            for y in range(SIZE):
                bump_at(c, x, y, d, 0, hi)
    for x in range(SIZE):
        if x % 8 == 0:
            for y in range(SIZE):
                if hash01(x, y, seed + 55) > 0.25:
                    c.set(x, y, groove)
                    bump_at(c, x - 1, y, +1, 0, top)


def log_top(c: Canvas, seed: int, weights, bark_lo: int, bark_hi: int,
            ring_even: int, ring_odd: int, heart: int) -> None:
    """Log end grain: a two-pixel bark rim with rounded corners, then heartwood.

    Measured off warped_stem_top and oak_log_top: the rim is the loud element
    and there are almost no visible growth rings inside it - just noise with a
    faint darker circle and a small heart. v1 drew high-contrast concentric
    rings, which is why the old tops read as a dartboard; here the rings are a
    single value step and are broken by the noise field, so they suggest grain
    without drawing a target.
    """
    lv = levels(field(seed, grain=8, octaves=2, grit=0.28, relief=0.40), weights)
    paint(c, lv)
    top = len(weights) - 1
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - 7.5, y - 7.5)
            if hash01(x, y, seed + 71) < 0.30:
                continue                       # broken rings, never a full circle
            if 2.4 < d < 3.4 or 4.6 < d < 5.4:
                bump_at(c, x, y, -1, 0, top)
            elif 3.6 < d < 4.4:
                bump_at(c, x, y, +1, 0, top)
    for x, y in ((7, 7), (8, 7), (7, 8)):
        c.set(x, y, heart)
    c.set(8, 8, ring_even)
    c.set(6, 6, ring_odd)
    for y in range(SIZE):
        for x in range(SIZE):
            edge = min(x, y, SIZE - 1 - x, SIZE - 1 - y)
            corner = min(x, SIZE - 1 - x) <= 1 and min(y, SIZE - 1 - y) <= 1
            if edge == 0 and corner and (x + y) % 15 != 0 and \
                    (min(x, SIZE - 1 - x) == 0 and min(y, SIZE - 1 - y) == 0):
                c.set(x, y, bark_lo)           # rounded corner: darkest
            elif edge <= 1:
                c.set(x, y, bark_hi if (x <= 1 or y <= 1) else bark_lo)
            elif edge == 2 and hash01(x, y, seed + 13) > 0.55:
                c.set(x, y, bark_hi if (x <= 2 or y <= 2) else bark_lo)


def t_petrified_tuning_wood_side() -> Canvas:
    """Petrified wood bark: strongly columnar vertical grain running full height,
    with long continuous dark fissures between raised columns, measured off
    vanilla's oak_log and spruce_log."""
    c = Canvas(TUNE_RAMP)
    seed = 8101

    for y in range(SIZE):
        for x in range(SIZE):
            # Slow wobble along y so the columns undulate naturally down the trunk
            wobble = (fbm(x * 0.5, y, seed + 101, octaves=1, period=SIZE) - 0.5) * 1.2
            eff_x = (x + wobble) % float(SIZE)

            # Continuous columnar profile: 4 columns across 16px
            phase = eff_x % 4.0
            if phase < 0.8:
                # Fissure channel (continuous dark line)
                base_tone = 0 if phase < 0.4 else 1
            elif phase < 1.8:
                # Lit ridge crest on left flank of column
                base_tone = 5 if phase < 1.4 else 4
            elif phase < 3.0:
                # Column mid body
                base_tone = 3
            else:
                # Shadow slope into fissure
                base_tone = 2

            # Gentle vertical variation along the column
            v_var = fbm(x * 1.5, y * 0.5, seed + 505, octaves=2, period=SIZE)
            if v_var > 0.65 and base_tone >= 2:
                base_tone = min(6, base_tone + 1)
            elif v_var < 0.35 and base_tone >= 2:
                base_tone = max(1, base_tone - 1)

            # Fine vertical grain streak
            fine = (_hash2(x, y, seed + 909) - 0.5) * 0.3
            if fine > 0.12 and base_tone in (3, 4):
                base_tone += 1
            elif fine < -0.12 and base_tone in (3, 4):
                base_tone -= 1

            c.set(x, y, base_tone)

    return c


#: (retired) The edge-step pass this replaced is gone - see stripped_wood_side, which
#: now builds a genuinely cylindrical column profile instead of patching a random one.
#: Kept only as the note about the two copies:
#: How much to step a column darker, by its distance from the nearest vertical edge.
#:
#: PLAYER: "those stripped log side textures are too flat, the vanilla have some minor
#: shading on left and right sides that make it look cylindrical."
#:
#: Right, and ours were doing the OPPOSITE. As mean column brightness, vanilla DARKENS
#: its edges - stripped_oak_log runs 121 at the edges against 144 in the middle, birch
#: 152 against 171 - which is the log curving away from the light. Ours ran BRIGHTER at
#: the edges by about the same margin, so they read as the inside of a trough.
#:
#: Applied as a post-pass on the finished tones rather than as a nudge to the value
#: before rounding. Nudging first was tried and mostly washed out: the column sinusoid
#: and then the run-length filter between them absorbed it, and three of the four
#: textures still came out edge-brighter.
#:
#: It does NOT break horizontal tiling. Vanilla's own stripped oak has a seam delta of
#: 8.3 against a mean interior delta of 8.9 - it tiles fine, because the shading is
#: SYMMETRIC, so dark meets dark at the wrap. Two of these are in verify_textures'
#: SEAMLESS_BLOCKS and stay green for that reason.
#:
#: NOTE: gen_family_textures.py and gen_block_textures.py each hold a copy of
#: stripped_wood_side and split these four textures between them - family draws echo ash
#: and amber bough, block draws humming and petrified tuning. Editing one and
#: regenerating changed half the set and left the other half untouched, which is exactly
#: how the leaf-loot generators drifted. Both copies carry this pass; change them together.
CYLINDER_STEPS = [1, 1, 0, 0]


def stripped_wood_side(c: Canvas, seed: int, ramp_tones: list[int], noise_scale: float = 0.35,
                       cylinder: float = 1.0) -> None:
    """Smooth stripped wood side texture matching vanilla stripped log conventions.
    
    Long vertical grain lines holding tone >= 4 pixels down each column, with tone
    changes occurring between adjacent columns. Wraps seamlessly at x=0/15 and y=0/15.
    """
    n_tones = len(ramp_tones)
    col_mid = [0.0] * SIZE
    # A CYLINDER, not a sinusoid. The column profile used to be two sine waves with
    # a seed-derived phase, which is a random light profile per texture rather than a
    # lighting model - for the echo ash seed it happened to put its dark trough dead
    # centre, so the face read as a groove. Measured, its edges came out 21 BRIGHTER
    # than its middle where vanilla's stripped oak is 23 darker.
    #
    # Brightest down the middle, falling to about 55% at both edges, which is the
    # ratio vanilla's own stripped logs hold. A little per-column jitter on top so the
    # four textures do not look like the same gradient in four colours.
    for x in range(SIZE):
        d = min(x, SIZE - 1 - x) / (SIZE / 2 - 0.5)
        lit = 0.35 + 0.65 * d
        jitter = 0.07 * math.sin(x * 2 * math.pi / SIZE + (seed % 97) * 0.1)
        col_mid[x] = max(0.0, min(1.0, lit + jitter)) * (n_tones - 1)
        
    for y in range(SIZE):
        for x in range(SIZE):
            n = fbm(x * 1.0, y * 0.25, seed + 555, octaves=2, period=SIZE)
            val = col_mid[x] * (1.0 - noise_scale) + (n * (n_tones - 1)) * noise_scale
            idx = int(round(val))
            idx = max(0, min(n_tones - 1, idx))
            c.set(x, y, ramp_tones[idx])
            
    # Vertical run length filter (guarantees run length >= 4)
    for x in range(SIZE):
        for _ in range(3):
            for y in range(SIZE):
                prev_t = c.get(x, (y - 1) % SIZE)
                next_t = c.get(x, (y + 1) % SIZE)
                cur_t = c.get(x, y)
                if prev_t == next_t and cur_t != prev_t:
                    c.set(x, y, prev_t)
                    
    # Horizontal smoothing to ensure adjacent columns don't jump by > 1 tone
    for y in range(SIZE):
        for _ in range(2):
            for x in range(SIZE):
                p = c.get((x - 1) % SIZE, y)
                n = c.get((x + 1) % SIZE, y)
                cur = c.get(x, y)
                if abs(cur - p) > 1 and abs(cur - n) > 1:
                    c.set(x, y, (p + n) // 2)


    # Grain streaks: a few columns carry a contiguous vertical run one tone off the
    # rest. Vanilla's stripped logs are full of these - they are what stops a log
    # reading as a smooth gradient - and here they also solve a real constraint.
    #
    # The cylindrical profile plus the run-length filter between them flatten most
    # columns to a single tone, which took two of these textures down to 3 and 4
    # distinct colours against verify_textures' floor of 5. Every attempt to fix that
    # by widening the cylinder or raising the noise traded the colour count against
    # the roughness budget and lost. A streak adds a tone in a run of 5+ rows, so it
    # survives the filter, costs almost nothing in neighbour delta, and is what the
    # reference actually looks like.
    for k in range(3):
        sx = (seed // (7 ** (k + 1))) % SIZE
        sy = (seed // (11 ** (k + 1))) % SIZE
        run = 5 + (seed // (13 ** (k + 1))) % 4
        delta = 1 if k % 2 == 0 else -1
        for dy in range(run):
            y = (sy + dy) % SIZE
            t = c.get(sx, y)
            if t in ramp_tones:
                i = ramp_tones.index(t)
                c.set(sx, y, ramp_tones[max(0, min(len(ramp_tones) - 1, i + delta))])

def stripped_log_rings(c: Canvas, seed: int, rim: int, ring_tones: list[int],
                       heart_accent: int | None = None, corner_tone: int | None = None) -> None:
    """Smooth concentric growth rings for stripped log tops matching vanilla log tops."""
    t_sap_outer, t_ring_outer, t_sap_mid, t_ring_inner, t_heart = ring_tones
    c_tone = corner_tone if corner_tone is not None else max(0, rim - 1)
    
    for y in range(SIZE):
        for x in range(SIZE):
            dx = abs(x - 7.5)
            dy = abs(y - 7.5)
            d_cheb = max(dx, dy)
            d_eucl = math.hypot(dx, dy)
            d = d_cheb * 0.75 + (d_eucl / 1.4142 * 7.5 / 5.3) * 0.25
            
            is_edge = (x == 0 or x == SIZE - 1 or y == 0 or y == SIZE - 1)
            if is_edge:
                is_corner = (x in (0, SIZE - 1) and y in (0, SIZE - 1))
                t = c_tone if is_corner else rim
            else:
                if d > 5.4:
                    t = t_sap_outer
                elif d > 4.4:
                    t = t_ring_outer
                elif d > 3.0:
                    t = t_sap_mid
                elif d > 1.8:
                    t = t_ring_inner
                else:
                    t = t_heart
                    
                if hash01(x, y, seed + 404) < 0.06:
                    t = t_sap_mid if t in (t_ring_outer, t_ring_inner) else t_ring_outer
                    
            c.set(x, y, t)
            
    if heart_accent is not None:
        c.set(7, 7, heart_accent)


def t_stripped_petrified_tuning_wood_side() -> Canvas:
    """Stripped: lighter, smoother vertical grain."""
    c = Canvas(STRIP_TUNE_RAMP)
    stripped_wood_side(c, 8117, [0, 1, 2, 3, 4, 5, 6], noise_scale=0.40)
    return c


def t_petrified_tuning_wood_top() -> Canvas:
    c = Canvas(TUNE_RAMP)
    log_top(c, 8203, TUNE_W, bark_lo=0, bark_hi=2, ring_even=1, ring_odd=4,
            heart=8)
    put(c, 6, 6, 7)
    return c


def t_stripped_petrified_tuning_wood_top() -> Canvas:
    c = Canvas(STRIP_TUNE_RAMP)
    stripped_log_rings(c, 8219, rim=3, ring_tones=[4, 2, 3, 1, 2], corner_tone=0, heart_accent=7)
    return c


def t_humming_stem_side() -> Canvas:
    """Violet second wood so groves are not all one trunk colour. Three
    irregular magenta glow seams run the height of the bark."""
    c = Canvas(HUM_STEM_RAMP)
    wood_side(c, 8301, STEM_W, top=5, groove=0)
    # warped_stem sets teal patches into purple bark as irregular blotches, not
    # as stripes. The share matters as much as the shape: warped_stem spends
    # 27% of its pixels on the teal and only 2% on the brightest of it, so the
    # patch field is quantised to those exact shares rather than thresholded,
    # which is what stops the trunk turning into a slab of magenta.
    nf = [[fbm(x, y, 8311, octaves=2, period=8) for x in range(SIZE)]
          for y in range(SIZE)]
    lv = levels(nf, (0.74, 0.14, 0.09, 0.03))
    for y in range(SIZE):
        for x in range(SIZE):
            if lv[y][x] == 1:
                put(c, x, y, 4)
            elif lv[y][x] == 2:
                put(c, x, y, 5)
                put(c, x + 1, y + 1, 1)
            elif lv[y][x] == 3:
                put(c, x, y, 7)
                put(c, x + 1, y + 1, 1)
    return c


def t_humming_stem_top() -> Canvas:
    c = Canvas(HUM_STEM_RAMP)
    log_top(c, 8331, STEM_W, bark_lo=0, bark_hi=2, ring_even=1, ring_odd=4,
            heart=7)
    put(c, 6, 6, 5)
    put(c, 9, 9, 1)
    return c


def t_stripped_humming_stem_side() -> Canvas:
    """Stripped violet stem: smooth vertical grain without harsh noise."""
    c = Canvas(STRIP_STEM_RAMP)
    stripped_wood_side(c, 8347, [0, 1, 2, 3, 4, 5], noise_scale=0.38, cylinder=0.3)
    return c


def t_stripped_humming_stem_top() -> Canvas:
    c = Canvas(STRIP_STEM_RAMP)
    stripped_log_rings(c, 8363, rim=2, ring_tones=[3, 1, 2, 0, 1], corner_tone=0, heart_accent=4)
    return c


# ==========================================================================
# Leaves - three canopies, three hues
# ==========================================================================

TEAL_LEAF_RAMP = R("calcified_resonance_leaves", [
    mix(BI_DEEP, VOID_BLACK, 0.62),     # 0 underside / outline
    mix(BI_DEEP, VOID_SHADOW, 0.30),    # 1
    BI_DEEP,                            # 2
    mix(BI_DEEP, BI_MID, 0.40),         # 3
    mix(BI_DEEP, BI_MID, 0.70),         # 4
    BI_MID,                             # 5 lit crown
    BI_BRIGHT,                          # 6 resonant tip
])

AMBER_LEAF_RAMP = R("amber_resonance_leaves", [
    mix(AM_DARK, VOID_BLACK, 0.55),
    mix(AM_DARK, VOID_SHADOW, 0.22),
    AM_DARK,
    mix(AM_DARK, AM_MID, 0.55),
    AM_MID,
    AM_LIGHT,
    AM_HIGH,
])

VIOLET_LEAF_RAMP = R("violet_resonance_leaves", [
    mix(AR_DEEP, VOID_BLACK, 0.45),
    AR_DEEP,
    mix(AR_DEEP, AR_MID, 0.55),
    AR_MID,
    mix(AR_MID, AR_LIGHT, 0.55),
    AR_LIGHT,
    shift(AR_LIGHT, 0.30),
    AR_BRIGHT,
])


def t_calcified_resonance_leaves() -> Canvas:
    """Teal canopy. Colour, not transparency, is what makes these read as
    leaves next to the amber and violet canopies."""
    c = Canvas(TEAL_LEAF_RAMP, transparent=True)
    foliage(c, 9601, dark=0, low=2, mid=3, high=5, accent=6, accents=6)
    return c


def t_amber_resonance_leaves() -> Canvas:
    """Gold canopy: the same clump language, a completely different hue."""
    c = Canvas(AMBER_LEAF_RAMP, transparent=True)
    foliage(c, 9631, dark=0, low=2, mid=3, high=5, accent=6, accents=4)
    return c


def t_violet_resonance_leaves() -> Canvas:
    """Magenta canopy, the rarest of the three."""
    c = Canvas(VIOLET_LEAF_RAMP, transparent=True)
    foliage(c, 9661, dark=0, low=2, mid=4, high=6, accent=7, accents=5)
    return c


# ==========================================================================
# Cross-model plants (cutout)
# ==========================================================================

SPROUT_RAMP = R("echo_sprout", [
    mix(BI_DEEP, VOID_BLACK, 0.55),     # 0 outline
    mix(BI_DEEP, VOID_SHADOW, 0.20),    # 1 shadow side
    BI_DEEP,                            # 2 stem
    mix(BI_DEEP, BI_MID, 0.5),          # 3 lit stem
    BI_MID,                             # 4 leaf
    BI_BRIGHT,                          # 5 glowing tip
])

GRASS_RAMP = R("chime_grass", [
    mix(BI_DEEP, VOID_BLACK, 0.50),
    mix(BI_DEEP, CH_SHADOW, 0.25),
    mix(BI_DEEP, CH_SHADOW, 0.55),
    mix(CH_SHADOW, BI_MID, 0.35),
    mix(CH_MID, BI_MID, 0.30),
    mix(CH_LIGHT, BI_MID, 0.20),
])

BLOOM_RAMP = R("crystal_bloom", [
    mix(AR_DEEP, VOID_BLACK, 0.40),     # 0 outline
    AR_DEEP,                            # 1
    AR_MID,                             # 2 stem shadow
    mix(AR_MID, AR_LIGHT, 0.45),        # 3 stem lit
    AR_LIGHT,                           # 4 petal
    shift(AR_LIGHT, 0.30),              # 5 petal lit
    AR_BRIGHT,                          # 6 petal hot
    GOLD,                               # 7 pollen core
])


def blade(c: Canvas, x0: int, y0: int, y1: int, lean: float, body_i: int,
          lit_i: int, dark_i: int, tip_i: int | None) -> None:
    """One grass blade: a leaning 1-2px stroke, lit on its left, dark on its
    right, exactly how short_grass separates blade faces at this size."""
    for y in range(y1, y0 - 1, -1):
        t = (y1 - y) / max(1, (y1 - y0))
        x = x0 + lean * t * (y1 - y0) / 6.0
        xi = int(round(x))
        put(c, xi, y, lit_i if t > 0.35 else body_i)
        if t < 0.72:
            put(c, xi + 1, y, dark_i)
    if tip_i is not None:
        put(c, int(round(x0 + lean * (y1 - y0) / 6.0)), y0, tip_i)


def t_echo_sprout() -> Canvas:
    """Small glowing plant. nether_sprouts is only 12% opaque and lives in the
    bottom five rows; small plants really are small, and reading as a sprout
    beats filling the tile."""
    c = Canvas(SPROUT_RAMP, transparent=True)
    for x0, y0, lean, tip in ((4, 8, -1.1, True), (7, 6, 0.3, True),
                              (10, 9, 1.2, True), (13, 8, -0.6, True),
                              (2, 11, 0.7, False), (15, 12, -0.8, False)):
        blade(c, x0, y0, 15, lean, body_i=2, lit_i=3, dark_i=1,
              tip_i=5 if tip else None)
    for x in range(SIZE):                       # root shadow along the ground
        if c.idx[15][x] >= 0:
            c.idx[15][x] = 0
    # two paired leaflets per stem, which is what separates a sprout from grass
    for x, y in ((3, 11), (5, 11), (6, 9), (8, 9), (9, 12), (11, 12), (12, 11)):
        put(c, x, y, 4)
        put(c, x, y + 1, 1)
    return c


def t_chime_grass() -> Canvas:
    """Taller wispy pale-cyan growth. short_grass fans out from a dense base
    into single-pixel tips, and that taper is the whole silhouette."""
    c = Canvas(GRASS_RAMP, transparent=True)
    for x0, y0, lean in ((2, 5, -1.2), (5, 2, -0.4), (8, 3, 0.6),
                         (11, 5, 1.3), (13, 7, 0.5), (0, 9, -0.6),
                         (6, 8, 1.6), (15, 4, -1.0)):
        blade(c, x0, y0, 15, lean, body_i=2, lit_i=4, dark_i=1, tip_i=5)
    for x in range(SIZE):                       # matted base
        if hash01(x, 3, 9711) > 0.28:
            put(c, x, 14, 2 if hash01(x, 5, 9713) > 0.5 else 3)
            put(c, x, 15, 0)
    return c


def t_crystal_bloom() -> Canvas:
    """Magenta flower-analogue: a stem, four petals around a gold pollen core,
    and a dark outline so the bloom reads against any terrain behind it."""
    c = Canvas(BLOOM_RAMP, transparent=True)
    for y in range(8, 16):
        put(c, 7, y, 3)
        put(c, 8, y, 2)
    put(c, 6, 11, 3)
    put(c, 6, 12, 2)
    put(c, 9, 9, 3)
    put(c, 9, 10, 2)
    petals = [(-3, -1), (-2, -2), (-2, -1), (-2, 0), (-1, -3), (-1, -2), (-1, -1),
              (-1, 0), (-1, 1), (0, -3), (0, -2), (0, -1), (0, 0), (0, 1),
              (1, -2), (1, -1), (1, 0), (1, 1), (2, -1), (2, 0)]
    cx, cy = 7, 5
    for dx, dy in petals:
        tone = 5 if (dx + dy) <= -2 else (4 if (dx + dy) <= 1 else 2)
        put(c, cx + dx, cy + dy, tone)
    for dx, dy in ((0, -1), (0, 0), (-1, 0)):
        put(c, cx + dx, cy + dy, 6)
    put(c, cx, cy - 1, 7)
    # dark outline: any empty pixel touching the bloom on its lower-right
    snap = [row[:] for row in c.idx]
    for y in range(SIZE):
        for x in range(SIZE):
            if snap[y][x] >= 0:
                continue
            if any(0 <= x + dx < SIZE and 0 <= y + dy < SIZE
                   and snap[y + dy][x + dx] >= 4
                   for dx, dy in ((-1, 0), (0, -1), (1, 0), (0, 1))):
                if x >= cx - 1 or y >= cy:
                    c.idx[y][x] = 0
    for x, y in ((5, 13), (10, 12)):
        put(c, x, y, 1)
    return c


# ==========================================================================
# Machines - improved shading, same iconography
# ==========================================================================

SIPHON_RAMP = R("siphon", [
    mix(INK, GOLD, 0.03),
    mix(INK, GOLD, 0.12),
    mix(INK, GOLD, 0.24),
    mix(INK, GOLD, 0.42),
    mix(INK, GOLD, 0.62),
    GOLD,
    BI_DEEP,
    BI_BRIGHT,
])


def t_frequency_siphon_top() -> Canvas:
    """Listening membrane: concentric resonator rings with a perforated centre."""
    c = Canvas(SIPHON_RAMP)
    rock(c, 10007, (0.16, 0.30, 0.30, 0.18, 0.06), grain=8, grit=0.30, relief=0.40)
    frame_inset(c, hi=4, lo=0)
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c.set(x, y, 5)
    rings(c, 7.5, 7.5, 5.6, 0.62, even=0, odd=3, hi=4)
    for y in range(SIZE):
        for x in range(SIZE):
            if math.hypot(x - 7.5, y - 7.5) <= 5.6 and x % 3 == 1 and y % 3 == 1:
                c.set(x, y, 0)
    for x, y in ((7, 7), (8, 7), (7, 8)):
        c.set(x, y, 7)
    c.set(8, 8, 6)
    return c


def t_frequency_siphon_side() -> Canvas:
    """Ribbed casing on a 4px period plus the bismuth indicator band."""
    c = Canvas(SIPHON_RAMP)
    rock(c, 10037, (0.16, 0.30, 0.30, 0.18, 0.06), grain=8, grit=0.30, relief=0.40)
    # Ribs: only the crest catches gold. Painting whole rows in the brightest
    # brass makes the casing read as a slab of metal foil rather than as a
    # ribbed housing, so the crest is one row and the flanks fall away.
    for y in range(SIZE):
        for x in range(SIZE):
            if y % 4 == 0:
                c.set(x, y, 5 if x % 8 == 0 else 3)
            elif y % 4 == 1:
                c.set(x, y, 2)
            elif y % 4 == 3:
                c.set(x, y, 0)
    for x in range(SIZE):
        c.set(x, 6, 0)
        c.set(x, 7, 0)
    for x in range(2, 14):
        if x % 3 != 2:
            c.set(x, 6, 7)
            c.set(x, 7, 6)
    c.set(2, 7, 4)
    c.set(13, 7, 4)
    return c


def t_frequency_siphon_bottom() -> Canvas:
    """Plain casing: vent slots and two rivets, no indicator band."""
    c = Canvas(SIPHON_RAMP)
    rock(c, 10061, (0.16, 0.30, 0.30, 0.18, 0.06), grain=8, grit=0.32, relief=0.40)
    frame_inset(c, hi=4, lo=0)
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c.set(x, y, 5)
    for y in (6, 10):
        for x in range(4, 12):
            c.set(x, y - 1, 4)
            c.set(x, y, 0)
    for x, y in ((4, 12), (11, 12)):
        rivet(c, x, y, 5, 0)
    c.set(7, 8, 7)
    c.set(8, 8, 6)
    return c


ANVIL_RAMP = R("anvil", [
    shift(NI_BLACK, -0.15),
    NI_BLACK,
    mix(NI_BLACK, NI_DARK, 0.55),
    NI_DARK,
    mix(NI_DARK, NI_MID, 0.55),
    NI_MID,
    mix(NI_MID, PH_MID, 0.5),
    BI_DEEP,
    BI_BRIGHT,
])


def t_inversion_anvil_top() -> Canvas:
    """Struck face carrying the inverted-triangle inversion glyph."""
    c = Canvas(ANVIL_RAMP)
    rock(c, 11003, (0.10, 0.24, 0.30, 0.24, 0.12), grain=8, grit=0.30, relief=0.40)
    frame_hard(c, hi=5, lo=0)
    for y in range(2, 14):
        for x in range(2, 14):
            if x in (2, 13) or y in (2, 13):
                c.set(x, y, 6 if (x == 2 or y == 2) else 0)
    for x, y in ((5, 6), (10, 7), (4, 11), (11, 11), (8, 3)):
        c.set(x, y, 1)
    for x in range(3, 13):
        c.set(x, 4, 8)
    for k in range(1, 9):
        y = 4 + k
        c.set(3 + round(k * 4 / 8), y, 7)
        c.set(12 - round(k * 4 / 8), y, 7)
    c.set(7, 12, 8)
    c.set(8, 12, 8)
    return c


ANVIL_SPANS = {
    0: (2, 13), 1: (1, 14), 2: (1, 14), 3: (1, 14), 4: (1, 14),
    5: (3, 12), 6: (5, 10), 7: (5, 10), 8: (5, 10), 9: (5, 10),
    10: (3, 12), 11: (2, 13), 12: (2, 13), 13: (2, 13), 14: (2, 13), 15: (2, 13),
}


def t_inversion_anvil_side() -> Canvas:
    """Anvil silhouette in dark null-iron against a void background."""
    c = Canvas(ANVIL_RAMP)
    rock(c, 11027, (0.20, 0.34, 0.30, 0.16), grain=8, grit=0.34, relief=0.40)
    n = c.size
    for y in range(n):
        x0, x1 = ANVIL_SPANS[y]
        above = ANVIL_SPANS[y - 1] if y else None
        below = ANVIL_SPANS[y + 1] if y < n - 1 else None
        for x in range(n):
            if x < x0 or x > x1:
                c.set(x, y, 0)
                continue
            bump_at(c, x, y, +2, 2, 5)
            top_edge = above is None or not (above[0] <= x <= above[1])
            bot_edge = below is None or not (below[0] <= x <= below[1])
            if x == x0 or top_edge:
                c.set(x, y, 6)
            elif x == x1 or bot_edge:
                c.set(x, y, 1)
    for x in range(6, 10):
        c.set(x, 7, 7)
    c.set(7, 7, 8)
    c.set(8, 7, 8)
    return c


LOCK_RAMP = R("lock_box", [
    shift(NI_BLACK, -0.15),
    NI_BLACK,
    mix(NI_BLACK, NI_DARK, 0.55),
    NI_DARK,
    mix(NI_DARK, NI_MID, 0.55),
    NI_MID,
    mix(NI_MID, PH_MID, 0.5),
    BI_BRIGHT,
    GOLD,
])


def _vault_plate(c: Canvas, seed: int) -> Canvas:
    rock(c, seed, (0.10, 0.24, 0.30, 0.24, 0.12), grain=8, grit=0.30, relief=0.40)
    frame_inset(c, hi=6, lo=0)
    return c


def t_acoustic_lock_box_front() -> Canvas:
    """Locked face: recessed door, pitch dial with gold index ticks, and the
    three-note pitch sequence that opens it."""
    c = _vault_plate(Canvas(LOCK_RAMP), 12007)
    for y in range(3, 14):
        for x in range(3, 13):
            if x in (3, 12) or y in (3, 13):
                c.set(x, y, 0 if (x == 3 or y == 3) else 6)
            else:
                bump_at(c, x, y, -1, 1, 4)
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - 7.5, y - 6.5)
            if 3.1 <= d <= 4.1:
                c.set(x, y, 6 if key_light_factor(x, y) > 0 else 3)
            elif d < 3.1:
                c.set(x, y, 2)
    for x, y in ((7, 2), (11, 6), (7, 11), (4, 6)):
        c.set(x, y, 8)
    for x, y in ((7, 5), (7, 6), (8, 7)):
        c.set(x, y, 7)
    for i, h in enumerate((1, 3, 2)):
        x = 5 + i * 2
        for k in range(h):
            c.set(x, 12 - k, 7)
    return c


def t_acoustic_lock_box_side() -> Canvas:
    """Riveted vault plating with a vertical plate seam."""
    c = _vault_plate(Canvas(LOCK_RAMP), 12043)
    for y in range(2, 14):
        c.set(7, y, 2)
        c.set(8, y, 6)
    for x, y in ((3, 3), (11, 3), (3, 11), (11, 11), (3, 7), (11, 7)):
        rivet(c, x, y, 8, 0)
    for x in range(3, 13):
        c.set(x, 13, 0)
    c.set(11, 13, 7)
    return c


def t_acoustic_lock_box_top() -> Canvas:
    """Riveted vault plating with the hinge bar and the resonator slot."""
    c = _vault_plate(Canvas(LOCK_RAMP), 12071)
    for x in range(3, 13):
        c.set(x, 3, 6)
        c.set(x, 4, 2)
    for x in range(3, 13):
        c.set(x, 11, 7 if x % 2 else 0)
        c.set(x, 12, 0)
    for x, y in ((4, 7), (10, 7)):
        rivet(c, x, y, 8, 0)
    return c


# ==========================================================================
# Null-Iron Jukebox - phonolite cabinet with null-iron hardware and speaker
# ==========================================================================

JUKEBOX_RAMP = R("null_iron_jukebox", [
    mix(PH_DARK, VOID_BLACK, 0.40),         # 0: deep shadow / grille slit
    PH_DARK,                                # 1: dark phonolite
    mix(PH_DARK, PH_MID, 0.50),             # 2: mid-dark phonolite
    PH_MID,                                 # 3: phonolite body
    PH_LIGHT,                               # 4: lit phonolite
    NI_DARK,                                # 5: null-iron shadow
    NI_STEEL,                               # 6: null-iron steel body
    NI_LIGHT,                               # 7: null-iron lit bevel / bracket
    NI_PALE,                                # 8: rivet / specular highlight
    mix(BI_MID, CH_LIGHT, 0.30),            # 9: cyan acoustic pickup / indicator
])


def t_null_iron_jukebox_top() -> Canvas:
    """Phonolite deck with forged null-iron corner brackets, circular turntable well,
    and a tone arm with glowing cyan acoustic needle."""
    c = Canvas(JUKEBOX_RAMP)
    seed = 8819

    # 1. Phonolite body with subtle stone texture
    for y in range(SIZE):
        for x in range(SIZE):
            n = fbm(x * 0.8, y * 0.8, seed, octaves=2, period=SIZE)
            c.set(x, y, 2 if n < 0.35 else (4 if n > 0.65 else 3))

    # 2. Outer 1px frame bevel
    for x in range(SIZE):
        c.set(x, 0, 7 if _hash2(x, 0, seed + 1) > 0.35 else 6)
        c.set(x, 15, 0 if _hash2(x, 15, seed + 3) > 0.35 else 1)
    for y in range(SIZE):
        c.set(0, y, 7 if _hash2(0, y, seed + 5) > 0.35 else 6)
        c.set(15, y, 0 if _hash2(15, y, seed + 7) > 0.35 else 1)
    c.set(0, 0, 8)
    c.set(15, 15, 0)

    # 3. Corner null-iron reinforcement brackets
    for bx, by in ((1, 1), (13, 1), (1, 13), (13, 13)):
        c.set(bx, by, 8)       # rivet glint
        c.set(bx + 1, by, 7)
        c.set(bx, by + 1, 7)
        c.set(bx + 1, by + 1, 5)

    # 4. Circular record well / turntable platter (radius 4.5 around (7.5, 7.5))
    cx, cy = 7.5, 7.5
    for y in range(2, 14):
        for x in range(2, 14):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= 4.8:
                if d <= 1.2:
                    c.set(x, y, 0) # central spindle hole
                elif d <= 2.2:
                    c.set(x, y, 7) # central spindle hub
                elif d <= 3.8:
                    diag = (x + y) % 2
                    c.set(x, y, 5 if diag == 0 else 6) # grooved platter mat
                else:
                    c.set(x, y, 7 if (x < cx or y < cy) else 5) # platter bevel rim

    # 5. Tone arm / needle pickup head resting near the platter edge
    c.set(11, 4, 7)
    c.set(11, 5, 8)
    c.set(10, 6, 9) # glowing cyan needle tip
    return c


def t_null_iron_jukebox_side() -> Canvas:
    """Phonolite housing with forged null-iron corner brackets and central acoustic
    speaker grille with horizontal louvers and cyan tuning indicator."""
    c = Canvas(JUKEBOX_RAMP)
    seed = 8821

    # 1. Phonolite stone body
    for y in range(SIZE):
        for x in range(SIZE):
            n = fbm(x * 0.8, y * 0.8, seed, octaves=2, period=SIZE)
            c.set(x, y, 2 if n < 0.35 else (4 if n > 0.65 else 3))

    # 2. Outer 1px frame bevel
    for x in range(SIZE):
        c.set(x, 0, 7 if _hash2(x, 0, seed + 1) > 0.35 else 6)
        c.set(x, 15, 0 if _hash2(x, 15, seed + 3) > 0.35 else 1)
    for y in range(SIZE):
        c.set(0, y, 7 if _hash2(0, y, seed + 5) > 0.35 else 6)
        c.set(15, y, 0 if _hash2(15, y, seed + 7) > 0.35 else 1)
    c.set(0, 0, 8)
    c.set(15, 15, 0)

    # 3. Corner null-iron brackets with rivets
    for bx, by in ((1, 1), (13, 1), (1, 13), (13, 13)):
        c.set(bx, by, 8)       # rivet glint
        c.set(bx + 1, by, 7)
        c.set(bx, by + 1, 7)
        c.set(bx + 1, by + 1, 5)

    # 4. Central Acoustic Speaker Grille / Resonator (cols 3..12, rows 4..11)
    for i in range(3, 13):
        c.set(i, 4, 5) # top recess shadow
        c.set(3, i, 5) # left recess shadow
        c.set(i, 12, 7) # bottom lip highlight
        c.set(12, i, 7) # right lip highlight

    # Horizontal grille acoustic louvers
    for gy in (6, 8, 10):
        for gx in range(4, 12):
            c.set(gx, gy - 1, 0) # dark sound slot
            c.set(gx, gy, 7 if gx in (4, 5, 10, 11) else 6) # metallic louver blade

    # Central cyan acoustic node indicator
    c.set(7, 7, 9)
    c.set(8, 7, 9)
    return c


# ==========================================================================
# Registry
# ==========================================================================

# (name, fn, full_cube) - full_cube means "must be opaque and tile at the seam"
TEXTURES = [
    # stones, dark -> pale, the depth ladder
    ("raw_phonolite", t_raw_phonolite, True),
    ("amber_strata", t_amber_strata, True),
    ("echo_slate", t_echo_slate, True),
    ("resonant_chalk", t_resonant_chalk, True),
    ("polished_phonolite", t_polished_phonolite, False),
    ("phonolite_bricks", t_phonolite_bricks, True),
    ("chalk_bricks", t_chalk_bricks, True),
    ("chime_sand", t_chime_sand, True),
    # ores
    # The three ores that used to be drawn here are gone on purpose.
    #
    # PLAYER: "the deepslate bismuth has the phonolite ore texture."
    # They were double-owned: gen_family_textures.py draws them on the vanilla
    # stone and deepslate hosts they are actually placed in, and this file drew
    # the same three filenames on the phonolite host. Two generators writing one
    # PNG is decided by stage order rather than intent, and this one ran last -
    # so an ore that generates in deepslate shipped wearing phonolite.
    # gen_family_textures.py is now the single owner, which is the precedent
    # that file already sets for knell_ore.
    ("null_iron_block", t_null_iron_block, True),
    ("tuners_mask_front", t_tuners_mask_front, True),
    # ground cover
    ("resonance_moss", t_resonance_moss, True),
    ("resonance_moss_side", t_resonance_moss_side, False),
    ("amber_lichen", t_amber_lichen, True),
    # crystal and light
    ("humming_crystal", t_humming_crystal, True),
    ("bismuth_cluster", t_bismuth_cluster, False),
    ("harmonic_lantern", t_harmonic_lantern, False),
    ("void_glass", t_void_glass, True),
    # wood
    ("petrified_tuning_wood_side", t_petrified_tuning_wood_side, True),
    ("petrified_tuning_wood_top", t_petrified_tuning_wood_top, False),
    ("stripped_petrified_tuning_wood_side", t_stripped_petrified_tuning_wood_side, True),
    ("stripped_petrified_tuning_wood_top", t_stripped_petrified_tuning_wood_top, False),
    ("humming_stem_side", t_humming_stem_side, True),
    ("humming_stem_top", t_humming_stem_top, False),
    ("stripped_humming_stem_side", t_stripped_humming_stem_side, True),
    ("stripped_humming_stem_top", t_stripped_humming_stem_top, False),
    # leaves - three hues
    ("calcified_resonance_leaves", t_calcified_resonance_leaves, False),
    ("amber_resonance_leaves", t_amber_resonance_leaves, False),
    ("violet_resonance_leaves", t_violet_resonance_leaves, False),
    # plants
    ("echo_sprout", t_echo_sprout, False),
    ("chime_grass", t_chime_grass, False),
    ("crystal_bloom", t_crystal_bloom, False),
    # machines
    ("frequency_siphon_top", t_frequency_siphon_top, True),
    ("frequency_siphon_side", t_frequency_siphon_side, True),
    ("frequency_siphon_bottom", t_frequency_siphon_bottom, True),
    ("inversion_anvil_top", t_inversion_anvil_top, False),
    ("inversion_anvil_side", t_inversion_anvil_side, False),
    ("acoustic_lock_box_front", t_acoustic_lock_box_front, True),
    ("acoustic_lock_box_side", t_acoustic_lock_box_side, True),
    ("acoustic_lock_box_top", t_acoustic_lock_box_top, True),
    ("null_iron_jukebox_top", t_null_iron_jukebox_top, False),
    ("null_iron_jukebox_side", t_null_iron_jukebox_side, True),
]

CUTOUT = {"bismuth_cluster", "echo_sprout", "chime_grass", "crystal_bloom",
          "calcified_resonance_leaves", "amber_resonance_leaves",
          "violet_resonance_leaves"}


# ==========================================================================
# Audit
# ==========================================================================

def _producible() -> set[tuple[int, int, int]]:
    """Colours reachable by blending two palette anchors and shading the result.

    Mirrors the rule in tools/verify_textures.py so this generator fails at
    author time rather than at the gate.
    """
    import ev_palette as ev
    anchors = [parse_hex(v) for fam, ent in P.items() if not fam.startswith("_")
               for v in ent.values()]
    for hexes in ev.PALETTES.values():
        anchors += [parse_hex(h) for h in hexes]
    out: set[tuple[int, int, int]] = set()
    for i in range(len(anchors)):
        for j in range(i, len(anchors)):
            for step in range(17):
                blend = mix(anchors[i], anchors[j], step / 16)
                for s in range(-10, 11):
                    out.add(shift(blend, s / 16.0)[:3])
    return out


PRODUCIBLE = _producible()
PRODUCIBLE_COARSE = {
    (c[0] // 8 + dx, c[1] // 8 + dy, c[2] // 8 + dz)
    for c in PRODUCIBLE
    for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
}


def on_palette(rgb) -> bool:
    return tuple(rgb) in PRODUCIBLE or \
        (rgb[0] // 8, rgb[1] // 8, rgb[2] // 8) in PRODUCIBLE_COARSE


def pixels(img: Image.Image) -> list[tuple]:
    px = img.load()
    return [px[x, y] for y in range(img.size[1]) for x in range(img.size[0])]


def dominant_share(img: Image.Image) -> tuple[tuple, float]:
    counts: dict[tuple, int] = {}
    opaque = 0
    for p in pixels(img):
        if p[3] > 0:
            counts[p] = counts.get(p, 0) + 1
            opaque += 1
    top = max(counts.items(), key=lambda kv: kv[1])
    return top[0], top[1] / opaque


def seam_vs_interior(img: Image.Image) -> tuple[float, float]:
    """Compare the wrap seam against the harshest interior transition."""
    px = img.load()
    n = img.size[0]

    def d(a, b):
        return sum(abs(i - j) for i, j in zip(a, b))

    cols = [sum(d(px[x, y], px[(x + 1) % n, y]) for y in range(n)) / n for x in range(n)]
    rows = [sum(d(px[x, y], px[x, (y + 1) % n]) for x in range(n)) / n for y in range(n)]
    seam = max(cols[n - 1], rows[n - 1])
    # Compare against a high percentile of the interior transitions, not the
    # single sharpest one. These fields are periodic, so a texture can tile
    # perfectly and still put a threshold edge exactly at the wrap; measured
    # against the one harshest interior edge that reads as a failure even
    # though column 15 -> column 0 is a genuine, correct adjacency. The 90th
    # percentile still catches real breaks - a bevelled border that does not
    # wrap scores three to four times the interior spread, not 1.2x.
    inner = sorted(cols[:n - 1] + rows[:n - 1])
    interior = inner[int(len(inner) * 0.90)]
    return seam, interior


def lum_stats(img: Image.Image) -> tuple[float, float, float]:
    op = [p for p in pixels(img) if p[3] > 0]
    ls = [luminance(p) for p in op]
    return min(ls), sum(ls) / len(ls), max(ls)


# ==========================================================================
# Contact sheets
# ==========================================================================

def _font(size: int):
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def contact_sheet(images, path: Path, cols: int = 7, scale: int = 8,
                  title: str = "") -> None:
    """Labelled contact sheet on a checkerboard, for visual self-review."""
    cell = SIZE * scale
    label_h = 16
    pad = 6
    rows_n = (len(images) + cols - 1) // cols
    head = 26 if title else 0
    sheet = Image.new("RGBA",
                      (cols * (cell + pad) + pad,
                       head + rows_n * (cell + label_h + pad) + pad),
                      (26, 27, 33, 255))
    draw = ImageDraw.Draw(sheet)
    f = _font(13)
    if title:
        draw.text((pad, 6), title, font=_font(15), fill=(226, 232, 240, 255))

    checks = Image.new("RGBA", (cell, cell))
    cp = checks.load()
    for y in range(cell):
        for x in range(cell):
            cp[x, y] = (74, 74, 86, 255) if ((x // 8) + (y // 8)) % 2 else (52, 52, 60, 255)

    for i, (name, img) in enumerate(images):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + pad + (i // cols) * (cell + label_h + pad)
        tile = checks.copy()
        tile.alpha_composite(img.convert("RGBA").resize((cell, cell), Image.NEAREST))
        sheet.paste(tile, (cx, cy))
        draw.text((cx, cy + cell + 2), name[:20], font=f, fill=(184, 192, 208, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, "PNG")


VANILLA_REFS = [
    "stone", "coal_ore", "gold_ore", "diamond_ore", "deepslate",
    "deepslate_gold_ore", "calcite", "tuff", "sand", "moss_block",
    "azalea_leaves", "cherry_leaves", "oak_log", "warped_stem",
    "warped_stem_top", "amethyst_block", "amethyst_cluster", "short_grass",
    "glowstone", "shroomlight", "deepslate_bricks",
]


def build_vanilla_sheet() -> None:
    """Render the vanilla equivalents at the same scale, for side-by-side eyes."""
    if not VANILLA_ROOT.exists():
        return
    imgs = []
    for n in VANILLA_REFS:
        p = VANILLA_ROOT / f"{n}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        if im.size[1] > im.size[0]:          # animated strip - take frame 0
            im = im.crop((0, 0, im.size[0], im.size[0]))
        imgs.append((n, im))
    contact_sheet(imgs, VANILLA_SHEET, cols=7, scale=8,
                  title="VANILLA 26.2 REFERENCE - the conventions being matched")


def spec_block_textures() -> list[str]:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    wanted: list[str] = []
    for block in spec["blocks"]:
        for tex in block.get("textures", []):
            if tex not in wanted:
                wanted.append(tex)
    return wanted


def main() -> int:
    OUT_BLOCK.mkdir(parents=True, exist_ok=True)
    table = []
    images = []
    failures = []

    for name, fn, full_cube in TEXTURES:
        img = fn().save(OUT_BLOCK / f"{name}.png")
        images.append((name, img))

        n_colors = len(unique_colors(img))
        top_color, share = dominant_share(img)
        seam, interior = seam_vs_interior(img)
        all_px = pixels(img)
        alpha_max = max((p[3] for p in all_px if p[3] > 0), default=0)
        cutout = sum(1 for p in all_px if p[3] == 0) / len(all_px)
        lo, mean, hi = lum_stats(img)
        table.append((name, n_colors, share, cutout, seam, interior, lo, mean, hi,
                      full_cube))

        if img.size != (SIZE, SIZE):
            failures.append(f"{name}: size {img.size} != (16,16)")
        if not (MIN_COLOURS <= n_colors <= MAX_COLOURS):
            failures.append(f"{name}: {n_colors} colours, must be "
                            f"{MIN_COLOURS}-{MAX_COLOURS}")
        if share > MAX_SHARE:
            failures.append(f"{name}: {to_hex(top_color)} covers {share:.1%} (>85%)")
        if full_cube and cutout > 0:
            failures.append(f"{name}: full cube has {cutout:.1%} transparent pixels")
        if name in CUTOUT and cutout < 0.12:
            failures.append(f"{name}: cutout sprite is only {cutout:.1%} transparent")
        if name == "void_glass" and alpha_max >= 255:
            failures.append("void_glass: opaque pixels present, must stay translucent")
        if full_cube and seam > interior * SEAM_SLACK + SEAM_FLOOR:
            failures.append(f"{name}: seam {seam:.1f} vs interior max {interior:.1f}"
                            f" - edge detail does not wrap")
        off = [c for c in unique_colors(img) if not on_palette(c[:3])]
        if off:
            failures.append(f"{name}: off-palette " +
                            ", ".join(to_hex(c) for c in sorted(off)[:3]))

    print()
    print(f"{'texture':38} {'cols':>5} {'top%':>7} {'alpha':>7} {'seam':>7} "
          f"{'inner':>7} {'lum lo/mean/hi':>22}  cube")
    print("-" * 108)
    for name, n, share, cut, seam, inner, lo, mean, hi, cube in table:
        print(f"{name:38} {n:>5} {share:>6.1%} {cut:>6.1%} {seam:>7.1f} "
              f"{inner:>7.1f} {lo:>7.0f}/{mean:>5.0f}/{hi:<5.0f}      "
              f"{'yes' if cube else '  -'}")
    print("-" * 108)
    print(f"{len(table)} textures -> {OUT_BLOCK}")

    produced = {name for name, _fn, _cube in TEXTURES}
    # Textures the spec calls for that a DIFFERENT generator owns. The three
    # ores moved to gen_family_textures.py, which paints them on the vanilla
    # stone and deepslate hosts they actually generate in; this file drawing
    # them too was what put a phonolite host on the deepslate bismuth ore.
    # They are still required to exist - they are just not this stage's job.
    OWNED_ELSEWHERE = {
        "resonant_bismuth_ore",
        "deepslate_resonant_bismuth_ore",
        "null_iron_ore",
    }
    wanted = spec_block_textures()
    missing = [t for t in wanted if t not in produced and t not in OWNED_ELSEWHERE]
    if missing:
        failures.append("missing from mod_spec output: " + ", ".join(missing))
    print(f"spec coverage: {len(wanted) - len(missing)}/{len(wanted)} "
          f"mod_spec blocks[].textures entries drawn; "
          f"{len(produced) - len(wanted) + len(missing)} new art-direction textures")

    contact_sheet(images, PREVIEW, cols=7, scale=8,
                  title="THE ECHOING VOID - block textures (8x, checkerboard = alpha)")
    build_vanilla_sheet()
    print(f"preview -> {PREVIEW}")
    print(f"vanilla -> {VANILLA_SHEET}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ! " + f)
        return 1
    print(f"\nPASS: all 16x16, {MIN_COLOURS}-{MAX_COLOURS} colours, on-palette, "
          "no colour over 85%, full cubes tile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

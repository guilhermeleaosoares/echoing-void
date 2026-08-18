"""
The Echoing Void - block family texture generator (expansion round 2).

Draws everything the new wood families, the fourth canopy and the host-matched
ores need, into
    src/main/resources/assets/echoing_void/textures/block/
plus the four door inventory icons, into
    src/main/resources/assets/echoing_void/textures/item/

WHY THIS FILE EXISTS SEPARATELY FROM gen_block_textures.py
----------------------------------------------------------
gen_block_textures.py owns the terrain set and is not edited here. This module
imports its drawing primitives - the periodic field, the histogram-matched
quantiser, the ore-cluster onion, the leaf-clump pass, the log-bark grain - so
the new families are drawn by exactly the same machinery and land on the same
palette. It then adds the things that round wanted and gen_block_textures never
had a reason to draw: planks, ringed log ends, doors and trapdoors, and ores
whose host rock is the rock they are actually embedded in.

MUST RUN AFTER gen_block_textures.py. Three ore textures and all four existing
log tops are deliberately redrawn here, so this stage has to overwrite that one.

WHAT WAS MEASURED, AND WHAT WAS COPIED FROM IT
----------------------------------------------
Every convention below was measured off the shipped 26.2 assets, not recalled.

  oak/spruce/warped_planks
        All three are the same 16x16 index map in different hues - 10 of the 12
        vanilla plank textures share one arrangement. 7 tones, luminance 82..161
        (span 78). Four boards of four rows: three rows of board face, then one
        row of seam. The seam row is NOT a flat dark line, it is mottled from the
        three darkest tones; the board faces are mottled from the four lightest.
        End joints are single darker pixels at a staggered x, one or two per
        board, never a ruled column. Shares, dark->light:
        11.3 / 9.4 / 7.0 / 18.4 / 18.8 / 20.3 / 14.8 percent.
        The arrangement is regenerated per wood rather than transcribed, so four
        plank blocks standing next to each other are not the same tile in four
        colours.

  oak / spruce / birch / cherry / warped log tops
        The growth rings are SQUARE, and all five woods are the same map.
        Indexing by Chebyshev distance from the tile edge,
        k = 7 - min(x, 15-x, y, 15-y), the level runs +0 +1 +0 +1 +2 +0 +2 steps
        above the dark heartwood tone for k = 0..6, and k = 7 is the one-pixel
        bark border. Rings k=1 and k=3 are laid perfectly flat - their measured
        luminance spread is exactly zero - while k=2 and k=5 wander a step
        either way, which is what keeps it from reading as a dartboard.
        Read radially the same texture suggests a 2.5px concentric period, and
        a first pass here drew Euclidean rings over a noise body on that basis:
        the result was a mottled disc, not end grain.

  birch_log
        Pale bark reads as bark because of the lenticels: 2-5px horizontal dark
        dashes at 51..94 luminance scattered across a 213..255 body. That single
        device is what separates a pale trunk from a pale wall.

  oak_door_bottom / oak_door_top / oak_trapdoor
        A frame plus inset panels. The inset convention is consistent and is the
        opposite of the block-face convention: the TOP and LEFT walls of a recess
        are dark and the BOTTOM and RIGHT walls are lit, because the light is
        falling into the recess from the top left. The door carries a 2x2 grid of
        panels per half; on the upper half the panels are cut clean through as
        windows (48 transparent pixels in oak_door_top). The trapdoor is a dark
        one-pixel border, three brace rows, and four 3x3 holes.
        At the corners the side walls win over the top and bottom ones - the
        top-right corner of every panel is lit, the bottom-left is dark - which
        also breaks what would otherwise be one unbroken dark bar across a door
        where two panels meet.

  oak_door (the inventory icon)
        6 tones, 55% transparent, a 10x14 door with a light frame lattice and
        eight cells. The frame carries 40% of the opaque pixels and the cells
        do the reading. Vanilla cuts the upper cells clean through, which our
        texture gate rejects: holes inside a sprite count as silhouette edge, so
        oak_door scores 0.38 and spruce_door 0.52 against a 0.55 dark-outline
        threshold. Ours paints those cells dark instead and keeps a solid
        outlined silhouette.

  stone / deepslate
        stone: 4 tones, #686868..#8F8F8F, luminance span 39, blobby 1-3px
        granules, no directional grain and no tile-wide gradient at all.
        deepslate: 5 tones, #2F2F37..#797979, span 73, features clearly longer
        across the tile than down it - 38% of pixels continue into their right
        neighbour against 26% downward.
        Both host palettes are reproduced verbatim, and gold_ore and iron_ore
        confirm that a vanilla ore really is drawn on stone's own four tones.
        An ore that is going to sit in an Overworld cliff face has to be that
        cliff face with specks cut into it; drawing it in our own phonolite is
        exactly the complaint being fixed. The field parameters for both hosts
        were fitted against a neighbour-agreement statistic rather than eyeballed
        - see host_stone() and host_deepslate().

Run:  python tools/gen_family_textures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from PIL import Image  # noqa: E402

from ev_palette import (  # noqa: E402
    SIZE, Canvas, fbm, mix, parse_hex, shift, to_hex, unique_colors,
)

# gen_block_textures is imported, never edited: it owns the terrain set, and
# reusing its primitives is what keeps these families on the same palette and
# the same lighting model as the blocks they will stand next to.
from gen_block_textures import (  # noqa: E402
    AM_DARK,
    AM_HIGH,
    AM_LIGHT,
    AM_MID,
    AR_DEEP,
    AR_LIGHT,
    AR_MID,
    BI_MID,
    BIS_BODY,
    BIS_CORE,
    BIS_RIM,
    BIS_SPARK,
    CH_HIGH,
    CH_LIGHT,
    CH_MID,
    CH_SHADOW,
    DEEP_ORE_SITES,
    HUM_STEM_RAMP,
    NI_BLACK,
    NI_DARK,
    NI_LIGHT,
    NI_MID,
    NI_PALE,
    NI_STEEL,
    ORE_SITES,
    PH_DARK,
    PH_LIGHT,
    PH_MID,
    PH_PALE,
    PH5,
    R,
    STRIP_STEM_RAMP,
    STRIP_TUNE_RAMP,
    TUNE_RAMP,
    VOID_BLACK,
    VOID_SHADOW,
    _phonolite_host,
    bump_at,
    contact_sheet,
    dominant_share,
    field,
    foliage,
    hash01,
    levels,
    lum_stats,
    on_palette,
    paint,
    pixels,
    put,
    scatter_ore,
    seam_vs_interior,
    wood_side,
)

ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void"
OUT_BLOCK = ASSETS / "textures" / "block"
OUT_ITEM = ASSETS / "textures" / "item"
PREVIEW_DIR = ROOT / "build" / "texture_preview"
VANILLA_ROOT = Path(r"C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block")
VANILLA_ITEM_ROOT = VANILLA_ROOT.parent / "item"

MIN_COLOURS = 5        # matches the v2 gate in tools/verify_textures.py
MAX_COLOURS = 16
MAX_SHARE = 0.85
SEAM_SLACK = 1.35
SEAM_FLOOR = 6.0


# ==========================================================================
# Planks
# ==========================================================================

BOARD_H = 4            # three rows of board face, then one row of seam
# Vanilla plank tone shares, renormalised within each group.
SEAM_W = (0.41, 0.34, 0.25)          # the three darkest tones, in the seam rows
FACE_W = (0.26, 0.26, 0.28, 0.20)    # the four lightest, on the board faces

# The single most important measured number in this file. oak_planks spans 78
# luminance, but that span is not spread evenly: the four face tones are packed
# into the top 27 of it and the three seam tones occupy the bottom 37, with a
# 14-wide gap between the groups. A first pass spread the face tones over 60+
# luminance and the result was static, not timber - the boards only read as
# milled surfaces because their four tones are nearly the same value and the
# seam is decisively darker than all of them.
PLANK_STOPS = (0.00, 0.24, 0.48, 0.66, 0.81, 0.89, 1.00)

# Per-row value lift inside one board; the seam row is quantised separately so
# its entry is unused.
ROW_LIFT = (0.32, -0.03, -0.10, 0.0)


def _lum(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def tone_ladder(dark, light, stops=PLANK_STOPS):
    """Interpolate `dark`..`light` so each stop lands at a target LUMINANCE.

    mix() blends in linear light, so an even spread of t is not an even spread
    of perceived value - and the plank ladder is defined by its luminance
    spacing, not by its blend fraction. Each stop is therefore solved for by
    bisection, which reproduces vanilla's exact tonal structure in any hue.
    """
    lo, hi = _lum(dark), _lum(light)
    out = []
    for s in stops:
        target = lo + (hi - lo) * s
        a, b = 0.0, 1.0
        for _ in range(24):
            m = (a + b) / 2
            if _lum(mix(dark, light, m)) < target:
                a = m
            else:
                b = m
        out.append(mix(dark, light, (a + b) / 2))
    return out


def _quantise(cells, weights) -> dict[tuple[int, int], int]:
    """Histogram-matched quantisation over an arbitrary set of cells.

    levels() in gen_block_textures slices a whole 16x16 field; planks need the
    board faces and the seam rows sliced independently so each group gets the
    measured vanilla share of its own tones. Same mechanism, arbitrary domain.
    """
    ordered = sorted(cells)
    total = float(sum(weights))
    out: dict[tuple[int, int], int] = {}
    i = 0
    acc = 0.0
    n = len(ordered)
    for lvl, w in enumerate(weights):
        acc += w / total
        stop = n if lvl == len(weights) - 1 else round(acc * n)
        while i < stop:
            _v, x, y = ordered[i]
            out[(x, y)] = lvl
            i += 1
    return out


def board_cells(seed: int, rows=None, bias=None):
    """The milled-timber value field: 2-4px horizontal streaks plus a little grit.

    y * 8 decorrelates one row from the next while x stays on half a lattice
    cell per pixel, so the field runs along the board rather than across it -
    the direction a plank is planed. Only a sixth of the value is per-pixel
    grit; more than that and the boards read as static rather than as timber.
    Shared by planks, doors and trapdoors so all three are the same wood.
    """
    cells = []
    for y in (range(SIZE) if rows is None else rows):
        b = 0.0 if bias is None else bias(y)
        for x in range(SIZE):
            cells.append((fbm(x, y * 8, seed, octaves=1, period=8) * 0.84
                          + hash01(x, y, seed ^ 0x51AB) * 0.16 + b, x, y))
    return cells


def planks(c: Canvas, seed: int, seam0: int, face0: int, joints) -> None:
    """Horizontal board run: four boards of four rows, vanilla's arrangement.

    The face field is stretched four times along the board so the grain runs
    with the plank rather than across it, and every board carries its own small
    value bias so the four boards read as four separate pieces of timber - that
    per-board bias is most of what makes a plank texture look milled rather than
    noisy. `joints` gives the x of each board's butt joint; they are staggered
    and drawn broken, because a ruled column reads as a grid, not as carpentry.
    """
    # Two biases. ROW_LIFT is measured: in every vanilla plank texture the first
    # row of each board averages 11-13 luminance above the other two, because
    # the top edge of a board is the edge facing the light. Missing it is what
    # left the first pass looking like four bands of mottle rather than like
    # stacked boards. The per-board term is much smaller and just stops the four
    # boards being the same piece of timber.
    def bias(y: int) -> float:
        return (0.05, -0.03, 0.02, -0.04)[y // BOARD_H] + ROW_LIFT[y % BOARD_H]

    face_rows = [y for y in range(SIZE) if y % BOARD_H != BOARD_H - 1]
    seam_rows = [y for y in range(SIZE) if y % BOARD_H == BOARD_H - 1]
    face_cells = board_cells(seed, face_rows, bias)
    seam_cells = board_cells(seed, seam_rows)

    for (x, y), lvl in _quantise(seam_cells, SEAM_W).items():
        c.set(x, y, seam0 + lvl)
    for (x, y), lvl in _quantise(face_cells, FACE_W).items():
        c.set(x, y, face0 + lvl)

    # Butt joints. One nick column per board, broken vertically, with the board
    # end to its right catching the key light.
    hi = face0 + len(FACE_W) - 1
    for board, jx in enumerate(joints):
        for row in range(BOARD_H - 1):
            y = board * BOARD_H + row
            if hash01(jx, y, seed + 6151) < 0.22:
                continue
            put(c, jx, y, seam0 + 2)
            bump_at(c, (jx + 1) % SIZE, y, +1, face0, hi)

    # A few end-grain flecks on the faces, the darkest thing on a board that is
    # not a seam. Vanilla scatters one or two of these per board.
    for k in range(6):
        x = int(hash01(k, 3, seed + 811) * SIZE)
        y = int(hash01(5, k, seed + 811) * SIZE)
        if (y % BOARD_H) == BOARD_H - 1:
            continue
        put(c, x, y, seam0 + 2)


# ==========================================================================
# Log ends - concentric growth rings
# ==========================================================================

# Growth rings are SQUARE, not circular. Ring index k = 7 - min(x, 15-x, y,
# 15-y) - Chebyshev distance from the tile edge - and the level at each k was
# measured identically on oak, spruce, birch, cherry and warped: every vanilla
# log top is the one map below in a different hue. A first pass here drew
# Euclidean rings over a noise body and read as a mottled disc, because vanilla
# rings are nested squares and the body carries almost no noise at all.
#
#   k        0     1     2     3     4     5     6      7
#   step     +0    +1    +0    +1    +2    +0    +2     bark
#   spread   14     0    33     0    15    33    15     (luminance, oak)
RING_STEP = (0, 1, 0, 1, 2, 0, 2)
RING_MOTTLE = (0.25, 0.0, 0.42, 0.0, 0.32, 0.42, 0.32)


def log_rings(c: Canvas, seed: int, dark: int, bark_dark: int, bark_mid: int,
              heart: int | None = None, bark_speck: float = 0.45) -> None:
    """Log end grain: a 1px bark border around nested square growth rings.

    `dark` is the ramp index of the darkest heartwood tone; the ring map lifts
    it by 0, 1 or 2 steps. Rings k=1 and k=3 are laid perfectly flat because
    vanilla's are - their measured spread is exactly zero - while the wider
    rings wander a step either way. That mix of dead-flat and mottled rings is
    what stops the result reading as either a dartboard or as noise.
    """
    top = len(c.ramp) - 1
    for y in range(SIZE):
        for x in range(SIZE):
            k = 7 - min(x, SIZE - 1 - x, y, SIZE - 1 - y)
            if k == 7:
                corner = min(x, SIZE - 1 - x) == 0 and min(y, SIZE - 1 - y) == 0
                c.set(x, y, bark_dark
                      if corner or hash01(x, y, seed + 5) > 1.0 - bark_speck
                      else bark_mid)
                continue
            t = dark + RING_STEP[k]
            m = RING_MOTTLE[k]
            if m and hash01(x, y, seed + 71) > 1.0 - m:
                t += 1 if hash01(y, x, seed + 137) > 0.55 else -1
            c.set(x, y, max(0, min(top, t)))

    # One resonant pixel at the heart. Vanilla has no such thing, but these are
    # singing trees and the accent is the only place the family glow appears on
    # an end grain, so it stays to a single pixel.
    if heart is not None:
        c.set(7, 7, heart)


# ==========================================================================
# Bark helpers for the two new woods
# ==========================================================================

def lenticels(c: Canvas, seed: int, dash: int, halo: int, count: int = 9) -> None:
    """Birch-style horizontal dark dashes on a pale trunk.

    Measured off birch_log: 2-5px runs, far darker than the body, scattered
    without a grid. On a pale bark this one device carries the whole read; the
    grain alone leaves it looking like a painted wall.
    """
    for k in range(count):
        x = int(hash01(k, 11, seed) * SIZE)
        y = int(hash01(13, k, seed) * SIZE)
        run = 2 + int(hash01(k, k, seed + 3) * 3)
        for i in range(run):
            put(c, x + i, y, dash)
        put(c, x - 1, y, halo)
        put(c, x + run, y, halo)


def resin_streaks(c: Canvas, seed: int, bright: int, shadow: int,
                  columns=(3, 11)) -> None:
    """Vertical amber resin runs down the bark, with a shadow on their right."""
    for cx in columns:
        for y in range(SIZE):
            if hash01(cx, y, seed) < 0.30:
                continue
            put(c, cx, y, bright)
            put(c, cx + 1, y, shadow)


# ==========================================================================
# Ramps - four wood families, one canopy
# ==========================================================================

# Planks. Seven tones each on the measured vanilla luminance ladder: indices
# 0-2 are the seam group, 3-6 the board faces, which is the split planks()
# expects (seam0=0, face0=3).
#
# Vanilla plank spans are narrow: spruce 44, birch 61, oak 78 luminance end to
# end. The first pass ran 90-110 and the boards looked bleached; each pair below
# is chosen to land inside that measured band.
TUNE_PLANK_RAMP = R("petrified_tuning_planks", tone_ladder(
    mix(PH_DARK, PH_MID, 0.45), mix(PH_LIGHT, PH_PALE, 0.68)))

HUM_PLANK_RAMP = R("humming_planks", tone_ladder(
    mix(AR_DEEP, AR_MID, 0.20), mix(AR_MID, AR_LIGHT, 0.90)))

ASH_PLANK_RAMP = R("echo_ash_planks", tone_ladder(
    mix(PH_PALE, CH_SHADOW, 0.75), mix(CH_LIGHT, AM_HIGH, 0.25)))

BOUGH_PLANK_RAMP = R("amber_bough_planks", tone_ladder(
    AM_DARK, mix(AM_LIGHT, AM_HIGH, 0.10)))

# Bark for the two new woods. Monotonic dark->light so bump_at and the groove
# pass in wood_side() behave; the accent tones live inside the ramp rather than
# above it, and the weights simply give the dark end a small share.
# birch_log holds its entire body inside 213..255 and spends about a dozen
# pixels on the 51..94 dashes. So the body tones are indices 0-4 and the two
# lenticel tones sit ABOVE them at 5-6, out of reach of the quantiser and of
# wood_side's column bias: the only way a dark pixel appears on this trunk is
# lenticels() putting it there. Giving the dark end a share of the histogram
# instead - which is what the first pass did - turned a pale trunk into grey
# static, because a third of the pixels were then free to fall to the bottom of
# a 150-wide range.
ASH_BARK_RAMP = R("echo_ash_log", [
    mix(PH_PALE, CH_SHADOW, 0.80),       # 0 groove / deep shadow
    mix(CH_SHADOW, CH_MID, 0.35),        # 1
    mix(CH_MID, AM_HIGH, 0.16),          # 2 bark body
    mix(CH_LIGHT, AM_HIGH, 0.14),        # 3
    mix(CH_HIGH, AM_HIGH, 0.10),         # 4 lit bark
    mix(PH_MID, PH_LIGHT, 0.40),         # 5 lenticel halo   - never quantised
    mix(PH_MID, VOID_SHADOW, 0.30),      # 6 lenticel        - never quantised
])
ASH_BARK_W = (0.08, 0.18, 0.32, 0.28, 0.14)

STRIP_ASH_RAMP = R("stripped_echo_ash_log", [
    mix(CH_SHADOW, CH_MID, 0.30),
    mix(CH_MID, AM_HIGH, 0.10),
    mix(CH_MID, CH_LIGHT, 0.60),
    mix(CH_LIGHT, AM_HIGH, 0.12),
    mix(CH_HIGH, AM_HIGH, 0.08),
    shift(CH_HIGH, 0.12),
])
STRIP_ASH_W = (0.10, 0.20, 0.27, 0.23, 0.14, 0.06)

BOUGH_BARK_RAMP = R("amber_bough_log", [
    mix(AM_DARK, VOID_BLACK, 0.55),
    mix(AM_DARK, VOID_BLACK, 0.28),
    mix(AM_DARK, VOID_SHADOW, 0.10),
    AM_DARK,
    mix(AM_DARK, AM_MID, 0.55),
    AM_MID,
    mix(AM_MID, AM_LIGHT, 0.45),
    AM_LIGHT,
])
# Weighted toward the light end on purpose. amber_strata means about 83
# luminance and amber_resonance_leaves about 99; a trunk sitting between them
# vanishes into both. This lands the bark near 115 so an Amber Bough reads as a
# trunk against its own band and its own canopy.
BOUGH_BARK_W = (0.02, 0.06, 0.12, 0.18, 0.24, 0.22, 0.12, 0.04)

STRIP_BOUGH_RAMP = R("stripped_amber_bough_log", [
    mix(AM_DARK, AM_MID, 0.70),
    AM_MID,
    mix(AM_MID, AM_LIGHT, 0.40),
    mix(AM_MID, AM_LIGHT, 0.75),
    AM_LIGHT,
    mix(AM_LIGHT, AM_HIGH, 0.55),
    AM_HIGH,
])
STRIP_BOUGH_W = (0.08, 0.18, 0.25, 0.22, 0.16, 0.08, 0.03)

# Warmed off the chalk spine with amber. Straight chalk gave a blue-white
# canopy that read as cloud rather than as bone; the amber content is what makes
# it foliage, and it also separates this hue from the chime sand and chalk
# terrain it will be seen against.
ASHEN_LEAF_RAMP = R("ashen_resonance_leaves", [
    mix(PH_MID, AM_DARK, 0.35),          # 0 underside / outline
    mix(PH_LIGHT, AM_MID, 0.40),         # 1
    mix(PH_PALE, CH_SHADOW, 0.55),       # 2
    mix(CH_SHADOW, AM_HIGH, 0.22),       # 3
    mix(CH_MID, AM_HIGH, 0.30),          # 4
    mix(CH_LIGHT, AM_HIGH, 0.28),        # 5 lit crown
    mix(CH_HIGH, AM_HIGH, 0.35),         # 6 pale tip
])


# ==========================================================================
# Plank textures
# ==========================================================================

def t_petrified_tuning_planks() -> Canvas:
    """Milled phonolite-grey boards, the dark wood of the family."""
    c = Canvas(TUNE_PLANK_RAMP)
    planks(c, 4201, seam0=0, face0=3, joints=(14, 6, 2, 10))
    return c


def t_humming_planks() -> Canvas:
    """Violet boards. The seam group runs almost black so the board rhythm
    still reads at distance against a saturated face."""
    c = Canvas(HUM_PLANK_RAMP)
    planks(c, 4231, seam0=0, face0=3, joints=(5, 13, 9, 1))
    return c


def t_echo_ash_planks() -> Canvas:
    """Pale bone boards for the chalk highlands - the brightest wood we have,
    and the one that will read as built structure against dark terrain."""
    c = Canvas(ASH_PLANK_RAMP)
    planks(c, 4261, seam0=0, face0=3, joints=(11, 3, 15, 7))
    return c


def t_amber_bough_planks() -> Canvas:
    """Warm gold boards. Value range is deliberately the closest of the four to
    vanilla oak, because this is the wood players will build with most."""
    c = Canvas(BOUGH_PLANK_RAMP)
    planks(c, 4297, seam0=0, face0=3, joints=(7, 15, 4, 12))
    return c


# ==========================================================================
# Log ends - all four woods, so a grove shows real end grain
# ==========================================================================

def t_petrified_tuning_wood_top() -> Canvas:
    """Redraws the old top. The previous one suppressed the rings to avoid a
    dartboard and ended up reading as stone; vanilla's rings are nested squares
    of a flat tone, so that is what this draws."""
    c = Canvas(TUNE_RAMP)
    log_rings(c, 8203, dark=2, bark_dark=0, bark_mid=1, heart=8)
    return c


def t_stripped_petrified_tuning_wood_top() -> Canvas:
    c = Canvas(STRIP_TUNE_RAMP)
    log_rings(c, 8219, dark=2, bark_dark=0, bark_mid=1)
    return c


def t_humming_stem_top() -> Canvas:
    c = Canvas(HUM_STEM_RAMP)
    log_rings(c, 8331, dark=2, bark_dark=0, bark_mid=1, heart=7)
    return c


def t_stripped_humming_stem_top() -> Canvas:
    c = Canvas(STRIP_STEM_RAMP)
    log_rings(c, 8363, dark=2, bark_dark=0, bark_mid=1)
    return c


def t_echo_ash_log_top() -> Canvas:
    """Pale bark, so the border ring stays in the bark's own body tone with a
    couple of lenticel-dark pixels in it - birch_log_top's rim is white, not
    black, and a dark square around pale heartwood would read as the wrong
    tree."""
    c = Canvas(ASH_BARK_RAMP)
    log_rings(c, 8401, dark=1, bark_dark=6, bark_mid=4, heart=None,
              bark_speck=0.14)
    return c


def t_stripped_echo_ash_log_top() -> Canvas:
    c = Canvas(STRIP_ASH_RAMP)
    log_rings(c, 8419, dark=2, bark_dark=0, bark_mid=1)
    return c


def t_amber_bough_log_top() -> Canvas:
    c = Canvas(BOUGH_BARK_RAMP)
    log_rings(c, 8443, dark=4, bark_dark=0, bark_mid=2, heart=7)
    return c


def t_stripped_amber_bough_log_top() -> Canvas:
    c = Canvas(STRIP_BOUGH_RAMP)
    log_rings(c, 8467, dark=2, bark_dark=0, bark_mid=1)
    return c


# ==========================================================================
# The two new woods - bark sides
# ==========================================================================

def t_echo_ash_log_side() -> Canvas:
    """Pale bone bark for the chalk highlands, marked with birch-style
    lenticels. Without the dashes a trunk this pale reads as a chalk pillar."""
    c = Canvas(ASH_BARK_RAMP)
    wood_side(c, 8401, ASH_BARK_W, top=4, groove=0, grain_strength=0.45)
    lenticels(c, 8407, dash=6, halo=5, count=9)
    return c


def t_stripped_echo_ash_log_side() -> Canvas:
    """Stripped: the lenticels are cut away with the bark and the whole trunk
    jumps some sixty luminance, so a stripped Echo Ash reads across a grove."""
    c = Canvas(STRIP_ASH_RAMP)
    wood_side(c, 8419, STRIP_ASH_W, top=5, groove=0, grain_strength=0.80)
    for x0 in (4, 12):
        for y in range(SIZE):
            put(c, x0, y, 4 if hash01(y, x0, 8423) > 0.45 else 3)
            put(c, x0 + 1, y, 0)
    return c


def t_amber_bough_log_side() -> Canvas:
    """Warm bark with resin runs down two grain channels - the only warm trunk
    in the dimension, and the amber band's counterpart to the violet stem."""
    c = Canvas(BOUGH_BARK_RAMP)
    wood_side(c, 8443, BOUGH_BARK_W, top=6, groove=2, grain_strength=0.60)
    resin_streaks(c, 8447, bright=7, shadow=1, columns=(3, 11))
    return c


def t_stripped_amber_bough_log_side() -> Canvas:
    c = Canvas(STRIP_BOUGH_RAMP)
    wood_side(c, 8467, STRIP_BOUGH_W, top=6, groove=0, grain_strength=0.85)
    for x0 in (5, 13):
        for y in range(SIZE):
            put(c, x0, y, 5 if hash01(y, x0, 8471) > 0.45 else 4)
            put(c, x0 + 1, y, 0)
    return c


# ==========================================================================
# The fourth canopy
# ==========================================================================

def t_ashen_resonance_leaves() -> Canvas:
    """Pale bone canopy for Echo Ash - the fourth leaf hue.

    Same clump language as the other three: overlapping rounded masses, crown
    lit and underside shadowed, the gaps between masses left as alpha. Hue is
    what separates the four canopies, so this one holds a bone-white body and
    takes its accent from the warm end rather than from a glow colour.
    """
    c = Canvas(ASHEN_LEAF_RAMP, transparent=True)
    foliage(c, 9691, dark=0, low=2, mid=3, high=5, accent=6, accents=4)
    return c


# ==========================================================================
# Doors and trapdoors
# ==========================================================================

# Measured off oak_door_bottom / oak_door_top / oak_trapdoor. A door is two
# stiles, three rails and a 2x2 grid of recessed panels; the upper half cuts its
# panels clean through as windows. Both panel columns are six wide including
# their walls, which is what leaves 16 across with the stiles.
PANEL_X = ((2, 7), (8, 13))
BOTTOM_BANDS = ((3, 7), (9, 13))     # solid panels: dark row, face, lit row
TOP_BANDS = ((2, 6), (7, 11))        # windows: dark row, hole, lit row
TRAP_X = ((2, 6), (9, 13))
TRAP_BANDS = ((2, 6), (9, 13))

# The hinge and handle. Vanilla draws them in iron grey; ours are null iron with
# a bismuth catch-light, because an iron-grey pixel is the one thing on a door
# that would not belong to this dimension.
HINGES = ((0, 4, 2, 2), (0, 12, 2, 2))
HANDLE = ((11, 13, 3, 2),)


def _panel(c: Canvas, x0: int, x1: int, y0: int, y1: int, seed: int,
           dark_wall: int, lit_wall: int, face: int, hollow: bool) -> None:
    """One recessed panel, lit the way vanilla lights a recess.

    Top and left walls dark, bottom and right walls lit. That is the opposite of
    the convention used on a raised block face, and it is correct: light falling
    in from the top left lands on the far walls of a hole, not on the near ones.

    The side walls take priority over the top and bottom ones at the corners.
    That is measured, not arbitrary: oak_door_bottom puts a lit pixel at the
    top-right corner of every panel and a dark one at the bottom-left. It also
    matters structurally - two panels sit side by side with no gap between them,
    so without the priority their top walls merge into one unbroken twelve-pixel
    dark bar across the door, which is exactly what the first pass drew.
    """
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if x == x0:
                c.set(x, y, dark_wall)
            elif x == x1:
                c.set(x, y, lit_wall)
            elif y == y0:
                c.set(x, y, dark_wall)
            elif y == y1:
                c.set(x, y, lit_wall)
            elif hollow:
                c.clear_px(x, y)
            else:
                t = face
                if hash01(x, y, seed + 401) > 0.70:
                    t += 1
                elif hash01(y, x, seed + 409) > 0.76:
                    t -= 1
                c.set(x, y, t)


def door_face(c: Canvas, seed: int, bands, hollow: bool,
              face0: int = 3, stile_lit: int = 6, stile_dark: int = 2,
              dark_wall: int = 1, lit_wall: int = 6) -> None:
    """A door half: milled board body, two stiles, then the recessed panels.

    The body is the plank field, not a flat fill. A vanilla door carries the
    same mottle as the planks it is built from, and the first pass here laid
    flat rails against high-contrast panel walls, which read as a drawn grid
    rather than as a piece of joinery.
    """
    for (x, y), lvl in _quantise(board_cells(seed), FACE_W).items():
        c.set(x, y, face0 + lvl)

    for y in range(SIZE):
        c.set(0, y, stile_lit if hash01(0, y, seed + 31) > 0.25 else stile_lit - 1)
        c.set(SIZE - 1, y, stile_dark if hash01(15, y, seed + 37) > 0.3
              else stile_dark + 1)

    for y0, y1 in bands:
        for x0, x1 in PANEL_X:
            _panel(c, x0, x1, y0, y1, seed, dark_wall, lit_wall, face0 + 1,
                   hollow)


def ironwork(c: Canvas, plates, body: int, lit: int, shadow: int) -> None:
    """Hinges and handle: null-iron plates with a bismuth catch-light.

    Each plate is at least two pixels across. A single-pixel fitting the way
    vanilla draws its iron hinge only works because iron grey is a hue no oak
    plank contains; our hardware is a blue-grey on blue-grey wood, so it needs
    the area and the dark corner to separate from the door behind it.
    """
    for x0, y0, w, h in plates:
        for dy in range(h):
            for dx in range(w):
                if dx == 0 and dy == 0:
                    t = lit
                elif dx == w - 1 and dy == h - 1:
                    t = shadow
                else:
                    t = body
                c.set(x0 + dx, y0 + dy, t)


def trapdoor_face(c: Canvas, seed: int, face0: int = 3, edge: int = 1,
                  dark_wall: int = 1, lit_wall: int = 6) -> None:
    """Braced slat door: dark border, three braces, four cut-through holes."""
    for (x, y), lvl in _quantise(board_cells(seed), FACE_W).items():
        c.set(x, y, face0 + lvl)

    # The three braces read as laid ON the slats, so they take the lit tone with
    # a shadow along their lower edge.
    for y in (1, 7, 14):
        for x in range(SIZE):
            c.set(x, y, face0 + 3 if hash01(x, y, seed + 61) > 0.42
                  else face0 + 2)
            if y + 1 < SIZE:
                c.set(x, y + 1, face0 if hash01(x, y, seed + 67) > 0.5
                      else face0 + 1)

    for y0, y1 in TRAP_BANDS:
        for x0, x1 in TRAP_X:
            _panel(c, x0, x1, y0, y1, seed, dark_wall, lit_wall, face0 + 1,
                   True)

    # The border is drawn last so it survives the panel walls, and it is weighted
    # to the darkest tone: oak_trapdoor's top and bottom rows are solid darkest,
    # and that hard frame is what stops a trapdoor reading as a thin plank slab.
    for i in range(SIZE):
        for x, y in ((i, 0), (i, SIZE - 1), (0, i), (SIZE - 1, i)):
            c.set(x, y, edge if hash01(x, y, seed + 97) > 0.72 else edge - 1)


DOOR_METAL = [
    mix(NI_DARK, PH_MID, 0.35),          # +0 hinge shadow
    mix(NI_MID, PH_PALE, 0.55),          # +1 hinge body
    mix(PH_PALE, BI_MID, 0.35),          # +2 catch-light
]


def door_ramp(name: str, plank_ramp):
    """Plank ladder plus the three ironwork tones, at indices 7, 8 and 9."""
    return R(name, list(plank_ramp.colors) + DOOR_METAL)


WOODS = (
    ("petrified_tuning", TUNE_PLANK_RAMP, 5101),
    ("humming", HUM_PLANK_RAMP, 5131),
    ("echo_ash", ASH_PLANK_RAMP, 5167),
    ("amber_bough", BOUGH_PLANK_RAMP, 5197),
)

DOOR_RAMPS = {wood: door_ramp(f"{wood}_door", ramp) for wood, ramp, _s in WOODS}


def make_door_top(wood: str, ramp, seed: int):
    def draw() -> Canvas:
        c = Canvas(ramp, transparent=True)
        door_face(c, seed, TOP_BANDS, hollow=True)
        ironwork(c, HINGES + HANDLE, body=8, lit=9, shadow=7)
        return c
    draw.__doc__ = (f"Upper half of the {wood} door: the two panel bands are cut "
                    "through as windows, with the hinge on the stile and the "
                    "handle at the bottom edge where the door's midline falls.")
    return draw


def make_door_bottom(wood: str, ramp, seed: int):
    def draw() -> Canvas:
        c = Canvas(ramp)
        door_face(c, seed + 1, BOTTOM_BANDS, hollow=False)
        return c
    draw.__doc__ = f"Lower half of the {wood} door: four solid recessed panels."
    return draw


def make_trapdoor(wood: str, ramp, seed: int):
    def draw() -> Canvas:
        c = Canvas(ramp, transparent=True)
        trapdoor_face(c, seed + 2)
        return c
    draw.__doc__ = (f"{wood} trapdoor: braced slats with four cut-through holes, "
                    "so it reads as a hatch rather than as a thin block.")
    return draw


# ==========================================================================
# Door item icons
# ==========================================================================

# The one deliverable here that is not a block texture. models/item/<wood>_door
# already points at echoing_void:item/<wood>_door and nothing was drawing it, so
# verify_resources fails on all four; the door ramps live in this file, so this
# is where they get drawn.
#
# Vanilla's oak_door icon cuts its windows clean through the sprite. Ours cannot:
# the texture gate requires a dark outline around an item silhouette, and holes
# punched through the middle of a sprite count as silhouette edge - measured,
# vanilla's own oak_door scores 0.38 and spruce_door 0.52 against a 0.55
# threshold, i.e. neither would pass. The windows are therefore painted as dark
# recesses rather than cut out, which reads the same at 16x16 and leaves a solid
# silhouette to outline.
# The icon is a lattice, not a set of shaded recesses. oak_door spends 40% of
# its opaque pixels on the light frame lines and lets the eight cells between
# them carry the read; a first pass here drew four shaded recesses instead and
# the result was mush at 16x16, because a one-pixel wall cannot show both a lit
# and a shadowed side. Same eight cells as vanilla, two columns by four rows.
ICON_X = (3, 12)                       # silhouette, outline included
ICON_Y = (1, 15)
ICON_FRAME_COLS = (4, 7, 8, 11)        # light stiles and the central mullion
ICON_FRAME_ROWS = (2, 5, 8, 11, 14)    # light rails
ICON_CELL_X = ((5, 6), (9, 10))
ICON_CELL_Y = ((3, 4), (6, 7), (9, 10), (12, 13))


def door_icon(c: Canvas, seed: int, outline: int = 0, face0: int = 3,
              window: int = 1, lit: int = 6) -> None:
    """A whole door drawn small: outline, light frame, eight cells, hardware."""
    x0, x1 = ICON_X
    y0, y1 = ICON_Y
    levels_map = _quantise(board_cells(seed), FACE_W)

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            on_frame = x in ICON_FRAME_COLS or y in ICON_FRAME_ROWS
            t = lit if on_frame else face0 + levels_map[(x, y)]
            if on_frame and hash01(x, y, seed + 811) > 0.72:
                t -= 1
            c.set(x, y, t)

    for i, (cy0, cy1) in enumerate(ICON_CELL_Y):
        for cx0, cx1 in ICON_CELL_X:
            for y in range(cy0, cy1 + 1):
                for x in range(cx0, cx1 + 1):
                    # upper half is glazed, lower half is a solid panel
                    if i < 2:
                        c.set(x, y, window)
                    else:
                        c.set(x, y, face0 + (1 if y == cy1 else 0))

    for x in range(x0, x1 + 1):
        c.set(x, y0, outline)
        c.set(x, y1, outline)
    for y in range(y0, y1 + 1):
        c.set(x0, y, outline)
        c.set(x1, y, outline)

    # Hardware. The hinges sit on the outline column and use the darkest metal
    # tone, so they read as fittings without lifting the silhouette edge.
    c.set(x0, 4, 7)
    c.set(x0, 11, 7)
    c.set(10, 8, 9)      # handle catch-light, interior so the outline is intact
    c.set(11, 8, 7)


def make_door_item(wood: str, ramp, seed: int):
    def draw() -> Canvas:
        c = Canvas(ramp, transparent=True)
        door_icon(c, seed + 3)
        return c
    draw.__doc__ = f"Inventory icon for the {wood} door."
    return draw


# ==========================================================================
# Host-matched ores
# ==========================================================================

# Vanilla stone and deepslate, verbatim. Both palettes pass the art-direction
# gate already - the producible set covers them - and there is no point drawing
# an approximation of a rock the player is standing in. An Overworld ore that
# does not use the Overworld's own host colours is the complaint being fixed.
STONE_TONES = [parse_hex(h) for h in ("#686868", "#747474", "#7F7F7F", "#8F8F8F")]
STONE_W = (0.066, 0.277, 0.461, 0.196)

DEEPSLATE_TONES = [parse_hex(h) for h in
                   ("#2F2F37", "#3D3D43", "#515151", "#646464", "#797979")]
DEEPSLATE_W = (0.102, 0.273, 0.305, 0.227, 0.093)

# The resource tones do NOT change with the host. Vanilla draws the same speck
# palette in coal_ore and deepslate_coal_ore, and that is what lets a player
# recognise an ore in rock they have never mined before.
BISMUTH_TONES = [BIS_RIM, BIS_BODY, BIS_CORE, BIS_SPARK]

# Null iron is a hole, not a crystal, so its shells are inverted: the rim is the
# lit lip of the pit and the core is void black.
NULL_TONES = [
    NI_DARK,                             # 0: deep shadow base
    NI_STEEL,                            # 1: null-iron steel body
    mix(NI_LIGHT, NI_PALE, 0.45),        # 2: bright lit metallic lip
    mix(NI_LIGHT, BI_MID, 0.50),         # 3: cyan bismuth glint on lit lip
]


def host_stone(c: Canvas, seed: int) -> None:
    """Reproduce vanilla stone: blobby 1-3px granules, no grain direction.

    stone.png carries no tile-wide gradient and almost no relief term - the
    diagonal shading a player sees on a stone block comes from block face
    lighting, not from the texture.

    The parameters are fitted, not guessed. Measuring the fraction of pixels
    whose four neighbours share their exact colour gives 0.393 on vanilla
    stone; grit 0.42 at one octave with a relief of 0.10 gives 0.395, and the
    first pass here - two octaves at grit 0.52 - gave 0.348, i.e. visibly
    noisier rock than the block it is meant to be embedded in.
    """
    paint(c, levels(field(seed, grain=8, octaves=1, grit=0.42, relief=0.10),
                    STONE_W))


def host_deepslate(c: Canvas, seed: int) -> None:
    """Reproduce vanilla deepslate: darker, higher contrast, streaked across.

    Sampling y at twice the frequency of x makes every feature twice as long
    across the tile as down it, which is the anisotropy measured on deepslate:
    38% of pixels continue horizontally into their right neighbour against only
    26% downward. The multiplier is an integer so the stretched lattice stays
    commensurate with the 16px tile and the texture still wraps.

    Fitted the same way as the stone host. Vanilla deepslate scores
    same 0.320 / horizontal 0.379 / vertical 0.262; these parameters give
    0.328 / 0.395 / 0.262.
    """
    f = [[fbm(x, y * 2, seed, octaves=2, period=4) * 0.74
          + hash01(x, y, seed ^ 0x2D5B) * 0.26 for x in range(SIZE)]
         for y in range(SIZE)]
    paint(c, levels(f, DEEPSLATE_W))


def make_ore(name: str, host: str, resource, host_seed: int, ore_seed: int,
             sparkle_on=(0,)):
    """One ore texture: a host rock with the resource cut into it.

    `host` picks which rock the specks are embedded in; the resource tones are
    appended above the host's own, so index `base` is the cluster rim and
    `base + 3` the sparkle, whichever host is underneath.
    """
    base_tones = {"stone": STONE_TONES, "deepslate": DEEPSLATE_TONES,
                  "phonolite": list(PH5)}[host]
    ramp = R(name, list(base_tones) + list(resource))
    base = len(base_tones)
    sites = ORE_SITES if host != "deepslate" else DEEP_ORE_SITES

    def draw() -> Canvas:
        c = Canvas(ramp)
        if host == "stone":
            host_stone(c, host_seed)
        elif host == "deepslate":
            host_deepslate(c, host_seed)
        else:
            _phonolite_host(c)
        scatter_ore(c, sites, dark=base, mid=base + 1, bright=base + 2,
                    sparkle=base + 3, sparkle_on=sparkle_on)
        return c

    draw.__doc__ = f"{name}: the {host} host with {len(sites)} clusters cut into it."
    return draw


# ==========================================================================
# Manifest and harness
# ==========================================================================

TEXTURES: list[tuple[str, object, bool]] = [
    # planks - four woods
    ("petrified_tuning_planks", t_petrified_tuning_planks, True),
    ("humming_planks", t_humming_planks, True),
    ("echo_ash_planks", t_echo_ash_planks, True),
    ("amber_bough_planks", t_amber_bough_planks, True),
    # log ends - four woods plus stripped
    ("petrified_tuning_wood_top", t_petrified_tuning_wood_top, True),
    ("stripped_petrified_tuning_wood_top", t_stripped_petrified_tuning_wood_top, True),
    ("humming_stem_top", t_humming_stem_top, True),
    ("stripped_humming_stem_top", t_stripped_humming_stem_top, True),
    ("echo_ash_log_top", t_echo_ash_log_top, True),
    ("stripped_echo_ash_log_top", t_stripped_echo_ash_log_top, True),
    ("amber_bough_log_top", t_amber_bough_log_top, True),
    ("stripped_amber_bough_log_top", t_stripped_amber_bough_log_top, True),
    # the two new woods - bark
    ("echo_ash_log_side", t_echo_ash_log_side, True),
    ("stripped_echo_ash_log_side", t_stripped_echo_ash_log_side, True),
    ("amber_bough_log_side", t_amber_bough_log_side, True),
    ("stripped_amber_bough_log_side", t_stripped_amber_bough_log_side, True),
    # the fourth canopy
    ("ashen_resonance_leaves", t_ashen_resonance_leaves, False),
]

ORES = [
    # (texture name, host, resource tones, host seed, ore seed, sparkle sites)
    ("resonant_bismuth_ore", "stone", BISMUTH_TONES, 6101, 6102, (0, 3)),
    ("deepslate_resonant_bismuth_ore", "deepslate", BISMUTH_TONES, 6131, 6132, (1,)),
    ("phonolite_resonant_bismuth_ore", "phonolite", BISMUTH_TONES, 6167, 6168, (0, 3)),
    # Null iron gets a catch-light on some clusters. Seen tiled, the pits alone
    # nearly disappear into deepslate and phonolite - both hosts are already
    # dark, so darkness cannot be the only signal. The glint replaces the
    # deepest core pixel, which is where a light would actually catch a lip.
    ("null_iron_ore", "stone", NULL_TONES, 6197, 6198, (1,)),
    ("deepslate_null_iron_ore", "deepslate", NULL_TONES, 6229, 6230, (0, 2)),
    ("phonolite_null_iron_ore", "phonolite", NULL_TONES, 6263, 6264, (0, 2, 4)),
    # knell_ore is deliberately NOT drawn here. It was on this file's list as
    # resonite_ore before the tier was renamed, but tools/gen_knell_textures.py
    # owns the whole Knell family - ore, storage block, integrator, items - and
    # draws the ore on the same _phonolite_host with the same cluster machinery.
    # Two generators writing one PNG is decided by stage order, not by intent,
    # and the family owner should win: its speck palette is pushed to magenta on
    # purpose so a knell vein is not mistaken for diamond ore, which only holds
    # if the ore matches the block and the ingot beside it.
]

for _name, _host, _res, _hs, _os, _sp in ORES:
    TEXTURES.append((_name, make_ore(_name, _host, _res, _hs, _os, _sp), True))

for _wood, _plank_ramp, _seed in WOODS:
    _r = DOOR_RAMPS[_wood]
    TEXTURES += [
        (f"{_wood}_door_top", make_door_top(_wood, _r, _seed), False),
        (f"{_wood}_door_bottom", make_door_bottom(_wood, _r, _seed), False),
        (f"{_wood}_trapdoor", make_trapdoor(_wood, _r, _seed), False),
    ]

CUTOUT = {"ashen_resonance_leaves"}
CUTOUT |= {f"{w}_door_top" for w, _r, _s in WOODS}
CUTOUT |= {f"{w}_trapdoor" for w, _r, _s in WOODS}

# Not full cubes - a door carries stiles and rails that must not wrap - but
# still required to be fully opaque.
OPAQUE = {f"{w}_door_bottom" for w, _r, _s in WOODS}

# textures/item/, not textures/block/. These are held to the item conventions:
# transparent surround, and a dark outline all the way round the silhouette.
ITEM_TEXTURES = [
    (f"{w}_door", make_door_item(w, DOOR_RAMPS[w], s)) for w, _r, s in WOODS
]
OUTLINE_MIN_RATIO = 0.55

# Full cubes that must tile at the 0/15 seam. Doors and trapdoors are excluded:
# they carry a deliberate frame, exactly as vanilla's do.
TILES = {name for name, _fn, cube in TEXTURES if cube}


def outline_ratio(img: Image.Image) -> float:
    """Fraction of silhouette-edge pixels darker than the interior mean.

    Mirrors check_outline in tools/verify_textures.py so an item fails here, at
    author time, rather than at the gate. Reimplemented rather than imported to
    keep this module free of the gate's import-time palette build.
    """
    px = img.load()
    w, h = img.size

    def opaque(x, y):
        return 0 <= x < w and 0 <= y < h and px[x, y][3] > 0

    edge, interior = [], []
    for y in range(h):
        for x in range(w):
            if not opaque(x, y):
                continue
            lum = _lum(px[x, y])
            is_edge = any(not opaque(x + dx, y + dy)
                          for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            (edge if is_edge else interior).append(lum)
    if not edge or not interior:
        return 0.0
    mean = sum(interior) / len(interior)
    return sum(1 for lum in edge if lum <= mean * 0.92) / len(edge)


def audit(name: str, img: Image.Image, full_cube: bool) -> list[str]:
    errors: list[str] = []
    if img.size != (SIZE, SIZE):
        errors.append(f"size {img.size} != (16,16)")
    n = len(unique_colors(img))
    if not (MIN_COLOURS <= n <= MAX_COLOURS):
        errors.append(f"{n} colours, must be {MIN_COLOURS}-{MAX_COLOURS}")
    top_color, share = dominant_share(img)
    if share > MAX_SHARE:
        errors.append(f"{to_hex(top_color)} covers {share:.1%} (>85%)")
    all_px = pixels(img)
    cut = sum(1 for p in all_px if p[3] == 0) / len(all_px)
    if (full_cube or name in OPAQUE) and cut > 0:
        errors.append(f"must be opaque, has {cut:.1%} transparent pixels")
    if name in CUTOUT and cut < 0.12:
        errors.append(f"cutout sprite is only {cut:.1%} transparent")
    if name in TILES:
        seam, interior = seam_vs_interior(img)
        if seam > interior * SEAM_SLACK + SEAM_FLOOR:
            errors.append(f"seam {seam:.1f} vs interior {interior:.1f} - does not wrap")
    off = [c for c in unique_colors(img) if not on_palette(c[:3])]
    if off:
        errors.append("off-palette " + ", ".join(to_hex(c) for c in sorted(off)[:3]))
    return errors


VANILLA_SHEETS = {
    "family_planks": (
        ["petrified_tuning_planks", "humming_planks", "echo_ash_planks",
         "amber_bough_planks"],
        ["oak_planks", "spruce_planks", "warped_planks", "birch_planks"],
        "PLANKS - ours (top) vs vanilla (bottom), 10x nearest",
    ),
    "family_logtops": (
        ["petrified_tuning_wood_top", "humming_stem_top", "echo_ash_log_top",
         "amber_bough_log_top", "stripped_petrified_tuning_wood_top",
         "stripped_humming_stem_top", "stripped_echo_ash_log_top",
         "stripped_amber_bough_log_top"],
        ["oak_log_top", "spruce_log_top", "birch_log_top", "warped_stem_top"],
        "LOG ENDS - ours vs vanilla, 10x nearest",
    ),
    "family_bark": (
        ["echo_ash_log_side", "stripped_echo_ash_log_side",
         "amber_bough_log_side", "stripped_amber_bough_log_side"],
        ["birch_log", "stripped_birch_log", "oak_log", "stripped_oak_log"],
        "NEW BARK - ours vs vanilla, 10x nearest",
    ),
    "family_leaves": (
        ["ashen_resonance_leaves"],
        ["oak_leaves", "azalea_leaves", "birch_leaves"],
        "FOURTH CANOPY - ours vs vanilla, 10x nearest",
    ),
    "family_doors": (
        ["petrified_tuning_door_top", "petrified_tuning_door_bottom",
         "petrified_tuning_trapdoor", "humming_door_top",
         "humming_door_bottom", "humming_trapdoor",
         "echo_ash_door_top", "echo_ash_door_bottom", "echo_ash_trapdoor",
         "amber_bough_door_top", "amber_bough_door_bottom",
         "amber_bough_trapdoor"],
        ["oak_door_top", "oak_door_bottom", "oak_trapdoor",
         "spruce_door_top", "spruce_door_bottom", "spruce_trapdoor"],
        "DOORS AND TRAPDOORS - ours vs vanilla, 10x nearest",
    ),
    "family_door_items": (
        ["petrified_tuning_door", "humming_door", "echo_ash_door",
         "amber_bough_door"],
        ["item/oak_door", "item/spruce_door", "item/iron_door"],
        "DOOR INVENTORY ICONS - ours vs vanilla, 10x nearest",
    ),
    "family_ores": (
        ["resonant_bismuth_ore", "deepslate_resonant_bismuth_ore",
         "phonolite_resonant_bismuth_ore",
         "null_iron_ore", "deepslate_null_iron_ore",
         "phonolite_null_iron_ore"],
        ["stone", "coal_ore", "gold_ore", "diamond_ore",
         "deepslate", "deepslate_coal_ore", "deepslate_gold_ore"],
        "HOST-MATCHED ORES - ours vs vanilla, 10x nearest. Rows 1-2 ours, "
        "rows 3-4 the hosts and ores being matched.",
    ),
}


# Full cubes are judged tiled, not as single icons. A seam that a metric passes
# can still read as a stripe once four copies sit against each other, and an ore
# is only convincing when it looks like a wall of the host rock.
TILED_SHEET = [
    "resonant_bismuth_ore", "null_iron_ore", "deepslate_resonant_bismuth_ore",
    "deepslate_null_iron_ore", "phonolite_resonant_bismuth_ore",
    "phonolite_null_iron_ore",
    "amber_bough_planks", "echo_ash_planks", "petrified_tuning_planks",
    "humming_planks", "echo_ash_log_side", "amber_bough_log_side",
]
TILED_VANILLA = ["stone", "gold_ore", "deepslate", "deepslate_gold_ore",
                 "oak_planks", "oak_log"]


def _tile2x2(img: Image.Image) -> Image.Image:
    out = Image.new("RGBA", (SIZE * 2, SIZE * 2))
    for dx in (0, SIZE):
        for dy in (0, SIZE):
            out.paste(img, (dx, dy))
    return out


def build_tiled_sheet(drawn: dict[str, Image.Image]) -> None:
    imgs = [(n, _tile2x2(drawn[n])) for n in TILED_SHEET if n in drawn]
    for n in TILED_VANILLA:
        p = VANILLA_ROOT / f"{n}.png"
        if p.exists():
            imgs.append((f"[V] {n}", _tile2x2(Image.open(p).convert("RGBA"))))
    # scale 8 gives cell = 128px, an exact 4x of the 32px tiled pair; a scale
    # that does not divide evenly resamples the pixels and hides the seam.
    contact_sheet(imgs, PREVIEW_DIR / "family_tiled.png", cols=6, scale=8,
                  title="2x2 TILED - the seam test full cubes actually have to pass")


def build_sheets(drawn: dict[str, Image.Image]) -> None:
    """Contact sheets with the vanilla equivalents rendered identically.

    Judging our own texture in isolation is how the first pass went wrong; the
    only useful question is whether it holds up beside the thing it imitates.
    """
    for stem, (ours, vanilla, title) in VANILLA_SHEETS.items():
        imgs = [(n, drawn[n]) for n in ours if n in drawn]
        for n in vanilla:
            # "item/foo" reaches the vanilla item folder; anything else is a
            # block texture.
            p = (VANILLA_ITEM_ROOT / f"{n[5:]}.png" if n.startswith("item/")
                 else VANILLA_ROOT / f"{n}.png")
            if not p.exists():
                continue
            im = Image.open(p).convert("RGBA")
            if im.size[1] > im.size[0]:
                im = im.crop((0, 0, im.size[0], im.size[0]))
            imgs.append((f"[V] {n}", im))
        contact_sheet(imgs, PREVIEW_DIR / f"{stem}.png", cols=4, scale=10,
                      title=title)


def main() -> int:
    OUT_BLOCK.mkdir(parents=True, exist_ok=True)
    drawn: dict[str, Image.Image] = {}
    failures: list[str] = []
    rows = []

    for name, fn, full_cube in TEXTURES:
        img = fn().save(OUT_BLOCK / f"{name}.png")
        drawn[name] = img
        failures += [f"{name}: {e}" for e in audit(name, img, full_cube)]
        lo, mean, hi = lum_stats(img)
        seam, interior = seam_vs_interior(img)
        cut = sum(1 for p in pixels(img) if p[3] == 0) / 256.0
        rows.append((name, len(unique_colors(img)), dominant_share(img)[1],
                     cut, seam, interior, lo, mean, hi))

    OUT_ITEM.mkdir(parents=True, exist_ok=True)
    for name, fn in ITEM_TEXTURES:
        img = fn().save(OUT_ITEM / f"{name}.png")
        drawn[name] = img
        failures += [f"item/{name}: {e}" for e in audit(name, img, False)]
        ratio = outline_ratio(img)
        if ratio < OUTLINE_MIN_RATIO:
            failures.append(f"item/{name}: only {ratio:.0%} of the silhouette "
                            f"edge is dark, need {OUTLINE_MIN_RATIO:.0%}")
        lo, mean, hi = lum_stats(img)
        seam, interior = seam_vs_interior(img)
        cut = sum(1 for p in pixels(img) if p[3] == 0) / 256.0
        rows.append((f"item/{name}", len(unique_colors(img)),
                     dominant_share(img)[1], cut, seam, interior, lo, mean, hi))

    build_sheets(drawn)
    build_tiled_sheet(drawn)

    print()
    print(f"{'texture':38} {'cols':>5} {'top%':>7} {'alpha':>7} {'seam':>7} "
          f"{'inner':>7} {'lum lo/mean/hi':>22}")
    print("-" * 100)
    for name, n, share, cut, seam, inner, lo, mean, hi in rows:
        print(f"{name:38} {n:>5} {share:>6.1%} {cut:>6.1%} {seam:>7.1f} "
              f"{inner:>7.1f} {lo:>7.0f}/{mean:>5.0f}/{hi:<5.0f}")
    print("-" * 100)
    print(f"{len(TEXTURES)} block textures -> {OUT_BLOCK}")
    print(f"{len(ITEM_TEXTURES)} item textures  -> {OUT_ITEM}")
    print(f"contact sheets -> {PREVIEW_DIR}")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

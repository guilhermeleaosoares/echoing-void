"""
The Echoing Void - textures for the Knell tier.

Draws the ore, the storage block, the Knell Integrator's faces, the three
materials, the nine pieces of resonant gear and the worn-armour sheets.

This script deliberately owns almost no drawing machinery of its own. The
conventions that make an icon read as Minecraft were measured off the real 26.2
client assets once already, in tools/gen_item_textures.py and
tools/gen_block_textures.py, and they are imported from there rather than
restated - the two-tone silhouette outline, the diagonal tool layout, the armour
span tables, the ore-speck onion, the histogram-matched rock body. A second copy
of those rules would drift away from the first the moment either was tuned.

WHAT IS NEW HERE is one material and one ramp:

  KNELL       a seven-step ramp running from a near-black violet outline up
                 through steel mauve to an almost-white highlight. Knell has
                 to read as "above netherite" at a glance, and netherite's cue is
                 that it is the DARKEST metal in the game - so knell goes the
                 other way and is the palest, which separates the two instantly
                 in a hotbar rather than making them fight. The violet in the
                 shadows is where the magenta harmonic comes from; it is never
                 painted as a surface, only as one or two accent pixels per
                 sprite, exactly the way this mod uses gold.

  the ore        raw phonolite, pixel for pixel, with pale magenta-white specks
                 cut into it. The host has to be the rock the ore is actually
                 embedded in - the ore only exists in raw phonolite below y 34 -
                 or it floats when a player looks at a vein in situ.

Every colour is a mix()/shift() of two anchors named in
docs/spec/art_direction.json, which is the continuum tools/verify_textures.py
authorises, so palette adherence holds by construction.

Run:  python tools/gen_knell_textures.py            regenerate every texture
      python tools/gen_knell_textures.py --preview  also build contact sheets
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from PIL import Image  # noqa: E402

import gen_block_textures as gb  # noqa: E402
import gen_item_textures as gi  # noqa: E402
import ev_vanilla_forms as vf  # noqa: E402
from ev_palette import Canvas, SIZE, _hash2, fbm, key_light_factor, mix, shift, unique_colors  # noqa: E402

ROOT = TOOLS.parent
TEX = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures"
BLOCK_DIR = TEX / "block"
ITEM_DIR = TEX / "item"
EQUIP = TEX / "entity" / "equipment"
PREVIEW_DIR = ROOT / "build" / "texture_preview"

SIZE = 16

col = gi.col
Sprite = gi.Sprite
Material = gi.Material
spans = gi.spans
poly = gi.poly
stroke = gi.stroke
bezier = gi.bezier
blob = gi.blob
lozenge = gi.lozenge


# ---------------------------------------------------------------------------
# The knell item material
# ---------------------------------------------------------------------------

#: Pale bismuth-white metal shadowed in violet. Entries 0 and 1 are the two
#: outline tones; 2..6 are the lit surface, dark to light.
KNELL = Material("knell", [
    col("arc_deep", "void_black", 10),
    col("arc_deep", "arc_mid", 5),
    col("arc_mid", "ph_light", 9),
    col("ph_pale", "chalk_shadow", 8),
    col("chalk_mid", "chalk_light", 8),
    col("chalk_light", "chalk_hi", 10),
    col("chalk_hi", "chalk_hi", 0, 3),
])

#: The magenta harmonic. Used only as accent pixels, never as a fill - two or
#: three per sprite is what makes knell look charged instead of painted.
HARMONIC = Material("harmonic", [
    col("arc_deep", "void_black", 8),
    col("arc_deep", "arc_mid", 8),
    col("arc_mid", "arc_light", 10),
    col("arc_light", "arc_bright", 8),
    col("arc_bright", "chalk_hi", 5),
])

#: The chassis of the Integrator and the handles of the gear: null iron, so the
#: station reads as built from the same stock as the Inversion Anvil next to it.
NULL_IRON = gi.NULL_IRON
SLATE = gi.SLATE
BISMUTH = gi.BISMUTH
AMBER = gi.AMBER


# ---------------------------------------------------------------------------
# Block ramps
# ---------------------------------------------------------------------------

R = gb.R
PH5 = gb.PH5

#: Ore specks. The three-shell onion vanilla cuts into a host stone: violet rim,
#: mauve body, near-white core, plus one magenta-white sparkle.
#: Pushed further toward magenta than the item ramp is. A vein seen in situ is
#: lit only by the player's torch and surrounded by cold blue-grey phonolite,
#: which drags a pale mauve back toward neutral - at 28% magenta the specks read
#: as another diamond ore. These sit at 40% and read as violet at ten blocks.
RES_RIM = mix(gb.AR_DEEP, gb.AR_MID, 0.55)
RES_BODY = mix(gb.AR_LIGHT, gb.CH_MID, 0.30)
RES_CORE = mix(gb.CH_LIGHT, gb.AR_BRIGHT, 0.40)
RES_SPARK = mix(gb.CH_HIGH, gb.AR_BRIGHT, 0.16)

ORE_RAMP = R("knell_ore", list(PH5) + [RES_RIM, RES_BODY, RES_CORE, RES_SPARK])

#: The storage block: a worked metal plate, built the same way null_iron_block
#: is so the two read as a matched pair on a wall, one black and one white.
BLOCK_RAMP = R("knell_block", [
    mix(gb.AR_MID, gb.CH_SHADOW, 0.40),           # 0 darkest corner seam (lum ~107)
    gb.CH_SHADOW,                                  # 1 shadow underplate / bevel (lum ~147)
    mix(gb.CH_SHADOW, gb.CH_MID, 0.40),           # 2 mid-dark shadow (lum ~161)
    mix(gb.CH_SHADOW, gb.CH_MID, 0.70),           # 3 soft shadow (lum ~170)
    gb.CH_MID,                                    # 4 pale metal body (lum ~179)
    mix(gb.CH_MID, gb.CH_LIGHT, 0.50),            # 5 pale metal lit (lum ~195)
    gb.CH_LIGHT,                                  # 6 bright plate (lum ~210)
    gb.CH_HIGH,                                   # 7 highlight bevel (lum ~226)
    mix(gb.CH_HIGH, gb.parse_hex("#FFFFFF"), 0.50),  # 8 specular white catch (lum ~242)
    mix(gb.CH_LIGHT, gb.AR_BRIGHT, 0.28),         # 9 harmonic rose-silver glow (lum ~191)
    mix(gb.CH_HIGH, gb.AR_BRIGHT, 0.28),          # 10 bright harmonic ridge glow (lum ~205)
])

#: Null-iron chassis with amber indicator lights, per the spec's description of
#: the station: "null-iron chassis, a bismuth resonator ring on top, amber
#: indicator lights, cabling down the sides".
CHASSIS_RAMP = R("knell_integrator", [
    shift(gb.NI_BLACK, -0.20),                  # 0 deepest shadow / cable gaps
    gb.NI_BLACK,                                # 1
    mix(gb.NI_BLACK, gb.NI_DARK, 0.55),         # 2
    gb.NI_DARK,                                 # 3 the plate itself
    mix(gb.NI_DARK, gb.NI_MID, 0.55),           # 4
    gb.NI_MID,                                  # 5
    mix(gb.NI_MID, gb.PH_MID, 0.45),            # 6 lit bevel
    mix(gb.AM_MID, gb.AM_LIGHT, 0.50),          # 7 indicator body
    gb.AM_HIGH,                                 # 8 indicator core
    gb.BI_MID,                                  # 9 bismuth conduit
    mix(gb.CH_HIGH, gb.AR_BRIGHT, 0.28),        # 10 magenta harmonic
])

#: The resonator ring. Bismuth, per the spec's description of the station, which
#: also keeps the two palettes doing different jobs: the STATION is null iron and
#: cyan, the MATERIAL it makes is pale white and magenta. If the ring were pale
#: too, a player could not tell the machine from its product at a glance.
#:
#: Banded horizontally on purpose: the block model slices this sprite into thin
#: strips for the four ring bars, and horizontal banding is the only layout where
#: every strip still reads as a turned metal bar.
RING_RAMP = R("knell_integrator_ring", [
    mix(gb.BI_DEEP, gb.VOID_BLACK, 0.60),
    mix(gb.BI_DEEP, gb.VOID_BLACK, 0.28),
    gb.BI_DEEP,
    mix(gb.BI_DEEP, gb.BI_MID, 0.55),
    gb.BI_MID,
    mix(gb.BI_MID, gb.CH_LIGHT, 0.40),
    gb.BI_BRIGHT,
    mix(gb.CH_HIGH, gb.AR_BRIGHT, 0.30),
    gb.GOLD,
])


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def t_knell_ore() -> Canvas:
    """Raw phonolite with knell cut into it.

    The host is gen_block_textures._phonolite_host - literally the raw_phonolite
    body - so a vein reads as the same rock the player is tunnelling through.
    Four clusters rather than the usual five, because the ore is meant to look
    scarce even inside its own block, and two of them carry the sparkle.
    """
    c = Canvas(ORE_RAMP)
    gb._phonolite_host(c)
    gb.scatter_ore(c, gb.DEEP_ORE_SITES, dark=5, mid=6, bright=7, sparkle=8,
                   sparkle_on=(0, 2))
    return c


def t_knell_block() -> Canvas:
    """Nine ingots pressed into a dense pale plate: bevelled inset frame,
    recessed centre panel with harmonic magenta glow emanating along the ridges
    and inner seams, and specular corner rivets."""
    c = Canvas(BLOCK_RAMP)
    seed = 6607

    # 1. Base plate: smooth forged directional gradient flowing from top-left to bottom-right
    grid = [[5] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            diag = (30.0 - (x + y)) / 30.0
            n = fbm(x * 0.8, y * 0.8, seed, octaves=2, period=SIZE) - 0.5
            v = diag * 0.55 + n * 0.20 + 0.30
            if v < 0.25:
                grid[y][x] = 4
            elif v < 0.50:
                grid[y][x] = 5
            elif v < 0.75:
                grid[y][x] = 6
            else:
                grid[y][x] = 7

    # 2. Outer perimeter rim (row 0, col 0, row 15, col 15)
    for x in range(SIZE):
        grid[0][x] = 7 if _hash2(x, 0, seed + 11) > 0.35 else 6
        grid[15][x] = 3 if _hash2(x, 15, seed + 13) > 0.35 else 2
    for y in range(SIZE):
        grid[y][0] = 7 if _hash2(0, y, seed + 17) > 0.35 else 6
        grid[y][15] = 3 if _hash2(15, y, seed + 19) > 0.35 else 2
    grid[0][0] = 7
    grid[15][15] = 1

    # 3. Inset Bevel Frame (at x=1, y=1 and x=14, y=14)
    # Ridge highlight carries bright harmonic glow along sections of the frame
    for i in range(1, SIZE - 1):
        if 4 <= i <= 10 and _hash2(i, 1, seed + 21) > 0.35:
            grid[1][i] = 10  # bright harmonic ridge glow
        else:
            grid[1][i] = 8 if _hash2(i, 1, seed + 23) > 0.30 else 7

        if 4 <= i <= 10 and _hash2(1, i, seed + 27) > 0.35:
            grid[i][1] = 10  # bright harmonic ridge glow
        else:
            grid[i][1] = 8 if _hash2(1, i, seed + 29) > 0.30 else 7

    for i in range(1, SIZE - 1):
        grid[14][i] = 2 if _hash2(i, 14, seed + 31) > 0.35 else 3
        grid[i][14] = 2 if _hash2(14, i, seed + 37) > 0.35 else 3

    # 4. Recessed centre panel seams (rows 3..12, cols 3..12)
    # The inner step-down seam at row 3 / col 3 and lip at row 12 / col 12 emanate harmonic glow
    for i in range(3, 13):
        if 4 <= i <= 11 and _hash2(i, 3, seed + 40) > 0.25:
            grid[3][i] = 9   # harmonic glow seam
        else:
            grid[3][i] = 3 if _hash2(i, 3, seed + 41) > 0.40 else 4

        if 4 <= i <= 11 and _hash2(3, i, seed + 42) > 0.25:
            grid[i][3] = 9   # harmonic glow seam
        else:
            grid[i][3] = 3 if _hash2(3, i, seed + 43) > 0.40 else 4

    for i in range(3, 13):
        if 4 <= i <= 11 and _hash2(i, 12, seed + 46) > 0.30:
            grid[12][i] = 10 # bright harmonic ridge lip
        else:
            grid[12][i] = 7 if _hash2(i, 12, seed + 47) > 0.40 else 6

        if 4 <= i <= 11 and _hash2(12, i, seed + 48) > 0.30:
            grid[i][12] = 10 # bright harmonic ridge lip
        else:
            grid[i][12] = 7 if _hash2(12, i, seed + 49) > 0.40 else 6

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
        grid[ry][rx] = 8          # specular white glint
        grid[ry][rx + 1] = 7      # right flank
        grid[ry + 1][rx] = 7      # lower flank
        grid[ry + 1][rx + 1] = 3  # shadow drop

    # 6. Smooth relaxation pass on the interior to enforce gradual drift
    for _ in range(3):
        for y in range(1, SIZE - 1):
            for x in range(1, SIZE - 1):
                if any(abs(x - rx) <= 1 and abs(y - ry) <= 1 for rx, ry in ((2, 2), (12, 2), (2, 12), (12, 12))):
                    continue
                if grid[y][x] in (9, 10):
                    continue
                nbrs = [grid[ny][nx] for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                        if 0 <= nx < SIZE and 0 <= ny < SIZE and grid[ny][nx] not in (9, 10)]
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


def _chassis_plate(c: Canvas, seed: int) -> None:
    """The shared null-iron body every Integrator face is built on."""
    gb.rock(c, seed, (0.10, 0.20, 0.28, 0.24, 0.13, 0.05), grain=8, grit=0.30,
            relief=0.40)
    gb.clamp_body(c, 1, 6)
    gb.frame_inset(c, hi=6, lo=0)


def t_knell_integrator_side() -> Canvas:
    """Chassis flank, laid out in three horizontal zones.

    The block model gives every face an explicit UV rectangle, so this sprite is
    an atlas rather than a picture: the model shows exactly the rows named here
    and no others, which is why the detail is grouped instead of centred.

      cols 0-1   the cable, sampled whole by the four corner conduits
      rows 1-2   the deck rim, sampled by the deck element's sides
      rows 4-13  the chassis flank, sampled by the chassis element's sides -
                 louvred vents and two amber indicator lamps
    """
    c = Canvas(CHASSIS_RAMP)
    _chassis_plate(c, 7717)

    # cabling down the corner posts: a bismuth conduit with a shadow gutter
    # beside it, run full height so any slice of it reads as continuous cable
    for y in range(SIZE):
        c.set(0, y, 9 if y % 3 else 5)
        c.set(1, y, 0)

    # the deck rim: a lit lip with a bolt line under it
    for x in range(2, 14):
        c.set(x, 1, 6)
        c.set(x, 2, 0 if x % 3 else 5)

    # louvred vents across the flank - a dark slot with a lit lip above each
    for y in (8, 10, 12):
        for x in range(4, 14):
            c.set(x, y, 0)
            c.set(x, y - 1, 5)

    # two amber indicator lamps, each a core with a dimmer halo below and left
    for lx, ly in ((10, 5), (12, 5)):
        c.set(lx, ly, 8)
        c.set(lx, ly + 1, 7)
        c.set(lx - 1, ly, 7)
    return c


def t_knell_integrator_top() -> Canvas:
    """The deck: a plate with a bismuth ring inlaid where the resonator sits, and
    a magenta core at the middle where the upgrade actually happens."""
    c = Canvas(CHASSIS_RAMP)
    _chassis_plate(c, 7723)

    # the inlaid ring: an octagon rather than a circle, because a rasterised
    # circle this small reads as a lumpy blob
    ring = [(5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3),
            (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10),
            (12, 5), (12, 6), (12, 7), (12, 8), (12, 9), (12, 10),
            (5, 12), (6, 12), (7, 12), (8, 12), (9, 12), (10, 12),
            (4, 4), (11, 4), (4, 11), (11, 11)]
    for x, y in ring:
        c.set(x, y, 9)
    for x, y in ((5, 3), (6, 3), (4, 4), (3, 5), (3, 6)):
        c.set(x, y, 10)                       # the lit quadrant of the inlay

    # the emitter well
    for y in range(6, 10):
        for x in range(6, 10):
            c.set(x, y, 0)
    for x, y in ((7, 7), (8, 7), (7, 8), (8, 8)):
        c.set(x, y, 10)
    c.set(7, 7, 8)
    return c


def t_knell_integrator_bottom() -> Canvas:
    """Underside: a plain bolted plate. Nothing decorative - it is never seen
    unless the player is standing under the block, and vanilla treats machine
    undersides the same way."""
    c = Canvas(CHASSIS_RAMP)
    _chassis_plate(c, 7741)
    for x, y in ((3, 3), (12, 3), (3, 12), (12, 12), (7, 7)):
        gb.rivet(c, x, y, 6, 0)
    return c


def t_knell_integrator_ring() -> Canvas:
    """The resonator ring stock: pale metal in horizontal bands with a magenta
    harmonic running through the middle third.

    Banded because the model cuts thin horizontal strips out of this sprite for
    the four ring bars and the emitter, and a band survives being sliced where a
    picture does not.
    """
    c = Canvas(RING_RAMP)
    #: (first row, last row, ramp index) - bright at the top, dark at the base,
    #: which is the top-left key light applied to a cylinder.
    bands = ((0, 1, 5), (2, 3, 6), (4, 5, 4), (6, 7, 7), (8, 9, 7),
             (10, 11, 4), (12, 13, 3), (14, 15, 2))
    for y0, y1, idx in bands:
        for y in range(y0, y1 + 1):
            for x in range(SIZE):
                n = fbm(x * 1.7, y * 1.7, 8123, octaves=2)
                c.set(x, y, idx + (1 if n > 0.66 else (-1 if n < 0.34 else 0)))
    gb.clamp_body(c, 0, 7)
    # bolt seams every four pixels, so a sliced strip still has structure in x
    for x in range(1, SIZE, 4):
        for y in range(SIZE):
            gb.bump_at(c, x, y, -1, 0, 7)
    # gold pips on the harmonic band - the mod's specular note, two pixels only
    for x in (3, 11):
        c.set(x, 7, 8)
    return c


# ---------------------------------------------------------------------------
# Material items
# ---------------------------------------------------------------------------

def raw_knell() -> Sprite:
    """An unsmelted lump, on vanilla's raw_iron silhouette.

    Painted metal-first and then dirtied, which is the way round vanilla draws
    raw_iron and raw_gold - a raw metal is mostly metal. The outline and the
    internal structure are measured from the real sprite so this sits beside
    raw iron and raw gold as obviously the same kind of object.
    """
    sp = Sprite()
    # Wide range, for the same reason as raw null iron: the clumped-nugget read
    # is contrast, not outline.
    lv = vf.levels(vf.RAW, lo=0.12, hi=1.0)
    for (x, y), level in lv.items():
        level += 0.07 * (fbm(x * 2.3, y * 2.3, 4703, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(level))

    # Host rock still clinging to the shadowed side. Driven off the sprite's own
    # luminance rather than a blob, so the matrix collects where vanilla put the
    # dark pixels and the lit face stays metal.
    for (x, y), level in lv.items():
        n = fbm(x * 2.3, y * 2.3, 4711, octaves=2)
        if level < 0.50 and n > 0.48:
            sp.put(x, y, SLATE, SLATE.tone(0.34 + 0.30 * (n - 0.5)))

    sp.outline()
    sp.stamp([(4, 4), (9, 10)], HARMONIC, 1.0)
    return sp


def knell_ingot() -> Sprite:
    """Smelted knell, on vanilla's iron_ingot silhouette.

    Same measured form as the null iron ingot - bright top face, specular along
    the crease, darker front face - carried in the pale knell ramp with a
    magenta harmonic struck into the top face. Knell has more internal contrast
    than null iron, so it takes the full range of the ramp.
    """
    sp = Sprite()
    lv = vf.levels(vf.INGOT, lo=0.26, hi=1.0)
    for (x, y), level in lv.items():
        level += 0.10 * (fbm(x * 2.0, y * 2.0, 5171, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(level))
    sp.outline()
    sp.stamp([(6, 6), (7, 6), (8, 7)], HARMONIC, 1.0)
    return sp


def knell_template() -> Sprite:
    """The template: a cut plate with a pierced centre.

    Vanilla smithing templates are read at a glance by their silhouette - a
    rectangular plate with a hole punched through it - so that is what this is,
    in null iron with a magenta inlay at each corner. The hole matters: without
    it the sprite is just another ingot.
    """
    sp = Sprite()
    # A squared plate with clipped corners rather than an octagon: an octagon
    # reads as a washer at this size, and the whole job of the silhouette is to
    # say "flat piece of stock" the instant it appears in the hotbar.
    plate = poly([(3.0, 1.0), (13.0, 1.0), (15.0, 3.0), (15.0, 13.0),
                  (13.0, 15.0), (3.0, 15.0), (1.0, 13.0), (1.0, 3.0)])
    sp.paint(plate, NULL_IRON, 0.48, 3907, spread=0.34, light=0.30)

    # A knell lip two pixels wide, laid down before the aperture is punched
    # so it survives at full width once the middle is removed.
    lip = poly([(8.0, 2.4), (13.6, 8.0), (8.0, 13.6), (2.4, 8.0)])
    sp.paint(lip & plate, KNELL, 0.66, 3911, spread=0.26, light=0.26)

    # Punch the diamond out. The hole is the template's whole identity - without
    # it this is an ingot.
    for (x, y) in poly([(8.0, 4.6), (11.4, 8.0), (8.0, 11.4), (4.6, 8.0)]):
        sp.clear(x, y)

    sp.outline()
    sp.stamp([(3, 3), (12, 3), (3, 12), (12, 12)], HARMONIC, 1.0)
    return sp


# ---------------------------------------------------------------------------
# Tools
#
# All five share one handle, on the bottom-left to top-right diagonal
# art_direction.json specifies and gen_item_textures.harmonic_pickaxe already
# uses. Only the head changes, which is exactly how the vanilla tool family
# stays recognisable across five silhouettes.
# ---------------------------------------------------------------------------

def knell_pickaxe() -> Sprite:
    """The Knell tier pickaxe: same north-star curved geometry as harmonic_pickaxe,
    in pale knell metal over null iron with drawn horns and magenta sparks."""
    sp = Sprite()
    handle = stroke([(2.4, 14.4), (10.4, 5.6)], 1.05)
    head = stroke(bezier((4.6, 3.6), (12.4, 2.0), (14.2, 10.8)), 1.05)
    sp.paint(handle, NULL_IRON, 0.58, 5801, spread=0.34, light=0.26)
    sp.paint(head - handle, KNELL, 0.64, 5807, spread=0.32, light=0.30)
    # Subtle tier flare: slightly drawn horns
    for (x, y) in ((4, 2), (14, 11)):
        sp.put(x, y, KNELL, KNELL.tone(0.88))
    sp.outline()
    sp.stamp([(9, 5), (10, 6)], NULL_IRON, 1.0)        # lashing at the eye
    sp.stamp([(7, 3), (12, 3)], KNELL, 1.0)            # knell highlights
    sp.stamp([(6, 3), (13, 5)], HARMONIC, 1.0)         # harmonic magenta sparks
    return sp


def knell_axe() -> Sprite:
    """The Knell tier war-axe: exact vanilla rear lobe and haft socket passage
    with a hollow circular parabolic cutting blade and harmonic magenta sparks."""
    sp = Sprite()
    haft_levels = {
        (11, 4): 0.50, (12, 4): 0.55,
        (12, 5): 0.40,
        (9, 6): 0.52,
        (8, 7): 0.50, (9, 7): 0.60, (10, 7): 0.38,
        (7, 8): 0.50, (8, 8): 0.68, (9, 8): 0.38,
        (6, 9): 0.50, (7, 9): 0.60, (8, 9): 0.38,
        (5, 10): 0.50, (6, 10): 0.60, (7, 10): 0.38,
        (4, 11): 0.50, (5, 11): 0.68, (6, 11): 0.38,
        (3, 12): 0.50, (4, 12): 0.60, (5, 12): 0.38,
        (2, 13): 0.50, (3, 13): 0.68, (4, 13): 0.38,
        (2, 14): 0.38, (3, 14): 0.38,
    }
    rear_lobe_levels = {
        (10, 6): 0.60, (11, 6): 0.55, (12, 6): 0.85, (13, 6): 0.35,
        (11, 7): 0.75, (12, 7): 0.85, (13, 7): 0.35,
        (11, 8): 0.35, (12, 8): 0.35,
    }
    front_blade_levels = {
        (7, 1): 0.45, (8, 1): 0.85, (9, 1): 0.45, (10, 1): 0.40,
        (6, 2): 0.45, (7, 2): 0.85, (8, 2): 0.85, (9, 2): 0.85, (10, 2): 0.75, (11, 2): 0.45,
        (5, 3): 0.45, (6, 3): 0.85, (7, 3): 0.85, (8, 3): 0.75, (9, 3): 0.75, (10, 3): 0.70, (11, 3): 0.65, (12, 3): 0.45,
        (5, 4): 0.85, (6, 4): 0.85, (7, 4): 0.75,             (9, 4): 0.65, (10, 4): 0.60,
        (5, 5): 0.85, (6, 5): 0.75,             (8, 5): 0.60, (9, 5): 0.55, (10, 5): 0.50, (11, 5): 0.65,
        (4, 6): 0.45, (5, 6): 0.85, (6, 6): 0.75, (7, 6): 0.65, (8, 6): 0.50,
        (5, 7): 0.85, (6, 7): 0.75, (7, 7): 0.55,
    }
    for (x, y), lvl in haft_levels.items():
        lvl += 0.08 * (fbm(x * 2.1, y * 2.1, 5813, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(lvl))
    for (x, y), lvl in {**rear_lobe_levels, **front_blade_levels}.items():
        lvl += 0.09 * (fbm(x * 2.1, y * 2.1, 5819, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(lvl))
    sp.outline()
    # Explicitly set rear lobe outer pixels to Knell's dark tone #462354 (index 1) to ensure they read as Head material
    for p in ((13, 6), (13, 7), (11, 8), (12, 8)):
        sp.put(p[0], p[1], KNELL, 1)
    sp.stamp([(12, 6), (12, 7)], KNELL, 1.0)
    sp.stamp([(10, 6), (11, 6), (11, 7)], KNELL, 0.75)
    sp.stamp([(9, 6), (8, 7), (11, 4)], NULL_IRON, 1.0)
    sp.stamp([(8, 1), (7, 2), (6, 3), (5, 4), (5, 5), (5, 6), (6, 7)], KNELL, 1.0)
    sp.stamp([(7, 2), (5, 7)], HARMONIC, 1.0)
    # Ensure hollow cutouts at (8,4) and (7,5) and gap at (10,8)
    for p in ((8, 4), (7, 5), (10, 8)):
        if p in sp.cell:
            del sp.cell[p]
    return sp


def knell_shovel() -> Sprite:
    """The Knell tier resonant spade: symmetrical diamond scoop with defined chisel tip,
    central reinforced spine, and balanced harmonic magenta accents."""
    sp = Sprite()
    head, haft = vf.tool_levels(vf.SHOVEL)
    for (x, y), level in haft.items():
        level += 0.08 * (fbm(x * 2.1, y * 2.1, 5821, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    for (x, y), level in head.items():
        level += 0.09 * (fbm(x * 2.1, y * 2.1, 5827, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(level))
    sp.outline()
    sp.stamp([(9, 6), (8, 7)], NULL_IRON, 1.0)         # socket ferrule
    sp.stamp([(12, 3), (11, 4), (10, 5)], KNELL, 1.0)  # central spade spine
    sp.stamp([(13, 4), (10, 7)], HARMONIC, 1.0)        # symmetrical harmonic magenta sparks
    return sp


def knell_hoe() -> Sprite:
    """Vanilla's hoe form, with a sharpened adze hook in knell metal."""
    sp = Sprite()
    head, haft = vf.tool_levels(vf.HOE)
    for (x, y), level in haft.items():
        level += 0.08 * (fbm(x * 2.1, y * 2.1, 5833, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    for (x, y), level in head.items():
        level += 0.09 * (fbm(x * 2.1, y * 2.1, 5839, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(level))
    # Flare: clean connected beak point at (6, 1) and (6, 3)
    for (x, y) in ((6, 1), (6, 3)):
        sp.put(x, y, KNELL, KNELL.tone(0.88))
    sp.outline()
    sp.stamp([(10, 5), (9, 6)], NULL_IRON, 1.0)
    sp.stamp([(7, 2), (8, 2), (6, 3)], KNELL, 1.0)
    sp.stamp([(7, 1), (12, 3)], HARMONIC, 1.0)
    return sp


def knell_sword() -> Sprite:
    """Vanilla's sword form, with swept guard quillons and knell metal."""
    sp = Sprite()
    head, haft = vf.tool_levels(vf.SWORD)
    for (x, y), level in haft.items():
        level += 0.08 * (fbm(x * 2.1, y * 2.1, 5841, octaves=2) - 0.5)
        sp.put(x, y, NULL_IRON, NULL_IRON.tone(level))
    for (x, y), level in head.items():
        level += 0.09 * (fbm(x * 2.1, y * 2.1, 5847, octaves=2) - 0.5)
        sp.put(x, y, KNELL, KNELL.tone(level))
    # Subtle guard sweep flare (cleanly 4-connected at quillons)
    for (x, y) in ((1, 6), (2, 5), (10, 13)):
        if 0 <= x < 16 and 0 <= y < 16:
            sp.put(x, y, KNELL, KNELL.tone(0.88))
    sp.outline()
    sp.stamp([(4, 11), (5, 10)], NULL_IRON, 1.0)
    sp.stamp([(13, 2), (10, 5), (7, 8)], KNELL, 1.0)
    sp.stamp([(4, 11), (13, 2)], HARMONIC, 1.0)
    return sp


# ---------------------------------------------------------------------------
# Armour icons
#
# The span tables are gen_item_textures', unchanged: the four iron armour
# silhouettes are the strongest readability convention in the inventory, so the
# shape stays put and only the paint changes.
# ---------------------------------------------------------------------------

def _plate(mask, seed: int, trim, cavity=None, base: float = 0.64,
           spread: float = 0.20, bands=None, horns=None, cutouts=None) -> Sprite:
    """Knell's armour-icon painter.

    PLAYER, correcting the first pass: "the coloring looks like a jumbled
    mess, look at netherite, it looks like stacked, geometric armor plates,
    not randomness... you can add stuff but keep some symmetry." `bands` is
    full-width horizontal courses (inherently symmetric); `horns` are explicit
    mirrored accent points that may extend past the vanilla silhouette for a
    real spike rather than a notch; `cutouts` punches real holes. See
    gi._plate_icon for the same technique on the Resonance tier, one step
    calmer.
    """
    sp = Sprite()
    full_mask = set(mask) | set(horns or ())
    sp.paint(full_mask, KNELL, base, seed, spread=spread, light=0.32)
    if cavity:
        for (x, y) in cavity & mask:
            sp.put(x, y, KNELL, KNELL.tone(0.05))
    if bands:
        # Same curved-band technique as gi._plate_icon - see that docstring.
        xs = [x for (x, _) in mask]
        if xs:
            x_lo, x_hi = min(xs), max(xs)
            half = max(1, (x_hi - x_lo) / 2.0)
            centre = (x_lo + x_hi) / 2.0
            curve = 2
            for row in bands:
                for x in range(x_lo, x_hi + 1):
                    t = 1.0 - min(1.0, abs(x - centre) / half)
                    y = row - round(curve * t * t)
                    if (x, y) in full_mask and (not cavity or (x, y) not in cavity):
                        sp.put(x, y, KNELL, KNELL.tone(0.96))
    if horns:
        for (x, y) in horns:
            sp.put(x, y, KNELL, KNELL.tone(0.92))
    if cutouts:
        for (x, y) in cutouts:
            if (x, y) in full_mask:
                sp.clear(x, y)
    sp.outline()
    sp.stamp([(x, y) for (x, y) in trim if (x, y) in full_mask], HARMONIC, 1.0)
    return sp


def knell_helmet() -> Sprite:
    """Pale dome: stacked plate courses, a vented ear guard cut clean through,
    and a pair of horns swept back from the temples - bolder than Resonance's,
    since this is the tier above it."""
    mask = spans(gi.HELMET_SPANS)
    cavity = spans({9: [(5, 10)], 10: [(5, 10)]})
    # Horns curve IN toward the dome as they rise, matching the Resonance
    # shape one size bolder - straight outward spikes read too aggressive and
    # too mechanical next to a rounded dome.
    # Horns properly 4-connected to the dome (row4 edges are x=4/x=11), rising
    # straight and hooking one step back toward centre at the tip - bolder
    # than Resonance's by one extra segment, not by floating further away.
    sp = _plate(mask, 9101, [(5, 8), (6, 8), (9, 8), (10, 8)], cavity=cavity,
                base=0.54, spread=0.20, bands=[7],
                horns=[(3, 4), (3, 3), (3, 2), (4, 1), (12, 4), (12, 3), (12, 2), (11, 1)],
                cutouts=[(3, 6), (12, 6)])
    sp.stamp([(7, 8), (8, 8)], HARMONIC, 0.55)
    sp.stamp([(5, 4), (6, 4)], KNELL, 1.0)
    # PLAYER: "correspond this by making the knell horns the pinkish [one]" -
    # same fix as Resonance's blue-glow horns, in this tier's own accent.
    sp.stamp([(3, 4), (3, 3), (3, 2), (4, 1), (12, 4), (12, 3), (12, 2), (11, 1)], HARMONIC, 1.0)
    return sp


def knell_chestplate() -> Sprite:
    """Pauldrons and a chest resonator, lit at the core, two plate courses,
    and a vented gap at each collarbone cut clean through the plate."""
    mask = spans(gi.CHESTPLATE_SPANS)
    sp = _plate(mask, 9113, [(7, 9), (8, 9), (7, 10), (8, 10)],
                base=0.50, spread=0.20, bands=[5, 9], cutouts=[(2, 3), (13, 3)])
    sp.stamp([(6, 9), (9, 9)], HARMONIC, 0.50)
    sp.stamp([(3, 3), (12, 3)], HARMONIC, 0.60)
    return sp


def knell_leggings() -> Sprite:
    """Two curved plate courses down each shaft, not one belt line - but not
    four either, which read as slats rather than plate."""
    mask = spans(gi.LEGGINGS_SPANS)
    sp = _plate(mask, 9127, [(4, 5), (5, 5), (10, 5), (11, 5)],
                base=0.48, spread=0.18, bands=[5, 10])
    sp.stamp([(7, 5), (8, 5)], HARMONIC, 0.45)
    return sp


def knell_boots() -> Sprite:
    """Curved plate courses from ankle to toe, plus a small heel spur."""
    mask = spans(gi.BOOTS_SPANS)
    sp = _plate(mask, 9141, [(4, 7), (5, 7), (10, 7), (11, 7)],
                base=0.46, spread=0.18, bands=[6, 9],
                horns=[(0, 10), (15, 10)])
    sp.stamp([(3, 10), (12, 10)], HARMONIC, 0.45)
    return sp


# ---------------------------------------------------------------------------
# Worn-armour sheets
#
# Regions come from gen_item_textures' box_faces arithmetic, which reproduces
# the unwrap the armour meshes actually sample. Nothing is guessed and nothing
# is lifted from a vanilla sheet.
# ---------------------------------------------------------------------------

def resonant_layer_1() -> gi.Sheet:
    """Helmet, chestplate and boots on the adult 64x32 humanoid layout."""
    sh = gi.Sheet(64, 32)
    helm = gi.adult_helmet_region()
    chest = gi.adult_chest_region()
    boots = gi.adult_boot_region()
    sh.plate(helm, KNELL, 4301, base=0.48, spread=0.38)
    sh.plate(chest, KNELL, 4307, base=0.50, spread=0.38)
    sh.plate(boots, KNELL, 4313, base=0.46, spread=0.36)

    # --- HELMET ---
    # Inlaid brow visor trim across row 10 of front face (above visor/eyes):
    fx0, fy0, fw, fh = gi.ADULT_HEAD["front"]
    sh.sp.put(fx0 + 1, fy0 + 2, HARMONIC, 4)
    sh.sp.put(fx0 + 2, fy0 + 2, HARMONIC, 4)
    sh.sp.put(fx0 + 3, fy0 + 2, HARMONIC, 2)
    sh.sp.put(fx0 + 4, fy0 + 2, HARMONIC, 2)
    sh.sp.put(fx0 + 5, fy0 + 2, HARMONIC, 4)
    sh.sp.put(fx0 + 6, fy0 + 2, HARMONIC, 4)
    sh.sp.put(fx0 + 0, fy0 + 2, HARMONIC, 1)
    sh.sp.put(fx0 + 7, fy0 + 2, HARMONIC, 1)

    # Forehead curved plate band at row 9
    sh.plates(gi.ADULT_HEAD["front"], KNELL, course=[1], lit=0.96)
    for key in ("right", "left", "back"):
        sh.plates(gi.ADULT_HEAD[key], KNELL, course=[2], lit=0.92)

    # Horns sweeping from temples up across side faces and crown top (EXACTLY AS APPROVED)
    # Right side:
    sh.sp.put(7, 11, HARMONIC, 1)
    sh.sp.stamp([(6, 10), (7, 10), (5, 9), (6, 9), (4, 8), (5, 8)], HARMONIC, 1.0)
    sh.sp.put(7, 9, HARMONIC, HARMONIC.tone(0.50))
    sh.sp.put(6, 8, HARMONIC, HARMONIC.tone(0.50))
    # Left side:
    sh.sp.put(16, 11, HARMONIC, 1)
    sh.sp.stamp([(16, 10), (17, 10), (17, 9), (18, 9), (18, 8), (19, 8)], HARMONIC, 1.0)
    sh.sp.put(16, 9, HARMONIC, HARMONIC.tone(0.50))
    sh.sp.put(17, 8, HARMONIC, HARMONIC.tone(0.50))
    # Front corners (temple attachment):
    sh.sp.stamp([(fx0, fy0 + 1), (fx0, fy0 + 2),
                 (fx0 + fw - 1, fy0 + 1), (fx0 + fw - 1, fy0 + 2)], HARMONIC, 1.0)
    # Top face crown sweep:
    sh.sp.stamp([(8, 3), (8, 4), (9, 4), (9, 5), (10, 5)], HARMONIC, 1.0)
    sh.sp.put(9, 3, HARMONIC, HARMONIC.tone(0.50))
    sh.sp.stamp([(15, 3), (15, 4), (14, 4), (14, 5), (13, 5)], HARMONIC, 1.0)
    sh.sp.put(14, 3, HARMONIC, HARMONIC.tone(0.50))

    # Dome top highlight
    tx0, ty0, tw, td = gi.ADULT_HEAD["top"]
    sh.sp.stamp([(tx0 + 3, ty0 + 2), (tx0 + 4, ty0 + 2)], KNELL, 1.0)

    # --- CHESTPLATE ---
    # Curved plate courses across torso with soft metallic luster & crease shading
    for key in ("right", "front", "left", "back"):
        face = gi.ADULT_BODY[key]
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        for r in (3, 8):
            gi.curved_band(lambda x, y: sh.sp.put(x, y, KNELL, 5) if sh.sp.opaque(x, y) else None,
                           face_mask, KNELL, y0 + r)
            if w >= 8:
                sh.sp.put(x0 + w // 2 - 1, y0 + r - 1, KNELL, 6)
                sh.sp.put(x0 + w // 2, y0 + r - 1, KNELL, 6)
            for x in range(x0, x0 + w):
                if (x, y0 + r + 1) in face_mask and sh.sp.opaque(x, y0 + r + 1):
                    sh.sp.put(x, y0 + r + 1, KNELL, 2)

    # Central resonator gem on chest front (inlaid faceted structure)
    bx0, by0, bw, bh = gi.ADULT_BODY["front"]
    sh.sp.put(bx0 + 3, by0 + 4, HARMONIC, 4)  # top-left facet highlight
    sh.sp.put(bx0 + 4, by0 + 4, HARMONIC, 3)  # top-right facet
    sh.sp.put(bx0 + 3, by0 + 5, HARMONIC, 3)  # bot-left facet
    sh.sp.put(bx0 + 4, by0 + 5, HARMONIC, 2)  # bot-right facet shadow
    sh.sp.put(bx0 + 2, by0 + 4, HARMONIC, 2)  # left flank bevel
    sh.sp.put(bx0 + 5, by0 + 4, HARMONIC, 2)  # right flank bevel
    sh.sp.put(bx0 + 3, by0 + 6, HARMONIC, 1)  # bottom tip bezel
    sh.sp.put(bx0 + 4, by0 + 6, HARMONIC, 1)  # bottom tip bezel
    sh.sp.put(bx0 + 2, by0 + 5, KNELL, 2)     # plate recess shadow
    sh.sp.put(bx0 + 5, by0 + 5, KNELL, 2)     # plate recess shadow

    # Pauldrons / arms: 2-tone rounded inlaid studs
    for key in ("right", "front", "left", "back"):
        face = gi.ADULT_ARM[key]
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        gi.curved_band(lambda x, y: sh.sp.put(x, y, KNELL, 5) if sh.sp.opaque(x, y) else None,
                       face_mask, KNELL, y0 + 3)
    for key in ("front", "right", "left", "back"):
        ax0, ay0, _, _ = gi.ADULT_ARM[key]
        sh.sp.put(ax0 + 1, ay0 + 1, HARMONIC, 4)  # highlight
        sh.sp.put(ax0 + 2, ay0 + 1, HARMONIC, 2)  # shadow bevel

    # --- BOOTS ---
    for key in ("right", "front", "left", "back"):
        face = gi.ADULT_LEG[key]
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        for r in (7, 9):
            gi.curved_band(lambda x, y: sh.sp.put(x, y, KNELL, 5) if sh.sp.opaque(x, y) else None,
                           face_mask, KNELL, y0 + r)
    # Inlaid cuff trim
    lx0, ly0, _, _ = gi.ADULT_LEG["front"]
    sh.sp.put(lx0 + 1, ly0 + 7, HARMONIC, 4)
    sh.sp.put(lx0 + 2, ly0 + 7, HARMONIC, 2)
    # Heel spurs
    ox0, oy0, _, _ = gi.ADULT_LEG["right"]
    sh.sp.put(ox0, oy0 + 10, HARMONIC, 4)
    sh.sp.put(ox0, oy0 + 11, HARMONIC, 1)
    ix0, iy0, _, _ = gi.ADULT_LEG["left"]
    sh.sp.put(ix0 + 3, iy0 + 10, HARMONIC, 4)
    sh.sp.put(ix0 + 3, iy0 + 11, HARMONIC, 1)
    for (x, y) in gi.face_rect(gi.ADULT_LEG["bottom"]):
        sh.sp.put(x, y, KNELL, 1)

    return sh


def resonant_layer_2() -> gi.Sheet:
    """Leggings on the adult 64x32 humanoid_leggings layout."""
    sh = gi.Sheet(64, 32)
    hips, skirt = gi.adult_leggings_regions()
    sh.plate(hips, KNELL, 4401, base=0.46, spread=0.38)
    sh.plate(skirt, KNELL, 4407, base=0.48, spread=0.38)

    # Waistband / belt on ADULT_BODY rows 27..31:
    bx0, by0, _, _ = gi.ADULT_BODY["front"]
    sh.sp.put(bx0 + 3, by0 + 7, HARMONIC, 4)  # buckle gem highlight
    sh.sp.put(bx0 + 4, by0 + 7, HARMONIC, 2)  # buckle gem shadow
    sh.sp.put(bx0 + 2, by0 + 7, KNELL, 5)     # silver clasp left
    sh.sp.put(bx0 + 5, by0 + 7, KNELL, 5)     # silver clasp right
    sh.sp.put(bx0 + 1, by0 + 7, HARMONIC, 3)  # belt clip left
    sh.sp.put(bx0 + 6, by0 + 7, HARMONIC, 3)  # belt clip right
    sh.sp.put(bx0 + 3, by0 + 8, HARMONIC, 1)  # buckle recess shadow
    sh.sp.put(bx0 + 4, by0 + 8, HARMONIC, 1)  # buckle recess shadow

    for key in ("right", "front", "left", "back"):
        face = gi.ADULT_BODY[key]
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        gi.curved_band(lambda x, y: sh.sp.put(x, y, KNELL, 5) if sh.sp.opaque(x, y) else None,
                       face_mask, KNELL, y0 + 9)
        for x in range(x0, x0 + w):
            if (x, y0 + 10) in face_mask and sh.sp.opaque(x, y0 + 10):
                sh.sp.put(x, y0 + 10, KNELL, 2)

    # Legs (ADULT_LEG rows 20..28):
    for key in ("right", "front", "left", "back"):
        face = gi.ADULT_LEG[key]
        x0, y0, w, h = face
        face_mask = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
        for r in (2, 6):
            gi.curved_band(lambda x, y: sh.sp.put(x, y, KNELL, 5) if sh.sp.opaque(x, y) else None,
                           face_mask, KNELL, y0 + r)
            if key == "front":
                sh.sp.put(x0 + 1, y0 + r - 1, KNELL, 6)
                sh.sp.put(x0 + 2, y0 + r - 1, KNELL, 6)
            for x in range(x0, x0 + w):
                if (x, y0 + r + 1) in face_mask and sh.sp.opaque(x, y0 + r + 1):
                    sh.sp.put(x, y0 + r + 1, KNELL, 2)

    # Knee plate accent on front face - 2-tone bevelled inlay
    lx0, ly0, _, _ = gi.ADULT_LEG["front"]
    sh.sp.put(lx0 + 1, ly0 + 6, HARMONIC, 4)  # top highlight
    sh.sp.put(lx0 + 2, ly0 + 6, HARMONIC, 2)  # lower shadow
    for (x, y) in gi.face_rect(gi.ADULT_LEG["top"]):
        sh.sp.put(x, y, KNELL, 1)

    return sh


def resonant_baby() -> gi.Sheet:
    """The 64x64 baby armour layout - a different unwrap, not a scaled copy."""
    sh = gi.Sheet(64, 64)
    helm, chest, boots = gi.baby_regions()
    sh.plate(helm, KNELL, 4501, base=0.52, spread=0.55)
    sh.plate(chest, KNELL, 4507, base=0.50, spread=0.55)
    sh.plate(boots, KNELL, 4513, base=0.46, spread=0.55)

    # Brow trim across baby helmet front
    sh.trim(gi.band(gi.BABY_HEAD["front"], 10, 10), HARMONIC, level=1.0)
    # Chest resonator core on baby body front
    bx0, by0, bw, bh = gi.BABY_BODY["front"]
    sh.sp.stamp([(bx0 + 2, by0 + 2), (bx0 + 3, by0 + 2)], HARMONIC, 1.0)
    sh.sp.stamp([(bx0 + 1, by0 + 2), (bx0 + 4, by0 + 2)], HARMONIC, 0.50)
    # Boot trim
    sh.trim({(x, 23) for x in range(0, 18)}, HARMONIC, level=0.9)
    sh.trim({(x, 30) for x in range(18, 30)}, HARMONIC, level=0.9)
    sh.trim({(x, 21) for x in range(18, 21)}, HARMONIC, level=0.9)
    sh.trim({(x, 28) for x in range(18, 21)}, HARMONIC, level=0.9)
    sh.plates(gi.BABY_BODY["front"], KNELL, course=[2], lit=1.0)
    return sh


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BLOCK_TEXTURES = [
    ("knell_ore", t_knell_ore),
    ("knell_block", t_knell_block),
    ("knell_integrator_top", t_knell_integrator_top),
    ("knell_integrator_side", t_knell_integrator_side),
    ("knell_integrator_bottom", t_knell_integrator_bottom),
    ("knell_integrator_ring", t_knell_integrator_ring),
]

ITEM_TEXTURES = [
    ("raw_knell", raw_knell),
    ("knell_ingot", knell_ingot),
    ("knell_template", knell_template),
    ("knell_sword", knell_sword),
    ("knell_pickaxe", knell_pickaxe),
    ("knell_axe", knell_axe),
    ("knell_shovel", knell_shovel),
    ("knell_hoe", knell_hoe),
    ("knell_helmet", knell_helmet),
    ("knell_chestplate", knell_chestplate),
    ("knell_leggings", knell_leggings),
    ("knell_boots", knell_boots),
]

EQUIPMENT_SHEETS = [
    ("humanoid/knell.png", resonant_layer_1, (64, 32)),
    ("humanoid_leggings/knell.png", resonant_layer_2, (64, 32)),
    ("humanoid_baby/knell.png", resonant_baby, (64, 64)),
]


# ---------------------------------------------------------------------------
# Audit - the same budget tools/verify_textures.py applies
# ---------------------------------------------------------------------------

MIN_COLOURS, MAX_COLOURS = 5, 16


def audit(img: Image.Image, expect, item: bool) -> list[str]:
    problems: list[str] = []
    if expect and img.size != expect:
        problems.append(f"size {img.size[0]}x{img.size[1]}, expected {expect[0]}x{expect[1]}")

    n = len(unique_colors(img))
    ceiling = MAX_COLOURS if expect == (16, 16) else 40
    if not (MIN_COLOURS <= n <= ceiling):
        problems.append(f"{n} colours, want {MIN_COLOURS}-{ceiling}")

    opaque = [c for c in img.convert("RGBA").getdata() if c[3] > 0]
    if opaque:
        counts: dict = {}
        for c in opaque:
            counts[c[:3]] = counts.get(c[:3], 0) + 1
        share = max(counts.values()) / len(opaque)
        if share > 0.85:
            problems.append(f"dominant colour covers {share:.0%} (limit 85%)")

    off = [c for c in unique_colors(img) if not gb.on_palette(c[:3])]
    if off:
        problems.append(f"{len(off)} off-palette colour(s)")

    if item:
        ok, ratio, note = _outline_check(img)
        if not ok:
            problems.append(f"no dark outline ({note or f'{ratio:.0%} of edge dark, need 55%'})")
    return problems


def _outline_check(img: Image.Image):
    """Mirror of tools/verify_textures.check_outline, so this fails at author
    time rather than at the gate."""
    px = img.convert("RGBA").load()
    w, h = img.size

    def opaque(x: int, y: int) -> bool:
        return 0 <= x < w and 0 <= y < h and px[x, y][3] > 0

    edge, interior = [], []
    for y in range(h):
        for x in range(w):
            if not opaque(x, y):
                continue
            lum = 0.2126 * px[x, y][0] + 0.7152 * px[x, y][1] + 0.0722 * px[x, y][2]
            is_edge = any(not opaque(x + dx, y + dy)
                          for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            (edge if is_edge else interior).append(lum)

    if not edge:
        return False, 0.0, "full-bleed, no silhouette"
    if not interior:
        return True, 1.0, "thin sprite"
    mean_interior = sum(interior) / len(interior)
    darker = sum(1 for lum in edge if lum <= mean_interior * 0.92)
    return darker / len(edge) >= 0.55, darker / len(edge), ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    for d in (BLOCK_DIR, ITEM_DIR):
        d.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    blocks: list[tuple[str, Image.Image]] = []
    items: list[tuple[str, Image.Image]] = []
    sheets: list[tuple[str, Image.Image]] = []

    print(f"{'texture':<34} {'size':<9} colours")
    for name, factory in BLOCK_TEXTURES:
        img = factory().save(BLOCK_DIR / f"{name}.png")
        blocks.append((name, img))
        problems = audit(img, (16, 16), item=False)
        print(f"block/{name:<28} {img.size[0]}x{img.size[1]:<6} {len(unique_colors(img))}"
              + ("  " + "; ".join(problems) if problems else ""))
        failures += [f"block/{name}: {p}" for p in problems]

    for name, factory in ITEM_TEXTURES:
        img = factory().save(ITEM_DIR / f"{name}.png")
        items.append((name, img))
        problems = audit(img, (16, 16), item=True)
        print(f"item/{name:<29} {img.size[0]}x{img.size[1]:<6} {len(unique_colors(img))}"
              + ("  " + "; ".join(problems) if problems else ""))
        failures += [f"item/{name}: {p}" for p in problems]

    for rel, factory, want in EQUIPMENT_SHEETS:
        img = factory().save(EQUIP / rel)
        sheets.append((rel, img))
        problems = audit(img, want, item=False)
        print(f"{rel:<34} {img.size[0]}x{img.size[1]:<6} {len(unique_colors(img))}"
              + ("  " + "; ".join(problems) if problems else ""))
        failures += [f"{rel}: {p}" for p in problems]

    if "--preview" in sys.argv:
        gi.contact_sheet(items, PREVIEW_DIR / "knell_items.png", columns=6)
        gi.contact_sheet(blocks, PREVIEW_DIR / "knell_blocks.png", columns=6)
        gi.strip_sheet(sheets, PREVIEW_DIR / "knell_equipment.png")
        print(f"\ncontact sheets written to {PREVIEW_DIR}")

    if failures:
        print(f"\nFAILED with {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

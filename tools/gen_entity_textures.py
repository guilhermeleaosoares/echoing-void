"""
The Echoing Void - creature texture sheets (base + emissive glow).

This work used to live inside gen_item_textures.py and produced three flat grey
animals. It is here now, and it is built on a different principle.

WHAT CHANGED, AND WHY
---------------------
The old sheets were drawn through ev_palette.Ramp, which caps a palette at six
indexed colours. Measured against the real thing that is simply the wrong
target: vanilla's spider sheet carries 13 distinct colours, the warden's 18, the
creaking's 17 and the iron golem's 46. Six colours cannot describe a lit,
mottled, banded material, so everything came out as flat value steps - grey
blocks. So these sheets are painted in direct RGBA off multi-stop material
ramps, and each lands in the 15-30 colour band vanilla actually uses.

Three further conventions were measured off vanilla and copied here:

  * per-face value steps. A box's top face is the lightest thing on the sheet
    and its underside the darkest, with the front/sides between, so a static box
    still reads as a lit solid.
  * within-face key light from the top-left, matching every other texture in
    this mod, plus a soft vertical gradient so tall faces do not read as decals.
  * emissive detail is a SEPARATE, mostly transparent sheet, exactly as vanilla
    does for spider eyes and the warden's bioluminescent layer. The base sheet
    still has to read on its own in the dark, so the glow pixels also exist,
    dimmer, on the base sheet.

The sheets are painted straight from the geometry: this module imports the
model builders from gen_geo_models and asks each one where it allocated the UV
rectangle for a given cube size and material group, so a change to the geometry
moves the paint with it and the two can never drift.

Run:  python tools/gen_entity_textures.py
Outputs:
  src/main/resources/assets/echoing_void/textures/entity/<creature>.png
  src/main/resources/assets/echoing_void/textures/entity/<creature>_glow.png
  build/texture_preview/creatures_sheets.png      the flat sheets, 6x, labelled
  build/texture_preview/creatures_render.png      isometric preview of each mob
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_geo_models import BUILDERS, Model             # noqa: E402
from ev_palette import parse_hex, mix, shift           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEX_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "entity"
PREVIEW_DIR = ROOT / "build" / "texture_preview"

RGBA = tuple[int, int, int, int]


# ---------------------------------------------------------------------------
# noise
# ---------------------------------------------------------------------------
#
# ev_palette's fbm is periodic with period 16 so that block textures tile. An
# entity sheet must NOT tile - a 60px face carrying a 16px repeat looks like
# wallpaper - so this module has its own aperiodic value noise.

def _hash(x: int, y: int, seed: int) -> float:
    h = (x * 0x27D4EB2D) ^ (y * 0x165667B1) ^ (seed * 0x9E3779B1)
    h &= 0xFFFFFFFF
    h = (h ^ (h >> 15)) * 0x85EBCA6B
    h &= 0xFFFFFFFF
    h ^= h >> 13
    return (h & 0xFFFFFF) / float(0x1000000)


def _vnoise(x: float, y: float, seed: int) -> float:
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    n00 = _hash(x0, y0, seed)
    n10 = _hash(x0 + 1, y0, seed)
    n01 = _hash(x0, y0 + 1, seed)
    n11 = _hash(x0 + 1, y0 + 1, seed)
    a = n00 + (n10 - n00) * sx
    b = n01 + (n11 - n01) * sx
    return a + (b - a) * sy


def grain(x: float, y: float, seed: int, octaves: int = 3, scale: float = 3.0) -> float:
    """Aperiodic fractal noise in [-1, 1]."""
    total, amp, norm, freq = 0.0, 1.0, 0.0, 1.0 / scale
    for o in range(octaves):
        total += _vnoise(x * freq, y * freq, seed + o * 7919) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return (total / norm) * 2.0 - 1.0


# ---------------------------------------------------------------------------
# material ramps
# ---------------------------------------------------------------------------

def ramp(*stops: str, steps: int = 7) -> list[RGBA]:
    """Interpolate hex anchors into an ordered dark -> light ramp."""
    anchors = [parse_hex(s) for s in stops]
    out: list[RGBA] = []
    for i in range(steps):
        pos = (i / (steps - 1)) * (len(anchors) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(anchors) - 1)
        out.append(mix(anchors[lo], anchors[hi], pos - lo))
    return out


# Palette families come from docs/spec/art_direction.json. The weaver is cold
# violet chitin with cyan light; the golem is phonolite banded with amber
# strata and gold crystal; the wraith is arcane violet shading into hot magenta.

CHITIN = ramp("#0D0B14", "#1A1726", "#28223C", "#372E56", "#4A3E72", "#645594", steps=7)
CHITIN_PALE = ramp("#241E36", "#3B3255", "#544878", "#70629C", "#8E80B8", steps=6)
CYAN = ramp("#0B5A6B", "#0B7A8C", "#1FA9BE", "#3FD0E0", "#7DE9F5", "#CFFAFF", steps=6)

STONE = ramp("#0F1014", "#1C1D21", "#282A31", "#3B4252", "#4C566A", "#63708A", "#8794AB", steps=7)
AMBER = ramp("#1E150A", "#3A2A16", "#6B4E2A", "#8A6A3C", "#C89B4A", "#E8C87A", steps=6)
GOLD = ramp("#4A3413", "#8A6A3C", "#C89B4A", "#E8C87A", "#FFD700", "#FFF3C4", steps=6)
CHALK = ramp("#6E7B94", "#8794AB", "#A8B4C8", "#C9D3E2", "#DCE3EE", steps=5)

ARCANE = ramp("#160B1E", "#2A1436", "#3A1D47", "#5A2E6B", "#7D3A8E", "#B14A9E", steps=6)
MAGENTA = ramp("#5A1240", "#95195E", "#D1237E", "#FF007F", "#FC79A3", "#FFD3EC", steps=6)


def pick(r: list[RGBA], value: float) -> RGBA:
    return r[max(0, min(len(r) - 1, int(round(value))))]


# ---------------------------------------------------------------------------
# sheet
# ---------------------------------------------------------------------------

class Sheet:
    """A texture surface that snaps every write onto a fixed palette.

    Painting in free RGBA is convenient - blends, gradients, radial falloff -
    but it is also how a 16x16-style sheet ends up with five hundred nearly
    identical colours, which is exactly the mush that made the old creatures
    read as noise. Vanilla sheets are effectively indexed: the spider uses 13
    colours, the iron golem 46. So every write here is snapped to the nearest
    entry of the creature's own palette, and alpha to one of a few levels. The
    drawing code stays expressive; the output stays indexed.
    """

    def __init__(self, size: int, palette: list[RGBA], alphas=(255,)):
        self.size = size
        self.img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.px = self.img.load()
        self.palette = list(palette)
        self.alphas = sorted(set(alphas))
        self._snap_cache: dict[RGBA, RGBA] = {}

    def snap(self, c: RGBA) -> RGBA:
        hit = self._snap_cache.get(c)
        if hit is not None:
            return hit
        r, g, b, a = c
        if a <= 4:
            out: RGBA = (0, 0, 0, 0)
        else:
            best = min(self.palette,
                       key=lambda p: 0.30 * (p[0] - r) ** 2
                       + 0.59 * (p[1] - g) ** 2
                       + 0.11 * (p[2] - b) ** 2)
            alpha = min(self.alphas, key=lambda x: abs(x - a))
            out = (best[0], best[1], best[2], alpha)
        self._snap_cache[c] = out
        return out

    def set(self, x: int, y: int, c: RGBA) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.px[x, y] = self.snap(c)

    def get(self, x: int, y: int) -> RGBA:
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.px[x, y]
        return (0, 0, 0, 0)

    def blend(self, x: int, y: int, c: RGBA, t: float) -> None:
        base = self.get(x, y)
        if base[3] == 0:
            self.set(x, y, c)
        else:
            self.set(x, y, mix(base, c, t))


# ---------------------------------------------------------------------------
# box unwrap
# ---------------------------------------------------------------------------
#
# Bedrock's cross layout, identical to the one tools/render_geo_preview.py and
# the game itself use:
#
#         [ up  ][ down ]
#   [west][north][ east ][south]

def box_faces(u: int, v: int, w: int, h: int, d: int) -> dict[str, tuple[int, int, int, int]]:
    return {
        "up":    (u + d, v, w, d),
        "down":  (u + d + w, v, w, d),
        "west":  (u, v + d, d, h),
        "north": (u + d, v + d, w, h),
        "east":  (u + d + w, v + d, d, h),
        "south": (u + d + w + d, v + d, w, h),
    }


# How far up its ramp each face sits. A box lit from above and in front reads as
# a solid without any outline work, which is exactly how vanilla does it.
FACE_STEP = {"up": 1.7, "north": 0.5, "west": 0.1, "east": -0.5, "south": -0.9, "down": -2.0}

# Faces whose art should be flipped so that "front" detail lands the right way
# round on the mirrored side of the box.
SIDE_FACES = ("west", "east", "north", "south")


def face_shade(i: int, j: int, fw: int, fh: int, face: str) -> float:
    """Top-left key light plus a soft vertical falloff, in ramp steps."""
    v = 0.0
    if j == 0:
        v += 0.55
    if i == 0:
        v += 0.30
    if j == fh - 1:
        v -= 0.55
    if i == fw - 1:
        v -= 0.30
    if fh > 3:
        v -= (j / max(1, fh - 1)) * 0.7
    if face in ("up", "down"):
        v += 0.2 - (j / max(1, fh - 1)) * 0.4
    return v


# ---------------------------------------------------------------------------
# generic painters
# ---------------------------------------------------------------------------

def fill_face(sheet: Sheet, rect, r: list[RGBA], base: float, face: str,
              seed: int, grain_amount: float = 1.1, scale: float = 3.0) -> None:
    x0, y0, fw, fh = rect
    for j in range(fh):
        for i in range(fw):
            n = grain(x0 + i, y0 + j, seed, scale=scale) * grain_amount
            level = base + FACE_STEP[face] + face_shade(i, j, fw, fh, face) + n
            sheet.set(x0 + i, y0 + j, pick(r, level))


def band_face(sheet: Sheet, rect, neutral: list[RGBA], accent: list[RGBA],
              base: float, face: str, seed: int, profile) -> None:
    """Horizontal strata banding. `profile(row) -> (ramp, offset)`."""
    x0, y0, fw, fh = rect
    for j in range(fh):
        r, off = profile(j)
        target = accent if r == "a" else neutral
        for i in range(fw):
            n = grain(x0 + i, y0 + j, seed, scale=2.6) * 0.9
            level = base + off + FACE_STEP[face] + face_shade(i, j, fw, fh, face) + n
            sheet.set(x0 + i, y0 + j, pick(target, level))


def strata_profile(seed: int):
    """A deterministic, geological-looking stack of bands.

    Even-width stripes read as a barcode, so band thickness comes off a hash and
    varies from 1 to 4 rows, with the occasional bright parting line.
    """
    def profile(row: int):
        # Walk a fixed pseudo-random sequence of band thicknesses.
        y, idx = 0, 0
        while True:
            h = 1 + int(_hash(idx, 0, seed) * 4)
            kind = _hash(idx, 1, seed)
            if row < y + h:
                if kind > 0.62:
                    return ("a", 0.4 if row == y else -0.2)
                if kind > 0.5:
                    return ("n", 1.3 if row == y else 0.0)
                return ("n", 0.2 if row == y else -0.35)
            y += h
            idx += 1
            if idx > 64:
                return ("n", 0.0)
    return profile


def crackle(sheet: Sheet, rect, dark: RGBA, seed: int, density: float = 0.055) -> None:
    """Short dark fissures. Rock without cracks reads as plastic."""
    x0, y0, fw, fh = rect
    for j in range(fh):
        for i in range(fw):
            if _hash(x0 + i, y0 + j, seed) < density:
                length = 1 + int(_hash(i, j, seed + 3) * 3)
                horiz = _hash(i, j, seed + 5) > 0.5
                for k in range(length):
                    sheet.blend(x0 + i + (k if horiz else 0),
                                y0 + j + (0 if horiz else k), dark, 0.72)


def outline_bottom(sheet: Sheet, rect, c: RGBA) -> None:
    """Darken the last row so stacked boxes separate visually."""
    x0, y0, fw, fh = rect
    for i in range(fw):
        sheet.blend(x0 + i, y0 + fh - 1, c, 0.55)


# ---------------------------------------------------------------------------
# ECHO WEAVER
# ---------------------------------------------------------------------------
#
# Cold violet chitin, banded, with cyan light in the seams. Cyan is the weaver's
# telegraph colour, so it appears only where the creature can flare it: eyes,
# crest membranes, leg joints, spinnerets.

def weaver_carapace(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 3.2, face, seed, grain_amount=1.2, scale=3.4)

    # Chitin plates: a light leading edge over a dark seam, every few rows.
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(1, fh - 1):
            if (j + (seed % 3)) % 4 != 0:
                continue
            for i in range(fw):
                base.blend(x0 + i, y0 + j, CHITIN[5], 0.55)
                if j + 1 < fh:
                    base.blend(x0 + i, y0 + j + 1, CHITIN[0], 0.55)

    # A raised ridge down the middle of the top face, with a cyan hairline.
    x0, y0, fw, fh = faces["up"]
    for j in range(fh):
        cx = x0 + fw // 2
        base.blend(cx - 1, y0 + j, CHITIN[5], 0.6)
        base.blend(cx, y0 + j, CHITIN_PALE[4], 0.5)
        if j % 3 == 1:
            base.blend(cx, y0 + j, CYAN[2], 0.55)
            glow.set(cx, y0 + j, (*CYAN[3][:3], 150))
    outline_bottom(base, faces["down"], parse_hex("#07060B"))


def weaver_plate(base: Sheet, glow: Sheet, u, v, size, seed):
    """The abdomen's dorsal plate: brighter chitin with a lit spine."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN_PALE, 2.4, face, seed, grain_amount=1.0)

    x0, y0, fw, fh = faces["up"]
    cx = x0 + fw // 2
    for j in range(fh):
        t = j / max(1, fh - 1)
        base.set(cx, y0 + j, mix(CYAN[1], CYAN[4], 1.0 - t))
        base.blend(cx - 1, y0 + j, CHITIN[1], 0.5)
        base.blend(cx + 1, y0 + j, CHITIN[1], 0.5)
        glow.set(cx, y0 + j, (*CYAN[4][:3], 235 - int(t * 90)))
    # Chevrons either side of the spine.
    for j in range(1, fh - 1, 3):
        for k in range(1, min(4, fw // 2 - 1)):
            base.blend(cx - 1 - k, y0 + j + k // 2, CYAN[1], 0.35)
            base.blend(cx + 1 + k, y0 + j + k // 2, CYAN[1], 0.35)


def weaver_face(base: Sheet, glow: Sheet, u, v, size, seed):
    """The clypeus. Six eyes in two rows on the front face."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 2.6, face, seed, grain_amount=0.9)

    x0, y0, fw, fh = faces["north"]
    # Two rows of three: a big pair centre-high, four smaller ones flanking.
    row_a = y0 + max(1, fh // 3 - 1)
    row_b = row_a + 2
    cx = x0 + fw // 2
    big = [(cx - 2, row_a), (cx + 1, row_a)]
    small = [(cx - 4, row_a), (cx + 3, row_a),
             (cx - 3, row_b), (cx + 2, row_b)]
    for ex, ey in big:
        for dx in (0, 1):
            base.set(ex + dx, ey, CYAN[4])
            base.set(ex + dx, ey + 1, CYAN[2])
            glow.set(ex + dx, ey, (*CYAN[5][:3], 255))
            glow.set(ex + dx, ey + 1, (*CYAN[3][:3], 210))
    for ex, ey in small:
        base.set(ex, ey, CYAN[3])
        glow.set(ex, ey, (*CYAN[4][:3], 225))
    # A dark browline above the eyes gives the face an expression.
    for i in range(fw):
        base.blend(x0 + i, row_a - 1, parse_hex("#08060E"), 0.7)


def weaver_fang(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 2.2, face, seed, grain_amount=0.7)
    for face in ("north", "west", "east", "south"):
        x0, y0, fw, fh = faces[face]
        for i in range(fw):                       # pale keratin tip
            base.set(x0 + i, y0 + fh - 1, CHALK[3])
            base.blend(x0 + i, y0 + fh - 2, CHALK[1], 0.65)
        base.blend(x0 + fw // 2, y0 + fh - 1, CYAN[4], 0.5)
    glow.set(faces["north"][0] + 1, faces["north"][1] + faces["north"][3] - 1,
             (*CYAN[4][:3], 190))


def weaver_crest(base: Sheet, glow: Sheet, u, v, size, seed):
    """Acoustic crest. The broad faces are the sail; they carry the veins."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 2.0, face, seed, grain_amount=0.8)

    for face in ("west", "east"):
        x0, y0, fw, fh = faces[face]
        for j in range(fh):
            t = 1.0 - j / max(1, fh - 1)          # brightest at the crest tip
            for i in range(fw):
                edge = (i == 0 or i == fw - 1)
                if edge:
                    base.set(x0 + i, y0 + j, mix(CHITIN[1], CHITIN[4], t))
                    continue
                if (i + j) % 2 == 0 or i == fw // 2:
                    c = mix(CYAN[1], CYAN[5], t)
                    base.set(x0 + i, y0 + j, c)
                    glow.set(x0 + i, y0 + j, (*c[:3], int(90 + 150 * t)))
                else:
                    base.set(x0 + i, y0 + j, mix(CHITIN[2], ARCANE[3], t * 0.6))
    # A bright tip cap on the narrow front/back faces.
    for face in ("north", "south"):
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.set(x0 + i, y0, CYAN[5])
            glow.set(x0 + i, y0, (*CYAN[5][:3], 255))


def weaver_limb(base: Sheet, glow: Sheet, u, v, size, seed):
    """Leg segment: banded chitin, with a lit joint at the proximal end."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 2.6, face, seed, grain_amount=0.9, scale=2.2)

    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            if i % 3 == 0:                        # annulations along the segment
                for j in range(fh):
                    base.blend(x0 + i, y0 + j, CHITIN[0], 0.5)
            elif i % 3 == 1:
                for j in range(fh):
                    base.blend(x0 + i, y0 + j, CHITIN[5], 0.35)
        for j in range(fh):                       # the joint itself
            base.set(x0, y0 + j, CYAN[2])
            glow.set(x0, y0 + j, (*CYAN[3][:3], 165))


def weaver_claw(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 1.6, face, seed, grain_amount=0.6)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(fh):                       # pale tip at the far end
            base.set(x0 + fw - 1, y0 + j, CHALK[2])
            base.blend(x0 + fw - 2, y0 + j, CHALK[0], 0.6)
            base.set(x0, y0 + j, CYAN[1])


def weaver_spinneret(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHITIN, 2.4, face, seed, grain_amount=0.9)
    x0, y0, fw, fh = faces["south"]
    for j in range(fh):
        for i in range(fw):
            if (i % 2 == 0) and (j % 2 == 0):
                base.set(x0 + i, y0 + j, CYAN[3])
                glow.set(x0 + i, y0 + j, (*CYAN[4][:3], 205))


# ---------------------------------------------------------------------------
# STRATA GOLEM
# ---------------------------------------------------------------------------
#
# Phonolite banded with amber strata - the warm band the dimension is short of -
# and gold crystal spires that carry the slam telegraph.

def golem_rock(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    profile = strata_profile(seed)
    for face, rect in faces.items():
        if face in ("up", "down"):
            fill_face(base, rect, STONE, 3.4, face, seed, grain_amount=1.3, scale=3.0)
        else:
            band_face(base, rect, STONE, AMBER, 3.2, face, seed, profile)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 11)

    # The chassis proper gets a resonance core burned into its chest.
    if w >= 24:
        x0, y0, fw, fh = faces["north"]
        cx, cy = x0 + fw // 2, y0 + fh // 2
        for j in range(-3, 4):
            for i in range(-4, 5):
                r = math.hypot(i * 0.75, j)
                if r > 3.4:
                    continue
                t = 1.0 - r / 3.4
                c = mix(AMBER[2], GOLD[5], t)
                base.set(cx + i, cy + j, c)
                glow.set(cx + i, cy + j, (*c[:3], int(70 + 185 * t)))
        for j in range(-3, 4):                    # cooled iron bezel
            base.blend(cx - 5, cy + j, STONE[0], 0.7)
            base.blend(cx + 5, cy + j, STONE[0], 0.7)
    outline_bottom(base, faces["down"], parse_hex("#08090C"))


def golem_pauldron(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 3.6, face, seed, grain_amount=1.1)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 7, density=0.04)
    for face in SIDE_FACES:                       # chalk cap, amber underline
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.set(x0 + i, y0, CHALK[2])
            base.blend(x0 + i, y0 + 1, CHALK[0], 0.6)
            base.blend(x0 + i, y0 + fh - 1, AMBER[2], 0.55)


def golem_head(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    profile = strata_profile(seed + 3)
    for face, rect in faces.items():
        if face in ("up", "down"):
            fill_face(base, rect, STONE, 3.4, face, seed, grain_amount=1.2)
        else:
            band_face(base, rect, STONE, AMBER, 3.2, face, seed, profile)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 13, density=0.05)

    x0, y0, fw, fh = faces["north"]
    eye_y = y0 + fh // 3
    for i in range(1, fw - 1):                    # a lit visor slot, not two dots
        lit = 2 <= i <= fw - 3
        c = GOLD[4] if lit else AMBER[1]
        base.set(x0 + i, eye_y, c)
        base.blend(x0 + i, eye_y + 1, AMBER[2], 0.6)
        base.blend(x0 + i, eye_y - 1, parse_hex("#07080B"), 0.8)
        if lit:
            glow.set(x0 + i, eye_y, (*GOLD[5][:3], 255))
            glow.set(x0 + i, eye_y + 1, (*GOLD[3][:3], 120))
    for i in range(fw):                           # brow overhang
        base.blend(x0 + i, eye_y - 2, STONE[5], 0.45)


def golem_jaw(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.6, face, seed, grain_amount=1.0)
    x0, y0, fw, fh = faces["north"]
    for i in range(1, fw - 1, 2):                 # vent slots venting amber heat
        for j in range(fh):
            base.set(x0 + i, y0 + j, AMBER[2] if j else AMBER[3])
            glow.set(x0 + i, y0 + j, (*AMBER[4][:3], 130 if j else 175))


def golem_spire(base: Sheet, glow: Sheet, u, v, size, seed):
    """Gold crystal. Facets rather than noise, and it glows along its length."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            # A crystal is brightest at the tip and darkest where it is rooted.
            t = 1.0 - (j / max(1, fh - 1))
            for i in range(fw):
                facet = abs((i / max(1, fw - 1)) - 0.35)
                level = 1.4 + t * 2.6 + FACE_STEP[face] * 0.5 - facet * 2.2
                level += grain(x0 + i, y0 + j, seed, scale=2.0) * 0.5
                c = pick(GOLD, level)
                base.set(x0 + i, y0 + j, c)
                if t > 0.25 or face in ("up",):
                    a = int(40 + 205 * max(0.0, t) ** 1.3)
                    glow.set(x0 + i, y0 + j, (*mix(c, GOLD[5], 0.5)[:3], a))
        if face in SIDE_FACES and fw >= 3:        # specular edge down one facet
            for j in range(fh):
                base.blend(x0 + max(1, fw // 3), y0 + j, GOLD[5], 0.55)
                base.blend(x0 + fw - 1, y0 + j, AMBER[1], 0.5)


# ---------------------------------------------------------------------------
# RESONANCE WRAITH
# ---------------------------------------------------------------------------
#
# Translucent throughout: the model asks for entityTranslucent, so alpha here is
# real. The core is hot magenta, the shell and ribbons are violet veils.

def wraith_shell(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            for i in range(fw):
                # Concentric interference rings around the face centre.
                dx = (i - (fw - 1) / 2) / max(1.0, fw / 2)
                dy = (j - (fh - 1) / 2) / max(1.0, fh / 2)
                r = math.hypot(dx, dy)
                ring = 0.5 + 0.5 * math.sin(r * 9.0 - 1.2)
                level = 1.1 + ring * 2.6 + FACE_STEP[face] * 0.35
                level += grain(x0 + i, y0 + j, seed, scale=2.4) * 0.6
                c = pick(ARCANE, level)
                alpha = int(96 + 96 * ring + 26 * (1.0 - min(1.0, r)))
                base.set(x0 + i, y0 + j, (*c[:3], min(235, alpha)))
        for i in range(fw):                       # a firmer rim on every face
            base.set(x0 + i, y0, (*ARCANE[4][:3], 225))
            base.set(x0 + i, y0 + fh - 1, (*ARCANE[1][:3], 215))


def wraith_core(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            for i in range(fw):
                dx = (i - (fw - 1) / 2) / max(1.0, fw / 2)
                dy = (j - (fh - 1) / 2) / max(1.0, fh / 2)
                t = max(0.0, 1.0 - math.hypot(dx, dy) * 0.85)
                level = 1.0 + t * 4.2 + FACE_STEP[face] * 0.3
                level += grain(x0 + i, y0 + j, seed, scale=1.6) * 0.4
                c = pick(MAGENTA, level)
                base.set(x0 + i, y0 + j, c)
                glow.set(x0 + i, y0 + j, (*c[:3], int(140 + 115 * t)))


def wraith_halo(base: Sheet, glow: Sheet, u, v, size, seed):
    """The resonance disc. Alpha punches the middle out so it reads as a ring."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face in ("up", "down"):
        x0, y0, fw, fh = faces[face]
        cx, cy = (fw - 1) / 2.0, (fh - 1) / 2.0
        outer = min(cx, cy) + 0.5
        for j in range(fh):
            for i in range(fw):
                r = math.hypot(i - cx, j - cy)
                band = r / outer
                if band < 0.52 or band > 1.02:
                    base.set(x0 + i, y0 + j, (0, 0, 0, 0))
                    continue
                # Two bright rings with a dimmer gap between them.
                ripple = 0.5 + 0.5 * math.sin((band - 0.52) * 12.0)
                c = mix(ARCANE[3], MAGENTA[4], ripple)
                alpha = int(70 + 160 * ripple * (1.0 - abs(band - 0.77) * 1.6))
                if alpha <= 8:
                    base.set(x0 + i, y0 + j, (0, 0, 0, 0))
                    continue
                base.set(x0 + i, y0 + j, (*c[:3], min(230, alpha)))
                glow.set(x0 + i, y0 + j, (*MAGENTA[4][:3], min(210, alpha)))
    for face in SIDE_FACES:                       # the disc's thin edge
        x0, y0, fw, fh = faces[face]
        for j in range(fh):
            for i in range(fw):
                t = 0.5 + 0.5 * math.sin(i * 0.7)
                c = mix(ARCANE[2], MAGENTA[3], t)
                base.set(x0 + i, y0 + j, (*c[:3], int(120 + 90 * t)))
                glow.set(x0 + i, y0 + j, (*c[:3], int(60 + 120 * t)))


def wraith_ribbon(base: Sheet, glow: Sheet, u, v, size, seed):
    """Layered ribbon: a violet veil with a hot leading edge and a travelling
    lighter streak, so a flat 2px band still reads as moving sound."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            for i in range(fw):
                across = i / max(1, fw - 1)
                along = j / max(1, fh - 1)
                wave = 0.5 + 0.5 * math.sin(across * math.pi * 2.4 + seed * 0.7 + along * 2.0)
                level = 0.9 + wave * 2.9 + FACE_STEP[face] * 0.4
                level += grain(x0 + i, y0 + j, seed, scale=2.0) * 0.5
                c = pick(ARCANE, level)
                alpha = int(110 + 105 * wave)
                if face in ("up", "down"):
                    alpha = min(255, alpha + 30)
                base.set(x0 + i, y0 + j, (*c[:3], alpha))
        # Hot magenta on the outer (leading) edge of the band.
        for j in range(fh):
            base.set(x0 + fw - 1, y0 + j, (*MAGENTA[3][:3], 235))
            glow.set(x0 + fw - 1, y0 + j, (*MAGENTA[4][:3], 235))
            base.blend(x0 + fw - 2, y0 + j, MAGENTA[1], 0.6)
            glow.set(x0 + fw - 2, y0 + j, (*MAGENTA[2][:3], 120))


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

OUTLINE = parse_hex("#07060B")

# One indexed palette per creature, sized to the vanilla band. Alpha levels are
# separate: opaque creatures get one, the wraith gets five because it renders
# through RenderTypes.entityTranslucent and its veils are the whole point.
PALETTES: dict[str, tuple[list[RGBA], tuple[int, ...]]] = {
    "echo_weaver": (
        CHITIN + CHITIN_PALE[1::2] + CYAN + [CHALK[2], CHALK[4], ARCANE[3], OUTLINE],
        (255,),
    ),
    "strata_golem": (
        STONE + AMBER + GOLD[2:] + [CHALK[1], CHALK[3], OUTLINE],
        (255,),
    ),
    "resonance_wraith": (
        ARCANE + MAGENTA,
        (120, 165, 205, 235, 255),
    ),
}

# Glow sheets are drawn in the same palette but need a fine alpha ladder: an
# emissive layer's whole job is to fall off, exactly as the warden's
# bioluminescent sheet does at alpha 50-110.
GLOW_ALPHAS = (60, 90, 120, 150, 180, 210, 235, 255)


PAINTERS = {
    "echo_weaver": {
        "carapace": weaver_carapace,
        "plate": weaver_plate,
        "face": weaver_face,
        "fang": weaver_fang,
        "crest": weaver_crest,
        "limb": weaver_limb,
        "claw": weaver_claw,
        "spinneret": weaver_spinneret,
    },
    "strata_golem": {
        "rock": golem_rock,
        "pauldron": golem_pauldron,
        "head": golem_head,
        "jaw": golem_jaw,
        "spire": golem_spire,
    },
    "resonance_wraith": {
        "shell": wraith_shell,
        "core": wraith_core,
        "halo": wraith_halo,
        "ribbon": wraith_ribbon,
    },
}


def paint(name: str, model: Model) -> tuple[Image.Image, Image.Image]:
    palette, alphas = PALETTES[name]
    base = Sheet(model.tex_w, palette, alphas)
    glow = Sheet(model.tex_w, palette, GLOW_ALPHAS)
    painters = PAINTERS[name]
    for u, v, size, group in model.regions():
        painter = painters.get(group)
        if painter is None:
            raise KeyError(f"{name}: no painter for material group {group!r}")
        seed = (u * 31 + v * 17 + size[0] * 7 + size[1] * 5 + size[2] * 3) & 0xFFFF
        painter(base, glow, u, v, size, seed)
    return base.img, glow.img


# ---------------------------------------------------------------------------
# preview: flat sheets
# ---------------------------------------------------------------------------

def label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str) -> None:
    draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 220))
    draw.text((x, y), text, fill=(226, 232, 240, 255))


def sheet_contact(images: list[tuple[str, Image.Image]], zoom: int) -> Image.Image:
    pad, top = 12, 18
    cells = [(n, im.resize((im.width * zoom, im.height * zoom), Image.NEAREST))
             for n, im in images]
    width = sum(c.width + pad for _, c in cells) + pad
    height = max(c.height for _, c in cells) + top + pad * 2
    out = Image.new("RGBA", (width, height), (18, 19, 24, 255))
    draw = ImageDraw.Draw(out)
    x = pad
    for name, cell in cells:
        # A mid-grey checker behind, so transparent areas are obvious.
        for j in range(0, cell.height, 16):
            for i in range(0, cell.width, 16):
                shadecol = (52, 54, 62, 255) if ((i + j) // 16) % 2 else (38, 40, 47, 255)
                out.paste(shadecol, (x + i, top + pad + j,
                                     min(x + i + 16, x + cell.width),
                                     min(top + pad + j + 16, top + pad + cell.height)))
        out.alpha_composite(cell, (x, top + pad))
        label(draw, x, top - 12, name)
        x += cell.width + pad
    return out


# ---------------------------------------------------------------------------
# preview: textured isometric render
# ---------------------------------------------------------------------------
#
# The flat sheet tells you the paint is there; only a render tells you whether
# the animal reads. This is a small painter's-algorithm rasteriser: bone
# hierarchy, pivots, rotations, real texture sampling per pixel.

# Preview lighting is computed from the rotated face normal rather than from the
# face's name, so turning the model round does not leave the lit side facing
# away from the camera.
_LIGHT_DIR = (-0.42, 0.84, -0.34)

FACE_NORMALS = {
    "up": (0.0, 1.0, 0.0), "down": (0.0, -1.0, 0.0),
    "north": (0.0, 0.0, -1.0), "south": (0.0, 0.0, 1.0),
    "west": (-1.0, 0.0, 0.0), "east": (1.0, 0.0, 0.0),
}


def _face_light(normal) -> float:
    d = sum(normal[i] * _LIGHT_DIR[i] for i in range(3))
    return 0.44 + 0.56 * max(0.0, d)


def _rot(p, degrees):
    x, y, z = p
    rx, ry, rz = (math.radians(d) for d in degrees)
    c, s = math.cos(rx), math.sin(rx)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ry), math.sin(ry)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(rz), math.sin(rz)
    x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def _world(point, bone, bones):
    cur = bone
    while cur is not None:
        rot = cur.get("rotation")
        if rot and any(abs(r) > 1e-6 for r in rot):
            px, py, pz = cur["pivot"]
            m = _rot((point[0] - px, point[1] - py, point[2] - pz), rot)
            point = (m[0] + px, m[1] + py, m[2] + pz)
        cur = bones.get(cur.get("parent"))
    return point


def _world_dir(direction, bone, bones):
    cur = bone
    while cur is not None:
        rot = cur.get("rotation")
        if rot and any(abs(r) > 1e-6 for r in rot):
            direction = _rot(direction, rot)
        cur = bones.get(cur.get("parent"))
    return direction


def _corners(origin, size):
    x, y, z = origin
    w, h, d = size
    return {
        "up":    ((x, y + h, z), (x + w, y + h, z), (x + w, y + h, z + d), (x, y + h, z + d)),
        "down":  ((x, y, z + d), (x + w, y, z + d), (x + w, y, z), (x, y, z)),
        "north": ((x, y + h, z), (x + w, y + h, z), (x + w, y, z), (x, y, z)),
        "south": ((x + w, y + h, z + d), (x, y + h, z + d), (x, y, z + d), (x + w, y, z + d)),
        "west":  ((x, y + h, z + d), (x, y + h, z), (x, y, z), (x, y, z + d)),
        "east":  ((x + w, y + h, z), (x + w, y + h, z + d), (x + w, y, z + d), (x + w, y, z)),
    }


def render_model(model: Model, tex: Image.Image, canvas: int = 340,
                 yaw: float = 0.0) -> Image.Image:
    """Isometric render, `yaw` degrees around the creature's own axis.

    Front is -Z, so yaw=0 looks at the creature's front-right quarter and
    yaw=180 at its back-left. Three views catch the failure the single view
    hides: art that only exists on the face you happened to look at.
    """
    data = model.to_json(0, 0, (0, 0, 0))["minecraft:geometry"][0]
    bones = {b["name"]: b for b in data["bones"]}

    quads = []
    for bone in data["bones"]:
        for cube in bone.get("cubes", []) or []:
            faces = _corners(cube["origin"], cube["size"])
            rects = box_faces(int(cube["uv"][0]), int(cube["uv"][1]), *[int(s) for s in cube["size"]])
            for face, corners in faces.items():
                world = [_world(c, bone, bones) for c in corners]
                # Directions rotate the same way points do, minus the pivot.
                normal = _world_dir(FACE_NORMALS[face], bone, bones)
                quads.append((normal, world, rects[face]))

    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def spin(p):
        x, y, z = p
        return (x * cy + z * sy, y, -x * sy + z * cy)

    quads = [(spin(n), [spin(p) for p in w], r) for n, w, r in quads]

    def project(p):
        x, y, z = p
        return ((x - z) * math.cos(math.radians(30)),
                (x + z) * math.sin(math.radians(30)) - y)

    pts = [project(p) for _, w, _ in quads for p in w]
    minx = min(p[0] for p in pts)
    maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts)
    maxy = max(p[1] for p in pts)
    scale = min((canvas - 24) / max(1e-3, maxx - minx), (canvas - 40) / max(1e-3, maxy - miny))
    ox = (canvas - (maxx - minx) * scale) / 2 - minx * scale
    oy = (canvas - (maxy - miny) * scale) / 2 - miny * scale

    img = Image.new("RGBA", (canvas, canvas), (20, 21, 27, 255))
    px = img.load()
    tpx = tex.load()

    quads.sort(key=lambda q: sum(p[0] + p[1] + p[2] for p in q[1]))
    for normal, world, rect in quads:
        s = [(project(p)[0] * scale + ox, project(p)[1] * scale + oy) for p in world]
        p0, p1, _, p3 = s
        ex = (p1[0] - p0[0], p1[1] - p0[1])
        ey = (p3[0] - p0[0], p3[1] - p0[1])
        det = ex[0] * ey[1] - ex[1] * ey[0]
        if abs(det) < 1e-6:
            continue
        rx, ry, rw, rh = rect
        light = _face_light(normal)
        xs = [p[0] for p in s]
        ys = [p[1] for p in s]
        for sy in range(max(0, int(min(ys))), min(canvas, int(max(ys)) + 1)):
            for sx in range(max(0, int(min(xs))), min(canvas, int(max(xs)) + 1)):
                dx, dy = sx + 0.5 - p0[0], sy + 0.5 - p0[1]
                a = (dx * ey[1] - dy * ey[0]) / det
                b = (ex[0] * dy - ex[1] * dx) / det
                if not (0.0 <= a < 1.0 and 0.0 <= b < 1.0):
                    continue
                tx = rx + min(rw - 1, int(a * rw))
                ty = ry + min(rh - 1, int(b * rh))
                r, g, bl, al = tpx[tx, ty]
                if al == 0:
                    continue
                dst = px[sx, sy]
                src = (int(r * light), int(g * light), int(bl * light))
                if al >= 250:
                    px[sx, sy] = (*src, 255)
                else:
                    t = al / 255.0
                    px[sx, sy] = (int(dst[0] + (src[0] - dst[0]) * t),
                                  int(dst[1] + (src[1] - dst[1]) * t),
                                  int(dst[2] + (src[2] - dst[2]) * t), 255)
    return img


# ---------------------------------------------------------------------------

def main() -> int:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    flat: list[tuple[str, Image.Image]] = []
    renders: list[tuple[str, Image.Image]] = []

    for name, (builder, _, _, _) in BUILDERS.items():
        model = builder()
        base_img, glow_img = paint(name, model)

        base_path = TEX_DIR / f"{name}.png"
        glow_path = TEX_DIR / f"{name}_glow.png"
        base_img.save(base_path, "PNG", optimize=True)
        glow_img.save(glow_path, "PNG", optimize=True)

        opaque = [c for c in base_img.getdata() if c[3] > 0]
        hues = len({c[:3] for c in opaque})
        levels = len({c[3] for c in opaque})
        lit = len([c for c in glow_img.getdata() if c[3] > 0])
        print(f"{name}.png {base_img.size[0]}x{base_img.size[1]}: "
              f"{hues} colours over {levels} alpha level(s), "
              f"{len(opaque)} painted texels, glow sheet lights {lit}")
        if not 10 <= hues <= 48:
            print(f"  WARNING: {hues} colours is outside the measured vanilla "
                  f"band (spider 13, warden 18, creaking 17, iron golem 46)")

        flat.append((name, base_img))
        flat.append((f"{name}_glow", glow_img))
        for yaw, view in ((0, "front"), (110, "side"), (200, "back")):
            renders.append((f"{name} / {view}", render_model(model, base_img, yaw=yaw)))

    contact = sheet_contact(flat, zoom=3)
    contact.save(PREVIEW_DIR / "creatures_sheets.png")

    pad, cols = 10, 3
    cell_w, cell_h = renders[0][1].width, renders[0][1].height
    rows = (len(renders) + cols - 1) // cols
    board = Image.new("RGBA",
                      (cols * (cell_w + pad) + pad, rows * (cell_h + 24 + pad) + pad),
                      (18, 19, 24, 255))
    draw = ImageDraw.Draw(board)
    for i, (name, im) in enumerate(renders):
        cx = pad + (i % cols) * (cell_w + pad)
        cyy = pad + (i // cols) * (cell_h + 24 + pad)
        board.alpha_composite(im, (cx, cyy + 18))
        label(draw, cx, cyy + 2, name)
    board.save(PREVIEW_DIR / "creatures_render.png")

    print(f"preview: {PREVIEW_DIR / 'creatures_sheets.png'}")
    print(f"preview: {PREVIEW_DIR / 'creatures_render.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

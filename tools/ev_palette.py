"""
The Echoing Void - shared palette, lighting and periodic-noise foundation.

Every texture in this mod is drawn through this module so that the four
Gauntlet texture rules hold *by construction* rather than by accident:

  1. exact 16x16 output
  2. directional top-left key lighting
  3. seamless (0,15) edge wrapping on full blocks - all noise here is periodic
     with period 16, so column 0 tiles against column 15 by definition
  4. 4-6 indexed colors per palette, no single-color fills

Nothing in this module imports Minecraft or Forge; it is pure Pillow + math so
it can run headless in the asset gate.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from PIL import Image

# --------------------------------------------------------------------------
# Palette definitions (from the brief)
# --------------------------------------------------------------------------

PALETTES: dict[str, list[str]] = {
    "resonant_bismuth": ["#00E5FF", "#FF007F", "#FFD700", "#2B2D42"],
    "phonolite":        ["#1C1D21", "#3B4252", "#4C566A"],
    "void_glass":       ["#0F0F1480", "#5E81ACCC"],
    "null_iron":        ["#08080A", "#1A1A24"],
}

RGBA = tuple[int, int, int, int]

MIN_COLORS = 4
MAX_COLORS = 6
SIZE = 16


# --------------------------------------------------------------------------
# Colour helpers
# --------------------------------------------------------------------------

def parse_hex(value: str) -> RGBA:
    """#RRGGBB or #RRGGBBAA -> (r, g, b, a)."""
    s = value.lstrip("#")
    if len(s) == 6:
        r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
        return (r, g, b, 255)
    if len(s) == 8:
        r, g, b, a = (int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
        return (r, g, b, a)
    raise ValueError(f"bad hex colour: {value!r}")


def to_hex(c: RGBA) -> str:
    return "#%02X%02X%02X%02X" % c


def luminance(c: RGBA) -> float:
    """Rec. 709 relative luminance, 0..255 scale."""
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _srgb_to_linear(u: float) -> float:
    u /= 255.0
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(u: float) -> float:
    v = 12.92 * u if u <= 0.0031308 else 1.055 * (u ** (1 / 2.4)) - 0.055
    return max(0, min(255, round(v * 255.0)))


def mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    """Perceptually sane blend: interpolate in linear light, not gamma space."""
    t = max(0.0, min(1.0, t))
    out = []
    for i in range(3):
        la, lb = _srgb_to_linear(a[i]), _srgb_to_linear(b[i])
        out.append(_linear_to_srgb(la + (lb - la) * t))
    out.append(round(a[3] + (b[3] - a[3]) * t))
    return (out[0], out[1], out[2], out[3])


def shift(c: RGBA, amount: float) -> RGBA:
    """Lighten (amount>0) or darken (amount<0) while keeping alpha and hue."""
    if amount >= 0:
        return mix(c, (255, 255, 255, c[3]), amount)
    return mix(c, (0, 0, 0, c[3]), -amount)


# --------------------------------------------------------------------------
# Ramp: turn a brief palette into an explicit indexed ramp of 4-6 colours
# --------------------------------------------------------------------------

class Ramp:
    """An explicit, ordered list of 4-6 colours, dark -> light.

    All drawing goes through integer indices into this ramp, which is what
    makes the "4-6 indexed colors, no arbitrary blending" rule structural.
    """

    def __init__(self, name: str, colors: Sequence[RGBA]):
        if not (MIN_COLORS <= len(colors) <= MAX_COLORS):
            raise ValueError(
                f"ramp {name!r} has {len(colors)} colours, must be {MIN_COLORS}-{MAX_COLORS}"
            )
        self.name = name
        self.colors: list[RGBA] = list(colors)

    def __len__(self) -> int:
        return len(self.colors)

    def __getitem__(self, i: int) -> RGBA:
        return self.colors[max(0, min(len(self.colors) - 1, int(i)))]

    @property
    def dark(self) -> int:
        return 0

    @property
    def light(self) -> int:
        return len(self.colors) - 1

    @property
    def mid(self) -> int:
        return len(self.colors) // 2

    def clamp(self, i: int) -> int:
        return max(0, min(len(self.colors) - 1, int(i)))


def build_ramp(palette_name: str, steps: int = 5, accent: str | None = None) -> Ramp:
    """Build an indexed ramp from a named brief palette.

    The brief's own colours are used as anchors, sorted dark->light and
    interpolated in linear light to reach exactly `steps` entries. When an
    `accent` palette is supplied its most saturated colour replaces the
    brightest ramp entry, which is how ore specks and glyph inlays stay
    on-palette without introducing a 7th colour.
    """
    if not (MIN_COLORS <= steps <= MAX_COLORS):
        raise ValueError(f"steps must be {MIN_COLORS}-{MAX_COLORS}, got {steps}")

    anchors = [parse_hex(h) for h in PALETTES[palette_name]]
    anchors.sort(key=luminance)

    # Widen a too-narrow anchor set so a full ramp has somewhere to go.
    if len(anchors) < 3:
        darkest, lightest = anchors[0], anchors[-1]
        anchors = [shift(darkest, -0.35), darkest, lightest, shift(lightest, 0.45)]
        anchors.sort(key=luminance)

    colors: list[RGBA] = []
    for i in range(steps):
        t = i / (steps - 1)
        pos = t * (len(anchors) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(anchors) - 1)
        colors.append(mix(anchors[lo], anchors[hi], pos - lo))

    if accent:
        acc = max((parse_hex(h) for h in PALETTES[accent]), key=_saturation)
        colors[-1] = acc

    # Guarantee distinctness: identical entries would collapse the index count.
    colors = _force_distinct(colors)
    return Ramp(palette_name if not accent else f"{palette_name}+{accent}", colors)


def _saturation(c: RGBA) -> float:
    mx, mn = max(c[:3]), min(c[:3])
    return 0.0 if mx == 0 else (mx - mn) / mx


def _force_distinct(colors: list[RGBA]) -> list[RGBA]:
    seen: set[RGBA] = set()
    out: list[RGBA] = []
    for c in colors:
        nudge = 0
        cur = c
        while cur in seen:
            nudge += 1
            cur = shift(c, 0.06 * nudge)
            if nudge > 12:
                break
        seen.add(cur)
        out.append(cur)
    return out


# --------------------------------------------------------------------------
# Deterministic periodic noise (period == 16, so it wraps seamlessly)
# --------------------------------------------------------------------------

def _hash2(x: int, y: int, seed: int) -> float:
    """Deterministic hash -> [0,1). Integer-only so builds are reproducible."""
    h = (x * 374761393) ^ (y * 668265263) ^ (seed * 2246822519)
    h &= 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177
    h &= 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


def value_noise(x: float, y: float, period: int, seed: int) -> float:
    """Smooth value noise on a lattice that repeats every `period` cells.

    Because lattice lookups are taken modulo `period`, sampling x in [0,16)
    produces a field where x=0 and x=16 are the same point - the texture tiles
    with no visible seam. This is the mechanism behind rule 3.
    """
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    # quintic smoothstep - C2 continuous, avoids the blocky look of linear lerp
    sx = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    sy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)

    def corner(ix: int, iy: int) -> float:
        return _hash2(ix % period, iy % period, seed)

    n00 = corner(x0, y0)
    n10 = corner(x0 + 1, y0)
    n01 = corner(x0, y0 + 1)
    n11 = corner(x0 + 1, y0 + 1)
    a = n00 + (n10 - n00) * sx
    b = n01 + (n11 - n01) * sx
    return a + (b - a) * sy


def fbm(x: float, y: float, seed: int, octaves: int = 3, period: int = SIZE) -> float:
    """Fractal sum of periodic value noise, normalised to [0,1].

    Every octave doubles the lattice frequency *and* the period, so all
    octaves stay commensurate with a 16px tile and the wrap survives.
    """
    total = 0.0
    amplitude = 1.0
    norm = 0.0
    freq = 1
    for o in range(octaves):
        total += value_noise(x * freq / SIZE * period, y * freq / SIZE * period,
                             period * freq, seed + o * 7919) * amplitude
        norm += amplitude
        amplitude *= 0.5
        freq *= 2
    return total / norm


# --------------------------------------------------------------------------
# Lighting
# --------------------------------------------------------------------------

# Key light travels from the top-left corner; this is the unit vector toward it.
KEY_LIGHT = (-0.7071, -0.7071)


def key_light_factor(x: int, y: int, size: int = SIZE) -> float:
    """Directional top-left key lighting term in [-1, 1].

    +1 = fully lit (top-left), -1 = fully shadowed (bottom-right). Used to bias
    the ramp index so every surface reads as lit from one consistent direction.
    """
    nx = (x + 0.5) / size * 2 - 1
    ny = (y + 0.5) / size * 2 - 1
    return -(nx * KEY_LIGHT[0] + ny * KEY_LIGHT[1]) * -1


def bevel_factor(x: int, y: int, size: int = SIZE) -> float:
    """Edge bevel: bright on the top/left rim, dark on the bottom/right rim."""
    top_left = min(x, y)
    bottom_right = min(size - 1 - x, size - 1 - y)
    if top_left == 0:
        return 1.0
    if bottom_right == 0:
        return -1.0
    if top_left == 1:
        return 0.5
    if bottom_right == 1:
        return -0.5
    return 0.0


# --------------------------------------------------------------------------
# Ordered dithering - adds structure without adding colours
# --------------------------------------------------------------------------

BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def bayer(x: int, y: int) -> float:
    """Ordered dither threshold in [0,1)."""
    return BAYER4[y % 4][x % 4] / 16.0


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

class Canvas:
    """A 16x16 indexed drawing surface bound to one Ramp."""

    def __init__(self, ramp: Ramp, size: int = SIZE, transparent: bool = False):
        self.ramp = ramp
        self.size = size
        self.transparent = transparent
        # -1 means "not painted" => stays transparent on export
        self.idx: list[list[int]] = [[-1] * size for _ in range(size)]

    def set(self, x: int, y: int, index: int) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.idx[y][x] = self.ramp.clamp(index)

    def get(self, x: int, y: int) -> int:
        return self.idx[y % self.size][x % self.size]

    def clear_px(self, x: int, y: int) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.idx[y][x] = -1

    def fill(self, index: int) -> None:
        for y in range(self.size):
            for x in range(self.size):
                self.idx[y][x] = self.ramp.clamp(index)

    def rect(self, x0: int, y0: int, x1: int, y1: int, index: int) -> None:
        for y in range(max(0, y0), min(self.size, y1 + 1)):
            for x in range(max(0, x0), min(self.size, x1 + 1)):
                self.idx[y][x] = self.ramp.clamp(index)

    def noise_field(self, seed: int, octaves: int = 3, spread: float = 1.0,
                    base: float | None = None) -> None:
        """Fill the whole canvas with periodic fbm mapped onto the ramp.

        This is the standard body of a full-cube block texture: it is never a
        flat fill, and it wraps at the 0/15 seam.
        """
        mid = self.ramp.mid if base is None else base
        top = len(self.ramp) - 1
        for y in range(self.size):
            for x in range(self.size):
                n = fbm(x, y, seed, octaves=octaves)
                lit = key_light_factor(x, y, self.size) * 0.5
                v = (n - 0.5) * 2.0 * spread + lit
                # dither by half a step so banding breaks up without new colours
                v += (bayer(x, y) - 0.5) * 0.35
                self.idx[y][x] = self.ramp.clamp(round(mid + v * (top / 2.0)))

    def speckle(self, seed: int, count: int, index: int, avoid_edges: bool = False) -> list[tuple[int, int]]:
        """Scatter deterministic single-pixel accents; returns their positions."""
        placed: list[tuple[int, int]] = []
        attempts = 0
        while len(placed) < count and attempts < count * 40:
            attempts += 1
            hx = _hash2(attempts, seed, 0x5EED)
            hy = _hash2(seed, attempts, 0xBEEF)
            x = int(hx * self.size)
            y = int(hy * self.size)
            if avoid_edges and (x == 0 or y == 0 or x == self.size - 1 or y == self.size - 1):
                continue
            if (x, y) in placed:
                continue
            placed.append((x, y))
            self.set(x, y, index)
        return placed

    def to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        px = img.load()
        for y in range(self.size):
            for x in range(self.size):
                i = self.idx[y][x]
                px[x, y] = (0, 0, 0, 0) if i < 0 else self.ramp[i]
        return img

    def save(self, path) -> Image.Image:
        img = self.to_image()
        img.save(path, "PNG", optimize=True)
        return img


def unique_colors(img: Image.Image) -> set[RGBA]:
    """Distinct fully-or-partially opaque colours in an image."""
    return {c for c in img.convert("RGBA").getdata() if c[3] > 0}

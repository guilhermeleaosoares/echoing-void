"""
The Echoing Void - Hushwater: animated fluid sprites, models and data.

Hushwater is the dimension's liquid: cyan, heavier and slower than water, and it
mends whatever swims in it. This stage owns every file that is not Java:

    textures/block/hushwater_still.png (+ .mcmeta)   16 x 16*FRAMES, looping
    textures/block/hushwater_flow.png  (+ .mcmeta)   32 x 32*FRAMES, scrolling
    textures/block/hushwater_overlay.png             16x16, drawn against glass
    textures/item/hushwater_bucket.png               the icon
    blockstates/hushwater.json, models/block/hushwater.json
    items/hushwater_bucket.json, models/item/hushwater_bucket.json
    data/echoing_void/tags/fluid/hushwater.json
    lang/en_us.json                                   additively

WHY THE SPRITES ARE BUILT THE WAY THEY ARE
------------------------------------------
tools/verify_textures.py judges an animation strip as ONE image: 5-16 distinct
colours across every frame put together, no colour over 85% of the sheet, and
every colour on the blend-and-shade continuum of docs/spec/art_direction.json.
A hand-shaded liquid would blow the colour budget on frame three. So both
strips are drawn by quantising a scalar field onto a fixed six-entry ramp built
with the same col(a, b, k, s) lattice the item generator uses - the budget then
holds by construction, whatever the animation does.

The motion is periodic in the frame index, not merely random per frame: the
still field advances two travelling waves through exactly one cycle over FRAMES,
and the flow field scrolls the sheet by exactly its own height. Frame FRAMES is
therefore frame 0, so neither strip pops when the animation wraps.

Run:  python tools/gen_fluid_assets.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from gen_item_textures import (  # noqa: E402
    Material, Sprite, col, spans, stroke,
)

NS = "echoing_void"
ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS
DATA = ROOT / "src" / "main" / "resources" / "data" / NS
TEX_BLOCK = ASSETS / "textures" / "block"
TEX_ITEM = ASSETS / "textures" / "item"

STILL_SIZE = 16
FLOW_SIZE = 32
FRAMES = 16

written: list[str] = []


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ---------------------------------------------------------------------------
# the ramp
#
# Six entries, dark to light, drawn entirely from the bismuth family so the
# fluid reads as the same cyan as the ore and the clusters. Every entry is
# mix(anchor_a, anchor_b, k/16) shaded by s/16, which is precisely the set
# verify_textures.py authorises.
# ---------------------------------------------------------------------------

RAMP = [
    col("bis_deep", "void_shadow", 7),      # 0 - the trough, nearly black teal
    col("bis_deep", "void_shadow", 3),      # 1
    col("bis_deep", "bis_mid", 4),          # 2
    col("bis_deep", "bis_mid", 10),         # 3
    col("bis_mid", "bis_bright", 7),        # 4
    col("bis_bright", "chalk_light", 5),    # 5 - the crest highlight
]


def render(field: list[float], w: int, h: int,
           shares: list[float]) -> Image.Image:
    """Histogram-matched quantisation of a scalar field onto RAMP.

    A fixed 0..1 -> index mapping is what a first attempt does, and it does not
    survive contact with fbm: the noise clusters around its mean, so the two
    ends of the ramp are simply never reached and the strip comes out with four
    colours instead of six - which the texture gate rejects outright as flat
    programmer art.

    Slicing the SORTED field by target shares instead dials the colour
    distribution in directly. Every ramp entry is guaranteed to appear, and the
    dominant-colour share is whatever the largest number in `shares` is, so the
    85% ceiling holds by construction rather than by luck.

    The whole strip is quantised against ONE histogram, not one per frame. That
    matters: per-frame histograms would re-level every frame and the animation
    would visibly pulse in brightness.
    """
    order = sorted(field)
    n = len(order)
    cuts: list[float] = []
    running = 0.0
    for share in shares[:-1]:
        running += share
        cuts.append(order[min(n - 1, int(running * n))])

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for i, value in enumerate(field):
        idx = 0
        while idx < len(cuts) and value > cuts[idx]:
            idx += 1
        px[i % w, i // w] = RAMP[idx]
    return img


# ---------------------------------------------------------------------------
# periodic value noise with an explicit period on each axis
#
# ev_palette.fbm hard-codes a period of 16, which is right for a 16x16 block
# face and wrong for a 32-wide flow sheet. This is the same construction with
# the period passed in, so the flow sheet wraps on 32 and the still on 16.
# ---------------------------------------------------------------------------

def _hash(x: int, y: int, seed: int) -> float:
    h = (x * 374761393) ^ (y * 668265263) ^ (seed * 2246822519)
    h &= 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177
    h &= 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


def _smooth(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def pnoise(x: float, y: float, px: int, py: int, seed: int) -> float:
    x0, y0 = math.floor(x), math.floor(y)
    sx, sy = _smooth(x - x0), _smooth(y - y0)

    def corner(ix: int, iy: int) -> float:
        return _hash(ix % px, iy % py, seed)

    a = corner(x0, y0) + (corner(x0 + 1, y0) - corner(x0, y0)) * sx
    b = corner(x0, y0 + 1) + (corner(x0 + 1, y0 + 1) - corner(x0, y0 + 1)) * sx
    return a + (b - a) * sy


def pfbm(x: float, y: float, px: int, py: int, seed: int, octaves: int = 3) -> float:
    total, amp, norm, freq = 0.0, 1.0, 0.0, 1
    for o in range(octaves):
        total += pnoise(x * freq, y * freq, px * freq, py * freq, seed + o * 7919) * amp
        norm += amp
        amp *= 0.5
        freq *= 2
    return total / norm


# ---------------------------------------------------------------------------
# still: a settled pool
# ---------------------------------------------------------------------------

def still_strip() -> Image.Image:
    """Two travelling swells crossing a fixed mottle.

    The swells run at different angles and wavelengths, so the interference
    pattern never repeats within a frame while the whole field still returns to
    its start after FRAMES. That is what a settled pool looks like: no
    direction, but never actually still.
    """
    size = STILL_SIZE
    field: list[float] = []
    for f in range(FRAMES):
        phase = 2.0 * math.pi * f / FRAMES
        for y in range(size):
            for x in range(size):
                # Both wave arguments are whole multiples of 2*pi/size in x and
                # y, so the sprite tiles against its own neighbours as well as
                # looping in time.
                w1 = math.sin(2.0 * math.pi * (x + y * 2) / size + phase)
                w2 = math.sin(2.0 * math.pi * (x * 2 - y) / size - phase * 2.0)
                mottle = pfbm(x / 4.0, y / 4.0, 4, 4, 20260819) - 0.5
                field.append(0.20 * w1 + 0.13 * w2 + 0.34 * mottle)
    return render(field, size, size * FRAMES,
                  [0.09, 0.17, 0.25, 0.25, 0.16, 0.08])


# ---------------------------------------------------------------------------
# flow: a face the fluid is running down
# ---------------------------------------------------------------------------

def flow_strip() -> Image.Image:
    """A field scrolled down by exactly one sheet height over FRAMES.

    Vanilla's flow sprite is 32 wide against a 16-wide still one because the
    renderer samples half of it per block face; matching that is what stops a
    waterfall reading as a repeating 16px stripe. The streaks are stretched
    vertically so the eye reads downward motion rather than boiling.
    """
    size = FLOW_SIZE
    field: list[float] = []
    for f in range(FRAMES):
        shift = size * f / FRAMES
        for y in range(size):
            for x in range(size):
                yy = y + shift
                # Two layers at different speeds: the slower one is the body of
                # the fall, the faster one the threads running ahead of it.
                slow = pfbm(x / 3.0, yy / 12.0, 11, 3, 771103)
                fast = pfbm(x / 1.6, yy * 1.6 / 12.0, 20, 5, 990017)
                streak = 0.5 + 0.5 * math.sin(2.0 * math.pi * (x / 8.0 + yy / size))
                field.append(0.52 * slow + 0.26 * fast + 0.16 * (streak - 0.5))
    # Weighted darker than the still sheet: a falling body is mostly shadow with
    # bright threads through it, not an evenly lit surface.
    return render(field, size, size * FRAMES,
                  [0.12, 0.21, 0.27, 0.21, 0.13, 0.06])


def overlay_tile() -> Image.Image:
    """The face drawn where hushwater meets a non-opaque block.

    Vanilla's water_overlay is a flatter, darker version of the still sprite so
    the fluid does not appear to glow through glass. Same idea: the mottle is
    kept, the swell is not, and the whole thing is pulled down the ramp.
    """
    size = STILL_SIZE
    field: list[float] = []
    for y in range(size):
        for x in range(size):
            mottle = pfbm(x / 3.0, y / 3.0, 5, 5, 4471) - 0.5
            grain = pfbm(x, y, size, size, 8821) - 0.5
            field.append(0.55 * mottle + 0.22 * grain)
    return render(field, size, size, [0.13, 0.24, 0.28, 0.20, 0.10, 0.05])


# ---------------------------------------------------------------------------
# the bucket icon
# ---------------------------------------------------------------------------

# Steel pail. Deliberately not the null-iron ramp: a bucket is a plain tool, and
# painting it in the mod's rarest metal would read as a null-iron bucket rather
# than as a bucket of something.
PAIL = Material("pail", [
    col("ph_dark", "void_black", 6),
    col("ph_dark", "ph_mid", 5),
    col("ph_mid", "ph_light", 4),
    col("ph_light", "ph_pale", 6),
    col("ph_pale", "chalk_mid", 7),
    col("chalk_mid", "chalk_light", 8),
])

FLUID = Material("hushwater", [
    col("bis_deep", "void_shadow", 7),
    col("bis_deep", "void_shadow", 2),
    col("bis_deep", "bis_mid", 6),
    col("bis_mid", "bis_bright", 4),
    col("bis_bright", "chalk_light", 6),
])


class _FixedSprite:
    """A sprite whose pixels are literal, not procedural.

    Every other sprite in this file is generated from a material and a shape,
    because that is what keeps the palette machinery honest. This one is not:
    it is Antigravity's hand-drawn hushwater bucket, PLAYER-approved after a
    dedicated design pass (docs/FIXES_round2.md item 1) and then silently
    overwritten by a later regeneration - "the hushwater textures and bucket
    item were reverted" - because it lived only as a checked-in PNG with no
    generator behind it, so the next `asset_gen.py` run rebuilt the old
    procedural version right over it.

    Encoding the exact pixel grid here closes that gap: this IS the generator
    now, so there is nothing left for a future regeneration to revert. The
    grid below was read pixel-by-pixel from that approved PNG (git show
    8b1926e:.../hushwater_bucket.png) rather than redrawn from memory, so this
    reproduces it exactly rather than approximately.
    """

    _ROWS = [
        "................",
        ".....KKKKKK.....",
        "...KKdgggmmKK...",
        "..KdADBCCDDAdK..",
        "..KABEEBCEFBAK..",
        "..KKKACBBCAKKK..",
        "..KLmKKFKKKdgK..",
        "..KLLLLmFgddgK..",
        "..KLLWLmmgddmK..",
        "..KmLWLmmgddmK..",
        "..KdLWLmmgddgK..",
        "...KLLLmmgdgK...",
        "...KmLLmggdgK...",
        "....KmLmgdgK....",
        ".....KKKKKK.....",
        "................",
    ]
    # Colours as measured off the approved PNG - not this file's usual
    # material ramps, because this sprite predates them and was approved as
    # drawn, pixel values and all.
    _PALETTE = {
        ".": (0, 0, 0, 0),
        "K": (53, 53, 53, 255),
        "m": (168, 168, 168, 255),
        "L": (216, 216, 216, 255),
        "g": (150, 150, 150, 255),
        "d": (114, 114, 114, 255),
        "A": (15, 94, 109, 255),
        "B": (50, 182, 198, 255),
        "C": (33, 150, 166, 255),
        "D": (13, 111, 128, 255),
        "E": (118, 224, 246, 255),
        "F": (47, 218, 238, 255),
        "W": (255, 255, 255, 255),
    }

    def save(self, path: Path) -> Image.Image:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for y, row in enumerate(self._ROWS):
            for x, ch in enumerate(row):
                img.putpixel((x, y), self._PALETTE[ch])
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "PNG", optimize=True)
        return img


def hushwater_bucket() -> _FixedSprite:
    """Antigravity's approved bucket design - see `_FixedSprite` for why this
    is pixel data rather than a procedural paint like every sprite above it."""
    return _FixedSprite()


# ---------------------------------------------------------------------------
# lang - additive, exactly as gen_knell_data.py does it
# ---------------------------------------------------------------------------

LANG = {
    "block.echoing_void.hushwater": "Hushwater",
    "item.echoing_void.hushwater_bucket": "Bucket of Hushwater",
    "fluid.echoing_void.hushwater": "Hushwater",
}


def merge_lang() -> int:
    path = ASSETS / "lang" / "en_us.json"
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    added = 0
    for key, value in LANG.items():
        if key not in current:
            current[key] = value
            added += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return added


def stats(img: Image.Image) -> tuple[int, float]:
    counts: dict[tuple[int, int, int], int] = {}
    for c in img.convert("RGBA").getdata():
        if c[3] > 0:
            counts[c[:3]] = counts.get(c[:3], 0) + 1
    total = sum(counts.values())
    return len(counts), (max(counts.values()) / total if total else 0.0)


def main() -> int:
    TEX_BLOCK.mkdir(parents=True, exist_ok=True)
    TEX_ITEM.mkdir(parents=True, exist_ok=True)

    sheets = [
        ("hushwater_still", still_strip(), {"animation": {"frametime": 3}}),
        ("hushwater_flow", flow_strip(), {"animation": {"frametime": 2}}),
    ]
    for name, img, meta in sheets:
        img.save(TEX_BLOCK / f"{name}.png", "PNG", optimize=True)
        (TEX_BLOCK / f"{name}.png.mcmeta").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        written.append(f"assets/{NS}/textures/block/{name}.png")

    overlay = overlay_tile()
    overlay.save(TEX_BLOCK / "hushwater_overlay.png", "PNG", optimize=True)
    written.append(f"assets/{NS}/textures/block/hushwater_overlay.png")

    bucket = hushwater_bucket().save(TEX_ITEM / "hushwater_bucket.png")
    written.append(f"assets/{NS}/textures/item/hushwater_bucket.png")

    # A liquid block has no geometry of its own - the fluid renderer draws it -
    # so the model exists only to name the particle sprite, exactly as vanilla
    # block/water.json does.
    write_json(ASSETS / "blockstates" / "hushwater.json",
               {"variants": {"": {"model": f"{NS}:block/hushwater"}}})
    write_json(ASSETS / "models" / "block" / "hushwater.json",
               {"textures": {"particle": f"{NS}:block/hushwater_still"}})

    write_json(ASSETS / "models" / "item" / "hushwater_bucket.json",
               {"parent": "minecraft:item/generated",
                "textures": {"layer0": f"{NS}:item/hushwater_bucket"}})
    write_json(ASSETS / "items" / "hushwater_bucket.json",
               {"model": {"type": "minecraft:model",
                          "model": f"{NS}:item/hushwater_bucket"}})

    # Both forms under one tag, so a predicate can ask "is this hushwater"
    # without naming the source and the flowing fluid separately.
    write_json(DATA / "tags" / "fluid" / "hushwater.json",
               {"replace": False,
                "values": [f"{NS}:hushwater", f"{NS}:flowing_hushwater"]})

    added = merge_lang()

    failures = []
    for label, img in (("still", sheets[0][1]), ("flow", sheets[1][1]),
                       ("overlay", overlay), ("bucket", bucket)):
        n, top = stats(img)
        print(f"  {label:8} {img.size[0]:>3}x{img.size[1]:<5} "
              f"{n:>2} colours  top {top:>5.1%}")
        if not (5 <= n <= 16):
            failures.append(f"{label}: {n} colours, want 5-16")
        if top > 0.85:
            failures.append(f"{label}: dominant colour covers {top:.0%}")

    print(f"hushwater: {len(written)} files, {added} new lang key(s)")
    for w in written:
        print("  " + w)
    if failures:
        print()
        print("FAILURES:")
        for f in failures:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

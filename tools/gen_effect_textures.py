"""
The Echoing Void - effects generator: portal animation, jukebox, anvil body.

Three pieces of art that do not fit the flat-cube pipeline in
gen_block_textures.py, plus the model and blockstate JSON that consumes them:

  hollow_horizon_portal   a MULTI-FRAME animated sprite. Minecraft animates a
                          texture by stacking its frames vertically in one PNG
                          and describing the timing in a sibling .png.mcmeta;
                          the precedent read for this is vanilla's
                          textures/block/nether_portal.png (16x512, 32 frames)
                          with {"animation": {}} beside it. Ours is a travelling
                          standing wave: nodes fixed across the width, crests
                          marching down the height, cyan on the positive half
                          cycle and magenta on the negative.
  null_iron_jukebox       top and side for the block that finally gives the
                          Harmonic Tuning Discs somewhere to be played.
  inversion_anvil_body    a plate texture laid out for vanilla's anvil UV map.
                          The vanilla anvil model samples ONE 16x16 texture at
                          eight different sub-rectangles - the base band lives
                          at y 12..15, the waist at y 6..11, the horn block at
                          y 0..5 - so this texture is drawn in those bands
                          rather than as a uniform tile.

Everything is deterministic: two runs produce byte-identical output.

This generator also writes the blockstates and block models for the portal, the
jukebox and the anvil. It must therefore run AFTER gen_models.py in
tools/asset_gen.py, because gen_models.py still writes an older, plainer
version of the portal and anvil models and the later writer wins.

Run:  python tools/gen_effect_textures.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from PIL import Image  # noqa: E402

from ev_palette import (  # noqa: E402
    SIZE,
    _hash2,
    fbm,
    mix,
    parse_hex,
    shift,
)

NS = "echoing_void"
ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS
OUT_BLOCK = ASSETS / "textures" / "block"
BLOCKSTATES = ASSETS / "blockstates"
BLOCK_MODELS = ASSETS / "models" / "block"
ITEM_DEFS = ASSETS / "items"

ART = json.loads((ROOT / "docs" / "spec" / "art_direction.json").read_text(encoding="utf-8"))
P = ART["palette"]

# Frames and timing for the portal. 16 frames at two ticks each is a 1.6 second
# cycle - slow enough to read as a standing wave rather than a flicker, and
# interpolation carries the crest smoothly between frames so the motion does not
# step. Vanilla's nether portal runs 32 frames at one tick with no interpolation;
# half the frames with interpolation costs half the atlas and looks smoother.
PORTAL_FRAMES = 16
PORTAL_FRAMETIME = 2

# The sheet stays partly see-through, like vanilla's portal texture whose alpha
# runs 155..255. Nodes are the thinnest part of the wave, so they are also the
# most transparent - you can see the far side of the frame through them.
PORTAL_ALPHA_MIN = 150
PORTAL_ALPHA_MAX = 255


# ==========================================================================
# Palette
# ==========================================================================

def anchor(family: str, tone: str):
    return parse_hex(P[family][tone])


def blend(a, b, sixteenths: int, shade: int = 0):
    """A colour on the authorised continuum.

    tools/verify_textures.py only accepts colours reachable as
    shift(mix(anchor_a, anchor_b, k/16), s/16) with |s| <= 10. Every colour in
    this file is built through this helper so it is inside that set by
    construction rather than by luck.
    """
    c = mix(a, b, sixteenths / 16.0)
    return shift(c, shade / 16.0) if shade else c


VOID_BLACK = anchor("void", "black")
VOID_SHADOW = anchor("void", "shadow")
PH_MID = anchor("phonolite", "mid")
CH_HIGH = anchor("chalk", "highlight")
BI_DEEP = anchor("bismuth", "deep")
BI_MID = anchor("bismuth", "mid")
BI_BRIGHT = anchor("bismuth", "bright")
GOLD = anchor("bismuth", "gold")
AR_DEEP = anchor("arcane", "deep")
AR_MID = anchor("arcane", "mid")
AR_LIGHT = anchor("arcane", "light")
AR_BRIGHT = anchor("arcane", "bright")
NI_BLACK = anchor("null_iron", "black")
NI_DARK = anchor("null_iron", "dark")
NI_MID = anchor("null_iron", "mid")

# Fourteen entries: void, then a magenta arm and a cyan arm of six each. The
# gate allows sixteen colours in a 16x16 sprite and counts RGB only, so varying
# alpha across the sheet costs nothing against that budget.
PORTAL_RAMP = [
    VOID_BLACK,                        # 0  node - the wave's zero crossing
    VOID_SHADOW,                       # 1
    blend(VOID_SHADOW, AR_DEEP, 8),    # 2  magenta arm
    AR_DEEP,                           # 3
    blend(AR_DEEP, AR_MID, 8),         # 4
    AR_MID,                            # 5
    AR_LIGHT,                          # 6
    AR_BRIGHT,                         # 7
    blend(VOID_SHADOW, BI_DEEP, 8),    # 8  cyan arm
    BI_DEEP,                           # 9
    blend(BI_DEEP, BI_MID, 8),         # 10
    BI_MID,                            # 11
    BI_BRIGHT,                         # 12
    blend(BI_BRIGHT, CH_HIGH, 6),      # 13 crest highlight
]
MAGENTA_ARM = 2
CYAN_ARM = 8
ARM_BANDS = 6

# Null-iron machinery, matching the ramp gen_block_textures.py already uses for
# the anvil so the new faces sit beside the old ones.
IRON_RAMP = [
    shift(NI_BLACK, -2 / 16.0),        # 0
    NI_BLACK,                          # 1
    blend(NI_BLACK, NI_DARK, 8),       # 2
    NI_DARK,                           # 3
    blend(NI_DARK, NI_MID, 8),         # 4
    NI_MID,                            # 5
    blend(NI_MID, PH_MID, 8),          # 6
    BI_DEEP,                           # 7
    BI_MID,                            # 8
    BI_BRIGHT,                         # 9
    GOLD,                              # 10
]
IRON_DARK, IRON_MID, IRON_LIGHT = 1, 3, 5
INLAY_DEEP, INLAY_MID, INLAY_BRIGHT, INLAY_GOLD = 7, 8, 9, 10


# ==========================================================================
# Field and quantisation - the two mechanisms behind every surface here
# ==========================================================================

def hash01(x: int, y: int, seed: int) -> float:
    return _hash2(x % SIZE, y % SIZE, seed)


def plate_field(seed: int, grain: int = 8, grit: float = 0.38,
                relief: float = 0.5) -> list[list[float]]:
    """Periodic value field with per-granule top-left key lighting.

    Identical in spirit to the field in gen_block_textures.py: smooth periodic
    fbm, per-pixel grit so the surface is not an airbrush, and a relief term
    that is the directional derivative of the smooth part. Because every lookup
    is modulo 16 the result tiles at the 0/15 seam.
    """
    smooth = [[fbm(x, y, seed, octaves=2, period=grain) for x in range(SIZE)]
              for y in range(SIZE)]
    out = [[0.0] * SIZE for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            dx = smooth[y][(x + 1) % SIZE] - smooth[y][(x - 1) % SIZE]
            dy = smooth[(y + 1) % SIZE][x] - smooth[y - 1][x]
            v = smooth[y][x]
            v += relief * (dx + dy)
            v += grit * (hash01(x, y, seed ^ 0x51ED) - 0.5)
            out[y][x] = v
    return out


def quantise(values: list[float], weights: list[float]) -> list[int]:
    """Histogram-matched quantisation: sort, then slice by cumulative share.

    Dialling the colour distribution in directly is what keeps any one tone from
    running away and covering the tile, which is the "no flat fills" rule in
    tools/verify_textures.py.
    """
    order = sorted(range(len(values)), key=lambda i: values[i])
    total = float(sum(weights))
    out = [0] * len(values)
    cursor = 0
    acc = 0.0
    n = len(values)
    for level, w in enumerate(weights):
        acc += w / total
        stop = n if level == len(weights) - 1 else round(acc * n)
        while cursor < stop:
            out[order[cursor]] = level
            cursor += 1
    return out


def to_image(idx: list[list[int]], ramp, alpha: list[list[int]] | None = None) -> Image.Image:
    h = len(idx)
    w = len(idx[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            i = idx[y][x]
            if i < 0:
                continue
            r, g, b, _ = ramp[i]
            px[x, y] = (r, g, b, 255 if alpha is None else alpha[y][x])
    return img


written: list[str] = []


def save_png(img: Image.Image, name: str) -> None:
    OUT_BLOCK.mkdir(parents=True, exist_ok=True)
    path = OUT_BLOCK / f"{name}.png"
    img.save(path, "PNG", optimize=True)
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ==========================================================================
# 1. The portal: an animated frame strip
# ==========================================================================

def portal_strip() -> Image.Image:
    """16 x (16*frames) frame strip of a travelling standing wave.

    The wave has two parts. A standing component fixes its nodes across the
    width - sin(2*pi*2x/16) is zero at four columns for every frame, so the
    sheet always shows the same vertical bands and reads as one resonating
    surface rather than as scrolling wallpaper. A travelling component moves the
    crest down the height as the phase advances. The magenta harmonic runs at a
    different frequency and in the opposite direction, so the two colours beat
    against each other instead of moving in lockstep.

    Every term is periodic over the 16px tile in x and over one full cycle in
    both y and phase, so the strip tiles against the next portal block sideways
    and up, and frame 15 runs back into frame 0 without a jump.
    """
    n = PORTAL_FRAMES
    height = SIZE * n
    signed: list[float] = []

    for f in range(n):
        phase = f / n
        for y in range(SIZE):
            for x in range(SIZE):
                u = x / SIZE
                v = y / SIZE
                # two nodes across the width, crest travelling down
                cyan = math.sin(2 * math.pi * 2 * u) * math.cos(2 * math.pi * (v - phase))
                # one broad lobe across, crest travelling up - the counter-running
                # harmonic. Keeping its spatial frequency low is what stops the two
                # colours dicing each other into confetti at the pixel scale.
                magenta = math.sin(2 * math.pi * u) * math.cos(2 * math.pi * (v + phase))
                grain = fbm(x, (y + f * 3) % SIZE, 0x9A57, octaves=2, period=SIZE) - 0.5
                signed.append(0.66 * cyan - 0.52 * magenta + 0.10 * grain)

    magnitudes = [abs(v) for v in signed]
    # Six magnitude bands per arm, plus two levels of near-node darkness. The
    # node share is the dominant tone at 26%, well inside the gate's 85% limit.
    ranks = quantise(magnitudes, [0.26, 0.12] + [0.62 / ARM_BANDS] * ARM_BANDS)

    idx = [[0] * SIZE for _ in range(height)]
    alpha = [[PORTAL_ALPHA_MIN] * SIZE for _ in range(height)]
    span = PORTAL_ALPHA_MAX - PORTAL_ALPHA_MIN
    for i, rank in enumerate(ranks):
        row, col = divmod(i, SIZE)
        if rank == 0:
            idx[row][col] = 0
        elif rank == 1:
            idx[row][col] = 1
        else:
            arm = CYAN_ARM if signed[i] >= 0.0 else MAGENTA_ARM
            idx[row][col] = arm + (rank - 2)
        # Brightness and opacity rise together: a node is thin and see-through,
        # a crest is dense and nearly solid.
        alpha[row][col] = PORTAL_ALPHA_MIN + round(span * rank / (ARM_BANDS + 1))

    return to_image(idx, PORTAL_RAMP, alpha)


def gen_portal() -> None:
    save_png(portal_strip(), "hollow_horizon_portal")

    meta = OUT_BLOCK / "hollow_horizon_portal.png.mcmeta"
    meta.write_text(json.dumps({
        "animation": {
            "frametime": PORTAL_FRAMETIME,
            "interpolate": True,
        }
    }, indent=2) + "\n", encoding="utf-8")
    written.append(str(meta.relative_to(ROOT)).replace("\\", "/"))

    # The sheet itself: a 4px pane standing in its own axis, the same geometry
    # vanilla gives a nether portal (block/nether_portal_ns.json). The only
    # change from the version gen_models.py writes is the sprite - it used to
    # borrow void_glass, which cannot animate because void_glass is a still tile
    # shared with the glass block.
    sprite = {"force_translucent": True, "sprite": f"{NS}:block/hollow_horizon_portal"}
    for suffix, frm, to, faces in (
        ("ns", [0, 0, 6], [16, 16, 10], ("north", "south")),
        ("ew", [6, 0, 0], [10, 16, 16], ("east", "west")),
    ):
        write_json(BLOCK_MODELS / f"hollow_horizon_portal_{suffix}.json", {
            "textures": {"particle": sprite, "portal": sprite},
            "elements": [{
                "from": frm,
                "to": to,
                "faces": {f: {"uv": [0, 0, 16, 16], "texture": "#portal"} for f in faces},
            }],
        })

    write_json(BLOCKSTATES / "hollow_horizon_portal.json", {
        "variants": {
            "axis=x": {"model": f"{NS}:block/hollow_horizon_portal_ns"},
            "axis=z": {"model": f"{NS}:block/hollow_horizon_portal_ew"},
        }
    })


# ==========================================================================
# 2. The null-iron jukebox
# ==========================================================================

def jukebox_side() -> Image.Image:
    """A null-iron cabinet: plated body, a bismuth inlay band, corner rivets."""
    values = plate_field(0x1B0C, grain=8, grit=0.34, relief=0.45)
    flat = [values[y][x] for y in range(SIZE) for x in range(SIZE)]
    levels = quantise(flat, [0.14, 0.30, 0.32, 0.18, 0.06])
    idx = [[levels[y * SIZE + x] + 1 for x in range(SIZE)] for y in range(SIZE)]

    # A recessed panel: dark rim inside the outer plate, so the cabinet reads as
    # built rather than as a solid lump.
    for x in range(1, SIZE - 1):
        idx[1][x] = IRON_LIGHT
        idx[SIZE - 2][x] = IRON_DARK
    for y in range(1, SIZE - 1):
        idx[y][1] = IRON_LIGHT
        idx[y][SIZE - 2] = IRON_DARK

    # The resonator seam. Two rows of bismuth with a dark shadow under them -
    # the same cyan that runs through every worked null-iron surface in the mod.
    for x in range(3, SIZE - 3):
        idx[7][x] = INLAY_DEEP
        idx[8][x] = INLAY_MID if x % 3 else INLAY_BRIGHT
        idx[9][x] = IRON_DARK

    for x, y in ((3, 3), (12, 3), (3, 12), (12, 12)):
        idx[y][x] = IRON_LIGHT
        idx[y + 1][x + 1] = IRON_DARK

    return to_image(idx, IRON_RAMP)


def jukebox_top() -> Image.Image:
    """The playing surface: a bismuth resonator ring around a disc slot."""
    values = plate_field(0x1B0D, grain=8, grit=0.30, relief=0.40)
    flat = [values[y][x] for y in range(SIZE) for x in range(SIZE)]
    levels = quantise(flat, [0.16, 0.32, 0.30, 0.16, 0.06])
    idx = [[levels[y * SIZE + x] + 1 for x in range(SIZE)] for y in range(SIZE)]

    for x in range(1, SIZE - 1):
        idx[1][x] = IRON_LIGHT
        idx[SIZE - 2][x] = IRON_DARK
    for y in range(1, SIZE - 1):
        idx[y][1] = IRON_LIGHT
        idx[y][SIZE - 2] = IRON_DARK

    # Concentric ring: bright on its top-left arc, deep on the bottom-right, so
    # the ring reads as raised under the same key light as everything else.
    cx = cy = 7.5
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - cx, y - cy)
            if 4.1 <= d <= 5.4:
                lit = (x - cx) + (y - cy) < 0
                idx[y][x] = INLAY_BRIGHT if lit else INLAY_DEEP
            elif 2.2 <= d < 4.1:
                idx[y][x] = IRON_DARK if (x + y) % 2 else IRON_MID
            elif d < 2.2:
                idx[y][x] = INLAY_GOLD if d < 0.9 else INLAY_MID

    return to_image(idx, IRON_RAMP)


def gen_jukebox() -> None:
    save_png(jukebox_side(), "null_iron_jukebox_side")
    save_png(jukebox_top(), "null_iron_jukebox_top")

    write_json(BLOCK_MODELS / "null_iron_jukebox.json", {
        "parent": "minecraft:block/cube_top",
        "textures": {
            "side": f"{NS}:block/null_iron_jukebox_side",
            "top": f"{NS}:block/null_iron_jukebox_top",
        },
    })
    # One variant for every state: vanilla's own jukebox.json does the same, and
    # has_record only changes what is inside, not how the cabinet looks.
    write_json(BLOCKSTATES / "null_iron_jukebox.json",
               {"variants": {"": {"model": f"{NS}:block/null_iron_jukebox"}}})
    write_json(ITEM_DEFS / "null_iron_jukebox.json",
               {"model": {"type": "minecraft:model", "model": f"{NS}:block/null_iron_jukebox"}})


# ==========================================================================
# 3. The inversion anvil: body plate + the real anvil shape
# ==========================================================================

def anvil_body() -> Image.Image:
    """One plate texture, drawn in the bands vanilla's anvil model samples.

    minecraft:block/template_anvil takes every face of all four elements out of
    a single 16x16 sprite. Reading the UVs back gives three horizontal bands:

        y  0..5    the horn block's north/south faces
        y  0..15   the horn block's east/west faces (x 10..15)
        y  6..11   the waist
        y 12..15   the base's north/south faces
        x  0..3    the base's east/west faces

    So the texture is drawn as bands rather than as a tile: heavy plating low
    down, a narrower waist through the middle, and a struck-looking top.
    """
    values = plate_field(0x2B01, grain=8, grit=0.34, relief=0.45)
    flat = [values[y][x] for y in range(SIZE) for x in range(SIZE)]
    levels = quantise(flat, [0.16, 0.30, 0.30, 0.18, 0.06])
    idx = [[levels[y * SIZE + x] + 1 for x in range(SIZE)] for y in range(SIZE)]

    # Horn block, y 0..5: lighter, with a bismuth inlay seam along its shoulder.
    for x in range(SIZE):
        for y in range(0, 6):
            idx[y][x] = min(len(IRON_RAMP) - 2, idx[y][x] + 1)
        idx[1][x] = INLAY_DEEP if x % 4 else INLAY_MID
        idx[0][x] = IRON_LIGHT
        idx[5][x] = IRON_DARK

    # Waist, y 6..11: darker with a vertical grain, and a cyan filament running
    # down the middle - the seam the inversion energy travels along.
    for y in range(6, 12):
        for x in range(SIZE):
            idx[y][x] = IRON_DARK if x % 2 else max(1, idx[y][x] - 1)
        idx[y][7] = INLAY_DEEP
        idx[y][8] = INLAY_BRIGHT if y % 2 else INLAY_MID

    # Base, y 12..15: the heaviest plating, with rivets at the corners.
    for y in range(12, SIZE):
        for x in range(SIZE):
            idx[y][x] = max(1, idx[y][x] - 1)
    for x in range(SIZE):
        idx[12][x] = IRON_LIGHT if x % 5 else IRON_MID
        idx[SIZE - 1][x] = IRON_DARK
    for x in (2, 8, 13):
        idx[14][x] = IRON_LIGHT
        idx[14][(x + 1) % SIZE] = IRON_DARK

    return to_image(idx, IRON_RAMP)


def anvil_model() -> dict:
    """Vanilla's anvil silhouette in four boxes, retextured for null-iron.

    Copied box-for-box and UV-for-UV from minecraft:block/template_anvil so the
    proportions are exactly the ones players already read as "anvil": a 12x4
    base, a 8x1 lip, a narrow 4x5 waist, and a 10x6 horn block overhanging front
    to back. Inlining it rather than parenting to template_anvil keeps the model
    readable next to the shape it is describing, and template_anvil hard-codes a
    vanilla #body texture we are replacing anyway.
    """
    body = f"{NS}:block/inversion_anvil_body"
    top = f"{NS}:block/inversion_anvil_top"
    return {
        "parent": "minecraft:block/block",
        "textures": {"particle": body, "body": body, "top": top},
        "display": {
            "fixed": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [0.5, 0.5, 0.5]},
            "on_shelf": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]},
        },
        "elements": [
            {
                "from": [2, 0, 2],
                "to": [14, 4, 14],
                "faces": {
                    "down": {"uv": [2, 2, 14, 14], "texture": "#body", "rotation": 180, "cullface": "down"},
                    "up": {"uv": [2, 2, 14, 14], "texture": "#body", "rotation": 180},
                    "north": {"uv": [2, 12, 14, 16], "texture": "#body"},
                    "south": {"uv": [2, 12, 14, 16], "texture": "#body"},
                    "west": {"uv": [0, 2, 4, 14], "texture": "#body", "rotation": 90},
                    "east": {"uv": [4, 2, 0, 14], "texture": "#body", "rotation": 270},
                },
            },
            {
                "from": [4, 4, 3],
                "to": [12, 5, 13],
                "faces": {
                    "up": {"uv": [4, 3, 12, 13], "texture": "#body", "rotation": 180},
                    "north": {"uv": [4, 11, 12, 12], "texture": "#body"},
                    "south": {"uv": [4, 11, 12, 12], "texture": "#body"},
                    "west": {"uv": [4, 3, 5, 13], "texture": "#body", "rotation": 90},
                    "east": {"uv": [5, 3, 4, 13], "texture": "#body", "rotation": 270},
                },
            },
            {
                "from": [6, 5, 4],
                "to": [10, 10, 12],
                "faces": {
                    "north": {"uv": [6, 6, 10, 11], "texture": "#body"},
                    "south": {"uv": [6, 6, 10, 11], "texture": "#body"},
                    "west": {"uv": [5, 4, 10, 12], "texture": "#body", "rotation": 90},
                    "east": {"uv": [10, 4, 5, 12], "texture": "#body", "rotation": 270},
                },
            },
            {
                "from": [3, 10, 0],
                "to": [13, 16, 16],
                "faces": {
                    "down": {"uv": [3, 0, 13, 16], "texture": "#body", "rotation": 180},
                    "up": {"uv": [3, 0, 13, 16], "texture": "#top", "rotation": 180},
                    "north": {"uv": [3, 0, 13, 6], "texture": "#body"},
                    "south": {"uv": [3, 0, 13, 6], "texture": "#body"},
                    "west": {"uv": [10, 0, 16, 16], "texture": "#body", "rotation": 90},
                    "east": {"uv": [16, 0, 10, 16], "texture": "#body", "rotation": 270},
                },
            },
        ],
    }


def gen_anvil() -> None:
    save_png(anvil_body(), "inversion_anvil_body")
    write_json(BLOCK_MODELS / "inversion_anvil.json", anvil_model())
    # Rotations match vanilla's anvil.json: the model is authored facing south,
    # and the other three facings are that model turned. Requires the block to
    # carry BlockStateProperties.HORIZONTAL_FACING.
    write_json(BLOCKSTATES / "inversion_anvil.json", {
        "variants": {
            "facing=north": {"model": f"{NS}:block/inversion_anvil", "y": 180},
            "facing=south": {"model": f"{NS}:block/inversion_anvil"},
            "facing=west": {"model": f"{NS}:block/inversion_anvil", "y": 90},
            "facing=east": {"model": f"{NS}:block/inversion_anvil", "y": 270},
        }
    })


# ==========================================================================

def main() -> int:
    gen_portal()
    gen_jukebox()
    gen_anvil()
    print(f"gen_effect_textures: wrote {len(written)} file(s)")
    for w in written:
        print(f"  {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

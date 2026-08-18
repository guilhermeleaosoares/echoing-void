"""
The Echoing Void - texture sheets for the expansion creatures.

Same principles as tools/gen_entity_textures.py, and deliberately the same
code: this module imports that one's Sheet, box unwrap, shading helpers,
material ramps and preview rasteriser rather than restating them. What lives
here is only what is specific to these animals - their palettes and their
per-material painters.

  chime_mote        a small drifting lantern - a null-iron cage around a lit
                     core, four vanes that fan as it moves, and a wisp of tail.
                     Neutral ambient life, so it has to read as a lamp with a
                     creature in it rather than as a threat.
  tuner_shade        a hooded, robed caster holding a resonator ring in front of
                     its chest. Player-sized, and deliberately silhouetted like a
                     person - the blink is only unsettling if the thing that
                     vanishes looks like it could have been talked to.
  strata_burrower    a low armoured digger: wedge head, paired mandibles, three
                     body segments and six stubby claws. Long and flat, because
                     the whole creature has to read as "something moving under
                     the floor" from the ridge line alone.
  tuner_trader       a robed, hatted trader with a satchel of goods, standing on
                     two legs rather than floating - the one silhouette down
                     here that reads as "safe to approach".
  tuners_protector   an iron-golem-shaped guardian built from oversized plate
                     limbs, quarried from the same phonolite the outposts it
                     guards are built of.

Every colour used here comes from a ramp already defined in
gen_entity_textures, so the whole set stays inside the palette continuum
tools/verify_textures.py enforces.

Run:  python tools/gen_new_creature_textures.py
Outputs:
  src/main/resources/assets/echoing_void/textures/entity/<creature>.png
  src/main/resources/assets/echoing_void/textures/entity/<creature>_glow.png
  build/texture_preview/new_creatures_sheets.png    the flat sheets, 4x, labelled
  build/texture_preview/new_creatures_render.png    isometric preview of each mob
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_new_creature_geo import BUILDERS                       # noqa: E402
from gen_geo_models import Model                                # noqa: E402
from ev_palette import parse_hex, mix                            # noqa: E402
from gen_entity_textures import (                                # noqa: E402
    AMBER, ARCANE, CHALK, CHITIN, CHITIN_PALE, CYAN, GOLD, MAGENTA, STONE,
    GLOW_ALPHAS, OUTLINE, SIDE_FACES,
    Sheet, _hash, band_face, box_faces, crackle, fill_face, grain, label,
    outline_bottom, pick, ramp, render_model, sheet_contact, strata_profile,
)

ROOT = Path(__file__).resolve().parent.parent
TEX_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "entity"
PREVIEW_DIR = ROOT / "build" / "texture_preview"

RGBA = tuple[int, int, int, int]


# ---------------------------------------------------------------------------
# chime_mote
#
# Almost all of its colour lives on the glow sheet: it is the only friendly
# thing down there and it has to be recognisable as a light from across a
# chasm, not just a shape.
# ---------------------------------------------------------------------------

def mote_frame(base: Sheet, glow: Sheet, u, v, size, seed):
    """The cage: null-iron-dark posts and caps, cold against the lit core."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.0, face, seed, grain_amount=1.3, scale=1.8)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.blend(x0 + i, y0, STONE[5], 0.5)
            base.blend(x0 + i, y0 + fh - 1, GOLD[1], 0.3)


def mote_core(base: Sheet, glow: Sheet, u, v, size, seed):
    """The lit centre - hot cyan, brightest thing on the sheet."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            for i in range(fw):
                base.set(x0 + i, y0 + j, CYAN[4])
                glow.set(x0 + i, y0 + j, (*CYAN[5][:3], 240))


def mote_vane(base: Sheet, glow: Sheet, u, v, size, seed):
    """A thin drifting vane, lit along its trailing edge."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 1.2, face, seed, grain_amount=0.5)
    x0, y0, fw, fh = next(iter(faces.values()))
    for i in range(fw):
        base.set(x0 + i, y0, CYAN[2])
        glow.set(x0 + i, y0, (*CYAN[3][:3], 150))


def mote_wisp(base: Sheet, glow: Sheet, u, v, size, seed):
    """The trailing tail - a soft fade from the core's colour down to stone."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            t = 1.0 - j / max(1, fh - 1)
            for i in range(fw):
                n = grain(x0 + i, y0 + j, seed, scale=1.5) * 0.6
                level = t * 4.5 + n
                c = pick(STONE if t < 0.35 else CYAN, level if t >= 0.35 else level + 1)
                base.set(x0 + i, y0 + j, c)
                if t > 0.35:
                    glow.set(x0 + i, y0 + j, (*CYAN[4][:3], int(60 + 140 * t)))


# ---------------------------------------------------------------------------
# tuner_shade
#
# Arcane violet cloth with magenta piping, a black hood cavity with two lit
# eyes, and a bright resonator ring - cloth, not armour, and it should look
# like it dies quickly.
# ---------------------------------------------------------------------------

def shade_robe(base: Sheet, glow: Sheet, u, v, size, seed):
    """Skirt and hem: deep arcane cloth, darkest at the ground."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 2.4, face, seed, grain_amount=1.0, scale=3.2)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        if fh >= 3:
            for i in range(fw):
                base.blend(x0 + i, y0 + fh - 2, MAGENTA[1], 0.45)
                base.blend(x0 + i, y0 + fh - 1, ARCANE[0], 0.6)


def shade_cloth(base: Sheet, glow: Sheet, u, v, size, seed):
    """The torso, carrying the tuning sigil the shade casts through."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 3.0, face, seed, grain_amount=0.9)
    x0, y0, fw, fh = faces.get("north", next(iter(faces.values())))
    cx = x0 + fw // 2
    for k in range(min(3, fh // 3)):
        row = y0 + fh // 3 + k
        for dx in (-k - 1, k + 1):
            base.blend(cx + dx, row, MAGENTA[2], 0.5)


def shade_mantle(base: Sheet, glow: Sheet, u, v, size, seed):
    """Shoulder mantle - a lit magenta edge over dark arcane cloth."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 2.0, face, seed, grain_amount=0.7)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.blend(x0 + i, y0, MAGENTA[2], 0.4)


def shade_hood(base: Sheet, glow: Sheet, u, v, size, seed):
    """The hood. Black cavity on the front face with two lit eyes in it."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 2.2, face, seed, grain_amount=0.8)

    x0, y0, fw, fh = faces.get("north", next(iter(faces.values())))
    if fw < 4 or fh < 4:
        for i in range(fw):
            base.set(x0 + i, y0, MAGENTA[3])
            glow.set(x0 + i, y0, (*MAGENTA[4][:3], 210))
        return

    for j in range(1, fh - 1):
        for i in range(1, fw - 1):
            base.set(x0 + i, y0 + j, OUTLINE)
    ey = y0 + fh // 2 - 1
    for k, dx in enumerate((fw // 3, fw - fw // 3 - 1)):
        base.set(x0 + dx, ey, MAGENTA[4])
        glow.set(x0 + dx, ey, (*MAGENTA[5][:3], 255 - k * 45))
        base.blend(x0 + dx, ey + 1, MAGENTA[2], 0.5)
        glow.set(x0 + dx, ey + 1, (*MAGENTA[3][:3], 140))


def shade_limb(base: Sheet, glow: Sheet, u, v, size, seed):
    """A sleeved arm: wrapped cloth, banded, with a lit cuff at the wrist."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 2.6, face, seed, grain_amount=0.7, scale=2.2)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(fh):
            if j % 3 == 0:
                for i in range(fw):
                    base.blend(x0 + i, y0 + j, ARCANE[0], 0.5)
            elif j % 3 == 1:
                for i in range(fw):
                    base.blend(x0 + i, y0 + j, CHITIN_PALE[3], 0.28)
        for i in range(fw):
            base.blend(x0 + i, y0 + fh - 1, MAGENTA[2], 0.5)


def shade_ring(base: Sheet, glow: Sheet, u, v, size, seed):
    """The resonator ring - a bright, thin frame, magenta-hot along its rim."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, ARCANE, 1.6, face, seed, grain_amount=0.4)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            n = grain(x0 + i, y0, seed + i, scale=1.5)
            level = 4.0 + n * 1.5
            c = pick(MAGENTA, level)
            base.set(x0 + i, y0, c)
            glow.set(x0 + i, y0, (*c[:3], int(180 + 75 * ((n + 1) / 2))))


def shade_spark(base: Sheet, glow: Sheet, u, v, size, seed):
    """The mote held inside the ring - the brightest thing on the model."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        x0, y0, fw, fh = rect
        for j in range(fh):
            for i in range(fw):
                n = grain(x0 + i, y0 + j, seed, scale=1.2)
                level = 4.5 + n
                c = pick(MAGENTA, level)
                base.set(x0 + i, y0 + j, c)
                glow.set(x0 + i, y0 + j, (*c[:3], int(200 + 55 * ((n + 1) / 2))))


# ---------------------------------------------------------------------------
# strata_burrower
#
# Banded phonolite carapace with amber strata running through it, chalk
# mandibles and gold-lit dorsal ridges - made of the rock it swims through,
# which is why it can hide in it.
# ---------------------------------------------------------------------------

def burrower_carapace(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    profile = strata_profile(seed)
    for face, rect in faces.items():
        if face in ("up", "down"):
            fill_face(base, rect, STONE, 3.0, face, seed, grain_amount=1.1)
        else:
            band_face(base, rect, STONE, AMBER, 2.8, face, seed, profile)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 5, density=0.045)
    outline_bottom(base, faces.get("down", next(iter(faces.values()))), OUTLINE)


def burrower_skull(base: Sheet, glow: Sheet, u, v, size, seed):
    """The wedge head - two dim amber eye sparks are enough; a burrower that
    surfaces behind you should be identifiable by two dim sparks, not a face."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.8, face, seed, grain_amount=1.0)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 9, density=0.04)
    x0, y0, fw, fh = faces.get("north", next(iter(faces.values())))
    ey = y0 + fh // 3
    for k, dx in enumerate((2, fw - 3)):
        base.set(x0 + dx, ey, AMBER[3])
        glow.set(x0 + dx, ey, (*AMBER[4][:3], 150 - k * 30))
        base.blend(x0 + dx, ey + 1, AMBER[1], 0.5)
        glow.set(x0 + dx, ey + 1, (*AMBER[2][:3], 90))


def burrower_plate(base: Sheet, glow: Sheet, u, v, size, seed):
    """Brow shield: a lighter chalk plate over the skull."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHALK, 2.2, face, seed, grain_amount=0.6)


def burrower_ridge(base: Sheet, glow: Sheet, u, v, size, seed):
    """Dorsal ridge - gold-lit spine, the part visible above ground."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.6, face, seed, grain_amount=0.7)
    if "up" in faces:
        x0, y0, fw, fh = faces["up"]
        for j in range(fh):
            for i in range(fw):
                n = grain(x0 + i, y0 + j, seed, scale=1.4)
                level = 3.0 + n * 1.8
                base.set(x0 + i, y0 + j, pick(GOLD, level))
                glow.set(x0 + i, y0 + j, (*pick(GOLD, level)[:3], int(150 + 80 * ((n + 1) / 2))))


def burrower_mandible(base: Sheet, glow: Sheet, u, v, size, seed):
    """Digging jaw: chalk-tipped, dark at the root."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.0, face, seed, grain_amount=0.7)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.set(x0 + i, y0, CHALK[3])
            base.blend(x0 + i, y0 + 1, CHALK[1], 0.6)


def burrower_limb(base: Sheet, glow: Sheet, u, v, size, seed):
    """Digging leg: banded stone, amber joint."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.2, face, seed, grain_amount=0.8, scale=2.0)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(fh):
            base.set(x0, y0 + j, AMBER[2])


def burrower_claw(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 1.4, face, seed, grain_amount=0.5)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(fh):
            base.set(x0 + fw - 1, y0 + j, CHALK[2])


# ---------------------------------------------------------------------------
# tuner_trader
# ---------------------------------------------------------------------------

def trader_robe(base: Sheet, glow: Sheet, u, v, size, seed):
    """Legs, torso and arms: warm amber cloth, the one warm material down
    here that reads as clothing rather than as armour or rock."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, AMBER, 2.6, face, seed, grain_amount=0.8, scale=2.6)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        if fh >= 3:
            for i in range(fw):
                base.blend(x0 + i, y0 + fh - 2, AMBER[0], 0.4)


def trader_satchel(base: Sheet, glow: Sheet, u, v, size, seed):
    """The satchel: brass-toned, the trader's tell at a distance."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, GOLD, 2.0, face, seed, grain_amount=0.6)


def trader_strap(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, GOLD, 1.4, face, seed, grain_amount=0.4)


def trader_head(base: Sheet, glow: Sheet, u, v, size, seed):
    """Pale, chalk-toned - a dweller who has spent a long time under the
    dimension's own light rather than the sun."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHALK, 3.0, face, seed, grain_amount=0.5)
    x0, y0, fw, fh = faces.get("north", next(iter(faces.values())))
    ey = y0 + fh // 2
    for k, dx in enumerate((fw // 3, fw - fw // 3 - 1)):
        base.set(x0 + dx, ey, CYAN[3])
        glow.set(x0 + dx, ey, (*CYAN[4 - k][:3], 220 - k * 40))
        base.blend(x0 + dx, ey + 1, CYAN[1], 0.5)
        glow.set(x0 + dx, ey + 1, (*CYAN[2 + k][:3], 120))


def trader_hat(base: Sheet, glow: Sheet, u, v, size, seed):
    """The brim and crown: dark, so the pale head reads clearly under it."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 2.0, face, seed, grain_amount=0.5)


def trader_hand(base: Sheet, glow: Sheet, u, v, size, seed):
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, CHALK, 2.6, face, seed, grain_amount=0.4)


# ---------------------------------------------------------------------------
# tuners_protector
# ---------------------------------------------------------------------------

def protector_plate(base: Sheet, glow: Sheet, u, v, size, seed):
    """The bulk of the guardian: stone plate, banded like the phonolite it is
    quarried from - the same rock the outpost it guards is built of."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    profile = strata_profile(seed)
    for face, rect in faces.items():
        if face in ("up", "down"):
            fill_face(base, rect, STONE, 4.0, face, seed, grain_amount=1.1, scale=2.4)
        else:
            band_face(base, rect, STONE, CHALK, 3.8, face, seed, profile)
        crackle(base, rect, parse_hex("#0A0B0F"), seed + 5, density=0.03)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for j in range(0, fh, 4):
            for i in range(fw):
                base.blend(x0 + i, y0 + j, GOLD[1], 0.25)


def protector_head(base: Sheet, glow: Sheet, u, v, size, seed):
    """A block of plate, not a face - two lit slits are the only feature."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 4.2, face, seed, grain_amount=0.6)
    x0, y0, fw, fh = faces.get("north", next(iter(faces.values())))
    slit_y = y0 + fh // 2
    for k, dx in enumerate((1, fw - 2)):
        base.set(x0 + dx, slit_y, GOLD[4])
        glow.set(x0 + dx, slit_y, (*GOLD[5][:3], 235 - k * 45))
        base.blend(x0 + dx, slit_y + 1, GOLD[2], 0.5)
        glow.set(x0 + dx, slit_y + 1, (*GOLD[3][:3], 130))


def protector_neck(base: Sheet, glow: Sheet, u, v, size, seed):
    """A dark stone collar joint between the plated head and the torso."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 1.4, face, seed, grain_amount=0.5)


def protector_fist(base: Sheet, glow: Sheet, u, v, size, seed):
    """The forearms: dark reinforced stone, the part of the body that actually
    lands the hit - this is the single strongest material read on it."""
    w, h, d = size
    faces = box_faces(u, v, w, h, d)
    for face, rect in faces.items():
        fill_face(base, rect, STONE, 1.6, face, seed, grain_amount=0.7, scale=2.0)
    for face in SIDE_FACES:
        x0, y0, fw, fh = faces[face]
        for i in range(fw):
            base.blend(x0 + i, y0, STONE[6], 0.35)


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

PALETTES: dict[str, tuple[list[RGBA], tuple[int, ...]]] = {
    "chime_mote": (
        STONE + CYAN + GOLD[1:4] + [OUTLINE],
        (255,),
    ),
    "tuner_shade": (
        ARCANE + MAGENTA + CHITIN[:4] + [CHITIN_PALE[3], CHITIN_PALE[4],
                                         CHALK[0], CHALK[4], CYAN[2], OUTLINE],
        (255,),
    ),
    "strata_burrower": (
        STONE + AMBER + GOLD[2:] + CHALK + [OUTLINE],
        (255,),
    ),
    "tuner_trader": (
        AMBER + GOLD + CHALK + CYAN[2:4] + STONE[:3] + [OUTLINE],
        (255,),
    ),
    "tuners_protector": (
        STONE + CHALK + GOLD + [OUTLINE],
        (255,),
    ),
}

PAINTERS = {
    "chime_mote": {
        "frame": mote_frame,
        "core": mote_core,
        "vane": mote_vane,
        "wisp": mote_wisp,
    },
    "tuner_shade": {
        "robe": shade_robe,
        "cloth": shade_cloth,
        "mantle": shade_mantle,
        "hood": shade_hood,
        "limb": shade_limb,
        "ring": shade_ring,
        "spark": shade_spark,
    },
    "strata_burrower": {
        "carapace": burrower_carapace,
        "skull": burrower_skull,
        "plate": burrower_plate,
        "ridge": burrower_ridge,
        "mandible": burrower_mandible,
        "limb": burrower_limb,
        "claw": burrower_claw,
    },
    "tuner_trader": {
        "robe": trader_robe,
        "satchel": trader_satchel,
        "strap": trader_strap,
        "head": trader_head,
        "hat": trader_hat,
        "hand": trader_hand,
    },
    "tuners_protector": {
        "plate": protector_plate,
        "head": protector_head,
        "neck": protector_neck,
        "fist": protector_fist,
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


def main() -> int:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    flat: list[tuple[str, Image.Image]] = []
    renders: list[tuple[str, Image.Image]] = []

    for name, (builder, _, _, _) in BUILDERS.items():
        model = builder()
        model.finalise()
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
              f"{hues} colours, {len(opaque)} painted texels, glow sheet lights {lit}")
        if not 10 <= hues <= 40:
            print(f"  WARNING: {hues} colours is outside the gate's entity band (10-40)")

        flat.append((name, base_img))
        flat.append((f"{name}_glow", glow_img))
        for yaw, view in ((0, "front"), (110, "side"), (200, "back")):
            renders.append((f"{name} / {view}", render_model(model, base_img, yaw=yaw)))

    contact = sheet_contact(flat, zoom=4)
    contact.save(PREVIEW_DIR / "new_creatures_sheets.png")

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
    board.save(PREVIEW_DIR / "new_creatures_render.png")

    print(f"preview: {PREVIEW_DIR / 'new_creatures_sheets.png'}")
    print(f"preview: {PREVIEW_DIR / 'new_creatures_render.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

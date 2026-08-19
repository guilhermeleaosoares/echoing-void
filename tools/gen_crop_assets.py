"""
The Echoing Void - void farming: sprites, models, loot, recipes and tags.

Owns everything non-Java for the farming set registered by
src/main/java/com/echoingvoid/registry/ModCrops.java:

    void_farmland (+ moist)        resonance moss cut open with a hoe
    resonant_wheat   8 stages      the grain that becomes Resonant Bread
    chime_roots      4 stages      the carrot analogue, edible raw
    void_tubers      4 stages      the potato analogue
    echo_gourd + stem + attached   the pumpkin analogue, also found wild

PALETTE, AND WHY THESE CROPS ARE NOT GREEN
------------------------------------------
docs/spec/art_direction.json has five families - a neutral slate-to-chalk spine,
a warm amber band, a cold cyan glow, an arcane magenta glow, and null-iron.
There is no green anywhere in it, and tools/verify_textures.py rejects any
colour off that continuum. So the farm is coloured by what it is rather than by
what earth crops look like: amber for the grain (the one warm band, and the one
that reads as "harvest"), cyan for the root and the gourd, violet for the tuber.
A green wheat field would have failed the gate and, more to the point, would
have looked like it came from a different mod.

STAGE COUNTS
------------
Vanilla maps eight AGE values onto however many sprites a crop has - wheat gets
eight, carrots and potatoes four (0,1|2,3|4,5,6|7). Both mappings are reproduced
here, so a player reads growth at exactly the rate they are used to.

THE COLOUR FLOOR IS THE HARD PART
---------------------------------
The gate demands 5-16 distinct colours in every sprite, and vanilla's own
wheat_stage0 has four. An early crop stage is a dozen pixels, so the shading has
to be deliberate rather than incidental: every stage draws its stalks at
staggered ramp levels instead of one flat tone, which is what keeps the count
above the floor without making a two-pixel sprout look mottled.

Run:  python tools/gen_crop_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from gen_item_textures import (  # noqa: E402
    Material, Sprite, col, spans, rect, blob, lozenge, stroke,
)
# The periodic-noise helper lives with the fluid sheets, which needed the same
# thing first. Duplicating it would be two hash functions to keep in step.
from gen_fluid_assets import pfbm  # noqa: E402

NS = "echoing_void"
ROOT = TOOLS.parent
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / NS
DATA = ROOT / "src" / "main" / "resources" / "data" / NS
TEX_BLOCK = ASSETS / "textures" / "block"
TEX_ITEM = ASSETS / "textures" / "item"

written: list[str] = []


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(path.relative_to(ROOT)).replace("\\", "/"))


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------

# Tilled moss: the moss's own cyan pushed down into the phonolite darks, so a
# ploughed field reads as opened ground rather than as a second kind of plant.
SOIL = Material("soil", [
    col("void_black", "ph_dark", 6),
    col("ph_dark", "bis_deep", 3),
    col("ph_dark", "bis_deep", 7),
    col("ph_mid", "bis_deep", 8),
    col("bis_deep", "ph_light", 6),
    col("bis_deep", "bis_mid", 5),
])

# The same soil watered. Darker overall and further toward the cyan, which is
# exactly the relationship vanilla farmland_moist has to farmland.
SOIL_WET = Material("soil_wet", [
    col("void_black", "void_shadow", 5),
    col("void_shadow", "bis_deep", 4),
    col("void_shadow", "bis_deep", 9),
    col("ph_dark", "bis_deep", 12),
    col("bis_deep", "bis_mid", 3),
    col("bis_deep", "bis_mid", 9),
])

# Grain. The amber band, which is the only warm family in the palette and the
# only one a player will read as a harvest.
GRAIN = Material("grain", [
    col("amber_dark", "void_black", 6),
    col("amber_dark", "ph_dark", 3),
    col("amber_dark", "amber_mid", 7),
    col("amber_mid", "amber_light", 8),
    col("amber_light", "amber_hi", 7),
    col("amber_hi", "chalk_light", 6),
])

# Chime root tops, and the gourd.
TEAL = Material("teal", [
    col("bis_deep", "void_black", 7),
    col("bis_deep", "void_shadow", 3),
    col("bis_deep", "bis_mid", 5),
    col("bis_mid", "bis_bright", 4),
    col("bis_bright", "chalk_light", 4),
    col("bis_bright", "chalk_light", 10),
])

# Void tuber. The arcane family: the one crop that looks like it should not be
# eaten, which is the right note for a potato analogue grown in a void.
VIOLET = Material("violet", [
    col("arc_deep", "void_black", 6),
    col("arc_deep", "void_shadow", 2),
    col("arc_deep", "arc_mid", 7),
    col("arc_mid", "arc_light", 7),
    col("arc_light", "arc_bright", 5),
    col("arc_light", "chalk_light", 7),
])

# Pale stone-white, for bread crumb.
PALE = Material("pale", [
    col("ph_dark", "void_black", 4),
    col("ph_mid", "ph_light", 6),
    col("chalk_shadow", "ph_light", 5),
    col("chalk_shadow", "chalk_mid", 8),
    col("chalk_mid", "chalk_light", 8),
    col("chalk_light", "chalk_hi", 8),
])

# Root flesh: chalk pulled toward the bismuth cyan. Straight chalk read as bone
# in the hotbar - a pale sliver with a teal tuft on it, which is not a
# vegetable. Tinting the flesh ties it to its own leaves.
ROOT_FLESH = Material("root", [
    col("bis_deep", "void_black", 8),      # lum  73
    col("bis_deep", "ph_mid", 4),          # lum  95
    col("bis_deep", "bis_mid", 3),         # lum 120
    col("ph_light", "bis_mid", 8),         # lum 144
    col("chalk_shadow", "bis_mid", 8),     # lum 167
    col("chalk_light", "chalk_hi", 6),     # lum 216
])


# ---------------------------------------------------------------------------
# crop sprites
# ---------------------------------------------------------------------------

# The four stalk PAIRS a cross-model crop is drawn on. Two pixels wide, not one,
# and that is not a style choice: Sprite.outline() repaints every silhouette-edge
# pixel to the ramp's two darkest tones, and a one-pixel stalk is ENTIRELY edge -
# the first version of these sprites came out in two colours and the texture gate
# rejected all sixteen of them as flat programmer art. A pair carries its own
# shading (dark column left, lit column right) and needs no outline pass at all,
# which is also how vanilla's own wheat is drawn.
STALK_X = (1, 5, 9, 13)


def stalk(sp: Sprite, mat: Material, x: int, top: int, base: int) -> None:
    """One two-pixel stem from the soil line (y=15) up to `top`.

    The ramp index walks UP as the stalk rises - a stem really is lighter at the
    tip - and the right column sits two steps brighter than the left. Between
    them a single stalk already spans four of the ramp's six entries, which is
    what keeps even a three-pixel sprout above the gate's five-colour floor.
    """
    span = max(1, 15 - top)
    for i, y in enumerate(range(15, top - 1, -1)):
        t = i / span
        shade = base + int(round(1.6 * t))
        sp.put(x, y, mat, shade, lock=True)
        sp.put(x + 1, y, mat, shade + 2, lock=True)


def head(sp: Sprite, mat: Material, x: int, top: int) -> None:
    """The grain head: a dark husk left of the stalk and a lit ear right of it.

    The husk is the ramp's darkest entry, and is the only place index 0 appears
    in a crop sprite - which is what gives a ripe ear its silhouette.
    """
    for i, y in enumerate((top, top + 1, top + 2)):
        sp.put(x - 1, y, mat, 0, lock=True)
        sp.put(x + 2, y, mat, 5 - i, lock=True)


def wheat_stage(n: int) -> Sprite:
    """Eight stages: bare sprouts, then stems, then heads, then a full ear."""
    sp = Sprite()
    top = 13 - n
    for i, x in enumerate(STALK_X):
        # The outer two stalks run a pixel shorter, so the silhouette is not a
        # flat-topped hedge.
        t = min(14, top + (1 if i in (0, 3) else 0))
        stalk(sp, GRAIN, x, t, 1)
        if n >= 5:
            head(sp, GRAIN, x, t)
    return sp


def leafy_stage(n: int, mat: Material, crown: Material | None,
                crown_level: float = 0.9) -> Sprite:
    """Four stages of a root crop: a tuft that spreads before it shows a crown."""
    sp = Sprite()
    top = 12 - 2 * n
    for i, x in enumerate(STALK_X):
        t = min(14, top + (1 if i in (0, 3) else 0))
        stalk(sp, mat, x, t, 1)
        for dx in range(1, n + 1):
            # Leaves fan out one row wider per stage, alternating dark and lit
            # so a full tuft still reads as separate blades.
            y = min(15, t + dx + 1)
            sp.put(x - dx, y, mat, max(0, 2 - dx), lock=True)
            sp.put(x + 1 + dx, y, mat, min(5, 5 - dx), lock=True)
    if crown is not None and n == 3:
        # Ripe: the crop itself breaks the soil between the stems.
        for x in (3, 11):
            sp.put(x, 15, crown, crown.tone(crown_level), lock=True)
            sp.put(x + 1, 15, crown, crown.tone(max(0.0, crown_level - 0.35)), lock=True)
            sp.put(x, 14, crown, crown.tone(max(0.0, crown_level - 0.6)), lock=True)
    return sp


def rope(sp: Sprite, mat: Material, path, thickness: float) -> None:
    """A tendril, shaded by a repeating index walk rather than by an outline.

    The stem model samples a GROWING SLICE of its texture (stem_growth0 takes
    rows 0-2, stem_growth7 all sixteen), so every horizontal band of this sprite
    has to carry the full range of tones on its own. A top-lit gradient would
    leave a young stem a single flat colour and an old one fine.
    """
    for (x, y) in sorted(stroke(path, thickness)):
        sp.put(x, y, mat, (x * 3 + y * 2) % 6, lock=True)


def gourd_stem_tex() -> Sprite:
    """The tendril sheet: one waving rope down the middle of the tile."""
    sp = Sprite()
    rope(sp, TEAL, [(8.0, 0.0), (6.5, 4.0), (9.0, 8.0), (7.0, 12.0), (8.0, 15.0)], 1.8)
    return sp


def attached_stem_tex() -> Sprite:
    """The thickened elbow that appears once a gourd has set beside the stem."""
    sp = Sprite()
    rope(sp, TEAL, [(1.0, 14.0), (5.0, 11.0), (8.0, 6.0), (8.0, 1.0)], 2.4)
    return sp


# ---------------------------------------------------------------------------
# full-cube sprites
#
# These use a histogram-matched fill rather than Sprite.paint(). paint() maps a
# narrow noise band through Material.tone(), which only ever reaches the middle
# of the ramp - it produced two-colour tiles here. Slicing the SORTED field by
# target shares instead guarantees every ramp entry appears and pins the
# dominant colour's share to the largest number in `shares`, so the gate's
# five-colour floor and 85% ceiling both hold by construction.
# ---------------------------------------------------------------------------

def field_fill(sp: Sprite, cells, mat: Material, seed: int,
               shares: list[float], scale: float = 3.5) -> None:
    cells = sorted(cells)
    values = [pfbm(x / scale, y / scale, 16, 16, seed) for (x, y) in cells]
    order = sorted(values)
    cuts: list[float] = []
    running = 0.0
    for share in shares[:-1]:
        running += share
        cuts.append(order[min(len(order) - 1, int(running * len(order)))])
    for (x, y), value in zip(cells, values):
        idx = 0
        while idx < len(cuts) and value > cuts[idx]:
            idx += 1
        sp.put(x, y, mat, idx, lock=True)


# Weighted toward the MIDDLE of the ramp rather than spread evenly across it.
# An even spread puts a tenth of the tile at each extreme, and with a six-entry
# ramp running from near-black to near-white that reads as blotches rather than
# as a surface. Vanilla's own stone.png spans 39 luminance across four colours;
# keeping the extremes to a twentieth each is what gets near that.
EVEN_SIX = [0.05, 0.17, 0.28, 0.28, 0.17, 0.05]


def farmland_top(mat: Material, seed: int, furrow: int) -> Sprite:
    """Tilled ground seen from above: three broken furrows in a mottled bed.

    The furrows are ONE row each and they are broken rather than continuous.
    The first version drew four unbroken two-row bands, a dark row against a
    light row, and the result read as a barcode rather than as ploughed
    ground - at 16 pixels a hard full-width line is the strongest shape in the
    tile and it beats everything else in it. Skipping roughly a third of each
    row against the same noise field that draws the bed keeps the direction
    legible while letting the soil show through.
    """
    sp = Sprite()
    field_fill(sp, rect(0, 0, 16, 16), mat, seed, EVEN_SIX)
    for row in (3, 8, 13):
        for x in range(16):
            if pfbm(x / 2.0, row / 2.0, 16, 16, seed + 991) > 0.42:
                sp.put(x, row, mat, furrow, lock=True)
    return sp


def gourd_side() -> Sprite:
    """Two ribs down a mottled body - the cue that says gourd at 16 pixels.

    Two, not four. Four ribs on a 16-wide tile is a rib every four pixels,
    which stops reading as a curved surface and starts reading as corrugated
    iron. Each rib is a dark line with a lit line beside it, so the eye reads
    a fold rather than a stripe.
    """
    sp = Sprite()
    field_fill(sp, rect(0, 0, 16, 16), TEAL, 3301, EVEN_SIX, scale=3.5)
    for x in (3, 11):
        for y in range(16):
            sp.put(x, y, TEAL, 1, lock=True)
            sp.put(x + 1, y, TEAL, 4, lock=True)
    return sp


def gourd_top() -> Sprite:
    """The stem scar, with the ribs running out from it to the rim."""
    sp = Sprite()
    field_fill(sp, rect(0, 0, 16, 16), TEAL, 3307, EVEN_SIX, scale=3.0)
    for (x, y) in blob(7.5, 7.5, 3.4, 5501, wobble=0.10):
        sp.put(x, y, TEAL, 1, lock=True)
    for (x, y) in blob(7.5, 7.5, 1.8, 5507, wobble=0.10):
        sp.put(x, y, TEAL, 5, lock=True)
    # No full-width rim rows. They read as a border drawn round the tile rather
    # than as the curve of a fruit, and on a top face that a player sees four
    # of side by side a hard border is the first thing to go.
    return sp


# ---------------------------------------------------------------------------
# item icons
# ---------------------------------------------------------------------------

def resonant_grain() -> Sprite:
    """A bound sheaf: three ears leaning the same way over a tie."""
    sp = Sprite()
    for i, base in enumerate((3, 6, 9)):
        path = [(base + 1.0, 14.0), (base + 2.0, 8.0), (base + 3.5, 2.0)]
        for (x, y) in sorted(stroke(path, 1.2)):
            sp.put(x, y, GRAIN, GRAIN.tone(0.40 + 0.04 * (15 - y)))
        for k in range(3):
            sp.put(base + 2 + k, 3 + k, GRAIN, GRAIN.tone(0.95 - 0.12 * k))
            sp.put(base + 4 + k, 4 + k, GRAIN, GRAIN.tone(0.80 - 0.12 * k))
    for x in range(4, 11):
        sp.put(x, 11, GRAIN, GRAIN.tone(0.22))
    sp.outline()
    return sp


def seed_icon(mat: Material, seed: int) -> Sprite:
    """A scatter of seeds. Four lozenges rather than loose pixels, because a
    single pixel disappears in a hotbar slot."""
    sp = Sprite()
    # Three seeds, further apart. Four fat lozenges at 16 pixels touch each
    # other and merge into an X, which is what the first draft read as - a
    # scatter has to have gaps in it to be a scatter.
    #
    # Each seed keeps a LOCKED core pixel, and the three cores sit at three
    # different ramp levels. A small lozenge is almost entirely silhouette
    # edge, and Sprite.outline() repaints every edge pixel into the ramp's two
    # darkest tones - without the locked cores the whole icon came out in two
    # colours and the gate rejected it as flat programmer art.
    for i, (cx, cy, angle, core) in enumerate((
            (4.5, 6.0, 35.0, 0.35), (10.5, 5.0, -30.0, 0.68), (7.5, 11.0, 10.0, 1.0))):
        for (x, y) in lozenge(cx, cy, 2.4, 1.3, angle):
            sp.put(x, y, mat, mat.tone(0.45 + 0.18 * (i % 3)))
        sp.stamp([(int(cx), int(cy))], mat, core, lock=True)
    sp.outline()
    return sp


def chime_root_icon() -> Sprite:
    """A tapered root, pale flesh with a teal crown - carrot's silhouette in
    this dimension's colours."""
    sp = Sprite()
    # A fatter shoulder than the first draft, which tapered from three pixels
    # and read as a splinter in the hotbar rather than as something to eat.
    body = spans({
        4: [(6, 10)], 5: [(5, 11)], 6: [(5, 11)], 7: [(5, 11)], 8: [(6, 10)],
        9: [(6, 10)], 10: [(7, 9)], 11: [(7, 9)], 12: [(8, 9)], 13: [(8, 8)],
    })
    sp.paint(body, ROOT_FLESH, 0.60, 7701, spread=0.30, light=0.26)
    # A crown big enough to read: five blades fanning off the shoulder rather
    # than the seven loose pixels the first draft scattered above it.
    for (x, y) in ((4, 3), (5, 2), (6, 1), (7, 0), (8, 1), (9, 1),
                   (10, 2), (11, 3), (6, 2), (9, 2), (7, 1), (8, 2)):
        sp.put(x, y, TEAL, TEAL.tone(0.40 + 0.14 * (x % 4)))
    for (x, y) in ((5, 1), (8, 0), (10, 1)):
        sp.put(x, y, TEAL, TEAL.tone(0.92))
    sp.outline()
    return sp


def void_tuber_icon() -> Sprite:
    """A lumpy oval with two eyes, which is the whole visual language of a
    potato."""
    sp = Sprite()
    for (x, y) in blob(8.0, 8.5, 5.0, 8811, wobble=0.26):
        sp.put(x, y, VIOLET, VIOLET.tone(0.5))
    sp.paint({(x, y) for (x, y) in blob(8.0, 8.5, 5.0, 8811, wobble=0.26)},
             VIOLET, 0.58, 8811, spread=0.34, light=0.28)
    for (x, y) in ((6, 7), (10, 10), (9, 6)):
        sp.put(x, y, VIOLET, VIOLET.tone(0.12))
        sp.put(x + 1, y, VIOLET, VIOLET.tone(0.28))
    sp.outline()
    return sp


def resonant_bread() -> Sprite:
    """A split loaf: amber crust, pale crumb through the score down the middle."""
    sp = Sprite()
    body = spans({
        5: [(3, 12)], 6: [(2, 13)], 7: [(2, 13)], 8: [(2, 13)],
        9: [(2, 13)], 10: [(3, 12)],
    })
    sp.paint(body, GRAIN, 0.55, 9901, spread=0.28, light=0.26)
    for x in range(4, 12):
        sp.put(x, 7, PALE, PALE.tone(0.70))
        sp.put(x, 8, PALE, PALE.tone(0.45))
    for x in (5, 8, 11):
        sp.put(x, 6, GRAIN, GRAIN.tone(0.95))
    sp.outline()
    return sp


# ---------------------------------------------------------------------------
# models and blockstates
# ---------------------------------------------------------------------------

# Vanilla's mapping of eight AGE values onto four sprites (carrots/potatoes).
FOUR_STAGE = (0, 0, 1, 1, 2, 2, 2, 3)


def crop_models(block: str, stages: int, stage_of_age) -> None:
    variants = {}
    for age in range(8):
        variants[f"age={age}"] = {"model": f"{NS}:block/{block}_stage{stage_of_age(age)}"}
    write_json(ASSETS / "blockstates" / f"{block}.json", {"variants": variants})
    for s in range(stages):
        write_json(ASSETS / "models" / "block" / f"{block}_stage{s}.json",
                   {"parent": "minecraft:block/crop",
                    "textures": {"crop": f"{NS}:block/{block}_stage{s}"}})


def gen_models() -> None:
    # ---- farmland ---------------------------------------------------------
    # Sides and bottom are the moss it was cut from, exactly as vanilla farmland
    # keeps dirt on five faces and only changes the top.
    write_json(ASSETS / "blockstates" / "void_farmland.json", {
        "variants": {
            **{f"moisture={m}": {"model": f"{NS}:block/void_farmland"} for m in range(7)},
            "moisture=7": {"model": f"{NS}:block/void_farmland_moist"},
        }
    })
    for name, top in (("void_farmland", "void_farmland"),
                      ("void_farmland_moist", "void_farmland_moist")):
        write_json(ASSETS / "models" / "block" / f"{name}.json", {
            "parent": "minecraft:block/template_farmland",
            "textures": {"dirt": f"{NS}:block/resonance_moss",
                         "top": f"{NS}:block/{top}"},
        })
    write_json(ASSETS / "items" / "void_farmland.json",
               {"model": {"type": "minecraft:model", "model": f"{NS}:block/void_farmland"}})

    # ---- crops ------------------------------------------------------------
    crop_models("resonant_wheat", 8, lambda age: age)
    crop_models("chime_roots", 4, lambda age: FOUR_STAGE[age])
    crop_models("void_tubers", 4, lambda age: FOUR_STAGE[age])

    # ---- the gourd --------------------------------------------------------
    write_json(ASSETS / "blockstates" / "echo_gourd.json",
               {"variants": {"": {"model": f"{NS}:block/echo_gourd"}}})
    write_json(ASSETS / "models" / "block" / "echo_gourd.json", {
        "parent": "minecraft:block/cube_column",
        "textures": {"end": f"{NS}:block/echo_gourd_top",
                     "side": f"{NS}:block/echo_gourd_side"},
    })
    write_json(ASSETS / "items" / "echo_gourd.json",
               {"model": {"type": "minecraft:model", "model": f"{NS}:block/echo_gourd"}})

    # The stem's eight models each inherit a different vanilla stem_growth
    # parent, which is what makes the tendril grow taller with age.
    write_json(ASSETS / "blockstates" / "echo_gourd_stem.json", {
        "variants": {f"age={a}": {"model": f"{NS}:block/echo_gourd_stem_stage{a}"}
                     for a in range(8)}
    })
    for a in range(8):
        write_json(ASSETS / "models" / "block" / f"echo_gourd_stem_stage{a}.json",
                   {"parent": f"minecraft:block/stem_growth{a}",
                    "textures": {"stem": f"{NS}:block/echo_gourd_stem"}})

    # Rotations copied from attached_pumpkin_stem.json: the model points west,
    # so facing=west needs no rotation and the rest count clockwise from it.
    write_json(ASSETS / "blockstates" / "attached_echo_gourd_stem.json", {
        "variants": {
            "facing=west": {"model": f"{NS}:block/attached_echo_gourd_stem"},
            "facing=north": {"model": f"{NS}:block/attached_echo_gourd_stem", "y": 90},
            "facing=east": {"model": f"{NS}:block/attached_echo_gourd_stem", "y": 180},
            "facing=south": {"model": f"{NS}:block/attached_echo_gourd_stem", "y": 270},
        }
    })
    write_json(ASSETS / "models" / "block" / "attached_echo_gourd_stem.json", {
        "parent": "minecraft:block/stem_fruit",
        "textures": {"stem": f"{NS}:block/echo_gourd_stem",
                     "upperstem": f"{NS}:block/attached_echo_gourd_stem"},
    })

    # ---- item models ------------------------------------------------------
    for item in ("resonant_wheat_seeds", "resonant_grain", "chime_root",
                 "void_tuber", "echo_gourd_seeds", "resonant_bread"):
        write_json(ASSETS / "models" / "item" / f"{item}.json",
                   {"parent": "minecraft:item/generated",
                    "textures": {"layer0": f"{NS}:item/{item}"}})
        write_json(ASSETS / "items" / f"{item}.json",
                   {"model": {"type": "minecraft:model", "model": f"{NS}:item/{item}"}})


# ---------------------------------------------------------------------------
# loot
# ---------------------------------------------------------------------------

EXPLOSION_DECAY = {"function": "minecraft:explosion_decay"}


def ripe(block: str) -> dict:
    return {"condition": "minecraft:block_state_property",
            "block": f"{NS}:{block}",
            "properties": {"age": "7"}}


def fortune_bonus() -> dict:
    """Vanilla's crop fortune curve, verbatim from blocks/wheat.json."""
    return {"function": "minecraft:apply_bonus",
            "enchantment": "minecraft:fortune",
            "formula": "minecraft:binomial_with_bonus_count",
            "parameters": {"extra": 3, "probability": 0.5714286}}


def write_loot(block: str, data: dict) -> None:
    data["random_sequence"] = f"{NS}:blocks/{block}"
    write_json(DATA / "loot_table" / "blocks" / f"{block}.json", data)


def gen_loot() -> None:
    # Grain crop: seeds always, grain and extra seeds only when ripe. Same
    # two-pool shape as vanilla wheat.
    write_loot("resonant_wheat", {
        "type": "minecraft:block",
        "functions": [EXPLOSION_DECAY],
        "pools": [
            {"rolls": 1.0, "entries": [{
                "type": "minecraft:alternatives",
                "children": [
                    {"type": "minecraft:item", "name": f"{NS}:resonant_grain",
                     "conditions": [ripe("resonant_wheat")]},
                    {"type": "minecraft:item", "name": f"{NS}:resonant_wheat_seeds"},
                ]}]},
            {"rolls": 1.0, "conditions": [ripe("resonant_wheat")],
             "entries": [{"type": "minecraft:item",
                          "name": f"{NS}:resonant_wheat_seeds",
                          "functions": [fortune_bonus()]}]},
        ],
    })

    # Root crops: the crop IS the seed, so one always drops and a ripe one
    # drops a fortune-scaled handful more. Vanilla carrots exactly.
    for block, item in (("chime_roots", "chime_root"), ("void_tubers", "void_tuber")):
        write_loot(block, {
            "type": "minecraft:block",
            "functions": [EXPLOSION_DECAY],
            "pools": [
                {"rolls": 1.0, "entries": [
                    {"type": "minecraft:item", "name": f"{NS}:{item}"}]},
                {"rolls": 1.0, "conditions": [ripe(block)],
                 "entries": [{"type": "minecraft:item", "name": f"{NS}:{item}",
                              "functions": [fortune_bonus()]}]},
            ],
        })

    write_loot("echo_gourd", {
        "type": "minecraft:block",
        "pools": [{"rolls": 1.0, "functions": [EXPLOSION_DECAY],
                   "entries": [{"type": "minecraft:item", "name": f"{NS}:echo_gourd"}]}],
    })

    # Stems drop seeds on a per-age binomial, so an old stem is worth breaking
    # and a fresh one is not. p climbs by 1/15 per age, as vanilla does.
    for block in ("echo_gourd_stem", "attached_echo_gourd_stem"):
        if block == "echo_gourd_stem":
            functions = [{"function": "minecraft:set_count",
                          "count": {"type": "minecraft:binomial",
                                    "n": 3.0, "p": round((age + 1) / 15.0, 8)},
                          "conditions": [{"condition": "minecraft:block_state_property",
                                          "block": f"{NS}:{block}",
                                          "properties": {"age": str(age)}}]}
                         for age in range(8)]
        else:
            # The attached form has no age; vanilla gives it a flat binomial.
            functions = [{"function": "minecraft:set_count",
                          "count": {"type": "minecraft:binomial", "n": 3.0, "p": 0.53333336}}]
        write_loot(block, {
            "type": "minecraft:block",
            "pools": [{"rolls": 1.0, "functions": [EXPLOSION_DECAY],
                       "entries": [{"type": "minecraft:item",
                                    "name": f"{NS}:echo_gourd_seeds",
                                    "functions": functions}]}],
        })

    # Tilled soil breaks back into the moss it was cut from, exactly as vanilla
    # farmland breaks into dirt rather than into farmland.
    write_loot("void_farmland", {
        "type": "minecraft:block",
        "pools": [{"rolls": 1.0,
                   "conditions": [{"condition": "minecraft:survives_explosion"}],
                   "entries": [{"type": "minecraft:item",
                                "name": f"{NS}:resonance_moss"}]}],
    })


# ---------------------------------------------------------------------------
# recipes and tags
# ---------------------------------------------------------------------------

def gen_recipes() -> None:
    recipe = DATA / "recipe"
    # "misc", not "food". CraftingBookCategory has exactly four values -
    # building, redstone, equipment, misc - and an unknown one is not ignored:
    # the datapack reload logs "Couldn't parse data file ... Unknown element
    # name:food" and the recipe simply does not exist in the game. Vanilla's own
    # bread.json omits the field entirely, which defaults to misc.
    write_json(recipe / "resonant_bread.json", {
        "type": "minecraft:crafting_shaped",
        "category": "misc",
        "key": {"#": f"{NS}:resonant_grain"},
        "pattern": ["###"],
        "result": {"id": f"{NS}:resonant_bread"},
    })
    # A wild gourd is the entry point to the whole farm: it is the only piece a
    # player can obtain without already owning seeds.
    write_json(recipe / "echo_gourd_seeds.json", {
        "type": "minecraft:crafting_shapeless",
        "category": "misc",
        "ingredients": [f"{NS}:echo_gourd"],
        "result": {"id": f"{NS}:echo_gourd_seeds", "count": 4},
    })


def gen_tags() -> None:
    # The stems' support test is a tag, not an instanceof - see ModCrops.VOID_SOIL.
    write_json(DATA / "tags" / "block" / "void_farmland.json",
               {"replace": False, "values": [f"{NS}:void_farmland"]})

    # Merged rather than overwritten: gen_terrain_tags.py and gen_family_tags.py
    # own these same vanilla files, and whichever generator ran last would
    # otherwise erase the other's entries.
    merge_tag(ROOT / "src" / "main" / "resources" / "data" / "minecraft" / "tags"
              / "block" / "mineable" / "shovel.json", [f"{NS}:void_farmland"])
    merge_tag(ROOT / "src" / "main" / "resources" / "data" / "minecraft" / "tags"
              / "block" / "mineable" / "axe.json", [f"{NS}:echo_gourd"])


def merge_tag(path: Path, values: list[str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() \
        else {"replace": False, "values": []}
    existing = list(data.get("values", []))
    for v in values:
        if v not in existing:
            existing.append(v)
    data["values"] = existing
    data.setdefault("replace", False)
    write_json(path, data)


# ---------------------------------------------------------------------------
# lang
# ---------------------------------------------------------------------------

LANG = {
    "block.echoing_void.void_farmland": "Void Farmland",
    "block.echoing_void.resonant_wheat": "Resonant Wheat",
    "block.echoing_void.chime_roots": "Chime Roots",
    "block.echoing_void.void_tubers": "Void Tubers",
    "block.echoing_void.echo_gourd": "Echo Gourd",
    "block.echoing_void.echo_gourd_stem": "Echo Gourd Stem",
    "block.echoing_void.attached_echo_gourd_stem": "Attached Echo Gourd Stem",
    "item.echoing_void.void_farmland": "Void Farmland",
    "item.echoing_void.resonant_wheat_seeds": "Resonant Wheat Seeds",
    "item.echoing_void.resonant_grain": "Resonant Grain",
    "item.echoing_void.chime_root": "Chime Root",
    "item.echoing_void.void_tuber": "Void Tuber",
    "item.echoing_void.echo_gourd_seeds": "Echo Gourd Seeds",
    "item.echoing_void.echo_gourd": "Echo Gourd",
    "item.echoing_void.resonant_bread": "Resonant Bread",
}


def merge_lang() -> int:
    path = ASSETS / "lang" / "en_us.json"
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    added = 0
    for key, value in LANG.items():
        if key not in current:
            current[key] = value
            added += 1
    path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return added


# ---------------------------------------------------------------------------

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

    block_sprites: list[tuple[str, Sprite]] = []
    block_sprites += [(f"resonant_wheat_stage{n}", wheat_stage(n)) for n in range(8)]
    block_sprites += [(f"chime_roots_stage{n}", leafy_stage(n, TEAL, PALE))
                      for n in range(4)]
    block_sprites += [(f"void_tubers_stage{n}", leafy_stage(n, VIOLET, VIOLET, 0.55))
                      for n in range(4)]
    block_sprites += [
        ("echo_gourd_stem", gourd_stem_tex()),
        ("attached_echo_gourd_stem", attached_stem_tex()),
        ("echo_gourd_side", gourd_side()),
        ("echo_gourd_top", gourd_top()),
        ("void_farmland", farmland_top(SOIL, 2201, 1)),
        ("void_farmland_moist", farmland_top(SOIL_WET, 2207, 1)),
    ]

    item_sprites = [
        ("resonant_grain", resonant_grain()),
        ("resonant_wheat_seeds", seed_icon(GRAIN, 4401)),
        ("echo_gourd_seeds", seed_icon(TEAL, 4407)),
        ("chime_root", chime_root_icon()),
        ("void_tuber", void_tuber_icon()),
        ("resonant_bread", resonant_bread()),
    ]

    failures: list[str] = []
    for name, sp in block_sprites:
        img = sp.save(TEX_BLOCK / f"{name}.png")
        written.append(f"assets/{NS}/textures/block/{name}.png")
        n, top = stats(img)
        if not (5 <= n <= 16):
            failures.append(f"block/{name}: {n} colours, want 5-16")
        if top > 0.85:
            failures.append(f"block/{name}: dominant colour covers {top:.0%}")
    for name, sp in item_sprites:
        img = sp.save(TEX_ITEM / f"{name}.png")
        written.append(f"assets/{NS}/textures/item/{name}.png")
        n, top = stats(img)
        if not (5 <= n <= 16):
            failures.append(f"item/{name}: {n} colours, want 5-16")
        if top > 0.85:
            failures.append(f"item/{name}: dominant colour covers {top:.0%}")

    gen_models()
    gen_loot()
    gen_recipes()
    gen_tags()
    added = merge_lang()

    print(f"void farming: {len(block_sprites)} block sprites, "
          f"{len(item_sprites)} item sprites, {len(written)} files, "
          f"{added} new lang key(s)")
    if failures:
        print()
        print("FAILURES:")
        for f in failures:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

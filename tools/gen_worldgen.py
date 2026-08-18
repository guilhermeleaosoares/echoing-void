"""
The Echoing Void - worldgen data generator.

Emits the Hollow Horizon dimension, its THREE biomes and the multi-noise source
that distributes them, the density-function graph that shapes the terrain, the
ore and vegetation features, and the PLACEMENT of the two jigsaw structures -
the Outpost of the Tuners and the Tuner Encampment. Their pieces and template
pools come from tools/gen_structures.py, which runs immediately after this
generator; nothing here writes into worldgen/template_pool or data/<ns>/structure.

Every schema here was read out of real 26.2 sources and data, not memory. The
26.x dimension_type in particular is nothing like the 1.21 one: `ultrawarm`,
`natural`, `piglin_safe`, `bed_works`, `has_raids` and the old `effects` block
are all gone, replaced by a namespaced `attributes` map plus `skybox`,
`timelines` and `default_clock` (net/minecraft/world/level/dimension/
DimensionType.java).


THE FIVE PLAYER COMPLAINTS THIS ROUND, AND WHERE EACH IS ANSWERED
-----------------------------------------------------------------
1. "islands are almost completely vertical and blocky; they should be rugged,
   imperfect, natural and conical, with roughly matching holes in the ground
   beneath filled with debris"
       -> `thickness` / `base_offset` in gen_density_functions, and the
          asymmetric sky-island tent in `sky_islands.json`. See ISLAND SHAPE.
2. "strata and chalk formations seem random and too much - a cliff tens of
   blocks in radius all made of strata"
       -> `surface_rule`, specifically INTERBEDDING. See STRATA.
3. "trees generate too densely and consistently sometimes on top of each other"
       -> `tree_placement`. See TREES.
4. "the outpost has trees generating atop"
       -> the same `tree_placement`, via the natural-ground tag. See TREES.
5. "there should be multiple biomes ... large islands making up plains, then a
   biome where many smaller islands generate, higher and lower"
       -> `gen_biomes` plus the multi_noise source in `gen_dimension`.


THE BIOME SOURCE
----------------
The dimension used a `minecraft:fixed` biome source, so there was exactly one
biome and nothing could vary by region. It now uses `minecraft:multi_noise` with
a hand-authored parameter list, in the same spirit as vanilla's nether preset
(MultiNoiseBiomeSourceParameterList.Preset.NETHER, which maps five biomes on
two axes and leaves the other four at zero).

Climate.Sampler is built from the noise router in RandomState:101 as

    (temperature, vegetation, continents, erosion, depth, ridges)
 -> (temperature, humidity,   continentalness, erosion, depth, weirdness)

so the router fields `continents` and `erosion` ARE the climate axes named
`continentalness` and `erosion` in a parameter point. Both were 0.0 before,
which is the other half of why one biome covered everything: even a multi_noise
source would have sampled a constant climate.

Two axes carry the whole mapping, and both also drive the terrain graph, so the
biome a player is standing in and the terrain under their feet cannot disagree:

    continentalness  how much land there is        low -> archipelago, high -> continent
    erosion          how high the land sits        low -> mid altitude, high -> plateau

    shattered_octaves   continentalness [-1.00, -0.08]   erosion [-1.0,  1.00]
    resonant_plains     continentalness [-0.08,  1.00]   erosion [-1.0,  0.22]
    chalk_reaches       continentalness [-0.08,  1.00]   erosion [ 0.22, 1.00]


ISLAND SHAPE
------------
The old graph made `depth` the minimum of a top ramp and an upside-down base
ramp, and offset the base ramp by `0.9 * continentalness` - a LINEAR function of
the island mask. A linear underside is a wedge, and a wedge under a high
`factor` reads as a vertical slab, which is exactly what players saw.

The underside is now placed by thickness rather than by an independent ramp.
Both gradients run at the same slope (3.0 over 256 blocks = 85.33 blocks per
unit of offset), so

    base_offset = thickness - surface_offset

puts the underside exactly `85.33 * thickness` blocks below the top surface,
whatever altitude that surface happens to be at. `thickness` then rises FASTER
THAN LINEARLY with the island mask:

    m = clamp(mass, 0, 1)          r = clamp(1.8 * mass, 0, 1)
    thickness = 0.13 + 0.40 * mass + 0.34 * m^2 + 0.68 * r^4

    mass  -0.33  ->   0.00   the coastline: past here there is no land at all
    mass   0.00  ->   0.13   ~11 blocks: a thin, crumbling rim
    mass   0.30  ->   0.31   ~26 blocks
    mass   0.45  ->   0.60   ~51 blocks
    mass   0.56  ->   1.14   ~97 blocks: the root reaches the deep strata
    mass   1.00  ->   1.55  ~132 blocks: a root nearly to the world floor

Both curved terms take the clamped mass, not the raw one: an even power of a
negative number is positive, and feeding raw mass to them turned the thickness
positive again far out in the void, hanging three-block sheets of rock in the
open sky. Clamped, the negative half is purely linear, so land ends once.

A superlinear thickness under a smooth top surface is a cone: broad flat top,
underside plunging away far faster than the top rises, meeting the top at the
rim. `factor` also came down from 5.2 to 3.6 so base_3d_noise can break the
edges up instead of being squashed flat - high factor is what produced sheer
walls - and a 3D ridge term is added to the base ramp ONLY, so the underside is
ragged while the top stays walkable.

The floating band above the continent is built the same way but with explicit
limbs, because there is no `factor` to hide behind: a steep upper limb (3.55
over 12 blocks) gives a top that varies only ~4 blocks from rim to core, and a
shallow lower limb (3.30 over 60 blocks) gives an underside that varies ~24.
That ratio is the cone.

The matching hollow is exact rather than decorative: `sky_present` is the same
2D field that decides where a floating island exists, and it is subtracted from
`surface_offset`, so every island digs its own bowl in the ground below it.


STRATA
------
Bands still follow altitude, per docs/spec/art_direction.json. What changed is
that each band is INTERBEDDED with thin seams of its neighbours at fixed
altitudes. The complaint was a cliff tens of blocks across in a single colour,
and that is what a 40-block-thick band produces on a 40-block cliff no matter
how well its boundary is dithered. A 40-block cliff now crosses three or four
material changes, which is what makes rock read as geology rather than as paint.
The boundary dither also came down from 14 blocks to 5, because a 14-block fade
is wide enough to read as mush rather than as a contact.


TREES
-----
TreeFeature.getMaxFreeTreeHeight rejects a tree whose volume is occupied, but
`TrunkPlacer.isFree` returns true for anything in `#minecraft:logs`
(TrunkPlacer:119) and `TreeFeature.validTreePos` accepts everything in
`#minecraft:replaceable_by_trees`, which includes `#minecraft:leaves`. Trunks
may therefore legally grow through other trunks and through other canopies, and
the old placement asked for a `MOTION_BLOCKING` heightmap, which counts leaves -
so a second tree was routinely seeded on top of the first one's canopy. That is
the reported bug, precisely.

Vanilla's guard is `would_survive` on a sapling: a sapling does not survive on
planks or cobblestone, which is also why villages do not grow trees out of their
roofs. We have no saplings, so the equivalent guard is an explicit whitelist -
`#echoing_void:hollow_horizon_natural_ground` - tested one block below the
trunk. Structure walls, floors and roofs are worked stone and are not in it, so
a tree cannot root on the outpost; leaves and logs are not in it either, so a
tree cannot root on another tree.

Structures generate before features WITHIN a decoration step and the outpost is
at `surface_structures` (ordinal 4) while trees are at `vegetal_decoration`
(ordinal 9) - ChunkGenerator.applyBiomeDecoration:350-372 runs structures for
step N before features for step N - so the outpost's blocks are already in the
world when a tree is tested against them.

On top of that the placement demands a clear eight-block column and no log
within three blocks horizontally, and per-chunk counts are weighted lists whose
mean is around one tree per chunk.


STUB MODE
---------
Several blocks this worldgen references belong to other agents' registries this
round. `--stub-unregistered` swaps every unregistered id for a vanilla stand-in
so the dimension still loads and the terrain can be probed on a live server.
Normal runs emit the real ids and print a warning listing anything that is not
registered yet.

Run:  python tools/gen_worldgen.py [--stub-unregistered]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NS = "echoing_void"
DIM = "the_hollow_horizon"
STRUCT = "outpost_of_the_tuners"
ENCAMPMENT = "tuner_encampment"

BIOME_PLAINS = "resonant_plains"
BIOME_OCTAVES = "shattered_octaves"
BIOME_CHALK = "chalk_reaches"
BIOMES = (BIOME_PLAINS, BIOME_OCTAVES, BIOME_CHALK)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "main" / "resources" / "data"
MOD = DATA / NS
REGISTRY_DIR = ROOT / "src" / "main" / "java" / "com" / "echoingvoid" / "registry"
VANILLA = Path(r"C:\Projects\mcref-26.2\clientjar\data\minecraft")

written: list[str] = []
written_paths: set[Path] = set()

# Directories this generator owns outright. Anything left in them from a
# previous layout is deleted, because a datapack loads every file it finds: a
# stale biome json that still names a placed feature this run no longer emits
# fails registry load for the whole pack, and the failure names the stale file
# rather than the change that orphaned it.
# Deliberately narrow. worldgen/template_pool and data/<ns>/structure belong to
# tools/gen_structures.py, which runs straight after this generator in
# asset_gen.py and emits pieces this file knows nothing about; pruning there
# deletes another generator's output. worldgen/structure and structure_set are
# shared too - this file writes the placement, that one writes the pieces - so
# neither is pruned either.
OWNED_DIRS = (
    ("worldgen", "density_function"),
    ("worldgen", "biome"),
    ("worldgen", "configured_feature"),
    ("worldgen", "placed_feature"),
    ("worldgen", "noise_settings"),
)


def write(rel_path: Path, data: dict) -> None:
    rel_path.parent.mkdir(parents=True, exist_ok=True)
    rel_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(str(rel_path.relative_to(DATA)).replace("\\", "/"))
    written_paths.add(rel_path.resolve())


def prune_orphans() -> list[str]:
    removed: list[str] = []
    for parts in OWNED_DIRS:
        directory = MOD.joinpath(*parts)
        if not directory.is_dir():
            continue
        for stale in sorted(directory.rglob("*.json")):
            if stale.resolve() in written_paths:
                continue
            stale.unlink()
            removed.append(str(stale.relative_to(DATA)).replace("\\", "/"))
    return removed


# ---------------------------------------------------------------------------
# terrain tunables
#
# Altitudes are given in world coordinates; the dimension runs y=0..255.
# ---------------------------------------------------------------------------

WORLD_MIN_Y = 0
WORLD_HEIGHT = 256

# Both gradients run at the same rate - 3.0 over 256 blocks - so an offset of
# 1.0 is worth exactly BLOCKS_PER_UNIT blocks on either surface, and the top and
# the underside can be reasoned about in the same units.
TOP_GRADIENT = (1.5, 0, -1.5, WORLD_HEIGHT)
BASE_GRADIENT = (-1.5, 0, 1.5, WORLD_HEIGHT)
BLOCKS_PER_UNIT = WORLD_HEIGHT / 3.0     # 85.33

# Island mask. Continentalness carries it; the ridge term breaks the outline out
# of circles and the rim noise makes the coast irregular at a scale a player
# reads as erosion rather than as noise.
MASK_CONTINENT = 1.15
MASK_RIDGE = 0.34
MASK_RIDGE_BIAS = 0.42
MASK_RIM = 0.24

# Conical thickness, in offset units. See ISLAND SHAPE in the module docstring.
THICK_CONST = 0.13
THICK_LINEAR = 0.40
THICK_SQUARE = 0.34
# The root term. Quartic, and gated to positive mass so it cannot resurrect land
# out in the void where the linear term has already taken the thickness
# negative. This is what gives the largest islands a long tapering root instead
# of a flat sole - and it is also the only reason the deep strata exist at all:
# a probe of the previous tuning found nothing below y=106 anywhere, so the
# phonolite band, the humming crystal masses and Knell's y 0-34 seam had no rock
# to generate in.
THICK_ROOT = 0.68
# The root term saturates at ROOT_KNEE * mass = 1, so it is a large island that
# grows a root, not only a maximal one. A probe with no knee at all found the
# deepest rock anywhere in eight region files at y=104: mass reaches 1.0 too
# rarely for the deep strata to exist.
ROOT_KNEE = 1.8

# Where the top surface sits. Erosion is the altitude axis and is also the
# climate axis that separates Chalk Reaches from Resonant Plains, so a high
# plateau and the biome named after it are the same fact.
SURFACE_BIAS = -0.09
SURFACE_EROSION = 0.58
SURFACE_MASS = 0.22
SURFACE_FINE = 0.06

# Shattered Octaves. Where continentalness is low, a small-scale field is
# allowed to throw whole islands up and down, which is what makes the biome hard
# to cross. SHATTER_JITTER is in offset units: 0.45 is +/- 38 blocks.
SHATTER_PIVOT = 0.02
SHATTER_GAIN = 2.2
SHATTER_JITTER = 0.45
# Without this, Shattered Octaves is a biome with no islands in it. A region
# dump found 38 sampled columns in the biome and land in two of them: the
# continent mask falls below the coastline at continentalness ~ -0.27, while the
# biome runs out to -1.0, so three quarters of it was open void carrying a biome
# name. SHARD_GAIN lets a small-scale field push the mask back over the
# coastline in patches out there - which is what an archipelago is.
SHARD_GAIN = 0.75
SHARD_BIAS = 0.15

FACTOR_BASE = 3.6           # was 5.2; high factor is what made the walls sheer
FACTOR_EROSION = 1.9
BASE_ROUGHNESS = 0.16       # 3D ridge noise added to the underside only

# Cave generosity. Vanilla overworld uses cheese bias 0.27 and layer weight 4.0.
# Slightly tighter than the previous pass, because a thin conical island that is
# also hollow is a shell a player falls through.
CAVE_CHEESE_BIAS = 0.18
CAVE_LAYER_WEIGHT = 3.4

# Canyons along the zero contours of the ridge noise.
CHASM_WIDTH = 0.035
CHASM_STRENGTH = 16.0

# The floating band. Limb altitudes are absolute; see ISLAND SHAPE.
# A probe of the first tuning found a floating island over roughly half of all
# columns, which is a chalk ceiling rather than a feature. Rarer, with a harder
# mask falloff and less 3D smear on the footprint.
SKY_RARITY = 0.60
SKY_MASK_GAIN = 3.0
SKY_MASK_FLOOR = -2.2
SKY_MASK_CEIL = 1.30
SKY_TOP_FROM = (0.95, 208)
SKY_TOP_TO = (-2.60, 220)
SKY_BOTTOM_FROM = (-2.20, 150)
SKY_BOTTOM_TO = (1.10, 210)
SKY_ROUGHNESS = 0.62

# The matching ground hollow. Offset units convert at ~85 blocks per unit
# (TOP_GRADIENT spans 3.0 over 256), so SKY_HOLLOW 0.20 against a mask that
# peaks near 0.64 is a bowl about 11 blocks deep under the middle of an island.
#
# MEASURED FAILURE OF THE PREVIOUS TUNING: at 0.17 inside the clamped sum, a
# chunk-local control (open-sky columns vs under-island columns of the SAME
# chunk, 247 usable chunks) put the median dip at +0.0 blocks and found the
# ground HIGHER under the island in 49% of chunks. Two causes, both fixed here:
# the term was competing with SURFACE_MASS * island_mass for headroom under a
# 0.80 ceiling that the island-bearing columns were already saturating, so the
# subtraction was being clipped away; and HOLLOW_GAIN was 3.0, which made
# sky_present a near-binary mask - a step in a 2D offset field is a cliff ring
# in the terrain, not a bowl.
SKY_HOLLOW = 0.13

# WHERE THE HOLLOW MASK HAS TO START, derived rather than guessed.
#
# An island exists where the 2D mask clamp(SKY_MASK_GAIN * (cont - SKY_RARITY))
# plus the vertical tent clears zero. The tent peaks at ~+0.95 near y208, so the
# footprint runs out to mask == -0.95, i.e. all the way down to
# cont == SKY_RARITY - 0.95/SKY_MASK_GAIN == 0.28 - and further still where the
# 3D roughness helps, which is why TENT_REACH carries a little of it.
#
# The previous mask pivoted at SKY_RARITY itself, so it was zero across nearly
# the whole footprint and only bit under the rare cont > 0.6 cores. That is why
# raising SKY_HOLLOW and softening the gain both failed to move the median: the
# mask was not shallow, it was ABSENT everywhere the islands actually are.
# Measured: 4% of chunks dipped >= 8 blocks (the cores) while the median stayed
# at +0.0 and 47% of chunks still read HIGHER under the island.
TENT_REACH = 1.25
HOLLOW_PIVOT = SKY_RARITY - TENT_REACH / SKY_MASK_GAIN
# Full depth by the time the mask reaches zero, i.e. under the island's middle.
HOLLOW_GAIN = 1.0 / (SKY_RARITY - HOLLOW_PIVOT)

# Strata boundaries, matching docs/spec/art_direction.json.
BAND_DEEP_TOP = 30
BAND_PHONOLITE_TOP = 70
BAND_AMBER_TOP = 110
BAND_SLATE_TOP = 150
BAND_DITHER = 5             # was 14, which read as mush rather than as a contact
SEAM_DITHER = 3

# Chalk Reaches is meant to be pale, so its chalk starts lower than elsewhere.
BAND_SLATE_TOP_CHALK_BIOME = 132


# ---------------------------------------------------------------------------
# block ids
# ---------------------------------------------------------------------------

# Vanilla stand-ins used by --stub-unregistered. They are picked to be visually
# and structurally distinct from one another so a region dump can tell the
# strata apart while the real blocks are still being written.
STUBS = {
    "resonant_chalk": "minecraft:calcite",
    "echo_slate": "minecraft:deepslate",
    "amber_strata": "minecraft:terracotta",
    "humming_crystal": "minecraft:amethyst_block",
    "resonance_moss": "minecraft:moss_block",
    "chime_sand": "minecraft:sand",
    "amber_lichen": "minecraft:packed_mud",
    "bismuth_cluster": "minecraft:amethyst_cluster",
    "echo_sprout": "minecraft:end_rod",
    "chime_grass": "minecraft:lightning_rod",
    "crystal_bloom": "minecraft:torch",
    "amber_resonance_leaves": "minecraft:oak_leaves",
    "violet_resonance_leaves": "minecraft:cherry_leaves",
    "ashen_resonance_leaves": "minecraft:azalea_leaves",
    "humming_stem": "minecraft:warped_stem",
    "stripped_humming_stem": "minecraft:stripped_warped_stem",
    "amber_bough_log": "minecraft:acacia_log",
    "echo_ash_log": "minecraft:birch_log",
    "chalk_bricks": "minecraft:quartz_bricks",
    "polished_phonolite": "minecraft:polished_deepslate",
    "harmonic_lantern": "minecraft:sea_lantern",
    "phonolite_resonant_bismuth_ore": "minecraft:deepslate_diamond_ore",
    "phonolite_null_iron_ore": "minecraft:deepslate_iron_ore",
    "deepslate_null_iron_ore": "minecraft:deepslate_iron_ore",
    "knell_ore": "minecraft:ancient_debris",
}

_stub_mode = False
_registered: set[str] = set()
_missing: set[str] = set()


def load_registered_blocks() -> set[str]:
    """Block ids the registry package appears to register.

    Deliberately a broad literal scan rather than a match on
    `BLOCKS.register("...")`. Two of the registry classes register through local
    helpers - ModBlockFamilies calls strippableLog("echo_ash_log", ...) and
    barePillar(...), and its family builders assemble ids by string
    concatenation - so a scan for the literal register call reported
    echo_ash_log and amber_bough_log as missing when both are registered, which
    would have stubbed real blocks out of the world.

    The failure modes are asymmetric: a missed id gets stubbed and the wrong
    block appears, while an over-broad match only costs a warning we did not
    print. So this errs wide - every snake_case string literal in the package
    counts - and the family suffixes are expanded on top, since those ids never
    exist as literals at all.
    """
    found: set[str] = set()
    if not REGISTRY_DIR.exists():
        return found

    literal = re.compile(r'"([a-z][a-z0-9_]{2,})"')
    stone_family = re.compile(r'stoneFamily\(\s*"([a-z0-9_]+)"')
    wood_family = re.compile(r'woodFamily\(\s*"([a-z0-9_]+)"')

    for java in sorted(REGISTRY_DIR.glob("*.java")):
        src = java.read_text(encoding="utf-8")
        found |= set(literal.findall(src))
        for prefix in stone_family.findall(src):
            found |= {f"{prefix}_{v}" for v in ("slab", "stairs", "wall")}
        for prefix in wood_family.findall(src):
            found |= {f"{prefix}_{v}" for v in
                      ("planks", "slab", "stairs", "fence", "fence_gate",
                       "door", "trapdoor")}
    return found


def block_id(name: str) -> str:
    """Resolve one of our block ids, substituting a stand-in when asked to."""
    if name in _registered:
        return f"{NS}:{name}"
    _missing.add(name)
    if _stub_mode and name in STUBS:
        return STUBS[name]
    return f"{NS}:{name}"


def B(name: str, **props: str) -> dict:
    """A BlockState json object. Only ever the default state plus given props."""
    state: dict = {"Name": block_id(name)}
    if props:
        state["Properties"] = dict(props)
    return state


# ---------------------------------------------------------------------------
# density function DSL
#
# Field names verified against DensityFunctions.java: add/mul/min/max take
# argument1/argument2, clamp takes input/min/max, range_choice takes
# input/min_inclusive/max_exclusive/when_in_range/when_out_of_range,
# noise takes noise/xz_scale/y_scale, shifted_noise adds shift_x/shift_y/shift_z,
# y_clamped_gradient takes from_value/from_y/to_value/to_y, and every
# single-argument marker or mapped function takes "argument".
# ---------------------------------------------------------------------------

DF = str | float | int | dict

SHIFT_X = "minecraft:shift_x"
SHIFT_Z = "minecraft:shift_z"
BASE_3D = "minecraft:overworld/base_3d_noise"
ENTRANCES = "minecraft:overworld/caves/entrances"
SPAGHETTI_2D = "minecraft:overworld/caves/spaghetti_2d"
SPAGHETTI_ROUGH = "minecraft:overworld/caves/spaghetti_roughness_function"
PILLARS = "minecraft:overworld/caves/pillars"
NOODLE = "minecraft:overworld/caves/noodle"
Y = "minecraft:y"


def d_add(a: DF, b: DF) -> dict:
    return {"type": "minecraft:add", "argument1": a, "argument2": b}


def d_sum(*args: DF) -> DF:
    out = args[0]
    for a in args[1:]:
        out = d_add(out, a)
    return out


def d_mul(a: DF, b: DF) -> dict:
    return {"type": "minecraft:mul", "argument1": a, "argument2": b}


def d_min(a: DF, b: DF) -> dict:
    return {"type": "minecraft:min", "argument1": a, "argument2": b}


def d_max(a: DF, b: DF) -> dict:
    return {"type": "minecraft:max", "argument1": a, "argument2": b}


def d_wrap(kind: str, arg: DF) -> dict:
    return {"type": f"minecraft:{kind}", "argument": arg}


def d_clamp(arg: DF, lo: float, hi: float) -> dict:
    return {"type": "minecraft:clamp", "input": arg, "min": lo, "max": hi}


def d_range(arg: DF, lo: float, hi: float, inside: DF, outside: DF) -> dict:
    return {
        "type": "minecraft:range_choice",
        "input": arg,
        "min_inclusive": lo,
        "max_exclusive": hi,
        "when_in_range": inside,
        "when_out_of_range": outside,
    }


def d_ygrad(from_value: float, from_y: int, to_value: float, to_y: int) -> dict:
    return {
        "type": "minecraft:y_clamped_gradient",
        "from_value": from_value,
        "from_y": from_y,
        "to_value": to_value,
        "to_y": to_y,
    }


def d_noise(noise: str, xz_scale: float, y_scale: float = 0.0) -> dict:
    return {"type": "minecraft:noise", "noise": noise,
            "xz_scale": xz_scale, "y_scale": y_scale}


def d_shifted(noise: str, xz_scale: float, y_scale: float = 0.0) -> dict:
    return {
        "type": "minecraft:shifted_noise",
        "noise": noise,
        "shift_x": SHIFT_X,
        "shift_y": 0.0,
        "shift_z": SHIFT_Z,
        "xz_scale": xz_scale,
        "y_scale": y_scale,
    }


def d_flat2d(arg: DF) -> dict:
    """The vanilla idiom for a purely horizontal field: flat_cache(cache_2d(x))."""
    return d_wrap("flat_cache", d_wrap("cache_2d", arg))


def d_lerp(delta: DF, low: float, high: DF) -> dict:
    """lerp(delta, a, b) = a + delta * (b - a), with a constant.

    This is exactly how vanilla's `slide` serialises - see the y_clamped_gradient
    pairs at the head of floating_islands.json.
    """
    return d_add(low, d_mul(delta, d_add(high, -low)))


def d_slide(value: DF, *, top_start: int, top_end: int, top_target: float,
            bottom_start: int, bottom_end: int, bottom_target: float) -> dict:
    """NoiseRouterData.slide, transcribed.

    Forces the density to `top_target` above the top band and `bottom_target`
    below the bottom band, lerping across each, so the world neither welds
    itself to the build ceiling nor leaves a slab hanging at y=0.
    """
    top_factor = d_ygrad(1.0, WORLD_MIN_Y + WORLD_HEIGHT - top_start,
                         0.0, WORLD_MIN_Y + WORLD_HEIGHT - top_end)
    value = d_lerp(top_factor, top_target, value)
    bottom_factor = d_ygrad(0.0, WORLD_MIN_Y + bottom_start,
                            1.0, WORLD_MIN_Y + bottom_end)
    return d_lerp(bottom_factor, bottom_target, value)


def d_post_process(value: DF) -> dict:
    """NoiseRouterData.postProcess: squeeze(interpolated(0.64 * blend_density))."""
    return d_wrap("squeeze", d_wrap("interpolated",
                                    d_mul(0.64, d_wrap("blend_density", value))))


def ev(name: str) -> str:
    return f"{NS}:{name}"


# ---------------------------------------------------------------------------
# surface rule DSL  (SurfaceRules.java)
# ---------------------------------------------------------------------------

def s_seq(*rules: dict) -> dict:
    return {"type": "minecraft:sequence", "sequence": list(rules)}


def s_cond(if_true: dict, then_run: dict) -> dict:
    return {"type": "minecraft:condition", "if_true": if_true, "then_run": then_run}


def s_block(name: str, **props: str) -> dict:
    return {"type": "minecraft:block", "result_state": B(name, **props)}


def s_not(cond: dict) -> dict:
    # NotConditionSource serialises its target under "invert" (SurfaceRules:631).
    return {"type": "minecraft:not", "invert": cond}


def s_stone_depth(surface_type: str = "floor", offset: int = 0,
                  add_surface_depth: bool = False,
                  secondary_depth_range: int = 0) -> dict:
    return {
        "type": "minecraft:stone_depth",
        "add_surface_depth": add_surface_depth,
        "offset": offset,
        "secondary_depth_range": secondary_depth_range,
        "surface_type": surface_type,
    }


def s_biome(*ids: str) -> dict:
    return {"type": "minecraft:biome", "biome_is": [ev(b) for b in ids]}


def s_below(name: str, top_y: int, dither: int = BAND_DITHER) -> dict:
    """True at and below `top_y`, fading out over `dither` blocks above it.

    The randomised fade is what stops a strata boundary reading as a painted
    line; it is the same condition vanilla uses for stone-to-deepslate.
    """
    return {
        "type": "minecraft:vertical_gradient",
        "random_name": ev(name),
        "true_at_and_below": {"absolute": top_y},
        "false_at_and_above": {"absolute": top_y + dither},
    }


def s_seam(name: str, lo: int, hi: int, material: str) -> dict:
    """A thin interbedded layer of `material` between `lo` and `hi`.

    Both edges are dithered, so the seam has a ragged contact rather than two
    ruled lines. Seams are the answer to "a cliff tens of blocks across all made
    of one band": they force a tall rock face to cross three or four material
    changes, which is what makes it read as geology.
    """
    return s_cond(s_below(f"{name}_hi", hi, SEAM_DITHER),
                  s_cond(s_not(s_below(f"{name}_lo", lo, SEAM_DITHER)),
                         s_block(material)))


def s_noise(noise: str, lo: float, hi: float, is_3d: bool = False) -> dict:
    rule = {"type": "minecraft:noise_threshold", "noise": noise,
            "min_threshold": lo, "max_threshold": hi}
    if is_3d:
        rule["is_3d"] = True
    return rule


# ---------------------------------------------------------------------------
# block predicate DSL  (BlockPredicateType.java)
#
# StateTestingPredicate.stateTestingCodec gives every state test an optional
# "offset", limited to +/-16 by Vec3i.offsetCodec(16).
# ---------------------------------------------------------------------------

# MatchingBlockTagPredicate takes TagKey.codec, not TagKey.hashedCodec
# (MatchingBlockTagPredicate:13), so a block-predicate tag is a bare id with
# no leading '#'. The '#' form belongs to HolderSet fields such as
# VegetationPatchConfiguration.replaceable and to biome tag references.
NATURAL_GROUND = f"{NS}:hollow_horizon_natural_ground"
LOGS_TAG = "minecraft:logs"


def p_all(*preds: dict) -> dict:
    return {"type": "minecraft:all_of", "predicates": list(preds)}


def p_any(*preds: dict) -> dict:
    return {"type": "minecraft:any_of", "predicates": list(preds)}


def p_not(pred: dict) -> dict:
    return {"type": "minecraft:not", "predicate": pred}


def p_replaceable(offset: tuple[int, int, int] = (0, 0, 0)) -> dict:
    p = {"type": "minecraft:replaceable"}
    if offset != (0, 0, 0):
        p["offset"] = list(offset)
    return p


def p_solid(offset: tuple[int, int, int] = (0, 0, 0)) -> dict:
    p = {"type": "minecraft:solid"}
    if offset != (0, 0, 0):
        p["offset"] = list(offset)
    return p


def p_tag(tag: str, offset: tuple[int, int, int] = (0, 0, 0)) -> dict:
    p = {"type": "minecraft:matching_block_tag", "tag": tag}
    if offset != (0, 0, 0):
        p["offset"] = list(offset)
    return p


def m_filter(pred: dict) -> dict:
    return {"type": "minecraft:block_predicate_filter", "predicate": pred}


# ---------------------------------------------------------------------------
# dimension
# ---------------------------------------------------------------------------

def gen_dimension_type() -> None:
    write(MOD / "dimension_type" / f"{DIM}.json", {
        "ambient_light": 0.14,
        "attributes": {
            "minecraft:audio/ambient_sounds": {
                "mood": {
                    "block_search_extent": 8,
                    "offset": 2.0,
                    "sound": "minecraft:ambient.cave",
                    "tick_delay": 4800,
                }
            },
            "minecraft:audio/background_music": {
                "default": {
                    "max_delay": 28000,
                    "min_delay": 9000,
                    "replace_current_music": True,
                    "sound": "minecraft:music.end",
                }
            },
            "minecraft:gameplay/bed_rule": {
                "can_set_spawn": "never",
                "can_sleep": "never",
                "explodes": True,
            },
            "minecraft:gameplay/respawn_anchor_works": False,
            # The old fog was near-black, which is half of why the dimension
            # read as "all black". A cool slate haze lets the strata colours
            # survive at distance instead of being crushed to nothing.
            "minecraft:visual/ambient_light_color": "#3d4f63",
            "minecraft:visual/fog_color": "#232c3a",
            "minecraft:visual/sky_color": "#0d1420",
            "minecraft:visual/sky_light_color": "#00e5ff",
            "minecraft:visual/sky_light_factor": 0.0,
        },
        "coordinate_scale": 1.0,
        "default_clock": "minecraft:the_end",
        "has_ceiling": False,
        "has_ender_dragon_fight": False,
        "has_fixed_time": True,
        "has_skylight": True,
        "height": WORLD_HEIGHT,
        "infiniburn": "#minecraft:infiniburn_end",
        "logical_height": WORLD_HEIGHT,
        "min_y": WORLD_MIN_Y,
        "monster_spawn_block_light_limit": 0,
        "monster_spawn_light_level": 7,
        "skybox": "end",
        "timelines": "#minecraft:in_end",
    })


def climate(continentalness: tuple[float, float],
            erosion: tuple[float, float]) -> dict:
    """One Climate.ParameterPoint.

    Climate.Parameter.CODEC is ExtraCodecs.intervalCodec over floatRange(-2, 2),
    so a span is a two-element list and a point is a bare float. Only the two
    axes this dimension actually uses are given spans; the rest are pinned to
    zero exactly as the nether preset pins everything but temperature and
    humidity.
    """
    return {
        "temperature": 0.0,
        "humidity": 0.0,
        "continentalness": list(continentalness),
        "erosion": list(erosion),
        "depth": 0.0,
        "weirdness": 0.0,
        "offset": 0.0,
    }


def gen_dimension() -> None:
    write(MOD / "dimension" / f"{DIM}.json", {
        "type": ev(DIM),
        "generator": {
            "type": "minecraft:noise",
            "settings": ev("hollow_horizon"),
            "biome_source": {
                "type": "minecraft:multi_noise",
                "biomes": [
                    {"biome": ev(BIOME_OCTAVES),
                     "parameters": climate((-1.0, -0.08), (-1.0, 1.0))},
                    {"biome": ev(BIOME_PLAINS),
                     "parameters": climate((-0.08, 1.0), (-1.0, 0.22))},
                    {"biome": ev(BIOME_CHALK),
                     "parameters": climate((-0.08, 1.0), (0.22, 1.0))},
                ],
            },
        },
    })


# ---------------------------------------------------------------------------
# density functions
# ---------------------------------------------------------------------------

def gen_density_functions() -> None:
    df = MOD / "worldgen" / "density_function"

    # ---- horizontal fields -------------------------------------------------
    # xz_scale multiplies the sample coordinate, so a larger number means
    # smaller features. Vanilla samples continentalness at 0.25 for
    # thousand-block continents; 0.62 gives landmasses a few hundred blocks
    # across, which is the scale at which a player sees open sky in one glance
    # and still has somewhere to walk.
    write(df / "continents.json",
          d_flat2d(d_shifted("minecraft:continentalness", 0.62)))
    write(df / "erosion.json",
          d_flat2d(d_shifted("minecraft:erosion", 0.85)))
    write(df / "ridges.json",
          d_flat2d(d_shifted("minecraft:ridge", 1.05)))
    # Coast detail: fine enough to make an outline irregular, coarse enough not
    # to read as static.
    write(df / "rim.json",
          d_flat2d(d_shifted("minecraft:surface", 1.35)))
    # The island-cell field for Shattered Octaves. Small features, so a player
    # crossing the biome meets a new island every thirty or forty blocks.
    write(df / "cells.json",
          d_flat2d(d_shifted("minecraft:continentalness", 4.6)))
    # A second small-scale field, deliberately NOT the one that sets island
    # heights: if the same noise decided both where an island is and how high it
    # sits, every island in the biome would be the same height as its neighbour
    # of the same size.
    write(df / "shard_noise.json",
          d_flat2d(d_shifted("minecraft:ridge", 3.4)))

    # ---- island mask -------------------------------------------------------
    # > 0 means there is land in this column at all. Everything about island
    # shape is a function of this one field.
    write(df / "island_mass.json", d_flat2d(d_clamp(
        d_sum(
            d_mul(MASK_CONTINENT, ev("continents")),
            d_mul(MASK_RIDGE, d_add(-MASK_RIDGE_BIAS, d_wrap("abs", ev("ridges")))),
            d_mul(MASK_RIM, ev("rim")),
            # Only bites where continentalness is low, because `shatter` is
            # zero everywhere else. This is what puts islands in Shattered
            # Octaves rather than a biome label on empty sky.
            d_mul(ev("shatter"),
                  d_mul(SHARD_GAIN, d_add(SHARD_BIAS, ev("shard_noise")))),
        ), -1.0, 1.0)))

    # How hard a floating island is present overhead, 0..1. Used twice: once to
    # build the island, once to dig the matching hollow in the ground below it.
    # 0 at the island's outer edge, 1 under its middle. Pivoted on
    # HOLLOW_PIVOT, not SKY_RARITY: see the derivation above.
    write(df / "sky_present.json", d_flat2d(d_clamp(
        d_mul(HOLLOW_GAIN,
              d_add(-HOLLOW_PIVOT, d_shifted("minecraft:continentalness", 2.35))),
        0.0, 1.0)))

    # Vertical scatter, gated on low continentalness so it only bites in
    # Shattered Octaves. This is the whole difference between "large connected
    # islands" and "many smaller islands, higher and lower".
    write(df / "shatter.json", d_flat2d(d_clamp(
        d_mul(SHATTER_GAIN, d_add(SHATTER_PIVOT, d_mul(-1.0, ev("continents")))),
        0.0, 1.0)))
    write(df / "height_jitter.json", d_flat2d(
        d_mul(ev("shatter"), d_mul(SHATTER_JITTER, ev("cells")))))

    # ---- the two surfaces --------------------------------------------------
    # The hollow is subtracted AFTER the clamp, not inside it. Inside, it shared
    # a ceiling with SURFACE_MASS * island_mass - and island_mass is high in
    # exactly the columns an island floats over, so the two terms fought over
    # the same headroom and the clamp threw the difference away. Outside, the
    # bowl is cut at its full depth no matter how saturated the terrain terms
    # are. base_offset is thickness - surface_offset, so the underside follows
    # the top down and the ground slab keeps its thickness instead of thinning
    # into a shell.
    write(df / "surface_offset.json", d_flat2d(d_add(
        d_clamp(
            d_sum(
                SURFACE_BIAS,
                d_mul(SURFACE_EROSION, ev("erosion")),
                d_mul(SURFACE_MASS, ev("island_mass")),
                ev("height_jitter"),
                d_mul(SURFACE_FINE, ev("rim")),
            ), -1.30, 0.80),
        d_mul(-SKY_HOLLOW, ev("sky_present")))))

    # Thickness, quadratic in the island mask. This is the cone.
    # Both curved terms take clamp(mass, 0, 1) rather than mass. An even power
    # of a negative number is positive, so feeding raw mass to them turned the
    # thickness positive again far out in the void and hung 3-block sheets of
    # rock in the deep sky. Clamped, the negative half is purely linear and the
    # land ends once and stays ended.
    solid_mass = d_clamp(ev("island_mass"), 0.0, 1.0)
    write(df / "thickness.json", d_flat2d(d_sum(
        THICK_CONST,
        d_mul(THICK_LINEAR, ev("island_mass")),
        d_mul(THICK_SQUARE, d_wrap("square", solid_mass)),
        d_mul(THICK_ROOT, d_wrap("square", d_wrap("square", d_clamp(
            d_mul(ROOT_KNEE, ev("island_mass")), 0.0, 1.0)))),
    )))

    # Both gradients share a slope, so subtracting the surface offset from the
    # thickness puts the underside exactly `thickness` units below the top
    # wherever the top happens to be.
    write(df / "base_offset.json", d_flat2d(
        d_add(ev("thickness"), d_mul(-1.0, ev("surface_offset")))))

    # Terrain steepness. High factor squashes the ramp into cliffs and plateaus
    # and hides base_3d_noise, which is what made the old islands sheer; this is
    # deliberately low, and rises with erosion so the plateau biome is the only
    # place that gets genuine cliff faces.
    write(df / "factor.json", d_flat2d(
        d_add(FACTOR_BASE, d_mul(FACTOR_EROSION, ev("erosion")))))

    # The two-sided depth field. The 3D ridge term is added to the BASE ramp
    # only, so the underside of every island is ragged while the top a player
    # walks on stays coherent.
    write(df / "depth.json", d_min(
        d_add(d_ygrad(*TOP_GRADIENT), ev("surface_offset")),
        d_sum(d_ygrad(*BASE_GRADIENT), ev("base_offset"),
              d_mul(BASE_ROUGHNESS, d_noise("minecraft:ridge", 1.6, 0.9))),
    ))

    write(df / "sloped_cheese.json", d_add(
        d_mul(4.0, d_wrap("quarter_negative", d_mul(ev("depth"), ev("factor")))),
        BASE_3D,
    ))

    # NoiseRouterData.underground, with the cheese bias and cavern-layer weight
    # loosened so the interior of the continent is walkable cavern rather than
    # the overworld's tighter warren.
    layered = d_mul(CAVE_LAYER_WEIGHT,
                    d_wrap("square", d_noise("minecraft:cave_layer", 8.0)))
    solidified = d_add(
        d_clamp(d_add(CAVE_CHEESE_BIAS,
                      d_noise("minecraft:cave_cheese", 0.6666666666666666)),
                -1.0, 1.0),
        d_clamp(d_add(1.5, d_mul(-0.64, ev("sloped_cheese"))), 0.0, 0.5),
    )
    write(df / "underground.json", d_max(
        d_min(d_min(d_add(layered, solidified), ENTRANCES),
              d_add(SPAGHETTI_2D, SPAGHETTI_ROUGH)),
        d_range(PILLARS, -1000000.0, 0.03, -1000000.0, PILLARS),
    ))

    write(df / "caves.json", d_range(
        ev("sloped_cheese"), -1000000.0, 1.5625,
        d_min(ev("sloped_cheese"), d_mul(5.0, ENTRANCES)),
        ev("underground"),
    ))

    # Full-height canyons along the zero contours of the ridge noise. Outside a
    # canyon this term is ~16, far above any density that could turn solid rock
    # into air, so it only ever bites where it is meant to.
    write(df / "chasms.json", d_flat2d(d_mul(
        CHASM_STRENGTH,
        d_add(-CHASM_WIDTH, d_wrap("abs", d_shifted("minecraft:ridge", 1.45))))))

    # ---- the floating band -------------------------------------------------
    # A horizontal mask ADDED to a vertical tent. Adding rather than min-ing is
    # what makes these conical: as the tent falls away below the island the sum
    # only stays positive where the mask is strongly positive, so the footprint
    # shrinks with depth. The limbs are deliberately asymmetric - 3.55 over 12
    # blocks above, 3.30 over 60 below - so the top is nearly flat and the
    # underside tapers over four times as far.
    write(df / "sky_islands.json", d_sum(
        d_flat2d(d_clamp(d_mul(SKY_MASK_GAIN,
                               d_add(-SKY_RARITY,
                                     d_shifted("minecraft:continentalness", 2.35))),
                         SKY_MASK_FLOOR, SKY_MASK_CEIL)),
        d_min(d_ygrad(SKY_TOP_FROM[0], SKY_TOP_FROM[1],
                      SKY_TOP_TO[0], SKY_TOP_TO[1]),
              d_ygrad(SKY_BOTTOM_FROM[0], SKY_BOTTOM_FROM[1],
                      SKY_BOTTOM_TO[0], SKY_BOTTOM_TO[1])),
        d_mul(SKY_ROUGHNESS, BASE_3D),
    ))


# ---------------------------------------------------------------------------
# noise settings
# ---------------------------------------------------------------------------

def strata_column(slate_top: int) -> dict:
    """The rock column below the skin, low to high, with interbedded seams.

    Order matters: the sequence is evaluated top-down and the first matching
    rule wins, so seams are listed before the bulk band they sit inside.
    """
    deep_stone = s_seq(
        s_cond(s_noise("minecraft:patch", 0.72, 4.0, is_3d=True),
               s_block("humming_crystal")),
        s_block("raw_phonolite"),
    )
    return s_seq(
        s_cond(s_below("band_deep", BAND_DEEP_TOP), deep_stone),
        s_cond(s_below("band_phonolite", BAND_PHONOLITE_TOP), s_seq(
            s_seam("seam_phon_amber", 55, 58, "amber_strata"),
            s_seam("seam_phon_slate", 40, 42, "echo_slate"),
            s_block("raw_phonolite"),
        )),
        s_cond(s_below("band_amber", BAND_AMBER_TOP), s_seq(
            s_seam("seam_amber_slate", 96, 99, "echo_slate"),
            s_seam("seam_amber_phon", 80, 82, "raw_phonolite"),
            s_block("amber_strata"),
        )),
        s_cond(s_below("band_slate", slate_top), s_seq(
            s_seam("seam_slate_chalk", 141, 143, "resonant_chalk"),
            s_seam("seam_slate_amber", 126, 129, "amber_strata"),
            s_block("echo_slate"),
        )),
        s_seq(
            s_seam("seam_chalk_slate_hi", 176, 178, "echo_slate"),
            s_seam("seam_chalk_slate_lo", 160, 162, "echo_slate"),
            s_block("resonant_chalk"),
        ),
    )


def surface_skin(biome: str, slate_top: int) -> dict:
    """The top block of every solid run, including cave floors and ledges.

    Each biome gets its own emphasis here, which is the third axis (after
    vegetation and mob weights) on which the three read differently.
    """
    if biome == BIOME_PLAINS:
        # Forgiving and alive: moss and lichen on anything walkable.
        high = s_seq(
            s_cond(s_noise("minecraft:surface", -0.55, 4.0), s_block("resonance_moss")),
            s_block("resonant_chalk"),
        )
        mid = s_seq(
            s_cond(s_noise("minecraft:surface", -0.35, 4.0), s_block("resonance_moss")),
            s_cond(s_noise("minecraft:surface_secondary", 0.55, 4.0), s_block("chime_sand")),
            s_block("echo_slate"),
        )
        amber = s_seq(
            s_cond(s_noise("minecraft:surface", -4.0, 0.35), s_block("amber_lichen")),
            s_block("amber_strata"),
        )
    elif biome == BIOME_OCTAVES:
        # Bare and hostile: almost no ground cover, crystal breaking through.
        high = s_seq(
            s_cond(s_noise("minecraft:patch", 0.55, 4.0, is_3d=True),
                   s_block("humming_crystal")),
            s_block("resonant_chalk"),
        )
        mid = s_seq(
            s_cond(s_noise("minecraft:patch", 0.60, 4.0, is_3d=True),
                   s_block("humming_crystal")),
            s_cond(s_noise("minecraft:surface", 0.55, 4.0), s_block("resonance_moss")),
            s_block("echo_slate"),
        )
        amber = s_seq(
            s_cond(s_noise("minecraft:surface", -4.0, -0.20), s_block("amber_lichen")),
            s_block("amber_strata"),
        )
    else:  # BIOME_CHALK
        # Pale and dusty: chime sand drifts across the plateaus.
        high = s_seq(
            s_cond(s_noise("minecraft:surface_secondary", 0.10, 4.0),
                   s_block("chime_sand")),
            s_cond(s_noise("minecraft:surface", -0.70, 4.0), s_block("resonance_moss")),
            s_block("resonant_chalk"),
        )
        mid = s_seq(
            s_cond(s_noise("minecraft:surface_secondary", 0.25, 4.0),
                   s_block("chime_sand")),
            s_block("echo_slate"),
        )
        amber = s_seq(
            s_cond(s_noise("minecraft:surface", -4.0, 0.10), s_block("amber_lichen")),
            s_block("amber_strata"),
        )

    deep_stone = s_seq(
        s_cond(s_noise("minecraft:patch", 0.72, 4.0, is_3d=True),
               s_block("humming_crystal")),
        s_block("raw_phonolite"),
    )
    return s_seq(
        s_cond(s_below("skin_deep", BAND_DEEP_TOP), deep_stone),
        s_cond(s_below("skin_phonolite", BAND_PHONOLITE_TOP), s_seq(
            s_cond(s_noise("minecraft:surface_secondary", 0.50, 4.0),
                   s_block("chime_sand")),
            s_block("raw_phonolite"),
        )),
        s_cond(s_below("skin_amber", BAND_AMBER_TOP), amber),
        s_cond(s_below("skin_slate", slate_top), mid),
        high,
    )


def surface_rule() -> dict:
    """Paint the whole rock column by altitude, per biome.

    SurfaceSystem.buildSurface walks every column from WORLD_SURFACE_WG down to
    min_y and applies this rule to every block that is still the default block,
    so altitude bands here colour the interior of the continent and the walls of
    every canyon, not just the skin.
    """
    def for_biome(biome: str, slate_top: int) -> dict:
        return s_cond(s_biome(biome), s_seq(
            s_cond(s_stone_depth("floor"), surface_skin(biome, slate_top)),
            strata_column(slate_top),
        ))

    return s_seq(
        for_biome(BIOME_CHALK, BAND_SLATE_TOP_CHALK_BIOME),
        for_biome(BIOME_OCTAVES, BAND_SLATE_TOP),
        for_biome(BIOME_PLAINS, BAND_SLATE_TOP),
        # Fallback for anything the biome conditions somehow miss, so no column
        # can ever be left as bare default block.
        s_cond(s_stone_depth("floor"), surface_skin(BIOME_PLAINS, BAND_SLATE_TOP)),
        strata_column(BAND_SLATE_TOP),
    )


def gen_noise_settings() -> None:
    terrain = d_max(d_min(ev("caves"), ev("chasms")), ev("sky_islands"))
    slid = d_slide(terrain,
                   top_start=20, top_end=6, top_target=-0.35,
                   bottom_start=2, bottom_end=20, bottom_target=-0.35)
    final_density = d_min(d_post_process(slid), NOODLE)

    write(MOD / "worldgen" / "noise_settings" / "hollow_horizon.json", {
        "aquifers_enabled": False,
        "default_block": B("raw_phonolite"),
        "default_fluid": {"Name": "minecraft:air"},
        "disable_mob_generation": False,
        "legacy_random_source": False,
        # cell 4 x 8 x 4, the overworld's own resolution - floating_islands used
        # 8 x 4 x 8, which is part of why its terrain came out so lumpy.
        "noise": {
            "height": WORLD_HEIGHT,
            "min_y": WORLD_MIN_Y,
            "size_horizontal": 1,
            "size_vertical": 2,
        },
        # continents and erosion are not decoration here: RandomState:101 feeds
        # them straight into Climate.Sampler as continentalness and erosion, so
        # these two lines are what make the multi_noise biome source work at all.
        "noise_router": {
            "barrier": 0.0,
            "continents": ev("continents"),
            "depth": 0.0,
            "erosion": ev("erosion"),
            "final_density": final_density,
            "fluid_level_floodedness": 0.0,
            "fluid_level_spread": 0.0,
            "lava": 0.0,
            "preliminary_surface_level": 0.0,
            "ridges": ev("ridges"),
            "temperature": 0.0,
            "vegetation": 0.0,
            "vein_gap": 0.0,
            "vein_ridged": 0.0,
            "vein_toggle": 0.0,
        },
        "ore_veins_enabled": False,
        "sea_level": 0,
        "spawn_target": [climate((0.10, 1.0), (-1.0, 0.22))],
        "surface_rule": surface_rule(),
    })


# ---------------------------------------------------------------------------
# biomes
# ---------------------------------------------------------------------------

# GenerationStep.Decoration ordinals (GenerationStep.java): 6 UNDERGROUND_ORES,
# 7 UNDERGROUND_DECORATION, 9 VEGETAL_DECORATION, 10 TOP_LAYER_MODIFICATION.
STEP_ORES = 6
STEP_UNDERGROUND = 7
STEP_VEGETAL = 9
STEP_TOP = 10


def spawner(entity: str, low: int, high: int, weight: int) -> dict:
    # camelCase minCount/maxCount is real here, inconsistent with the snake_case
    # elsewhere in worldgen but that is what SpawnerData decodes.
    return {"type": ev(entity), "minCount": low, "maxCount": high, "weight": weight}


def spawn_cost(entity: str, charge: float, budget: float) -> tuple[str, dict]:
    """MobSpawnSettings.MobSpawnCost - the potential-energy cap.

    PLAYER COMPLAINT: "the mobs are overwhelming as they spawn so many
    together". Weight and maxCount only shape one roll; this caps the STANDING
    population. NaturalSpawner charges `charge` per live mob against a budget of
    `energy_budget` computed from the surrounding density field, and refuses the
    spawn once the budget is spent - which is exactly how vanilla stops Soul Sand
    Valley filling up with skeletons. Without it, a run of lucky rolls still
    produces a nest however small the group size is.
    """
    return ev(entity), {"charge": charge, "energy_budget": budget}


def write_biome(name: str, *, fog: str, foliage: str, grass: str,
                monsters: list[dict], costs: list[tuple[str, dict]],
                ores: list[str], underground: list[str],
                vegetal: list[str], top: list[str],
                ambient: list[dict] | None = None) -> None:
    """Write one biome.

    `ambient` is the MobCategory.AMBIENT bucket and is separate from `monsters`
    on purpose. AMBIENT mobs are counted against the bat's own per-chunk cap, so
    anything listed here cannot consume the hostile budget - a cave full of
    chime motes still gets its monsters. Defaults to empty, which is what every
    biome had hardcoded before.
    """
    features: list[list[str]] = [[] for _ in range(11)]
    features[STEP_ORES] = ores
    features[STEP_UNDERGROUND] = underground
    features[STEP_VEGETAL] = vegetal
    features[STEP_TOP] = top

    write(MOD / "worldgen" / "biome" / f"{name}.json", {
        "carvers": [],
        "downfall": 0.0,
        # In 26.2 biome "effects" accepts ONLY water_color / foliage_color /
        # dry_foliage_color / grass_color / grass_color_modifier. Fog, sky and
        # water-fog colours moved to the biome-level "attributes" map, and
        # putting them back in "effects" fails the decode outright.
        "effects": {
            "water_color": "#1b3b47",
            "foliage_color": foliage,
            "grass_color": grass,
        },
        "attributes": {
            "minecraft:visual/fog_color": fog,
            "minecraft:visual/water_fog_color": "#0a141a",
        },
        "features": features,
        "has_precipitation": False,
        "spawn_costs": dict(costs),
        "spawners": {
            "ambient": ambient or [],
            "axolotls": [],
            "creature": [],
            "misc": [],
            "monster": monsters,
            "underground_water_creature": [],
            "water_ambient": [],
            "water_creature": [],
        },
        "temperature": 0.4,
    })


# Namespaced, like every other feature list: a bare id in a biome's features
# array decodes as minecraft:<id> and fails registry load.
COMMON_ORES = [
    ev("ore_phonolite_resonant_bismuth_placed"),
    ev("ore_phonolite_null_iron_placed"),
    ev("ore_knell_placed"),
    ev("humming_crystal_vein_placed"),
]


def gen_biomes() -> None:
    # ---- Resonant Plains ---------------------------------------------------
    # The forgiving biome. Broad connected tops, amber groves, thick ground
    # cover, and the weakest of the three monsters as the common spawn.
    write_biome(
        BIOME_PLAINS,
        fog="#28303e", foliage="#c89b4a", grass="#3fd0e0",
        # A player should meet a weaver, not a nest of them. Group size 1-2,
        # and the total monster weight across the biome is 11 where it used to
        # be 41.
        monsters=[
            spawner("echo_weaver", 1, 2, 6),
            spawner("resonance_wraith", 1, 1, 2),
            # Both newcomers are the UNCOMMON spawn here. The shade wants gaps
            # to blink across and the burrower wants open rock, and plains is
            # the forgiving biome, so neither gets to own it.
            spawner("tuner_shade", 1, 1, 2),
            spawner("strata_burrower", 1, 1, 1),
        ],
        ambient=[spawner("chime_mote", 1, 3, 10)],
        costs=[
            spawn_cost("echo_weaver", 0.9, 0.14),
            spawn_cost("resonance_wraith", 1.0, 0.10),
            spawn_cost("tuner_shade", 0.9, 0.08),
            spawn_cost("strata_burrower", 1.0, 0.08),
        ],
        ores=COMMON_ORES,
        underground=[
            ev("bismuth_cluster_placed"),
            ev("chime_sand_hollow_placed"),
            ev("cavern_ground_cover_placed"),
            ev("cavern_debris_placed"),
        ],
        vegetal=[
            ev("amber_bough_grove_placed"),
            ev("petrified_grove_placed"),
            ev("ground_cover_placed"),
            ev("chime_grass_meadow_placed"),
        ],
        top=[ev("island_debris_placed")],
    )

    # ---- Shattered Octaves -------------------------------------------------
    # Deliberately hard. Sparse vegetation so there is nothing to break a fall,
    # and the flier is the common spawn because it does not care about the gaps.
    write_biome(
        BIOME_OCTAVES,
        fog="#1b2130", foliage="#b14a9e", grass="#5a2e6b",
        monsters=[
            spawner("resonance_wraith", 1, 2, 5),
            # The shade is COMMON here: blinking reads at its best across the
            # gaps, and it is the one hostile that the broken ground flatters.
            spawner("tuner_shade", 1, 1, 4),
            spawner("strata_golem", 1, 1, 1),
            spawner("echo_weaver", 1, 1, 1),
        ],
        ambient=[spawner("chime_mote", 1, 3, 10)],
        costs=[
            spawn_cost("resonance_wraith", 0.9, 0.14),
            spawn_cost("tuner_shade", 0.9, 0.12),
            # the golem is a setpiece, not a crowd - one is an encounter
            spawn_cost("strata_golem", 1.0, 0.07),
            spawn_cost("echo_weaver", 1.0, 0.08),
        ],
        ores=COMMON_ORES,
        underground=[
            ev("bismuth_cluster_dense_placed"),
            ev("cavern_debris_placed"),
        ],
        vegetal=[
            ev("humming_grove_placed"),
            ev("sparse_ground_cover_placed"),
        ],
        top=[ev("island_debris_placed")],
    )

    # ---- Chalk Reaches -----------------------------------------------------
    # High and pale. Echo Ash groves, chime sand drifts, and the golem as the
    # common spawn because it belongs to the rock.
    write_biome(
        BIOME_CHALK,
        fog="#3a4557", foliage="#c9d3e2", grass="#a8b4c8",
        monsters=[
            spawner("strata_golem", 1, 1, 3),
            # The burrower is COMMON here: the ambush needs broad walkable rock
            # to surface out of, which is what the reaches are made of.
            spawner("strata_burrower", 1, 1, 3),
            spawner("echo_weaver", 1, 1, 1),
        ],
        ambient=[spawner("chime_mote", 1, 3, 10)],
        costs=[
            spawn_cost("strata_golem", 1.0, 0.09),
            spawn_cost("strata_burrower", 1.0, 0.12),
            spawn_cost("echo_weaver", 1.0, 0.10),
        ],
        ores=COMMON_ORES,
        underground=[
            ev("bismuth_cluster_placed"),
            ev("chime_sand_hollow_placed"),
            ev("cavern_ground_cover_placed"),
        ],
        vegetal=[
            ev("echo_ash_grove_placed"),
            ev("ground_cover_placed"),
            ev("chime_sand_drift_placed"),
        ],
        top=[ev("island_debris_placed")],
    )


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------

CARVABLE = f"#{NS}:hollow_horizon_carvable"


def _ore(state: dict, size: int, discard: float = 0.0,
         tag: str = f"{NS}:hollow_horizon_carvable") -> dict:
    return {
        "type": "minecraft:ore",
        "config": {
            "discard_chance_on_air_exposure": discard,
            "size": size,
            "targets": [{
                "state": state,
                "target": {"predicate_type": "minecraft:tag_match", "tag": tag},
            }],
        },
    }


def _uniform(lo: int, hi: int) -> dict:
    return {"type": "minecraft:uniform",
            "min_inclusive": {"absolute": lo},
            "max_inclusive": {"absolute": hi}}


def _weighted_count(*pairs: tuple[int, int]) -> dict:
    """An IntProvider that is a weighted list of fixed counts.

    This is how vanilla caps tree density - trees_plains is 19:1 weighted
    between 0 and 1 trees per chunk - and it is a far harder cap than a uniform
    range, because most chunks draw zero.
    """
    return {"type": "minecraft:weighted_list",
            "distribution": [{"data": d, "weight": w} for d, w in pairs]}


def _tree(trunk: str, leaves: str, below: str, base: int, rand_a: int,
          radius: int, height: int, *, placer: str = "straight_trunk_placer",
          foliage: str = "blob_foliage_placer") -> dict:
    trunk_placer = {"type": f"minecraft:{placer}", "base_height": base,
                    "height_rand_a": rand_a, "height_rand_b": 2}
    if placer == "forking_trunk_placer":
        # ForkingTrunkPlacer takes the same three fields; kept explicit so the
        # difference between species is visible here rather than implied.
        pass
    foliage_placer: dict = {"type": f"minecraft:{foliage}",
                            "radius": radius, "offset": 0}
    if foliage in ("blob_foliage_placer", "bush_foliage_placer"):
        foliage_placer["height"] = height
    elif foliage == "spruce_foliage_placer":
        foliage_placer["trunk_height"] = {"type": "minecraft:uniform",
                                          "min_inclusive": 1, "max_inclusive": 2}
    return {
        "type": "minecraft:tree",
        "config": {
            "ignore_vines": True,
            # 26.2 replaced force_dirt/dirt_provider with a required
            # below_trunk_provider - the block laid under the trunk.
            "below_trunk_provider": {
                "type": "minecraft:rule_based_state_provider",
                "rules": [{
                    "if_true": {
                        "type": "minecraft:not",
                        "predicate": {
                            "type": "minecraft:matching_block_tag",
                            "tag": "minecraft:cannot_replace_below_tree_trunk",
                        },
                    },
                    "then": {
                        "type": "minecraft:simple_state_provider",
                        "state": B(below),
                    },
                }],
            },
            "trunk_provider": {"type": "minecraft:simple_state_provider",
                               "state": B(trunk, axis="y")},
            "foliage_provider": {"type": "minecraft:simple_state_provider",
                                 "state": B(leaves)},
            "trunk_placer": trunk_placer,
            "foliage_placer": foliage_placer,
            "minimum_size": {"type": "minecraft:two_layers_feature_size",
                             "limit": 1, "lower_size": 0, "upper_size": 2},
            "decorators": [],
        },
    }


def tree_placement(count: dict | int, *, clear_height: int = 8,
                   spacing: int = 3, rarity: int | None = None) -> list[dict]:
    """The placement chain every grove uses. See TREES in the module docstring.

    Three guards, in order of what they answer:

    * ground whitelist - a trunk may only root on natural terrain, which is what
      keeps trees off the outpost's roof and off other trees.
    * clear column - `clear_height` replaceable blocks straight up, so a trunk
      cannot start inside anything.
    * spacing ring - no block of `#minecraft:logs` within `spacing` blocks
      horizontally at trunk height. TrunkPlacer.isFree deliberately treats logs
      as free space, so without this trees pass through one another.
    """
    ring: list[dict] = []
    for r in range(2, spacing + 1):
        for dx, dz in ((r, 0), (-r, 0), (0, r), (0, -r)):
            ring.append(p_not(p_tag(LOGS_TAG, (dx, 1, dz))))

    modifiers: list[dict] = []
    if rarity is not None:
        modifiers.append({"type": "minecraft:rarity_filter", "chance": rarity})
    modifiers += [
        {"type": "minecraft:count", "count": count},
        {"type": "minecraft:in_square"},
        # OCEAN_FLOOR_WG, not MOTION_BLOCKING. Both count leaves - LeavesBlock
        # blocks motion - but MOTION_BLOCKING is a CLIENT-usage heightmap that
        # is not maintained during generation, so asking for it mid-worldgen
        # returned heights that had drifted from the chunk. The _WG variants are
        # the two Heightmap.Usage.WORLDGEN maps and are the only ones a
        # placement modifier can trust. Leaves are excluded by the ground
        # whitelist below, not by the heightmap.
        {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
        m_filter(p_all(
            p_tag(NATURAL_GROUND, (0, -1, 0)),
            *[p_replaceable((0, dy, 0)) for dy in range(0, clear_height)],
            *ring,
        )),
        {"type": "minecraft:biome"},
    ]
    return modifiers


def ground_placement(count: int, *, xz: int = 7, y: int = 3) -> list[dict]:
    """Small-plant scatter that also refuses to grow on worked stone."""
    return [
        {"type": "minecraft:count", "count": count},
        {"type": "minecraft:in_square"},
        {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
        {"type": "minecraft:random_offset",
         "xz_spread": {"type": "minecraft:trapezoid", "min": -xz, "max": xz,
                       "plateau": 0},
         "y_spread": {"type": "minecraft:trapezoid", "min": -y, "max": y,
                      "plateau": 0}},
        m_filter(p_all(p_replaceable(), p_tag(NATURAL_GROUND, (0, -1, 0)))),
        {"type": "minecraft:biome"},
    ]


def gen_features() -> None:
    cf = MOD / "worldgen" / "configured_feature"
    pf = MOD / "worldgen" / "placed_feature"

    # ---- Overworld ore ----------------------------------------------------
    # Host-matched: the stone variant in the stone band, the deepslate variant
    # below it. Both targets are listed on one ore feature, exactly as vanilla
    # does for every overworld ore, so a single vein that straddles the boundary
    # comes out in the right rock on both sides of it.
    # PLAYER: "bismuth 25% rarer than diamond" / "i cannot find deepslate or
    # regular bismuth". It was at roughly 39% of diamond's ore volume - about
    # 2.6x rarer, not 1.33x - with a band whose top sat 24 blocks above
    # diamond's. Vanilla diamond is size 8 at ~4.7 veins/chunk = ~75 units;
    # size 8 x count 7 = 56 units is 25% under that.
    write(cf / "ore_resonant_bismuth.json", {
        "type": "minecraft:ore",
        "config": {
            "discard_chance_on_air_exposure": 0.0,
            "size": 8,
            "targets": [
                {"state": B("resonant_bismuth_ore"),
                 "target": {"predicate_type": "minecraft:tag_match",
                            "tag": "minecraft:stone_ore_replaceables"}},
                {"state": B("deepslate_resonant_bismuth_ore"),
                 "target": {"predicate_type": "minecraft:tag_match",
                            "tag": "minecraft:deepslate_ore_replaceables"}},
            ],
        },
    })
    write(pf / "ore_resonant_bismuth_placed.json", {
        "feature": ev("ore_resonant_bismuth"),
        "placement": [
            {"type": "minecraft:count", "count": 7},
            {"type": "minecraft:in_square"},
            # Diamond's own band, so bismuth is found where a player already
            # digs for diamond rather than 24 blocks above it.
            {"type": "minecraft:height_range",
             "height": {"type": "minecraft:trapezoid",
                        "min_inclusive": {"above_bottom": -80},
                        "max_inclusive": {"above_bottom": 80}}},
            {"type": "minecraft:biome"},
        ],
    })

    # PLAYER: "null iron should be 25% rarer than gold". It was a 3-block
    # SCATTERED ore at 0.5 veins/chunk confined to y-64..-8: about 27x less ore
    # per chunk than gold (96% rarer), never forming a recognisable vein, and
    # with its whole band below y-8 so the stone-host null_iron_ore variant was
    # effectively unreachable. Now gold's own vein shape and air-exposure
    # discard, at 3 veins/chunk against gold's 4 - 25% rarer.
    write(cf / "ore_null_iron_overworld.json", {
        "type": "minecraft:ore",
        "config": {
            "discard_chance_on_air_exposure": 0.5,
            "size": 9,
            "targets": [
                {"state": B("deepslate_null_iron_ore"),
                 "target": {"predicate_type": "minecraft:tag_match",
                            "tag": "minecraft:deepslate_ore_replaceables"}},
                {"state": B("null_iron_ore"),
                 "target": {"predicate_type": "minecraft:tag_match",
                            "tag": "minecraft:stone_ore_replaceables"}},
            ],
        },
    })
    write(pf / "ore_null_iron_overworld_placed.json", {
        "feature": ev("ore_null_iron_overworld"),
        "placement": [
            {"type": "minecraft:count", "count": 3},
            {"type": "minecraft:in_square"},
            # Reaches up into stone now, so the stone-host variant can appear.
            {"type": "minecraft:height_range",
             "height": {"type": "minecraft:trapezoid",
                        "min_inclusive": {"absolute": -64},
                        "max_inclusive": {"absolute": 32}}},
            {"type": "minecraft:biome"},
        ],
    })

    # PLAYER: "phonolite should generate in large patches like tuff, i havent
    # seen any at all yet" / "i havent been able to find a single drop of
    # phonolite yet."
    #
    # It had NO Overworld generation of any kind, and no crafting or loot route
    # outside the Hollow Horizon - which made the mod a hard progression
    # deadlock in survival, because the portal frame is phonolite_bricks and
    # those are craftable only from raw_phonolite. You needed phonolite to
    # reach the only place that had phonolite.
    #
    # Shaped like vanilla ore_tuff rather than like an ore: size 64 blobs
    # against base_stone_overworld, low in the column, so it reads as a rock
    # formation a player stumbles into rather than something to prospect for.
    write(cf / "ore_raw_phonolite.json", {
        "type": "minecraft:ore",
        "config": {
            "discard_chance_on_air_exposure": 0.0,
            "size": 64,
            "targets": [
                {"state": B("raw_phonolite"),
                 "target": {"predicate_type": "minecraft:tag_match",
                            "tag": "minecraft:base_stone_overworld"}},
            ],
        },
    })
    write(pf / "ore_raw_phonolite_placed.json", {
        "feature": ev("ore_raw_phonolite"),
        "placement": [
            {"type": "minecraft:count", "count": 2},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:height_range",
             "height": {"type": "minecraft:uniform",
                        "min_inclusive": {"above_bottom": 0},
                        "max_inclusive": {"absolute": 0}}},
            {"type": "minecraft:biome"},
        ],
    })

    # ---- Hollow Horizon ores ---------------------------------------------
    write(cf / "ore_phonolite_resonant_bismuth.json",
          _ore(B("phonolite_resonant_bismuth_ore"), 9))
    write(pf / "ore_phonolite_resonant_bismuth_placed.json", {
        "feature": ev("ore_phonolite_resonant_bismuth"),
        "placement": [
            {"type": "minecraft:count", "count": 14},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:height_range", "height": _uniform(10, 200)},
            {"type": "minecraft:biome"},
        ],
    })

    write(cf / "ore_phonolite_null_iron.json", {
        "type": "minecraft:scattered_ore",
        "config": {
            "discard_chance_on_air_exposure": 0.6,
            "size": 3,
            "targets": [{
                "state": B("phonolite_null_iron_ore"),
                "target": {"predicate_type": "minecraft:tag_match",
                           "tag": f"{NS}:hollow_horizon_carvable"},
            }],
        },
    })
    write(pf / "ore_phonolite_null_iron_placed.json", {
        "feature": ev("ore_phonolite_null_iron"),
        "placement": [
            {"type": "minecraft:count", "count": 4},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:height_range", "height": _uniform(4, 90)},
            {"type": "minecraft:biome"},
        ],
    })

    # Knell. Deep strata of the Hollow Horizon only, hosted in raw phonolite
    # rather than in the carvable set, so it can never turn up in a chalk
    # highland: 2 veins per chunk at size 2, y 0..34, per expansion.json.
    # Size 3, not the spec's 2. minecraft:ore derives its vein radius from size:
    # at size 2 the radius works out to ~0.5 blocks, the ellipsoid test
    # dx^2+dy^2+dz^2 < 1 excludes every block centre, and the feature places
    # NOTHING. Asked directly, the running server agrees - /place feature
    # echoing_void:ore_knell on a block the server confirms is in
    # #echoing_void:phonolite_ore_replaceables answers "Failed to place feature",
    # which is what OreFeature returns when it placed zero blocks. Vanilla's
    # smallest ore of this type is emerald at size 3, which is the floor that
    # actually works. The intent - a very rare, near-single-block vein - is
    # unchanged; 2 was simply below the mechanism's floor.
    write(cf / "ore_knell.json",
          _ore(B("knell_ore"), 3, discard=0.0,
               tag=f"{NS}:phonolite_ore_replaceables"))
    write(pf / "ore_knell_placed.json", {
        "feature": ev("ore_knell"),
        "placement": [
            {"type": "minecraft:count", "count": 2},
            {"type": "minecraft:in_square"},
            # Any depth of the Hollow Horizon, overwhelmingly the deepest. The
            # player was explicit twice over that Knell belongs to this
            # dimension and nowhere else, so there is deliberately NO forge
            # biome_modifier for it: the only route it has into a chunk is the
            # three Hollow Horizon biomes' own feature lists.
            #
            # very_biased_to_bottom rolls twice and keeps the lower, so the
            # deepest rock takes the overwhelming majority of veins.
            #
            # The band was [0, 34], taken from expansion.json. Measured against
            # a generated world that window turned out to hold 0.347% of the
            # dimension's rock and 3.76% of its phonolite - 90% of phonolite
            # sits at y48-95 - and across 1552 fully generated chunks the ore
            # spawned exactly zero times. The endgame tier was unobtainable.
            #
            # The spec constant predates the terrain it was meant to describe,
            # so the band moves to where the deep strata actually is. The design
            # intent is unchanged and still enforced: very_biased_to_bottom
            # keeps this "the deepest strata", and the ore is still reachable
            # only through the Hollow Horizon.
            {"type": "minecraft:height_range",
             "height": {"type": "minecraft:very_biased_to_bottom",
                        "min_inclusive": {"absolute": 32},
                        "max_inclusive": {"absolute": 96},
                        "inner": 4}},
            {"type": "minecraft:biome"},
        ],
    })

    # Humming Crystal: big emissive masses in the deep strata, so the underside
    # of the continent is lit from within rather than being a black ceiling.
    write(cf / "humming_crystal_vein.json", _ore(B("humming_crystal"), 16))
    write(pf / "humming_crystal_vein_placed.json", {
        "feature": ev("humming_crystal_vein"),
        "placement": [
            {"type": "minecraft:count", "count": 10},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:height_range", "height": _uniform(2, 56)},
            {"type": "minecraft:biome"},
        ],
    })

    # ---- cave decoration --------------------------------------------------
    # Bismuth clusters on cave floors and ceilings. simple_block asks the state
    # whether it can survive where it landed, so an attachment it dislikes is
    # skipped silently rather than crashing generation.
    cluster = {"type": "minecraft:simple_block",
               "config": {"to_place": {"type": "minecraft:simple_state_provider",
                                       "state": B("bismuth_cluster")}}}

    def scan(direction: str, y_spread: int) -> list[dict]:
        return [
            {"type": "minecraft:environment_scan",
             "direction_of_search": direction,
             "max_steps": 12,
             "allowed_search_condition": {"type": "minecraft:matching_block_tag",
                                          "tag": "minecraft:air"},
             "target_condition": {"type": "minecraft:solid"}},
            {"type": "minecraft:random_offset", "xz_spread": 0, "y_spread": y_spread},
        ]

    write(cf / "bismuth_cluster.json", {
        "type": "minecraft:simple_random_selector",
        "config": {"features": [
            {"feature": cluster, "placement": scan("down", 1)},
            {"feature": cluster, "placement": scan("up", -1)},
        ]},
    })
    for suffix, count in (("", 22), ("_dense", 40)):
        write(pf / f"bismuth_cluster{suffix}_placed.json", {
            "feature": ev("bismuth_cluster"),
            "placement": [
                {"type": "minecraft:count", "count": count},
                {"type": "minecraft:in_square"},
                {"type": "minecraft:height_range", "height": _uniform(6, 200)},
                {"type": "minecraft:biome"},
            ],
        })

    # Chime Sand drifts pooling on cavern floors.
    write(cf / "chime_sand_hollow.json", {
        "type": "minecraft:vegetation_patch",
        "config": {
            "depth": 2,
            "extra_bottom_block_chance": 0.15,
            "extra_edge_column_chance": 0.3,
            "ground_state": {"type": "minecraft:simple_state_provider",
                             "state": B("chime_sand")},
            "replaceable": f"#{NS}:hollow_horizon_carvable",
            "surface": "floor",
            "vegetation_chance": 0.0,
            "vegetation_feature": {"feature": ev("ground_cover"), "placement": []},
            "vertical_range": 5,
            "xz_radius": {"type": "minecraft:uniform",
                          "min_inclusive": 3, "max_inclusive": 7},
        },
    })
    write(pf / "chime_sand_hollow_placed.json", {
        "feature": ev("chime_sand_hollow"),
        "placement": [
            {"type": "minecraft:count", "count": 5},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:height_range", "height": _uniform(10, 160)},
            {"type": "minecraft:biome"},
        ],
    })

    # Surface drifts, for Chalk Reaches: the same patch feature run on the open
    # plateau tops rather than in caves.
    write(pf / "chime_sand_drift_placed.json", {
        "feature": ev("chime_sand_hollow"),
        "placement": [
            {"type": "minecraft:count", "count": 3},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
            m_filter(p_tag(NATURAL_GROUND, (0, -1, 0))),
            {"type": "minecraft:biome"},
        ],
    })

    # ---- debris -----------------------------------------------------------
    # Fallen rock beneath islands. block_pile lays an irregular two-layer heap
    # on any sturdy face (BlockPileFeature.mayPlaceOn), which is what rubble
    # under an overhang looks like; the state list is the strata the island
    # above is made of, plus chime sand for the fines.
    rubble = {
        "type": "minecraft:block_pile",
        "config": {"state_provider": {
            "type": "minecraft:weighted_state_provider",
            "entries": [
                {"data": B("raw_phonolite"), "weight": 30},
                {"data": B("echo_slate"), "weight": 24},
                {"data": B("amber_strata"), "weight": 18},
                {"data": B("resonant_chalk"), "weight": 14},
                {"data": B("chime_sand"), "weight": 14},
            ],
        }},
    }
    write(cf / "fallen_debris.json", rubble)

    # "Beneath an island" is tested literally: something solid overhead, checked
    # at three heights, and no higher than 15: Vec3i.offsetCodec(16) validates
    # |component| < 16 strictly, so 15 is as far as a block predicate may look.
    # That is exact for the undersides, overhangs and low fragments a player
    # actually walks beneath; it does not reach a sky island seventy blocks up,
    # whose matching hollow is cut by `sky_present` in the density graph instead.
    beneath_something = p_any(p_solid((0, 15, 0)), p_solid((0, 11, 0)),
                              p_solid((0, 7, 0)))
    # PLAYER: "i dont really like the random artifacts that generate atop the
    # floating island biome. i get that it adds variety, but they spawn far too
    # frequently, they need to spawn at a twentieth the density."
    #
    # Was a flat count of 8 per chunk. A count of 1 is the floor, so a twentieth
    # cannot be reached by lowering the count alone - it takes a rarity filter as
    # well. rarity_filter 5 lets one chunk in five through, and 2 placements in
    # those chunks gives 2/5 = 0.4 per chunk against the old 8, which is exactly
    # one twentieth. The filter goes FIRST so it discards the chunk before any
    # of the more expensive per-placement predicates run.
    write(pf / "island_debris_placed.json", {
        "feature": ev("fallen_debris"),
        "placement": [
            {"type": "minecraft:rarity_filter", "chance": 5},
            {"type": "minecraft:count", "count": 2},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
            m_filter(p_all(p_replaceable(), p_tag(NATURAL_GROUND, (0, -1, 0)),
                           beneath_something)),
            {"type": "minecraft:biome"},
        ],
    })
    # The same rubble on every cave floor and ledge in the column, which is
    # where most of the "under an island" surface area actually is.
    write(pf / "cavern_debris_placed.json", {
        "feature": ev("fallen_debris"),
        "placement": [
            {"type": "minecraft:count_on_every_layer", "count": 2},
            m_filter(p_all(p_replaceable(), p_tag(NATURAL_GROUND, (0, -1, 0)))),
            {"type": "minecraft:biome"},
        ],
    })

    # ---- ground cover -----------------------------------------------------
    write(cf / "ground_cover.json", {
        "type": "minecraft:simple_block",
        "config": {"to_place": {
            "type": "minecraft:weighted_state_provider",
            "entries": [
                {"data": B("chime_grass"), "weight": 46},
                {"data": B("echo_sprout"), "weight": 38},
                {"data": B("crystal_bloom"), "weight": 16},
            ],
        }},
    })
    write(pf / "ground_cover_placed.json", {
        "feature": ev("ground_cover"),
        "placement": ground_placement(64),
    })
    # Shattered Octaves is meant to feel bare, so it gets a sixth of the cover
    # and no meadow at all.
    write(pf / "sparse_ground_cover_placed.json", {
        "feature": ev("ground_cover"),
        "placement": ground_placement(10, xz=5, y=2),
    })

    # The same cover again, but on every cave floor in the column rather than
    # only the sky-facing surface. This is what stops the interior reading dead.
    write(pf / "cavern_ground_cover_placed.json", {
        "feature": ev("ground_cover"),
        "placement": [
            {"type": "minecraft:count_on_every_layer", "count": 4},
            m_filter(p_all(p_replaceable(), p_tag(NATURAL_GROUND, (0, -1, 0)))),
            {"type": "minecraft:biome"},
        ],
    })

    # Denser meadows of chime grass alone, for texture on open ground.
    write(cf / "chime_grass_meadow.json", {
        "type": "minecraft:simple_block",
        "config": {"to_place": {"type": "minecraft:simple_state_provider",
                                "state": B("chime_grass")}},
    })
    write(pf / "chime_grass_meadow_placed.json", {
        "feature": ev("chime_grass_meadow"),
        "placement": [
            {"type": "minecraft:noise_threshold_count",
             "noise_level": -0.8, "below_noise": 6, "above_noise": 14},
            {"type": "minecraft:in_square"},
            {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
            {"type": "minecraft:count", "count": 24},
            {"type": "minecraft:random_offset",
             "xz_spread": {"type": "minecraft:trapezoid", "min": -7, "max": 7,
                           "plateau": 0},
             "y_spread": {"type": "minecraft:trapezoid", "min": -2, "max": 2,
                          "plateau": 0}},
            m_filter(p_all(p_replaceable(), p_tag(NATURAL_GROUND, (0, -1, 0)))),
            {"type": "minecraft:biome"},
        ],
    })

    # ---- groves -----------------------------------------------------------
    # One species per biome, per docs/spec/expansion.json: Amber Bough in the
    # plains, Echo Ash in the chalk reaches, Humming in the octaves. Silhouettes
    # differ as well as hues, so a grove tells a player where they are from a
    # long way off.
    write(cf / "amber_bough_grove.json",
          _tree("amber_bough_log", "amber_resonance_leaves", "amber_strata",
                6, 4, 3, 3))
    write(cf / "echo_ash_grove.json",
          _tree("echo_ash_log", "ashen_resonance_leaves", "resonant_chalk",
                7, 3, 2, 3, placer="forking_trunk_placer"))
    write(cf / "humming_grove.json",
          _tree("humming_stem", "violet_resonance_leaves", "echo_slate",
                8, 4, 2, 4))
    write(cf / "petrified_grove.json",
          _tree("petrified_tuning_wood", "calcified_resonance_leaves",
                "raw_phonolite", 5, 3, 2, 3))

    # Counts are weighted lists whose mean is around one tree per chunk, and
    # every one of them is subject to the ground/column/spacing guard.
    write(pf / "amber_bough_grove_placed.json", {
        "feature": ev("amber_bough_grove"),
        "placement": tree_placement(_weighted_count((0, 3), (1, 6), (2, 3)),
                                    clear_height=9, spacing=3),
    })
    write(pf / "echo_ash_grove_placed.json", {
        "feature": ev("echo_ash_grove"),
        "placement": tree_placement(_weighted_count((0, 5), (1, 4), (2, 1)),
                                    clear_height=9, spacing=3),
    })
    write(pf / "humming_grove_placed.json", {
        "feature": ev("humming_grove"),
        "placement": tree_placement(1, clear_height=10, spacing=4, rarity=4),
    })
    write(pf / "petrified_grove_placed.json", {
        "feature": ev("petrified_grove"),
        "placement": tree_placement(1, clear_height=8, spacing=3, rarity=6),
    })


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def gen_structure() -> None:
    """Structure placement only.

    The jigsaw PIECES and their template pools are written by
    tools/gen_structures.py, which runs immediately after this generator. What
    lives here is the half that is a terrain question: which heightmap a start
    is projected onto, how the terrain is adapted around it, how far apart the
    sites are spread, and which biomes may host one.
    """
    # THE PLACEMENT FIX.
    #
    # JigsawStructure.findGenerationPoint samples start_height and passes it to
    # JigsawPlacement.addPieces, which computes
    #
    #     bottomY = position.getY() + getFirstFreeHeight(centreX, centreZ, hm)
    #
    # when project_start_to_heightmap is present (JigsawPlacement:110). start_height
    # is therefore an OFFSET FROM THE HEIGHTMAP, not an absolute altitude. The old
    # config asked for {absolute: 96} on top of the surface height, which threw the
    # outpost 96 blocks off the ground and past the checks in
    # isStartTooCloseToWorldHeightLimits. Every vanilla surface jigsaw - village,
    # pillager outpost - uses {absolute: 0} with WORLD_SURFACE_WG, so we do too.
    #
    # terrain_adaptation was "none", which also meant no beardifier density was
    # added around the pieces; on the new broken terrain that would leave outposts
    # hanging over canyons. beard_thin is the village setting and pulls a thin
    # skirt of stone up under the footprint. JigsawStructure.verifyRange requires
    # max_distance_from_center + 12 <= 128 once adaptation is on, so 96 is safe.
    write(MOD / "worldgen" / "structure" / f"{STRUCT}.json", {
        "type": "minecraft:jigsaw",
        "biomes": f"#{NS}:has_structure/{STRUCT}",
        "max_distance_from_center": 96,
        "project_start_to_heightmap": "WORLD_SURFACE_WG",
        # The outpost's pools chain start -> bridges -> buildings ->
        # terminators/gate_caps, so a depth of 5 stops one branch short of its
        # cap piece and leaves a bridge ending in nothing. 6 is also the village
        # setting, and the depth that lets the fan actually terminate.
        "size": 6,
        # PLAYER: "the outpost and camp could have different varieties of neutral mobs that can
        # trade... the outpost could have a village iron golem equivalent creature that spawns
        # naturally in inhabited outposts... it only exists in outposts, not the camps."
        #
        # spawn_overrides is the ordinary structure-scoped spawn mechanism (ChunkGenerator.
        # getMobsAt REPLACES the biome's category list outright inside the structure's bounding
        # box) - the same thing that puts pillagers at a pillager outpost. tuner_trader defaults
        # to Variety.OUTPOST on spawn, which is correct here without any extra wiring; see
        # TraderMob.finalizeSpawn for how it tells outpost apart from camp when it isn't.
        "spawn_overrides": {
            "creature": {
                "bounding_box": "full",
                "spawns": [spawner("tuner_trader", 1, 2, 6), spawner("tuners_protector", 1, 1, 2)],
            },
        },
        "start_height": {"absolute": 0},
        "start_pool": f"{NS}:{STRUCT}/start",
        "step": "surface_structures",
        "terrain_adaptation": "beard_thin",
        "use_expansion_hack": True,
    })

    write(MOD / "worldgen" / "structure_set" / f"{STRUCT}.json", {
        "placement": {
            "type": "minecraft:random_spread",
            # PLAYER: "the outposts spawn too frequently."
            # Was 0.8 / sep 6 / spacing 20 = 1 per 500 chunks. Now 1 per 2560
            # chunks - roughly 820 blocks apart, rarer than a village and still
            # commoner than a pillager outpost - with a 10-chunk minimum gap
            # that comfortably exceeds the structure's own 96-block footprint.
            "frequency": 0.4,
            "frequency_reduction_method": "default",
            "salt": 20260817,
            "separation": 10,
            "spacing": 32,
        },
        "structures": [{"structure": f"{NS}:{STRUCT}", "weight": 1}],
    })

    # The outpost belongs to Resonant Plains now - it is the biome a player is
    # meant to arrive in and get their footing, and it is the only one with the
    # broad connected tops a five-piece jigsaw needs.
    write(MOD / "tags" / "worldgen" / "biome" / "has_structure" / f"{STRUCT}.json", {
        "replace": False,
        "values": [ev(BIOME_PLAINS)],
    })

    # ---- Tuner Encampment ------------------------------------------------
    # Cheap, scattered and small, for Shattered Octaves. Its pieces and pools
    # come from gen_structures.py; the placement is here.
    #
    # size 2 and max_distance_from_center 48 because the biome's islands are
    # small - a five-piece sprawl would routinely run off the edge of one and
    # hang in the air. beard_thin still applies, so a tent gets a footing.
    write(MOD / "worldgen" / "structure" / f"{ENCAMPMENT}.json", {
        "type": "minecraft:jigsaw",
        "biomes": f"#{NS}:has_structure/{ENCAMPMENT}",
        "max_distance_from_center": 48,
        "project_start_to_heightmap": "WORLD_SURFACE_WG",
        "size": 2,
        # Trader only, no protector - the camp is the un-guarded settlement variety.
        "spawn_overrides": {
            "creature": {
                "bounding_box": "full",
                "spawns": [spawner("tuner_trader", 1, 2, 6)],
            },
        },
        "start_height": {"absolute": 0},
        "start_pool": f"{NS}:{ENCAMPMENT}/start",
        "step": "surface_structures",
        "terrain_adaptation": "beard_thin",
        "use_expansion_hack": False,
    })
    write(MOD / "worldgen" / "structure_set" / f"{ENCAMPMENT}.json", {
        "placement": {
            "type": "minecraft:random_spread",
            "frequency": 1.0,
            "frequency_reduction_method": "default",
            # A different salt from the outpost, or the two grids would land on
            # the same chunks wherever their biomes happen to meet.
            "salt": 20260818,
            "separation": 4,
            "spacing": 13,
        },
        "structures": [{"structure": f"{NS}:{ENCAMPMENT}", "weight": 1}],
    })

    write(MOD / "tags" / "worldgen" / "biome" / "has_structure"
          / f"{ENCAMPMENT}.json", {
        "replace": False,
        "values": [ev(BIOME_OCTAVES)],
    })


def gen_tags_and_modifiers() -> None:
    # Every stone the Hollow Horizon is built from, so ores and patches can
    # replace whichever band they happen to spawn in. Kept under its own name
    # rather than reusing phonolite_ore_replaceables, which gen_tags.py owns.
    write(MOD / "tags" / "block" / "hollow_horizon_carvable.json", {
        "replace": False,
        "values": [
            block_id("raw_phonolite"),
            block_id("echo_slate"),
            block_id("amber_strata"),
            block_id("resonant_chalk"),
        ],
    })

    # THE STRUCTURE GUARD. Natural terrain surfaces only. Deliberately excludes
    # every worked block - chalk_bricks, polished_phonolite, phonolite_bricks -
    # and every plant, log and leaf, so a tree or a plant can root on ground the
    # generator made and on nothing else. This is what keeps trees off the
    # outpost's roof and out of each other, and it is why it must NOT be merged
    # with supports_void_vegetation, which includes the structure materials on
    # purpose so a player can farm on them.
    write(MOD / "tags" / "block" / "hollow_horizon_natural_ground.json", {
        "replace": False,
        "values": [
            block_id("raw_phonolite"),
            block_id("echo_slate"),
            block_id("amber_strata"),
            block_id("resonant_chalk"),
            block_id("resonance_moss"),
            block_id("amber_lichen"),
            block_id("chime_sand"),
        ],
    })

    # Forge biome modifiers: seed both resources through the Overworld in their
    # host-matched variants.
    # Format from net/minecraftforge/common/world/ForgeBiomeModifiers.java
    write(MOD / "forge" / "biome_modifier" / "add_resonant_bismuth_ore.json", {
        "type": "forge:add_features",
        "biomes": "#minecraft:is_overworld",
        "features": ev("ore_resonant_bismuth_placed"),
        "step": "underground_ores",
    })
    write(MOD / "forge" / "biome_modifier" / "add_null_iron_ore.json", {
        "type": "forge:add_features",
        "biomes": "#minecraft:is_overworld",
        "features": ev("ore_null_iron_overworld_placed"),
        "step": "underground_ores",
    })
    # Without this the portal is unreachable in survival - see ore_raw_phonolite.
    write(MOD / "forge" / "biome_modifier" / "add_raw_phonolite.json", {
        "type": "forge:add_features",
        "biomes": "#minecraft:is_overworld",
        "features": ev("ore_raw_phonolite_placed"),
        "step": "underground_ores",
    })


def main() -> int:
    global _stub_mode, _registered

    ap = argparse.ArgumentParser()
    ap.add_argument("--force-stub", default="",
                    help="comma-separated block ids to treat as unregistered "
                         "regardless of what the registry sources say. The "
                         "source scan cannot tell whether a DeferredRegister "
                         "holder class is ever class-loaded, so when the server "
                         "log reports 'Unknown registry key' for an id that IS "
                         "in the sources, this is how a probe run gets past it.")
    ap.add_argument("--stub-unregistered", action="store_true",
                    help="swap unregistered mod blocks for vanilla stand-ins so "
                         "the dimension can be probed before the registries land")
    args = ap.parse_args()
    _stub_mode = args.stub_unregistered

    if not VANILLA.exists():
        print(f"FAIL: vanilla reference data not found at {VANILLA}")
        return 1

    _registered = load_registered_blocks()
    forced = {name.strip() for name in args.force_stub.split(",") if name.strip()}
    if forced:
        _registered -= forced
        print(f"forcing {len(forced)} id(s) to be treated as unregistered: "
              f"{', '.join(sorted(forced))}")
    if not _registered:
        print(f"WARNING: could not read block ids from {REGISTRY_DIR}")

    gen_dimension_type()
    gen_dimension()
    gen_density_functions()
    gen_noise_settings()
    gen_biomes()
    gen_features()
    gen_structure()
    gen_tags_and_modifiers()

    removed = prune_orphans()

    print(f"generated {len(written)} worldgen files")
    for w in written:
        print("  " + w)
    if removed:
        print(f"\npruned {len(removed)} orphaned file(s) from the previous layout:")
        for r in removed:
            print("  " + r)

    if _missing:
        label = "STUBBED" if _stub_mode else "NOT REGISTERED"
        print(f"\n{label}: {len(_missing)} block ids referenced by worldgen are "
              f"not registered yet:")
        for name in sorted(_missing):
            note = f" -> {STUBS[name]}" if _stub_mode and name in STUBS else ""
            print(f"  {NS}:{name}{note}")
        if not _stub_mode:
            print("  (the dimension will fail to load until these are registered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

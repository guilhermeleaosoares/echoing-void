# Antigravity brief — redraw the four void saplings

The player, looking at them in game:

> "the sapling items look really awful. look to the vanilla saplings for a
> reference"

Four sprites, all 16x16, all in `src/main/resources/assets/echoing_void/textures/block/`:

`petrified_tuning_sapling` · `echo_ash_sapling` · `amber_bough_sapling` ·
`humming_sapling`

## What is wrong — measured, not guessed

I generated these and they are bad in specific, fixable ways. Here is our amber
sapling next to vanilla's oak and spruce, opaque pixels as `#`:

```
   VANILLA oak            VANILLA spruce         OURS (all four)
   ................       ................       ................
   ...........#....       .......#........       ................
   .......#..##....       ......###.......       ......####......
   ....#.##..####..       ......###.......       .....######.....
   ....##########..       .....#####......       ...##########...
   ..#####.######..       ....#######.....       ...#######.##...
   ...#####.##.###.       .....######.....       ...##.#######...
   ......####...##.       .....#######....       ...##.#######...
   .....#####.##...       ....#######.....       ...##########...
   ...###########..       ....#######.....       ...##########...
   ..#############.       .....#######....       .....######.....
   .###.#######.##.       ....########....       .......##.......
   .....######...#.       ...########.#...       .......##.......
   .....######.....       .....#######....       .......##.......
   .......####.....       ......###.#.....       .......##.......
   .......###......       .......##.......       ................
```

Six concrete faults:

1. **All four of ours are the SAME SHAPE.** Pixel for pixel: 81 opaque pixels,
   bounding box (3,2)-(12,14), 13 rows, widest row 10 — identical across all four.
   Only the palette changes. Vanilla's four are four different plants: oak 111
   pixels, birch 98, spruce 83, cherry 122, each with its own bounding box and its
   own silhouette. **This one is my fault and I argued for it in a comment** — I
   claimed four silhouettes would read as "four different KINDS of thing". That was
   wrong; vanilla plainly varies the silhouette per tree and the trees still read as
   saplings. Ignore that comment and give each tree its own shape.

2. **They float.** Every vanilla sapling reaches row 15, the bottom row of the
   sprite. Ours stop at row 14, so there is a gap under the stem and the plant does
   not sit on anything.

3. **They are too small.** Vanilla spans 15–16 rows of the 16. Ours span 13 and are
   inset three pixels from each side.

4. **Perfect bilateral symmetry.** Ours mirror exactly about the centre line. None
   of vanilla's four do. Symmetry is what makes ours read as a logo rather than a
   plant.

5. **The gaps are in the wrong place.** Ours punches two rectangular holes into the
   middle of a solid crown, which reads as windows. Vanilla's foliage is irregular
   at its EDGE — bites out of the outline, single pixels poking out at the top — and
   mostly solid inside.

6. **The stem is a drawn straight line.** A dead-straight 2-pixel column for four
   rows, with a hard join to the crown. Vanilla has no straight vertical edge longer
   than about three pixels anywhere, and the foliage overlaps and hides the top of
   the trunk instead of sitting on it.

## Study these first

Open them and copy the *construction*, not the colours:

```
C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block\
    oak_sapling.png  birch_sapling.png  spruce_sapling.png
    cherry_sapling.png  jungle_sapling.png  acacia_sapling.png
```

Note in particular how oak's crown is a lopsided mass with stray single pixels
above it; how spruce is a narrow cone that is a completely different silhouette
from oak and still unmistakably a sapling; and how in every one of them the trunk
emerges from *under* the foliage rather than being a stick with a blob on top.

## Give each tree its own shape

These are four different trees and their grown forms already differ. Match the
sapling to the tree it becomes:

| sapling | grows | the grown tree | suggested read |
|---|---|---|---|
| `petrified_tuning_sapling` | `petrified_grove` | pale, stony, tuning-fork branches | narrow, upright, sparse |
| `echo_ash_sapling` | `echo_ash_grove` | dark slate trunk, ashen canopy | drooping, wispy |
| `amber_bough_sapling` | `amber_bough_grove` | the biggest canopy of the four | broad and full |
| `humming_sapling` | `humming_grove` | violet, glowing, fungal stem | bulbous, mushroom-like |

Sample each one's real colours from the blocks it actually grows into rather than
picking by eye:

```
textures/block/calcified_resonance_leaves.png + petrified_tuning_wood.png
textures/block/ashen_resonance_leaves.png     + echo_ash_log.png
textures/block/amber_resonance_leaves.png     + amber_bough_log.png
textures/block/violet_resonance_leaves.png    + humming_stem.png
```

## Targets you can check yourself

Measurable, so verify rather than eyeball:

- **Bottom row**: the lowest opaque pixel is at y=15 in all four.
- **Height**: at least 14 of the 16 rows carry opaque pixels.
- **Fill**: between 80 and 125 opaque pixels — vanilla's range.
- **Asymmetry**: the sprite must NOT equal its own horizontal mirror.
- **Distinctness**: no two of the four may share a bounding box AND a pixel count.
- **No long straight edges**: no unbroken vertical run of the same row-span for more
  than three consecutive rows.

## Rules that are not yours to change

- Work in the **generator**, `tools/gen_tree_assets.py`, never by hand-editing the
  PNGs — `python tools/asset_gen.py` regenerates them and would overwrite you. The
  four sprites come from `sapling_sprite()`, which currently takes one shape for all
  four; it will need to become four shapes.
- Materials come from `gen_item_textures` (`gi.PALE_BONE`, `gi.SLATE`, `gi.AMBER`,
  `gi.ARCANE`, `gi.NULL_IRON`, `gi.TUNING_WOOD`). A `Material` is a ramp of blended
  palette entries, not a list of hex strings — do not define new ones with raw hex,
  it will not construct.
- `python tools/verify_textures.py` must stay green: 16x16, **5–16 colours**,
  on-palette against `docs/spec/art_direction.json`.
- Re-run `python tools/gen_tree_assets.py`, then the gate, then
  `python tools/verify_resources.py`.
- Render your four at 12x beside the six vanilla references and **look at the
  image** before reporting done. If they still read as a lollipop — a symmetric blob
  on a stick — they are not finished.

---

# Second job — smooth the stripped log textures

The player, same breath:

> "also revise all the stripped log textures, make them a bit smoother. look at
> the vanilla stripped textures"

Eight sprites, all 16x16, all in `textures/block/`:

`stripped_amber_bough_log_side` / `_top` ·
`stripped_echo_ash_log_side` / `_top` ·
`stripped_humming_stem_side` / `_top` ·
`stripped_petrified_tuning_wood_side` / `_top`

## "Smoother" is measurable, and ours are badly out

Mean absolute difference between neighbouring pixels — how much the surface jumps
from one pixel to the next:

| texture | roughness | colours |
|---|---|---|
| VANILLA `stripped_spruce_log` | **4.82** | 9 |
| VANILLA `stripped_birch_log` | **6.45** | 45 |
| VANILLA `stripped_warped_stem` | **6.56** | 7 |
| VANILLA `stripped_oak_log` | **6.67** | 37 |
| OURS `stripped_echo_ash_log_side` | 23.04 | 6 |
| OURS `stripped_petrified_tuning_wood_side` | 23.26 | 8 |
| OURS `stripped_amber_bough_log_side` | 26.98 | 7 |
| OURS `stripped_humming_stem_side` | **45.13** | 7 |

Vanilla lives between 4.8 and 6.7. Ours are 3.5x to 7x rougher. The Humming Stem is
the worst offender at nearly seven times `stripped_warped_stem`, which is its
closest vanilla relative.

**Note what this is NOT about: colour count.** `stripped_warped_stem` gets a smooth
surface out of seven colours, and ours has seven too. The difference is how they are
arranged. Vanilla runs long, mostly-vertical grain lines that hold the same tone for
many pixels down the column, with tone changes happening BETWEEN columns. Ours
changes tone almost every pixel in every direction, which is dithering, and at 16x16
dithering reads as static rather than as wood.

## What to do

- Aim for a roughness between **5 and 9**. Under 4 is a flat fill; over 12 is noise.
- Grain runs **along the log's length** — vertical on the `_side` textures, and
  concentric rings on the `_top` ones.
- Hold a tone for **at least 4 pixels down a column** before changing it. Change
  tone between neighbouring columns, not within one.
- Keep the existing palettes. These are the right colours; only their arrangement is
  wrong.
- The `_top` faces should read as end grain — rings around a centre — not as the
  same noise field rotated.

Same rules as the sapling job: work in the generators
(`tools/gen_family_textures.py`, `tools/gen_block_textures.py` — grep for
`stripped`), never hand-edit the PNGs; keep `python tools/verify_textures.py`
green; and measure the roughness of your result before reporting done rather than
trusting your eye.

# Antigravity brief — round 2 on the four void saplings

Your last pass fixed the structural faults and the player confirmed three of the
four read well. Then, looking again:

> "actually on second thought, improve the saplings again, they look flat and
> solid, not bushy and leafy"

and separately, before that:

> "i dont like the echo ash sapling, all others are good"

So: **all four need foliage that reads as leaves rather than as a filled shape,
and `echo_ash_sapling` needs the most work of the four.**

Everything you achieved last round must survive. These are already met and must
stay met:

- lowest opaque pixel at y=15 in all four
- at least 14 of 16 rows carry pixels
- 80–125 opaque pixels
- not horizontally symmetric
- no two of the four share a bounding box AND a pixel count

## What "flat and solid" means, measured

Here is where they are now. `#` is any opaque pixel:

```
  petrified_tuning        echo_ash               amber_bough            humming
  ................       ................       ................       ................
  .........##.....       ........##......       .....#...##.....       ......###.......
  .....##.####....       .......####.....       ....###.####....       .....######.....
  .....#######....       ......######....       ...##########...       ....########....
  ....##.######...       .....########...       ..############..       ...##########...
  ....###..###....       ....#####.###...       ..#############.       ...###########..
  ...#########....       ....########....       .#############..       ...###########..
  ...########.....       ...####.##......       .########.####..       ..############..
  ...####.####....       ...###.######...       ..############..       ..###########...
  ....########....       ..####.##.###...       ..###########...       ...##########...
  ....######......       ..###.####.##...       ...###.##.##....       ....##.##.##....
  ....#######.....       ..##..###..#....       ....##.##.#.....       ....#..##..#....
  .......##.#.....       ...#..##........       ....#####.......       .......##.......
  .......##.......       ......###.......       .......##.......       .......##.......
  .......##.......       .......##.......       .......##.......       ......####......
  .......###......       ......###.......       ......###.......       ......####......
```

Two faults, and they are about the INTERIOR, not the outline:

1. **The crowns are solid masses.** `humming` and `amber_bough` in particular are
   near-unbroken fills eleven pixels across. Vanilla's oak has holes punched right
   through the middle of its canopy — look at rows 5 through 9 of `oak_sapling.png`,
   where the foliage is more gap than leaf in places. A canopy with no interior
   holes reads as a balloon.

2. **The outline is smooth where it should be ragged.** Vanilla's canopies end in
   single pixels and one-pixel steps that stick out and bite in; ours mostly step by
   two or more and follow a clean curve. `humming`'s outline is a near-perfect
   rounded triangle.

`echo_ash` is the one the player singled out. It has the opposite problem from the
others — it is *scattered* rather than solid, and reads as noise or as a damaged
sprite rather than as a wispy tree. Its rows 7 to 12 are a spray of disconnected
two-pixel clumps with no clear mass anywhere. Give it a readable silhouette with a
definite (if sparse and drooping) canopy, then open that canopy up the way you do
the others.

## Study this specifically

```
C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block\
    oak_sapling.png       <- the reference for interior holes
    birch_sapling.png     <- the reference for a sparse, airy canopy
    jungle_sapling.png    <- the reference for a ragged outline
```

Count the holes in oak's canopy and match that density. Note that vanilla's holes
are *irregular* — one pixel here, a two-pixel notch there — never a repeating
pattern.

## New measurable targets, on top of last round's

Check these yourself:

- **Interior holes**: at least 6 fully-enclosed transparent pixels per sprite —
  a transparent pixel with opaque pixels on all four sides. Ours currently have
  very few, and that single number is most of the "solid" complaint.
- **Ragged edge**: at least 8 rows where the row's opaque span changes by exactly
  one pixel from the row above. Smooth curves step by two or more.
- **echo_ash connectivity**: its opaque pixels must form at most **2** connected
  components (4-connectivity). It is currently fragmented; a plant is one thing.
- Keep at least 3 distinct tones of the canopy material so the foliage has
  depth rather than being one flat colour with holes in it.

## Rules that are not yours to change

- Work in `tools/gen_tree_assets.py` only. The PNGs under `src/` are generated and
  hand edits are overwritten by `python tools/asset_gen.py`.
- Materials come from `gen_item_textures` (`gi.PALE_BONE`, `gi.SLATE`, `gi.AMBER`,
  `gi.ARCANE`, `gi.NULL_IRON`, `gi.TUNING_WOOD`). A `Material` is a ramp of blended
  palette entries, not hex strings.
- `python tools/verify_textures.py` must stay green: 16x16, **5–16 colours**,
  on-palette.
- **Do not touch the stripped log textures this round** — that work is being done
  in parallel and your changes there would be overwritten. `gen_family_textures.py`
  and `gen_block_textures.py` are off limits.
- Re-run `python tools/gen_tree_assets.py`, then the gate, then render at 12x
  beside oak, birch and jungle and **look at it**. If a canopy still reads as a
  solid blob with a couple of notches, it is not finished.

## Absolutely off limits

- **`src/main/resources/data/echoing_void/worldgen/` — do not open, do not edit.**
  The player has been explicit: "really dont touch world gen, keep it exactly as
  is, you dont touch world gen, world gen is sacred." Nothing in this job needs it.
- `tools/gen_worldgen.py` likewise.
- `tools/gen_family_textures.py` and `tools/gen_block_textures.py` — being worked
  on in parallel.

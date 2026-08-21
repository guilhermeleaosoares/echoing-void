# Antigravity brief — rework every food icon so it reads as food

The player, looking at the items folder:

> "the ribs the loin the tart, the old resonance bread chime root and void
> tuber, they dont look too much like food, nor the new echo gourd slice.
> theyre not supposed to look like vanilla or completely vanilla, but look at
> how mojang depicts a pumpkin pie or a watermelon slice, or a steak, its
> completely different... those items must look like they came out of those
> animals or plants. in addition to that, i would ask for a rework on resonant
> grain too."

Ten sprites, all 16x16, all in `textures/item/`:

`drone_loin` · `seared_drone_loin` · `thrum_ribs` · `seared_thrum_ribs` ·
`echo_gourd_slice` · `humming_tart` · `resonant_bread` · `chime_root` ·
`void_tuber` · `resonant_grain`

Note three of these you reviewed last run and passed as "fine as is"
(`resonant_grain`, `resonant_bread`, `chime_root`). The player disagrees. Look
again with fresh eyes rather than re-confirming the earlier call.

## What is actually wrong — diagnosed, not guessed

I rendered all ten beside their vanilla counterparts. The gap is not palette
and it is not detail. It is **presentation**, and it is the same four mistakes
in nearly every sprite:

1. **Axis-aligned, not diagonal.** Vanilla food is almost always drawn on a
   three-quarter diagonal — `beef`, `cooked_beef`, `porkchop`, `bread`,
   `carrot`, `potato`, `melon_slice` all run corner to corner. Ours are drawn
   flat-on and square to the pixel grid, which is what makes them read as
   *tiles* rather than as objects.
2. **Too small, floating in the middle.** Vanilla food fills roughly 12-14 of
   the 16 pixels on its long axis. Several of ours sit at 8-10 with a wide
   empty margin, which reads as a token rather than a thing you could pick up.
3. **Rectangles.** Long runs of identical-width rows with hard horizontal tops
   and bottoms. `resonant_bread` is a rectangle. `humming_tart` is a rectangle
   with a rectangle inside it. Real food has no straight edges: every row of a
   vanilla loaf is a different width.
4. **No volume.** Vanilla lights every food from the top-left, so there is a
   highlight edge, a mid tone and a shadow side, and the object reads as round.
   Ours are mostly flat fills with speckle, which is texture without form.

Specific reads I got, unprompted, looking at them cold:
`resonant_grain` reads as **a wooden ladder or scaffold**. `resonant_bread`
reads as **a rug or a doormat**. `void_tuber` reads as **a magenta crystal
shard**. `humming_tart` reads as **a picture frame**. `seared_drone_loin` reads
as **a cookie**. Those are the ones to fix hardest.

## Study these first

Open them, actually look, and copy the *construction* rather than the colours:

```
C:\Projects\mcref-26.2\assets\assets\minecraft\textures\item\
    beef.png  cooked_beef.png  porkchop.png  cooked_porkchop.png
    melon_slice.png  pumpkin_pie.png  bread.png  carrot.png
    potato.png  wheat.png
```

Note in particular how `pumpkin_pie` is a *round* pie seen at an angle with a
wedge missing, not a framed square; how `melon_slice` is a fat crescent with
the rind hugging the outer curve and the flesh bulging; and how `wheat` is a
loose diagonal bundle of separate ears, not a lattice.

## Lineage — the part the player asked for explicitly

> "those items must look like they came out of those animals or plants"

Each icon must be recognisably cut from its source. Pull the actual palette out
of the source texture rather than picking a similar colour by eye:

| item | comes from | source texture to sample |
|---|---|---|
| `drone_loin`, `seared_drone_loin` | Drone Auroch | `textures/entity/drone_auroch.png` |
| `thrum_ribs`, `seared_thrum_ribs` | Thrum Boar | `textures/entity/thrum_boar.png` |
| `echo_gourd_slice` | Echo Gourd block | `textures/block/echo_gourd_side.png`, `echo_gourd_top.png` |
| `humming_tart` | gourd filling + grain crust | both of the above, plus the grain |
| `resonant_bread`, `resonant_grain` | Resonant Wheat | `textures/block/resonant_wheat_stage7.png` |
| `chime_root` | Chime Roots crop | `textures/block/chime_roots_stage3.png` |
| `void_tuber` | Void Tubers crop | `textures/block/void_tubers_stage3.png` |

A player who sees the raw loin should be able to point at the auroch and say
"that came off that". Right now the loin is pink and the auroch is not.

## Concrete targets you can check yourself

These are measurable, so verify them rather than eyeballing:

- **Bounding box** of the opaque pixels: at least 12x12, and not a square block
  of solid rows — the widths should vary down the sprite.
- **Diagonal**: the long axis should run corner-to-corner, not parallel to an
  edge. A quick check: the widest row should not be at the very top or bottom.
- **Row-width variance**: no more than 3 consecutive rows sharing the exact
  same span. That single rule kills every rectangle above.
- **Tonal range**: at least 3 distinct tones of the main material, arranged as
  a top-left highlight through to a bottom-right shadow.

## Rules that are not yours to change

- Work in the **generators** (`tools/gen_crop_assets.py`,
  `tools/gen_item_textures.py`, `tools/gen_new_creature_textures.py`), never by
  hand-editing PNGs under `src/` — a regeneration overwrites hand edits, and it
  has already cost this project a day once.
- `python tools/verify_textures.py` must stay green: 16x16, 5-16 colours,
  on-palette against `docs/spec/art_direction.json`, dark outline on items.
- Re-run `python tools/asset_gen.py` at the end and confirm the gate again.
- Render your finished sprites at 16x scale beside the vanilla references and
  **look at the image** before reporting done. If a sprite still reads as a
  rectangle or a tile at that size, it is not finished.

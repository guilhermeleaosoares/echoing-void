# Task: three texture reworks

Minecraft Forge 26.2 mod. Every texture here is **generated from Python** under
`tools/` — never hand-edit a PNG. Edit the generator, re-run it, look at the
output, iterate.

Three separate jobs, in priority order.

---

## 1. Polished Phonolite — MAJOR rework

`tools/gen_block_textures.py` → `t_polished_phonolite()` (and its
`POLISH_RAMP`).

Reviewer: *"you need a major rework on the polished phonolite, does not look
polished at all."*

It has to read as a **polished stone block** — the same family of read as
vanilla's `polished_andesite`, `polished_deepslate`, `polished_diorite`,
`smooth_stone`. Go and open those in
`C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block\` and study what
actually makes them read as "polished":

- very low local contrast and almost no per-pixel noise (the opposite of the
  raw stone it is cut from)
- a flat, even value field — polish means *uniform*, not *shiny*
- structure comes from a subtle border/bevel or a faint large-scale gradient,
  not from granular speckle
- crucially, it should sit next to `raw_phonolite` and read as unmistakably
  *the same rock, worked smooth*

This is the one place you have real latitude. The current version is too noisy
and too busy to read as worked stone. Make it genuinely look polished.

---

## 2. Harmonic and Knell tool sets — small reworks for silhouette

Item icons: `tools/gen_item_textures.py` (harmonic) and
`tools/gen_knell_textures.py` (knell).

Reviewer: *"both the knell and harmonic tool sets need to look in terms of
shape and silhouette close enough to their vanilla counterparts to be
identified as the respective tool types in an instant, but have a bit more
flare, just like the armor... only ask for small reworks to make it look
nicer."*

The rule: **a player must recognise sword / axe / shovel / hoe / pickaxe at a
glance**, from silhouette alone, exactly as they do with the vanilla items.
Compare each against its vanilla counterpart in
`C:\Projects\mcref-26.2\assets\assets\minecraft\textures\item\`
(`diamond_sword.png`, `diamond_axe.png`, `diamond_shovel.png`,
`diamond_hoe.png`, `netherite_*.png`). Where our silhouette has drifted away
from the vanilla read, pull it back. Then add a *bit* of flare on top — the
same restrained treatment the armour got, not a redesign.

**DO NOT CHANGE `harmonic_pickaxe`.** The reviewer explicitly likes it:
*"i love what you did with the harmonic pickaxe, looks like a pickaxe, has a
nice thematic rework to the echoing void."* It is the **north star** — bring
the other tools up to that same standard of "instantly readable as its tool
type, with a thematic twist". Study it and match its level of restraint.

These are **small** reworks. Do not restyle the whole set.

---

## 3. Petrified Tuning Wood side texture — needs to look like bark

`tools/gen_block_textures.py` → `t_petrified_tuning_wood_side()`.
**Only the non-stripped variant.** Leave
`t_stripped_petrified_tuning_wood_side` alone.

Reviewer: *"the side texture of the petrified tuning wood needs a lot of work
(the non stripped variant), it does not look like bark."*

Study real bark in
`C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block\` —
`oak_log.png`, `spruce_log.png`, `dark_oak_log.png`, `warped_stem.png`,
`crimson_stem.png`. Bark reads through **vertical broken fissures of varying
depth and length**, irregular and not evenly spaced, with the darkest values in
the cracks. This is petrified wood, so it may be stony in colour — but it must
still read as bark, not as a striped stone block.

---

## How to run and check your work

```bash
cd "C:\Projects\The Echoing Void"

python tools/gen_block_textures.py     # jobs 1 and 3
python tools/gen_item_textures.py      # job 2 (harmonic)
python tools/gen_knell_textures.py     # job 2 (knell)

python tools/verify_textures.py        # the gate - MUST pass
```

`build/texture_preview/blocks_preview.png` shows every block texture together —
that side-by-side is how you judge whether polished phonolite reads as polished
next to the raw stone, and whether the log reads as bark.

The gate enforces 5–16 distinct colours per texture, on-palette colours, no
single colour over 85% coverage, and that full-cube textures tile at the seam.
It must pass before you are done.

**Iterate**: generate → render → *actually open and look at the images* →
change → repeat, until you are happy with each of the three. Several passes are
expected.

## Constraints

- Never hand-edit a PNG; all changes go in the Python generators.
- Do not change `harmonic_pickaxe`.
- Do not touch the armour worn-sheets or item icons you did earlier — those are
  approved and signed off.
- A backup of the current tool textures is in `build/toolset_backup_*/` if you
  need to compare against where you started.
- **Do not touch**: `tools/gen_structures.py`, `tools/gen_worldgen.py`,
  `tools/gen_new_creature_geo.py`, `tools/gen_new_creature_textures.py`, or
  anything under `src/main/java/` — another agent is working in those files at
  the same time.

When you are done, report what you changed for each of the three jobs and
confirm `verify_textures.py` passes.

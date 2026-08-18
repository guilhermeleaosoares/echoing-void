# Task: make the WORN armour match the ITEM icons

You are picking up one scoped visual task on an existing, working Minecraft
Forge 26.2 mod. Everything builds and runs today — this is purely an art fix.

## The one-sentence problem

The armour **item icons** (what you see in the inventory) look good and are
signed off. The **worn armour** (what you see on the player model in the world)
does not match them — different plate rhythm, different contrast, different
shapes. They read as two unrelated designs. Fix the worn side so it reads as
the same armour as the icon.

## HARD CONSTRAINT — do not change the item icons

The item icons are **final and approved**. Do not touch:

- `tools/gen_item_textures.py` → `resonance_helmet()`, `resonance_chestplate()`,
  `resonance_leggings()`, `resonance_boots()`, `aero_stride_greaves()`,
  and the `_plate_icon()` helper they call.
- `tools/gen_knell_textures.py` → `knell_helmet()`, `knell_chestplate()`,
  `knell_leggings()`, `knell_boots()`, and the `_plate()` helper they call.
- The resulting PNGs in
  `src/main/resources/assets/echoing_void/textures/item/`.

If you believe an icon must change to make the match work, **stop and say so
in your final message instead of changing it.** The icon is the reference; the
worn sheet is the thing that moves.

## What you MAY change

The worn-equipment sheets and only those:

- `tools/gen_item_textures.py`
  - `resonance_layer_1()`   → body/head/arms/boots sheet (64x32)
  - `resonance_layer_2()`   → leggings sheet (64x32)
  - `aero_stride_layer_1()` → the Aero-Stride boots
  - `baby_sheet()`          → the 64x64 baby-model variants
  - the `Sheet` class helpers: `Sheet.plate()`, `Sheet.plates()`,
    `Sheet.wing_shape()`
  - `curved_band()` — **the shared function, see below**
- `tools/gen_knell_textures.py`
  - `resonant_layer_1()`, `resonant_layer_2()`, `resonant_baby()`

These write to
`src/main/resources/assets/echoing_void/textures/entity/equipment/humanoid/`,
`.../humanoid_leggings/`, and `.../humanoid_baby/`.

Everything is **generated** — never hand-edit a PNG. Edit the Python, re-run
the generator, look at the output.

## Critical context — read this before you design anything

These are real findings from the work already done. Repeating any of these
mistakes will get the result rejected again.

1. **`curved_band()` in `gen_item_textures.py` (line ~812) is deliberately
   shared** between the item icon and the worn sheet. It exists *because* the
   two had drifted apart when each had its own copy of the banding maths. Keep
   them sharing it. If the icon and the sheet compute their plates by two
   different code paths, they will drift again — that is the root cause of the
   bug you are fixing.

2. **`Sheet.bevel()` was deleted from all 14 call sites on purpose.** It painted
   a full-height vertical stripe per face while `Sheet.plates()` was already
   drawing its own per-band lit/shadow edge. The two overlapping produced a grid
   of dark blotches the reviewer called "a jumbled mess". Do not reintroduce a
   second, independent shading pass on top of `plates()`.

3. **Rejected already, do not do these:**
   - Shading that contrasts harder on the worn sheet than on the icon. The exact
     complaint was *"your shading contrasts too much, and it does not match the
     inventory items."*
   - Too many plate stripes. *"the armor plate stripes are too frequent, look
     overdone."*
   - Straight horizontal lines across the chestplate. *"the chestplate cannot
     have just straight lines going across, that does not look like actual
     plates, they need to curve."*
   - Random/asymmetric mottling. The target is *"stacked, geometric armor
     plates, not randomness"* with symmetry, like netherite.

4. **Design north star:** netherite's differentiation from diamond is *purely*
   internal value language — the silhouette is byte-identical. Darker base,
   mottled not gradient, occasional bright flecks. This armour adds real horns
   and cutouts on top of that, but the *value* discipline is the same.

5. There is a **texture gate** that fails the build if a sheet has too few
   distinct colours or one colour covers >85%. If you flatten the contrast too
   far you will trip the colour-count floor. The `spread` parameter on
   `Sheet.plate()` is the intended dial for this (baby sheets already run
   0.40–0.50 to compensate for the removed bevel).

## How to run and look at your work

```bash
cd "C:\Projects\The Echoing Void"

# regenerate (item icons regenerate too — they must come out UNCHANGED)
python tools/gen_item_textures.py
python tools/gen_knell_textures.py

# flat paper-doll + item rows  -> build/texture_preview/
python tools/render_armor_preview.py

# 3D renders -> build/model_preview/player_resonance.png,
#               player_knell.png, player_aero_stride.png,
#               player_contact_sheet.png
python tools/render_player_preview.py
```

`build/texture_preview/armor_items.png` is the icon reference (8 icons:
4 Resonance + 4 Knell). `build/texture_preview/armor_on_player.png` and
`..._side.png` are the worn views. Put them side by side — that comparison *is*
the task.

**Verify the icons did not move:** `git status` should show no change to
anything under `textures/item/`. The repo is a git repo on branch `main`; if
an icon PNG shows as modified, you changed something you should not have.

## Deliverable

1. The worn sheets updated so they read as the same armour as the icons.
2. **3D renders copied to `C:\Users\admin\Downloads\`** — at minimum
   `player_resonance.png`, `player_knell.png`, and `player_contact_sheet.png`
   from `build/model_preview/`. Give them clear names.
3. A short note on what you changed and why.

Do not touch anything outside the armour texture pipeline. Another agent is
working on the Protector mob and the structures in this same repo at the same
time — stay in your lane (`gen_item_textures.py` worn-sheet functions,
`gen_knell_textures.py` worn-sheet functions) and you will not collide.

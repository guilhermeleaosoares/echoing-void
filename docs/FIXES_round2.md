# Fix list, round 2 — from the player, after seeing it in game

Seven items. All of them are things the player saw with their own eyes in a
running world, so treat each as confirmed, not hypothetical.

I have investigated a few of these far enough to hand you the likely cause —
those notes are marked **Diagnosis**. Verify before you act on them; they are
leads, not conclusions.

---

## 1. The Hushwater bucket item needs redesigning (hand this to Antigravity)

> "it really needs to redesign the hushwater item to be closer to the vanilla
> fluid buckets"

`hushwater_bucket.png` does not read as a bucket of liquid. Vanilla's
`water_bucket.png`, `lava_bucket.png` and `powder_snow_bucket.png` all share one
construction: **the same grey bucket silhouette every time**, with the fluid
sitting inside the rim as a distinct band of colour. The bucket is the constant;
the fluid is the variable. Ours needs to obey that.

References to open:
`C:\Projects\mcref-26.2\assets\assets\minecraft\textures\item\water_bucket.png`,
`lava_bucket.png`, `powder_snow_bucket.png`, and plain `bucket.png`.

### How to hand design work to Antigravity

There is a second CLI on this machine, **Antigravity**, running Gemini on its
own auth. It costs nothing from the Claude budget and the player rates its
visual judgement above ours, so design iterations go to it, not to us.

```
"C:\Users\admin\AppData\Local\agy\bin\agy.exe" --continue \
  --model gemini-3.7-flash-high --effort high \
  --dangerously-skip-permissions --print-timeout 60m \
  -p "<your brief here>"
```

Rules that were learned expensively:

- **`-p` / `--print` takes a value, so it must come LAST.** Put it earlier and
  it swallows the next flag, the prompt never arrives, and the run silently
  no-ops while looking like it worked. This cost two dead handoffs.
- **`--continue` resumes the existing conversation**, which already holds the
  whole art direction of this mod. Use it unless you deliberately want a fresh
  context.
- **Give it PNGs and pixel maps, not adjectives.** Six rounds of prose
  ping-ponged on the axe icon — each brief fixed the stated defect and
  introduced a new one — and two rounds of explicit pixel coordinates ended it.
  If shape matters, dump the pixel grid into the brief and save reference PNGs
  it can open.
- **Back up before handing over**, and tell it exactly which files it may touch
  and which are signed off. It will otherwise "improve" things that were already
  approved.
- **Verify its work yourself afterwards** by measuring, not by reading its
  summary. It has reported success on a file it did not change.

## 2. Hushwater renders as the black-and-purple missing texture

> "fix the hushwawter as none of the textures load, its just black and purple"

**Diagnosis (verify this):** the PNGs all exist —
`hushwater_still.png`, `hushwater_flow.png`, `hushwater_overlay.png` and both
`.mcmeta` files are on disk, and `IClientFluidTypeExtensions` is implemented and
points at the right identifiers. So this is not a missing file and not missing
client extensions.

What is missing is that **the sprites are never stitched into the block
atlas**. A fluid's still/flow textures are looked up by name *in the block
atlas*; they only get stitched if something puts them there. There is no
`assets/echoing_void/atlases/` directory at all, and the only model referencing
them is `models/block/hushwater.json` — which, if it is not reachable from a
blockstate that the game actually loads, never contributes its sprites.

Two ways to fix it; pick one and say which:
- add `assets/echoing_void/atlases/blocks.json` with a `minecraft:single` or
  `minecraft:directory` sprite source naming the three textures, or
- make sure the fluid block's blockstate → model chain is genuinely loaded so
  the sprites are pulled in that way.

Check it by looking for the sprite names in the client log's atlas warnings, and
confirm in game rather than by inspection.

## 3. Ground support builds a shell, not a column — my bug, and the fix is precise

> "the structure generation to meet the ground is wrong. it should extend an
> entire column of raw phonolite below all bottom layer blocks, not just an
> outer shell. because now it is generating hollow space below the structure"

`GroundSupportProcessor.java` takes an `edges_only` flag, and
`tools/gen_structures.py` passes `"edges_only": True`. That was my call and it
is wrong: it legs only the perimeter columns, so every piece now sits on a rim
with a hollow void underneath.

Required behaviour:
- extend **every** bottom-layer column, not just the perimeter
- fill with **`echoing_void:raw_phonolite`**, not with a copy of whatever block
  happens to be lowest in that column (which is what it does now)

So `edges_only` should go away entirely rather than be flipped to `false`, and
the support block should be a constant. Keep `max_depth` — a piece over true
void must not drill to the world floor.

## 4. Moss and Hushwater are generating inside the outposts

> "there is moss and hushwater overriding the generation of outpost structures
> meaning that there is hushwater and moss inside the walkways and interiors"

Features are decorating over the top of the structure. Both the moss ground
cover and the new hushwater lakes/springs are landing inside walkways and rooms.

The usual fixes, in order of preference:
- have the feature's placement reject positions inside a structure, or
- move the feature to a decoration step that runs before structures, or
- give the structure pieces a processor that protects their volume.

Note the mod already restricts some features with a
`hollow_horizon_natural_ground` tag — look at how the existing ground-cover and
debris placements guard themselves, since that pattern may already be most of
the answer.

## 5. bridge_stair is extending slabs downward instead of full blocks

> "in the bridge stairs in the outside, though i did tell you to extend the
> lowest block downwards, here you are extending slabs. move to the full block
> equivilent"

`bridge_stair`'s `kerb()` places `t.slab(kx, y, z, POLISHED, "top")`, so the
lowest block in those columns is a slab — and the support column inherits it.
A leg made of stacked slabs is wrong. Use the full block for the support, which
follows automatically once item 3 makes the support a constant raw phonolite.
Check the visible result, not just the code.

## 6. Interior slabs are in the top half and appear to float

> "in many interiors you are using slabs, but they are generating in the higher
> position floating, instead of in the lower position as intended"

There are still **18** `slab(..., "top")` calls in `tools/gen_structures.py`.
Some are deliberate — a chimney cap, a workbench surface, a table top and the
bridge kerbs are meant to sit flush with the course above. The interior floor
and shelf slabs are not; they should be `"bottom"`.

Go through all 18, decide each on its merits, and record why any that stay as
`"top"` are correct. The observatory dome was already corrected this way for
exactly this reason.

## 7. Soul lanterns still floating — chain them to the archways

> "soul lanterns are still floating, we need to connect those with a chain to
> the archways"

An audit I ran previously found only 2 unsupported lanterns and I chained those,
but the player is still seeing floaters, so the audit was too narrow. It walked
up through chains to find an anchor and treated anything solid as sufficient —
which misses lanterns whose anchor is a *slab* or a *stair* or a fence, and
misses the archway lamps entirely because those stand on a wall post rather than
hanging.

Redo the audit properly: for every lantern in every generated `.nbt`, confirm
there is a genuine full-block anchor above it, chained if there is a gap.
Where a lantern is near an archway, connect it to the archway with chain as the
player asks. Then re-verify by dumping the pixel/voxel neighbourhood, not by
eye.

---

## Before you report any of this as done

- `python tools/verify_textures.py`, `verify_models.py`, `check_creative_tabs.py`
- boot a server and confirm **zero** `Unbound values`, `Failed to parse`,
  `Errors in element` and `ERROR]` in `run/logs/latest.log`
- for anything visual, render it and look at the image
- for structure changes, regenerate the pieces and inspect the previews

Your own `docs/HARNESS_findings.md` note about the server pausing when empty
applies to every one of these tests — make sure `pause-when-empty-seconds=0` is
in effect for anything that waits on the world to act.

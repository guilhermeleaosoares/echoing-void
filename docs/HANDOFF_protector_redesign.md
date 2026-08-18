# Total creative direction: the Tuner's Protector

You own the look of this creature completely — its geometry and its texture.
Two previous attempts were rejected outright ("still looks awful", "i still
don't like the protector at all"). Do not iterate on them. **Redo the
physicality.**

The code, the AI behaviour and the build recipe are all good and must not
change. Only how it *looks* is in scope.

---

## What the creature is, in the game

The Tuners are a people who live in outposts in the Hollow Horizon — a
dimension of sound, resonance and dead stone. The Protector is their **iron
golem**: a big, slow, heavy guardian that stands in the outpost and does
nothing until something attacks a trader, then kills it.

Concretely:

- **Neutral.** It never picks a fight. It only ever gets a target from being
  hit itself, or from a nearby trader being hit.
- **Heavy and slow.** 90 HP, 0.24 movement speed, 12 attack damage, full
  knockback resistance. It should *read* as slow and dangerous before it moves.
- **It is a construct, not an animal.** Nobody grew this. It was assembled.
- Sizes: hitbox 1.4 wide × 2.4 tall. The current mesh is 38 units tall and
  22 wide across the arms (16 units = 1 block).

## The single non-negotiable constraint

**A player builds one by stacking blocks**, exactly like an iron golem:

```
 ~^~     a Tuner's Mask          -> the head
 ###     Blocks of Null-Iron     -> torso, with an arm hanging either side
 #~#     Blocks of Null-Iron     -> two legs, gap between them
```

So the finished creature **must unmistakably read as assembled out of Blocks of
Null-Iron with a Tuner's Mask for a face.** That is the whole concept — a
player who stacks those blocks should look at what stands up and think "yes,
that is what I just built."

Everything else — proportions, silhouette, pose, plating, how the mask sits,
how the limbs attach, whether it has a neck at all — is yours.

### Reference textures (open these first)

- `src/main/resources/assets/echoing_void/textures/block/null_iron_block.png`
  — you designed this. Dark forged plate, bevelled frame, recessed centre
  panel, corner rivets, directional sheen.
- `src/main/resources/assets/echoing_void/textures/block/tuners_mask_front.png`
  — literally that block with two gold slits carved into it (it copies the
  block's pixels, so it always matches).
- For scale and attitude, vanilla's own golem:
  `C:\Projects\mcref-26.2\assets\assets\minecraft\textures\entity\iron_golem\iron_golem.png`
  and its model in
  `C:\Projects\mcref-26.2\sources\net\minecraft\client\model\IronGolemModel.java`.

### What was wrong with the rejected versions

Both were coherent with the block but visually dead: extremely dark, very low
contrast, limbs merging into one mass, so at any distance it read as a black
blob with two gold dots. Your own `null_iron_block` rework solved exactly that
problem for the block — it has legible structure and a real forged sheen. The
creature never got that treatment. Also consider whether the **proportions**
are part of the failure, not just the texture; you may change them.

---

## The pipeline

Everything is generated from Python. Never hand-edit a PNG or a geo JSON.

### 1. Geometry — `tools/gen_new_creature_geo.py`

`build_tuners_protector()` builds a Bedrock-style box model with a small DSL:

```python
m = Model("tuners_protector", 128, 128)      # name, atlas width, height
m.bone("root", (0, 0, 0))                     # returns a bone handle
legs = m.bone("legs", (0, 10, 0), parent="root")   # pivot, parent
m.cube(legs, (x, y, z), (w, h, d), "plate", mirror=True)
#          ^bone  ^origin   ^size    ^material key
```

- `origin` is the **corner** of the box in model units, Y up, and **the front
  of the creature is −Z** (that is where a Minecraft entity faces).
- The `"plate"` string is a **material key**: it selects which painter function
  draws that box's faces. You define what keys exist.
- `BUILDERS["tuners_protector"] = (builder_fn, visible_bounds_w,
  visible_bounds_h, offset)` — the two numbers are the culling box, harmless if
  generous.
- The atlas is packed automatically; keep the model inside 128×128 of UV.
- There is an `ANIMATIONS` table in the same file mapping the model to its
  animation class; if you rename or add bones, update the animation entry, and
  note the Java model class `TunersProtectorModel` is regenerated from the geo
  by `tools/gen_entity_models.py`, so **run that too** if you change bones.

### 2. Texture — `tools/gen_new_creature_textures.py`

Painters are registered per material key:

```python
PAINTERS["tuners_protector"] = {
    "plate": protector_plate,   # each is fn(base, glow, u, v, size, seed)
    "head":  protector_head,
    ...
}
PALETTES["tuners_protector"] = (list_of_allowed_rgba, (255,))
```

Inside a painter:

- `box_faces(u, v, w, h, d)` returns `{"north","south","east","west","up","down"}
  -> (x0, y0, fw, fh)` — the rect each face unwraps to. **`north` is the front.**
- `fill_face(sheet, rect, ramp, level, face, seed, grain_amount=, scale=)`
  fills a face from a colour ramp at a brightness level, with per-face lighting.
- `sheet.set(x, y, rgba)` / `sheet.blend(x, y, rgba, t)` for individual pixels.
- `ramp("#hex", "#hex", ..., steps=N)` builds a dark→light ramp;
  `pick(ramp, level)` indexes it.
- Two sheets are passed: `base` is the body, `glow` is the **emissive** sheet —
  anything you write there glows in the dark (that is how the eye slits work).
- `PALETTES` constrains the output: every colour written gets snapped to the
  nearest entry, so add any new colour you want to use.

### 3. Look at it

```bash
python tools/gen_new_creature_geo.py        # if you changed geometry
python tools/gen_entity_models.py           # if you changed BONES
python tools/gen_new_creature_textures.py   # textures + preview
```

The last one writes
`build/texture_preview/new_creatures_render.png` — an **isometric front / side
/ back render of all five creatures**, protector on the bottom row. That is your
feedback loop: change, regenerate, open the image, judge, repeat.

(The front/side/back labels are correct as of now — they used to be inverted.)

### Gates

- The script warns if an entity sheet is outside **10–40 distinct colours**.
- `python tools/verify_textures.py` must pass.
- `python tools/verify_models.py` must pass (valid bones, in-bounds
  non-overlapping UVs).

---

## Deliverable

A protector you are genuinely happy with, that reads as built from null-iron
blocks and a mask, and that looks good — legible limbs, real material presence,
recognisable silhouette at distance.

Then render it and tell me what you changed and why.

Do not touch: `tools/gen_block_textures.py`, `tools/gen_knell_textures.py`,
`tools/gen_item_textures.py`, `tools/gen_structures.py`,
`tools/gen_worldgen.py`, or anything under `src/main/java/`.

# Handoff: the Echoing Void, next block of work

You are picking up a large, working Minecraft Forge mod. Everything described
below as "done" is built, verified in a running game, and pushed. Your job is
the five features that were scoped but never started.

**Read this whole file before touching anything.**

---

## The project

- **Path**: `C:\Projects\The Echoing Void`
- **Target**: Minecraft **26.2**, Forge **26.2-65.1.1**, Java **25**
- **Remote**: https://github.com/guilhermeleaosoares/echoing-void (branch `main`)
- **Decompiled vanilla source**: `C:\Projects\mcref-26.2\sources`
- **Vanilla assets/data**: `C:\Projects\mcref-26.2\assets\assets\minecraft` and
  `C:\Projects\mcref-26.2\assets\data\minecraft`

The mod adds a dimension — the **Hollow Horizon** — reached through a Phonolite
portal struck with a Tuning Fork. It has three biomes (Resonant Plains,
Shattered Octaves, Chalk Reaches), two gear tiers (Resonance, then Knell), seven
creatures, and two jigsaw settlements (Outpost of the Tuners, Tuner Encampment).

### JAVA_HOME is not set globally

Every gradle command needs it. Use:

```bash
JAVA_HOME="/c/Program Files/Eclipse Adoptium/jdk-25.0.4.7-hotspot" \
PATH="/c/Program Files/Eclipse Adoptium/jdk-25.0.4.7-hotspot/bin:$PATH" \
./gradlew build -x test --console=plain -q
```

Install for the player with:
`cp -f build/libs/echoing-void-1.0.0.jar "/c/Users/admin/AppData/Roaming/.minecraft/mods/"`

---

## THE MOST IMPORTANT RULE

**A datapack that generates and compiles is not a datapack that loads.**

This bit me hard. I shipped a tree rework that produced valid-looking JSON and
compiled green, and it took the *entire worldgen registry* down at server boot —
twelve unbound `placed_feature` values and two codec failures. Three separate
schema mistakes, none visible without running the game:

- `fancy_foliage_placer` requires `height`; omitting it is a hard parse failure.
- `upwards_branching_trunk_placer` requires `can_grow_through`.
- `random_selector` holds **PlacedFeature**, not ConfiguredFeature.

**So: after any worldgen, structure, or registry change, boot a server and read
the log.** `python tools/test_structures.py` does this. Then check:

```bash
grep -cE "Unbound values|Failed to parse|Errors in element|ERROR\]" run/logs/latest.log
```

Zero, or you are not done. Never report worldgen work as finished on the
strength of "the JSON generated".

---

## How this codebase works

**Every asset is generated from Python in `tools/`.** Textures, models,
blockstates, loot tables, tags, recipes, worldgen JSON, structure NBT — all of
it. **Never hand-edit a PNG or a generated JSON/NBT.** Edit the generator and
re-run it. If you edit output directly, the next generator run silently reverts
you.

Key generators:

| script | owns |
|---|---|
| `gen_block_textures.py` | terrain/block textures, `polished_phonolite`, `null_iron_block`, `tuners_mask_front` |
| `gen_family_textures.py` | block-family cuts and the host-matched **ores** |
| `gen_item_textures.py` | item icons, armour worn-sheets, the shared `Sprite`/`Material` API |
| `gen_knell_textures.py` | the Knell tier's icons and sheets |
| `gen_worldgen.py` | biomes, features, ores, trees, structure placement, noise settings |
| `gen_structures.py` | the two settlements' NBT pieces and template pools |
| `gen_new_creature_geo.py` / `gen_new_creature_textures.py` | the newer creatures |
| `gen_recipes.py`, `gen_loot_tables.py`, `gen_tags.py`, `gen_models.py` | data |

### Gates — all must pass before you commit

```bash
python tools/verify_textures.py      # 5-16 colours, on-palette, tiling, outlines
python tools/verify_models.py        # bones, parents, UV bounds
python tools/check_creative_tabs.py  # every registry with tabOrder() is sourced
```

### Runtime tests — these boot a real server

```bash
python tools/diagnose_registry.py      # every id resolves in-game
python tools/test_structures.py        # both settlements generate AND are populated
python tools/test_jukebox.py           # all discs play; compares against a vanilla jukebox
python tools/test_protector_build.py   # the mask builds a golem, only from a complete body
```

**A test that runs at coordinates outside the loaded spawn area silently
no-ops** — every command answers "That position is not loaded" and the suite
reports a false pass or a false failure. `forceload add` first. I lost a round
to this on the jukebox test.

---

## The five things to build

The player's own words are quoted; honour the intent, not just the letter.

### 1. Dead Water — the void fluid (do this first)

> "we need a void liquid come up with a name for it maybe dead water... maybe
> that is cyan like bismuth and with a viscosity and flow between water and
> lava, maybe it heals you when you swim in it. this means you can also have
> lakes and waterfalls generate, it would be cool to see this liquid generate in
> a lake in the floating islands and then see it flow down, also gives an easy
> way to access the floating islands. you could have lakes streams and
> waterfalls."

Do this first because it is also a **traversal fix**: a fall of dead water off a
floating island gives the player a way up and down. The name "dead water" is the
player's suggestion, not a requirement — pick something that fits the
dimension's voice if you have a better one, but say what you chose and why.

Needs: a `FluidType` + flowing/source fluids + a liquid block + a bucket item +
still/flow textures (animated, via `.mcmeta`) + a lake feature placed on the
island tops. Flow rate and tick delay between water and lava. Healing on
contact rather than damage. Look at how vanilla registers water and lava in
`net.minecraft.world.level.material` and how Forge's `FluidType` differs.

### 2. Void crops and farmland

> "i also think it would be funny to have an equivilent to the pumpkin crop
> spawn naturally in patches in the voids plains. also in the encampments the
> traders could be growing some void specific crops that can make a food like
> resonant bread that could give a temporary potion effect related to the
> echoing void, or give saturation or absorption. you cold have special wheat
> that you name related to the echoing void that makes that bread, you could
> have carrot and potato equivilents... make sure we can till the moss with a
> hoe to have farmland that only works for these void crops"

So: a pumpkin-equivalent generating in patches on Resonant Plains; wheat, carrot
and potato equivalents; **Resonant Bread** with a themed effect (or saturation /
absorption); and `resonance_moss` tillable with a hoe into a **void farmland**
that only these crops accept. Vanilla's `CropBlock`, `FarmBlock` and
`HoeItem`'s tilling map are the references.

### 3. A farm structure

> "you could also create a farm structure in the echoing void"

A new jigsaw piece set, or an addition to the encampment, showing the traders
actually farming. Note the encampment's `camp_center` already carries two
CAMP-variety traders written into its template — see `Template.entity` in
`gen_structures.py`.

### 4. Cave generation

> "i would ask you to implement some cave generation like in the vanilla
> overworld, and that it would be easier to find bismuth null iron and knell in
> these cave systems"

The dimension's noise settings currently have no carvers. Look at vanilla's
overworld `noise_settings` and its carver list. Then bias the Hollow Horizon ore
features toward exposure in those caves.

### 5. Structure interiors

> "i also need you to rework the interions (not the exteriors in any way) of the
> structures as they are disorganized messes. you have enough height for 2
> floors and 3 floors in some houses, you can connect those with stairs. make it
> look like actually inhabited structures inside with some sense of organization
> and order"

**Interiors only. The exteriors are signed off and must not change.** Several
pieces have the height for two or three floors — add floors, connect them with
stairs, and furnish them so they read as lived-in rooms. `forge_hall`,
`tuner_lodge`, `observatory`, `sound_vault` and `signal_tower` are the
candidates.

---

## Design conventions you must not break

- **Null-iron is hue 240.** Its palette has six anchors in
  `docs/spec/art_direction.json` — `black/dark/mid/steel/light/pale`. The
  `steel/light/pale` half exists specifically so nothing has to borrow phonolite
  (hue ~220) for a highlight; borrowing is what made the metal drift violet in
  the darks and blue in the lights. Do not reintroduce phonolite mixes into
  null-iron ramps.
- **The Tuner's Mask is generated by copying `t_null_iron_block()`'s pixels**
  and carving the sigil. Do not re-implement it; they drifted apart once
  already. Its slit colour indices are derived from the ramp length
  (`SLIT_DIM`/`SLIT_LIT`) because a hardcoded index broke when the ramp grew.
- **The Protector must read as built from Blocks of Null-Iron with a Tuner's
  Mask** — that is literally how a player builds one.
- Measured targets that took several rounds to find, if you touch these:
  polished stone wants an edge/field luminance ratio near **0.71**; worn armour
  sheets want **9-11 colours** and a neighbour-delta near **10**.

---

## Working style the player has asked for

- **Do not spawn agent swarms.** They are on a Max 5x plan and a workflow of
  24 Opus agents burned a third of a session. If you use subagents at all, use
  **Sonnet**, and few.
- **There is a second CLI available for design work**: Antigravity, at
  `C:\Users\admin\AppData\Local\agy\bin\agy.exe`. It runs Gemini on separate
  auth, so it costs nothing from the Claude budget, and the player rates its
  visual judgement above ours. Invoke it as:
  `agy.exe --continue --model gemini-3.7-flash-high --effort high --dangerously-skip-permissions --print-timeout 60m -p "<brief>"`
  Note `--print`/`-p` takes a **value**, so it must come last or it swallows the
  next flag — that silently cost me two no-op handoffs.
  **When briefing it about shapes, give it saved PNGs and pixel maps, not prose.**
  Six rounds of adjectives ping-ponged on an axe; two rounds of coordinates
  landed it.
- **Send the player renders.** They review visually and expect images at each
  milestone. Back up assets before handing them to another tool for rework.
- **Verify, then report.** They have caught me reporting things as working that
  were not. Prefer "I ran X and it printed Y" over "this should work".

## Pushing

The remote needs a GitHub token; there is no cached credential and no token in
this repo. **Ask the player for it** — do not go looking. They have supplied it
inline before, and it should be used for the push only and never written to
`.git/config`.

---

## State right now

Working tree clean, everything pushed, jar built and installed. Last commits
cover the toolset icons, the axe geometry, the null-iron colour unification, the
jukebox, ground-support legs under floating structure pieces, and the removal of
1605 leftover `structure_void` blocks.

`docs/bug_sweep_findings.json` holds 38 investigated findings with file:line
evidence — several relevant to your work, especially the cave-carver and
tree-placer entries. Read it before re-investigating anything.

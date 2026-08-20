# The Echoing Void

## Installing the mod

1. **Download the jar** from the
   [v1.3.0 release](https://github.com/guilhermeleaosoares/echoing-void/releases/tag/v1.3.0) —
   `echoing-void-1.0.0.jar`, under **Assets**. (Linked directly rather than to "latest": every
   release here is marked pre-release, which GitHub's `/releases/latest` excludes entirely — that
   link redirects to the plain release list instead of a download, so it isn't used here.)
2. **Install Forge 26.2-65.1.1** for Minecraft 26.2 if you haven't already — get the installer from
   [files.minecraftforge.net](https://files.minecraftforge.net/) and run it in *Install client*
   mode. This creates the `forge-26.2-65.1.1` profile in your launcher and the `mods` folder it
   loads from.
3. **Copy the jar into your mods folder.** From a Run dialog or File Explorer's address bar, go to:
   ```
   %appdata%\.minecraft\mods
   ```
   (create the `mods` folder if it doesn't exist yet), and drop `echoing-void-1.0.0.jar` in there.
4. **Launch Minecraft** through your launcher, select the `forge-26.2-65.1.1` profile, and play.

Building from source is only needed if you're modifying the mod yourself — see **Building** below.

---

A resonance-and-acoustics dimension mod for **Minecraft 26.2** on **Forge 26.2-65.1.1** (Java 25).

Mine Resonant Bismuth and Null-Iron, tune a frame of Phonolite Bricks with a Tuning Fork, and
cross into the **Hollow Horizon** — a shattered sky of floating petrified strata and acoustic fog,
where the Outposts of the Tuners still hum.

---

## Building

Any JDK on your `PATH` or `JAVA_HOME` is enough to bootstrap Gradle — the build then downloads its
own JDK 25 toolchain automatically (via `foojay-resolver-convention` in `settings.gradle`) and
compiles with that, regardless of what version you had installed. Don't hardcode `JAVA_HOME` to a
specific JDK's install path; `gradlew` fails immediately if that exact path doesn't exist, and a
patch-version path like `jdk-25.0.4.7-hotspot` is specific to whichever build happens to be
installed on one machine.

PowerShell needs the `.\` prefix to run a script from the current directory; Command Prompt doesn't.

```powershell
.\gradlew.bat build          # compile + jar
.\gradlew.bat runClient      # play it
.\gradlew.bat runServer      # dedicated server
```

The built jar lands in `build/libs/echoing-void-1.0.0.jar`.

## The gauntlet gates

```bash
gradlew compileJava build          # Gate 1  - Java + jar
python tools/verify_resources.py   # Gate 1b - JSON + resource graph
python tools/verify_textures.py    # Gate 2  - 16x16 pixel art & palette audit
python tools/verify_models.py      # Gate 3  - Blockbench bone & UV check
python tools/test_tps.py           # Gate 4  - headless TPS stress benchmark
```

Last measured, all four green:

| Gate | Result |
|---|---|
| 1 — build | BUILD SUCCESSFUL, `echoing-void-1.0.0.jar` (173 KB) |
| 1b — resources | 155 JSON files parse; blockstate → model → texture graph fully resolves |
| 2 — textures | 45/45 conform (16×16, 4–6 indexed colours, seamless, on-palette) |
| 3 — models | 3/3 valid bones, resolvable parents, in-bounds non-overlapping UVs |
| 4 — TPS | **20.000 TPS** mean/worst/best over 60 samples under stress |

Gate 4's load is 256 force-loaded chunks, a 64-block Frequency Siphon farm (64 live vibration
listeners), `randomTickSpeed 90`, thunder, and 61 mobs. That raises mean tick time from 0.145 ms
idle to 1.733 ms — roughly a 12× load — with no tick-rate loss. The dedicated server boots in
~2 s and `/forge tps` reports `echoing_void:the_hollow_horizon` ticking alongside the vanilla
dimensions, which is the real proof the custom dimension loads.

## Regenerating assets

Every texture, model, loot table, recipe, tag, structure and worldgen file in this mod is
**generated and reproducible** — no binary asset is hand-edited. One command rebuilds all of it,
deterministically (same bytes every run):

```bash
python tools/asset_gen.py
```

| Tool | Produces |
|---|---|
| `ev_palette.py` | shared palette / periodic-noise / lighting foundation |
| `ev_nbt.py` | minimal NBT codec (structure templates) |
| `gen_block_textures.py` | 20 block textures |
| `gen_item_textures.py` | items, tools, armour icons, equipment sheets, entity sheets |
| `gen_models.py` | blockstates, block models, item model definitions |
| `gen_geo_models.py` | the three `.geo.json` creatures, with UV packing |
| `gen_entity_models.py` | Java `LayerDefinition` model classes generated from those `.geo.json` |
| `gen_spawn_egg_textures.py` | the three spawn egg sprites |
| `gen_tags.py` | block/item tags (tool class, tier gating, repair materials) |
| `gen_loot_tables.py` | block drops + structure chest loot |
| `gen_recipes.py` | crafting, smelting, blasting |
| `gen_worldgen.py` | dimension, biome, ore features, jigsaw structure |
| `gen_structures.py` | the four Outpost `.nbt` templates |
| `render_geo_preview.py` | offline isometric render of each creature (a look, not a gate) |

## Contents

### Blocks

| Block | Hardness / Blast | Tool | Sound | Light | Behaviour |
|---|---|---|---|---|---|
| `resonant_bismuth_ore` | 4.5 / 3.0 | Pickaxe (Diamond) | AMETHYST | 3 | drops 1–3 shards; vibration particle on step |
| `deepslate_resonant_bismuth_ore` | 6.0 / 4.0 | Pickaxe (Diamond) | DEEPSLATE | 3 | deepslate variant |
| `raw_phonolite` | 5.0 / 6.0 | Pickaxe (Diamond) | BASALT | 0 | volcanic slate base |
| `phonolite_bricks` | 5.5 / 6.0 | Pickaxe (Diamond) | STONE | 0 | portal frame |
| `void_glass` | 0.8 / 0.5 | Silk Touch | GLASS | 0 | negates fall damage; zero-g walk surface |
| `null_iron_ore` | 5.0 / 6.0 | Pickaxe (Netherite) | ANCIENT_DEBRIS | 0 | light-absorbing |
| `null_iron_block` | 8.0 / 12.0 | Pickaxe (Netherite) | NETHERITE_BLOCK | 0 | absorbs nearby blasts |
| `petrified_tuning_wood` | 3.0 / 3.0 | Axe (Iron+) | WOOD | 0 | strippable pillar |
| `calcified_resonance_leaves` | 0.4 / 0.2 | Shears / Hoe | AZALEA_LEAVES | 6 | harmonic rustle; drops seedlings |
| `frequency_siphon` | 3.5 / 4.0 | Pickaxe (Iron) | COPPER | 1 | vibration listener → analog redstone 1–15 |
| `inversion_anvil` | 6.0 / 1200.0 | Pickaxe (Diamond) | ANVIL | 2 | uncrafts items by remaining durability |
| `acoustic_lock_box` | 50.0 / 1200.0 | — | METAL | 0 | opens to a matching pitch sequence |

### Gear

- **Harmonic Pickaxe** — mine five blocks at a steady rhythm (any speed, within 33% variance) and
  the 3×3 plane you're facing starts shattering, and keeps shattering while the rhythm holds
- **Sonic Lance** — absorbs incoming projectile damage as charge, discharges a piercing shockwave
- **Void-Glass Rapier** — bypasses half of armour; critical strikes grant brief invisibility
- **Resonance Armour** — banks incoming kinetic damage; double-tap crouch releases it as a shockwave
- **Aero-Stride Greaves** — no fall damage, zero-gravity drift on landing, wall-running

### Creatures

| Creature | Behaviour |
|---|---|
| **Echo Weaver** | Fast, fragile ceiling ambusher. Climbs walls like a spider and hunts from above. Its ceiling probes go through a fixed 64-slot cache (two `long` bitsets, generation eviction) so circling a target never re-raycasts the same column. |
| **Strata Golem** | Slow, armoured, territorial. Carries three crystal spire clusters; a heavy blow shears one off, dropping a shard and leaving the golem faster but weaker. The remaining count is synched so the model can hide shed clusters. |
| **Resonance Wraith** | Drifting flier that ignores terrain and attacks with sound rather than weight. |

All three spawn naturally in the Hollow Horizon, have spawn eggs, and drop themed loot.

Their geometry has a **single source of truth**: `assets/echoing_void/geo/*.geo.json` is audited by
Gate 3, and `tools/gen_entity_models.py` converts it into the Java `LayerDefinition` classes the
renderers use. Edit the geometry, re-run the generator, and the render side follows. The converter
handles the Bedrock→Java coordinate change properly — Y-flip, min-corner cube origins, and bone
pivots that are absolute in Bedrock but parent-relative in Java.

### The Hollow Horizon

A fixed-time dimension of floating Phonolite strata under an end-like sky, generated from vanilla's
floating-islands density graph re-based onto Phonolite. Lit by a **Tuning Fork** struck against a
Phonolite Bricks frame. Contains the **Outpost of the Tuners** — a jigsaw structure of a
Resonance Forge linked by chain bridges to Observatory Domes and Sound Vaults.

---

## Design notes

**Everything is verified against the real 26.2 API.** Minecraft 26.2 postdates most published
modding documentation, and the API moved a long way from 1.21: `ResourceLocation` is now
`Identifier`, `Tier`/`Tiers` and `PickaxeItem`/`SwordItem`/`ArmorItem` no longer exist (tools and
armour are plain `Item` plus builder methods on `Item.Properties`), `BlockEntityType.Builder` is
gone, block entities save through `ValueInput`/`ValueOutput` rather than `CompoundTag`, and the
event bus is EventBus 7 (`SomeEvent.BUS.addListener(...)`). The `dimension_type` schema was
rewritten entirely around a namespaced `attributes` map. Rather than trust memory, the decompiled
26.2 sources and vanilla data were extracted and grepped for every API and JSON schema used here.

**Known deviations from the brief**, stated plainly:

1. **`>20.0 TPS` is unreachable.** The server loop is rate-limited to one tick per 50 ms, so 20.0
   is the engine ceiling. Gate 4 therefore requires the server to *hold* full tick rate
   (mean ≥ 19.90) under stress, and always prints the measured value.
2. **Seamless edge wrapping applies to natural full cubes.** Ores, stone, brickwork and wood tile
   seamlessly and are checked as such. Machine faces (`frequency_siphon`, `inversion_anvil`,
   `acoustic_lock_box`) carry deliberate borders, exactly as vanilla furnace and dispenser faces
   do, and are excluded from the wrap check.
3. **Null-Iron's "diminishes adjacent block light by 1"** is implemented as full light opacity.
   The lighting engine exposes no per-neighbour emission hook; a true −1 to neighbouring blocks
   would require a mixin into the light engine.
4. **Custom sounds are vanilla sounds.** Shipping new `SoundEvent`s would mean shipping `.ogg`
   audio, which cannot be synthesised here; on-theme vanilla sounds are used instead.
5. **The mod id is `echoing_void`.** The brief's prose calls the mod "The Resonance Fractures";
   the project was commissioned as *The Echoing Void*, so that is the display name and namespace.

## What has and has not been verified

Verified by actually running it:

- the mod compiles and jars (`gradlew build`)
- a dedicated server boots it, loads every datapack file, and lists
  `echoing_void:the_hollow_horizon` in `/forge tps` alongside the vanilla dimensions
- the server holds 20.000 TPS under a real load
- the dev client reaches the main menu with the creature layers baked and the renderers
  registered, reporting zero missing models or textures
- every texture, model, blockstate, loot table, recipe, tag, structure and worldgen file passes
  its gate, and the whole resource graph resolves
- the creature geometry has been rendered offline and looked at (`tools/render_geo_preview.py`)

Not verified, because nobody has played it: portal traversal, wall-running, the rhythmic pickaxe,
the uncrafting table, the lock-box pitch sequence, and the creatures' AI in a live world. All of
that is compile-correct and boot-correct; none of it has been felt.

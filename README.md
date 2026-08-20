# The Echoing Void

A resonance-and-acoustics dimension mod for **Minecraft 26.2** on **Forge 26.2-65.1.1** (Java 25).

Mine Resonant Bismuth and Null-Iron, tune a frame of Phonolite Bricks with a Tuning Fork, and
cross into the **Hollow Horizon** — a shattered sky of floating petrified strata and acoustic fog,
where the Outposts of the Tuners still hum.

## Installing the mod

1. **Download the jar** from the
   [latest release](https://github.com/guilhermeleaosoares/echoing-void/releases/latest) —
   `echoing-void-1.0.0.jar`, under **Assets**.
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

## Getting there

The Hollow Horizon is reached the same way you'd reach any dimension: build the frame, light it.

1. **Find Raw Phonolite.** It generates in the Overworld as large tuff-like blobs low in the
   stone column — a rock formation you stumble into rather than something to prospect for.
2. **Craft Phonolite Bricks** and build a portal frame from them.
3. **Craft a Tuning Fork** and strike the frame with it. The frame answers, and opens.

Resonant Bismuth and Null-Iron both generate in the Overworld too, so the first tier of gear is
craftable before you ever cross over.

## Progression

| Tier | Material | Where it comes from |
|---|---|---|
| **Resonance / Harmonic** | Resonance Shards, from Resonant Bismuth ore | Overworld and Hollow Horizon |
| **Knell** | Knell Ingots, smelted from Knell ore | **Hollow Horizon only**, deep strata |

Knell gear is a smithing-table upgrade *from* the Harmonic set, using a **Knell Template**
(4 Resonance Shards + 1 Null-Iron Ingot, yields 2). Knell ore is the rarest material in the mod —
roughly a third as common as null-iron in the same dimension, in a narrow band weighted to the
deepest rock, with no Overworld source and no chest-loot route. Mining it is the only way.

## Gear

Every piece takes its normal enchantments — Sharpness, Efficiency, Fortune, Silk Touch,
Protection, Unbreaking, Mending and the rest — verified item by item against a running server.

### Weapons

- **Harmonic / Knell Sword** — right-click discharges a sonic burst: everything hostile in range
  takes Slowness III and Darkness and is thrown back. Harmonic is 6 blocks / 5 seconds; Knell is
  9 blocks / 10 seconds. Every hit also banks 30% of the sword's damage into a worn Resonance
  chestplate, which is what the armour releases.
- **Void-Glass Rapier** — passive. Every hit gives back half of whatever the target's armour
  absorbed, so it scales with how armoured the target is. Every critical hit grants 3 seconds of
  invisibility to disengage.
- **Sonic Lance** — passive charge, active discharge. Projectile damage taken while it's in
  either hand is 35% absorbed into the lance instead of into you. Right-click with at least 20
  charge to fire a piercing beam down your line of sight — 4–14 blocks and 4–13 damage, scaling
  with charge, knocking back everything living in the line. The tooltip shows the charge level.

### Tools

- **Harmonic / Knell Pickaxe** — mine five blocks at a steady rhythm and the plane you're facing
  starts shattering, and keeps shattering on every further block that holds the beat. There is no
  required tempo: the first gap you leave *sets* the cadence, and later gaps have to stay within
  33% of it. Harmonic breaks a 3×3 plane; Knell breaks 5 wide by 4 tall.
- **Harmonic / Knell Axe, Shovel, Hoe** — full tool sets on both tiers.

### Armour

- **Resonance / Knell Armour** — banks a share of incoming damage. Double-tap crouch to dump the
  bank as a concussive ring that damages and throws back everything hostile within 6 blocks,
  falling off with distance. The chestplate holds the charge; the full four-piece set also shaves
  20% off incoming damage, against 8% for the chestplate alone.
- **Aero-Stride Greaves** — boots, despite the name. No fall damage, a zero-gravity drift on
  landing from height, and wall-running.

## The Hollow Horizon

A fixed-time dimension of floating Phonolite strata under an end-like sky, built from vanilla's
floating-islands density graph re-based onto Phonolite.

**Three biomes** — Resonant Plains, Chalk Reaches, Shattered Octaves.

**Carved caves.** Three carvers cut real tunnel systems through the strata (`hollow_cave`,
`hollow_cave_deep`, `hollow_canyon`), so the rock is genuinely hollow rather than solid to the
core — measured at 4.5× more enclosed cave pocket than the same seed with carvers disabled.

**Hushwater**, a void-native fluid: cyan, viscosity between water and lava, and it *heals* what
stands in it. Generates as lakes, springs and cascades, including waterfalls off the underside of
floating islands.

**Void farming.** Till Resonance Moss with a hoe to get Void Farmland, water it with hushwater,
and grow Resonant Wheat, Void Tubers, Echo Gourds and Chime Roots. Resonant Bread is craftable
from the wheat and carries its own effect.

### Structures

- **Outpost of the Tuners** — a jigsaw settlement: a Forge Hall linked by chain bridges to an
  Observatory dome, a Signal Tower, a Sound Vault and a Tuner Lodge. Every building is a real
  multi-floor interior — sleeping quarters in the roof, a stair a player can actually climb,
  furnished workspaces — and the whole settlement legs itself down to the ground on columns of
  raw phonolite rather than floating.
- **Tuner Encampment** — smaller camps: tents, a lean-to store, a signal post, a granary and a
  worked farm field.

### The people who live there

| Creature | Behaviour |
|---|---|
| **Tuner Trader** | Neutral. Trades like a villager, with five levels and villager XP thresholds, restocking on a timer. Attacks if struck. Written into the structure templates directly, so an outpost is inhabited the moment you find it. |
| **Tuner's Protector** | Neutral guardian, outposts only. Stands where it can see the gates and retaliates when a trader is attacked. |
| **Echo Weaver** | Fast, fragile ceiling ambusher. Climbs walls like a spider and hunts from above. |
| **Strata Golem** | Slow, armoured, territorial. Carries three crystal spire clusters; a heavy blow shears one off, dropping a shard and leaving it faster but weaker. |
| **Resonance Wraith** | Drifting flier that ignores terrain and attacks with sound rather than weight. |
| **Chime Mote**, **Strata Burrower**, **Tuner Shade** | Smaller dimension natives. |

## Notable blocks

| Block | Behaviour |
|---|---|
| `frequency_siphon` | Vibration listener → analog redstone 1–15 |
| `inversion_anvil` | Uncrafts items, by remaining durability |
| `acoustic_lock_box` | The Sound Vault safe. Four horizontal faces are tines; strike them with a Tuning Fork in the right order to open it. The combination comes from the block's own coordinates, is never written to disk, and can only be learned by ear. |
| `null_iron_jukebox` | Plays any music disc, and pays out on each play |
| `void_glass` | Negates fall damage; zero-gravity walk surface |
| `null_iron_block` | Absorbs nearby blasts |
| `resonance_moss` | Tillable into Void Farmland |

Plus full block families — stairs, slabs, walls, fences, gates, doors, trapdoors — for phonolite,
resonant chalk, echo slate, amber strata, and four wood sets.

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

## The gates

```bash
gradlew build                       # Java + jar
python tools/verify_resources.py    # JSON + the whole resource graph
python tools/verify_textures.py     # 16x16 pixel art & palette audit
python tools/verify_models.py       # Blockbench bone & UV check
python tools/check_creative_tabs.py # every registry is sourced by the tab
python tools/verify_interiors.py    # structure exteriors unchanged by interior work
python tools/test_tps.py            # headless TPS stress benchmark
```

Last measured, all green:

| Gate | Result |
|---|---|
| build | BUILD SUCCESSFUL |
| resources | 1136 JSON files parse; 110 blocks and 151 items registered; blockstate → model → texture graph fully resolves |
| textures | 181/181 conform (16×16, 5–16 indexed colours, seamless, on-palette) |
| models | 8/8 valid bones, resolvable parents, in-bounds non-overlapping UVs |
| creative tabs | every registry offering a `tabOrder()` is sourced by the tab |
| interiors | no wall, roof, deck, window or arch block moved by any interior rework |
| TPS | **20.000 TPS** mean/worst/best over 60 samples under stress |

Gate TPS's load is 256 force-loaded chunks, a 64-block Frequency Siphon farm (64 live vibration
listeners), `randomTickSpeed 90`, thunder, and 61 mobs — roughly a 12× load, with no tick-rate
loss. `>20.0 TPS` is unreachable by design: the server loop is rate-limited to one tick per 50 ms,
so 20.0 is the engine ceiling and the gate requires the server to *hold* it.

### Behaviour tests

Beyond the static gates, these drive a real server and assert on what it does:

```bash
python tools/test_enchantments.py       # every tool/weapon/armour accepts its enchantments
python tools/test_hushwater.py          # falls as a column, matches water, generates, heals
python tools/test_void_farming.py       # crops grow on watered void farmland and nothing else
python tools/test_ground_support.py     # structures leg down to the ground, no hollow rim
python tools/test_feature_intrusion.py  # no moss or hushwater inside settlements
python tools/test_worldgen_features.py  # hushwater, gourds and carved caves in a real world
python tools/audit_lanterns.py          # every lantern has a genuine anchor
```

## Regenerating assets

Every texture, model, loot table, recipe, tag, structure and worldgen file in this mod is
**generated and reproducible** — no binary asset is hand-edited, and a full regeneration is
byte-identical to what's committed. One command rebuilds all of it:

```bash
python tools/asset_gen.py
```

29 generators sit behind that, covering block and item textures, the Knell tier, block families,
terrain, creatures and their geometry, crops, the hushwater fluid, structures, worldgen, loot,
recipes and tags.

Creature geometry has a **single source of truth**: `assets/echoing_void/geo/*.geo.json` is
audited by the model gate, and `tools/gen_entity_models.py` converts it into the Java
`LayerDefinition` classes the renderers use. Edit the geometry, re-run the generator, and the
render side follows. The converter handles the Bedrock→Java coordinate change properly — Y-flip,
min-corner cube origins, and bone pivots that are absolute in Bedrock but parent-relative in Java.

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

Two lessons this project paid for, recorded so they aren't relearned:

- **Valid JSON that compiles green does not prove a datapack loads.** A tree-generation rework
  once took the entire worldgen registry down at boot with 12 unbound values, despite every file
  parsing and the build succeeding. Booting a server and grepping the log is the only proof.
- **Enchantability is tag-driven, not material-driven.** An item outside `#minecraft:swords`,
  `#pickaxes`, `#axes`, `#shovels`, `#hoes` or the four armour-slot tags takes *no* enchantments,
  however good its material. There is no code-side symptom; only a running game shows it.

**Known deviations, stated plainly:**

1. **Null-Iron's "diminishes adjacent block light by 1"** is implemented as full light opacity.
   The lighting engine exposes no per-neighbour emission hook; a true −1 to neighbouring blocks
   would require a mixin into the light engine.
2. **Seamless edge wrapping applies to natural full cubes.** Ores, stone, brickwork and wood tile
   seamlessly and are checked as such. Machine faces (`frequency_siphon`, `inversion_anvil`,
   `acoustic_lock_box`) carry deliberate borders, exactly as vanilla furnace and dispenser faces
   do, and are excluded from the wrap check.
3. **The mod id is `echoing_void`.**

## What has and has not been verified

Verified by actually running it:

- the mod compiles and jars, and a dedicated server boots it with zero `Unbound values`,
  `Failed to parse`, `Errors in element`, `ERROR]` or `Exception` in the log
- the server holds 20.000 TPS under a real stress load
- every tool, weapon and armour piece accepts its enchantments — 101 of 101 applications, checked
  one at a time through the same `canEnchant` path the enchanting table and anvil use
- hushwater falls as a column, matches vanilla water on the flat, generates as lakes, and heals
  what stands in it — with a dry control mob proving the gain comes from the fluid
- void crops grow on watered Void Farmland and on nothing else, and refuse vanilla farmland
- structures leg down to solid ground with no hollow rim, and no moss or hushwater generates
  inside a settlement — with a control column proving the features still place in open terrain
- caves are genuinely carved, measured against the same seed with carvers disabled
- every lantern in every generated structure has a real anchor (101 lamps, 19 templates)
- all static gates pass, and a full asset regeneration is byte-identical to what is committed

Not verified end-to-end by a human playing it: portal traversal, wall-running, the lock-box pitch
sequence, and the creatures' AI over a long session. That work is compile-correct, boot-correct
and server-verified; it has not been *felt*.

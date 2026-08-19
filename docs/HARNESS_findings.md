# Harness findings: what a headless server here does and does not do

Seven things about `tools/test_*.py`'s environment and about the mod's own blocks
were discovered the expensive way while building the fluid and the farming set, and
every one of them made a working feature read as broken. They are recorded here
so the next round does not spend a session rediscovering them.

## 1. A dedicated server with no players stops ticking the world

`DedicatedServerProperties.pauseWhenEmptySeconds` defaults to **60**. After that,
`MinecraftServer.tickServer` returns early every tick (`MinecraftServer.java`,
the `emptyTickThreshold` block) and calls only `tickConnection()`.

The server keeps answering commands the whole time. `/setblock` lands, `/execute
if block` answers, `/data get` reports. Nothing in the transcript says the world
is frozen. But game time does not advance, no scheduled tick fires, no crop
grows, no mob ticks, and no fluid moves.

**Every headless test in this repo runs without a player**, so any of them that
waits for the world to *do* something was, past its first minute, measuring a
paused server. `tools/test_tps.py`'s `ensure_server_properties()` now writes
`pause-when-empty-seconds=0`.

The symptom to recognise: `/execute in <dim> run time query gametime` returns
the same number twice in a row. `tools/test_hushwater.py`'s `wait_ticks()` is
built on exactly that check, and every test that waits for the world should use
it rather than `time.sleep`.

## 2. Gamerule names are snake_case in 26.2, and the old spellings are PARSE ERRORS

`gamerule randomTickSpeed 100` is not a deprecated spelling that still works. It
is a Brigadier parse failure - the server answers with the usual
`... gamerule randomTickSpeed 100<--[HERE]` marker and the rule keeps its
default. Nothing about the transcript looks like a failure unless you are
reading for it.

Every gamerule in this repo was written in the pre-26.2 camelCase, so none of
them had been doing anything. That includes GATE 4's stress phases, which have
been running at the default random tick speed and with mob spawning at its
default rather than the values they name. The current names live in
`net/minecraft/world/level/gamerules/GameRules.java`:

| was | is |
|---|---|
| `randomTickSpeed` | `random_tick_speed` |
| `doMobSpawning` | `spawn_mobs` |
| `mobGriefing` | `mob_griefing` |
| `doDaylightCycle` | `advance_time` |

This is what made a farming test that asked for `randomTickSpeed 100` see no
crop grow in 1200 ticks: it was really running at the default of 3, which is
about one random tick per block per 1400 ticks.

## 3. Wall-clock waits are not tick waits

While a forceloaded box is still generating, this dimension drags the server far
below 20 TPS - six seconds of `time.sleep` has been measured as fewer than
twenty game ticks. A fluid needs a scheduled tick every 5 to 12 to move at all.
Count game ticks (`wait_ticks`), never seconds.

## 4. Horizontal fluid spread does not happen on this server. Vertical does.

`tools/diag_fluid_ticks.py` isolates this with the mod out of the picture
entirely. In a forceloaded, confirmed-ticking box, over ~290 game ticks:

| probe | result |
|---|---|
| a falling-sand block placed by `/setblock` falls | **yes** |
| a wounded mob standing in a fluid is ticked | **yes** |
| vanilla WATER over a hole falls, making a column | **yes** |
| vanilla WATER on a flat floor spreads sideways | **no** |
| vanilla LAVA on a flat floor spreads sideways | **no** |
| two water sources one block apart convert the gap | **no** |

So block ticks run, entity ticks run, and fluid ticks run (a fall *is* a fluid
tick - `FlowingFluid#spread` tries DOWN first). Only the sideways branch does
nothing, and it does nothing for vanilla fluids exactly as much as for the
mod's.

Every line of `FlowingFluid.getSpread` / `getNewLiquid` / `canPassThroughWall`
was read against the decompiled 26.2 source and none of them explains it, so
this is recorded as an environment property rather than a diagnosis.

Two candidate explanations were checked and ruled out. It is NOT finding 2: a
fluid spreads on SCHEDULED ticks, and `random_tick_speed` has nothing to do with
it (the falling case in the same table is itself a scheduled fluid tick, and it
works). And it is NOT `SharedConstants.DEBUG_DISABLE_LIQUID_SPREADING`, which
`debugFlag()` gates behind `DEBUG_ENABLED` - a system property this workspace
does not set - and which would in any case have stopped the falling case too.

**What to do about it in a test:** assert against a vanilla-water control rather
than in absolutes. "Hushwater behaves exactly as water does in the same rig" is
both the sound claim and the one worth failing over - if the two ever diverge,
the mod's fluid has stopped using water's machinery.

**What it does NOT block:** the fluid's player-facing behaviour. Lakes are
stamped in place by `minecraft:lake`, and a spring places a `falling=true`
source that spreads DOWN. The waterfall off a floating island - the traversal
half of the feature - is verified working.

## 5. `/setblock` cannot make a crop re-check whether it may stay

`CropBlock#canSurvive` runs at ITEM placement time, and a plant is turned to air
by `VegetationBlock#updateShape`, which only fires when a NEIGHBOUR changes. A
crop dropped onto illegal ground by `/setblock` therefore just sits there, and a
test that reads that as "the placement rule is broken" is reading its own
harness.

Poke a NEIGHBOUR afterwards, and make the poke a real state change: setting a
block to the state it already holds is a no-op (`LevelChunk#setBlockState`
returns null and `Level#setBlock` then skips `updateNeighbourShapes` entirely),
so re-placing the same soil achieves nothing. `tools/test_void_farming.py`'s
`plant()` helper sets a side neighbour to stone and back to air.

## 6. Two things that only a running world caught, both in mod code

Recording these because both looked correct on the page and neither is
discoverable by reading:

* **Forge's empty fluid answers "yes" to `canHydrate`, and this breaks VANILLA
  FARMLAND in this build.** `FarmBlock#isNearWater` asks
  `state.canBeHydrated(...)` at all 162 positions in a 9x2x9 box without first
  checking that there is a fluid at any of them, and the empty fluid state
  answers that it hydrates. Farmland in the middle of a dry plain therefore sits
  at moisture 7 for ever and never reverts to dirt.

  Measured directly: a `minecraft:farmland[moisture=0]` block placed next to a
  `echoing_void:void_farmland[moisture=0]` block, in a chunk where crops were
  observably growing, did not revert in 1200 ticks. `VoidFarmlandBlock` skips
  empty fluid states explicitly and does revert. Worth knowing if a player ever
  reports that ordinary farmland behaves oddly in this pack - it is not the
  mod.
* **`mayPlaceOn` governs placement only.** Once a plant is standing,
  `VegetationBlock#canSurvive` takes its other branch and asks the SOIL through
  Forge's `canSustainPlant`, whose fallback chain reaches
  `PlantType.CROP -> BlockTags.GROWS_CROPS` - a tag vanilla farmland is in. A
  crop restricted only through `mayPlaceOn` is restricted only against the item
  in your hand. `VoidCropBlock`, `VoidStemBlock` and `VoidAttachedStemBlock`
  override both.

## 7. Read until the ANSWER, not for a fixed number of seconds

Every helper in this repo's tests was written as "send the command, then collect
lines for N seconds". N is a guess about how fast the server is, and under load
- a large forceload, a high `random_tick_speed` - the reply routinely lands
after the window closes. The check then reads as a negative, and a negative is
indistinguishable from a real failure.

That is how a farmland block was reported as "NOT moisture 0" the instant after
being set to moisture 0.

`tools/test_void_farming.py`'s `is_block()` sends the query and then reads until
`Test passed` or `Test failed` appears, with a generous ceiling. It is both
correct and faster in the common case. Any new check should be written the same
way.

## Two rigging rules that follow from all of the above

* **Build fluid and crop rigs in the OVERWORLD SKY**, not in the Hollow Horizon.
  Fluid and crop physics are dimension-independent, and this dimension's terrain
  at any given altitude is unpredictable - the first version of the hushwater
  test built its slab straight into native rock and reported a working fluid as
  broken. Only worldgen (`/place feature`, `/place structure`) needs to run in
  the dimension.
* **Forceload every rig, and check it took.** `forceload add` returns as soon as
  the tickets are added, not when the chunks have generated, and a command aimed
  at a chunk that is still generating answers "That position is not loaded" and
  does nothing. Two rigs in an early draft sat outside the box entirely, which
  presented as "the healing does not work".

# Backlog — rebalance null-iron, resonant bismuth, and Knell rarity

Player instruction, not implemented yet by request ("keep these in the
backlog"). Three changes, stated as ratios against numbers already in
`tools/gen_worldgen.py` — edit that file, not the generated JSON under
`data/echoing_void/worldgen/`, which `gen_worldgen.py` overwrites.

## The instruction, verbatim

> "null iron should be as rare as the current resonant bismuth in both
> dimensions, and resonant bismuth should be 1.3x rarer than it is now. keep
> these in the backlog. null iron should be more common than resonant
> bismuth."
>
> "knell should be 1.1x more common than what it currently is. keep that in
> the backlog too"

## Current numbers (verified against `tools/gen_worldgen.py`, not the docs)

| Ore | Dimension | Feature type | Vein size | Attempts/chunk | Height band |
|---|---|---|---|---|---|
| Null-iron | Overworld | `minecraft:ore` | 9 | 3 | y −64..32 (trapezoid) |
| Null-iron | Hollow Horizon | `minecraft:scattered_ore` | 3 | 6 | y 6..100 (uniform) |
| Resonant bismuth | Overworld | `minecraft:ore` | 8 | 7 | diamond's band, above_bottom −80..80 (trapezoid) |
| Resonant bismuth | Hollow Horizon | `minecraft:ore` | 9 | 14 | y 10..150 (uniform) |
| Bismuth cluster (surface deco, HH only, no vein) | Hollow Horizon | `minecraft:simple_random_selector` | n/a | 22 (dense variant: 40) | y 6..200 (uniform) |
| Knell | Hollow Horizon only | `minecraft:ore` | 3 | 2 | y 32..96, `very_biased_to_bottom`, inner 4 |

Source: `ore_null_iron_overworld`/`ore_phonolite_null_iron`,
`ore_resonant_bismuth`/`ore_phonolite_resonant_bismuth`, `bismuth_cluster`,
`ore_knell` and their `*_placed` counterparts, all in `tools/gen_worldgen.py`
around lines 1700-1885.

## Three traps for whoever implements this

**1. Knell's `size` cannot go below 3 - this is already a proven mechanism
floor, not a preference.** The comment directly above `ore_knell` in
`gen_worldgen.py` records that size 2 was tried, tested across 1552 fully
generated chunks, and placed the ore *zero times* - `minecraft:ore`'s vein
radius at size 2 rounds to ~0.5 blocks and the ellipsoid placement test
excludes every block centre. Emerald (vanilla's smallest ore of this type)
is size 3, which is the floor that actually works. "1.1x more common" has to
be delivered through `count` or the height band, never by shrinking `size`.

**2. `count` is an integer, and 2 x 1.1 = 2.2 rounds to nothing.** Knell's
current count is 2 attempts/chunk; scaling that by 1.1 and rounding lands
back on 2 - no change at all. A literal 10% increase needs either the height
band widened by ~10% (64 -> ~70 blocks), the `inner` bias parameter adjusted,
or a `count` expressed as a number provider that only averages 2.2 (e.g.
alternating 2 and 3 with the right weighting) rather than a flat integer.
Confirm which with the player rather than picking one.

**3. Hollow Horizon null-iron is `scattered_ore`, every other ore here is
plain `ore`.** "As rare as the current resonant bismuth" most likely means
matching bismuth's mechanism too, not just its numbers with the wrong
feature type attached - `scattered_ore` spreads single blocks loosely across
an area instead of a compact findable vein, so leaving the type unchanged
while copying bismuth's count/size would not actually feel as rare/common as
bismuth feels, even with identical numbers.

## What this supersedes

Overworld null-iron's current numbers (size 9, count 3) are not arbitrary -
the comment right above them in `gen_worldgen.py` records they were
deliberately tuned to "25% rarer than gold" (gold's own vein shape, 3
veins/chunk against gold's 4) after an earlier player complaint that null-iron
was unfindable. Matching null-iron to bismuth's current Overworld numbers
(size 8, count 7) throws that ratio out entirely - null-iron would go from
rarer-than-gold to closer to as-common-as-diamond (bismuth's Overworld band
is explicitly "diamond's own band" per its own comment). That is what the
player is asking for here, but it is a deliberate reversal of a previous
tuning pass, not an oversight - worth a line in the commit message so the
history reads coherently rather than as one pass fighting the last.

## One worked interpretation (count-only scaling; confirm before using)

Scaling only `count` (the safest lever - it never risks Knell's size floor,
and is the most literal reading of "how often you run into it"), and holding
`size` and height bands unchanged:

| Ore | Dimension | Count now | Count proposed | Ratio actually achieved |
|---|---|---|---|---|
| Null-iron | Overworld | 3 | 7 (= bismuth's current) | matches bismuth exactly |
| Null-iron | Hollow Horizon | 6 | 14 (= bismuth's current) | matches bismuth exactly, **also switch `scattered_ore` -> `ore`** per trap #3 |
| Resonant bismuth | Overworld | 7 | 5 | 1.4x rarer (7/5); 1.3x exactly is 5.38, non-integer |
| Resonant bismuth | Hollow Horizon | 14 | 11 | 1.27x rarer (14/11); 1.3x exactly is 10.77 |
| Knell | Hollow Horizon | 2 | unchanged at integer count - see trap #2 | needs the height band or a number-provider count instead |

Invariant to check after any implementation: **null-iron's new count must
exceed bismuth's new count in the same dimension** (7 > 5 and 14 > 11 both
hold above) - the player stated this as an explicit requirement, and it's
worth asserting directly rather than trusting it falls out of the other two
changes correctly.

Open question this doc does not resolve: does "1.3x rarer" for bismuth also
apply to `bismuth_cluster`/`bismuth_cluster_dense` (the separate surface
decoration feature, not a vein), or only to the ore veins proper? Confirm
with the player before touching it.

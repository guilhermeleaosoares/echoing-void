# Backlog — Harmonic/Knell pickaxe shatter, two defects

Both reported by the player after playing with it. #1 is fixed; #2 is not,
and could not be fixed responsibly without a live player - see its note.

## Status: #1 FIXED

`HarmonicPickaxeItem`'s single `loOffset()/hiOffset()` pair became two
independent pairs, `widthLo/widthHi` and `heightLo/heightHi`. Knell now
overrides width to `-2..2` (5, exact centre) and height to `-1..2` (4, biased
positive like the old 4x4 was, for the same reason). Verified two ways:
statically, by simulating the exact coordinate loop now in `shatter()` for
all three face axes (X/Z walls both produce 19 blocks = a true 4x5 minus the
centre; Y floor/ceiling produces 24 = a 5x5 square at the wide dimension,
which is the documented, deliberate fallback for a plane with no vertical
axis) - and by rebuilding and running the three static gates clean.
Harmonic's base 3x3 is untouched and stays symmetric.

## Status: #2 NOT FIXED - needs a live player, not another guess

Evidence below is from reading the code, not from a live test.

## 1. Knell's plane is a 4x4 square, not a 4x5 rectangle (5 wide, 4 tall)

> "the harmonic pickaxe does the chain thing at cadence it breaks the 3x3,
> knell seems to not do the 4x5 it should"

`KnellPickaxeItem` (`src/main/java/com/echoingvoid/item/KnellPickaxeItem.java:18-25`)
overrides `loOffset()`/`hiOffset()` to `-1..2`. `HarmonicPickaxeItem.shatter()`
(`HarmonicPickaxeItem.java:136-137`) applies that *same* pair to both loop axes:

```java
for (int a = lo; a <= hi; a++) {
    for (int b = lo; b <= hi; b++) {
```

One offset pair can only ever produce a square. Getting a 5-wide x 4-tall
rectangle needs two independent offset pairs - one per axis - not a change to
the existing pair's numbers. `shatter()`'s axis dispatch already treats `a`
and `b` as distinct (`CURSOR.setWithOffset(pos, 0, a, b)` etc. per
`face.getAxis()`), so the plumbing to keep them independent is already most
of the way there; `loOffset()`/`hiOffset()` just need to become four methods
(or a small record) instead of two, and the base `HarmonicPickaxeItem` 3x3
case needs to stay square when it's converted.

## 2. Shatters chain back-to-back instead of needing a fresh 2-block build-up each time

> "in the cadence, as soon as it breaks the first 3x3, every new block it
> breaks that stays in the same cadence breaks 3x3 again, so not block block
> 3x3 block 3x3 block 3x3, but instead block block 3x3 3x3 3x3 3x3 etc, same
> but 4x5 for knell"

Wanted: two on-beat blocks build the cadence, the third shatters, and then it
takes two *more* on-beat blocks before the next shatter - block, block, S,
block, S, block, S...

Observed: after the first shatter, every subsequent on-beat block shatters
again immediately - block, block, S, S, S, S...

**This doesn't match what the code appears to do**, and that mismatch is the
actual finding, not a confirmed root cause. `mineBlock()`
(`HarmonicPickaxeItem.java:94-96`) resets `beat.streak = 0` the moment a
shatter fires:

```java
if (beat.streak >= STREAK_TO_SHATTER) {
    beat.streak = 0;
    shatter(serverLevel, player, stack, state, pos);
}
```

Read statically, that reset should force `STREAK_TO_SHATTER` (2) fresh
on-beat intervals before the next shatter can fire - i.e. exactly the
block-block-3x3 pattern the player wants, not the chained one they're
seeing. Do not trust that trace over the player's report; this session has
already been burned once by assuming a static read proves runtime behaviour
(the tree worldgen registry looked correct and compiled green while being
completely broken at boot - see git history / HANDOFF docs from this repo).
Whoever picks this up should watch it happen in a live game with logging on
`interval`/`beat.streak`/`shattering` before changing anything, since the
cause could be in this method, in how the shatter's own `destroyBlock` calls
interact with tick timing despite the `shattering` guard, or somewhere
neither of us has looked yet.

I looked into reproducing this without a live human before giving up on it
this pass: `mineBlock()` only fires from the real survival mining flow
(`ServerPlayerGameMode.destroyBlock`), which nothing reachable from RCON
commands goes through - there is no way to script "a player breaks N blocks
at a controlled tick interval" from the harness this repo's other tests use.
Forge's GameTest framework (`forge.enableGameTest=true` is already on for
this project's runServer task) could plausibly script that through a fake
player and would be the right tool, but no GameTest infrastructure exists in
this codebase yet - it would need to be built from nothing. Given that cost,
this stays a live-play bug, not a guessed fix.

## Scope note

Fix #1 for Harmonic too if the base 3x3 is meant to stay square while Knell's
is not - confirm with the player rather than assuming symmetry is intentional
or accidental.

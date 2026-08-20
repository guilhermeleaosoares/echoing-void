# Harmonic/Knell pickaxe shatter — all three defects, resolved

Everything in this file is now fixed. Kept as the record of what was wrong,
because two of the three were my own errors and one of those was a
misreading of the player that sent an earlier pass in the wrong direction.

## 1. Knell's plane was a 4x4 square, not 4x5 — FIXED

`KnellPickaxeItem` overrode a single `loOffset()/hiOffset()` pair, and
`HarmonicPickaxeItem.shatter()` applied that same pair to *both* loop axes.
One pair can only ever describe a square, so the requested 5-wide x 4-tall
rectangle was not expressible at any values.

Split into `widthLo/widthHi` and `heightLo/heightHi`. Knell is width `-2..2`
(5, exact centre) and height `-1..2` (4, biased one step positive, as the old
4x4 was). Harmonic's base stays a symmetric 3x3. A floor or ceiling strike has
no vertical axis in its plane at all, so that case applies the width pair to
both axes — documented in the method, not incidental.

Verified by simulating the exact coordinate loop for all three face axes:
X and Z walls give 19 blocks (a true 5x4 minus the struck centre), Y gives 24.

## 2. The trigger never fired in Creative — FIXED

The trigger lived in `Item#mineBlock`. `ServerPlayerGameMode#destroyBlock`
only reaches that call when the player's `preventsBlockDrops()` is false, and
a Creative player's is true — the method early-returns first. So the entire
effect was invisible to anyone who tried the tool in Creative, which is the
obvious first thing to do with a new tool.

`ForgeHooks.onBlockBreakEvent` runs a few lines earlier in that same method
and fires `BlockEvent.BreakEvent` unconditionally in both game modes. The
trigger is on that event now (`CombatEvents.onBlockBreak`), and `mineBlock` is
no longer overridden — keeping both would have double-counted every survival
break.

## 3. The tempo was an absolute-time clause, and impossible to hit — FIXED

This is the one that kept the effect dead even after #2, and it was a
straightforward failure to implement what was asked.

The player's rule, verbatim: *"make it without an absolute time clause, just
say that if 5 blocks are mined at a similar time per block and similar cadance
within 33% variance in the cadance, the effect starts taking effect."*

What was actually in the code was `|interval - 10| <= 3`: a hard requirement
to break a block every ten ticks give or take three. That is precisely the
absolute time clause that was ruled out, and virtually nothing a player does
lands inside it — Creative insta-breaking is far faster than a ten-tick gap,
and survival mining times move with block hardness and tool speed. I had
previously marked this item complete on the claim that no absolute-time clause
remained. That claim was wrong; the clause was right there.

Now implemented as asked: the first interval of a phrase *sets* the cadence at
whatever speed the player is already mining, and each later interval has to
stay within 33% of the running reference. Five blocks arms it. There is no
required tempo at any point.

Two supporting details, both deliberate:

- **Smoothing.** Each in-cadence interval folds half its value back into the
  reference. Pinning the cadence to the very first interval means a rhythm
  that drifts even slightly — every human one does — walks out of the window
  and drops the phrase.
- **One time bound survives**, and it is not a tempo: a 600-tick (30s) gap
  ends the phrase. Thirty seconds between blocks is not a rhythm anyone is
  holding, and without it a break now and a break next week read as a cadence.

### The chaining, which I had recorded backwards

The player asked for: *"as soon as it breaks the first 3x3, every new block it
breaks that stays in the same cadence breaks 3x3 again, so not block block 3x3
block 3x3 block 3x3, but instead block block 3x3 3x3 3x3 3x3 etc"*.

That is a request for the shatter to **latch on** — once armed, keep firing on
every in-cadence break. An earlier version of this document recorded it as the
exact opposite ("shatters chain back-to-back instead of needing a fresh
build-up") and filed the chaining as the bug, when chaining is the wanted
behaviour and the resetting was the bug. The old code did
`beat.streak = 0` immediately after each shatter, producing exactly the
`block block S block block S` pattern the player said they did not want.

The counter is no longer reset on shatter. It only resets when the rhythm
itself breaks.

## Verified sequences

Simulated against the shipped constants (`.` = plain break, `S` = shatter):

```
creative insta-break, every 1 tick     ....SSSSSSSS
creative held, every 5 ticks           ....SSSSSSSS
survival steady, every 15 ticks        ....SSSSSSSS
slow steady, every 40 ticks            ....SSSSSSSS
steady with +-1 human jitter           ....SSSSS
steady, one stumble mid-run            ....SS....SS
erratic, no rhythm                     ........
steady, long pause, steady again       ....S....SS
gradual slow-down (drift)              ....SSSSSSS
```

Four plain breaks then continuous shattering, at any tempo; tolerant of jitter
and of gradual drift; resets on a stumble or a long pause; never fires on
erratic mining.

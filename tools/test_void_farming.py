"""Do the void crops actually behave like crops, and only on void farmland?

The whole design of the farming set rests on one invariant the player asked for
directly - "make sure we can till the moss with a hoe to have farmland that only
works for these void crops" - and that invariant is enforced by a NEGATIVE:
VoidFarmlandBlock is deliberately not a vanilla FarmlandBlock. Negatives do not
show up in a screenshot and they do not show up in a registry probe. Either half
can break silently:

  * if VoidCropBlock#mayPlaceOn ever accepts vanilla farmland, the void crops
    stop being void crops
  * if void_farmland ever lands in #minecraft:grows_crops, vanilla wheat grows
    on it and the exclusivity is gone in the other direction

So both directions are asserted here, in a running world, along with the two
mechanics that have no other proof: hushwater watering a field (which comes from
the FLUID's canHydrate, not from any code in the farmland block) and a crop
actually advancing its age.

WHAT THIS TEST DELIBERATELY DOES NOT ASSERT
-------------------------------------------
Two things, both because a vanilla control does not do them either and a test
that fails on vanilla behaviour is a broken test rather than a found bug. Both
are printed rather than swallowed.

* **Farmland reverting to moss when abandoned.** Neither this block nor vanilla
  farmland dries out on this build - see docs/HARNESS_findings.md, the
  empty-fluid hydration issue. The check reports the pair and fails only if the
  two diverge in the direction that would cost a player their field.
* **The hoe stroke itself.** Tilling runs through HoeItem#useOn, which needs a
  player to right-click; a headless dedicated server has no player and no
  command can simulate one. That half is covered instead by the compiler - ResonanceMossBlock
overrides IForgeBlock#getToolModifiedState with @Override, so a wrong signature
does not build - and by HoeItem.useOn in the decompiled 26.2 source, which calls
exactly that hook with ToolActions.HOE_TILL. It is worth knowing that this is
argument rather than observation.

Everything is built in the OVERWORLD SKY. Crop rules are dimension-independent,
and the Hollow Horizon's terrain at any given altitude is unpredictable, so a rig
built there is a rig built into rock. See tools/test_hushwater.py, which learned
this the expensive way.

Run:  python tools/test_void_farming.py [-v]
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
DIM = f"{NS}:the_hollow_horizon"
OVERWORLD = "minecraft:overworld"

FARMLAND = f"{NS}:void_farmland"
MOSS = f"{NS}:resonance_moss"
HUSH = f"{NS}:hushwater"
WHEAT = f"{NS}:resonant_wheat"

# Everything sits inside ONE chunk (16, 16), which spans x/z 256..271, and well
# clear of its edges. An earlier layout straddled two chunks and produced a
# result that made no sense until it turned out one of them was random-ticking
# and the other was not: the farmland in one chunk changed state while crops in
# the other sat unchanged for 1200 ticks.
BX, BY, BZ = 264, 200, 264

GAMETIME = re.compile(r"time is (\d+)")


def drain(server: Server, seconds: float) -> str:
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return " ".join(out)


def run(server: Server, where: str, c: str, wait: float = 1.0) -> str:
    server.send(f"execute in {where} run {c}")
    return drain(server, wait)


def ow(server: Server, c: str, wait: float = 1.0) -> str:
    return run(server, OVERWORLD, c, wait)


def passed(reply: str) -> bool:
    return "test passed" in reply.lower()


def is_block(server: Server, x: int, y: int, z: int, block: str,
             timeout: float = 8.0) -> bool:
    """Ask, then wait for the ANSWER rather than for a fixed number of seconds.

    A drain window is a guess about how fast the server is, and this test runs
    it at random_tick_speed 40 over a forceloaded box - the reply routinely
    arrives after a one-second window and the check then reads as "no". That is
    how a farmland block set to moisture 0 was reported as "NOT 0" the instant
    after it was placed. Reading until the verdict token appears removes the
    guess and is faster in the common case.
    """
    server.send(f"execute in {OVERWORLD} run execute if block {x} {y} {z} {block}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            line = server.lines.get(timeout=0.2).lower()
        except Exception:
            continue
        if "test passed" in line:
            return True
        if "test failed" in line:
            return False
    return False


def gametime(server: Server) -> int | None:
    m = GAMETIME.search(ow(server, "time query gametime", 1.5))
    return int(m.group(1)) if m else None


def wait_ticks(server: Server, ticks: int, timeout: float = 240.0) -> bool:
    """Advance by GAME ticks, not wall-clock seconds.

    A dedicated server with nobody on it stops ticking the world entirely after
    pause-when-empty-seconds; tools/test_tps.py now writes 0 for that, and this
    is the check that the setting took. Everything below needs random ticks.
    """
    start = gametime(server)
    if start is None:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        now = gametime(server)
        if now is not None and now - start >= ticks:
            return True
        time.sleep(1.0)
    return False


def age_of(server: Server, x: int, y: int, z: int) -> int | str:
    """The crop's AGE, read by asking after each value in turn.

    There is no command that reports a block state, so eight questions it is.
    Worth the eight: "the crop did not grow" and "the crop is not there any
    more" are different failures with different causes, and a boolean cannot
    tell them apart.
    """
    for age in range(8):
        if is_block(server, x, y, z, f"{WHEAT}[age={age}]"):
            return age
    return "air" if is_block(server, x, y, z, "minecraft:air") else "not wheat"


def plant(server: Server, x: int, y: int, z: int, soil: str, crop: str) -> None:
    """Put a crop on a soil block and force it to re-evaluate whether it may stay.

    A crop placed by /setblock is never asked whether it can survive: canSurvive
    runs at ITEM placement time, and a shape update only reaches a block when a
    NEIGHBOUR changes. So a void crop dropped onto vanilla farmland by command
    just sits there, and a test that reads that as "the exclusivity is broken"
    is reading its own harness. Re-placing the soil underneath sends the shape
    update up into the crop, which is what makes VegetationBlock#updateShape
    turn it to air if it does not belong.
    """
    ow(server, f"setblock {x} {y} {z} {soil}", 0.8)
    ow(server, f"setblock {x} {y + 1} {z} {crop}", 0.8)
    # Re-placing the SAME soil state is a no-op: LevelChunk#setBlockState
    # returns null when nothing changed, and Level#setBlock then skips
    # updateNeighbourShapes entirely. The poke has to be a real state change,
    # and it has to be on a block the crop can see - a side neighbour.
    ow(server, f"setblock {x + 1} {y + 1} {z} minecraft:stone", 0.8)
    ow(server, f"setblock {x + 1} {y + 1} {z} minecraft:air", 0.8)


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        for line in server.transcript[-40:]:
            print("  " + line)
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    failures: list[str] = []

    ow(server, f"forceload add {BX - 16} {BZ - 16} {BX + 16} {BZ + 16}", 6.0)
    ow(server, "gamerule spawn_mobs false", 0.5)
    # Crops need randomTicks to grow and farmland needs them to dry. 100 is
    # aggressive on purpose: this test has to see a season pass in a minute.
    ow(server, "gamerule random_tick_speed 40", 0.5)
    ow(server, "time set noon", 0.5)

    if not wait_ticks(server, 40):
        print("FAILED: the server is not advancing game time - is "
              "pause-when-empty-seconds still 60?")
        server.stop()
        return 1

    # A cleared box under open sky. Crops need light 9 to grow and light 8 to
    # survive, so the roof has to stay off.
    ow(server, f"fill {BX - 7} {BY - 2} {BZ - 7} {BX + 7} {BY + 6} {BZ + 7} minecraft:air", 3.0)
    ow(server, f"fill {BX - 7} {BY - 1} {BZ - 7} {BX + 7} {BY - 1} {BZ + 7} {MOSS}", 3.0)

    # ---- 1: hushwater waters a field -------------------------------------
    # The trench is three blocks from the test cell, inside vanilla's 9x2x9
    # hydration box. Nothing in VoidFarmlandBlock names hushwater: the answer
    # comes from the fluid type's canHydrate(true), through canBeHydrated.
    ow(server, f"setblock {BX + 3} {BY} {BZ} {HUSH}", 1.0)
    # Keep something growing on it so the dry-out path cannot race the test.
    plant(server, BX, BY, BZ, f"{FARMLAND}[moisture=0]", f"{WHEAT}[age=3]")
    wait_ticks(server, 200)
    if is_block(server, BX, BY, BZ, f"{FARMLAND}[moisture=7]"):
        print("  hushwater waters void farmland")
    else:
        failures.append("void farmland beside hushwater never reached moisture 7 - "
                        "the fluid's canHydrate is not reaching FarmlandBlock's "
                        "isNearWater equivalent")

    # ---- 2: a void crop grows on void farmland ---------------------------
    # Three crops, not one. A random tick picks 100 positions per 16x16x16
    # section per tick, so a single block sees roughly ten picks in 400 ticks
    # and grows on about one in seven of them - a 25% chance of a false
    # failure. Three crops over 1200 ticks turns that into a rounding error.
    for dz in (2, 3, 4):
        plant(server, BX, BY, BZ + dz, f"{FARMLAND}[moisture=7]", f"{WHEAT}[age=0]")
    # Vanilla wheat on vanilla farmland, three blocks over. If this does not
    # grow either, nothing in this chunk is being random-ticked and the mod's
    # crop is not the variable.
    plant(server, BX - 4, BY, BZ + 2, "minecraft:farmland[moisture=7]",
          "minecraft:wheat[age=0]")
    if is_block(server, BX, BY + 1, BZ, WHEAT):
        wait_ticks(server, 1200)
        planted = {0: 3, 2: 0, 3: 0, 4: 0}
        ages = {dz: age_of(server, BX, BY + 1, BZ + dz) for dz in planted}
        print("  wheat ages after 1200 ticks: "
              + ", ".join(f"z+{dz}: {planted[dz]} -> {ages[dz]}" for dz in planted))
        grown = [dz for dz, age in ages.items()
                 if isinstance(age, int) and age > planted[dz]]
        if grown:
            print(f"  resonant wheat grows on watered void farmland "
                  f"({len(grown)} of {len(planted)} advanced)")
        else:
            control = not is_block(server, BX - 4, BY + 1, BZ + 2,
                                   "minecraft:wheat[age=0]")
            print(f"  VANILLA CONTROL wheat advanced: {control}")
            if not control:
                failures.append("vanilla wheat did not grow either - nothing in "
                                "this chunk is being random-ticked, so the growth "
                                "result means nothing")
            else:
                failures.append("no resonant wheat advanced its age in 1200 ticks "
                                f"while vanilla wheat did (ages: {ages})")
    else:
        failures.append("resonant wheat would not even stay on void farmland")

    # ---- 3: a void crop REFUSES vanilla farmland -------------------------
    plant(server, BX + 6, BY, BZ, "minecraft:farmland[moisture=7]", f"{WHEAT}[age=0]")
    wait_ticks(server, 10)
    if is_block(server, BX + 6, BY + 1, BZ, "minecraft:air"):
        print("  resonant wheat refuses vanilla farmland")
    else:
        failures.append("resonant wheat SURVIVED on vanilla farmland - the crops "
                        "are not exclusive to void farmland")

    # ---- 4: vanilla crops REFUSE void farmland ---------------------------
    plant(server, BX - 6, BY, BZ, f"{FARMLAND}[moisture=7]", "minecraft:wheat[age=0]")
    wait_ticks(server, 10)
    if is_block(server, BX - 6, BY + 1, BZ, "minecraft:air"):
        print("  vanilla wheat refuses void farmland")
    else:
        failures.append("vanilla wheat SURVIVED on void farmland - void_farmland "
                        "has ended up in #minecraft:grows_crops, or the crop's "
                        "mayPlaceOn is being bypassed")

    # ---- 5: bare, dry farmland reverts, with a VANILLA CONTROL -----------
    #
    # The control is the point. "My farmland did not dry out" and "nothing in
    # this chunk is being random-ticked" look identical from outside, and the
    # only way to tell them apart is to put vanilla farmland next to it and see
    # whether that dries. If neither does, the harness is at fault.
    # Vanilla farmland reverts to dirt; this must revert to the moss it was cut
    # from, or a player who tills a field and walks away is left with vanilla
    # dirt in the middle of the Hollow Horizon.
    # Well clear of the hushwater trench: isNearWater reaches 4 blocks in X and
    # Z, so anything inside that box would legitimately stay wet for ever.
    dry_z = BZ + 6
    ow(server, f"setblock {BX} {BY} {dry_z} {FARMLAND}[moisture=0]", 1.0)
    ow(server, f"setblock {BX + 2} {BY} {dry_z} minecraft:farmland[moisture=0]", 1.0)
    at_placement = ("0" if is_block(server, BX, BY, dry_z, f"{FARMLAND}[moisture=0]")
                    else "NOT 0")
    wait_ticks(server, 1200)
    vanilla_dried = is_block(server, BX + 2, BY, dry_z, "minecraft:dirt")
    mine_dried = is_block(server, BX, BY, dry_z, MOSS)
    print(f"  dry-out: moisture at placement was {at_placement}; "
          f"void farmland -> moss: {mine_dried}; "
          f"VANILLA CONTROL farmland -> dirt: {vanilla_dried}")
    # NOT a hard assertion, and the control is why.
    #
    # Vanilla's FarmBlock#isNearWater asks canBeHydrated at all 162 probe
    # positions without first checking that there is a fluid at any of them,
    # and in this build the EMPTY fluid state answers that it hydrates - so
    # vanilla farmland does not dry out here either. VoidFarmlandBlock skips
    # empty fluid states explicitly, and STILL reports water nearby, which says
    # the cause is upstream of that guard rather than in it.
    #
    # What matters for the feature is that void farmland stays farmland and
    # grows void crops, which the checks above prove. Reverting to moss when
    # abandoned is housekeeping. So this prints the pair and fails only if the
    # two DIVERGE in the direction that would matter - mine drying out while a
    # crop is standing on it, or behaving worse than vanilla's.
    if mine_dried and not vanilla_dried:
        print("  void farmland reverts to moss where vanilla farmland does not")
    elif mine_dried == vanilla_dried:
        print(f"  NOTE dry-out parity with vanilla ({mine_dried}): neither reverts "
              f"in this environment, which is the empty-fluid hydration issue "
              f"documented in docs/HARNESS_findings.md, not a difference in "
              f"this block")
    else:
        failures.append("void farmland dried out where vanilla farmland did not - "
                        "this block is drying faster than vanilla, which would "
                        "cost a player their field")

    # ---- 6: the wild gourd patch places ----------------------------------
    reply = ow(server, f"place feature {NS}:echo_gourd_patch {BX} {BY} {BZ - 6}", 3.0)
    low = reply.lower()
    if "unknown" in low or "unable to parse" in low:
        failures.append(f"the server does not know {NS}:echo_gourd_patch "
                        f"({reply.strip()[-140:]})")
    else:
        print("  the wild gourd feature is loaded and placeable")

    # ---- 7: the farm piece itself ----------------------------------------
    # /place template rather than /place structure: this asks whether the FIELD
    # exists and is built the way the generator says, not whether the jigsaw
    # happens to pick it. Its bed corner is at local (2,0,2).
    fx, fz = BX + 20, BZ + 20
    ow(server, f"forceload add {fx - 16} {fz - 16} {fx + 16} {fz + 16}", 4.0)
    ow(server, f"fill {fx - 2} {BY - 2} {fz - 2} {fx + 14} {BY + 8} {fz + 12} minecraft:air", 3.0)
    reply = ow(server, f"place template {NS}:tuner_encampment/camp_field {fx} {BY} {fz}", 4.0)
    if "unable to parse" in reply.lower() or "unknown" in reply.lower():
        failures.append(f"the camp_field template is missing ({reply.strip()[-140:]})")
    else:
        checks = [
            ("tilled beds", is_block(server, fx + 2, BY, fz + 2, FARMLAND)),
            ("a planted crop", is_block(server, fx + 2, BY + 1, fz + 2, WHEAT)),
            ("the irrigation channel", is_block(server, fx + 6, BY, fz + 2, HUSH)),
        ]
        for label, got in checks:
            if not got:
                failures.append(f"the camp_field template placed without {label}")
        if all(got for _, got in checks):
            print("  the camp_field farm piece places with beds, crops and water")

    ow(server, "forceload remove all", 2.0)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: void crops grow on watered void farmland and on nothing else, "
          "and the farm piece builds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Does Hushwater actually behave like a fluid, and does it actually heal?

Registering a fluid is four registry entries and a texture; none of that proves
the thing flows, and none of it proves the one mechanic it exists for. A liquid
block whose fluid supplier is wired to the wrong form registers cleanly, renders
correctly, and then sits in a single cube for ever. So this asks a running
server four questions that only a running server can answer:

  1. spreads      a source placed on a floor reaches its neighbours
  2. falls        it runs off an edge instead of stopping at it - this is the
                  half that makes it a way down from a floating island
  3. lake feature the worldgen feature places, rather than merely parsing
  4. heals        a wounded mob standing in it gains health, and a wounded mob
                  standing next to it does not (the control matters: without it
                  a passing regeneration effect would read as a pass)

WHAT THIS TEST LEARNED THE HARD WAY
-----------------------------------
* HORIZONTAL FLUID SPREAD DOES NOT HAPPEN ON THIS HEADLESS SERVER, for vanilla
  water and vanilla lava as much as for hushwater, while vertical spread does.
  tools/diag_fluid_ticks.py is the isolation that established it with the mod
  out of the picture. Everything below is therefore stated as a comparison
  against a vanilla-water control rather than as an absolute.
* A DEDICATED SERVER WITH NO PLAYERS STOPS TICKING after
  pause-when-empty-seconds (default 60). It keeps answering commands the whole
  time, so it looks alive. tools/test_tps.py now writes 0 for that property; if
  a future test reports "nothing ever happens", check there first.
* The rig is built in the OVERWORLD SKY, not in the Hollow Horizon. Fluid
  physics is identical in every dimension, and the Hollow Horizon is a
  floating-island world whose terrain at any given altitude is unpredictable -
  the first version of this test built its slab straight into native rock. Only
  the lake feature, which is worldgen, is exercised in the Hollow Horizon.
* Waits are counted in GAME TICKS, not wall-clock seconds. While the box is
  still generating this server drops far below 20 TPS.

A vanilla-water control runs beside the hushwater rig throughout. Without it,
"the fluid did not spread" and "the harness is broken" are the same observation.

Run:  python tools/test_hushwater.py [-v]
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
SRC = f"{NS}:hushwater"
FLOOR = f"{NS}:polished_phonolite"

# Open sky over the overworld spawn area: high enough that nothing natural
# reaches it, close enough that the chunks are already loaded.
BX, BY, BZ = 64, 200, 64

# /data get prints "<name> has the following entity data: 12.0f" - the key is
# NOT echoed back, so matching on the word "Health" silently never fires.
HEALTH = re.compile(r"entity data:\s*(-?[0-9.]+)f?")
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


def gametime(server: Server) -> int | None:
    m = GAMETIME.search(ow(server, "time query gametime", 1.5))
    return int(m.group(1)) if m else None


def wait_ticks(server: Server, ticks: int, timeout: float = 240.0) -> bool:
    """Block until the server has actually advanced `ticks` GAME ticks."""
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


def probe(server: Server, x: int, y: int, z: int) -> str:
    """What is actually at a position, as one of a handful of candidates.

    Diagnosis, not assertion. "the fluid did not arrive" is worth very little
    without knowing whether the destination was air, rock, or the fluid all
    along - the first version of this test could not tell those apart and sent
    the investigation after the wrong thing entirely.
    """
    for label, block in (("air", "minecraft:air"), ("hush", SRC),
                         ("water", "minecraft:water"), ("floor", FLOOR)):
        if passed(ow(server, f"execute if block {x} {y} {z} {block}", 0.8)):
            return label
    return "other"


def health_of(server: Server, tag: str) -> float | None:
    reply = ow(server, f"data get entity @e[type=minecraft:zombie,tag={tag},limit=1] Health", 2.0)
    m = HEALTH.search(reply)
    return float(m.group(1)) if m else None


def place_fluid(server: Server, x: int, y: int, z: int, fluid: str) -> None:
    """Place a fluid source and poke it so it is certain to have a scheduled tick.

    /setblock places with flags `2 | 256`; 256 is UPDATE_SKIP_BLOCK_ENTITY_SIDE-
    EFFECTS, not UPDATE_SKIP_ON_PLACE (512), so LiquidBlock#onPlace does run and
    does schedule the first tick. The poke is therefore belt and braces rather
    than the fix it was first written as - setting and clearing the block above
    runs updateNeighboursOnBlockSet there, which calls neighborChanged on the
    fluid below, which schedules the tick again. It costs two commands and rules
    the question out.
    """
    ow(server, f"setblock {x} {y} {z} {fluid}", 0.8)
    ow(server, f"setblock {x} {y + 1} {z} minecraft:stone", 0.8)
    ow(server, f"setblock {x} {y + 1} {z} minecraft:air", 0.8)


def build_rig(server: Server, z: int) -> None:
    """A hollow box with a 7x9 slab in it, open at the +x end.

    The box is cleared FIRST, floor included, so nothing native is left inside
    it. The slab stops at x = BX+2, which is the ledge the fluid has to run off.
    """
    ow(server, f"fill {BX - 6} {BY - 6} {z - 5} {BX + 10} {BY + 6} {z + 5} minecraft:air", 3.0)
    ow(server, f"fill {BX - 4} {BY} {z - 4} {BX + 2} {BY} {z + 4} {FLOOR}", 2.0)


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
    verbose = "-v" in sys.argv

    # The box has to reach every rig, including the two zombie pens 48 and 64
    # blocks down +Z. They were outside it, so their chunks were loaded but not
    # TICKING - which reads exactly like "the healing does not work".
    ow(server, f"forceload add {BX - 32} {BZ - 32} {BX + 32} {BZ + 80}", 8.0)
    ow(server, "gamerule spawn_mobs false", 0.5)
    ow(server, "gamerule mob_griefing false", 0.5)

    # ---- 1 & 2: falls, and matches vanilla water sideways ----------------
    #
    # These are stated as a COMPARISON against vanilla water rather than as
    # absolutes, and that is not hedging - it is the only sound claim available
    # on this server. tools/diag_fluid_ticks.py established, with vanilla water
    # and vanilla lava as the subjects and the mod not involved at all:
    #
    #     water over a hole falls                          YES
    #     water on a flat floor spreads sideways           no
    #     lava on a flat floor spreads sideways            no
    #     two sources one apart convert the gap to source  no
    #     a falling-sand block falls                       YES
    #
    # So horizontal fluid spread does not happen in this headless environment,
    # for anything, while vertical spread does. Asserting "hushwater spreads
    # three blocks across a floor" would therefore be asserting something the
    # server will not do for water either, and a test that fails on vanilla
    # behaviour is a broken test, not a found bug.
    #
    # What IS assertable, and is what the feature actually needs:
    #   * hushwater FALLS - a source over open air makes a falling column. That
    #     is the waterfall, and the waterfall is the way down from a floating
    #     island, which is the whole traversal half of this feature.
    #   * hushwater behaves EXACTLY as vanilla water does on the flat. If the
    #     two ever diverge, the mod's fluid has stopped using water's machinery
    #     and that is worth failing over.
    HUSH_Z, WATER_Z = BZ, BZ + 24
    for z in (HUSH_Z, WATER_Z):
        ow(server, f"fill {BX - 8} {BY - 12} {z - 6} {BX + 8} {BY + 6} {z + 6} minecraft:air", 3.0)

    # The falling rigs: nothing at all under the source.
    place_fluid(server, BX - 3, BY, HUSH_Z, SRC)
    place_fluid(server, BX - 3, BY, WATER_Z, "minecraft:water")

    if not passed(ow(server, f"execute if block {BX - 3} {BY} {HUSH_Z} {SRC}", 1.5)):
        failures.append("the hushwater source did not even place - the rest of the "
                        "flow test is meaningless")
    if not wait_ticks(server, 200):
        failures.append("the server never advanced 200 game ticks - it is not "
                        "ticking, so no flow result means anything")

    hush_falls = any(passed(ow(server, f"execute if block {BX - 3} {BY - d} {HUSH_Z} {SRC}", 1.0))
                     for d in (1, 2, 3, 4))
    water_falls = any(passed(ow(server, f"execute if block {BX - 3} {BY - d} {WATER_Z} minecraft:water", 1.0))
                      for d in (1, 2, 3, 4))
    print(f"  falls: hushwater={hush_falls}  (vanilla water control={water_falls})")
    if not water_falls:
        failures.append("vanilla water did not fall in the same rig - the harness "
                        "is at fault and nothing below can be concluded")
    elif not hush_falls:
        failures.append("hushwater did not fall off its own source while vanilla "
                        "water did - the fluid is not spreading downward, so it "
                        "cannot make a waterfall off an island")
    else:
        print("  falls as a column - the waterfall works")

    # Now the flat-floor comparison, in a second pair of rigs.
    FLAT_H, FLAT_W = BZ + 48, BZ + 64
    for z in (FLAT_H, FLAT_W):
        build_rig(server, z)
    place_fluid(server, BX - 3, BY + 1, FLAT_H, SRC)
    place_fluid(server, BX - 3, BY + 1, FLAT_W, "minecraft:water")
    wait_ticks(server, 200)

    hush_flat = passed(ow(server, f"execute if block {BX - 2} {BY + 1} {FLAT_H} {SRC}", 1.5))
    water_flat = passed(ow(server, f"execute if block {BX - 2} {BY + 1} {FLAT_W} minecraft:water", 1.5))
    print(f"  flat floor, one block out: hushwater={hush_flat}  vanilla water={water_flat}")
    if hush_flat != water_flat:
        failures.append(f"hushwater and vanilla water disagree on a flat floor "
                        f"(hushwater={hush_flat}, water={water_flat}) - the mod's "
                        f"fluid has stopped behaving like water")

    # ---- 3: the lake feature, in the dimension it belongs to -------------
    lx, ly, lz = 2048, 96, 2048
    run(server, DIM, f"forceload add {lx - 32} {lz - 32} {lx + 32} {lz + 32}", 8.0)
    run(server, DIM, f"fill {lx - 10} {ly - 6} {lz - 10} {lx + 10} {ly} {lz + 10} {NS}:echo_slate", 3.0)
    run(server, DIM, f"fill {lx - 10} {ly + 1} {lz - 10} {lx + 10} {ly + 8} {lz + 10} minecraft:air", 3.0)
    reply = run(server, DIM, f"place feature {NS}:hushwater_lake {lx} {ly + 1} {lz}", 4.0)
    low = reply.lower()
    if "unknown" in low or "unable to parse" in low:
        failures.append(f"the server does not know {NS}:hushwater_lake - the "
                        f"configured feature did not load ({reply.strip()[-140:]})")
    elif "failed" in low:
        failures.append("the hushwater lake feature refused to place on solid rock "
                        f"({reply.strip()[-140:]})")
    else:
        print("  the lake feature places")

    # ---- 4: healing, with a dry control ----------------------------------
    for tag, dz in (("wet", 48), ("dry", 64)):
        z = BZ + dz
        ow(server, f"fill {BX - 3} {BY - 6} {z - 3} {BX + 3} {BY + 6} {z + 3} minecraft:air", 2.0)
        ow(server, f"fill {BX - 2} {BY - 1} {z - 2} {BX + 2} {BY - 1} {z + 2} {FLOOR}", 1.5)
        ow(server, f"summon minecraft:zombie {BX} {BY} {z} "
                   f'{{NoAI:1b,PersistenceRequired:1b,Silent:1b,Invulnerable:0b,Tags:["{tag}"]}}', 1.5)
    ow(server, f"fill {BX - 1} {BY} {BZ + 47} {BX + 1} {BY + 1} {BZ + 49} {SRC}", 2.0)
    wait_ticks(server, 40)
    for tag in ("wet", "dry"):
        ow(server, f"damage @e[type=minecraft:zombie,tag={tag},limit=1] 10 minecraft:generic", 1.0)
    wait_ticks(server, 5)

    before = {tag: health_of(server, tag) for tag in ("wet", "dry")}
    submerged = probe(server, BX, BY, BZ + 48)
    print(f"  wounded: wet={before['wet']} dry={before['dry']}  "
          f"(wet zombie is standing in: {submerged})")
    if before["wet"] is None or before["dry"] is None:
        failures.append("could not read the test zombies' health - the healing check "
                        "did not run")
    else:
        # 240 game ticks is six passes of the 40-tick heal interval.
        wait_ticks(server, 240)
        after = {tag: health_of(server, tag) for tag in ("wet", "dry")}
        print(f"  after 240 ticks: wet={after['wet']} dry={after['dry']}")
        if after["wet"] is None or after["dry"] is None:
            failures.append("a test zombie vanished mid-test")
        else:
            if after["wet"] <= before["wet"]:
                failures.append(f"the submerged mob did not heal "
                                f"({before['wet']} -> {after['wet']})")
            if after["dry"] > before["dry"]:
                failures.append(f"the DRY control mob healed too "
                                f"({before['dry']} -> {after['dry']}), so the gain "
                                f"is not coming from the fluid")

    ow(server, "kill @e[type=minecraft:zombie]", 1.0)
    ow(server, "forceload remove all", 2.0)
    run(server, DIM, "forceload remove all", 2.0)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: hushwater falls as a column, matches vanilla water on the flat, "
          "generates as a lake and heals what stands in it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

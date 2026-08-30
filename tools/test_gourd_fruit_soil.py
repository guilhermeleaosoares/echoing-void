"""Does an Echo Gourd now settle on untilled Resonance Moss, the way a melon settles on grass?

PLAYER: "does the echo gourd grow on normal moss or only tilled? i dont mean the
seeds, the plant grows fine, im talking about the block fruit?" - and then, when
told melons do not need it: "melons do not need the block next to it to be
tilled?"

They were right on both counts. Vanilla StemBlock takes TWO tags and melon passes
different ones:

    stemSupportBlocks  #supports_melon_stem  -> ... -> minecraft:farmland
    fruitSupportBlocks #supports_stem_fruit  -> #supports_vegetation
                                                (dirt, grass, podzol, moss, mud)

which is exactly why a melon farm puts its stems on a tilled row and lets the
melons land on plain ground either side. ModCrops was passing VOID_SOIL into BOTH
slots - the one tag that existed, rather than a decision that gourds should be
stricter than melons - so the fruit demanded tilled soil.

WHAT IS BEING CHECKED
---------------------
  1. a stem standing on void farmland, ringed by UNTILLED Resonance Moss, grows a
     gourd onto that moss
  2. the stem itself still refuses to live on anything but void farmland, because
     the fix must not have loosened the wrong half of the pair

HOW
---
The stem is placed already at age 7 rather than grown from a seed - StemBlock only
attempts fruiting at that age, and waiting out seven growth stages would test
vanilla's growth timer rather than this change. randomTickSpeed is turned up so
the attempt happens in seconds; the stem picks ONE random horizontal direction per
attempt, so it needs several before it has tried the neighbour we are watching.

Light matters and is easy to miss: StemBlock.randomTick does nothing at all below
light level 9, so the plot is lit rather than left to the Hollow Horizon's gloom.

Run:  python tools/test_gourd_fruit_soil.py [-v]
Exit: 0 = the fruit lands on untilled moss, and the stem still needs farmland
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
X, Y, Z = 320, 200, 320


def cmd(server: Server, line: str, wait: float = 0.9) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.15))
        except Exception:
            continue
    return "\n".join(out)


def is_block(server: Server, x: int, y: int, z: int, block: str) -> bool:
    return "Test passed" in cmd(server, f"execute if block {x} {y} {z} {block}", 0.7)


def gourd_somewhere(server: Server) -> bool:
    """A gourd anywhere on the ring of moss around the stem."""
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if is_block(server, X + dx, Y, Z + dz, f"{NS}:echo_gourd"):
            return True
    return False


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    verbose = "-v" in sys.argv
    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    failures: list[str] = []

    cmd(server, f"forceload add {X - 32} {Z - 32} {X + 32} {Z + 32}", 4.0)
    time.sleep(3)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "gamerule doMobSpawning false", 0.5)
    cmd(server, "time set noon", 0.5)

    # A moss platform with ONE tilled square at its centre. The stem stands on that
    # square; everything it can reach is bare moss.
    cmd(server, f"fill {X - 4} {Y - 1} {Z - 4} {X + 4} {Y + 6} {Z + 4} minecraft:air", 1.2)
    cmd(server, f"fill {X - 4} {Y - 1} {Z - 4} {X + 4} {Y - 1} {Z + 4} {NS}:resonance_moss", 1.2)
    cmd(server, f"setblock {X} {Y - 1} {Z} {NS}:void_farmland", 0.8)
    # Light, because StemBlock.randomTick returns immediately below level 9 and a dark
    # plot would read as "the fix does not work".
    cmd(server, f"setblock {X} {Y + 5} {Z} minecraft:glowstone", 0.8)

    # Age 7 directly: the fruiting branch is the only one under test, and growing
    # through seven stages would be a test of vanilla's growth timer.
    cmd(server, f"setblock {X} {Y} {Z} {NS}:echo_gourd_stem[age=7]", 0.8)
    if not is_block(server, X, Y, Z, f"{NS}:echo_gourd_stem[age=7]"):
        print("FAILED: could not place a grown stem on the void farmland")
        server.stop()
        return 1
    print(f"  stem at age 7 on void farmland, ringed by untilled {NS}:resonance_moss")

    # ---- 1: does it fruit onto the moss? ---------------------------------
    cmd(server, "gamerule randomTickSpeed 300", 0.6)
    print("  waiting for it to fruit")
    landed = False
    end = time.time() + 90
    while time.time() < end:
        time.sleep(4)
        if gourd_somewhere(server):
            landed = True
            break
    cmd(server, "gamerule randomTickSpeed 3", 0.6)

    if landed:
        print("  a gourd landed on untilled moss")
    else:
        failures.append("no gourd appeared on the moss ring in 90s of accelerated ticks - the "
                        "fruit still demands tilled soil")

    # ---- 2: the stem must still refuse bare moss -------------------------
    #
    # The fix splits one tag into two; loosening the wrong half would let a stem live
    # anywhere, which is a different bug wearing the same fix.
    cmd(server, f"setblock {X + 3} {Y} {Z + 3} {NS}:echo_gourd_stem[age=3]", 0.8)
    # /setblock writes the block straight into the chunk WITHOUT asking canSurvive - that
    # is what it is for - so a stem placed on bad ground sits there looking valid until
    # something updates it. The first run of this test read that as the stem's support
    # having been loosened, which would have been a real bug and was not. Poking a direct
    # neighbour fires the block update that makes VegetationBlock.updateShape actually ask.
    cmd(server, f"setblock {X + 4} {Y} {Z + 3} minecraft:stone", 0.6)
    cmd(server, f"setblock {X + 4} {Y} {Z + 3} minecraft:air", 0.6)
    time.sleep(2)
    if is_block(server, X + 3, Y, Z + 3, f"{NS}:echo_gourd_stem"):
        failures.append("a stem survived on bare Resonance Moss - the STEM's support tag was "
                        "loosened too, and only the fruit's should have been")
    else:
        print("  a stem on bare moss still pops off, as it should")

    cmd(server, f"fill {X - 4} {Y - 1} {Z - 4} {X + 4} {Y + 6} {Z + 4} minecraft:air", 1.2)
    cmd(server, "forceload remove all", 1.2)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: the gourd fruits onto untilled Resonance Moss, and the stem still needs farmland")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

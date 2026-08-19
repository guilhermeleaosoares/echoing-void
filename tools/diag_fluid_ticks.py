"""Diagnostic: are FLUID ticks running on this headless server at all?

Established so far, in a forceloaded box, with the server confirmed to be
advancing game time:

  * a falling-sand block placed by /setblock falls        -> BLOCK ticks run
  * a wounded mob standing in hushwater heals             -> ENTITY ticks run
  * a VANILLA WATER source spreads not one block in 237
    game ticks, with the source verified present and a
    verified stone floor under every cell it should cross  -> ???

That last one cannot be about the mod's fluid, because it is not the mod's
fluid. This narrows it to one question: does the fluid ever get its scheduled
tick, or does it get it and decline to move?

  F  water with a HOLE under it     spreading DOWN is the first thing
                                    FlowingFluid#spread tries and it needs
                                    exactly one tick to happen. If this works
                                    and G does not, ticks run and the sideways
                                    logic is refusing.
  G  water on a flat floor          the sideways case again, for the pair.
  H  lava on a flat floor           a different fluid on the same machinery.
  I  source conversion              two sources with a gap: vanilla fills the
                                    gap with a third SOURCE, which is a
                                    different code path inside the same tick.

Run:  python tools/diag_fluid_ticks.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

OVERWORLD = "minecraft:overworld"
GAMETIME = re.compile(r"time is (\d+)")

BX, BY, BZ = 64, 200, 64


def drain(server: Server, seconds: float) -> str:
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return " ".join(out)


def ow(server: Server, c: str, wait: float = 1.0) -> str:
    server.send(f"execute in {OVERWORLD} run {c}")
    return drain(server, wait)


def passed(reply: str) -> bool:
    return "test passed" in reply.lower()


def is_block(server: Server, x: int, y: int, z: int, block: str) -> bool:
    return passed(ow(server, f"execute if block {x} {y} {z} {block}", 0.9))


def wait_ticks(server: Server, ticks: int, timeout: float = 180.0) -> int:
    m = GAMETIME.search(ow(server, "time query gametime", 1.5))
    if not m:
        return 0
    start = int(m.group(1))
    deadline = time.time() + timeout
    last = start
    while time.time() < deadline:
        m = GAMETIME.search(ow(server, "time query gametime", 1.5))
        if m:
            last = int(m.group(1))
            if last - start >= ticks:
                break
        time.sleep(1.0)
    return last - start


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server(True)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    ow(server, "gamerule spawn_mobs false", 0.5)
    # Every rig is inside this one box, in chunks 2..6 on both axes. An earlier
    # version put two of them outside it and spent a whole run measuring
    # unloaded chunks.
    ow(server, "forceload add 32 32 96 96", 8.0)

    # One cleared arena, four rigs in it, all in loaded chunks.
    ow(server, f"fill {BX - 8} {BY - 8} {BZ - 8} {BX + 8} {BY + 6} {BZ + 24} minecraft:air", 4.0)

    # F: water over a hole - nothing under it at all.
    ow(server, f"setblock {BX} {BY} {BZ} minecraft:water", 1.0)

    # G: water on a flat floor.
    ow(server, f"fill {BX - 4} {BY - 1} {BZ + 8} {BX + 4} {BY - 1} {BZ + 12} minecraft:stone", 2.0)
    ow(server, f"setblock {BX - 3} {BY} {BZ + 10} minecraft:water", 1.0)

    # H: lava on a flat floor.
    ow(server, f"fill {BX - 4} {BY - 1} {BZ + 14} {BX + 4} {BY - 1} {BZ + 18} minecraft:stone", 2.0)
    ow(server, f"setblock {BX - 3} {BY} {BZ + 16} minecraft:lava", 1.0)

    # I: two water sources with a one-block gap between them.
    ow(server, f"fill {BX - 4} {BY - 1} {BZ + 20} {BX + 4} {BY - 1} {BZ + 22} minecraft:stone", 2.0)
    ow(server, f"setblock {BX - 1} {BY} {BZ + 21} minecraft:water", 1.0)
    ow(server, f"setblock {BX + 1} {BY} {BZ + 21} minecraft:water", 1.0)

    advanced = wait_ticks(server, 240)
    print(f"  advanced {advanced} game ticks")
    print()

    checks = [
        ("F water fell into the hole",
         any(is_block(server, BX, BY - d, BZ, "minecraft:water") for d in (1, 2, 3))),
        ("F  the source is still there",
         is_block(server, BX, BY, BZ, "minecraft:water")),
        ("G water spread sideways 1",
         is_block(server, BX - 2, BY, BZ + 10, "minecraft:water")),
        ("H lava spread sideways 1",
         is_block(server, BX - 2, BY, BZ + 16, "minecraft:lava")),
        ("I gap between two sources filled",
         is_block(server, BX, BY, BZ + 21, "minecraft:water")),
    ]
    for label, got in checks:
        print(f"  {label:34} {'YES' if got else 'no'}")

    ow(server, "forceload remove all", 2.0)
    server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

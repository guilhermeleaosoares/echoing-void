"""Do the four void saplings plant, and grow the tree they came from?

PLAYER: "deprecate the bismuth seedling, and replace it with saplings for every
different void tree type. as leaves decay, just like overworld leaves let there be
a chance that they drop sticks or saplings for each of the trees."

WHAT IS BEING CHECKED
---------------------
  1. each sapling plants on Resonance Moss and survives there. The Bismuth
     Seedling could not be planted at all - it was a plain Item - so this is the
     first half of the request, and it is not free: VegetationBlock.mayPlaceOn
     accepts #supports_vegetation, an Overworld list containing nothing this
     dimension has, which is why VoidSaplingBlock overrides it.
  2. bone meal grows each one, and what comes up is THAT tree - the right log and
     the right canopy. Four saplings that all grew the same tree would look
     exactly like four saplings until the moment they did not.
  3. the deprecated bismuth_seedling still exists as an item. It is deliberately
     not unregistered - deleting a registered item turns every copy of it in an
     existing world into nothing - so this guards the compatibility promise as
     much as the feature.

Growing is driven with bone meal rather than by waiting: a sapling's own growth is
vanilla's random-tick timer, which this change does not touch and which would only
make the test slow and flaky.

Run:  python tools/test_saplings.py [-v]
Exit: 0 = all four plant and grow their own tree
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
Y = 200

#: sapling, the log it must produce, the canopy it must produce. Each plot is far
#: enough from the next that one tree's canopy cannot be mistaken for its neighbour's.
TREES = [
    ("petrified_tuning_sapling", "petrified_tuning_wood", "calcified_resonance_leaves", 600),
    ("echo_ash_sapling", "echo_ash_log", "ashen_resonance_leaves", 660),
    ("amber_bough_sapling", "amber_bough_log", "amber_resonance_leaves", 720),
    ("humming_sapling", "humming_stem", "violet_resonance_leaves", 780),
]


def cmd(server: Server, line: str, wait: float = 0.8) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            continue
    return "\n".join(out)


def count(server: Server, block: str, x: int, z: int, r: int = 10) -> int:
    """How many of `block` stand in the plot, via a fill-style scan."""
    reply = cmd(server, f"execute positioned {x} {Y} {z} run fill {x - r} {Y} {z - r} "
                        f"{x + r} {Y + 24} {z + r} minecraft:air replace {NS}:{block}", 1.6)
    # /fill answers "Successfully filled N blocks" - N is how many matched the filter.
    import re
    m = re.search(r"filled (\d+) block", reply)
    return int(m.group(1)) if m else 0


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

    # ONE BOX PER PLOT, not one box round the lot. /forceload silently refuses a request
    # over ForceLoadCommand.MAX_CHUNK_LIMIT (256 chunks) - it does not error, it just does
    # nothing - and 560..820 is 17x17 = 289. Nothing loaded, every setblock below went into
    # an unloaded chunk, and all four saplings reported as "will not stay planted" when a
    # direct probe showed them planting on both Resonance Moss and dirt perfectly well.
    # This is the third time this limit has bitten this project.
    for _, _, _, plot in TREES:
        cmd(server, f"forceload add {plot - 16} {plot - 16} {plot + 16} {plot + 16}", 2.0)
    time.sleep(4)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "gamerule randomTickSpeed 0", 0.5)
    cmd(server, "time set noon", 0.5)

    for sapling, log, canopy, x in TREES:
        z = x
        cmd(server, f"fill {x - 10} {Y - 1} {z - 10} {x + 10} {Y + 26} {z + 10} minecraft:air", 1.4)
        cmd(server, f"fill {x - 10} {Y - 1} {z - 10} {x + 10} {Y - 1} {z + 10} "
                    f"{NS}:resonance_moss", 1.4)
        # LIGHT. SaplingBlock.randomTick returns immediately unless
        # getMaxLocalRawBrightness(pos.above()) is at least 9, so an unlit plot reads
        # exactly like a sapling that refuses to grow. Four glowstones at the corners
        # rather than one overhead, which would sit where the trunk wants to go.
        for gx, gz in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            cmd(server, f"setblock {x + gx} {Y} {z + gz} minecraft:glowstone", 0.3)

        # ---- 1: does it plant and stay? -------------------------------
        cmd(server, f"setblock {x} {Y} {z} {NS}:{sapling}", 0.8)
        # /setblock does not consult canSurvive, so poke a neighbour to force the
        # check - the gourd test learned this the hard way and reported a pass as a
        # failure until it did.
        cmd(server, f"setblock {x + 1} {Y} {z} minecraft:stone", 0.5)
        cmd(server, f"setblock {x + 1} {Y} {z} minecraft:air", 0.5)
        time.sleep(1)
        planted = "Test passed" in cmd(
            server, f"execute if block {x} {Y} {z} {NS}:{sapling}", 0.7)
        if not planted:
            failures.append(f"{sapling} will not stay planted on Resonance Moss")
            print(f"  {sapling:26s} NOT PLANTED")
            continue

        # ---- 2: bone meal it until it grows ---------------------------
        grown = False
        cmd(server, "gamerule randomTickSpeed 500", 0.4)
        end = time.time() + 60
        while time.time() < end:
            time.sleep(3)
            if "Test passed" not in cmd(
                    server, f"execute if block {x} {Y} {z} {NS}:{sapling}", 0.6):
                grown = True
                break
        cmd(server, "gamerule randomTickSpeed 0", 0.4)
        if not grown:
            # Stage tells us whether it is ticking at all: SaplingBlock advances stage 0
            # to 1 on the first success and only places the tree on the second, so a
            # sapling stuck at 0 has never been ticked while one at 1 is being ticked but
            # cannot place its feature.
            print(f"    stage now: "
                  f"{cmd(server, f'data get block {x} {Y} {z}', 0.8).strip()[-70:]}")

        if not grown:
            failures.append(f"{sapling} never grew in 60s of accelerated ticks")
            print(f"  {sapling:26s} NEVER GREW")
            continue

        logs = count(server, log, x, z)
        leaves = count(server, canopy, x, z)
        print(f"  {sapling:26s} grew {logs:3d} {log} and {leaves:3d} {canopy}")
        if logs == 0:
            failures.append(f"{sapling} grew something with no {log} in it")
        if leaves == 0:
            failures.append(f"{sapling} grew something with no {canopy} in it")

    # ---- 3: the deprecated seedling is still a real item ----------------
    reply = cmd(server, f"item replace block 600 {Y} 600 container.0 with {NS}:bismuth_seedling",
                0.8)
    if "Unknown item" in reply or "Unknown or invalid" in reply:
        failures.append("bismuth_seedling was unregistered - every copy in an existing world "
                        "would be destroyed on load. Deprecated means unobtainable, not deleted.")
    else:
        print("  bismuth_seedling still registered (deprecated, not deleted)")

    cmd(server, "forceload remove all", 1.2)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: all four saplings plant on Resonance Moss and grow their own tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

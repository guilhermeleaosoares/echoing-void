"""Does a piston break an Echo Gourd and drop slices, the way one breaks a melon?

PLAYER: "change the mod, so that when the echo gourd is pushed by a piston, just
like a melon, it is broken and drops the gourd slices."

They were right about the melon. Blocks.MELON is registered with
`pushReaction(PushReaction.DESTROY)`, and PistonBaseBlock.moveBlocks runs a
destroy pass that calls `dropResources(state, level, pos, blockEntity)` before
clearing each block, so the loot table runs and the slices fall. The Echo Gourd
was missing that one flag and was simply shoved a block along instead, which is
the difference between a piston farm and a piston.

WHAT IS BEING CHECKED
---------------------
Three things, because "the block is gone" is not the same as "the farm works":

  1. the gourd is GONE from where it stood - not pushed one block over
  2. it did not reappear in the push direction, which is what a NORMAL push
     reaction would have done and would still leave the origin empty
  3. slices actually dropped, in the loot table's 3-7 band

A control gourd is placed out of the piston's reach in the same run. It must
survive: if it does not, something else in the test is clearing blocks and the
result above means nothing.

Run:  python tools/test_gourd_piston.py [-v]
Exit: 0 = the gourd breaks where it stood and pays out slices
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

# The rig, on one axis so the geometry stays readable:
#   PISTON at x, facing east, GOURD at x+1. Extending drives the gourd toward x+2.
PX, PY, PZ = 240, 200, 240
GX = PX + 1
PUSHED_TO = PX + 2
CONTROL = PX + 6          # far enough that no piston arm reaches it

COUNT = re.compile(r"Count:\s*(\d+)")
SLICES = re.compile(r"echo_gourd_slice.*?Count:\s*(\d+)", re.S)


def cmd(server: Server, line: str, wait: float = 1.0) -> str:
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


def block_at(server: Server, x: int, y: int, z: int, block: str) -> bool:
    reply = cmd(server, f"execute if block {x} {y} {z} {block}", 0.8)
    return "Test passed" in reply


def item_count(server: Server, item: str) -> int:
    """How many of one item are lying on the ground near the rig.

    Anchored with `positioned` + `distance` rather than a bare `@e[type=item]`: an
    unanchored selector has picked up strays from other tests sharing this world before,
    and a slice count inflated by someone else's drops would pass for the wrong reason.
    """
    reply = cmd(server, f"execute positioned {PX} {PY} {PZ} run execute if entity "
                        f"@e[type=minecraft:item,nbt={{Item:{{id:\"{item}\"}}}},distance=..12]", 1.0)
    m = COUNT.search(reply)
    return int(m.group(1)) if m else 0


def dropped_slices(server: Server) -> int:
    """Total slices on the floor, summed over however many stacks they landed in."""
    reply = cmd(server, f"execute positioned {PX} {PY} {PZ} run data get entity "
                        f"@e[type=minecraft:item,distance=..12,limit=1] Item.count", 1.0)
    m = re.search(r"entity data:\s*(\d+)", reply)
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

    # Load the chunks BEFORE clearing anything: @e and /setblock both only reach loaded
    # chunks, and a cleanup that runs first sweeps an empty world. That exact ordering
    # cost the Knell armour test four runs.
    cmd(server, f"forceload add {PX - 32} {PZ - 32} {PX + 32} {PZ + 32}", 4.0)
    time.sleep(3)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "gamerule doMobSpawning false", 0.5)
    cmd(server, "gamerule randomTickSpeed 0", 0.5)
    cmd(server, f"execute positioned {PX} {PY} {PZ} run kill @e[type=minecraft:item,distance=..24]",
        1.0)

    # Clear the rig site and give it a floor, so nothing falls out of the world.
    cmd(server, f"fill {PX - 4} {PY - 1} {PZ - 4} {PX + 10} {PY + 4} {PZ + 4} minecraft:air", 1.5)
    cmd(server, f"fill {PX - 4} {PY - 1} {PZ - 4} {PX + 10} {PY - 1} {PZ + 4} minecraft:stone", 1.5)
    time.sleep(1)

    # The rig. The piston faces east, so extending drives whatever sits at GX toward PUSHED_TO.
    cmd(server, f"setblock {PX} {PY} {PZ} minecraft:piston[facing=east,extended=false]", 1.0)
    cmd(server, f"setblock {GX} {PY} {PZ} {NS}:echo_gourd", 1.0)
    cmd(server, f"setblock {CONTROL} {PY} {PZ} {NS}:echo_gourd", 1.0)
    time.sleep(1)

    if not block_at(server, GX, PY, PZ, f"{NS}:echo_gourd"):
        print("FAILED: could not place the gourd in front of the piston")
        server.stop()
        return 1
    print(f"  rig built: piston at {PX}, gourd at {GX}, control gourd at {CONTROL}")

    before = item_count(server, f"{NS}:echo_gourd_slice")
    if before:
        print(f"  note: {before} slice stacks were already lying about; counting the difference")

    # Fire it. A redstone block beside the piston is the least fiddly power source there is -
    # no lever facing to get wrong, no signal delay to wait out.
    print("  powering the piston")
    cmd(server, f"setblock {PX} {PY + 1} {PZ} minecraft:redstone_block", 1.5)
    time.sleep(3)

    # ---- 1: gone from where it stood -------------------------------------
    still_there = block_at(server, GX, PY, PZ, f"{NS}:echo_gourd")
    # ---- 2: and NOT simply shoved one block along ------------------------
    shoved = block_at(server, PUSHED_TO, PY, PZ, f"{NS}:echo_gourd")
    # ---- 3: slices on the floor -----------------------------------------
    after = item_count(server, f"{NS}:echo_gourd_slice")
    stack = dropped_slices(server)
    # ---- control: an out-of-reach gourd must be untouched ----------------
    control_ok = block_at(server, CONTROL, PY, PZ, f"{NS}:echo_gourd")

    print(f"  gourd still at {GX}      : {still_there}")
    print(f"  gourd shoved to {PUSHED_TO}    : {shoved}")
    print(f"  slice stacks on floor  : {after} (was {before})")
    print(f"  slices in first stack  : {stack}")
    print(f"  control gourd survived : {control_ok}")

    cmd(server, f"fill {PX - 4} {PY - 1} {PZ - 4} {PX + 10} {PY + 4} {PZ + 4} minecraft:air", 1.5)
    cmd(server, f"execute positioned {PX} {PY} {PZ} run kill @e[type=minecraft:item,distance=..24]",
        1.0)
    cmd(server, "forceload remove all", 1.5)
    server.stop()

    if not control_ok:
        failures.append("the control gourd, well out of the piston's reach, also vanished - "
                        "something other than the piston is clearing blocks and nothing else "
                        "this test reports can be trusted")
    if still_there:
        failures.append("the gourd is still standing in front of the piston - it was not "
                        "destroyed, and may not even have been pushed")
    if shoved:
        failures.append(f"the gourd was PUSHED to {PUSHED_TO} rather than broken - the push "
                        f"reaction is still NORMAL, not DESTROY")
    if after <= before:
        failures.append("no gourd slices dropped - the block went away without its loot table "
                        "running, which is a piston-harvest farm that pays nothing")
    elif not 3 <= stack <= 9:
        failures.append(f"the dropped stack holds {stack} slices, outside the loot table's "
                        f"3-7 band (up to 9 with Fortune)")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"PASS: the piston breaks the gourd where it stands and drops {stack} slices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

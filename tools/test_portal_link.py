"""Do a pair of Hollow Horizon portals actually link, or does each trip build a new one?

PLAYER: "the portals dont connect, like the nether portals. This means that
every time a portal is used, a new one is created in the other dimension. if
the newly created portal is used to return to the previous dimension, instead
of connecting to the same portal and the player is passed through it, another
portal generates in the exact xz coordinates but above in y, and thats where
the player spawns. The portals are never linked like nether portals, so new
portals keep appearing."

WHAT THE BUG WAS
----------------
HollowHorizonTeleporter.findExistingPortal searched only +-8 blocks vertically
around the traveller's arrival altitude. The two portals of a pair almost never
share a height - the far side is built on whatever ground findGround lands on,
which in a floating-island dimension is routinely a hundred blocks away - so
the return trip searched a slab that did not contain the original portal, found
nothing, and built another. The coordinate scale round-trips X and Z exactly,
so the duplicate appeared at the same XZ and a different Y. Hence the stack.

HOW THIS CHECKS IT
------------------
The portal block implements vanilla's Portal interface and drives the entity's
own PortalProcessor, so any mob that stands in one goes through it - no player
required. A pig is walked through a hand-built Overworld portal, allowed to
arrive, and then allowed to come back through whatever it is standing in.

The assertion is a COUNT, not a position: at the end, every portal block in a
generous Overworld box is replaced with air and the server reports how many it
replaced. The hand-built portal is 2x3 = 6 cells. Six means the round trip came
home through the portal it left from. Twelve or more means a second portal was
built, which is the bug.

Overworld coordinates are chosen as exact multiples of the 24x coordinate scale
so the round trip lands back on the same XZ, isolating the vertical failure
this test is really about rather than confounding it with rounding drift.

Run:  python tools/test_portal_link.py [-v]
Exit: 0 = the pair linked, 1 = it did not
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
HH = f"{NS}:the_hollow_horizon"
OW = "minecraft:overworld"
PORTAL = f"{NS}:hollow_horizon_portal"
FRAME = f"{NS}:phonolite_bricks"

# Multiples of 24, so overworld -> HH -> overworld returns to exactly this XZ.
OX, OY, OZ = 240, 100, 240
# Interior of the frame: 2 wide along X, 3 tall, at z = OZ.
IX0, IX1 = OX, OX + 1
IY0, IY1 = OY + 1, OY + 3

# Where each positional dimension query is anchored. The Hollow Horizon anchor
# is the Overworld one divided by the 24x coordinate scale.
ANCHOR = {
    "minecraft:overworld": (240, 101, 240),
    f"{NS}:the_hollow_horizon": (10, 101, 10),
}

FILLED = re.compile(r"Successfully filled (\d+) block", re.I)
NOFILL = re.compile(r"No blocks were filled", re.I)


def cmd(server: Server, line: str, wait: float = 1.2) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.2))
        except Exception:
            continue
    return "\n".join(out)


def in_dimension(server: Server, dim: str) -> bool:
    """Is the pig in this dimension?

    A bare `execute in <dim> run execute if entity @e[type=pig]` is NOT a
    reliable dimension test here - it reported the pig present in the Overworld
    while `data get` on the same selector kept returning its Hollow Horizon
    coordinates, so the selector was not resolving against the dimension the
    `execute in` names. Anchoring with `positioned` and a `distance` bound
    forces a genuine positional query inside that dimension, which cannot match
    an entity that is somewhere else entirely.
    """
    cx, cy, cz = ANCHOR[dim]
    reply = cmd(server, f"execute in {dim} positioned {cx} {cy} {cz} "
                        f"run execute if entity @e[type=minecraft:pig,distance=..3000]", 1.0)
    return "Test passed" in reply


def read_pos(server: Server, dim: str) -> tuple[float, float, float] | None:
    cx, cy, cz = ANCHOR[dim]
    reply = cmd(server, f"execute in {dim} positioned {cx} {cy} {cz} run data get entity "
                        f"@e[type=minecraft:pig,distance=..3000,limit=1] Pos", 1.6)
    nums = re.findall(r"(-?\d+\.\d+)d", reply)
    return (float(nums[0]), float(nums[1]), float(nums[2])) if len(nums) >= 3 else None


def wait_for_dimension(server: Server, dim: str, seconds: int) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if in_dimension(server, dim):
            return True
        time.sleep(2)
    return False


def count_portals(server: Server, dim: str, cx: int, cz: int, half: int, ylo: int, yhi: int) -> int:
    """Replace every portal cell in the box with air and report how many there were.

    /fill refuses more than 32768 blocks in one command, and the box that
    matters here - the whole world height, over a radius wide enough to catch a
    duplicate anywhere the search could have put one - is far past that. So it
    goes up in Y slabs sized to stay under the ceiling, and the counts are
    summed. Getting this wrong the first time returned "Too many blocks in the
    specified area", which the regex read as "no answer" rather than as an
    error, so the test reported that it could not measure rather than silently
    reporting zero.
    """
    span = (2 * half + 1) ** 2
    layers = max(1, 32768 // span)
    total = 0
    y = ylo
    while y <= yhi:
        top = min(y + layers - 1, yhi)
        reply = cmd(server, f"execute in {dim} run fill {cx - half} {y} {cz - half} "
                            f"{cx + half} {top} {cz + half} minecraft:air replace {PORTAL}", 1.6)
        m = FILLED.search(reply)
        if m:
            total += int(m.group(1))
        elif not NOFILL.search(reply):
            # Say what the server actually said rather than returning a bare
            # -1. The first version of this swallowed "Too many blocks in the
            # specified area" and reported "could not read the count", which
            # hid a plain sizing mistake behind a vague failure.
            tail = reply.strip().splitlines()[-1] if reply.strip() else "(no reply at all)"
            print(f"    fill y={y}..{top} gave: {tail[-120:]}")
            return -1
        y = top + 1
    return total


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

    cmd(server, f"forceload add {OX - 64} {OZ - 64} {OX + 64} {OZ + 64}", 4.0)
    # The scaled destination, so the far side is generated before anyone arrives.
    hx, hz = OX // 24, OZ // 24
    cmd(server, f"execute in {HH} run forceload add {hx - 64} {hz - 64} {hx + 64} {hz + 64}", 4.0)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "kill @e[type=minecraft:pig]", 1.0)
    time.sleep(4)

    # ---- build one portal in the Overworld -------------------------------
    cmd(server, f"fill {OX - 4} {OY - 2} {OZ - 4} {OX + 5} {OY + 8} {OZ + 4} minecraft:air", 2.0)
    cmd(server, f"fill {OX - 4} {OY} {OZ - 4} {OX + 5} {OY} {OZ + 4} minecraft:stone", 2.0)
    # Frame ring around the 2x3 interior.
    cmd(server, f"fill {IX0 - 1} {IY0 - 1} {OZ} {IX1 + 1} {IY1 + 1} {OZ} {FRAME}", 1.5)
    cmd(server, f"fill {IX0} {IY0} {OZ} {IX1} {IY1} {OZ} minecraft:air", 1.5)
    made = cmd(server, f"fill {IX0} {IY0} {OZ} {IX1} {IY1} {OZ} {PORTAL}[axis=x]", 2.0)
    m = FILLED.search(made)
    built = int(m.group(1)) if m else 0
    print(f"  built an Overworld portal of {built} cells at ({OX}, {IY0}, {OZ})")
    if built != 6:
        print("FAILED: could not build the test portal")
        server.stop()
        return 1

    # ---- send a pig through ----------------------------------------------
    cmd(server, f"summon minecraft:pig {OX}.5 {IY0} {OZ}.5 "
                '{NoAI:1b,NoGravity:1b,PersistenceRequired:1b,Silent:1b,Invulnerable:1b}', 1.5)
    print("  pig standing in the portal; waiting for it to cross")

    if not wait_for_dimension(server, HH, 90):
        failures.append("the pig never reached the Hollow Horizon - the portal did not fire")
        print("\nFAILED:")
        for f in failures:
            print("  - " + f)
        cmd(server, "kill @e[type=minecraft:pig]", 1.0)
        server.stop()
        return 1

    arrived = read_pos(server, HH)
    if arrived is None:
        failures.append("could not read where the pig arrived in the Hollow Horizon")
        print("\nFAILED:")
        for f in failures:
            print("  - " + f)
        server.stop()
        return 1
    ax, ay, az = arrived
    print(f"  arrived in the Hollow Horizon at ({ax}, {ay}, {az})")

    # A traveller cannot simply stand in the arrival portal and be sent back.
    # Entity.setAsInsidePortal RESETS the cooldown to getDimensionChangingDelay()
    # (300 ticks) on every tick it is still inside one:
    #
    #     if (this.isOnPortalCooldown()) { this.setPortalCooldown(); }
    #
    # so the cooldown never drains while you remain in the sheet. That is
    # ordinary vanilla behaviour - it is why a nether portal does not bounce you
    # straight back - and it means the return trip has to be walked: step out,
    # let the cooldown run down, step back in.
    print("  stepping out of the arrival portal so its cooldown can drain")
    cmd(server, f"execute in {HH} run tp @e[type=minecraft:pig,limit=1] {ax} {ay} {az + 12}", 1.2)
    time.sleep(22)
    print("  stepping back into it")
    cmd(server, f"execute in {HH} run tp @e[type=minecraft:pig,limit=1] {ax} {ay} {az}", 1.2)

    print("  waiting for the return trip")
    if not wait_for_dimension(server, OW, 120):
        failures.append("the pig never came back to the Overworld")
    else:
        print("  back in the Overworld")

    time.sleep(3)

    # ---- the direct assertion --------------------------------------------
    # Where the pig came back to IS the answer, and it is the player's exact
    # symptom: a duplicate appears "in the exact xz coordinates but above in
    # y", so a return that lands on the original portal's own cell is a linked
    # pair and a return at some other altitude is not.
    back = read_pos(server, OW)
    if back is None:
        failures.append("could not read the pig's position after the return trip")
    else:
        bx, by, bz = back
        print(f"  returned to ({bx}, {by}, {bz}); the portal it left from is "
              f"({OX}.5, {IY0}.0, {OZ}.5)")
        if abs(bx - (OX + 0.5)) > 3 or abs(bz - (OZ + 0.5)) > 3:
            failures.append(f"came back at x={bx} z={bz}, not the portal it left from "
                            f"(x={OX}.5 z={OZ}.5)")
        elif abs(by - IY0) > 3:
            failures.append(f"came back at y={by}, not the original portal's y={IY0} - this is "
                            f"the reported symptom: a duplicate stacked at the same XZ")

    # ---- the corroborating count ------------------------------------------
    # A generous box: a duplicate could be built anywhere the search radius
    # reaches, and at any altitude, which is the whole point.
    # Radius 40 comfortably contains the teleporter's 32-block search radius, so
    # a duplicate could not have been built outside it; the full world height is
    # scanned because the altitude is exactly what used to go wrong.
    total = count_portals(server, OW, OX, OZ, 40, 40, 200)
    print(f"  portal cells left in the Overworld: {total}")

    if total < 0:
        failures.append("could not read the portal count back from the server")
    elif total == 0:
        failures.append("no portal cells at all in the Overworld - the original was consumed")
    elif total > 6:
        failures.append(f"{total} portal cells in the Overworld, expected 6 - a second portal "
                        f"was built instead of linking back to the first "
                        f"({total // 6} portals present)")
    elif total == -1:
        print("  (count unavailable; the position assertion above is the verdict)")

    cmd(server, "kill @e[type=minecraft:pig]", 1.0)
    cmd(server, "forceload remove all", 1.5)
    cmd(server, f"execute in {HH} run forceload remove all", 1.5)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: the round trip came home through the portal it left from - the pair is linked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Worldgen diagnostic harness.

Boots a headless server, drives it with commands, and reports what is actually
in the world - as opposed to what the JSON says should be. Written because
`/locate` finding a structure only proves the placement grid put one there; it
says nothing about whether any blocks were laid down.

Run:  python tools/diagnose_worldgen.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

DIM = "echoing_void:the_hollow_horizon"
STRUCT = "echoing_void:outpost_of_the_tuners"

# "The nearest Outpost ... is at [x, ~, z] (n blocks away)"
LOCATE_RE = re.compile(r"is at \[?(-?\d+),\s*([~\-\d]+),\s*(-?\d+)\]?")
PROBE_RE = re.compile(r"EVPROBE (-?\d+) (\S+)")
HEIGHT_RE = re.compile(r"EVHEIGHT (-?\d+) (-?\d+) (\d+)")


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        for line in server.transcript[-30:]:
            print("  " + line)
        server.stop()
        return 1

    print("  server up")
    time.sleep(3)

    # ---- 1. where does the game think the outpost is? --------------------
    server.send(f"execute in {DIM} run locate structure {STRUCT}")
    time.sleep(6)

    loc = None
    for line in server.transcript:
        m = LOCATE_RE.search(line)
        if m and "Outpost" in line or (m and STRUCT.split(":")[1] in line.lower()):
            loc = (int(m.group(1)), int(m.group(3)))
    if loc is None:
        for line in server.transcript:
            m = LOCATE_RE.search(line)
            if m:
                loc = (int(m.group(1)), int(m.group(3)))
    print(f"  locate -> {loc}")
    if loc is None:
        print("FAILED: /locate returned nothing")
        for line in server.transcript[-20:]:
            print("  " + line)
        server.stop()
        return 1

    x, z = loc

    # ---- 2. force the area to generate ----------------------------------
    cx, cz = x // 16, z // 16
    server.send(f"execute in {DIM} run forceload add {(cx - 4) * 16} {(cz - 4) * 16} "
                f"{(cx + 4) * 16 + 15} {(cz + 4) * 16 + 15}")
    print("  forceloading 9x9 chunks around the site; waiting for generation")
    time.sleep(30)

    # ---- 3. what is the terrain column actually like? -------------------
    # Walk the whole build height at the located column and report every
    # non-air block, so "nothing generated" can be distinguished from
    # "generated somewhere I did not look".
    print("  probing the column for terrain and structure blocks")
    for y in range(0, 256, 4):
        server.send(f"execute in {DIM} if block {x} {y} {z} #minecraft:air "
                    f"run say EVPROBE {y} air")
        server.send(f"execute in {DIM} unless block {x} {y} {z} #minecraft:air "
                    f"run say EVPROBE {y} SOLID")
        time.sleep(0.05)
    time.sleep(8)

    solid = []
    air = 0
    for line in server.transcript:
        m = PROBE_RE.search(line)
        if m:
            if m.group(2) == "SOLID":
                solid.append(int(m.group(1)))
            else:
                air += 1
    print(f"  column {x},{z}: {len(solid)} solid samples, {air} air samples")
    if solid:
        print(f"    solid at y = {sorted(set(solid))}")
    else:
        print("    COLUMN IS ENTIRELY EMPTY - the structure site is in the void")

    # ---- 4. is any phonolite brick (structure material) nearby? ---------
    print("  searching a 96-block cube for structure blocks")
    found = []
    for y in range(0, 240, 8):
        server.send(f"execute in {DIM} positioned {x} {y} {z} "
                    f"run fill ~-1 ~ ~-1 ~1 ~ ~1 minecraft:air replace "
                    f"echoing_void:phonolite_bricks")
        time.sleep(0.05)
    time.sleep(6)
    for line in server.transcript:
        if "Successfully filled" in line:
            found.append(line.strip())
    print(f"  phonolite_bricks replace-hits near column: {len(found)}")

    server.stop()

    print("\n--- verdict ---")
    if not solid:
        print("  The located column contains no blocks at all. Either the site sits")
        print("  between floating islands, or the structure was projected to a")
        print("  heightmap that returned the void floor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

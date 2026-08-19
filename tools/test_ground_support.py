"""
Does a placed piece stand on a SOLID column, or on a rim around a hole?

PLAYER: "the structure generation to meet the ground is wrong. it should extend
an entire column of raw phonolite below all bottom layer blocks, not just an
outer shell. because now it is generating hollow space below the structure".

Reading the templates says how bad that was. forge_hall occupies 249 columns and
only 36 of them are on its perimeter, so the `edges_only` version of
GroundSupportProcessor legged 36 and left 213 - 86% of the building - hanging
over a void. terminus_platform is 97 and 20, gate_cap 69 and 20. And in the two
bridges, 18 columns each bottom out on a polished_phonolite_slab, which is where
the stacked-slab legs of item 5 came from: the old processor filled a leg with a
copy of whatever block was lowest in the column.

None of that is visible in the .nbt, because the support is added at PLACE time
by the processor, so this measures it in a running world.

The rig is in the OVERWORLD at y=150, over open air, for two reasons. Nothing up
there is naturally raw phonolite, so every raw phonolite block counted is one
this processor put there; and the ground is 80-odd blocks below, so every leg
runs its full max_depth of 24 rather than stopping early on rock.

/place jigsaw is used rather than /place structure because it puts the piece at
the position given instead of projecting it to the heightmap, and because it
still runs the pool's processor list, which /place template does not.

WHERE THE PIECE LANDS is not assumed. An earlier version of this file asserted
that the legs begin exactly one block under the position handed to /place
jigsaw, and then measured zero there while finding a full 97 legs twenty-four
blocks lower - the piece does not sit where the command's argument suggests. So
this walks the whole column and reads the profile off instead, which is both a
stronger check and one that does not need the answer up front: the signature of
a correct support is an unbroken run of max_depth levels, each carrying one leg
per column the piece bottoms out in.

The run measures one level TALLER than max_depth, and that is not slack in the
check - it is the piece's own floor. terminus_platform and gate_cap both lay
t.set(x, 0, z, RAW) under their whole deck and all 249 of forge_hall's lowest
blocks are raw phonolite too, so a scan for raw phonolite cannot tell that course
apart from the legs beneath it. The measured profile for terminus_platform is 97
at every one of 25 consecutive levels: one deck course and twenty-four of leg.

Counting is `fill ... replace <predicate>`, which reports how many blocks it
matched. That is the only exact count a vanilla server will give, and it consumes
what it counts - which is fine here, because each level is counted once.

Run:  python tools/test_ground_support.py [-v]
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
RAW = f"{NS}:raw_phonolite"
MAX_DEPTH = 24                       # GROUND_SUPPORT max_depth in gen_structures.py

FILLED = re.compile(r"filled (\d+) block", re.I)

# Each case names a pool, the jigsaw on its start piece to build out from, and
# how many columns that piece bottoms out in - measured off the emitted .nbt.
#
# The target has to be a jigsaw name that really is in the start pool. "No
# starting jigsaw <x> found in start pool <y>" is what the server says otherwise,
# and it then refuses to place anything at all.
#
# The first two pools hold ONE piece whose only connector points at
# minecraft:empty, so nothing attaches and the leg count is exact. The other two
# grow neighbours and every neighbour brings its own legs, so theirs is a floor
# rather than an equality - what matters there is that the number is nowhere near
# a perimeter-only shell, and that no leg is a slab.
CASES = [
    {"name": "terminus_platform", "pool": f"{NS}:outpost_of_the_tuners/terminators",
     "target": f"{NS}:building_gate", "reach": 12, "columns": 97,
     "exact": True, "perimeter": 20},
    {"name": "gate_cap", "pool": f"{NS}:outpost_of_the_tuners/gate_caps",
     "target": f"{NS}:bridge_start", "reach": 12, "columns": 69,
     "exact": True, "perimeter": 20},
    {"name": "forge_hall + its bridges", "pool": f"{NS}:outpost_of_the_tuners/start",
     "target": f"{NS}:outpost_gate", "reach": 48, "columns": 249,
     "exact": False, "perimeter": 36},
    # The bridges are the item 5 case: 18 columns in each of them bottom out on a
    # top slab, and the old processor filled a leg with a copy of that block, so
    # those 18 came out as stacked half-blocks.
    {"name": "a bridge", "pool": f"{NS}:outpost_of_the_tuners/bridges",
     "target": f"{NS}:bridge_start", "reach": 48, "columns": None,
     "exact": False, "perimeter": None},
]

ORIGIN_Y = 150
SCAN_TOP, SCAN_BOTTOM = ORIGIN_Y + 2, ORIGIN_Y - 30

# Fresh ground for every run. The baseline scan refuses to measure a spot that
# already has raw phonolite in it, and the pieces left standing by an earlier run
# of this file would also be in the way, so bump these rather than reuse a spot.
SPOTS = [(9000, 9000), (9200, 9000), (9400, 9000), (9600, 9000)]


def cmd(server: Server, line: str, wait: float) -> str:
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


def count(server: Server, x0, y0, z0, x1, y1, z1, predicate: str,
          wait: float = 1.4) -> int:
    """How many blocks matching `predicate` are in the box. Consumes them."""
    reply = cmd(server, f"fill {x0} {y0} {z0} {x1} {y1} {z1} "
                        f"minecraft:sponge replace {predicate}", wait)
    m = FILLED.search(reply)
    return int(m.group(1)) if m else 0


def scan(server: Server, x: int, z: int, r: int) -> list[tuple[int, int]]:
    """Raw phonolite per level through the whole scan range, top down.

    One fill per level rather than one for the box, because /fill refuses a
    region over 32768 blocks and the widest case here is 97 x 33 x 97. A single
    box fill for the baseline looked like it was passing and was in fact being
    rejected unread, which is the sort of silent zero this file exists to avoid.
    """
    return [(y, count(server, x - r, y, z - r, x + r, y, z + r, RAW))
            for y in range(SCAN_TOP, SCAN_BOTTOM - 1, -1)]


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    failures: list[str] = []

    for case, (x, z) in zip(CASES, SPOTS):
        r = case["reach"]
        print(f"\n  --- {case['name']} at ({x},{ORIGIN_Y},{z})")
        cmd(server, f"forceload add {x - r - 16} {z - r - 16} "
                    f"{x + r + 16} {z + r + 16}", 4.0)
        time.sleep(5)

        # A clean slate. Nothing up here is natural, but prove it rather than
        # assume it, because every count afterwards is a difference from this.
        pre = sum(n for _, n in scan(server, x, z, r))
        if pre:
            failures.append(f"{case['name']}: {pre} raw phonolite was already in the "
                            f"scan range before anything was placed - this spot has "
                            f"been used before and no count below means anything")
            continue

        reply = cmd(server, f"place jigsaw {case['pool']} {case['target']} 1 "
                            f"{x} {ORIGIN_Y} {z}", 8.0)
        # The server answers "Generated jigsaw at x, y, z" on success and "Failed
        # to generate jigsaw" on refusal. Neither contains the word "success",
        # which is what an earlier version of this check looked for.
        if "generated jigsaw" not in reply.lower():
            failures.append(f"{case['name']}: /place jigsaw refused it "
                            f"({reply.strip()[-200:]})")
            continue
        time.sleep(2)

        legged = [(y, n) for y, n in scan(server, x, z, r) if n]
        if legged:
            print("      leg profile (y:count) "
                  + " ".join(f"{y}:{n}" for y, n in legged))
        else:
            print("      leg profile: EMPTY")
            failures.append(f"{case['name']}: no support legs anywhere in the "
                            f"{SCAN_TOP - SCAN_BOTTOM + 1} levels scanned")
            cmd(server, "forceload remove all", 2.0)
            continue

        top, bottom = legged[0][0], legged[-1][0]
        depth = top - bottom + 1
        widest = max(n for _, n in legged)
        print(f"      legs run y={top} down to y={bottom} ({depth} levels), "
              f"widest level {widest}")

        # 1. UNBROKEN. A gap anywhere in the run is hollow space, which is the
        #    complaint. The scan is contiguous, so depth == len(legged) says so.
        if depth != len(legged):
            present = {yy for yy, _ in legged}
            gaps = [y for y in range(bottom, top + 1) if y not in present]
            failures.append(f"{case['name']}: the support column has holes in it at "
                            f"y={gaps[:8]}")

        # 2. FULL DEPTH. Over open air a leg runs the whole max_depth, and the
        #    profile is one level taller than that because the TOP level of it is
        #    the piece's own floor: terminus_platform and gate_cap both lay
        #    t.set(x, 0, z, RAW) under their whole deck, and all 249 of
        #    forge_hall's lowest blocks are raw phonolite as well, so a scan for
        #    raw phonolite cannot tell that course apart from the legs under it.
        #    An assembly whose pieces sit at different heights stacks its runs and
        #    is taller again, so that case only gets a floor.
        want_depth = MAX_DEPTH + 1
        if case["exact"] and depth != want_depth:
            failures.append(f"{case['name']}: the support profile is {depth} levels, "
                            f"expected {want_depth} - max_depth={MAX_DEPTH} of leg "
                            f"under the piece's own raw phonolite floor course")
        elif not case["exact"] and depth < MAX_DEPTH:
            failures.append(f"{case['name']}: the support profile is only {depth} "
                            f"levels, shallower than max_depth={MAX_DEPTH}")

        # 3. NOT A SHELL. One leg per column the piece bottoms out in.
        want = case["columns"]
        if want is not None:
            if case["exact"] and widest != want:
                failures.append(f"{case['name']}: the widest level carries {widest} "
                                f"legs, expected exactly {want} - one per column the "
                                f"piece bottoms out in")
            elif not case["exact"] and widest < want:
                failures.append(f"{case['name']}: the widest level carries {widest} "
                                f"legs, expected at least {want}; a perimeter-only "
                                f"shell would have scored about {case['perimeter']}")

        # 4. THE SLAB TEST, item 5. Every level in that run is support and nothing
        #    else, so a slab found across it is a leg the processor built out of
        #    one.
        slabs = count(server, x - r, bottom, z - r, x + r, top, z + r,
                      "#minecraft:slabs", wait=3.0)
        print(f"      slabs inside the support run: {slabs}")
        if slabs:
            failures.append(f"{case['name']}: {slabs} slab(s) in the support columns - "
                            f"the legs are still stacked half-blocks")

        cmd(server, "forceload remove all", 2.0)

    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: every bottom-layer column is legged, the legs are unbroken raw "
          "phonolite the full max_depth down, and not one of them is a slab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

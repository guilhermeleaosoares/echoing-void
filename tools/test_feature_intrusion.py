"""
Do moss and hushwater still land inside a settlement?

PLAYER: "there is moss and hushwater overriding the generation of outpost
structures meaning that there is hushwater and moss inside the walkways and
interiors".

The mechanism is ChunkGenerator.applyBiomeDecoration:350-372. It walks the
eleven decoration steps in order and, at each one, places that step's STRUCTURES
before that step's FEATURES. The settlements are at surface_structures, ordinal
4. The hushwater springs were at fluid_springs (8) and the moss at
vegetal_decoration (9), both above it, so both decorated a building that was
already standing. They are at local_modifications (2) now, below it, so the
building lands on top of them instead.

Two things this file has to get right, because the first draft got both wrong and
returned a number that meant nothing.

A FRESH WORLD. Decoration order is decided when a chunk is GENERATED. A chunk
some earlier session already wrote answers with whatever the biome JSON said
then, and run/tps_bench has been carried across many rounds. So this generates
its own level and every chunk it reads is a chunk it made.

A PROBE THAT IS ACTUALLY ON THE BUILDING. /locate answers with the centre of the
whole structure's bounding box, and a settlement that sprawls over bridges has
open air at its centre - the first draft probed there, found 27 blocks of
structure in the column and 86 moss, and 86 was just the natural moss of the
island it stands on. So this sweeps a grid of narrow columns, scores each by how
much worked stone is in it, and reads the intruders off the column that is most
solidly inside a building.

Counting is `fill ... replace <predicate>`, which reports how many blocks it
matched. It is the only exact count a vanilla server will give, and it consumes
what it counts - which is fine, because each column is counted once.

Run:  python tools/test_feature_intrusion.py [-v]
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import (RUN_DIR, Server, ensure_eula,  # noqa: E402
                      ensure_server_properties)

NS = "echoing_void"
DIM = f"{NS}:the_hollow_horizon"
# Bump this when re-running: the sweep CONSUMES what it counts, so a level this
# file has already measured answers zero for everything the second time round.
LEVEL = "feature_order_probe4"

MOSS = f"{NS}:resonance_moss"
HUSHWATER = f"{NS}:hushwater"
# Only a settlement makes polished phonolite. It is a worked block and no terrain
# feature places it, so its count is how far inside a building the column is.
MARKER = f"{NS}:polished_phonolite"
# A SECOND structure-only block, so the two phases below do not eat each
# other's evidence. `fill ... replace` consumes what it counts, so the sweep
# marks columns with one of these and the depth profile reads the other.
MARKER2 = f"{NS}:chalk_bricks"
# What the terrain itself is made of. A control column has to prove there is
# GROUND in it before its moss count means anything.
TERRAIN = f"#{NS}:hollow_horizon_natural_ground"

# the_hollow_horizon.json is min_y 0, height 256. A 5x5 footprint keeps one
# column at 5 * 5 * 256 = 6400 blocks, well inside /fill's 32768 ceiling, and
# narrow enough that a column landing on forge_hall's 17x17 deck is inside the
# building rather than straddling its edge.
Y_MIN, Y_MAX = 0, 255
HALF = 2
# A 7x7 sweep on an 8-block pitch, so +/- 24 blocks around whatever /locate says.
OFFSETS = [-24, -16, -8, 0, 8, 16, 24]

FOUND = re.compile(r"nearest .*? is at \[?\s*(-?\d+),\s*~?,?\s*(-?\d+)", re.I)
FILLED = re.compile(r"filled (\d+) block", re.I)


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


def count(server: Server, x: int, z: int, predicate: str, wait: float = 1.4) -> int:
    reply = cmd(server, f"execute in {DIM} run fill {x - HALF} {Y_MIN} {z - HALF} "
                        f"{x + HALF} {Y_MAX} {z + HALF} minecraft:sponge "
                        f"replace {predicate}", wait)
    m = FILLED.search(reply)
    return int(m.group(1)) if m else 0


def probe(server: Server, x: int, z: int) -> int:
    """How much worked stone is in this column - how far inside a building it is."""
    return count(server, x, z, MARKER2)


def band(server: Server, x: int, z: int, y0: int, y1: int, predicate: str) -> int:
    reply = cmd(server, f"execute in {DIM} run fill {x - HALF} {y0} {z - HALF} "
                        f"{x + HALF} {y1} {z + HALF} minecraft:sponge "
                        f"replace {predicate}", 1.2)
    m = FILLED.search(reply)
    return int(m.group(1)) if m else 0


def use_fresh_level() -> None:
    """Point the server at LEVEL, so every chunk it reads it also generated."""
    props = RUN_DIR / "server.properties"
    lines = props.read_text(encoding="utf-8").splitlines()
    out, seen = [], False
    for line in lines:
        if line.startswith("level-name="):
            out.append(f"level-name={LEVEL}")
            seen = True
        else:
            out.append(line)
    if not seen:
        out.append(f"level-name={LEVEL}")
    props.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  level-name set to {LEVEL}")


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()
    use_fresh_level()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    reply = cmd(server, f"execute in {DIM} run locate structure "
                        f"{NS}:outpost_of_the_tuners", 40.0)
    m = FOUND.search(reply)
    if not m:
        print("FAILED: could not locate an outpost")
        print("  " + reply.strip()[-300:])
        server.stop()
        return 1
    ox, oz = int(m.group(1)), int(m.group(2))
    print(f"  outpost located at x={ox} z={oz}")

    cmd(server, f"execute in {DIM} run forceload add {ox - 64} {oz - 64} "
                f"{ox + 64} {oz + 64}", 5.0)
    time.sleep(10)

    print("\n  phase 1: sweeping columns for worked stone, to find the building")
    results: list[tuple[int, int, int]] = []
    for dx in OFFSETS:
        for dz in OFFSETS:
            n = probe(server, ox + dx, oz + dz)
            results.append((ox + dx, oz + dz, n))
            if n:
                print(f"      ({ox + dx:6d},{oz + dz:6d})  worked stone {n:4d}")

    # PHASE 2, and this is the distinction a whole-column count cannot make.
    #
    # With the fix in place, moss CANNOT survive inside a piece. A template
    # writes every cell of its own volume, air included, so the settlement
    # overwrites whatever step 2 left in it. What it does NOT overwrite is the
    # island surface under it: the ground support legs stop at the first solid
    # block, moss is solid, so moss that was already there ends up buried beneath
    # the legs. Buried moss is invisible in play and is not what the player saw.
    #
    # So the column is read in 16-block bands, and moss counts as intrusion only
    # where it shares a band WITH structure. Anything else is the island.
    #
    # "At or above the lowest structure block" was the first rule here and it was
    # not safe: one column came back with six blocks of worked stone at y 0-15,
    # eighty blocks below the settlement - some other piece entirely - and that
    # one stray anchored the floor at the bottom of the world, so seven moss at
    # y 96-127 were reported as being inside a building that is nowhere near
    # them. Sharing a band is the question actually being asked.
    at_or_above = below = 0
    if any(n for _, _, n in results):
        bx, bz, best = max(results, key=lambda r: r[2])
        print(f"\n  phase 2: depth profile of the deepest column ({bx},{bz}), "
              f"{best} worked-stone blocks")
        bands = []
        for y0 in range(Y_MIN, Y_MAX + 1, 16):
            y1 = min(y0 + 15, Y_MAX)
            structure = band(server, bx, bz, y0, y1, MARKER)
            moss = band(server, bx, bz, y0, y1, MOSS)
            water = band(server, bx, bz, y0, y1, HUSHWATER)
            bands.append((y0, structure, moss, water))
            if structure or moss or water:
                print(f"      y {y0:3d}-{y1:3d}  structure {structure:4d}  "
                      f"moss {moss:3d}  hushwater {water:3d}")
        for _, structure, moss, water in bands:
            if structure:
                at_or_above += moss + water
            else:
                below += moss + water
        print(f"      -> moss/hushwater sharing a band with structure: "
              f"{at_or_above};  in bands with no structure at all: {below}")

    cmd(server, f"execute in {DIM} run forceload remove all", 2.0)

    # Controls on plain terrain: far enough that no piece of the settlement
    # reaches them, near enough to be the same biome and the same feature list.
    # Several of them, because a single column in a dimension made of floating
    # islands is quite likely to be empty sky - the first control this file used
    # was exactly that, read zero moss, and reported that moss had stopped
    # generating. Each one only counts once its own terrain count proves it has
    # ground in it.
    print("\n  control columns on plain terrain")
    control_moss = control_terrain = 0
    for dx, dz in ((400, 400), (-400, 400), (400, -400), (-400, -400),
                   (600, 0), (0, 600)):
        cx, cz = ox + dx, oz + dz
        cmd(server, f"execute in {DIM} run forceload add {cx - 16} {cz - 16} "
                    f"{cx + 16} {cz + 16}", 4.0)
        time.sleep(6)
        moss = count(server, cx, cz, MOSS, wait=2.0)
        # After the moss fill, so the moss - which is itself in that tag - is not
        # counted twice as the ground it grew on.
        ground = count(server, cx, cz, TERRAIN, wait=2.0)
        cmd(server, f"execute in {DIM} run forceload remove all", 2.0)
        print(f"      ({cx:6d},{cz:6d})  terrain {ground:5d}  moss {moss:3d}")
        control_moss += moss
        control_terrain += ground
        if control_moss:
            break

    server.stop()

    failures: list[str] = []
    if not any(n for _, _, n in results):
        failures.append("not one of the swept columns contained worked stone, so the "
                        "sweep never found the settlement and none of its numbers "
                        "mean anything")
    elif at_or_above:
        failures.append(f"{at_or_above} moss or hushwater block(s) at the same "
                        f"altitude as the building's own blocks - that is moss in "
                        f"the settlement, not on the island under it")

    # The obvious way this fix could go wrong: a feature moved to a step whose
    # prerequisites are not ready simply stops placing, and a silent zero
    # everywhere would look exactly like success above.
    if control_terrain == 0:
        failures.append("every control column was empty sky, so nothing was measured "
                        "about whether moss still generates at all")
    elif control_moss == 0:
        failures.append("no moss generated on plain terrain that does have ground in "
                        "it - moving it to local_modifications has stopped it placing "
                        "at all, which is worse than the bug")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: no moss and no hushwater shares an altitude with the building's "
          f"own blocks ({below} sit clear of it on the island), while plain terrain "
          f"nearby still grows {control_moss} moss")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

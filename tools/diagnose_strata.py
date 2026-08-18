"""
Strata and biome probe: what is the Hollow Horizon actually made of?

Boots a headless server and answers, from the running game rather than from the
JSON, the questions the terrain work is judged on:

  * do all three biomes exist, and where?                      (locate biome)
  * which biome is each probe column in?                       (execute if biome)
  * is the column navigable - open sky above, land underfoot?  (air/solid walk)
  * are the strata bands actually painted, and does a tall rock
    face cross more than one of them?                          (block walk)
  * how many trees does a chunk get, and are any of them
    standing on the Outpost?                                   (fill ... replace)

Everything printed here is a server response, not an inference.

Run:  python tools/diagnose_strata.py [-v] [--no-trees]
"""

from __future__ import annotations

import collections
import gzip
import re
import sys
import time
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import ev_nbt  # noqa: E402
from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
DIM = f"{NS}:the_hollow_horizon"
PROBE_PORT = 25599
STRUCT = f"{NS}:outpost_of_the_tuners"

BIOMES = [f"{NS}:resonant_plains", f"{NS}:shattered_octaves", f"{NS}:chalk_reaches"]

# The blocks a strata probe cares about. Kept short on purpose: every entry
# costs one command per sampled height per column.
STRATA = [
    "resonant_chalk",
    "echo_slate",
    "amber_strata",
    "raw_phonolite",
    "humming_crystal",
    "resonance_moss",
    "amber_lichen",
    "chime_sand",
]
# Checked once per column at the surface only.
SURFACE_EXTRAS = [
    "echo_sprout", "chime_grass", "crystal_bloom", "bismuth_cluster",
    "amber_resonance_leaves", "violet_resonance_leaves",
    "calcified_resonance_leaves", "humming_stem", "petrified_tuning_wood",
]

FIXED_COLUMNS = [(0, 0), (512, -384)]

BAND_LO, BAND_HI, BAND_STEP = 40, 216, 4       # strata walk
AIR_LO, AIR_HI, AIR_STEP = 0, 252, 2           # navigability walk

LOCATE_RE = re.compile(r"is at \[?(-?\d+),\s*([~\-\d]+),\s*(-?\d+)\]?")
BIOME_HIT = re.compile(r"EVBIOME (-?\d+) (-?\d+) (\S+)")
BLOCK_HIT = re.compile(r"EVB (-?\d+) (-?\d+) (-?\d+) (\S+)")
SOLID_HIT = re.compile(r"EVS (-?\d+) (-?\d+) (-?\d+) (\S+)")
FILLED_RE = re.compile(r"Successfully filled (\d+) block")


# The line shapes RegistryDataLoader.logErrors and TagLoader emit when a
# datapack entry fails to decode. Surfacing these on a boot failure is the
# difference between "the server did not start" and "echoing_void:echo_ash_grove
# names a block that is not registered".
REGISTRY_ERROR = re.compile(
    r">> Errors in|Errors in registry|Failed to parse|Unknown registry key|"
    r"Unbound values|Missing tag|Couldn't load tag|Failed to load datapacks")


def drain(server: Server, seconds: float) -> None:
    time.sleep(seconds)


def locate_biomes(server: Server) -> dict[str, tuple[int, int] | None]:
    found: dict[str, tuple[int, int] | None] = {}
    for biome in BIOMES:
        mark = len(server.transcript)
        server.send(f"execute in {DIM} run locate biome {biome}")
        drain(server, 4)
        hit = None
        for line in server.transcript[mark:]:
            m = LOCATE_RE.search(line)
            if m:
                hit = (int(m.group(1)), int(m.group(3)))
        found[biome] = hit
        print(f"  locate biome {biome:38s} -> {hit}")
    return found


# ---------------------------------------------------------------------------
# offline mode
#
# The live probe drives a server with /execute if block, which is fine until a
# second agent boots a server into the same run/ directory - the two fight over
# the world lock and the log, and the sampling dies half way through. Once the
# probe has generated chunks, everything it was asking the server is already on
# disk in the region files, at full resolution rather than every second block.
#
# Region format: a 4096-byte header of big-endian (3-byte sector offset,
# 1-byte sector count) per chunk, then each chunk as a 4-byte length, a 1-byte
# compression id (1 gzip, 2 zlib, 3 none) and the compressed NBT. Section block
# data is a palette plus a packed long array at
# max(4, ceil(log2(len(palette)))) bits per entry, packed WITHOUT straddling
# long boundaries.
# ---------------------------------------------------------------------------

def _unpack(data: list[int], bits: int, count: int) -> list[int]:
    per_long = 64 // bits
    mask = (1 << bits) - 1
    out: list[int] = []
    for value in data:
        v = value & 0xFFFFFFFFFFFFFFFF
        for i in range(per_long):
            if len(out) >= count:
                return out
            out.append((v >> (i * bits)) & mask)
    return out


def _read_chunk(raw: bytes, cx: int, cz: int) -> dict | None:
    index = ((cx & 31) + (cz & 31) * 32) * 4
    offset = int.from_bytes(raw[index:index + 3], "big")
    if offset == 0:
        return None
    start = offset * 4096
    length = int.from_bytes(raw[start:start + 4], "big")
    scheme = raw[start + 4]
    blob = raw[start + 5:start + 4 + length]
    if scheme == 1:
        blob = gzip.decompress(blob)
    elif scheme == 2:
        blob = zlib.decompress(blob)
    reader = ev_nbt._Reader(blob)
    if reader.u(">b") != ev_nbt.TAG_COMPOUND:
        return None
    reader.string()
    return reader.payload(ev_nbt.TAG_COMPOUND)


def _column(chunk: dict, lx: int, lz: int) -> tuple[dict[int, str], dict[int, str]]:
    """Every block and every biome in one column, keyed by world y."""
    blocks: dict[int, str] = {}
    biomes: dict[int, str] = {}
    for section in chunk.get("sections", []):
        base = section["Y"] * 16
        states = section.get("block_states")
        if states:
            palette = [e["Name"] for e in states["palette"]]
            if len(palette) == 1:
                for y in range(16):
                    blocks[base + y] = palette[0]
            elif states.get("data"):
                bits = max(4, (len(palette) - 1).bit_length())
                idx = _unpack(states["data"], bits, 4096)
                for y in range(16):
                    blocks[base + y] = palette[idx[y * 256 + lz * 16 + lx]]
        bio = section.get("biomes")
        if bio:
            palette = list(bio["palette"])
            if len(palette) == 1:
                for y in range(16):
                    biomes[base + y] = palette[0]
                continue
            bits = max(1, (len(palette) - 1).bit_length())
            idx = _unpack(bio.get("data", []), bits, 64)
            if idx:
                for y in range(16):
                    q = (y // 4) * 16 + (lz // 4) * 4 + (lx // 4)
                    biomes[base + y] = palette[idx[q]]
    return blocks, biomes


def offline(world: str) -> int:
    region = (ROOT / "run" / world / "dimensions" / NS / "the_hollow_horizon"
              / "region")
    files = sorted(region.glob("*.mca"))
    if not files:
        print(f"no region files under {region} - run the live probe first")
        return 1
    print(f"reading {len(files)} region file(s) from {region}")

    biome_area: collections.Counter[str] = collections.Counter()
    # Void columns carry a biome too, so a share of ALL columns overstates
    # any biome that is mostly open sky. Counting the land-bearing columns
    # separately is the figure that says how much walkable world each owns.
    biome_land: collections.Counter[str] = collections.Counter()
    block_total: collections.Counter[str] = collections.Counter()
    samples: list[tuple[int, int, str, dict[int, str]]] = []
    columns_seen = 0

    for path in files:
        raw = path.read_bytes()
        rx, rz = (int(part) for part in path.stem.split(".")[1:3])
        for cx in range(32):
            for cz in range(32):
                chunk = _read_chunk(raw, cx, cz)
                if not chunk or chunk.get("Status", "") .split(":")[-1] not in (
                        "full", "minecraft:full", ""):
                    if chunk is None:
                        continue
                wx = (rx * 32 + cx) * 16
                wz = (rz * 32 + cz) * 16
                for lx, lz in ((8, 8),):
                    blocks, biomes = _column(chunk, lx, lz)
                    if not blocks:
                        continue
                    columns_seen += 1
                    solid = {y: n for y, n in blocks.items() if n != "minecraft:air"}
                    for n in solid.values():
                        block_total[n] += 1
                    surface_biome = ""
                    if solid:
                        top = max(solid)
                        surface_biome = biomes.get(top, "")
                    else:
                        surface_biome = biomes.get(128, "")
                    if surface_biome:
                        biome_area[surface_biome] += 1
                        if solid:
                            biome_land[surface_biome] += 1
                    if solid and len(samples) < 400:
                        samples.append((wx + lx, wz + lz, surface_biome, blocks))

    print(f"\n=== {columns_seen} columns read ===")
    total_cols = max(1, sum(biome_area.values()))
    total_land = max(1, sum(biome_land.values()))
    print("\nBIOME BY COLUMN (one sample per chunk, at the surface):")
    print("       all   share    with land   share   biome")
    for name, n in biome_area.most_common():
        land = biome_land[name]
        print(f"  {n:8d} {100 * n // total_cols:5d}% "
              f"{land:11d} {100 * land // total_land:6d}%   {name}")
    print(f"  {sum(biome_land.values())} of {total_cols} sampled columns contain any land")

    deepest = min((y for _, _, _, blocks in samples for y, n in blocks.items()
                   if n != "minecraft:air"), default=None)
    if deepest is not None:
        print(f"\nDEEPEST ROCK in any sampled column: y={deepest}")
    print("\nBLOCKS BY VOLUME (non-air, across every sampled column):")
    for name, n in block_total.most_common(24):
        print(f"  {n:7d}  {name}")

    print("\nCOLUMNS (air runs collapsed, so the shape of the land is visible):")
    for wx, wz, biome, blocks in samples[:8]:
        runs: list[tuple[int, int, str]] = []
        for y in sorted(blocks):
            name = blocks[y].split(":")[-1]
            if runs and runs[-1][2] == name and runs[-1][1] == y - 1:
                runs[-1] = (runs[-1][0], y, name)
            else:
                runs.append((y, y, name))
        solid = [r for r in runs if r[2] != "air"]
        air = sum(hi - lo + 1 for lo, hi, n in runs if n == "air")
        total = sum(hi - lo + 1 for lo, hi, n in runs)
        print(f"\n  {wx},{wz}  biome={biome.rpartition(chr(58))[2]}  "
              f"{air}/{total} air ({100 * air // max(1, total)}% open)")
        print("    " + "  ".join(
            f"{lo}-{hi}:{n}" if hi > lo else f"{lo}:{n}" for lo, hi, n in solid))
    return 0


def main() -> int:
    if "--offline" in sys.argv:
        idx = sys.argv.index("--offline")
        world = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "worldgen_probe"
        return offline(world)

    verbose = "-v" in sys.argv
    do_trees = "--no-trees" not in sys.argv

    if not ensure_eula(True):
        return 1
    ensure_server_properties()
    # Own world, own lock. test_tps.ensure_server_properties pins level-name to
    # tps_bench, and if a benchmark server - or a second probe - is already
    # holding that world the boot dies with "another process has locked a
    # portion of the file" rather than with anything that looks like a worldgen
    # problem. A separate level name makes this probe safe to run alongside the
    # TPS gate and alongside another agent.
    props = ROOT / "run" / "server.properties"
    if props.exists():
        text = props.read_text(encoding="utf-8")
        text = re.sub(r"^level-name=.*$", "level-name=worldgen_probe",
                      text, flags=re.M)
        # Own port as well as own world. Two agents booting servers out of the
        # same run/ directory otherwise collide on 25565 and the loser dies with
        # "FAILED TO BIND TO PORT", which the transcript reports as a boot
        # failure and which reads exactly like a broken datapack.
        if re.search(r"^server-port=", text, flags=re.M):
            text = re.sub(r"^server-port=.*$", f"server-port={PROBE_PORT}",
                          text, flags=re.M)
        else:
            text = text.rstrip() + f"{chr(10)}server-port={PROBE_PORT}{chr(10)}"
        props.write_text(text, encoding="utf-8")

    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        # RegistryDataLoader.logErrors names the offending entry and the id it
        # could not resolve, and those lines are scrolled far off the end of the
        # transcript by the stack trace that follows. Without pulling them out,
        # every datapack fault looks identical: "server did not boot".
        errors = [l for l in server.transcript if REGISTRY_ERROR.search(l)]
        if errors:
            print(f"  {len(errors)} datapack / registry error line(s):")
            for line in dict.fromkeys(errors):
                print("    " + line.strip()[:200])
        else:
            for line in server.transcript[-40:]:
                print("  " + line)
        server.stop()
        return 1
    print("  server up")
    drain(server, 3)

    # ---- 1. do the three biomes exist at all? -----------------------------
    print("\n--- biome presence ---")
    located = locate_biomes(server)

    columns: list[tuple[int, int]] = list(FIXED_COLUMNS)
    for pos in located.values():
        if pos and pos not in columns:
            columns.append(pos)

    # ---- 2. generate the probe areas --------------------------------------
    for x, z in columns:
        server.send(f"execute in {DIM} run forceload add {x - 32} {z - 32} "
                    f"{x + 32} {z + 32}")
    print(f"\n  forceloading {len(columns)} probe areas; waiting for generation")
    drain(server, 45)

    # ---- 3. which biome is each column in? --------------------------------
    for x, z in columns:
        for biome in BIOMES:
            server.send(f"execute in {DIM} if biome {x} 128 {z} {biome} "
                        f"run say EVBIOME {x} {z} {biome.split(':')[1]}")
            time.sleep(0.02)
    drain(server, 6)

    # ---- 4. navigability: air vs solid over the whole build height --------
    print("  walking every column for air and solid")
    for x, z in columns:
        for y in range(AIR_LO, AIR_HI + 1, AIR_STEP):
            server.send(f"execute in {DIM} if block {x} {y} {z} #minecraft:air "
                        f"run say EVS {x} {y} {z} air")
            server.send(f"execute in {DIM} unless block {x} {y} {z} #minecraft:air "
                        f"run say EVS {x} {y} {z} solid")
            time.sleep(0.012)
    drain(server, 10)

    # ---- 5. strata: which rock at which altitude --------------------------
    print("  walking every column for strata")
    for x, z in columns:
        for y in range(BAND_LO, BAND_HI + 1, BAND_STEP):
            for block in STRATA:
                server.send(f"execute in {DIM} if block {x} {y} {z} {NS}:{block} "
                            f"run say EVB {x} {y} {z} {block}")
                time.sleep(0.010)
    drain(server, 12)

    # ---- 6. what is growing on the surface? -------------------------------
    print("  sampling the surface for vegetation")
    for x, z in columns:
        for dx, dz in ((0, 0), (4, 4), (-4, 4), (4, -4), (-4, -4), (8, 0), (0, 8)):
            for y in range(96, 220, 2):
                for block in SURFACE_EXTRAS:
                    server.send(
                        f"execute in {DIM} if block {x + dx} {y} {z + dz} "
                        f"{NS}:{block} run say EVB {x} {y} {z} {block}")
                    time.sleep(0.004)
    drain(server, 15)

    # ---- 7. trees: density, and are any on the Outpost? -------------------
    tree_report: list[str] = []
    if do_trees:
        mark = len(server.transcript)
        server.send(f"execute in {DIM} run locate structure {STRUCT}")
        drain(server, 6)
        site = None
        for line in server.transcript[mark:]:
            m = LOCATE_RE.search(line)
            if m:
                site = (int(m.group(1)), int(m.group(3)))
        tree_report.append(f"outpost located at {site}")
        if site:
            sx, sz = site
            server.send(f"execute in {DIM} run forceload add {sx - 48} {sz - 48} "
                        f"{sx + 48} {sz + 48}")
            drain(server, 40)

            # Count the outpost's own worked stone, to prove blocks were laid.
            for material in ("chalk_bricks", "phonolite_bricks", "polished_phonolite"):
                mark = len(server.transcript)
                server.send(
                    f"execute in {DIM} run fill {sx - 40} 0 {sz - 40} "
                    f"{sx + 40} 255 {sz + 40} {NS}:{material} replace {NS}:{material}")
                drain(server, 3)
                n = 0
                for line in server.transcript[mark:]:
                    m = FILLED_RE.search(line)
                    if m:
                        n = int(m.group(1))
                tree_report.append(f"{material} blocks within 40 of the outpost: {n}")

            # Logs anywhere in that same cube, and logs in the air ABOVE the
            # outpost's own footprint. A tree standing on the roof shows up as
            # logs high in the column; a tree standing on the ground beside it
            # does not.
            for label, y0, y1 in (("logs in outpost cube", 0, 255),):
                mark = len(server.transcript)
                server.send(
                    f"execute in {DIM} run fill {sx - 40} {y0} {sz - 40} "
                    f"{sx + 40} {y1} {sz + 40} minecraft:stone replace "
                    f"#minecraft:logs")
                drain(server, 3)
                n = 0
                for line in server.transcript[mark:]:
                    m = FILLED_RE.search(line)
                    if m:
                        n = int(m.group(1))
                tree_report.append(f"{label}: {n}")

        # Tree density on open terrain, well away from any structure.
        for x, z in columns[:2]:
            mark = len(server.transcript)
            server.send(f"execute in {DIM} run fill {x - 24} 0 {z - 24} "
                        f"{x + 23} 255 {z + 23} minecraft:stone replace "
                        f"#minecraft:logs")
            drain(server, 3)
            n = 0
            for line in server.transcript[mark:]:
                m = FILLED_RE.search(line)
                if m:
                    n = int(m.group(1))
            tree_report.append(f"log blocks in the 3x3 chunks at {x},{z}: {n}")

    server.stop()

    # ---- report -----------------------------------------------------------
    biome_of: dict[tuple[int, int], str] = {}
    solid: dict[tuple[int, int], dict[int, str]] = {c: {} for c in columns}
    rock: dict[tuple[int, int], dict[int, str]] = {c: {} for c in columns}
    surface_kinds: dict[tuple[int, int], set[str]] = {c: set() for c in columns}

    for line in server.transcript:
        m = BIOME_HIT.search(line)
        if m:
            biome_of[(int(m.group(1)), int(m.group(2)))] = m.group(3)
            continue
        m = SOLID_HIT.search(line)
        if m:
            key = (int(m.group(1)), int(m.group(3)))
            if key in solid:
                solid[key][int(m.group(2))] = m.group(4)
            continue
        m = BLOCK_HIT.search(line)
        if m:
            key = (int(m.group(1)), int(m.group(3)))
            name = m.group(4)
            if key in rock:
                if name in STRATA:
                    rock[key][int(m.group(2))] = name
                else:
                    surface_kinds[key].add(name)

    print("\n=== BIOMES PRESENT ===")
    for biome, pos in located.items():
        state = f"found at {pos}" if pos else "NOT FOUND"
        print(f"  {biome:40s} {state}")

    print("\n=== COLUMNS ===")
    for col in columns:
        x, z = col
        air = sum(1 for v in solid[col].values() if v == "air")
        total = len(solid[col])
        tops = [y for y, v in solid[col].items() if v == "solid"]
        kinds = sorted(set(rock[col].values()))
        print(f"\n  column {x},{z}  biome={biome_of.get(col, 'UNKNOWN')}")
        if not total:
            print("    no data (chunk never generated?)")
            continue
        print(f"    {air}/{total} sampled heights are air "
              f"({100 * air // total}% open)")
        if tops:
            print(f"    solid from y={min(tops)} to y={max(tops)}; "
                  f"highest solid sample y={max(tops)}")
        else:
            print("    NO SOLID BLOCKS - this column is pure void")
        print(f"    strata present: {', '.join(kinds) if kinds else 'NONE'}")
        if surface_kinds[col]:
            print(f"    vegetation present: {', '.join(sorted(surface_kinds[col]))}")
        strip = "    "
        for y in sorted(rock[col]):
            strip += f"{y}:{rock[col][y][:14]}  "
        if strip.strip():
            print(strip)

    if tree_report:
        print("\n=== TREES AND STRUCTURE ===")
        for line in tree_report:
            print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

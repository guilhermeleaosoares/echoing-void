"""
Hollow Horizon terrain diagnostic.

diagnose_worldgen.py answers "is this column solid?" one /execute at a time,
which is slow and only ever reports SOLID or air. This one boots the same
headless server, forceloads a block of chunks so the dimension actually
generates, shuts the server down cleanly, and then reads the region files off
disk. That gives the real block id of every position, so the report can say
whether the strata bands are present, how much of each column is open air, how
deep the caves go, and where the outpost pieces ended up.

Region parsing is deliberately small: header -> sector offset -> zlib -> NBT
(reusing ev_nbt's reader) -> sections -> block_states palette + packed indices.

Run:  python tools/diagnose_terrain.py            boot, generate, analyse
      python tools/diagnose_terrain.py --analyse  analyse whatever is on disk
      python tools/diagnose_terrain.py --wait 150 longer generation window
"""

from __future__ import annotations

import argparse
import collections
import re
import struct
import sys
import time
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import ev_nbt  # noqa: E402
from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

DIM = "echoing_void:the_hollow_horizon"
STRUCT = "echoing_void:outpost_of_the_tuners"
LEVEL = "tps_bench"
REGION_DIR = (ROOT / "run" / LEVEL / "dimensions" / "echoing_void"
              / "the_hollow_horizon" / "region")

LOCATE_RE = re.compile(r"\[(-?\d+), ?([~\-\d]+), ?(-?\d+)\]")

STRUCTURE_BLOCKS = {
    "echoing_void:phonolite_bricks",
    "echoing_void:void_glass",
    "echoing_void:null_iron_block",
    "echoing_void:acoustic_lock_box",
}


# ---------------------------------------------------------------------------
# region reading
# ---------------------------------------------------------------------------

def read_chunk(raw: bytes, index: int) -> dict | None:
    off, sectors = struct.unpack(">I", raw[index * 4:index * 4 + 4])[0] >> 8, raw[index * 4 + 3]
    if off == 0 or sectors == 0:
        return None
    start = off * 4096
    length = struct.unpack(">i", raw[start:start + 4])[0]
    scheme = raw[start + 4]
    payload = raw[start + 5:start + 4 + length]
    if scheme == 1:
        import gzip
        payload = gzip.decompress(payload)
    elif scheme == 2:
        payload = zlib.decompress(payload)
    elif scheme != 3:
        return None
    r = ev_nbt._Reader(payload)
    if r.u(">b") != ev_nbt.TAG_COMPOUND:
        return None
    r.string()
    return r.payload(ev_nbt.TAG_COMPOUND)


def unpack_indices(data: list[int], bits: int, count: int) -> list[int]:
    """1.16+ packing: entries never straddle a long."""
    per_long = 64 // bits
    mask = (1 << bits) - 1
    out: list[int] = []
    for word in data:
        word &= 0xFFFFFFFFFFFFFFFF
        for slot in range(per_long):
            if len(out) >= count:
                return out
            out.append((word >> (slot * bits)) & mask)
    return out


def section_blocks(section: dict) -> tuple[int, list[str]] | None:
    """Return (sectionY, 4096 block names in y*256+z*16+x order)."""
    states = section.get("block_states")
    if not states:
        return None
    palette = [entry.get("Name", "?") for entry in states.get("palette", [])]
    if not palette:
        return None
    y = section.get("Y", 0)
    data = states.get("data")
    if not data:
        return y, [palette[0]] * 4096
    bits = max(4, (len(palette) - 1).bit_length())
    idx = unpack_indices(data, bits, 4096)
    return y, [palette[i] if i < len(palette) else "?" for i in idx]


def load_world() -> dict[tuple[int, int], dict[int, list[str]]]:
    """chunk (cx, cz) -> {sectionY: 4096 names}."""
    world: dict[tuple[int, int], dict[int, list[str]]] = {}
    if not REGION_DIR.exists():
        return world
    for mca in sorted(REGION_DIR.glob("r.*.mca")):
        parts = mca.stem.split(".")
        rx, rz = int(parts[1]), int(parts[2])
        raw = mca.read_bytes()
        if len(raw) < 8192:
            continue
        for i in range(1024):
            chunk = read_chunk(raw, i)
            if not chunk:
                continue
            sections = {}
            for section in chunk.get("sections", []):
                got = section_blocks(section)
                if got:
                    sections[got[0]] = got[1]
            if sections:
                world[(rx * 32 + i % 32, rz * 32 + i // 32)] = sections
    return world


def block_at(world, x: int, y: int, z: int) -> str:
    chunk = world.get((x >> 4, z >> 4))
    if not chunk:
        return "<ungenerated>"
    section = chunk.get(y >> 4)
    if section is None:
        return "minecraft:air"
    return section[(y & 15) * 256 + (z & 15) * 16 + (x & 15)]


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def describe_column(world, x: int, z: int, min_y: int, max_y: int) -> str:
    """Run-length summary of a column, which is the evidence that matters."""
    runs: list[tuple[str, int, int]] = []
    for y in range(min_y, max_y):
        name = block_at(world, x, y, z)
        short = name.split(":", 1)[-1]
        if runs and runs[-1][0] == short:
            runs[-1] = (short, runs[-1][1], y)
        else:
            runs.append((short, y, y))
    parts = [f"{lo}-{hi} {name}" if hi > lo else f"{lo} {name}"
             for name, lo, hi in runs]
    return " | ".join(parts)


def analyse(world, min_y: int, max_y: int) -> None:
    if not world:
        print("  NO REGION DATA - nothing generated")
        return

    print(f"  chunks on disk: {len(world)}")

    xs = [cx for cx, _ in world]
    zs = [cz for _, cz in world]
    print(f"  chunk x {min(xs)}..{max(xs)}  z {min(zs)}..{max(zs)}")

    # ---- whole-volume histogram ------------------------------------------
    hist: collections.Counter = collections.Counter()
    per_band: dict[str, collections.Counter] = {
        "y0-30": collections.Counter(), "y30-70": collections.Counter(),
        "y70-110": collections.Counter(), "y110-150": collections.Counter(),
        "y150-256": collections.Counter(),
    }

    def band_of(y: int) -> str:
        if y < 30:
            return "y0-30"
        if y < 70:
            return "y30-70"
        if y < 110:
            return "y70-110"
        if y < 150:
            return "y110-150"
        return "y150-256"

    sampled_chunks = sorted(world)[::3] or sorted(world)
    total = 0
    for key in sampled_chunks:
        for sy, names in world[key].items():
            base_y = sy * 16
            if base_y < min_y or base_y >= max_y:
                continue
            for i, name in enumerate(names):
                short = name.split(":", 1)[-1]
                hist[short] += 1
                per_band[band_of(base_y + i // 256)][short] += 1
                total += 1

    if not total:
        print("  no block data in range")
        return

    print(f"\n  block census over {len(sampled_chunks)} chunks "
          f"({total} positions):")
    for name, n in hist.most_common(18):
        print(f"    {n * 100.0 / total:6.2f}%  {n:>9}  {name}")

    print("\n  by altitude band (top 4 each):")
    for band, counter in per_band.items():
        sub = sum(counter.values())
        if not sub:
            continue
        top = ", ".join(f"{n * 100.0 / sub:.0f}% {k}" for k, n in counter.most_common(4))
        print(f"    {band:<10} {top}")

    # ---- openness --------------------------------------------------------
    air = hist.get("air", 0) + hist.get("cave_air", 0) + hist.get("void_air", 0)
    print(f"\n  open air fraction of the whole build volume: "
          f"{air * 100.0 / total:.1f}%")

    # ---- surface heights and longest solid run ---------------------------
    heights: list[int] = []
    longest_runs: list[int] = []
    keys = sorted(world)
    probe_chunks = keys[::5] or keys
    for cx, cz in probe_chunks:
        for dx, dz in ((2, 2), (8, 8), (13, 5)):
            x, z = cx * 16 + dx, cz * 16 + dz
            top = None
            run = best = 0
            for y in range(max_y - 1, min_y - 1, -1):
                name = block_at(world, x, y, z)
                if name.endswith("air"):
                    run = 0
                else:
                    if top is None:
                        top = y
                    run += 1
                    best = max(best, run)
            if top is not None:
                heights.append(top)
            longest_runs.append(best)

    if heights:
        heights.sort()
        print(f"  surface height over {len(heights)} probes: "
              f"min {heights[0]}, p25 {heights[len(heights) // 4]}, "
              f"median {heights[len(heights) // 2]}, "
              f"p75 {heights[3 * len(heights) // 4]}, max {heights[-1]}")
    void_columns = len(longest_runs) - len(heights)
    print(f"  columns that are pure void (no block at all): "
          f"{void_columns}/{len(longest_runs)}")
    if longest_runs:
        longest_runs.sort()
        print(f"  longest uninterrupted solid run per column: "
              f"median {longest_runs[len(longest_runs) // 2]}, "
              f"p90 {longest_runs[int(len(longest_runs) * 0.9)]}, "
              f"max {longest_runs[-1]}")

    # ---- structures ------------------------------------------------------
    found: collections.Counter = collections.Counter()
    ys: list[int] = []
    for key in keys:
        for sy, names in world[key].items():
            for i, name in enumerate(names):
                if name in STRUCTURE_BLOCKS:
                    found[name] += 1
                    ys.append(sy * 16 + i // 256)
    if found:
        print(f"\n  outpost blocks found: {sum(found.values())} "
              f"({dict(found)}) at y {min(ys)}..{max(ys)}")
    else:
        print("\n  no outpost blocks in the generated area")


def sample_columns(world, coords: list[tuple[int, int]], min_y: int, max_y: int) -> None:
    print("\n  sample columns (run-length encoded, this is the probe the brief asked for):")
    for x, z in coords:
        print(f"\n   ({x}, {z}):")
        text = describe_column(world, x, z, min_y, max_y)
        for i in range(0, len(text), 150):
            print("     " + text[i:i + 150])


# ---------------------------------------------------------------------------

def boot_and_generate(wait: int, verbose: bool, fresh: bool) -> tuple[int, int] | None:
    if not ensure_eula(True):
        return None
    ensure_server_properties()

    if fresh:
        world = ROOT / "run" / LEVEL
        if world.exists():
            # Terrain is only ever generated once per chunk, so a stale world
            # would silently report the OLD generator's output.
            shutil.rmtree(world)
            print(f"  deleted stale world {world}")

    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        for line in server.transcript[-40:]:
            print("  " + line)
        server.stop()
        return None
    print("  server up")
    time.sleep(3)

    errors = [ln for ln in server.transcript
              if "echoing_void" in ln and ("ERROR" in ln or "Failed" in ln
                                           or "failed" in ln)]
    if errors:
        print("  datapack complaints during boot:")
        for line in errors[:15]:
            print("    " + line.strip())

    mark = len(server.transcript)
    server.send(f"execute in {DIM} run locate structure {STRUCT}")
    time.sleep(6)
    site = None
    for line in server.transcript[mark:]:
        m = LOCATE_RE.search(line)
        if m:
            site = (int(m.group(1)), int(m.group(3)))
    print(f"  locate structure -> {site}")

    print("  forceloading 16x16 chunks at the origin")
    server.send(f"execute in {DIM} run forceload add -128 -128 127 127")
    time.sleep(wait)
    server.send("save-all flush")
    time.sleep(10)

    if site is not None:
        sx, sz = site
        print(f"  forceloading 12x12 chunks around the outpost site {site}")
        server.send(f"execute in {DIM} run forceload remove all")
        time.sleep(2)
        server.send(f"execute in {DIM} run forceload add {sx - 96} {sz - 96} "
                    f"{sx + 95} {sz + 95}")
        time.sleep(wait)
        server.send("save-all flush")
        time.sleep(10)

    server.stop()
    return site


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyse", action="store_true",
                    help="skip the server, just read the region files on disk")
    ap.add_argument("--wait", type=int, default=120,
                    help="seconds to let each forceloaded block generate")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--columns", type=int, default=6)
    args = ap.parse_args()

    site = None
    if not args.analyse:
        site = boot_and_generate(args.wait, args.verbose)

    print("\n--- reading region files ---")
    world = load_world()
    analyse(world, 0, 256)

    coords: list[tuple[int, int]] = []
    keys = sorted(world)
    if keys:
        step = max(1, len(keys) // max(1, args.columns))
        for cx, cz in keys[::step][:args.columns]:
            coords.append((cx * 16 + 8, cz * 16 + 8))
    if site:
        coords.append(site)
    if coords:
        sample_columns(world, coords, 0, 256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

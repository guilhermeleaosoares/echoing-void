"""
Full-resolution Hollow Horizon probe.

Two phases, deliberately separated so that a rate-limited or crashed driver
never costs the generated world:

  python tools/probe_hollow.py --gen        boot a server, forceload a spread of
                                            chunks in the Hollow Horizon AND in
                                            the Overworld, save, stop. Every
                                            server reply is echoed verbatim.

  python tools/probe_hollow.py --analyze    read the region files at FULL
                                            resolution (all 256 columns of every
                                            chunk, every y) and answer the five
                                            questions the terrain work is judged
                                            on.

Nothing here infers terrain from a dropped sample: phase one only writes chunks,
phase two only reads what is on disk.
"""

from __future__ import annotations

import collections
import math
import re
import statistics
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import ev_nbt  # noqa: E402
from diagnose_strata import _read_chunk, _unpack  # noqa: E402

NS = "echoing_void"
HH = f"{NS}:the_hollow_horizon"
WORLD = "worldgen_probe2"
PROBE_PORT = 25601

# Six widely separated patches. Spread matters more than volume: the biome
# source keys off continentalness and erosion, both of which are large-scale
# noises, so six patches 1-6 km apart sample far more of the parameter space
# than one big block at spawn would.
PATCHES = [
    (0, 0), (3000, 512), (-2560, 2048), (1536, -3584), (6000, 6000), (-6000, -1024),
]
PATCH_CHUNKS = 12                      # 12x12 = 144 chunks, under the 256 cap
OVERWORLD_PATCH = (0, 0)
OVERWORLD_CHUNKS = 10

LOG_BLOCKS = {
    f"{NS}:amber_bough_log", f"{NS}:echo_ash_log", f"{NS}:humming_stem",
    f"{NS}:petrified_tuning_wood",
}
LEAF_BLOCKS = {
    f"{NS}:amber_resonance_leaves", f"{NS}:violet_resonance_leaves",
    f"{NS}:calcified_resonance_leaves", f"{NS}:ashen_resonance_leaves",
}
# fallen_debris draws from exactly these five, weighted.
DEBRIS_BLOCKS = {
    f"{NS}:raw_phonolite", f"{NS}:echo_slate", f"{NS}:amber_strata",
    f"{NS}:resonant_chalk", f"{NS}:chime_sand",
}
AIR = "minecraft:air"


# ---------------------------------------------------------------------------
# phase one: generate
# ---------------------------------------------------------------------------

def generate(wait_seconds: int) -> int:
    import re
    from test_tps import Server, ensure_eula, ensure_server_properties

    if not ensure_eula(True):
        print("FAILED: eula not accepted")
        return 1
    ensure_server_properties()

    props = ROOT / "run" / "server.properties"
    text = props.read_text(encoding="utf-8")
    text = re.sub(r"^level-name=.*$", f"level-name={WORLD}", text, flags=re.M)
    if re.search(r"^server-port=", text, flags=re.M):
        text = re.sub(r"^server-port=.*$", f"server-port={PROBE_PORT}", text, flags=re.M)
    else:
        text = text.rstrip() + f"\nserver-port={PROBE_PORT}\n"
    props.write_text(text, encoding="utf-8")
    print(f"  level-name={WORLD}  server-port={PROBE_PORT}")

    # A previous probe whose stdout was still buffered can look finished while
    # its server is very much alive. Two servers on one port means the second
    # dies in startTcpServerListener with a netty error that looks nothing like
    # a port clash, and the run silently produces no world at all.
    import socket
    probe_sock = socket.socket()
    probe_sock.settimeout(1.0)
    if probe_sock.connect_ex(("127.0.0.1", PROBE_PORT)) == 0:
        probe_sock.close()
        print(f"FAILED: something is already listening on port {PROBE_PORT}. "
              f"A previous probe server is still running - stop it first.")
        return 1
    probe_sock.close()

    server = Server(False)
    server.start()
    if not server.wait_for_boot(1200):
        print("FAILED: server did not boot. Last 60 transcript lines:")
        for line in server.transcript[-60:]:
            print("  " + line)
        return 1
    print("  server up")
    time.sleep(3)

    def run(cmd: str, settle: float = 1.5) -> list[str]:
        """Send one command and return whatever the server said about it."""
        mark = len(server.transcript)
        server.send(cmd)
        time.sleep(settle)
        replies = [l for l in server.transcript[mark:] if "Server thread" in l or l.strip()]
        tail = []
        for line in replies:
            # strip the log preamble so the reply itself is readable
            idx = line.find("]: ")
            tail.append(line[idx + 3:] if idx >= 0 else line)
        return tail

    failures: list[tuple[str, list[str]]] = []

    def forceload(dim: str, ox: int, oz: int, chunks: int) -> None:
        span = chunks * 16 - 1
        cmd = f"execute in {dim} run forceload add {ox} {oz} {ox + span} {oz + span}"
        out = run(cmd, 2.0)
        joined = " ".join(out)
        ok = "forced to load" in joined or "Marked" in joined
        print(f"  > {cmd}")
        for line in out[:4]:
            print(f"      {line}")
        if not ok:
            failures.append((cmd, out))

    print("\n=== forceload: Hollow Horizon ===")
    for ox, oz in PATCHES:
        forceload(HH, ox, oz, PATCH_CHUNKS)
    print("\n=== forceload: Overworld (the Knell control sample) ===")
    forceload("minecraft:overworld", *OVERWORLD_PATCH, OVERWORLD_CHUNKS)

    total = len(PATCHES) * PATCH_CHUNKS ** 2 + OVERWORLD_CHUNKS ** 2
    print(f"\n  waiting {wait_seconds}s for {total} chunks to generate")
    step = 30
    for elapsed in range(0, wait_seconds, step):
        time.sleep(min(step, wait_seconds - elapsed))
        out = run("save-all flush", 6.0)
        saved = [l for l in out if "Saved" in l or "Saving" in l]
        size = sum(p.stat().st_size for p in
                   (ROOT / "run" / WORLD).rglob("*.mca")) // (1024 * 1024)
        print(f"    t+{elapsed + step:4d}s  region bytes: {size} MiB   "
              f"{saved[-1] if saved else 'no save reply'}")

    print("\n=== stopping ===")
    for line in run("save-all flush", 8.0)[:3]:
        print("  " + line)
    server.send("stop")
    if server.proc:
        try:
            server.proc.wait(timeout=180)
        except Exception:
            server.proc.kill()
    print("  server stopped")

    if failures:
        print(f"\n!! {len(failures)} command(s) did not report success:")
        for cmd, out in failures:
            print(f"  {cmd}")
            for line in out[:6]:
                print(f"      {line}")
        return 1
    return 0


# ---------------------------------------------------------------------------
# phase two: read
# ---------------------------------------------------------------------------

class Chunk:
    """One chunk decoded once, indexable at (x, y, z) without re-unpacking."""

    __slots__ = ("blocks", "biomes", "ymin", "ymax", "status")

    def __init__(self, nbt: dict):
        self.status = str(nbt.get("Status", ""))
        self.blocks: dict[int, list[str]] = {}     # section Y -> 4096 names
        self.biomes: dict[int, list[str]] = {}     # section Y -> 64 names
        ys = []
        for section in nbt.get("sections", []):
            sy = section["Y"]
            states = section.get("block_states")
            if states:
                palette = [e["Name"] for e in states["palette"]]
                if len(palette) == 1:
                    self.blocks[sy] = [palette[0]] * 4096
                elif states.get("data"):
                    bits = max(4, (len(palette) - 1).bit_length())
                    idx = _unpack(states["data"], bits, 4096)
                    self.blocks[sy] = [palette[i] for i in idx]
                if sy in self.blocks:
                    ys.append(sy)
            bio = section.get("biomes")
            if bio:
                palette = list(bio["palette"])
                if len(palette) == 1:
                    self.biomes[sy] = [palette[0]] * 64
                elif bio.get("data"):
                    bits = max(1, (len(palette) - 1).bit_length())
                    idx = _unpack(bio["data"], bits, 64)
                    self.biomes[sy] = [palette[i] for i in idx]
        self.ymin = min(ys) * 16 if ys else 0
        self.ymax = (max(ys) + 1) * 16 - 1 if ys else 0

    def block(self, lx: int, y: int, lz: int) -> str:
        sec = self.blocks.get(y >> 4)
        if sec is None:
            return AIR
        return sec[(y & 15) * 256 + lz * 16 + lx]

    def biome(self, lx: int, y: int, lz: int) -> str:
        sec = self.biomes.get(y >> 4)
        if sec is None:
            return ""
        return sec[((y & 15) // 4) * 16 + (lz // 4) * 4 + (lx // 4)]

    def column(self, lx: int, lz: int) -> dict[int, str]:
        out = {}
        for sy, sec in self.blocks.items():
            base = sy * 16
            for dy in range(16):
                name = sec[dy * 256 + lz * 16 + lx]
                if name != AIR:
                    out[base + dy] = name
        return out

    def top_y(self, lx: int, lz: int) -> int | None:
        for sy in sorted(self.blocks, reverse=True):
            sec = self.blocks[sy]
            for dy in range(15, -1, -1):
                if sec[dy * 256 + lz * 16 + lx] != AIR:
                    return sy * 16 + dy
        return None


def load_chunks(world: str, dim: str) -> dict[tuple[int, int], Chunk]:
    if dim == "overworld":
        region = ROOT / "run" / world / "region"
        if not region.is_dir():
            region = ROOT / "run" / world / "dimensions" / "minecraft" / "overworld" / "region"
    else:
        region = ROOT / "run" / world / "dimensions" / NS / "the_hollow_horizon" / "region"
    out: dict[tuple[int, int], Chunk] = {}
    if not region.is_dir():
        print(f"  (no region dir at {region})")
        return out
    for path in sorted(region.glob("*.mca")):
        if path.stat().st_size == 0:
            continue
        raw = path.read_bytes()
        rx, rz = (int(p) for p in path.stem.split(".")[1:3])
        for cx in range(32):
            for cz in range(32):
                try:
                    nbt = _read_chunk(raw, cx, cz)
                except Exception:
                    continue
                if not nbt:
                    continue
                ch = Chunk(nbt)
                if not ch.blocks:
                    continue
                # Forceloading a patch also leaves a wide apron of proto-chunks
                # around it at earlier generation stages. Those carry all-air
                # sections and a placeholder biome, and counting them would
                # inflate the air fraction and invent a minecraft:plains biome
                # that the dimension does not have. Only finished chunks count.
                if "full" not in ch.status:
                    continue
                out[(rx * 32 + cx, rz * 32 + cz)] = ch
    return out


def short(name: str) -> str:
    return name.split(":")[-1]


# The main land mass tops out well below this; anything whose LOWEST block is
# above it is a body of rock with void underneath, i.e. a floating island.
SKY_FLOOR = 150
COMPONENT_MIN_Y = 128          # only flood-fill the upper world, for speed


def islands_and_hollows(hh: dict[tuple[int, int], "Chunk"]) -> None:
    """Find floating islands as 3D connected components and measure their shape.

    Per-chunk heuristics cannot answer 'conical or vertical' because an island
    straddles chunk borders; a component that is flood-filled across the whole
    patch can. Restricted to y>=128 so the fill stays cheap - the question is
    only ever about the bodies that float.
    """
    print("\n" + "=" * 72)
    print("3. FLOATING ISLANDS  (3D connected components; rugged/conical vs "
          "vertical/blocky)")
    print("=" * 72)

    # group chunks into patches so each flood fill stays local and bounded
    patches: collections.defaultdict[tuple[int, int], list] = collections.defaultdict(list)
    for (cx, cz) in hh:
        patches[(cx // 24, cz // 24)].append((cx, cz))

    # Pack (x, y, z) into one int. The offset makes negative world coordinates
    # non-negative BEFORE the shift; writing it as `x + 1 << 20` would parse as
    # `(x + 1) << 20`, which silently mispacks every cell and leaves the flood
    # fill unable to find any neighbour.
    OFF = 1 << 21
    MASK = (1 << 22) - 1

    def key(x: int, y: int, z: int) -> int:
        return ((x + OFF) << 44) | ((z + OFF) << 22) | (y & 0xFF)

    def unkey(k: int) -> tuple[int, int, int]:
        return (((k >> 44) & MASK) - OFF, k & 0xFF, ((k >> 22) & MASK) - OFF)

    all_islands: list[dict] = []
    ground_top: dict[tuple[int, int], int] = {}

    for pk, members in sorted(patches.items()):
        if len(members) < 16:
            continue
        solid: set[int] = set()
        for (cx, cz) in members:
            ch = hh[(cx, cz)]
            for lx in range(16):
                wx = cx * 16 + lx
                for lz in range(16):
                    wz = cz * 16 + lz
                    col = ch.column(lx, lz)
                    below = [y for y in col if y < SKY_FLOOR]
                    if below:
                        ground_top[(wx, wz)] = max(below)
                    for y in col:
                        if y >= COMPONENT_MIN_Y:
                            solid.add(key(wx, y, wz))
        seen: set[int] = set()
        for start in solid:
            if start in seen:
                continue
            stack = [start]
            seen.add(start)
            comp = []
            while stack:
                k = stack.pop()
                comp.append(k)
                x, y, z = unkey(k)
                for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                   (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    nk = key(x + dx, y + dy, z + dz)
                    if nk in solid and nk not in seen:
                        seen.add(nk)
                        stack.append(nk)
            if len(comp) < 150:
                continue
            decoded = [unkey(k) for k in comp]
            ys = [d[1] for d in decoded]
            if min(ys) <= SKY_FLOOR:
                continue                      # attached to the main land mass
            xs = [d[0] for d in decoded]
            zs = [d[2] for d in decoded]
            area: collections.Counter[int] = collections.Counter(ys)
            all_islands.append({
                "volume": len(comp), "ymin": min(ys), "ymax": max(ys),
                "area": area, "xs": (min(xs), max(xs)), "zs": (min(zs), max(zs)),
                "cells": comp,
            })

    if not all_islands:
        print("  NO FLOATING ISLANDS FOUND above y%d" % SKY_FLOOR)
        return

    print(f"  islands found (volume >= 150, entirely above y{SKY_FLOOR}): "
          f"{len(all_islands)}")
    vols = sorted(i["volume"] for i in all_islands)
    print(f"  volume: min {vols[0]}  median {vols[len(vols)//2]}  max {vols[-1]}")

    taper: list[float] = []
    top_heavy: list[float] = []
    wall: list[float] = []
    for isl in all_islands:
        area = isl["area"]
        peak = max(area.values())
        peak_y = max(area, key=lambda y: area[y])
        height = isl["ymax"] - isl["ymin"] + 1
        # conical: the bottom third is much narrower than the widest layer
        low = [area.get(y, 0) for y in range(isl["ymin"], isl["ymin"] + max(1, height // 3))]
        taper.append((sum(low) / len(low)) / peak)
        # wide flattish TOP: the widest layer should sit in the upper half
        top_heavy.append((peak_y - isl["ymin"]) / max(1, height - 1))
        # straight wall: share of layers within 90% of the widest
        wall.append(sum(1 for y in range(isl["ymin"], isl["ymax"] + 1)
                        if area.get(y, 0) >= 0.9 * peak) / height)

    print(f"\n  BOTTOM-THIRD WIDTH as a share of the widest layer:")
    print(f"    mean {statistics.mean(taper):.2f}   median {statistics.median(taper):.2f}"
          f"      (conical < 0.50, straight-sided ~1.0)")
    print(f"  WIDEST LAYER POSITION (0 = at the very bottom, 1 = at the top):")
    print(f"    mean {statistics.mean(top_heavy):.2f}   median "
          f"{statistics.median(top_heavy):.2f}   (wide flat top => > 0.6)")
    print(f"  STRAIGHT-WALL SHARE (layers within 90% of the widest):")
    print(f"    mean {statistics.mean(wall):.2f}   median {statistics.median(wall):.2f}"
          f"      (a blocky pillar approaches 1.0)")

    print("\n  LARGEST ISLANDS, layer by layer (top to bottom):")
    for isl in sorted(all_islands, key=lambda i: -i["volume"])[:4]:
        area = isl["area"]
        w = isl["xs"][1] - isl["xs"][0] + 1
        d = isl["zs"][1] - isl["zs"][0] + 1
        print(f"\n    island at x{isl['xs'][0]}..{isl['xs'][1]} "
              f"z{isl['zs'][0]}..{isl['zs'][1]}  y{isl['ymin']}..{isl['ymax']}  "
              f"volume {isl['volume']}  footprint {w}x{d}")
        for y in range(isl["ymax"], isl["ymin"] - 1, -1):
            a = area.get(y, 0)
            print(f"      y{y:3d} {a:5d} " + "#" * min(60, a // 2))

    # ---- the matching hollow ------------------------------------------------
    print("\n" + "=" * 72)
    print("4. MATCHING HOLLOWS IN THE GROUND BENEATH, AND DEBRIS")
    print("=" * 72)
    if not ground_top:
        print("  no ground layer found below y%d" % SKY_FLOOR)
        return
    matched = 0
    checked = 0
    depths: list[float] = []
    for isl in sorted(all_islands, key=lambda i: -i["volume"])[:40]:
        x0, x1 = isl["xs"]
        z0, z1 = isl["zs"]
        inside = [ground_top[(x, z)] for x in range(x0, x1 + 1)
                  for z in range(z0, z1 + 1) if (x, z) in ground_top]
        pad = 12
        ring = [ground_top[(x, z)]
                for x in range(x0 - pad, x1 + pad + 1)
                for z in range(z0 - pad, z1 + pad + 1)
                if (x, z) in ground_top and not (x0 <= x <= x1 and z0 <= z <= z1)]
        if len(inside) < 30 or len(ring) < 30:
            continue
        checked += 1
        drop = statistics.median(ring) - statistics.median(inside)
        depths.append(drop)
        if drop >= 3:
            matched += 1
    print(f"  islands with enough ground around them to judge: {checked}")
    if depths:
        print(f"  ground beneath the island vs the ring around it "
              f"(positive = a hollow):")
        print(f"    mean {statistics.mean(depths):+.1f} blocks   median "
              f"{statistics.median(depths):+.1f}   max {max(depths):+.1f}")
        print(f"  islands sitting over a hollow at least 3 blocks deep: "
              f"{matched}/{checked}")

    debris_in_hollow = 0
    debris_total = 0
    for (wx, wz), y in ground_top.items():
        cx, cz = wx >> 4, wz >> 4
        ch = hh.get((cx, cz))
        if ch is None:
            continue
        if ch.block(wx & 15, y, wz & 15) in DEBRIS_BLOCKS:
            debris_total += 1
    print(f"  ground-surface columns topped by a fallen-debris block: {debris_total}"
          f" of {len(ground_top)}")


def analyze(world: str) -> int:
    print(f"=== reading {world} ===")
    hh = load_chunks(world, "hh")
    ow = load_chunks(world, "overworld")
    print(f"  Hollow Horizon chunks on disk: {len(hh)}")
    print(f"  Overworld chunks on disk:      {len(ow)}")
    if not hh:
        print("  nothing to analyze - run --gen first")
        return 1
    full = sum(1 for c in hh.values() if "full" in c.status)
    print(f"  of those, Status=full:         {full}")

    # ---------------- biomes -------------------------------------------------
    print("\n" + "=" * 72)
    print("1. BIOME SELECTION  (surface biome, all 256 columns of every chunk)")
    print("=" * 72)
    biome_cols: collections.Counter[str] = collections.Counter()
    biome_land: collections.Counter[str] = collections.Counter()
    biome_chunks: collections.defaultdict[str, set] = collections.defaultdict(set)
    for (cx, cz), ch in hh.items():
        for lx in range(0, 16, 2):
            for lz in range(0, 16, 2):
                top = ch.top_y(lx, lz)
                b = ch.biome(lx, top if top is not None else 128, lz)
                if not b:
                    continue
                biome_cols[b] += 1
                biome_chunks[b].add((cx, cz))
                if top is not None:
                    biome_land[b] += 1
    total = max(1, sum(biome_cols.values()))
    print(f"  {total} columns sampled across {len(hh)} chunks")
    print(f"  {'columns':>9} {'share':>7} {'with land':>10} {'chunks':>8}  biome")
    for b, n in biome_cols.most_common():
        print(f"  {n:9d} {100 * n / total:6.1f}% {biome_land[b]:10d} "
              f"{len(biome_chunks[b]):8d}  {b}")
    if len(biome_cols) < 2:
        print("  !! ONLY ONE BIOME IS EVER SELECTED")

    # ---------------- columns ------------------------------------------------
    print("\n" + "=" * 72)
    print("2. COLUMN DUMPS  (every y, air runs collapsed; air fraction over y0-255)")
    print("=" * 72)
    air_fracs: list[float] = []
    block_volume: collections.Counter[str] = collections.Counter()
    chalk_ys: list[int] = []
    strata_ys: collections.defaultdict[str, list[int]] = collections.defaultdict(list)
    surface_ys: list[int] = []
    for ch in hh.values():
        for lx in range(0, 16, 4):
            for lz in range(0, 16, 4):
                col = ch.column(lx, lz)
                air_fracs.append(1.0 - len(col) / 256.0)
                for y, n in col.items():
                    block_volume[n] += 1
                    s = short(n)
                    if s in ("resonant_chalk", "echo_slate", "amber_strata",
                             "raw_phonolite", "chime_sand"):
                        strata_ys[s].append(y)
                    if s == "resonant_chalk":
                        chalk_ys.append(y)
                t = ch.top_y(lx, lz)
                if t is not None:
                    surface_ys.append(t)
    print(f"  columns measured: {len(air_fracs)}")
    print(f"  mean air fraction (y0-255): {100 * statistics.mean(air_fracs):.1f}%")
    qs = statistics.quantiles(air_fracs, n=10)
    print(f"  air fraction p10 {100*qs[0]:.1f}%  median {100*statistics.median(air_fracs):.1f}%"
          f"  p90 {100*qs[-1]:.1f}%")
    land = [a for a in air_fracs if a < 1.0]
    print(f"  columns with any solid block: {len(land)}/{len(air_fracs)} "
          f"({100 * len(land) / max(1, len(air_fracs)):.1f}%)")
    if land:
        print(f"  mean air fraction of LAND-BEARING columns: "
              f"{100 * statistics.mean(land):.1f}%")
    if surface_ys:
        print(f"  surface y: min {min(surface_ys)}  median "
              f"{int(statistics.median(surface_ys))}  max {max(surface_ys)}")

    print("\n  STRATA BAND EXTENTS (y range where each block actually occurs):")
    for name, ys in sorted(strata_ys.items(), key=lambda kv: -len(kv[1])):
        if not ys:
            continue
        ys.sort()
        p5 = ys[len(ys) // 20]
        p95 = ys[min(len(ys) - 1, len(ys) * 19 // 20)]
        print(f"    {name:18s} n={len(ys):8d}  y {min(ys)}..{max(ys)}   "
              f"p5-p95 {p5}..{p95}   median {ys[len(ys)//2]}")

    print("\n  BLOCKS BY VOLUME (top 20, sampled columns):")
    tot_solid = max(1, sum(block_volume.values()))
    for n, c in block_volume.most_common(20):
        print(f"    {c:9d} {100*c/tot_solid:5.1f}%  {n}")

    print("\n  SAMPLE COLUMNS:")
    shown = 0
    for (cx, cz), ch in sorted(hh.items()):
        if shown >= 12:
            break
        lx = lz = 8
        col = ch.column(lx, lz)
        if not col:
            continue
        top = max(col)
        b = short(ch.biome(lx, top, lz))
        runs: list[list] = []
        for y in range(0, 256):
            name = short(col.get(y, AIR))
            if runs and runs[-1][2] == name:
                runs[-1][1] = y
            else:
                runs.append([y, y, name])
        solid = [r for r in runs if r[2] != "air"]
        frac = 100 * (1 - len(col) / 256)
        print(f"\n   ({cx * 16 + lx}, {cz * 16 + lz})  biome={b}  "
              f"air={frac:.0f}%  top=y{top}  solid blocks={len(col)}")
        print("      " + "  ".join(
            f"{a}-{b2}:{n}" if b2 > a else f"{a}:{n}" for a, b2, n in solid))
        shown += 1

    islands_and_hollows(hh)

    # ---------------- island shape (per-chunk, kept as a cross-check) --------
    print("\n" + "=" * 72)
    print("3b. SURFACE ROUGHNESS PER CHUNK (cross-check)")
    print("=" * 72)
    roughness: list[float] = []
    taper_scores: list[float] = []
    profiles_printed = 0
    for (cx, cz), ch in sorted(hh.items()):
        heights: dict[tuple[int, int], int] = {}
        for lx in range(16):
            for lz in range(16):
                t = ch.top_y(lx, lz)
                if t is not None:
                    heights[(lx, lz)] = t
        if len(heights) < 40:
            continue
        diffs = []
        for (lx, lz), h in heights.items():
            for dx, dz in ((1, 0), (0, 1)):
                n = heights.get((lx + dx, lz + dz))
                if n is not None:
                    diffs.append(abs(h - n))
        if diffs:
            roughness.append(statistics.mean(diffs))
        # area per y: a cone loses area downward, a pillar keeps it
        area: collections.Counter[int] = collections.Counter()
        for lx in range(16):
            for lz in range(16):
                for y in ch.column(lx, lz):
                    area[y] += 1
        if not area:
            continue
        ytop = max(area)
        ybot = min(area)
        peak_y = max(area, key=lambda y: area[y])
        peak = area[peak_y]
        below = [y for y in area if y < peak_y]
        if below and peak:
            # how much of the widest layer survives 8 blocks further down
            probe = peak_y - 8
            score = area.get(probe, 0) / peak
            taper_scores.append(score)
        if profiles_printed < 6 and (ytop - ybot) > 12:
            print(f"\n   chunk ({cx},{cz}) blocks x{cx*16}..{cx*16+15} "
                  f"z{cz*16}..{cz*16+15}   solid y{ybot}..{ytop}")
            print(f"     surface roughness (mean |dh| between adjacent columns): "
                  f"{statistics.mean(diffs):.2f} blocks")
            step = max(1, (ytop - ybot) // 16)
            bars = []
            for y in range(ytop, ybot - 1, -step):
                a = area.get(y, 0)
                bars.append(f"     y{y:3d} {a:3d}/256 " + "#" * (a // 6))
            print("\n".join(bars))
            profiles_printed += 1
    if roughness:
        print(f"\n  chunks profiled: {len(roughness)}")
        print(f"  MEAN SURFACE ROUGHNESS: {statistics.mean(roughness):.2f} blocks "
              f"(0 = flat plate, >1.5 = rugged)")
        print(f"    p10 {sorted(roughness)[len(roughness)//10]:.2f}   "
              f"median {statistics.median(roughness):.2f}   "
              f"p90 {sorted(roughness)[9*len(roughness)//10]:.2f}")
    if taper_scores:
        print(f"  UNDERSIDE TAPER: area 8 blocks below the widest layer, as a "
              f"share of it")
        print(f"    mean {statistics.mean(taper_scores):.2f}  "
              f"median {statistics.median(taper_scores):.2f}    "
              f"(1.0 = vertical wall, <0.6 = conical)")

    # ---------------- holes and debris ---------------------------------------
    print("\n" + "=" * 72)
    print("4. GROUND HOLES AND DEBRIS")
    print("=" * 72)
    holes = 0
    holes_with_debris = 0
    chunks_with_holes = 0
    debris_surface = 0
    for ch in hh.values():
        heights = {}
        for lx in range(16):
            for lz in range(16):
                t = ch.top_y(lx, lz)
                if t is not None:
                    heights[(lx, lz)] = t
        if len(heights) < 60:
            continue
        med = statistics.median(heights.values())
        found = 0
        for (lx, lz), h in heights.items():
            if med - h >= 4:
                found += 1
                floor_block = ch.block(lx, h, lz)
                if floor_block in DEBRIS_BLOCKS:
                    holes_with_debris += 1
            if ch.block(lx, h, lz) in DEBRIS_BLOCKS and h >= med:
                debris_surface += 1
        holes += found
        if found:
            chunks_with_holes += 1
    print(f"  chunks with a measurable surface (>=60 land columns): checked")
    print(f"  depression columns (>=4 blocks below the chunk median surface): {holes}")
    print(f"    of which the floor block is a debris block: {holes_with_debris}")
    print(f"  chunks containing at least one depression: {chunks_with_holes}")
    print(f"  surface columns topped by a debris-palette block: {debris_surface}")

    # ---------------- trees --------------------------------------------------
    print("\n" + "=" * 72)
    print("5. TREES PER CHUNK")
    print("=" * 72)
    per_chunk: list[int] = []
    trunk_positions: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    species: collections.Counter[str] = collections.Counter()
    leaf_total = 0
    for (cx, cz), ch in hh.items():
        trunks: list[tuple[int, int, int]] = []
        for lx in range(16):
            for lz in range(16):
                col = ch.column(lx, lz)
                for y, name in col.items():
                    if name in LOG_BLOCKS and col.get(y - 1) not in LOG_BLOCKS:
                        trunks.append((cx * 16 + lx, y, cz * 16 + lz))
                        species[short(name)] += 1
                    elif name in LEAF_BLOCKS:
                        leaf_total += 1
        per_chunk.append(len(trunks))
        if trunks:
            trunk_positions[(cx, cz)] = trunks
    if per_chunk:
        n = len(per_chunk)
        print(f"  chunks examined: {n}")
        print(f"  TREE BASES PER CHUNK: mean {sum(per_chunk)/n:.2f}   "
              f"median {int(statistics.median(per_chunk))}   max {max(per_chunk)}")
        hist = collections.Counter(per_chunk)
        print("  distribution:")
        for k in sorted(hist):
            print(f"    {k:3d} trees: {hist[k]:5d} chunks "
                  f"({100*hist[k]/n:5.1f}%)  " + "#" * min(40, hist[k] * 40 // n))
        print(f"  total trunk bases: {sum(per_chunk)}   leaf blocks: {leaf_total}")
        print(f"  by species: {dict(species)}")

    # nearest-neighbour spacing, diagonals included
    allt = [t for v in trunk_positions.values() for t in v]
    if len(allt) > 1:
        dists = []
        for i, (x1, y1, z1) in enumerate(allt):
            best = None
            for j, (x2, y2, z2) in enumerate(allt):
                if i == j:
                    continue
                d = math.hypot(x1 - x2, z1 - z2)
                if d < 40 and (best is None or d < best):
                    best = d
            if best is not None:
                dists.append(best)
        if dists:
            dists.sort()
            print(f"\n  NEAREST-NEIGHBOUR TRUNK SPACING (horizontal, diagonals "
                  f"included), n={len(dists)}")
            print(f"    min {dists[0]:.2f}   p10 {dists[len(dists)//10]:.2f}   "
                  f"median {dists[len(dists)//2]:.2f}   mean "
                  f"{statistics.mean(dists):.2f} blocks")
            for cut in (1.5, 2.5, 3.5, 4.5):
                c = sum(1 for d in dists if d < cut)
                print(f"    trunks with a neighbour closer than {cut}: {c} "
                      f"({100*c/len(dists):.1f}%)")

    # ---------------- knell --------------------------------------------------
    print("\n" + "=" * 72)
    print("6. KNELL ORE CONTAINMENT")
    print("=" * 72)
    for label, chunks in (("Hollow Horizon", hh), ("Overworld", ow)):
        counts: collections.Counter[str] = collections.Counter()
        knell_ys: list[int] = []
        knell = f"{NS}:knell_ore"
        for ch in chunks.values():
            for sy, sec in ch.blocks.items():
                # Counter() over the section runs in C; a per-block Python loop
                # over ~90M blocks does not. Only sections that actually contain
                # Knell pay for the index walk that recovers its y.
                tally = collections.Counter(sec)
                for name, n in tally.items():
                    if name.startswith(NS + ":"):
                        counts[name] += n
                if knell in tally:
                    for i, name in enumerate(sec):
                        if name == knell:
                            knell_ys.append(sy * 16 + (i // 256))
        print(f"\n  {label}: {len(chunks)} chunks")
        knell = counts.get(f"{NS}:knell_ore", 0)
        print(f"    echoing_void:knell_ore = {knell}")
        if knell_ys:
            print(f"      y range {min(knell_ys)}..{max(knell_ys)}, "
                  f"median {int(statistics.median(knell_ys))}")
        ores = {k: v for k, v in counts.items() if "ore" in k}
        for k, v in sorted(ores.items(), key=lambda kv: -kv[1]):
            print(f"    {k} = {v}")
        if label == "Overworld" and chunks:
            print(f"    (control: {sum(counts.values())} echoing_void blocks total "
                  f"in the Overworld sample)")
    return 0


# ---------------------------------------------------------------------------
# phase three: ask the running server, so the biome names are replies not reads
# ---------------------------------------------------------------------------

BIOMES = [f"{NS}:resonant_plains", f"{NS}:shattered_octaves", f"{NS}:chalk_reaches"]
STRUCTURES = [f"{NS}:outpost_of_the_tuners", f"{NS}:tuner_encampment"]


def live(points: list[tuple[int, int]]) -> int:
    import re
    from test_tps import Server, ensure_eula, ensure_server_properties

    ensure_eula(True)
    ensure_server_properties()
    props = ROOT / "run" / "server.properties"
    text = props.read_text(encoding="utf-8")
    text = re.sub(r"^level-name=.*$", f"level-name={WORLD}", text, flags=re.M)
    text = re.sub(r"^server-port=.*$", f"server-port={PROBE_PORT}", text, flags=re.M)
    props.write_text(text, encoding="utf-8")

    server = Server(False)
    server.start()
    if not server.wait_for_boot(1200):
        print("FAILED: server did not boot. Last 60 lines:")
        for line in server.transcript[-60:]:
            print("  " + line)
        return 1
    print(f"  server up on world {WORLD}")
    time.sleep(3)

    def run(cmd: str, settle: float = 1.2) -> list[str]:
        mark = len(server.transcript)
        server.send(cmd)
        time.sleep(settle)
        out = []
        for line in server.transcript[mark:]:
            idx = line.find("]: ")
            out.append(line[idx + 3:] if idx >= 0 else line)
        return [l for l in out if l.strip()]

    print("\n=== /locate biome (raw server replies) ===")
    for b in BIOMES:
        cmd = f"execute in {HH} run locate biome {b}"
        print(f"  > {cmd}")
        for line in run(cmd, 4.0):
            print(f"    {line}")

    print("\n=== /locate structure (raw server replies) ===")
    for s in STRUCTURES:
        cmd = f"execute in {HH} run locate structure {s}"
        print(f"  > {cmd}")
        for line in run(cmd, 6.0):
            print(f"    {line}")

    print("\n=== biome at each sample point (execute if biome) ===")
    for (x, z) in points:
        hits = []
        for b in BIOMES:
            cmd = (f"execute in {HH} positioned {x} 128 {z} "
                   f"if biome ~ ~ ~ {b} run say EVBIOME {x} {z} {b}")
            out = run(cmd, 1.0)
            said = [l for l in out if "EVBIOME" in l]
            failed = [l for l in out if "Unknown" in l or "Incorrect" in l
                      or "Expected" in l or "error" in l.lower()]
            if failed:
                print(f"  ({x},{z}) COMMAND ERROR for {b}:")
                for line in failed:
                    print(f"      {line}")
            if said:
                hits.append((b, said[-1]))
        if hits:
            for b, line in hits:
                print(f"  ({x:6d},{z:6d}) -> {line}")
        else:
            print(f"  ({x:6d},{z:6d}) -> NO BIOME MATCHED any of the three")

    print("\n=== Knell containment, asked of the server ===")
    for dim in (HH, "minecraft:overworld"):
        cmd = f"execute in {dim} run locate biome {NS}:resonant_plains"
        print(f"  > {cmd}")
        for line in run(cmd, 4.0):
            print(f"    {line}")

    server.send("stop")
    if server.proc:
        try:
            server.proc.wait(timeout=180)
        except Exception:
            server.proc.kill()
    print("  server stopped")
    return 0





# ---------------------------------------------------------------------------
# phase four: the follow-ups the first pass raised
# ---------------------------------------------------------------------------

SOIL = {
    f"{NS}:resonance_moss", f"{NS}:amber_lichen", f"{NS}:chime_grass",
    f"{NS}:echo_sprout", f"{NS}:crystal_bloom",
}
# Everything worldgen itself can put in a Hollow Horizon chunk: the surface
# rule's strata and soils, the ore and vegetation features, and the four trees.
# Naming the NATURAL set rather than a handful of structure blocks means the
# structure test keeps working when a structure is rebuilt out of new material -
# the encampment tents just moved to stair rooflines, and a hardcoded list of
# {polished_phonolite, chalk_bricks} would have stopped seeing them.
NATURAL = {
    AIR,
    f"{NS}:raw_phonolite", f"{NS}:echo_slate", f"{NS}:amber_strata",
    f"{NS}:resonant_chalk", f"{NS}:chime_sand", f"{NS}:humming_crystal",
    f"{NS}:resonance_moss", f"{NS}:amber_lichen", f"{NS}:chime_grass",
    f"{NS}:echo_sprout", f"{NS}:crystal_bloom", f"{NS}:bismuth_cluster",
    f"{NS}:phonolite_resonant_bismuth_ore", f"{NS}:phonolite_null_iron_ore",
    f"{NS}:knell_ore",
} | LOG_BLOCKS | LEAF_BLOCKS


def is_structure_chunk(ch: "Chunk") -> bool:
    for sec in ch.blocks.values():
        for name in set(sec):
            if name not in NATURAL:
                return True
    return False


def detail(world: str) -> int:
    hh = load_chunks(world, "hh")
    print(f"=== detail pass over {len(hh)} full chunks ===")

    # ---- A. where is the rock, and does the Knell window contain any? -------
    print("\n" + "=" * 72)
    print("A. THE KNELL HEIGHT WINDOW vs WHERE PHONOLITE ACTUALLY IS")
    print("=" * 72)
    solid_by_y: collections.Counter[int] = collections.Counter()
    phon_by_y: collections.Counter[int] = collections.Counter()
    phon = f"{NS}:raw_phonolite"
    for ch in hh.values():
        for sy, sec in ch.blocks.items():
            base = sy * 16
            for i, name in enumerate(sec):
                if name != AIR:
                    y = base + (i // 256)
                    solid_by_y[y] += 1
                    if name == phon:
                        phon_by_y[y] += 1
    tot_solid = sum(solid_by_y.values())
    tot_phon = sum(phon_by_y.values())
    print(f"  total solid blocks: {tot_solid}   raw_phonolite: {tot_phon}")
    win_solid = sum(n for y, n in solid_by_y.items() if 0 <= y <= 34)
    win_phon = sum(n for y, n in phon_by_y.items() if 0 <= y <= 34)
    print(f"\n  ore_knell_placed height_range is absolute 0..34, "
          f"very_biased_to_bottom(inner=4)")
    print(f"    solid blocks inside y0..34:   {win_solid} "
          f"({100*win_solid/max(1,tot_solid):.3f}% of all rock)")
    print(f"    raw_phonolite inside y0..34:  {win_phon} "
          f"({100*win_phon/max(1,tot_phon):.3f}% of all phonolite)")
    print(f"    -> the ore can ONLY replace raw_phonolite "
          f"(tag phonolite_ore_replaceables)")
    print("\n  raw_phonolite by 16-block band:")
    for lo in range(0, 256, 16):
        n = sum(phon_by_y.get(y, 0) for y in range(lo, lo + 16))
        if n:
            print(f"    y{lo:3d}-{lo+15:3d}: {n:9d} " + "#" * min(50, n // 2000))

    # ---- B. trees, counted properly ----------------------------------------
    print("\n" + "=" * 72)
    print("B. TREES, EXCLUDING STRUCTURE TIMBER AND FORK BRANCHES")
    print("=" * 72)
    per_chunk: list[int] = []
    struct_chunks = 0
    trunks_all: list[tuple[int, int, int]] = []
    species: collections.Counter[str] = collections.Counter()
    for (cx, cz), ch in hh.items():
        if is_structure_chunk(ch):
            struct_chunks += 1
            continue
        trunks = []
        for lx in range(16):
            for lz in range(16):
                col = ch.column(lx, lz)
                for y, name in col.items():
                    if name not in LOG_BLOCKS:
                        continue
                    below = col.get(y - 1)
                    # A real trunk base stands ON GROUND. A fork branch has air
                    # or leaves under it, and the block above a lower trunk log
                    # belongs to the same trunk.
                    if below is not None and below not in LOG_BLOCKS \
                            and below not in LEAF_BLOCKS:
                        trunks.append((cx * 16 + lx, y, cz * 16 + lz))
                        species[short(name)] += 1
        per_chunk.append(len(trunks))
        trunks_all.extend(trunks)
    n = max(1, len(per_chunk))
    print(f"  natural chunks: {len(per_chunk)}   structure chunks excluded: "
          f"{struct_chunks}")
    print(f"  TREES PER CHUNK: mean {sum(per_chunk)/n:.2f}   "
          f"median {int(statistics.median(per_chunk))}   max {max(per_chunk)}")
    hist = collections.Counter(per_chunk)
    for k in sorted(hist):
        print(f"    {k:3d} trees: {hist[k]:5d} chunks ({100*hist[k]/n:5.1f}%)  "
              + "#" * min(40, hist[k] * 40 // n))
    print(f"  total trees: {sum(per_chunk)}   by species: {dict(species)}")
    if len(trunks_all) > 1:
        dists = []
        for i, (x1, y1, z1) in enumerate(trunks_all):
            best = None
            for j, (x2, y2, z2) in enumerate(trunks_all):
                if i == j:
                    continue
                d = math.hypot(x1 - x2, z1 - z2)
                if d < 48 and (best is None or d < best):
                    best = d
            if best is not None:
                dists.append(best)
        dists.sort()
        print(f"\n  NEAREST-NEIGHBOUR SPACING (diagonals included), n={len(dists)}")
        print(f"    min {dists[0]:.2f}  p5 {dists[len(dists)//20]:.2f}  "
              f"p25 {dists[len(dists)//4]:.2f}  median {dists[len(dists)//2]:.2f}"
              f"  mean {statistics.mean(dists):.2f}")
        for cut in (1.01, 2.01, 3.01, 4.01, 5.01):
            c = sum(1 for d in dists if d < cut)
            print(f"    closer than {cut - 0.01:.0f}: {c:5d} "
                  f"({100*c/len(dists):5.1f}%)")

    # ---- C. debris that is demonstrably PLACED ------------------------------
    print("\n" + "=" * 72)
    print("C. FALLEN DEBRIS (a strata block resting on soil = placed, not strata)")
    print("=" * 72)
    placed = 0
    chunks_with = 0
    for ch in hh.values():
        hit = 0
        for lx in range(16):
            for lz in range(16):
                col = ch.column(lx, lz)
                if not col:
                    continue
                top = max(col)
                if col[top] in DEBRIS_BLOCKS and col.get(top - 1) in SOIL:
                    hit += 1
        placed += hit
        if hit:
            chunks_with += 1
    print(f"  debris blocks resting on soil: {placed}")
    print(f"  chunks containing at least one: {chunks_with} of {len(hh)}")
    print(f"  mean per chunk: {placed / max(1, len(hh)):.2f}   "
          f"(island_debris_placed asks for count=8 tries per chunk)")
    return 0



def hollow(world: str) -> int:
    """The matching-hollow test, with a chunk-local control.

    For every column: the ground surface is the highest solid block below
    SKY_FLOOR, and the column is 'under an island' if anything solid floats
    above SKY_FLOOR. Comparing the two populations WITHIN each chunk cancels the
    large-scale trend in ground height, which a bounding-box ring around the
    island does not - the first version of this measurement used a ring and was
    misled by it on the largest islands.
    """
    hh = load_chunks(world, "hh")
    print(f"=== hollow test over {len(hh)} full chunks (SKY_FLOOR={SKY_FLOOR}) ===")
    diffs: list[float] = []
    n_under = n_open = 0
    debris_under = debris_open = 0
    for ch in hh.values():
        under: list[int] = []
        openc: list[int] = []
        for lx in range(16):
            for lz in range(16):
                col = ch.column(lx, lz)
                if not col:
                    continue
                below = [y for y in col if y < SKY_FLOOR]
                if not below:
                    continue
                top = max(below)
                floats = any(y >= SKY_FLOOR for y in col)
                (under if floats else openc).append(top)
                if col[top] in DEBRIS_BLOCKS and col.get(top - 1) in SOIL:
                    if floats:
                        debris_under += 1
                    else:
                        debris_open += 1
        n_under += len(under)
        n_open += len(openc)
        if len(under) >= 12 and len(openc) >= 12:
            diffs.append(statistics.median(openc) - statistics.median(under))
    print(f"  ground columns under an island: {n_under}")
    print(f"  ground columns under open sky:  {n_open}")
    print(f"  chunks with >=12 of each:       {len(diffs)}")
    if not diffs:
        print("  not enough paired columns to judge")
        return 1
    diffs.sort()
    print("\n  GROUND HEIGHT: open-sky median MINUS under-island median, per chunk")
    print("  positive = the ground dips under the island, which is the contract")
    print(f"    mean {statistics.mean(diffs):+.2f} blocks   "
          f"median {statistics.median(diffs):+.1f}")
    print(f"    p10 {diffs[len(diffs)//10]:+.1f}   p25 {diffs[len(diffs)//4]:+.1f}"
          f"   p75 {diffs[3*len(diffs)//4]:+.1f}   p90 {diffs[9*len(diffs)//10]:+.1f}")
    for cut in (1, 2, 3, 5, 8):
        c = sum(1 for d in diffs if d >= cut)
        print(f"    chunks dipping >= {cut} blocks: {c}/{len(diffs)} "
              f"({100*c/len(diffs):.0f}%)")
    bad = sum(1 for d in diffs if d <= -1)
    print(f"    chunks where the ground is HIGHER under the island: {bad}/"
          f"{len(diffs)} ({100*bad/len(diffs):.0f}%)")
    print(f"\n  debris resting on soil, under an island: {debris_under}")
    print(f"  debris resting on soil, under open sky:  {debris_open}")
    if n_under and n_open:
        print(f"  per 1000 ground columns: {1000*debris_under/n_under:.1f} under "
              f"island vs {1000*debris_open/n_open:.1f} in the open")
    return 0



def tagtest(spots: list[tuple[int, int, int]]) -> int:
    """Ask the running game whether the ore target tags actually contain anything.

    knell_ore is the only ore in the mod that targets
    echoing_void:phonolite_ore_replaceables; every ore that DOES generate targets
    echoing_void:hollow_horizon_carvable. If the first tag is empty at runtime,
    the ore feature runs, finds nothing it may replace, and places zero blocks
    without logging anything - which is exactly what the region scan shows.
    """
    from test_tps import Server, ensure_eula, ensure_server_properties

    ensure_eula(True)
    ensure_server_properties()
    props = ROOT / "run" / "server.properties"
    text = props.read_text(encoding="utf-8")
    text = re.sub(r"^level-name=.*$", f"level-name={WORLD}", text, flags=re.M)
    text = re.sub(r"^server-port=.*$", f"server-port={PROBE_PORT}", text, flags=re.M)
    props.write_text(text, encoding="utf-8")

    server = Server(False)
    server.start()
    if not server.wait_for_boot(1200):
        print("FAILED: server did not boot")
        for line in server.transcript[-40:]:
            print("  " + line)
        return 1
    print("  server up")
    time.sleep(3)

    def run(cmd: str, settle: float = 1.2) -> list[str]:
        mark = len(server.transcript)
        server.send(cmd)
        time.sleep(settle)
        out = []
        for line in server.transcript[mark:]:
            i = line.find("]: ")
            out.append(line[i + 3:] if i >= 0 else line)
        return [l for l in out if l.strip()]

    # A scratch spot in the void, well away from any terrain.
    X, Y, Z = 500, 100, 500

    # Nothing is loaded on a fresh boot except spawn, and /setblock, /place and
    # /execute if block all answer "That position is not loaded" rather than
    # failing in a way that looks like a tag problem. Pull every position we are
    # about to touch into memory first.
    print("\n=== loading the chunks under test ===")
    for (tx, tz) in [(X, Z)] + [(a, c) for (a, _, c) in spots]:
        out = run(f"execute in {HH} run forceload add {tx-16} {tz-16} {tx+16} {tz+16}",
                  2.0)
        for line in out[:1]:
            print(f"    {line}")
    time.sleep(8)
    print("\n=== put a known block down, then ask the tags about it ===")
    for cmd in (
        f"execute in {HH} run setblock {X} {Y} {Z} {NS}:raw_phonolite replace",
        f"execute in {HH} run setblock {X} {Y} {Z+2} {NS}:echo_slate replace",
    ):
        print(f"  > {cmd}")
        for line in run(cmd, 2.0):
            print(f"    {line}")

    checks = [
        (f"{NS}:phonolite_ore_replaceables", X, Z, "raw_phonolite"),
        (f"{NS}:hollow_horizon_carvable", X, Z, "raw_phonolite"),
        (f"{NS}:phonolite_ore_replaceables", X, Z + 2, "echo_slate"),
        (f"{NS}:hollow_horizon_carvable", X, Z + 2, "echo_slate"),
    ]
    print("\n=== tag membership, as the server reports it ===")
    for tag, x, z, what in checks:
        cmd = (f"execute in {HH} if block {x} {Y} {z} #{tag} "
               f"run say EVTAG {tag} matches {what}")
        out = run(cmd, 1.5)
        hit = [l for l in out if "EVTAG" in l]
        err = [l for l in out if "Unknown" in l or "Incorrect" in l
               or "Can't" in l or "Expected" in l]
        verdict = "MATCH" if hit else "no match"
        print(f"  {what:16s} in #{tag}: {verdict}")
        for line in (err or [])[:3]:
            print(f"      RAW: {line}")
        if hit:
            print(f"      RAW: {hit[-1]}")

    print("\n=== and confirm the ore block itself exists ===")
    for cmd in (f"execute in {HH} run setblock {X} {Y+4} {Z} {NS}:knell_ore replace",
                f"execute in {HH} run data get block {X} {Y+4} {Z}"):
        print(f"  > {cmd}")
        for line in run(cmd, 2.0)[:3]:
            print(f"    {line}")

    # The decisive test: force the feature to run ON A REAL PHONOLITE BLOCK and
    # count what it leaves behind. This separates "the feature is broken" from
    # "the feature works but almost never lands on a legal host block".
    print("\n=== /place feature ore_knell on known raw_phonolite ===")
    total_placed = 0
    for (px, py, pz) in spots:
        run(f"execute in {HH} run setblock {px} {py} {pz} {NS}:raw_phonolite replace", 1.0)
        run(f"execute in {HH} run fill {px-4} {py-4} {pz-4} {px+4} {py+4} {pz+4} "
            f"{NS}:raw_phonolite replace {NS}:knell_ore", 1.5)
        # Size sweep. OreFeature's vein radius is derived from `size`, and below
        # some floor the ellipsoid never contains a block centre, so the feature
        # places nothing at all. Each size is tried REPS times, resetting the
        # host rock between trials because a success eats the phonolite the next
        # trial needs.
        REPS = 8
        print(f"    size  placed/{REPS}   knell blocks (total over {REPS} runs)")
        for n in range(2, 11):
            feat = f"{NS}:zz_size_{n:02d}"
            ok = 0
            blocks = 0
            for _ in range(REPS):
                run(f"execute in {HH} run fill {px-5} {py-5} {pz-5} {px+5} {py+5} "
                    f"{pz+5} {NS}:raw_phonolite", 1.0)
                out = run(f"execute in {HH} run place feature {feat} {px} {py} {pz}",
                          1.6)
                if any("Placed" in l for l in out):
                    ok += 1
                cnt = run(f"execute in {HH} run fill {px-5} {py-5} {pz-5} {px+5} "
                          f"{py+5} {pz+5} {NS}:raw_phonolite replace {NS}:knell_ore",
                          1.6)
                for line in cnt:
                    m = re.search(r"Successfully filled (\d+) block", line)
                    if m:
                        blocks += int(m.group(1))
            print(f"    {n:4d}  {ok:6d}      {blocks:5d}   "
                  f"(mean {blocks / max(1, ok):.1f} per success)")
        cmd = ""
        out = []
        cnt = run(f"execute in {HH} run fill {px-4} {py-4} {pz-4} {px+4} {py+4} "
                  f"{pz+4} {NS}:raw_phonolite replace {NS}:knell_ore", 2.0)
        got = 0
        for line in cnt:
            m = re.search(r"Successfully filled (\d+) block", line)
            if m:
                got = int(m.group(1))
        print(f"    -> knell_ore blocks placed here: {got}")
        total_placed += got
    print(f"\n  TOTAL knell_ore placed by {len(spots)} forced runs: {total_placed}")

    server.send("stop")
    if server.proc:
        try:
            server.proc.wait(timeout=180)
        except Exception:
            server.proc.kill()
    print("  server stopped")
    return 0


def main() -> int:
    global WORLD
    if "--world" in sys.argv:
        WORLD = sys.argv[sys.argv.index("--world") + 1]
        print(f"(world: {WORLD})")
    if "--tags" in sys.argv:
        i = sys.argv.index("--tags")
        spots = []
        trip = re.compile(r"^-?\d+,-?\d+,-?\d+$")
        for arg in sys.argv[i + 1:]:
            if not trip.match(arg):
                break
            a, b, c = arg.split(",")
            spots.append((int(a), int(b), int(c)))
        return tagtest(spots)
    if "--hollow" in sys.argv:
        i = sys.argv.index("--hollow")
        w = sys.argv[i + 1] if len(sys.argv) > i + 1 and             not sys.argv[i + 1].startswith("-") else WORLD
        return hollow(w)
    if "--detail" in sys.argv:
        idx = sys.argv.index("--detail")
        w = sys.argv[idx + 1] if len(sys.argv) > idx + 1 and             not sys.argv[idx + 1].startswith("-") else WORLD
        return detail(w)
    if "--live" in sys.argv:
        idx = sys.argv.index("--live")
        pts = []
        # A point may legitimately start with '-' (negative x), so match the
        # shape of a coordinate pair rather than treating any leading dash as
        # the start of the next flag.
        point_re = re.compile(r"^-?\d+,-?\d+$")
        for arg in sys.argv[idx + 1:]:
            if not point_re.match(arg):
                break
            x, _, z = arg.partition(",")
            pts.append((int(x), int(z)))
        if not pts:
            pts = [(x + 96, z + 96) for x, z in PATCHES]
        return live(pts)
    if "--gen" in sys.argv:
        idx = sys.argv.index("--wait") if "--wait" in sys.argv else -1
        wait = int(sys.argv[idx + 1]) if idx >= 0 else 180
        return generate(wait)
    if "--analyze" in sys.argv:
        idx = sys.argv.index("--analyze")
        world = sys.argv[idx + 1] if len(sys.argv) > idx + 1 and \
            not sys.argv[idx + 1].startswith("-") else WORLD
        return analyze(world)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

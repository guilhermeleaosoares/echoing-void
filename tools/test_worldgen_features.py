"""Do this round's worldgen features actually appear in a generated world?

`/place feature` proves a configured feature parses and can build. It says
nothing about whether the PLACEMENT ever fires - the rarity filter, the
heightmap, the biome list and the block-predicate filter are all between a
loaded feature and a feature a player will ever walk into, and every one of them
can silently reject every attempt.

So this generates a fresh world, forceloads a spread of Hollow Horizon chunks,
saves, and then reads the region files off disk and counts:

  hushwater      lakes on the island tops, and springs through the rock
  echo gourd     the wild patches on the Resonant Plains
  carved air     see below

Phase one and phase two are separate commands on purpose, exactly as
tools/probe_hollow.py splits them: a crashed or rate-limited driver then never
costs the generated world.

  python tools/test_worldgen_features.py --gen
  python tools/test_worldgen_features.py --analyze

ON PROVING THE CARVERS RAN
--------------------------
There is no signature to look for. Vanilla marks carved blocks CAVE_AIR only
because its aquifer hands one back; this dimension has aquifers off and
`default_fluid: air`, so WorldCarver#getCarveState returns plain AIR through
Aquifer.FluidStatus#at and a carved block is indistinguishable from a noise
cavern by inspection.

The measurement here is therefore a COMPARISON, and it needs both halves to mean
anything: generate once as shipped, then again on the same seed with the biomes'
carver lists emptied (`python tools/gen_worldgen.py --no-carvers`), and compare
the open-air fraction inside the carver band. Running only the first half prints
the number and says so rather than passing.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import probe_hollow  # noqa: E402
from probe_hollow import Chunk, load_chunks  # noqa: E402
from test_tps import Server, ensure_eula  # noqa: E402

NS = "echoing_void"
HH = f"{NS}:the_hollow_horizon"
AIR = "minecraft:air"

HUSHWATER = f"{NS}:hushwater"
GOURD = f"{NS}:echo_gourd"
CARVABLE = {f"{NS}:raw_phonolite", f"{NS}:echo_slate",
            f"{NS}:amber_strata", f"{NS}:resonant_chalk"}

# The band the three carvers cut: hollow_cave 30..140, hollow_cave_deep 10..70,
# hollow_canyon 50..110.
CARVER_LO, CARVER_HI = 30, 140

# A single wide patch rather than probe_hollow's six: this is a presence test,
# not a biome-parameter survey, and one 20x20 block of chunks generates in a
# fraction of the time.
PATCH_CHUNKS = 20


def generate(world: str, port: int) -> int:
    """Boot, forceload a block of Hollow Horizon chunks, save, stop."""
    if not ensure_eula(True):
        return 1

    props = ROOT / "run" / "server.properties"
    text = props.read_text(encoding="utf-8") if props.exists() else ""
    text = re.sub(r"^level-name=.*$", f"level-name={world}", text, flags=re.M)
    text = re.sub(r"^server-port=.*$", f"server-port={port}", text, flags=re.M)
    if "pause-when-empty-seconds" not in text:
        text += "\npause-when-empty-seconds=0\n"
    else:
        text = re.sub(r"^pause-when-empty-seconds=.*$",
                      "pause-when-empty-seconds=0", text, flags=re.M)
    props.write_text(text, encoding="utf-8")
    print(f"  level-name={world}  server-port={port}")

    server = Server(True)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    half = PATCH_CHUNKS * 16 // 2
    server.send(f"execute in {HH} run forceload add {-half} {-half} {half - 1} {half - 1}")
    time.sleep(2)
    # Generation is asynchronous; give it real time rather than a fixed sleep
    # that happens to be long enough on this machine today.
    deadline = time.time() + 600
    while time.time() < deadline:
        server.send(f"execute in {HH} run setblock {half - 8} 200 {half - 8} minecraft:air replace")
        got = []
        end = time.time() + 3
        while time.time() < end:
            try:
                got.append(server.lines.get(timeout=0.2))
            except Exception:
                pass
        if "not loaded" not in " ".join(got).lower():
            break
        time.sleep(5)
    print(f"  patch generated after {int(600 - (deadline - time.time()))}s")

    server.send("save-all flush")
    time.sleep(15)
    server.send(f"execute in {HH} run forceload remove all")
    time.sleep(2)
    server.stop()
    return 0


def analyze(world: str) -> int:
    chunks = load_chunks(world, HH)
    if not chunks:
        print(f"FAILED: no region data for run/{world}")
        return 1

    counts = {HUSHWATER: 0, GOURD: 0}
    carver_air = 0
    carver_rock = 0
    full = 0
    for ch in chunks.values():
        if not str(ch.status).endswith("full"):
            continue
        full += 1
        for sy, section in ch.blocks.items():
            base = sy * 16
            in_band = CARVER_LO <= base <= CARVER_HI
            for i, name in enumerate(section):
                if name in counts:
                    counts[name] += 1
                if in_band:
                    if name == AIR:
                        carver_air += 1
                    elif name in CARVABLE:
                        carver_rock += 1

    total = carver_air + carver_rock
    fraction = carver_air / total if total else 0.0
    print(f"  {full} fully generated chunks read from run/{world}")
    print(f"  hushwater blocks      {counts[HUSHWATER]:>8}")
    print(f"  echo gourd blocks     {counts[GOURD]:>8}")
    print(f"  carver band y{CARVER_LO}-{CARVER_HI}: {carver_air} open, {carver_rock} rock "
          f"-> {fraction:.1%} open")

    failures = []
    if full < 100:
        failures.append(f"only {full} chunks generated - the patch did not finish, "
                        f"so a zero count below proves nothing")
    if counts[HUSHWATER] == 0:
        failures.append("no hushwater anywhere in the sample - neither the lakes nor "
                        "the springs are placing")
    if counts[GOURD] == 0:
        failures.append("no echo gourds anywhere in the sample - the wild patch "
                        "feature is not placing")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: hushwater and wild gourds both generate in the Hollow Horizon")
    print("      (the carver figure above is one half of a comparison - see the "
          "module docstring)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--world", default="feature_probe")
    ap.add_argument("--port", type=int, default=25602)
    args = ap.parse_args()

    if args.gen:
        return generate(args.world, args.port)
    if args.analyze:
        return analyze(args.world)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

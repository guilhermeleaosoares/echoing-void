"""
GATE 3 - Blockbench Bone & UV Coordinate Check.

Audits the .geo.json creature models:

  structure   valid Blockbench geometry envelope (format_version,
              minecraft:geometry[].description/bones), sane texture size
  bones       unique names, every parent resolves, no cycles, numeric pivots
  cubes       numeric origin, positive integer size, numeric uv
  uv bounds   each cube's box unwrap - (2d+2w) x (d+h) - fits inside the sheet
  uv overlap  two cubes may share a uv rect only if they are the same size
              (the intentional mirrored-limb case); differently sized cubes
              overlapping in uv space is a texture bug and fails the gate
  brief       each creature actually has the anatomy the brief specifies:
              echo_weaver      4 crests + 8 legs, each femur/tibia/tarsus
              strata_golem     4 legs + detachable crystal spire clusters
              resonance_wraith a core + 4 layered ribbon bands

Exit code 0 = gate passed, 1 = gate failed.

Run:  python tools/verify_models.py [-v]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEO_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "geo"

REQUIRED = {
    "echo_weaver": {
        "min_bones": 20,
        "expect": {
            "crest_": 4,
            "_femur": 8,
            "_tibia": 8,
            "_tarsus": 8,
        },
        "must_contain": ["cephalothorax", "abdomen"],
    },
    "strata_golem": {
        "min_bones": 10,
        "expect": {
            "_upper": 4,
            "_lower": 4,
            "cluster_": 3,
        },
        "must_contain": ["chassis", "head"],
    },
    "resonance_wraith": {
        "min_bones": 10,
        "expect": {
            "ribbon_1": 4,   # band root + inner/mid/outer layers
            "_inner": 4,
            "_mid": 4,
            "_outer": 4,
        },
        "must_contain": ["core"],
    },
}


def footprint(size: list[float]) -> tuple[int, int]:
    w, h, d = (int(round(v)) for v in size)
    return (2 * d + 2 * w, d + h)


def rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def audit(path: Path, verbose: bool) -> list[str]:
    name = path.name.replace(".geo.json", "")
    errors: list[str] = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unparseable JSON ({exc})"]

    if "format_version" not in data:
        errors.append("missing format_version")
    geos = data.get("minecraft:geometry")
    if not isinstance(geos, list) or not geos:
        return [f"{path.name}: missing minecraft:geometry array"]

    geo = geos[0]
    desc = geo.get("description", {})
    ident = desc.get("identifier", "")
    if not ident.startswith("geometry."):
        errors.append(f"identifier {ident!r} should start with 'geometry.'")

    tw, th = desc.get("texture_width"), desc.get("texture_height")
    if not isinstance(tw, int) or not isinstance(th, int) or tw <= 0 or th <= 0:
        return [f"{path.name}: bad texture_width/texture_height ({tw}x{th})"]

    bones = geo.get("bones")
    if not isinstance(bones, list) or not bones:
        return [f"{path.name}: no bones"]

    # ---- bone graph -----------------------------------------------------
    names: list[str] = []
    parents: dict[str, str | None] = {}
    for b in bones:
        bn = b.get("name")
        if not isinstance(bn, str) or not bn:
            errors.append("bone with missing/invalid name")
            continue
        if bn in parents:
            errors.append(f"duplicate bone name {bn!r}")
        names.append(bn)
        parents[bn] = b.get("parent")

        pivot = b.get("pivot")
        if not (isinstance(pivot, list) and len(pivot) == 3
                and all(isinstance(v, (int, float)) for v in pivot)):
            errors.append(f"bone {bn!r} has invalid pivot {pivot!r}")

    for bn, parent in parents.items():
        if parent is not None and parent not in parents:
            errors.append(f"bone {bn!r} references missing parent {parent!r}")

    for bn in parents:                       # cycle detection
        seen, cur, depth = {bn}, parents.get(bn), 0
        while cur is not None and depth < 64:
            if cur in seen:
                errors.append(f"bone cycle involving {bn!r}")
                break
            seen.add(cur)
            cur = parents.get(cur)
            depth += 1

    # ---- cubes and UV ---------------------------------------------------
    placed: list[tuple[tuple[int, int, int, int], tuple[int, int, int], str]] = []
    cube_count = 0
    for b in bones:
        bn = b.get("name", "?")
        for cube in b.get("cubes", []) or []:
            cube_count += 1
            origin, size, uv = cube.get("origin"), cube.get("size"), cube.get("uv")

            if not (isinstance(origin, list) and len(origin) == 3
                    and all(isinstance(v, (int, float)) for v in origin)):
                errors.append(f"{bn}: invalid origin {origin!r}")
                continue
            if not (isinstance(size, list) and len(size) == 3
                    and all(isinstance(v, (int, float)) and v > 0 for v in size)):
                errors.append(f"{bn}: invalid size {size!r}")
                continue
            if not (isinstance(uv, list) and len(uv) == 2
                    and all(isinstance(v, (int, float)) for v in uv)):
                errors.append(f"{bn}: invalid uv {uv!r}")
                continue

            fw, fh = footprint(size)
            ux, uy = int(uv[0]), int(uv[1])
            if ux < 0 or uy < 0:
                errors.append(f"{bn}: negative uv {uv!r}")
            if ux + fw > tw or uy + fh > th:
                errors.append(
                    f"{bn}: uv box {ux},{uy} +{fw}x{fh} overflows {tw}x{th} sheet")

            key = tuple(int(round(v)) for v in size)
            rect = (ux, uy, fw, fh)
            for other_rect, other_key, other_bone in placed:
                if other_key == key and other_rect == rect:
                    continue                      # shared sheet for identical limbs
                if rects_overlap(rect, other_rect):
                    errors.append(
                        f"{bn}: uv {rect} overlaps {other_bone} {other_rect} "
                        f"with a different cube size {other_key} vs {key}")
                    break
            placed.append((rect, key, bn))  # type: ignore[arg-type]

    # ---- brief conformance ---------------------------------------------
    spec = REQUIRED.get(name)
    if spec:
        if len(bones) < spec["min_bones"]:
            errors.append(f"only {len(bones)} bones, brief implies >= {spec['min_bones']}")
        for token, want in spec["expect"].items():
            got = sum(1 for n in names if token in n)
            if got < want:
                errors.append(f"expected >= {want} bones containing {token!r}, found {got}")
        for token in spec["must_contain"]:
            if not any(token in n for n in names):
                errors.append(f"missing a bone named for {token!r}")

    if verbose and not errors:
        used = sum(w * h for (_, _, w, h), _, _ in placed)
        print(f"  PASS {path.name}: {len(bones)} bones, {cube_count} cubes, "
              f"sheet {tw}x{th}, uv coverage {used * 100 // (tw * th)}%")

    return [f"{path.name}: {e}" for e in errors]


def main() -> int:
    verbose = "-v" in sys.argv

    if not GEO_DIR.exists():
        print(f"FAIL: no geo directory at {GEO_DIR}")
        return 1

    files = sorted(GEO_DIR.glob("*.geo.json"))
    if not files:
        print("FAIL: no .geo.json models found")
        return 1

    print(f"GATE 3: auditing {len(files)} geometry models")

    missing = [n for n in REQUIRED if not (GEO_DIR / f"{n}.geo.json").exists()]
    errors = [f"missing required model {n}.geo.json" for n in missing]
    for f in files:
        errors.extend(audit(f, verbose))

    if errors:
        print(f"\nFAILED with {len(errors)} violation(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"\nPASS: all {len(files)} models have valid bones, resolvable parents "
          f"and in-bounds non-overlapping UVs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

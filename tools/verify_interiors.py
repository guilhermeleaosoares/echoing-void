"""
GATE 5 - the interior rework did not touch a single exterior block.

PLAYER: "rework the interions (not the exteriors in any way) of the structures".

"In any way" is not a check a person can perform by looking at a screenshot, and
it is not a check the structure generator can perform either - gen_structures.py
knows whether a piece floats or whether its jigsaws are clear, and nothing about
what a piece looked like yesterday. So this compares each emitted template
against the version in git HEAD and refuses any change to a block that can be
seen from outside the building.

HOW "SEEN FROM OUTSIDE" IS DECIDED
---------------------------------
A block is exterior if an axis-aligned ray from it reaches the edge of the
template through nothing but air. That is a deliberate over-approximation - it
catches the walls, the roof, the deck, the window glass and frames, the
parapets, the gable infill and the eave courses in one rule, without any of them
having to be listed - and over-approximating is the right way round: a false
exterior costs one argument, a missed one ships a changed elevation.

The one adjustment is the archways. Every settlement archway is a 3x3 hole with
a jigsaw connector in the middle, and a hole lets rays straight into the room
behind it, which would classify half the ground floor as elevation. But an
archway is a socket: a bridge or a terrace plugs into it, and nothing is ever
seen through it from outside. So the connector cell and the eight cells around
it are treated as solid for ray purposes, which is what they effectively are
once the structure is assembled.

Exit code 0 = gate passed, 1 = an exterior block changed.

Run:  python tools/verify_interiors.py [-v]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import ev_nbt as nbt  # noqa: E402

NS = "echoing_void"
ROOT = TOOLS.parent
STRUCT_DIR = ROOT / "src" / "main" / "resources" / "data" / NS / "structure"

AIR = "minecraft:air"
VOID = "minecraft:structure_void"
JIGSAW = "minecraft:jigsaw"

# Only the pieces whose interiors this round reworked. A piece that was not
# touched has nothing to prove and would only add noise; adding one here is how
# a future round opts in.
REWORKED = [
    "outpost_of_the_tuners/forge_hall",
    "outpost_of_the_tuners/tuner_lodge",
    "outpost_of_the_tuners/signal_tower",
    "outpost_of_the_tuners/observatory",
    "outpost_of_the_tuners/sound_vault",
]


def git_show(rel: str) -> bytes | None:
    """The committed bytes of a file, or None if git does not have it."""
    proc = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(ROOT),
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def decode(path: Path) -> tuple[tuple[int, int, int], dict]:
    """A template as {(x, y, z): block name}, plus its size."""
    d = nbt.read_file(path)
    size = tuple(d["size"])
    pal = d["palette"]
    grid: dict[tuple[int, int, int], str] = {}
    for b in d["blocks"]:
        grid[tuple(b["pos"])] = pal[b["state"]]["Name"]
    return size, grid


def sealed_openings(grid: dict) -> set[tuple[int, int, int]]:
    """The 3x3 of cells around every jigsaw connector.

    These are the archway sockets. A bridge or a terrace is bolted into each of
    them, so nothing behind one is ever part of the elevation - but left open
    they would let a ray walk straight into the room.
    """
    out: set[tuple[int, int, int]] = set()
    for (x, y, z), name in grid.items():
        if name != JIGSAW:
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    out.add((x + dx, y + dy, z + dz))
    return out


def exterior_cells(size: tuple[int, int, int], grid: dict) -> set[tuple[int, int, int]]:
    """Every cell an axis-aligned ray can reach from outside through open air."""
    sx, sy, sz = size
    sealed = sealed_openings(grid)

    def open_cell(p) -> bool:
        return grid.get(p, AIR) in (AIR, VOID) and p not in sealed

    seen: set[tuple[int, int, int]] = set()
    for axis in range(3):
        for a in range(size[(axis + 1) % 3]):
            for b in range(size[(axis + 2) % 3]):
                for direction in (1, -1):
                    span = range(size[axis]) if direction == 1 \
                        else range(size[axis] - 1, -1, -1)
                    for i in span:
                        p = [0, 0, 0]
                        p[axis] = i
                        p[(axis + 1) % 3] = a
                        p[(axis + 2) % 3] = b
                        pos = (p[0], p[1], p[2])
                        seen.add(pos)
                        # The ray stops at the first thing it cannot see past -
                        # that block is exterior, everything behind it is not.
                        if not open_cell(pos):
                            break
    return seen


# A cell a player can stand IN. Lanterns and chains have no collision, and a
# jigsaw marker is swapped for its final_state (air) when the piece is placed.
# Doors, gates and trapdoors count too: they are obstacles a player opens, and a
# route that stops at a closed front door is not a route that is blocked.
PASSABLE_SUFFIX = ("_lantern", "chain", "jigsaw", "soul_lantern", "torch",
                   "_door", "_trapdoor", "_fence_gate")

# Where the new upper floors are, and the standing cell that proves you got
# there. A floor nobody can climb to is not a floor, and "I added a staircase"
# is exactly the kind of claim that looks right in the generator and is wrong in
# the world - one missing riser and the flight is a wall.
UPPER_FLOOR = {
    "outpost_of_the_tuners/forge_hall": [("the roof quarters", (8, 7, 8))],
    "outpost_of_the_tuners/tuner_lodge": [("the sleeping loft", (5, 7, 5))],
    "outpost_of_the_tuners/signal_tower": [("the crew room", (5, 7, 5)),
                                           ("the belfry", (4, 12, 5))],
    "outpost_of_the_tuners/observatory": [("the gallery study", (7, 7, 11))],
}


def passable(grid: dict, p) -> bool:
    name = grid.get(p, AIR)
    return name in (AIR, VOID) or name.endswith(PASSABLE_SUFFIX)


def walkable(grid: dict, p) -> bool:
    """Feet at p: something solid under them, and two clear blocks to stand in."""
    x, y, z = p
    return (not passable(grid, (x, y - 1, z))
            and passable(grid, p)
            and passable(grid, (x, y + 1, z)))


def reachable(size, grid: dict) -> set:
    """Every cell a player can walk to from the piece's own doorways.

    Movement is the vanilla envelope, minus jumping: one block horizontally,
    stepping up at most one block or falling at most three. Deliberately no
    jump - if a floor can only be reached by jumping, the staircase is wrong.
    """
    sx, sy, sz = size
    starts = []
    for (x, y, z), name in grid.items():
        if name != JIGSAW:
            continue
        # An archway connector stands two blocks above the floor it serves.
        foot = (x, y - 1, z)
        if walkable(grid, foot):
            starts.append(foot)

    seen = set(starts)
    queue = list(starts)
    while queue:
        x, y, z = queue.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (1, 0, -1, -2, -3):
                nxt = (x + dx, y + dy, z + dz)
                if nxt in seen or not (0 <= nxt[0] < sx and 0 <= nxt[1] < sy
                                       and 0 <= nxt[2] < sz):
                    continue
                # Stepping up needs headroom over the block being climbed.
                if dy > 0 and not passable(grid, (x, y + 2, z)):
                    continue
                if walkable(grid, nxt):
                    seen.add(nxt)
                    queue.append(nxt)
                    break
    return seen


def audit(piece: str, verbose: bool) -> list[str]:
    rel = f"src/main/resources/data/{NS}/structure/{piece}.nbt"
    new_path = ROOT / rel
    if not new_path.is_file():
        return [f"{piece}: emitted template is missing"]

    old_bytes = git_show(rel)
    if old_bytes is None:
        return [f"{piece}: no committed version to compare against "
                f"(is this a new piece? then it has no exterior to preserve)"]

    tmp = ROOT / "build" / "interior_check"
    tmp.mkdir(parents=True, exist_ok=True)
    old_path = tmp / f"{piece.replace('/', '_')}.nbt"
    old_path.write_bytes(old_bytes)

    old_size, old_grid = decode(old_path)
    new_size, new_grid = decode(new_path)

    errors: list[str] = []
    if old_size != new_size:
        return [f"{piece}: size changed {old_size} -> {new_size}, which is an "
                f"exterior change by definition"]

    outside = exterior_cells(old_size, old_grid)
    changed = {p for p in set(old_grid) | set(new_grid)
               if old_grid.get(p, AIR) != new_grid.get(p, AIR)}
    breaches = sorted(changed & outside)

    if verbose:
        print(f"  {piece:44} {len(changed):5d} changed  "
              f"{len(outside):5d} exterior cells  "
              f"{'BREACH' if breaches else 'clean'}")

    for p in breaches[:12]:
        errors.append(f"{piece}: exterior block at {p} changed "
                      f"{old_grid.get(p, AIR)} -> {new_grid.get(p, AIR)}")
    if len(breaches) > 12:
        errors.append(f"{piece}: ... and {len(breaches) - 12} more exterior changes")

    targets = UPPER_FLOOR.get(piece)
    if targets:
        walk = reachable(new_size, new_grid)
        for label, cell in targets:
            if cell in walk:
                if verbose:
                    print(f"      {label:22} at {cell}: reachable on foot")
            else:
                why = ("that cell is not somewhere a player can stand at all"
                       if not walkable(new_grid, cell)
                       else "no walk-and-step-up route leads there from a doorway")
                errors.append(f"{piece}: {label} at {cell} is cut off - {why}")
    return errors


def main() -> int:
    verbose = "-v" in sys.argv
    print(f"GATE 5: {len(REWORKED)} reworked pieces, checking every exterior "
          f"block against git HEAD")

    errors: list[str] = []
    for piece in REWORKED:
        errors.extend(audit(piece, verbose))

    if errors:
        print()
        print(f"FAILED with {len(errors)} exterior change(s):")
        for e in errors:
            print("  - " + e)
        return 1

    print()
    print("PASS: every change is behind the elevation - no wall, roof, deck, "
          "window or arch block moved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

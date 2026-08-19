"""
Every lantern in every generated template, and what actually holds it up.

PLAYER: "soul lanterns are still floating, we need to connect those with a chain
to the archways".

An earlier audit answered this question and got it wrong, so it is worth saying
exactly what that one did: it walked up through chains and accepted the first
block that was "solid". That let three whole classes of floater through.

  * A SLAB, STAIR, FENCE or WALL answers yes to a solid test but is not a
    ceiling. A lantern chained to the underside of a TOP slab has nothing over
    it at all - the top half of that cell is the slab, the bottom half, which is
    where the chain's head is, is air.
  * A lantern that STANDS on something was never examined, because the walk only
    ever went up. The archway lamps stand on a wall post, which is a 8x16x8
    stalk, so each of them is a cube balanced on a stick.
  * "Solid" was read off a name, and this mod's own lamp block, harmonic_lantern,
    is itself in that set - so a lamp resting on a lamp counted as anchored.

This one asks the question the player is actually asking: is there a genuine
FULL BLOCK carrying this lamp, and if the lamp hangs, is the run between them
chain the whole way? Anything else is reported with its voxel neighbourhood
dumped so the answer can be checked without opening the world.

Run:  python tools/audit_lanterns.py [-v]
Exit: 0 = every lantern anchored, 1 = at least one is not
"""

from __future__ import annotations

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
CHAIN = "minecraft:chain"
SOUL = "minecraft:soul_lantern"
LAMP = f"{NS}:harmonic_lantern"

# Shapes that are not a full cube, by id suffix. A lamp may not be anchored on
# any of them: none of them presents a whole face for it to be fixed to, which
# is the difference between a fitting and a thing balanced on a spike.
PARTIAL_SUFFIXES = (
    "_slab", "_stairs", "_wall", "_fence", "_fence_gate", "_trapdoor", "_door",
    "_pane", "_bars", "_sign", "_button", "_pressure_plate", "_carpet",
)
# Named partials with no useful suffix.
PARTIAL_NAMES = {
    CHAIN, SOUL, LAMP, "minecraft:lantern", "minecraft:chest", "minecraft:lectern",
    "minecraft:soul_campfire", "minecraft:campfire", "minecraft:composter",
    "minecraft:jigsaw", "minecraft:end_rod", "minecraft:torch",
    "minecraft:soul_torch", "minecraft:cauldron", "minecraft:brewing_stand",
    "minecraft:anvil", "minecraft:enchanting_table", "minecraft:flower_pot",
    f"{NS}:hushwater", f"{NS}:resonant_wheat", f"{NS}:chime_roots",
    f"{NS}:void_tubers", f"{NS}:echo_gourd_stem",
}


def is_full_block(name: str) -> bool:
    """A whole cube a fitting can be anchored to."""
    if name in (AIR, VOID) or name in PARTIAL_NAMES:
        return False
    return not name.endswith(PARTIAL_SUFFIXES)


def load(path: Path) -> tuple[dict, tuple[int, int, int]]:
    root = nbt.read_file(path)
    palette = [(e["Name"], e.get("Properties", {})) for e in root["palette"]]
    grid: dict[tuple[int, int, int], tuple[str, dict]] = {}
    for b in root["blocks"]:
        x, y, z = b["pos"]
        grid[(x, y, z)] = palette[b["state"]]
    sx, sy, sz = root["size"]
    return grid, (sx, sy, sz)


def name_at(grid: dict, pos: tuple[int, int, int]) -> str:
    return grid.get(pos, (AIR, {}))[0]


def neighbourhood(grid: dict, x: int, y: int, z: int, up: int = 6, down: int = 2) -> list[str]:
    """The column through a lamp, one line per y, so a claim can be checked."""
    out = []
    for dy in range(up, -down - 1, -1):
        n = name_at(grid, (x, y + dy, z))
        mark = " <-- lamp" if dy == 0 else ""
        out.append(f"        y{y + dy:+3d}  {n}{mark}")
    return out


def ceiling_ok(name: str, props: dict) -> bool:
    """Does this block present a whole face DOWNWARD for a lamp to hang off?

    A full cube does. So does a bottom slab and a bottom-half stair, both of
    which are a real ceiling plane at the floor of their own cell. A TOP slab
    does not - the half the chain's head is in is air - and neither does a fence
    post, a wall post or an upside-down stair. That distinction is the whole
    reason the previous audit reported two floaters where there were more: it
    tested "is this solid" and every one of these answers yes to that.
    """
    if is_full_block(name):
        return True
    if name.endswith("_slab"):
        return props.get("type") == "bottom"
    if name.endswith("_stairs"):
        return props.get("half") == "bottom"
    return False


def audit(path: Path, verbose: bool) -> list[str]:
    grid, size = load(path)
    faults = []

    for (x, y, z), (name, props) in sorted(grid.items()):
        if name not in (SOUL, LAMP):
            continue

        if name == SOUL and props.get("hanging") == "true":
            # Walk up through chain; anything else ends the run and has to be a
            # ceiling.
            run = 0
            cy = y + 1
            while name_at(grid, (x, cy, z)) == CHAIN:
                run += 1
                cy += 1
            anchor, anchor_props = grid.get((x, cy, z), (AIR, {}))
            if ceiling_ok(anchor, anchor_props):
                continue
            why = (f"hangs on {run} chain(s) up to {anchor} {anchor_props}"
                   if run else f"hangs directly under {anchor} {anchor_props}")
            faults.append((x, y, z, why))
        else:
            # A lamp that does not hang has to be HELD: a full block under it to
            # stand on, or a full block over it to be set into. A fence or wall
            # post alone is not holding it, it is a spike with a cube on the end,
            # which is exactly what every gate lamp used to be.
            below = name_at(grid, (x, y - 1, z))
            above = name_at(grid, (x, y + 1, z))
            if is_full_block(below) or is_full_block(above):
                continue
            faults.append((x, y, z, f"stands on {below}, carries {above}"))

    lines = []
    if faults:
        lines.append(f"{path.parent.name}/{path.stem}  ({len(faults)} unanchored)")
        for x, y, z, why in faults:
            lines.append(f"    ({x},{y},{z}) {why}")
            if verbose:
                lines.extend(neighbourhood(grid, x, y, z))
    return lines


def main() -> int:
    verbose = "-v" in sys.argv
    bad = 0
    total = 0
    for path in sorted(STRUCT_DIR.rglob("*.nbt")):
        grid, _ = load(path)
        total += sum(1 for v in grid.values() if v[0] in (SOUL, LAMP))
        lines = audit(path, verbose)
        if lines:
            bad += 1
            print("\n".join(lines))
    print(f"\n{total} lamps across {len(list(STRUCT_DIR.rglob('*.nbt')))} templates; "
          f"{bad} template(s) with unanchored lamps")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

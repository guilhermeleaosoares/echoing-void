"""Do the Aeroshell's two durability pools really wear and split independently?

PLAYER: "the knell aeroshell should have two different durability bars. 1 for
wings, 1 for the chestplate. they degrade seperately... if the chestplate
durability runs out, the user is left with just wings at the durability they were
already out. if the wings durability runs out, the user is left with just the
regular chestplate, with its durability the same."

WHAT IS BEING CHECKED
---------------------
The two splits, which are the part that cannot be inferred from the code
compiling, and the part a player will actually notice going wrong:

  1. an Aeroshell whose PLATE is spent becomes a plain elytra, and that elytra
     carries the wings' wear across rather than arriving factory-fresh
  2. an Aeroshell whose WINGS are spent becomes a plain Knell chestplate, and it
     carries the plate's wear across
  3. neither case destroys the item, which is what would happen if the pools were
     allowed to reach their maxima - vanilla deletes a stack whose damage reaches
     max, and the whole feature is that it splits instead

HOW, WITHOUT FLYING ANYTHING
----------------------------
A headless server has no player to glide, so the wear is written directly with
/item modify-style component edits rather than earned: `/item replace entity ...
with <item>[components]` sets both the vanilla damage value and the mod's
wing_damage counter, and then the armour stand is left to tick.

The split runs in Item.inventoryTick, which EntityEquipment.tick calls for every
worn piece on any LivingEntity - not only players - so an armour stand wearing the
Aeroshell exercises exactly the same path a player would.

Run:  python tools/test_aeroshell_pools.py [-v]
Exit: 0 = both splits happen, and both carry the other pool's wear across
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
X, Y, Z = 480, 200, 480

# KnellAeroshellItem.WING_MAX, and the plate's max comes from ArmorMaterial(59) with
# the chestplate multiplier - read back from the game rather than assumed.
WING_MAX = 432

NUM = re.compile(r"entity data:\s*(-?\d+)")


def cmd(server: Server, line: str, wait: float = 0.9) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            continue
    return "\n".join(out)


def worn(server: Server, path: str) -> str:
    """Read one field of whatever the stand is wearing on its chest."""
    return cmd(server, f"data get entity @e[type=minecraft:armor_stand,tag=rig,limit=1] "
                       f"equipment.chest{path}", 0.9)


def worn_id(server: Server) -> str:
    reply = worn(server, ".id")
    m = re.search(r'entity data:\s*"?([a-z_]+:[a-z_]+)"?', reply)
    return m.group(1) if m else "GONE"


def worn_int(server: Server, path: str) -> int | None:
    m = NUM.search(worn(server, path))
    return int(m.group(1)) if m else None


def dress(server: Server, damage: int, wing: int) -> None:
    """Put a fresh Aeroshell on the stand with both pools set exactly."""
    cmd(server, f"item replace entity @e[type=minecraft:armor_stand,tag=rig,limit=1] armor.chest "
                f'with {NS}:knell_aeroshell[minecraft:damage={damage},'
                f'{NS}:wing_damage={wing}]', 1.2)
    time.sleep(1.5)


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    verbose = "-v" in sys.argv
    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    failures: list[str] = []

    cmd(server, f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", 3.0)
    time.sleep(2)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "kill @e[tag=rig]", 0.8)
    cmd(server, f"fill {X - 2} {Y - 1} {Z - 2} {X + 2} {Y - 1} {Z + 2} minecraft:stone", 1.0)
    cmd(server, f"summon minecraft:armor_stand {X} {Y} {Z} "
                '{Tags:["rig"],NoGravity:1b,Invulnerable:1b}', 1.2)

    # The plate's maximum is the material's, not a number this test should guess.
    dress(server, 0, 0)
    if worn_id(server) != f"{NS}:knell_aeroshell":
        print(f"FAILED: could not dress the stand - it is wearing {worn_id(server)}")
        server.stop()
        return 1
    plate_max = worn_int(server, '.components."minecraft:max_damage"')
    if plate_max is None:
        # Not written into the stack unless overridden; fall back to the material's own
        # figure - ArmorMaterial(59) with vanilla's chestplate multiplier of 16.
        plate_max = 59 * 16
        print(f"  plate max not on the stack; using the material's {plate_max}")
    else:
        print(f"  plate max {plate_max}, wing max {WING_MAX}")

    # ---- 1: plate spent -> elytra, wings carried across -------------------
    print("  spending the plate with the wings half worn")
    dress(server, plate_max - 1, 200)
    time.sleep(2)
    became = worn_id(server)
    carried = worn_int(server, '.components."minecraft:damage"')
    print(f"    became {became}, damage {carried}")
    if became != "minecraft:elytra":
        failures.append(f"a spent plate left {became}, expected minecraft:elytra")
    elif carried != 200:
        failures.append(f"the elytra came out at damage {carried}, expected the wings' 200 - "
                        f"the wing wear was not carried across")

    # ---- 2: wings spent -> knell chestplate, plate carried across ---------
    print("  spending the wings with the plate half worn")
    dress(server, 300, WING_MAX - 1)
    time.sleep(2)
    became = worn_id(server)
    carried = worn_int(server, '.components."minecraft:damage"')
    print(f"    became {became}, damage {carried}")
    if became != f"{NS}:knell_chestplate":
        failures.append(f"spent wings left {became}, expected {NS}:knell_chestplate")
    elif carried != 300:
        failures.append(f"the chestplate came out at damage {carried}, expected the plate's 300 - "
                        f"the plate wear was not carried across")

    # ---- 3: a healthy Aeroshell is left alone -----------------------------
    print("  checking a healthy one is not split")
    dress(server, 100, 100)
    time.sleep(3)
    became = worn_id(server)
    print(f"    still {became}")
    if became != f"{NS}:knell_aeroshell":
        failures.append(f"an Aeroshell with both pools half-full was split anyway, into {became}")

    cmd(server, "kill @e[tag=rig]", 0.8)
    cmd(server, "forceload remove all", 1.0)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: each pool splits the Aeroshell on its own and carries the other pool's wear across")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

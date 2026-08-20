"""Can every tool, weapon and piece of armour in this mod actually be enchanted?

PLAYER: "make sure all enchantments work as normal in all the new armors tools
and weapons. all of them from both full sets and the greaves, rapier and lance".

WHY THIS TEST EXISTS
--------------------
Enchantability in 26.2 is decided by ITEM TAGS, not by the item's class or its
material's enchantment value. Every enchantment declares `supported_items`, and
those point at vanilla class tags, which chain like this (read off the 26.2 tag
files):

    enchantable/mining       -> #axes #pickaxes #shovels #hoes
    enchantable/melee_weapon -> #swords #spears
    enchantable/sharp_weapon -> #enchantable/melee_weapon #axes
    enchantable/weapon       -> #enchantable/sharp_weapon
    enchantable/durability   -> #swords #axes #pickaxes #shovels #hoes
                                + the four armour slot tags

An item outside those class tags takes NO enchantments at all - not from a
table, not from an anvil, not from /enchant - however good its material is.
That is exactly the state every tool and weapon in this mod was in: the four
armour slot tags were populated, and #swords / #pickaxes / #axes / #shovels /
#hoes did not exist at all.

HOW IT CHECKS
-------------
`/enchant` calls the same `Enchantment#canEnchant` the table and the anvil use,
so it is a true test of the tag chain rather than a proxy for it. An armour
stand holds the item (no player is needed on a headless server), and the
server's own reply is the result: "Applied enchantment" for a pass, anything
else - typically "cannot support that enchantment" - for a fail.

The stand is re-summoned per item so a leftover from a previous case can never
be the thing being measured; a stray entity answering the selector is the exact
class of contamination that made tools/test_hushwater.py report a false failure
earlier in this project.

Run:  python tools/test_enchantments.py [-v]
Exit: 0 = every case applied, 1 = at least one did not
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
X, Y, Z = 64, 200, 64

# slot -> items -> the enchantments that slot must accept.
#
# Silk Touch and Fortune are mutually exclusive, so they are applied to fresh
# stands rather than stacked; each case here is applied to its own clean item.
MELEE = ["minecraft:sharpness", "minecraft:looting", "minecraft:fire_aspect",
         "minecraft:unbreaking", "minecraft:mending"]
DIGGER = ["minecraft:efficiency", "minecraft:fortune", "minecraft:silk_touch",
          "minecraft:unbreaking", "minecraft:mending"]
ARMOUR = ["minecraft:protection", "minecraft:unbreaking", "minecraft:mending"]

CASES: list[tuple[str, str, list[str]]] = []

# --- weapons: both tier swords, plus the two the player named specifically ---
for it in ("harmonic_sword", "knell_sword", "void_glass_rapier", "sonic_lance"):
    CASES.append(("weapon.mainhand", it, MELEE))

# --- diggers: both full tool sets -------------------------------------------
for it in ("harmonic_pickaxe", "knell_pickaxe",
           "harmonic_shovel", "knell_shovel",
           "harmonic_hoe", "knell_hoe"):
    CASES.append(("weapon.mainhand", it, DIGGER))

# Axes are both: vanilla puts #axes in enchantable/sharp_weapon as well as in
# enchantable/mining, so an axe that cannot take Sharpness is a real failure.
for it in ("harmonic_axe", "knell_axe"):
    CASES.append(("weapon.mainhand", it, DIGGER + ["minecraft:sharpness"]))

# --- armour: both full sets, slot by slot -----------------------------------
for slot, pieces in (
    ("armor.head", ("resonance_helmet", "knell_helmet")),
    ("armor.chest", ("resonance_chestplate", "knell_chestplate")),
    ("armor.legs", ("resonance_leggings", "knell_leggings")),
    ("armor.feet", ("resonance_boots", "knell_boots")),
):
    for it in pieces:
        CASES.append((slot, it, ARMOUR))

# Boots carry the movement enchantments too, and those are the ones that catch
# a wrong slot tag: enchantable/foot_armor is fed ONLY by #minecraft:foot_armor,
# so a boot filed under leg_armor still takes Protection and Unbreaking (both
# reachable through other tags) while silently refusing every one of these.
BOOT_ONLY = ["minecraft:feather_falling", "minecraft:depth_strider",
             "minecraft:frost_walker", "minecraft:soul_speed"]
for it in ("resonance_boots", "knell_boots"):
    CASES.append(("armor.feet", it, BOOT_ONLY))

# The greaves, which the player named specifically. They are BOOTS - ModItems
# builds them with ArmorType.BOOTS and isWorn() reads EquipmentSlot.FEET - and
# they were tagged leg_armor, so they were exactly the case described above:
# a fall-damage boot that could not take Feather Falling.
CASES.append(("armor.feet", "aero_stride_greaves", ARMOUR + BOOT_ONLY))


def cmd(server: Server, line: str, wait: float = 1.2) -> str:
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

    cmd(server, f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", 3.0)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    # Any stand left behind by an interrupted earlier run would answer the
    # selector below and be measured instead of the fresh one.
    cmd(server, "kill @e[type=minecraft:armor_stand,tag=ench]", 1.0)

    failures: list[str] = []
    passed = 0

    for slot, item, enchants in CASES:
        for ench in enchants:
            cmd(server, "kill @e[type=minecraft:armor_stand,tag=ench]", 0.6)
            cmd(server, f'summon minecraft:armor_stand {X} {Y} {Z} '
                        f'{{Tags:["ench"],NoGravity:1b,Invulnerable:1b}}', 0.8)
            # ALWAYS the main hand, never the item's real slot. EnchantCommand
            # reads getMainHandItem() and nothing else, so armour parked in an
            # armour slot comes back "Armor Stand is not holding any item" -
            # which looks exactly like a refused enchantment and is not one.
            # canEnchant is a property of the ItemStack, not of where it sits,
            # so holding the piece is a faithful test of the tag chain.
            put = cmd(server, f"item replace entity @e[tag=ench,limit=1] weapon.mainhand "
                              f"with {NS}:{item}", 1.0)
            if "Replaced a slot" not in put:
                failures.append(f"{item}: could not be put in the main hand "
                                f"({put.strip()[-120:]})")
                continue
            reply = cmd(server, f"enchant @e[tag=ench,limit=1] {ench} 1", 1.2)
            if "Applied enchantment" in reply:
                passed += 1
                if verbose:
                    print(f"    ok   {item:22s} {ench}")
            else:
                tail = reply.strip().splitlines()[-1] if reply.strip() else "(no reply)"
                failures.append(f"{item} refused {ench} -> {tail[-140:]}")
                print(f"    FAIL {item:22s} {ench}")

    cmd(server, "kill @e[type=minecraft:armor_stand,tag=ench]", 1.0)
    cmd(server, "forceload remove all", 1.5)
    server.stop()

    print()
    print(f"  {passed} of {passed + len(failures)} enchantment applications succeeded")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: every tool, weapon and armour piece accepts its enchantments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Does Knell armour actually bank and hold a bigger charge than Resonance armour?

PLAYER: "fix knell armor please" - the four Knell plates were registered as plain
`Item`s rather than as ResonanceArmorItem, so the tier ABOVE the Resonance set
silently had FEWER abilities than the tier below it. No banking, no shockwave,
and nothing anywhere said so: the pieces looked the same, wore the same, and
just never charged.

WHAT IS BEING CHECKED
---------------------
Three claims, none of which compiling proves:

  1. a Knell chestplate banks at all. Before the fix ResonanceArmorItem.tierOf
     returned null for it and every bank call was a silent no-op, so any figure
     above zero here is the fix working.
  2. it banks past 60, which was the old hard cap baked into ModComponents.
     Knell holds 100.
  3. Resonance still stops at exactly 60 - the tiering must not have been bought
     by quietly buffing the tier below.

And, because the same commit fixed it, a fourth:

  4. the Knell SWORD banks 2.55 a hit, not 1.65. HarmonicSwordItem.attackDamage
     was `private static` and hardcoded RESONANT_BISMUTH's bonus, so the Knell
     sword - which subclasses it and is registered against KNELL for a real
     swing of 8.5 - banked as though it swung for 5.5. 35% short, and being
     private static, unoverridable.

HOW, WITHOUT A PLAYER
---------------------
A headless server has no player, and the armour's own damage-banking path is
gated on `victim instanceof Player`. The SWORD path is not: Mob.doHurtTarget
(Mob.java:1436) calls `weaponItem.hurtEnemy(livingTarget, this)` for any mob,
and HarmonicSwordItem.hurtEnemy banks into whatever resonating chestplate the
ATTACKER is wearing. So an armed, armoured zombie hitting something charges its
own chestplate, and that is fully readable from the server console.

Per-hit size is measured by POLLING the bank and recording every increase, then
taking the smallest one. That is exact regardless of how many times each zombie
managed to swing, which a fixed-duration comparison would not be.

NOT COVERED: the double-crouch release itself. It needs a real player pressing a
real key, and there is no player here. What this test does establish is that the
charge the release consumes now exists and is the right size.

Run:  python tools/test_knell_armor.py [-v]
Exit: 0 = Knell banks, holds 100, banks 2.55 a hit, and Resonance is unchanged
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
Y = 200

# Two independent pens, far enough apart that neither zombie wanders into the
# other's fight and banks off the wrong sword.
PENS = {
    "resonance": {"x": 96, "z": 96, "sword": "harmonic_sword", "chest": "resonance_chestplate"},
    "knell": {"x": 96, "z": 160, "sword": "knell_sword", "chest": "knell_chestplate"},
}

# ToolMaterial.createSwordAttributes builds ATTACK_DAMAGE as baseline + bonus, and
# HarmonicSwordItem.BANK_RATE is 0.30.
SWING = {"resonance": 3.0 + 2.5, "knell": 3.0 + 5.5}
BANK_RATE = 0.30
EXPECTED_PER_HIT = {tier: SWING[tier] * BANK_RATE for tier in SWING}

RESONANCE_CAP = 60.0
KNELL_CAP = 100.0
CAP = {"resonance": RESONANCE_CAP, "knell": KNELL_CAP}

STORED = re.compile(r"entity data:\s*(-?[0-9]+\.?[0-9]*)f?")


def cmd(server: Server, line: str, wait: float = 1.0) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.15))
        except Exception:
            continue
    return "\n".join(out)


def banked(server: Server, tier: str) -> float:
    """Read the banked charge straight off the zombie's worn chestplate.

    26.2 saves a mob's gear under `equipment` as a slot-name map (LivingEntity.java:779,
    EntityEquipment.CODEC), NOT the old ArmorItems/HandItems lists - so the path is
    equipment.chest, and the component sits under the stack's own `components`.

    The server answers `<name> has the following entity data: 4.95f`, or refuses with
    "Found no elements matching..." while the component is still absent, which is a
    perfectly ordinary zero rather than an error.
    """
    reply = cmd(server, f'data get entity @e[type=minecraft:zombie,tag={tier},limit=1] '
                        f'equipment.chest.components."{NS}:stored_damage"', 0.5)
    m = STORED.search(reply)
    return float(m.group(1)) if m else 0.0


def alive(server: Server) -> str:
    """Who is standing, what they are, and where - read BEFORE any health top-up.

    Reading after a top-up tells you only that the top-up ran. The interesting questions
    are whether the victim is still the entity that was summoned, whether it is losing
    health at all, and whether the two are still within swinging distance.
    """
    parts = []
    for tier in PENS:
        vic = cmd(server, f"data get entity @e[tag=victim_{tier},limit=1] Health", 0.5)
        m = STORED.search(vic)
        hp = m.group(1) if m else "GONE"
        kind = cmd(server, f"execute if entity @e[tag=victim_{tier},type=minecraft:villager]", 0.4)
        is_villager = "Count: 1" in kind
        pos = cmd(server, f"data get entity @e[tag=victim_{tier},limit=1] Pos[0]", 0.4)
        mv = STORED.search(pos)
        zpos = cmd(server, f"data get entity @e[type=minecraft:zombie,tag={tier},limit=1] Pos[0]",
                   0.4)
        mz = STORED.search(zpos)
        gap = ("?" if not (mv and mz)
               else f"{abs(float(mv.group(1)) - float(mz.group(1))):.1f}")
        parts.append(f"{tier[:3]}[hp={hp} villager={is_villager} dx={gap}]")
    return " ".join(parts)


def build_pen(server: Server, tier: str) -> None:
    pen = PENS[tier]
    x, z = pen["x"], pen["z"]

    # A 5x5 sealed cell. Floor and roof because an unhelmeted zombie burns in daylight and
    # a burning zombie breaks off to run for shade; walls because a panicking villager will
    # otherwise put distance between them, and the first walled run measured the Resonance
    # tier over 9 swings against Knell's 31 for no reason but a better escape.
    cmd(server, f"fill {x - 2} {Y - 1} {z - 2} {x + 2} {Y - 1} {z + 2} minecraft:stone", 1.2)
    cmd(server, f"fill {x - 2} {Y} {z - 2} {x + 2} {Y + 3} {z + 2} minecraft:air", 1.2)
    cmd(server, f"fill {x - 2} {Y + 4} {z - 2} {x + 2} {Y + 4} {z + 2} minecraft:stone", 1.2)
    # WALLS. The roof alone is not a pen - a villager with its AI intact panics and runs,
    # and the census caught one 16 blocks out, off the end of the platform entirely.
    for wall in (f"{x - 2} {Y} {z - 2} {x + 2} {Y + 3} {z - 2}",
                 f"{x - 2} {Y} {z + 2} {x + 2} {Y + 3} {z + 2}",
                 f"{x - 2} {Y} {z - 2} {x - 2} {Y + 3} {z + 2}",
                 f"{x + 2} {Y} {z - 2} {x + 2} {Y + 3} {z + 2}"):
        cmd(server, f"fill {wall} minecraft:stone", 0.8)

    # ORDER MATTERS, and getting it wrong cost two runs. Summoning the zombie first let it
    # kill a stock 20-HP villager within about three swings, before the health commands
    # below could land - and on normal difficulty a killed villager turns into a ZOMBIE
    # villager, which keeps its tags (so the census still saw a live "victim") but is not a
    # target any zombie will attack. The bank froze after three hits and looked exactly like
    # a mod bug. The victim is therefore raised to full health BEFORE anything can hit it.
    cmd(server, f"summon minecraft:villager {x + 1} {Y} {z} "
                f'{{Tags:["victim_{tier}"],PersistenceRequired:1b,Silent:1b}}', 1.5)
    for line in (f"attribute @e[tag=victim_{tier},limit=1] minecraft:max_health base set 1024",
                 f'data merge entity @e[tag=victim_{tier},limit=1] {{Health:1024f}}'):
        reply = cmd(server, line, 1.0)
        if any(bad in reply for bad in ("Unknown", "Incorrect", "Expected", "Invalid",
                                        "Unable", "No entity")):
            print(f"    !! setup command rejected: {line}")
            print(f"       {reply.strip()[-160:]}")

    # 1024 is the ceiling on minecraft:max_health - asking for more is silently clamped, so
    # this is as much padding as the game allows. It is topped back up during the run.
    kind = cmd(server, f"execute if entity @e[tag=victim_{tier},type=minecraft:villager]", 0.8)
    if "Count: 1" not in kind:
        raise SystemExit(f"SETUP FAILED: the {tier} victim is not a single live villager "
                         f"({kind.strip()[-120:]}). Something stale is wearing the tag, and "
                         f"every command below would land on it instead.")
    reply = cmd(server, f"data get entity @e[tag=victim_{tier},limit=1] Health", 0.8)
    m = STORED.search(reply)
    if not m or float(m.group(1)) < 1000.0:
        raise SystemExit(f"SETUP FAILED: the {tier} victim is not on full health "
                         f"({reply.strip()[-120:]}). Measuring past this would report a mod "
                         f"bug that is really a dead sparring partner.")

    # The attacker, last. Its own attack damage is irrelevant - the bank is computed from
    # the sword stack's ATTACK_DAMAGE modifier, which is the whole point of the sword fix.
    cmd(server, f"summon minecraft:zombie {x} {Y} {z} "
                f'{{Tags:["{tier}"],PersistenceRequired:1b,Silent:1b,'
                f'attributes:[{{id:"minecraft:follow_range",base:64}}],'
                f'equipment:{{mainhand:{{id:"{NS}:{pen["sword"]}",count:1}},'
                f'chest:{{id:"{NS}:{pen["chest"]}",count:1}}}}}}', 1.5)


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

    # Easy, not normal: on normal a killed villager has a 50% chance of becoming a
    # zombie villager, which inherits the tag and is not attackable by zombies. On easy
    # that conversion never happens, so the failure mode cannot recur.
    cmd(server, "difficulty easy", 0.6)
    cmd(server, "gamerule spawn_mobs false", 0.6)
    cmd(server, "gamerule doMobSpawning false", 0.6)
    cmd(server, "gamerule naturalRegeneration false", 0.6)
    cmd(server, "gamerule mobGriefing false", 0.6)
    cmd(server, "time set midnight", 0.6)
    # LOAD THE CHUNKS FIRST. @e only ever matches entities in LOADED chunks, so a cleanup
    # that runs before the forceload sweeps an empty world and leaves everything standing.
    # That single line of ordering cost four runs: the pens still held zombie villagers
    # from an earlier run, they survived the "kill", and every setup command afterwards
    # landed on them instead of the fresh victim - the server log said it plainly, "the
    # base value for attribute Max Health for entity Zombie Villager set to 1024", while
    # the actual villager stayed on its stock 20 HP and died in three swings.
    cmd(server, "forceload add 32 32 224 224", 4.0)
    time.sleep(4)

    # Clear by TAG, not by type. A villager killed by a zombie can come back as a ZOMBIE
    # villager, which carries the tags across but changes the type, so `kill @e[type=villager]`
    # walks straight past it.
    for tag in list(PENS) + [f"victim_{t}" for t in PENS]:
        cmd(server, f"kill @e[tag={tag}]", 0.8)
    for kind in ("zombie", "villager", "zombie_villager"):
        cmd(server, f"kill @e[type=minecraft:{kind}]", 0.8)
    time.sleep(2)

    for tier in PENS:
        build_pen(server, tier)
        print(f"  {tier} pen built: {PENS[tier]['sword']} + {PENS[tier]['chest']}")

    # Poll fast enough to catch single swings. A mob's attack interval is about a
    # second, so every increase seen here is normally one hit; the SMALLEST increase
    # is one hit even when two land between polls.
    print("  fighting, polling the banks")
    deltas: dict[str, list[float]] = {tier: [] for tier in PENS}
    peak: dict[str, float] = {tier: 0.0 for tier in PENS}
    last: dict[str, float] = {tier: 0.0 for tier in PENS}

    end = time.time() + 300
    next_report = time.time() + 20
    while time.time() < end:
        for tier in PENS:
            now = banked(server, tier)
            # The hit that FILLS the bank is clipped by the cap - the first run measured
            # Knell at 0.55 a hit for exactly that reason (100 - 39 x 2.55). A clipped
            # increment says nothing about what a swing is worth, so it is not a sample.
            if now > last[tier] + 1.0e-4 and now < CAP[tier] - 1.0e-4:
                deltas[tier].append(round(now - last[tier], 4))
            last[tier] = now
            peak[tier] = max(peak[tier], now)

        if time.time() >= next_report:
            next_report = time.time() + 20
            census = alive(server)
            # Top up AFTER reading, never before - reading a freshly-healed victim only
            # proves the heal ran, which is how three runs reported "victim on full health"
            # while the fight had in fact stopped.
            for t in PENS:
                cmd(server, f"data merge entity @e[tag=victim_{t},limit=1] {{Health:1024f}}", 0.3)
            print(f"    {int(end - time.time()):3d}s left  "
                  + "  ".join(f"{t}={peak[t]:.2f}" for t in PENS)
                  + "   " + census)
        if peak["knell"] >= KNELL_CAP - 0.01 and peak["resonance"] >= RESONANCE_CAP - 0.01:
            print("  both banks reached their caps")
            break

    for tier in PENS:
        per_hit = min(deltas[tier]) if deltas[tier] else 0.0
        print(f"  {tier:10s} peak {peak[tier]:6.2f}   hits seen {len(deltas[tier]):3d}   "
              f"smallest increment {per_hit:.3f}   (expected {EXPECTED_PER_HIT[tier]:.3f})")

    cmd(server, "kill @e[type=minecraft:zombie]", 1.0)
    cmd(server, "kill @e[type=minecraft:villager]", 1.0)
    cmd(server, "forceload remove all", 1.5)
    server.stop()

    # ---- 1: the Knell chestplate banks at all ---------------------------
    if peak["knell"] <= 0.0:
        failures.append("a Knell chestplate banked nothing - it is still not a resonating piece, "
                        "which is the original bug")

    # ---- 2: it holds more than the old hard cap -------------------------
    if peak["knell"] <= RESONANCE_CAP:
        failures.append(f"the Knell bank peaked at {peak['knell']:.2f}, no better than the "
                        f"Resonance cap of {RESONANCE_CAP} - the capacity is not tiered")
    elif abs(peak["knell"] - KNELL_CAP) > 0.01:
        failures.append(f"the Knell bank peaked at {peak['knell']:.2f}, expected exactly "
                        f"{KNELL_CAP}")

    # ---- 3: Resonance is untouched --------------------------------------
    if abs(peak["resonance"] - RESONANCE_CAP) > 0.01:
        failures.append(f"the Resonance bank peaked at {peak['resonance']:.2f}, expected exactly "
                        f"{RESONANCE_CAP} - the tier below has been changed by accident")

    # ---- 4: the Knell sword banks off its own swing ---------------------
    for tier in PENS:
        if not deltas[tier]:
            failures.append(f"never saw the {tier} bank move at all")
            continue
        per_hit = min(deltas[tier])
        if abs(per_hit - EXPECTED_PER_HIT[tier]) > 0.02:
            failures.append(f"the {tier} sword banks {per_hit:.3f} a hit, expected "
                            f"{EXPECTED_PER_HIT[tier]:.3f} ({SWING[tier]} swing x {BANK_RATE})")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"PASS: Knell banks {min(deltas['knell']):.2f} a hit up to {KNELL_CAP:.0f}; "
          f"Resonance still {min(deltas['resonance']):.2f} up to {RESONANCE_CAP:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

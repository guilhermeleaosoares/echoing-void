"""Does a struck Tuner Trader actually fight back, with magic, at 75% of a Shade's bolt?

PLAYER: "the tuner trader mobs should be neutral, not passive, like piglings.
they have the trade gui, but when attacked they turn hostile and will attack you
back, they can attack with magic like the tuner shader mob, similar attacks to
those, though dealing 75% the damage of what a tuner shader would."

WHAT IS BEING CHECKED
---------------------
Three separate claims, and compiling proves none of them:

  1. an unprovoked Tuner does NOT attack - it is neutral, not hostile
  2. a Tuner that has been hurt DOES retaliate, and the retaliation reaches a
     target it never touches, which is what makes it magic rather than melee
  3. the bolt lands for 3.75 rather than the Shade's 5.0

The victim is a NoAI pig standing 9 blocks away, and the choice is not
incidental: the first version of this test used an armour stand and reported
that the trader never retaliated. That was the TEST being wrong.
ArmorStand.attackable() returns false, so HurtByTargetGoal can never acquire
one as a target no matter how angry the mob is - the retaliation had nowhere to
go. A pig is attackable, passive, and will not fight back or wander off.

Nine blocks matters: ResonanceBoltGoal will not cast closer than 6 (it gives ground
instead) and gives up past 15, so a target inside that band is the only way the
cast path is exercised at all. A test run at melee range would show the trader
doing nothing and would look exactly like a failure.

Damage is attributed with `/damage ... by <entity>`, so the trader's
HurtByTargetGoal has a real attacker to acquire rather than a nameless source.

Run:  python tools/test_trader_neutral.py [-v]
Exit: 0 = neutral until hit, then casts for the right damage
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
X, Y, Z = 96, 200, 96
RANGE = 9                       # inside the goal's 6..15 casting band
HEALTH = re.compile(r"entity data:\s*(-?[0-9.]+)f?")

# The Shade's bolt is 5.0 and the Tuner's is meant to be 75% of it.
SHADE_BOLT = 5.0
EXPECTED = SHADE_BOLT * 0.75    # 3.75


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


def victim_health(server: Server) -> float | None:
    reply = cmd(server, "data get entity @e[type=minecraft:pig,tag=victim,limit=1] Health", 1.4)
    m = HEALTH.search(reply)
    return float(m.group(1)) if m else None


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

    cmd(server, f"forceload add {X - 32} {Z - 32} {X + 32} {Z + 32}", 4.0)
    cmd(server, "gamerule spawn_mobs false", 0.5)
    cmd(server, "gamerule naturalRegeneration false", 0.5)
    # Anything left from an interrupted run would answer the selectors below.
    cmd(server, f"kill @e[type={NS}:tuner_trader]", 1.0)
    cmd(server, "kill @e[type=minecraft:pig,tag=victim]", 1.0)
    time.sleep(2)

    # A floor, so neither party falls out of the world.
    cmd(server, f"fill {X - 14} {Y - 1} {Z - 14} {X + 14} {Y - 1} {Z + 14} minecraft:stone", 2.0)
    cmd(server, f"fill {X - 14} {Y} {Z - 14} {X + 14} {Y + 4} {Z + 14} minecraft:air", 2.0)

    cmd(server, f"summon {NS}:tuner_trader {X} {Y} {Z} "
                '{PersistenceRequired:1b,Silent:1b}', 1.5)
    cmd(server, f"summon minecraft:pig {X} {Y} {Z + RANGE} "
                '{Tags:["victim"],NoAI:1b,PersistenceRequired:1b,Silent:1b}', 1.5)

    baseline = victim_health(server)
    if baseline is None:
        print("FAILED: could not read the victim's health")
        server.stop()
        return 1
    print(f"  victim at {baseline} health, {RANGE} blocks from the trader")

    # ---- 1: unprovoked, it must do nothing ------------------------------
    print("  watching an unprovoked trader for 15s")
    time.sleep(15)
    idle = victim_health(server)
    if idle is not None and idle < baseline:
        failures.append(f"an unprovoked trader attacked: victim went {baseline} -> {idle}. "
                        f"It is hostile, not neutral.")
    else:
        print("  unprovoked trader did nothing - neutral confirmed")

    # ---- 2 & 3: hit it, and see what comes back -------------------------
    print("  striking the trader, attributed to the victim")
    cmd(server, f"damage @e[type={NS}:tuner_trader,limit=1] 2 minecraft:magic "
                "by @e[type=minecraft:pig,tag=victim,limit=1]", 1.5)

    before = victim_health(server)
    print(f"  victim at {before} before retaliation; waiting up to 40s for a bolt")

    landed = None
    end = time.time() + 40
    while time.time() < end:
        time.sleep(3)
        now = victim_health(server)
        if now is None:
            failures.append("the victim disappeared mid-test")
            break
        if now < before:
            landed = before - now
            print(f"  bolt landed for {landed}")
            break

    if landed is None and not failures:
        failures.append("the trader never retaliated within 40s - it is still passive, or the "
                        "bolt goal never fired")
    elif landed is not None:
        # A pig has no armour, so the figure read here is the raw bolt damage.
        if abs(landed - EXPECTED) > 0.51:
            failures.append(f"bolt dealt {landed}, expected about {EXPECTED} "
                            f"(75% of the Shade's {SHADE_BOLT})")
        else:
            print(f"  damage {landed} matches the intended {EXPECTED}")

    cmd(server, f"kill @e[type={NS}:tuner_trader]", 1.0)
    cmd(server, "kill @e[type=minecraft:pig,tag=victim]", 1.0)
    cmd(server, "forceload remove all", 1.5)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: the Tuner is neutral until struck, then answers with magic at 75% of a Shade's bolt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

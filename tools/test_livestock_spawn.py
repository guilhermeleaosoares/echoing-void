"""Do the Drone Auroch and Thrum Boar actually spawn naturally in the Hollow Horizon?

PLAYER: "do the new passive mobs spawn naturally? where and with what
frequency" and then, having gone and looked: "none of the passive mobs are
spawning naturally."

They were right, and the reason is worth writing down because nothing about it
is visible from the code that looks wrong:

  * the biome files listed them under `spawners.creature` with sane weights
  * SpawnPlacementRegisterEvent registered them
  * and they still could not spawn, because the placement predicate was
    Animal::checkAnimalSpawnRules, which ends in

        level.getBlockState(pos.below()).is(BlockTags.ANIMALS_SPAWNABLE_ON)

    and vanilla's animals_spawnable_on contains exactly ONE entry:
    minecraft:grass_block. There is not one grass block in the Hollow Horizon.

The second half of that same method is `getRawBrightness(pos, 0) > 8`, which a
deliberately dim dimension (ambient_light 0.14, end-like fixed sky) also fails,
so both halves had to be dealt with: the tag is extended in gen_tags.py, and the
light clause is dropped by a custom predicate in ModNewEntities.

HOW THIS CHECKS IT
------------------
MobCategory.CREATURE is overwhelmingly a WORLD-GENERATION spawn: vanilla places
its animals when a chunk is first generated and only rarely afterwards. So this
generates fresh Hollow Horizon chunks and counts what is standing in them,
rather than waiting on the spawn cycle in already-generated terrain - a test
that forceloaded old chunks and waited would report zero even after the fix.

Counting is `/execute in <dim> run execute if entity @e[type=...]`, which
reports "Test passed. Count: N".

Run:  python tools/test_livestock_spawn.py [-v]
Exit: 0 = both species present in freshly generated terrain
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

ROOT = TOOLS.parent
WORLD = "livestock_probe"

NS = "echoing_void"
HH = f"{NS}:the_hollow_horizon"

# 15x15 chunks: under /forceload's 256-chunk ceiling (that limit silently
# refuses the whole command, which cost this project an afternoon once) and a
# big enough sample that zero is meaningful rather than unlucky.
PATCH = 15
CENTRE = [0, 0]      # filled in once the plains are located
COUNT = re.compile(r"Count:\s*(\d+)")


def cmd(server: Server, line: str, wait: float = 1.5) -> str:
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


def census(server: Server, entity: str) -> int:
    """Count one species inside the generated patch.

    Anchored with `positioned` and a `distance` bound rather than a bare
    `execute in <dim> run execute if entity @e[...]`. That bare form does NOT
    reliably resolve the selector against the dimension the `execute in` names -
    the portal test in this project hit the same trap and reported an entity
    present in two dimensions at once. A positional query cannot do that.
    """
    reply = cmd(server, f"execute in {HH} positioned {CENTRE[0]} 128 {CENTRE[1]} run execute if entity "
                        f"@e[type={NS}:{entity},distance=..400]", 1.6)
    m = COUNT.search(reply)
    return int(m.group(1)) if m else 0


def total_entities(server: Server) -> str:
    """Everything alive in the patch, so a zero census can be told apart from an empty world."""
    reply = cmd(server, f"execute in {HH} positioned {CENTRE[0]} 128 {CENTRE[1]} run execute if entity "
                        "@e[distance=..400]", 1.6)
    m = COUNT.search(reply)
    return m.group(1) if m else "unreadable"


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    # A FRESH world, every run, and this is the crux of the whole test.
    #
    # MobCategory.CREATURE is placed when a chunk is FIRST generated and
    # essentially never again. The shared test world persists between runs, so
    # the second run of this test re-used terrain the first run had already
    # generated, no chunk generation happened, and it reported zero animals no
    # matter what the mod did. Three runs were spent chasing that as a mod bug.
    import re as _re
    import shutil
    world_dir = ROOT / "run" / WORLD
    if world_dir.exists():
        shutil.rmtree(world_dir, ignore_errors=True)
    props = ROOT / "run" / "server.properties"
    text = props.read_text(encoding="utf-8") if props.exists() else ""
    text = _re.sub(r"^level-name=.*$", f"level-name={WORLD}", text, flags=_re.M)
    props.write_text(text, encoding="utf-8")
    print(f"  fresh world: run/{WORLD}")

    verbose = "-v" in sys.argv
    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    # WHERE matters. Only the Resonant Plains and the Chalk Reaches carry herds -
    # the Shattered Octaves deliberately has none - so a patch generated at
    # whatever biome happens to sit at 0,0 can legitimately contain zero animals
    # and prove nothing. Find the plains first and generate there.
    reply = cmd(server, f"execute in {HH} run locate biome {NS}:resonant_plains", 20.0)
    found = re.search(r"(-?\d+),\s*(?:~|-?\d+),\s*(-?\d+)", reply)
    if not found:
        print("FAILED: could not locate the Resonant Plains")
        print("  " + reply.strip()[-200:])
        server.stop()
        return 1
    cx, cz = int(found.group(1)), int(found.group(2))
    print(f"  Resonant Plains at x={cx} z={cz}")
    CENTRE[0], CENTRE[1] = cx, cz

    # Gamerules live in level.dat and PERSIST between runs. Several other tests in
    # this directory turn spawning off to keep their own measurements clean, and
    # they all share this world - so a livestock test that does not turn it back
    # on measures whatever the last test left behind. This is not hypothetical:
    # the first run of this test found 213 entities and not one mob among them.
    cmd(server, "gamerule spawn_mobs true", 1.0)
    cmd(server, "gamerule doMobSpawning true", 1.0)

    half = PATCH * 16 // 2
    print(f"  generating a {PATCH}x{PATCH} chunk patch there")
    cmd(server, f"execute in {HH} run forceload add {cx - half} {cz - half} "
                f"{cx + half - 1} {cz + half - 1}", 5.0)

    # Generation is asynchronous. Poll a block in the far corner until the
    # server stops saying "not loaded", rather than sleeping a fixed guess.
    ready = False
    end = time.time() + 420
    while time.time() < end:
        reply = cmd(server, f"execute in {HH} run setblock {cx + half - 8} 200 "
                            f"{cz + half - 8} minecraft:air replace", 2.0)
        if "not loaded" not in reply.lower():
            ready = True
            break
        time.sleep(5)
    if not ready:
        print("FAILED: the patch never finished generating")
        server.stop()
        return 1
    print("  patch generated")
    time.sleep(5)

    aurochs = census(server, "drone_auroch")
    boars = census(server, "thrum_boar")
    # NOT a control any more. The Chime Mote is MobCategory.AMBIENT, and ambient
    # spawning runs off the player-driven spawn cycle - with nobody logged in it
    # is always zero, which says nothing either way. CREATURE is different: it is
    # placed during chunk generation, which is exactly why this test generates
    # fresh terrain instead of waiting.
    motes = census(server, "chime_mote")

    print(f"  drone_auroch : {aurochs}")
    print(f"  thrum_boar   : {boars}")
    print(f"  chime_mote   : {motes}   (ambient - expected 0 with no player online)")
    print(f"  all entities : {total_entities(server)}   (is anything alive at all?)")

    cmd(server, f"execute in {HH} run forceload remove all", 2.0)
    server.stop()

    failures = []
    if aurochs == 0:
        failures.append("no Drone Aurochs in freshly generated terrain")
    if boars == 0:
        failures.append("no Thrum Boars in freshly generated terrain")


    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"PASS: {aurochs} aurochs and {boars} boars spawned naturally in "
          f"{PATCH * PATCH} freshly generated chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

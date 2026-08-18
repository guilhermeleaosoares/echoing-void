"""
Registry smoke test.

Boots a headless server and asks the running game - not the source tree - which
ids actually exist. Written after a whole round of work compiled green while
three DeferredRegisters were never class-loaded, so every id in them was absent
at runtime. A source scan cannot see that; only the server can.

Each check is a command whose reply distinguishes "known" from "unknown". For
items and blocks that is /give and /setblock against a fake player: an unknown
id fails at parse time with "Unknown item", while a known id fails later with
"No player was found". The two are different strings, so the reply proves
whether the registry entry is there without needing a real player.

Run:  python tools/diagnose_registry.py [-v]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"

# The three creatures whose registry never loaded last round, plus their eggs.
ENTITIES = ["chime_mote", "tuner_shade", "strata_burrower",
            "echo_weaver", "strata_golem", "resonance_wraith",
            "tuner_trader", "tuners_protector"]

ITEMS = [
    # spawn eggs - these resolve their EntityType eagerly, so a missing entity
    # takes the item down with it and this catches both at once
    "chime_mote_spawn_egg", "tuner_shade_spawn_egg", "strata_burrower_spawn_egg",
    "tuner_trader_spawn_egg", "tuners_protector_spawn_egg",
    # the Knell tier
    "knell_ingot", "knell_sword", "knell_helmet", "knell_chestplate",
    "knell_leggings", "knell_boots", "knell_template", "raw_knell",
    # the Resonance tier the Knell smithing recipes upgrade from - every one of
    # these is the base of a smithing_transform, so a missing id here silently
    # removes a Knell recipe rather than erroring
    "harmonic_sword", "harmonic_axe", "harmonic_shovel", "harmonic_hoe",
    "harmonic_pickaxe",
    "resonance_helmet", "resonance_chestplate",
    "resonance_leggings", "resonance_boots",
]

BLOCKS = [
    # one cut from each wood family, which is what the missing <wood>_logs tags
    # took down last time
    "echo_ash_planks", "echo_ash_slab", "echo_ash_stairs", "echo_ash_fence",
    "echo_ash_fence_gate", "echo_ash_door", "echo_ash_trapdoor", "echo_ash_log",
    "amber_bough_planks", "amber_bough_door", "amber_bough_log",
    "petrified_tuning_planks", "humming_planks",
    # one cut from each stone family
    "raw_phonolite_slab", "polished_phonolite_stairs", "phonolite_brick_wall",
    "resonant_chalk_slab", "chalk_brick_stairs", "echo_slate_wall",
    "amber_strata_slab",
    # the effect blocks and the new tier's station
    "null_iron_jukebox", "inversion_anvil", "knell_integrator",
    "knell_ore", "knell_block",
    "tuners_mask", "acoustic_lock_box",
    # host-matched ores
    "deepslate_null_iron_ore", "phonolite_null_iron_ore",
    "phonolite_resonant_bismuth_ore", "ashen_resonance_leaves",
]

# Tags whose absence is silent but fatal downstream.
TAGS = [f"{w}_logs" for w in ("echo_ash", "amber_bough", "petrified_tuning", "humming")]


def drain(server: Server, seconds: float = 1.5) -> list[str]:
    """Collect whatever the server has said since the last drain."""
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return out


def probe(server: Server, label: str, commands: list[tuple[str, str]]) -> list[str]:
    """Run each command and return the ids whose reply says the id is unknown.

    `commands` is (id, command). An id is judged missing only on an explicit
    "Unknown ..." / "Unable to parse" reply - never on silence, because silence
    here means the command was accepted.
    """
    missing: list[str] = []
    drain(server, 0.5)
    for ident, cmd in commands:
        server.send(cmd)
        reply = " ".join(drain(server, 0.35))
        low = reply.lower()
        if "unknown" in low or "unable to parse" in low or "did not match" in low:
            missing.append(ident)
    print(f"  {label}: {len(commands) - len(missing)}/{len(commands)} present")
    for m in missing:
        print(f"      MISSING {m}")
    return missing


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        for line in server.transcript[-40:]:
            print("  " + line)
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    missing: list[str] = []

    # A known entity id parses and then fails on the position/selector; an
    # unknown one fails at the id itself.
    missing += probe(server, "entities", [
        (e, f"summon {NS}:{e} 0 -64 0") for e in ENTITIES])

    missing += probe(server, "items", [
        (i, f"give @p {NS}:{i}") for i in ITEMS])

    missing += probe(server, "blocks", [
        (b, f"setblock 0 -64 0 {NS}:{b}") for b in BLOCKS])

    missing += probe(server, "tags", [
        (t, f"execute if block 0 -64 0 #{NS}:{t}") for t in TAGS])

    # The startup log is the other half: a tag that failed to load never errors
    # at a command, it just silently holds nothing.
    joined = "\n".join(server.transcript)
    # A recipe naming an unregistered item is not an error at any command - the
    # game drops it at datapack load and the player simply never sees it. That
    # is exactly how the Knell smithing recipes could have gone missing while
    # every id they name still resolved, so the log is the only witness.
    for phrase in ("Unknown registry key", "Couldn't load tag", "Missing tag",
                   "Failed to load registries", "Unregistered",
                   "Parsing error loading recipe",
                   "Failed to parse", "Couldn't parse data file"):
        n = joined.count(phrase)
        print(f"  log '{phrase}': {n}")
        if n:
            missing.append(f"log:{phrase}")

    server.stop()

    if missing:
        print(f"\nFAILED: {len(missing)} registry problem(s)")
        return 1
    print("\nPASS: every probed id resolves in the running game")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

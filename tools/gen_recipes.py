"""
The Echoing Void - recipe generator.

Schema taken from real 26.2 vanilla recipes in
C:\\Projects\\mcref-26.2\\clientjar\\data\\minecraft\\recipe\\ - note that 26.2
writes ingredients as bare ids ("ingredient": "minecraft:raw_iron") and results
as {"id": ...}, and that recipe files live in data/<ns>/recipe/ (singular).

Run:  python tools/gen_recipes.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "main" / "resources" / "data" / NS / "recipe"

written: list[str] = []


def write(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(name)


def shaped(name: str, pattern: list[str], key: dict[str, str], result: str,
           count: int = 1, category: str = "misc") -> None:
    data: dict = {
        "type": "minecraft:crafting_shaped",
        "category": category,
        "key": key,
        "pattern": pattern,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    write(name, data)


def shapeless(name: str, ingredients: list[str], result: str, count: int = 1,
              category: str = "misc") -> None:
    data: dict = {
        "type": "minecraft:crafting_shapeless",
        "category": category,
        "ingredients": ingredients,
        "result": {"id": result},
    }
    if count > 1:
        data["result"]["count"] = count
    write(name, data)


def cooking(name: str, kind: str, ingredient: str, result: str,
            xp: float, time: int, group: str) -> None:
    write(name, {
        "type": f"minecraft:{kind}",
        "category": "misc",
        "cookingtime": time,
        "experience": xp,
        "group": group,
        "ingredient": ingredient,
        "result": {"id": result},
    })


def main() -> int:
    shard = f"{NS}:resonance_shard"
    raw_null = f"{NS}:raw_null_iron"
    ingot = f"{NS}:null_iron_ingot"
    glass_shard = f"{NS}:void_glass_shard"
    stick = "minecraft:stick"

    # ---- smelting: raw Null-Iron -> ingot (slow and hot; it resists) --------
    cooking("null_iron_ingot_from_smelting", "smelting", raw_null, ingot, 1.2, 400, "null_iron_ingot")
    cooking("null_iron_ingot_from_blasting", "blasting", raw_null, ingot, 1.2, 200, "null_iron_ingot")

    # ---- storage blocks -----------------------------------------------------
    shaped("null_iron_block", ["###", "###", "###"], {"#": ingot},
           f"{NS}:null_iron_block", category="building")
    shapeless("null_iron_ingot_from_block", [f"{NS}:null_iron_block"], ingot, 9)

    # ---- stone set ----------------------------------------------------------
    shaped("phonolite_bricks", ["##", "##"], {"#": f"{NS}:raw_phonolite"},
           f"{NS}:phonolite_bricks", count=4, category="building")
    shaped("void_glass", ["##", "##"], {"#": glass_shard},
           f"{NS}:void_glass", count=2, category="building")

    # ---- the Tuner's Mask: the key to building a guardian -------------------
    # PLAYER: "make sure the tuners mask can be crafted and/or obtained naturally."
    #
    # A block of null-iron with the tuners' sigil struck into it and two shards
    # set as the eyes. Deliberately the BLOCK rather than nine loose ingots, so
    # the mask costs exactly what one segment of the body it completes costs -
    # a guardian is seven blocks of null-iron all in, and the head is one of
    # them. Shapeless because there is no arrangement worth memorising.
    shapeless("tuners_mask", [f"{NS}:null_iron_block", shard, shard],
              f"{NS}:tuners_mask", category="building")

    # ---- the tuning fork: the key to the Hollow Horizon ---------------------
    shaped("tuning_fork", ["S S", " S ", " I "], {"S": shard, "I": "minecraft:iron_ingot"},
           f"{NS}:tuning_fork", category="equipment")

    # ---- tools and weapons --------------------------------------------------
    shaped("harmonic_pickaxe", ["SSS", " # ", " # "], {"S": shard, "#": stick},
           f"{NS}:harmonic_pickaxe", category="equipment")
    shaped("sonic_lance", ["  N", " # ", "#  "], {"N": ingot, "#": stick},
           f"{NS}:sonic_lance", category="equipment")
    shaped("void_glass_rapier", ["  G", " G ", "S  "], {"G": glass_shard, "S": shard},
           f"{NS}:void_glass_rapier", category="equipment")

    # The Resonance toolset. Vanilla patterns exactly, in shards on sticks, so a
    # player who has ever made an iron tool already knows these. They are cheap
    # on purpose: the tier is now the mandatory step to Knell, and gating the
    # step behind a fiddly recipe would only tax the path rather than guard it.
    # The pickaxe slot is deliberately absent - the Harmonic Pickaxe is already
    # resonant bismuth and fills it.
    shaped("harmonic_sword", [" S ", " S ", " # "], {"S": shard, "#": stick},
           f"{NS}:harmonic_sword", category="equipment")
    shaped("harmonic_axe", ["SS ", "S# ", " # "], {"S": shard, "#": stick},
           f"{NS}:harmonic_axe", category="equipment")
    shaped("harmonic_shovel", [" S ", " # ", " # "], {"S": shard, "#": stick},
           f"{NS}:harmonic_shovel", category="equipment")
    shaped("harmonic_hoe", ["SS ", " # ", " # "], {"S": shard, "#": stick},
           f"{NS}:harmonic_hoe", category="equipment")

    # ---- armour -------------------------------------------------------------
    shaped("resonance_helmet", ["NSN", "N N"], {"N": ingot, "S": shard},
           f"{NS}:resonance_helmet", category="equipment")
    shaped("resonance_chestplate", ["N N", "NSN", "NNN"], {"N": ingot, "S": shard},
           f"{NS}:resonance_chestplate", category="equipment")
    shaped("resonance_leggings", ["NSN", "N N", "N N"], {"N": ingot, "S": shard},
           f"{NS}:resonance_leggings", category="equipment")
    shaped("resonance_boots", ["N N", "S S"], {"N": ingot, "S": shard},
           f"{NS}:resonance_boots", category="equipment")
    shaped("aero_stride_greaves", ["G G", "S S"], {"G": glass_shard, "S": shard},
           f"{NS}:aero_stride_greaves", category="equipment")

    # ---- the frequency machines ---------------------------------------------
    shaped("frequency_siphon", ["CSC", "SRS", "CSC"],
           {"C": "minecraft:copper_ingot", "S": shard, "R": "minecraft:redstone"},
           f"{NS}:frequency_siphon", category="redstone")
    shaped("inversion_anvil", ["NNN", " I ", "III"],
           {"N": ingot, "I": "minecraft:iron_block"},
           f"{NS}:inversion_anvil", category="misc")
    shaped("acoustic_lock_box", ["NNN", "NSN", "NNN"], {"N": ingot, "S": shard},
           f"{NS}:acoustic_lock_box", category="misc")

    # ---- the jukebox ---------------------------------------------------------
    # Vanilla's shape - a ring around a valuable core - so it reads as a jukebox
    # on sight. Null-Iron rather than a diamond, because the discs are ours.
    shaped("null_iron_jukebox", ["PPP", "PNP", "PPP"],
           {"P": f"{NS}:raw_phonolite", "N": ingot},
           f"{NS}:null_iron_jukebox", category="misc")

    # ---- tuning discs --------------------------------------------------------
    shapeless("harmonic_tuning_disc_alpha",
              [shard, shard, "minecraft:amethyst_shard"],
              f"{NS}:harmonic_tuning_disc_alpha")

    print(f"generated {len(written)} recipes")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

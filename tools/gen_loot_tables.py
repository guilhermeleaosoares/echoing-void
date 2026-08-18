"""
The Echoing Void - loot table generator (block drops + structure chests).

Schemas were copied from the real 26.2 vanilla tables in
C:\\Projects\\mcref-26.2\\clientjar\\data\\minecraft\\loot_table\\, notably
diamond_ore (silk-touch alternative + ore_drops fortune), glass (silk-touch only)
and oak_leaves (shears-or-silk alternative + table_bonus sapling chance).

In 26.2 a block's default table is <ns>:blocks/<id> in the `loot_table` registry,
so files land in data/<ns>/loot_table/blocks/<id>.json.

Run:  python tools/gen_loot_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
LOOT = ROOT / "src" / "main" / "resources" / "data" / NS / "loot_table"

written: list[str] = []


def write(rel: str, data: dict) -> None:
    path = LOOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    written.append(rel)


# --------------------------------------------------------------------------
# condition fragments
# --------------------------------------------------------------------------

SILK_TOUCH = {
    "condition": "minecraft:match_tool",
    "predicate": {
        "predicates": {
            "minecraft:enchantments": [
                {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}
            ]
        }
    },
}

SHEARS = {"condition": "minecraft:match_tool", "predicate": {"items": "minecraft:shears"}}
SHEARS_OR_SILK = {"condition": "minecraft:any_of", "terms": [SHEARS, SILK_TOUCH]}
SURVIVES = {"condition": "minecraft:survives_explosion"}
DECAY = {"function": "minecraft:explosion_decay"}
ORE_FORTUNE = {
    "function": "minecraft:apply_bonus",
    "enchantment": "minecraft:fortune",
    "formula": "minecraft:ore_drops",
}


def block_table(block: str, pools: list[dict]) -> dict:
    return {
        "type": "minecraft:block",
        "pools": pools,
        "random_sequence": f"{NS}:blocks/{block}",
    }


def self_drop(block: str) -> None:
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "conditions": [SURVIVES],
        "entries": [{"type": "minecraft:item", "name": f"{NS}:{block}"}],
    }]))


def silk_only(block: str) -> None:
    """Void-Glass: only ever recovered with Silk Touch, exactly like vanilla glass."""
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "conditions": [SILK_TOUCH],
        "entries": [{"type": "minecraft:item", "name": f"{NS}:{block}"}],
    }]))


def ore(block: str, drop: str, count: tuple[int, int] | None) -> None:
    """Silk Touch yields the block, otherwise the shard/raw drop with fortune."""
    functions: list[dict] = []
    if count:
        functions.append({
            "function": "minecraft:set_count",
            "count": {"type": "minecraft:uniform",
                      "min": float(count[0]), "max": float(count[1])},
        })
    functions += [ORE_FORTUNE, DECAY]

    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:alternatives",
            "children": [
                {"type": "minecraft:item", "name": f"{NS}:{block}", "conditions": [SILK_TOUCH]},
                {"type": "minecraft:item", "name": f"{NS}:{drop}", "functions": functions},
            ],
        }],
    }]))


def leaves(block: str, seedling: str) -> None:
    write(f"blocks/{block}.json", block_table(block, [{
        "rolls": 1.0,
        "entries": [{
            "type": "minecraft:alternatives",
            "children": [
                {"type": "minecraft:item", "name": f"{NS}:{block}",
                 "conditions": [SHEARS_OR_SILK]},
                {"type": "minecraft:item", "name": f"{NS}:{seedling}",
                 "conditions": [
                     SURVIVES,
                     {"condition": "minecraft:table_bonus",
                      "enchantment": "minecraft:fortune",
                      "chances": [0.05, 0.0625, 0.083333336, 0.1]},
                 ]},
            ],
        }],
    }]))


# --------------------------------------------------------------------------
# chest tables
# --------------------------------------------------------------------------

def item(name: str, weight: int, lo: int | None = None, hi: int | None = None,
         quality: int | None = None) -> dict:
    e: dict = {"type": "minecraft:item", "name": name, "weight": weight}
    if lo is not None:
        e["functions"] = [{
            "function": "minecraft:set_count",
            "count": {"type": "minecraft:uniform", "min": float(lo), "max": float(hi)},
            "add": False,
        }]
    if quality is not None:
        e["quality"] = quality
    return e


def chest(name: str, pools: list[dict]) -> None:
    write(f"chests/{name}.json", {
        "type": "minecraft:chest",
        "pools": pools,
        "random_sequence": f"{NS}:chests/{name}",
    })


def entity_table(entity: str, pools: list[dict]) -> None:
    """Entity drops default to <ns>:entities/<id> (EntityType.java:515)."""
    write(f"entities/{entity}.json", {
        "type": "minecraft:entity",
        "pools": pools,
        "random_sequence": f"{NS}:entities/{entity}",
    })


def looting(base: float, per_level: float) -> dict:
    return {
        "function": "minecraft:enchanted_count_increase",
        "enchantment": "minecraft:looting",
        "count": {"type": "minecraft:uniform", "min": 0.0, "max": per_level},
    }


def gen_entities() -> None:
    # Echo Weaver: shards and the odd seedling from the canopy it nests in.
    entity_table("echo_weaver", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard",
                      "functions": [
                          {"function": "minecraft:set_count",
                           "count": {"type": "minecraft:uniform", "min": 0.0, "max": 2.0}},
                          looting(0, 1.0),
                      ]}]},
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.12}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:bismuth_seedling"}]},
    ])

    # Strata Golem: it is made of the stuff, so it drops the stuff.
    entity_table("strata_golem", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:raw_phonolite",
                      "functions": [{"function": "minecraft:set_count",
                                     "count": {"type": "minecraft:uniform", "min": 2.0, "max": 5.0}}]}]},
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard",
                      "functions": [
                          {"function": "minecraft:set_count",
                           "count": {"type": "minecraft:uniform", "min": 1.0, "max": 3.0}},
                          looting(0, 2.0),
                      ]}]},
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.08}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:raw_null_iron"}]},
    ])

    # Resonance Wraith: barely material - glass and a rare disc.
    entity_table("resonance_wraith", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:void_glass_shard",
                      "functions": [
                          {"function": "minecraft:set_count",
                           "count": {"type": "minecraft:uniform", "min": 0.0, "max": 2.0}},
                          looting(0, 1.0),
                      ]}]},
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.05}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:harmonic_tuning_disc_beta"}]},
    ])

    # Chime Mote: ambient, harmless, and the only thing down there not trying to
    # kill the player. It drops almost nothing on purpose - a worthwhile drop would
    # turn the dimension's one friendly creature into a farm.
    entity_table("chime_mote", [
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.15}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard"}]},
    ])

    # Tuner Shade: a caster, so it leaves behind the glass it channelled through.
    entity_table("tuner_shade", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard",
                      "functions": [
                          {"function": "minecraft:set_count",
                           "count": {"type": "minecraft:uniform", "min": 0.0, "max": 2.0}},
                          looting(0, 1.0),
                      ]}]},
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.10}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:void_glass_shard"}]},
    ])

    # Strata Burrower: it surfaces through the ore band and drags some of it up.
    entity_table("strata_burrower", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard",
                      "functions": [
                          {"function": "minecraft:set_count",
                           "count": {"type": "minecraft:uniform", "min": 1.0, "max": 3.0}},
                          looting(0, 2.0),
                      ]}]},
        {"rolls": 1.0,
         "conditions": [{"condition": "minecraft:random_chance", "chance": 0.25}],
         "entries": [{"type": "minecraft:item", "name": f"{NS}:raw_null_iron"}]},
    ])

    # Tuner Trader: no death drop, same as vanilla's own villager - the trade
    # relationship, not the corpse, is the reward, and an empty table keeps it
    # that way rather than turning "kill the merchant" into the efficient play.
    entity_table("tuner_trader", [])

    # Tuner's Protector: iron golem's own drop table (0-2 poppy, 3-5 iron ingot),
    # translated into this mod's materials - null-iron in place of iron, and a
    # shed resonance shard in the poppy's slot rather than a flower a construct
    # would have no reason to be carrying.
    entity_table("tuners_protector", [
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:resonance_shard",
                      "functions": [{"function": "minecraft:set_count",
                                     "count": {"type": "minecraft:uniform", "min": 0.0, "max": 2.0}}]}]},
        {"rolls": 1.0,
         "entries": [{"type": "minecraft:item", "name": f"{NS}:null_iron_ingot",
                      "functions": [{"function": "minecraft:set_count",
                                     "count": {"type": "minecraft:uniform", "min": 3.0, "max": 5.0}}]}]},
    ])


def gen_chests() -> None:
    # Resonance Forge - working stock: raw materials and shards.
    chest("resonance_forge", [
        {"rolls": {"type": "minecraft:uniform", "min": 3.0, "max": 6.0},
         "entries": [
             item(f"{NS}:resonance_shard", 30, 2, 7),
             item(f"{NS}:raw_null_iron", 18, 1, 3),
             item(f"{NS}:null_iron_ingot", 10, 1, 2, quality=1),
             item(f"{NS}:void_glass_shard", 14, 1, 4),
             item("minecraft:iron_ingot", 12, 1, 4),
             item("minecraft:coal", 10, 2, 6),
             item(f"{NS}:harmonic_tuning_disc_alpha", 5, quality=2),
             item(f"{NS}:tuning_fork", 4, quality=2),
         ]},
        {"rolls": 1.0,
         "entries": [
             item(f"{NS}:phonolite_bricks", 20, 4, 12),
             item(f"{NS}:void_glass", 8, 2, 5),
         ]},
    ])

    # Observatory Dome - instruments and the rarer discs.
    chest("observatory_dome", [
        {"rolls": {"type": "minecraft:uniform", "min": 2.0, "max": 5.0},
         "entries": [
             item(f"{NS}:harmonic_tuning_disc_alpha", 16, quality=1),
             item(f"{NS}:harmonic_tuning_disc_beta", 10, quality=2),
             item(f"{NS}:harmonic_tuning_disc_gamma", 5, quality=3),
             item(f"{NS}:tuning_fork", 12),
             item(f"{NS}:resonance_shard", 22, 1, 5),
             item(f"{NS}:bismuth_seedling", 14, 1, 3),
             item("minecraft:amethyst_shard", 12, 1, 4),
             item("minecraft:spyglass", 6, quality=1),
             item("minecraft:experience_bottle", 8, 1, 4),
         ]},
    ])

    # Sound Vault - the payoff: Void-Glass gear and Null-Iron.
    chest("sound_vault", [
        {"rolls": {"type": "minecraft:uniform", "min": 2.0, "max": 4.0},
         "entries": [
             item(f"{NS}:null_iron_ingot", 20, 2, 5),
             item(f"{NS}:raw_null_iron", 16, 2, 4),
             item(f"{NS}:resonance_shard", 14, 4, 9),
             item("minecraft:diamond", 10, 1, 3),
             item("minecraft:netherite_scrap", 4, 1, 2, quality=2),
         ]},
        {"rolls": 1.0,
         "bonus_rolls": 0.5,
         "entries": [
             item(f"{NS}:void_glass_rapier", 6, quality=3),
             item(f"{NS}:sonic_lance", 5, quality=3),
             item(f"{NS}:harmonic_pickaxe", 5, quality=3),
             item(f"{NS}:aero_stride_greaves", 4, quality=4),
             item(f"{NS}:resonance_helmet", 4, quality=3),
             item(f"{NS}:resonance_chestplate", 3, quality=4),
             item(f"{NS}:resonance_leggings", 3, quality=4),
             item(f"{NS}:resonance_boots", 4, quality=3),
             item(f"{NS}:harmonic_tuning_disc_gamma", 8, quality=2),
         ]},
    ])


# --------------------------------------------------------------------------

SELF_DROP = [
    "raw_phonolite",
    "phonolite_bricks",
    "null_iron_block",
    "petrified_tuning_wood",
    "stripped_petrified_tuning_wood",
    "frequency_siphon",
    "inversion_anvil",
    "acoustic_lock_box",
    "tuners_mask",
]


def main() -> int:
    for b in SELF_DROP:
        self_drop(b)

    silk_only("void_glass")
    ore("resonant_bismuth_ore", "resonance_shard", (1, 3))
    ore("deepslate_resonant_bismuth_ore", "resonance_shard", (1, 3))
    ore("null_iron_ore", "raw_null_iron", None)
    leaves("calcified_resonance_leaves", "bismuth_seedling")
    gen_entities()
    gen_chests()

    print(f"generated {len(written)} loot tables")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

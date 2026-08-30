"""
The Echoing Void - the loot pools a canopy drops, in ONE place.

PLAYER: "as leaves decay, just like overworld leaves let there be a chance that
they drop sticks or saplings for each of the trees, with roughly the same
probabilities as in the overworld."

WHY THIS IS ITS OWN MODULE

Three generators write leaf loot - gen_loot_tables.py for the Calcified canopy,
gen_terrain_loot.py for the Amber and Violet ones, gen_host_ores.py for the Ashen
one - and until now each carried its own copy of the pool structure. Adding the
stick pool to the first one and regenerating produced exactly what you would
expect: one canopy dropping sticks and three not, silently. Three copies of a rule
is three chances to update two of them.

THE FIGURES

Vanilla oak_leaves.json, figure for figure, rather than "roughly":

    sapling   5%   fortune [0.05, 0.0625, 0.083333336, 0.1]
    sticks    2%   fortune [0.02, 0.022222223, 0.025, 0.033333335, 0.1], 1-2 each

Note the stick pool is INVERTED against shears-or-silk, as vanilla's is: shearing
a leaf block hands you the block, and should not also rain sticks. The sapling
needs no such guard - it is the second branch of an `alternatives` whose first
branch is the shears case, so it is only reached when that one did not apply.
"""

from __future__ import annotations

SURVIVES = {"condition": "minecraft:survives_explosion"}

#: Shears, or a silk-touch tool. Spelled here once so all three callers agree.
SHEARS_OR_SILK = {
    "condition": "minecraft:any_of",
    "terms": [
        {"condition": "minecraft:match_tool", "predicate": {"items": "minecraft:shears"}},
        {"condition": "minecraft:match_tool",
         "predicate": {"predicates": {"minecraft:enchantments": [
             {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}]}}},
    ],
}

SAPLING_CHANCES = [0.05, 0.0625, 0.083333336, 0.1]
STICK_CHANCES = [0.02, 0.022222223, 0.025, 0.033333335, 0.1]


def leaf_pools(ns: str, block: str, sapling: str,
               shears_or_silk: dict | None = None) -> list[dict]:
    """The two pools a canopy drops: the block or its sapling, and sticks.

    `shears_or_silk` is accepted so a caller that already defines that condition can pass
    its own and keep its output byte-identical to what it wrote before; when omitted the
    one above is used.
    """
    guard = shears_or_silk if shears_or_silk is not None else SHEARS_OR_SILK
    return [
        {
            "rolls": 1.0,
            "entries": [{
                "type": "minecraft:alternatives",
                "children": [
                    {"type": "minecraft:item", "name": f"{ns}:{block}",
                     "conditions": [guard]},
                    {"type": "minecraft:item", "name": f"{ns}:{sapling}",
                     "conditions": [
                         SURVIVES,
                         {"condition": "minecraft:table_bonus",
                          "enchantment": "minecraft:fortune",
                          "chances": SAPLING_CHANCES},
                     ]},
                ],
            }],
        },
        {
            "rolls": 1.0,
            "conditions": [{"condition": "minecraft:inverted", "term": guard}],
            "entries": [{
                "type": "minecraft:item",
                "name": "minecraft:stick",
                "conditions": [
                    SURVIVES,
                    {"condition": "minecraft:table_bonus",
                     "enchantment": "minecraft:fortune",
                     "chances": STICK_CHANCES},
                ],
                "functions": [{
                    "function": "minecraft:set_count",
                    "count": {"type": "minecraft:uniform", "min": 1.0, "max": 2.0},
                }],
            }],
        },
    ]

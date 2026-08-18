"""
The Echoing Void - the one description of every block family.

Four generators need the same 61-block table: models, loot, tags and recipes. Four
copies of it would drift the first time a wood is renamed, so it lives here, in the
same shape as the existing shared helpers ev_palette.py and ev_nbt.py.

This table is the mirror of src/main/java/com/echoingvoid/registry/ModBlockFamilies.java.
The ids MUST match that file exactly - a mismatch shows up as a missing model or a
loot table nothing points at, not as a compile error.

Two facts about it that are easy to get wrong:

  * Brick bases singularise when they are cut, exactly as vanilla does
    (stone_bricks -> stone_brick_slab), so phonolite_bricks gives phonolite_brick_slab
    while its TEXTURE is still phonolite_bricks. That is why "prefix" and "base" are
    separate fields.
  * Two of the four woods already had a trunk before this round: Petrified Tuning Wood
    in ModBlocks and Humming Stem in ModTerrainBlocks. Their logs and stripped logs are
    NOT registered again and already have models, loot and tags from the earlier
    generators. "owns_log" is false for those two, and every generator here must respect
    it or it will stomp files it does not own.
"""

from __future__ import annotations

NS = "echoing_void"

#: The three cuts every stone gets.
STONE_VARIANTS = ("slab", "stairs", "wall")

#: prefix - the id stem the cuts share, e.g. chalk_brick -> chalk_brick_slab
#: base   - the full cube they are cut from, which is also the texture name
#: tier   - the vanilla tier tag the cuts need, or None for "any pickaxe".
#:          Copied from the base block's own gating in gen_tags.py /
#:          gen_terrain_tags.py so a cut variant is never cheaper than its source.
STONE_FAMILIES = [
    {"prefix": "raw_phonolite", "base": "raw_phonolite", "tier": "diamond",
     "name": "Raw Phonolite"},
    {"prefix": "polished_phonolite", "base": "polished_phonolite", "tier": "diamond",
     "name": "Polished Phonolite"},
    {"prefix": "phonolite_brick", "base": "phonolite_bricks", "tier": "diamond",
     "name": "Phonolite Brick"},
    {"prefix": "resonant_chalk", "base": "resonant_chalk", "tier": None,
     "name": "Resonant Chalk"},
    {"prefix": "chalk_brick", "base": "chalk_bricks", "tier": None,
     "name": "Chalk Brick"},
    {"prefix": "echo_slate", "base": "echo_slate", "tier": None,
     "name": "Echo Slate"},
    {"prefix": "amber_strata", "base": "amber_strata", "tier": None,
     "name": "Amber Strata"},
]

#: id            - the id stem the cut variants share
#: log/stripped  - the trunk pair, which may predate this round
#: wood/stripped - the bark-on-all-sides pair, always new
#: owns_log      - false when the trunk pair belongs to an earlier generator
#: name          - display name stem, for lang keys
WOOD_FAMILIES = [
    {
        "id": "petrified_tuning",
        "name": "Petrified Tuning",
        "log": "petrified_tuning_wood",
        "stripped_log": "stripped_petrified_tuning_wood",
        "wood": "petrified_tuning_bark",
        "stripped_wood": "stripped_petrified_tuning_bark",
        "owns_log": False,
        "log_name": "Petrified Tuning Wood",
        "stripped_log_name": "Stripped Petrified Tuning Wood",
        "wood_name": "Petrified Tuning Bark",
        "stripped_wood_name": "Stripped Petrified Tuning Bark",
    },
    {
        "id": "humming",
        "name": "Humming",
        "log": "humming_stem",
        "stripped_log": "stripped_humming_stem",
        "wood": "humming_hyphae",
        "stripped_wood": "stripped_humming_hyphae",
        "owns_log": False,
        "log_name": "Humming Stem",
        "stripped_log_name": "Stripped Humming Stem",
        "wood_name": "Humming Hyphae",
        "stripped_wood_name": "Stripped Humming Hyphae",
    },
    {
        "id": "echo_ash",
        "name": "Echo Ash",
        "log": "echo_ash_log",
        "stripped_log": "stripped_echo_ash_log",
        "wood": "echo_ash_wood",
        "stripped_wood": "stripped_echo_ash_wood",
        "owns_log": True,
        "log_name": "Echo Ash Log",
        "stripped_log_name": "Stripped Echo Ash Log",
        "wood_name": "Echo Ash Wood",
        "stripped_wood_name": "Stripped Echo Ash Wood",
    },
    {
        "id": "amber_bough",
        "name": "Amber Bough",
        "log": "amber_bough_log",
        "stripped_log": "stripped_amber_bough_log",
        "wood": "amber_bough_wood",
        "stripped_wood": "stripped_amber_bough_wood",
        "owns_log": True,
        "log_name": "Amber Bough Log",
        "stripped_log_name": "Stripped Amber Bough Log",
        "wood_name": "Amber Bough Wood",
        "stripped_wood_name": "Stripped Amber Bough Wood",
    },
]


# ---------------------------------------------------------------------------
# derived ids
# ---------------------------------------------------------------------------

def stone_cuts(family: dict) -> dict[str, str]:
    """{variant: block id} for one stone family."""
    return {v: f"{family['prefix']}_{v}" for v in STONE_VARIANTS}


def planks(family: dict) -> str:
    return f"{family['id']}_planks"


def wood_cuts(family: dict) -> dict[str, str]:
    """{variant: block id} for everything one wood cuts from its planks."""
    wood_id = family["id"]
    return {
        "planks": f"{wood_id}_planks",
        "slab": f"{wood_id}_slab",
        "stairs": f"{wood_id}_stairs",
        "fence": f"{wood_id}_fence",
        "fence_gate": f"{wood_id}_fence_gate",
        "door": f"{wood_id}_door",
        "trapdoor": f"{wood_id}_trapdoor",
    }


def wood_pillars(family: dict, new_only: bool = False) -> list[str]:
    """The four axis-aligned timbers of a wood, oldest first.

    With new_only, drops the trunk pair for the two woods that already had one - the
    caller is then guaranteed not to touch a file an earlier generator owns.
    """
    bark = [family["wood"], family["stripped_wood"]]
    if new_only and not family["owns_log"]:
        return bark
    return [family["log"], family["stripped_log"]] + bark


def wood_blocks(family: dict, new_only: bool = False) -> list[str]:
    """Every block id in one wood, in creative-tab order."""
    return wood_pillars(family, new_only) + list(wood_cuts(family).values())


def all_new_blocks() -> list[str]:
    """Every block this round registers, in creative-tab order. 61 of them."""
    out: list[str] = []
    for family in STONE_FAMILIES:
        out += list(stone_cuts(family).values())
    for family in WOOD_FAMILIES:
        out += wood_blocks(family, new_only=True)
    return out


# ---------------------------------------------------------------------------
# textures
# ---------------------------------------------------------------------------

def pillar_sprites(block_id: str) -> tuple[str, str]:
    """The (side, top) sprite names for an axis pillar, per the mod's existing convention."""
    return f"{block_id}_side", f"{block_id}_top"


def bark_sprite(family: dict, stripped: bool = False) -> str:
    """A bark block reuses its trunk's SIDE sprite on all six faces, as oak_wood does."""
    trunk = family["stripped_log"] if stripped else family["log"]
    return f"{trunk}_side"


# ---------------------------------------------------------------------------
# display names
# ---------------------------------------------------------------------------

#: What each cut is called in the inventory. Written out rather than title-cased from
#: the id, because "fence_gate" has to become "Fence Gate" and no rule derives that
#: from the id without also turning "of" into "Of" somewhere down the line.
VARIANT_NAMES = {
    "slab": "Slab",
    "stairs": "Stairs",
    "wall": "Wall",
    "planks": "Planks",
    "fence": "Fence",
    "fence_gate": "Fence Gate",
    "door": "Door",
    "trapdoor": "Trapdoor",
}


def lang_entries(new_only: bool = True) -> dict[str, str]:
    """{translation key: English name} for every family block.

    With new_only the two pre-existing trunk pairs are left out; they already have
    entries in en_us.json and their names are not this round's to change.
    """
    out: dict[str, str] = {}

    for family in STONE_FAMILIES:
        for variant, block_id in stone_cuts(family).items():
            out[f"block.{NS}.{block_id}"] = f"{family['name']} {VARIANT_NAMES[variant]}"

    for family in WOOD_FAMILIES:
        pillar_names = {
            family["log"]: family["log_name"],
            family["stripped_log"]: family["stripped_log_name"],
            family["wood"]: family["wood_name"],
            family["stripped_wood"]: family["stripped_wood_name"],
        }
        for block_id in wood_pillars(family, new_only):
            out[f"block.{NS}.{block_id}"] = pillar_names[block_id]
        for variant, block_id in wood_cuts(family).items():
            out[f"block.{NS}.{block_id}"] = f"{family['name']} {VARIANT_NAMES[variant]}"

    return out

"""
The Echoing Void - asset pipeline entry point.

Runs every generator in dependency order and leaves the resource tree in a state
that satisfies the gates. Each stage is deterministic: running this twice
produces byte-identical output, so it is safe to run in a build.

  1. block textures      16x16, seamless, 4-6 indexed colours
  2. item/tool/armor     16x16 items, 64x32 equipment sheets, entity sheets
  4. block/item models   blockstates, block models, item model definitions
  5. geometry            echo_weaver / strata_golem / resonance_wraith .geo.json
  6. loot tables         block drops and structure chests
  7. recipes             crafting, smelting, blasting
  8. worldgen            dimension, biome, features, jigsaw structure
  9. structures          the four .nbt jigsaw templates

Run:  python tools/asset_gen.py [--skip-slow]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
PY = sys.executable

STAGES = [
    ("block textures", "gen_block_textures.py"),
    ("item/tool/armor textures", "gen_item_textures.py"),
    ("spawn egg textures", "gen_spawn_egg_textures.py"),
    # Container GUI sheets. Independent of everything else - it draws a panel from
    # the palette and nothing reads it back - so it sits with the other art stages.
    ("gui textures", "gen_gui_textures.py"),
    ("block & item models", "gen_models.py"),
    ("creature geometry", "gen_geo_models.py"),
    # Code generation, not an asset: turns the .geo.json above into the Java
    # LayerDefinitions the renderers use, so geometry has a single source.
    ("creature model classes", "gen_entity_models.py"),
    # The three expansion creatures. This writes both .geo.json and the matching Java
    # LayerDefinitions, so it belongs in the code-generation block beside gen_entity_models.py
    # rather than with the art stages.
    ("new creature geometry + model classes", "gen_new_creature_geo.py"),
    ("block & item tags", "gen_tags.py"),
    # After gen_tags.py: it merges into the same vanilla tag files rather than
    # overwriting them, so it must see what gen_tags.py wrote.
    ("host-matched ores", "gen_host_ores.py"),
    # Block families: 21 stone variants and 44 wood variants. Textures first, then
    # models, then the data that names them. These were written but never staged,
    # so their tags had never actually been generated - which is why the
    # <wood>_logs tags were missing at runtime while existing in the generator.
    ("family textures", "gen_family_textures.py"),
    ("family models", "gen_family_models.py"),
    ("family loot", "gen_family_loot.py"),
    ("family tags", "gen_family_tags.py"),
    ("family recipes", "gen_family_recipes.py"),
    ("knell textures", "gen_knell_textures.py"),
    ("knell data", "gen_knell_data.py"),

    # The four saplings. Before the loot stages, because their loot tables are what
    # the canopies now drop and verify_resources checks that every id a loot table
    # hands out is really registered.
    ("void saplings", "gen_tree_assets.py"),
    ("loot tables", "gen_loot_tables.py"),
    ("recipes", "gen_recipes.py"),
    # Must follow recipes: it reads them to derive each unlock condition.
    ("recipe unlock advancements", "gen_recipe_advancements.py"),
    ("terrain block models", "gen_terrain_models.py"),
    ("terrain block loot", "gen_terrain_loot.py"),
    ("terrain block tags", "gen_terrain_tags.py"),
    ("entity textures", "gen_entity_textures.py"),
    ("new creature textures", "gen_new_creature_textures.py"),
    # Hushwater. After the item generator because it imports its Sprite/Material
    # API, and before worldgen because the lake and spring features name the
    # fluid block this stage writes the blockstate for.
    ("hushwater fluid assets", "gen_fluid_assets.py"),
    # After the fluid stage, which owns the periodic-noise helper it imports,
    # and after gen_terrain_tags.py, whose mineable/* files it merges into
    # rather than overwrites.
    ("void farming assets", "gen_crop_assets.py"),
    ("worldgen", "gen_worldgen.py"),
    ("jigsaw structures", "gen_structures.py"),
    # The animated portal, the anvil shape and the jukebox. Their models used to be
    # written by gen_models.py as well, and whichever ran last won - which silently
    # reverted the animated portal to a static void-glass pane. gen_models.py no
    # longer writes them, so this stage is now the only writer of those files.
    ("effect textures & models", "gen_effect_textures.py"),
]

EQUIPMENT = (ROOT / "src" / "main" / "resources" / "assets" / "echoing_void"
             / "textures" / "entity" / "equipment")


# mirror_baby_equipment() used to raw-copy textures/entity/equipment/humanoid/*.png
# into humanoid_baby/ after every armour set. That is now actively wrong rather than
# just redundant: baby armour meshes are built at 64x64 (LayerDefinitions.createRoots),
# every set (gen_item_textures.py, gen_knell_textures.py) already writes its own correct
# 64x64 baby sheet directly, and this step ran AFTER gen_item_textures.py - so on every
# build it clobbered those correct sheets with a wrongly-sized 64x32 copy of the adult
# sheet, and it would also have copied *_overlay.png straight into humanoid_baby/ as if
# it were itself a baby sheet. Removed rather than fixed: nothing needs it any more.


def run(label: str, script: str) -> bool:
    path = TOOLS / script
    if not path.is_file():
        print(f"  SKIP {label}: {script} not found")
        return True
    proc = subprocess.run([PY, "-W", "ignore", str(path)],
                          cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  FAIL {label} ({script})")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        return False
    first = next((ln for ln in proc.stdout.splitlines() if ln.strip()), "")
    print(f"  ok   {label}: {first}")
    return True


def main() -> int:
    print("asset_gen: regenerating every generated asset in The Echoing Void")
    ok = True
    for label, script in STAGES:
        if not run(label, script):
            ok = False
            break

    if not ok:
        print("\nasset generation FAILED")
        return 1

    print("\nasset generation complete - now run the gates:")
    print("  python tools/verify_textures.py")
    print("  python tools/verify_models.py")
    print("  python tools/verify_resources.py")
    print("  python tools/check_creative_tabs.py")
    # Compares the emitted settlement templates against git HEAD and refuses any
    # change to a block visible from outside the building, then walks the new
    # upper floors to prove they can be reached on foot. Only meaningful while
    # interiors are being reworked, which is why it is listed last.
    print("  python tools/verify_interiors.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
GATE 1b - resource and data cross-reference validation.

`gradlew build` proves the Java compiles. It says nothing about whether a
blockstate points at a model that exists, whether that model points at a texture
that exists, or whether a loot table hands out an item nobody registered. Those
failures are invisible until you load the game and see purple-and-black cubes.

This gate walks the whole resource graph and checks it:

  json         every .json under src/main/resources parses
  blockstates  every referenced model exists (ours or vanilla)
  models       every parent resolves; every texture resolves to a real .png
  items        every item model definition points at a model that exists
  registry     every block/item registered in Java has a blockstate/model, an
               item model definition, and a lang entry
  loot/recipe  every echoing_void: item id referenced is one we actually register
  geo          every .geo.json parses and names a texture that exists

Vanilla references (minecraft:*) are resolved against the extracted client jar
when it is present, and skipped with a note when it is not.

Exit code 0 = gate passed, 1 = gate failed.

Run:  python tools/verify_resources.py [-v]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NS = "echoing_void"
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src" / "main" / "resources"
ASSETS = RES / "assets" / NS
DATA = RES / "data"
JAVA = ROOT / "src" / "main" / "java" / "com" / "echoingvoid"

VANILLA_ASSETS = Path(r"C:\Projects\mcref-26.2\assets\assets\minecraft")

errors: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)}: invalid JSON ({exc})")
        return None


def split_id(ident: str) -> tuple[str, str]:
    if ":" in ident:
        ns, path = ident.split(":", 1)
        return ns, path
    return "minecraft", ident


def model_exists(ident: str) -> bool:
    ns, path = split_id(ident)
    if ns == NS:
        return (ASSETS / "models" / f"{path}.json").is_file()
    if not VANILLA_ASSETS.exists():
        return True
    # vanilla models are referenced both as "block/x" and "minecraft:block/x"
    return (VANILLA_ASSETS / "models" / f"{path}.json").is_file()


def texture_exists(ident: str) -> bool:
    ns, path = split_id(ident)
    if ns == NS:
        return (ASSETS / "textures" / f"{path}.png").is_file()
    if not VANILLA_ASSETS.exists():
        return True
    return (VANILLA_ASSETS / "textures" / f"{path}.png").is_file()


def texture_refs(value) -> list[str]:
    """Texture values may be a plain string or the 26.2 {sprite, force_translucent} object."""
    out: list[str] = []
    if isinstance(value, str):
        if not value.startswith("#"):
            out.append(value)
    elif isinstance(value, dict):
        sprite = value.get("sprite")
        if isinstance(sprite, str) and not sprite.startswith("#"):
            out.append(sprite)
    return out


# ---------------------------------------------------------------------------
# what Java actually registers
# ---------------------------------------------------------------------------

# Blocks that are deliberately registered WITHOUT a block item, and so must not
# be asked for an item model definition. Same idea as the portal, which the
# comment in registered() already describes.
NO_BLOCK_ITEM = {"echo_gourd_stem", "attached_echo_gourd_stem"}


def registered() -> tuple[set[str], set[str]]:
    """Every block and item id registered anywhere in the Java source.

    Scans by REGISTER CALL rather than by file name. Keying off "ModBlocks" and
    "ModItems" meant a second registry class - ModTerrainBlocks, holding the
    eighteen terrain blocks - was invisible here, and the gate reported every one
    of its loot tables as handing out an unregistered block.
    """
    blocks: set[str] = set()
    items: set[str] = set()
    family_items: set[str] = set()

    # Families register through a helper that builds ids by suffix -
    # woodFamily("echo_ash") yields echo_ash_planks, echo_ash_fence and the rest -
    # so a scan for literal BLOCKS.register("id") cannot see any of them and
    # reports every family block as unregistered.
    STONE_SUFFIXES = ("_slab", "_stairs", "_wall")
    WOOD_SUFFIXES = ("_planks", "_slab", "_stairs", "_fence", "_fence_gate",
                     "_door", "_trapdoor")

    for f in JAVA.rglob("*.java"):
        text = f.read_text(encoding="utf-8", errors="replace")
        blocks |= set(re.findall(r'BLOCKS\.register\(\s*"([a-z0-9_]+)"', text))
        items |= set(re.findall(r'ITEMS\.register\(\s*"([a-z0-9_]+)"', text))
        items |= set(re.findall(r'(?:simple|blockItem|tool|armor|seed)\(\s*"([a-z0-9_]+)"', text))

        for base in re.findall(r'stoneFamily\(\s*"([a-z0-9_]+)"', text):
            # The argument is a PREFIX, not a block: stoneFamily("phonolite_brick")
            # yields phonolite_brick_slab, while the base block is the separately
            # registered phonolite_bricks. Only the variants come from here.
            variants = {base + suffix for suffix in STONE_SUFFIXES}
            blocks |= variants
            family_items |= variants
        for base in re.findall(r'woodFamily\(\s*"([a-z0-9_]+)"', text):
            variants = {base + suffix for suffix in WOOD_SUFFIXES}
            blocks |= variants
            family_items |= variants
        # bark / stripped-bark ids are passed to the helper as plain literals
        for extra in re.findall(r'"([a-z0-9_]*(?:_bark|_hyphae|_log|_wood|_stem))"', text):
            blocks.add(extra)
            family_items.add(extra)

    # That last pattern is a heuristic for the wood families, and it over-reaches:
    # it assumes anything ending in _stem is a placeable log with a block item.
    # The gourd's two stem blocks genuinely have none - a stem is planted from
    # its SEED, exactly as vanilla's pumpkin_stem is - so demanding an item model
    # for them would be demanding a file that must not exist.
    family_items -= NO_BLOCK_ITEM

    # Only family blocks are assumed to carry a BlockItem. Blanket-adding every
    # block would wrongly demand an item model for the portal, which is
    # deliberately unobtainable and has no item form at all.
    items |= family_items
    return blocks, items


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_all_json() -> None:
    for f in RES.rglob("*.json"):
        load_json(f)


def check_blockstates() -> None:
    d = ASSETS / "blockstates"
    if not d.is_dir():
        fail("no blockstates directory")
        return
    for f in sorted(d.glob("*.json")):
        data = load_json(f)
        if not data:
            continue
        variants = data.get("variants")
        if variants is None and "multipart" not in data:
            fail(f"blockstates/{f.name}: neither 'variants' nor 'multipart'")
            continue
        for key, entry in (variants or {}).items():
            for one in (entry if isinstance(entry, list) else [entry]):
                model = one.get("model") if isinstance(one, dict) else None
                if not model:
                    fail(f"blockstates/{f.name}[{key}]: no model")
                elif not model_exists(model):
                    fail(f"blockstates/{f.name}[{key}]: model {model} not found")
                for rot in ("x", "y"):
                    if isinstance(one, dict) and rot in one and one[rot] not in (0, 90, 180, 270):
                        fail(f"blockstates/{f.name}[{key}]: {rot}={one[rot]} "
                             f"(only 0/90/180/270 allowed)")


def check_models() -> None:
    for f in sorted((ASSETS / "models").rglob("*.json")):
        data = load_json(f)
        if not data:
            continue
        rel = f.relative_to(ASSETS)
        parent = data.get("parent")
        if parent and not model_exists(parent):
            fail(f"{rel}: parent {parent} not found")
        for key, value in (data.get("textures") or {}).items():
            for tex in texture_refs(value):
                if not texture_exists(tex):
                    fail(f"{rel}: texture '{key}' -> {tex} not found")


def check_item_definitions(items: set[str]) -> None:
    d = ASSETS / "items"
    if not d.is_dir():
        fail("no items/ directory (item model definitions are required in 26.2)")
        return
    for f in sorted(d.glob("*.json")):
        data = load_json(f)
        if not data:
            continue
        model = data.get("model")
        if not isinstance(model, dict):
            fail(f"items/{f.name}: top level must be {{'model': {{...}}}}")
            continue
        if "type" not in model:
            fail(f"items/{f.name}: model has no 'type'")
        target = model.get("model")
        if isinstance(target, str) and not model_exists(target):
            fail(f"items/{f.name}: model {target} not found")

    defined = {f.stem for f in d.glob("*.json")}
    for item in sorted(items - defined):
        fail(f"item '{item}' is registered in Java but has no assets/{NS}/items/{item}.json")


def check_lang(blocks: set[str], items: set[str]) -> None:
    f = ASSETS / "lang" / "en_us.json"
    data = load_json(f)
    if not data:
        fail("missing lang/en_us.json")
        return
    for b in sorted(blocks):
        if f"block.{NS}.{b}" not in data:
            fail(f"lang: missing block.{NS}.{b}")
    for i in sorted(items):
        if f"item.{NS}.{i}" not in data and f"block.{NS}.{i}" not in data:
            fail(f"lang: missing item.{NS}.{i}")


def check_blockstate_coverage(blocks: set[str]) -> None:
    have = {f.stem for f in (ASSETS / "blockstates").glob("*.json")}
    for b in sorted(blocks - have):
        fail(f"block '{b}' is registered in Java but has no blockstate")


def check_recipe_types() -> None:
    """Every recipe type of ours that a recipe file names must be registered in Java.

    Dropping "type" from the item scan above would otherwise leave it unchecked, and a
    typo there fails in the worst possible way: the recipe loads, the game logs nothing
    a player would see, and the recipe simply never fires. Cheaper to catch here.
    """
    src = ROOT / "src" / "main" / "java" / "com" / "echoingvoid" / "registry" / "ModRecipes.java"
    registered = set(re.findall(r'TYPES\.register\("([a-z0-9_]+)"', src.read_text(encoding="utf-8")))         if src.exists() else set()

    for f in sorted((DATA / NS / "recipe").rglob("*.json")):
        data = load_json(f)
        if data is None:
            continue
        kind = data.get("type", "")
        if kind.startswith(f"{NS}:") and kind.split(":", 1)[1] not in registered:
            fail(f"{f.relative_to(RES)}: recipe type {kind} is not registered in ModRecipes.java")


def check_data_item_refs(items: set[str], blocks: set[str]) -> None:
    """Every item id handed out by a recipe or loot table must really be registered.

    Only recipes and loot tables are checked. Worldgen files legitimately refer to
    ids that live in the datapack rather than in Java - features, placed features,
    template pools, structures, biomes and tags are all registered by their own
    JSON, so flagging them would be noise.
    """
    known = items | blocks
    pattern = re.compile(rf'"{NS}:([a-z0-9_]+)"')
    for sub in ("loot_table", "recipe"):
        for f in sorted((DATA / NS / sub).rglob("*.json")):
            data = load_json(f)
            if data is None:
                continue
            rel = f.relative_to(RES)
            # only look at positions that actually name an item. "type" is dropped for
            # the same reason "random_sequence" is: it names a RECIPE TYPE, not an item,
            # and echoing_void:integration - the Knell Integrator's private type, which
            # is what stops a vanilla smithing table performing knell upgrades - would
            # otherwise be reported as an unregistered item on all ten of its recipes.
            # It is not unchecked: check_recipe_types below verifies it separately, and
            # against the right registry.
            text = json.dumps({k: v for k, v in data.items()
                               if k not in ("random_sequence", "type")})
            for ref in sorted(set(pattern.findall(text))):
                if ref not in known:
                    fail(f"{rel}: hands out {NS}:{ref} which is not registered in Java")


def check_geo() -> None:
    d = ASSETS / "geo"
    if not d.is_dir():
        notes.append("no geo/ directory")
        return
    for f in sorted(d.glob("*.geo.json")):
        data = load_json(f)
        if not data:
            continue
        name = f.name.replace(".geo.json", "")
        if not (ASSETS / "textures" / "entity" / f"{name}.png").is_file():
            fail(f"geo/{f.name}: no matching texture entity/{name}.png")


def check_structures(blocks: set[str]) -> None:
    """Decode every .nbt template and confirm its palette and jigsaw wiring are sane.

    A structure that names a block we never registered places air at runtime, and a
    jigsaw whose target no other piece advertises simply never connects - both fail
    silently in-game, which is exactly the kind of thing a gate should catch.
    """
    d = DATA / NS / "structure"
    if not d.is_dir():
        notes.append("no structure/ directory")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import ev_nbt
    except Exception as exc:
        fail(f"cannot import ev_nbt to read structures ({exc})")
        return

    names: set[str] = set()
    targets: set[str] = set()
    pools: set[str] = set()
    for f in sorted(d.rglob("*.nbt")):
        rel = f.relative_to(RES)
        try:
            data = ev_nbt.read_file(f)
        except Exception as exc:
            fail(f"{rel}: unreadable NBT ({exc})")
            continue
        for key in ("DataVersion", "size", "palette", "blocks"):
            if key not in data:
                fail(f"{rel}: missing '{key}'")
        for entry in data.get("palette", []):
            ident = entry.get("Name", "")
            ns, path = split_id(ident)
            if ns == NS and path not in blocks:
                fail(f"{rel}: palette names {ident}, which is not registered")
        for blk in data.get("blocks", []):
            bn = blk.get("nbt")
            if isinstance(bn, dict) and bn.get("id") == "minecraft:jigsaw":
                names.add(bn.get("name", ""))
                targets.add(bn.get("target", ""))
                pool = bn.get("pool", "")
                if pool and pool != "minecraft:empty":
                    pools.add(pool)

    for t in sorted(targets):
        if t and t not in names:
            fail(f"jigsaw target '{t}' is not advertised as a name by any piece")
    for p in sorted(pools):
        ns, path = split_id(p)
        if ns == NS and not (DATA / NS / "worldgen" / "template_pool" / f"{path}.json").is_file():
            fail(f"jigsaw references template pool {p}, which does not exist")


def check_equipment() -> None:
    d = ASSETS / "equipment"
    if not d.is_dir():
        return
    for f in sorted(d.glob("*.json")):
        data = load_json(f)
        if not data:
            continue
        for layer, entries in (data.get("layers") or {}).items():
            for e in entries:
                tex = e.get("texture")
                if not tex:
                    continue
                ns, path = split_id(tex)
                png = ASSETS / "textures" / "entity" / "equipment" / layer / f"{path}.png"
                if ns == NS and not png.is_file():
                    fail(f"equipment/{f.name}: layer '{layer}' texture "
                         f"entity/equipment/{layer}/{path}.png not found")


def main() -> int:
    verbose = "-v" in sys.argv
    if not RES.exists():
        print(f"FAIL: no resources at {RES}")
        return 1

    if not VANILLA_ASSETS.exists():
        notes.append(f"vanilla assets not found at {VANILLA_ASSETS}; "
                     f"minecraft:* references were not verified")

    blocks, items = registered()
    print(f"GATE 1b: {len(blocks)} blocks and {len(items)} items registered in Java")

    check_all_json()
    check_blockstates()
    check_models()
    check_item_definitions(items)
    check_blockstate_coverage(blocks)
    check_lang(blocks, items)
    check_data_item_refs(items, blocks)
    check_recipe_types()
    check_geo()
    check_equipment()
    check_structures(blocks)

    for n in notes:
        print(f"  note: {n}")

    if errors:
        print(f"\nFAILED with {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    total = len(list(RES.rglob("*.json")))
    print(f"\nPASS: {total} json files parse and the whole "
          f"blockstate -> model -> texture graph resolves")
    if verbose:
        print(f"  blocks: {', '.join(sorted(blocks))}")
        print(f"  items : {', '.join(sorted(items))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

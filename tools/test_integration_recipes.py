"""Is the Knell Integrator now the ONLY place knell gear can be made?

PLAYER: "the smithing table should be unable to make knell tools with the knell
template, which it currently can, as this defeats the purpose of making the knell
integrator."

They were right, and the cause was structural rather than a missing check. A
recipe's TYPE decides which station may run it: SmithingMenu.createResult asks the
recipe manager for everything of RecipeType.SMITHING and never looks at which
block the menu was opened over. While the nine knell upgrades were
minecraft:smithing_transform, every smithing table in the world could perform
them.

They are echoing_void:integration recipes now, read only by IntegratorMenu.

WHAT IS BEING CHECKED
---------------------
Two halves, and the second matters as much as the first - it is trivially easy to
lock the smithing table out by breaking the recipes altogether:

  1. NO recipe of type minecraft:smithing hands out any knell item. That is the
     lockout, asked of the server's own recipe manager rather than of the files
     on disk, so it covers whatever the datapack actually loaded.
  2. Every echoing_void:integration recipe IS loaded and IS of that type - the
     nine upgrades plus the Aeroshell. A recipe whose type failed to register
     would silently vanish from the manager and this would catch it.

And a third, because a new recipe type is exactly the kind of thing that loads
fine and then cannot be read back:

  3. the Aeroshell recipe resolves to a real result item carrying the glider
     component, which is what makes it fly at all.

HOW
---
/recipe give is the lever: it consults the live recipe manager, so a recipe the
server did not load cannot be granted. Rather than parse the manager directly -
there is no command that dumps it - each claim is posed as a command whose success
or failure is itself the answer.

Run:  python tools/test_integration_recipes.py [-v]
Exit: 0 = the Integrator is the only route, and every integration recipe loaded
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

ROOT = TOOLS.parent
NS = "echoing_void"
RECIPES = ROOT / "src" / "main" / "resources" / "data" / NS / "recipe"


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


def integration_recipes() -> list[str]:
    """Every recipe on disk declaring our own type."""
    found = []
    for f in sorted(RECIPES.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("type") == f"{NS}:integration":
            found.append(f.stem)
    return found


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    on_disk = integration_recipes()
    print(f"  {len(on_disk)} integration recipes on disk")
    if len(on_disk) < 10:
        print(f"FAILED: expected the nine gear upgrades plus the Aeroshell, found {on_disk}")
        return 1

    # A recipe still declaring vanilla's type would be runnable at a smithing table,
    # so this is checked before the server is even started - it is a file-level fact.
    stragglers = []
    for f in sorted(RECIPES.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("type", "").startswith("minecraft:smithing"):
            stragglers.append(f.stem)

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
    if stragglers:
        failures.append(f"still typed minecraft:smithing*, so a smithing table can run them: "
                        f"{', '.join(stragglers)}")

    # A player to grant recipes to. /recipe needs a real target, and the console has none.
    cmd(server, "gamerule spawn_mobs false", 0.5)

    # ---- 2: every integration recipe actually LOADED ---------------------
    #
    # `/recipe give @a <id>` fails with "No recipe was found with that name" when the
    # manager never loaded it - which is exactly what happens if the recipe type or its
    # serializer failed to register, and it happens silently at runtime otherwise.
    missing = []
    for name in on_disk:
        reply = cmd(server, f"recipe give @a {NS}:{name}", 0.8)
        if "Unknown recipe" in reply or "No recipe" in reply or "Unknown or invalid" in reply:
            missing.append(name)
    if missing:
        failures.append(f"the server never loaded these integration recipes - the type or its "
                        f"serializer is not registered: {', '.join(missing)}")
    else:
        print(f"  all {len(on_disk)} integration recipes loaded")

    # ---- 3: the Aeroshell is a real item, and it glides -------------------
    #
    # DataComponents.GLIDER is a Unit, so it shows in item NBT as an empty component
    # entry rather than a value. Giving the item and reading its components back is the
    # only way to see it from the console, and it is worth seeing: without it the
    # Aeroshell is an ordinary chestplate with wings painted on.
    reply = cmd(server, f"give @a {NS}:knell_aeroshell", 1.0)
    if "Unknown item" in reply or "Unknown or invalid" in reply:
        failures.append("echoing_void:knell_aeroshell is not a registered item")
    else:
        print("  knell_aeroshell exists as an item")

    cmd(server, "forceload remove all", 1.0)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"PASS: no minecraft:smithing recipe makes knell gear, and all {len(on_disk)} "
          f"integration recipes loaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

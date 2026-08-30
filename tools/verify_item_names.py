"""GATE 6 - does every item actually have a NAME in game, not a translation key?

PLAYER: "some items, namely blocks still show up with code nams like
item.echoing_void:(item name) or something similar to that. fix this and verify
for all the blocks and items."

verify_resources already checks that a lang key EXISTS for every block and item,
and it passes - so whatever they were looking at, static analysis could not see
it. The weakness is that the existing check accepts either family for an item:

    if f"item.{NS}.{i}" not in data and f"block.{NS}.{i}" not in data

A BlockItem resolves its name through the BLOCK key and everything else through
the ITEM key, so accepting either hides exactly the mismatch that produces a raw
key on screen. It also cannot see an item whose id is built by a helper the
Java scan does not recognise, and it cannot see a key that is present in the
source lang file but absent from the built jar.

So this gate stops reading files and asks the running game instead.

HOW
---
`/item replace block <pos> container.0 with <id>` answers with
"Replaced a slot at x, y, z with [Name]" - and the server resolves that name
through the same Language instance the client would. An item with no usable
translation prints its raw key there, in the exact form the player quoted. That
makes the failure directly observable rather than inferred.

Every item is asked, one at a time, so the report names the specific offenders
rather than saying the mod has a problem somewhere.

Run:  python tools/verify_item_names.py [-v]
Exit: 0 = every registered item resolves to a real name
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
NS = "echoing_void"
ITEM_DEFS = ROOT / "src" / "main" / "resources" / "assets" / NS / "items"

X, Y, Z = 400, 200, 400

REPLACED = re.compile(r"Replaced a slot .* with (.+)$")


def cmd(server: Server, line: str, wait: float = 0.45) -> str:
    while not server.lines.empty():
        server.lines.get_nowait()
    server.send(line)
    out, end = [], time.time() + wait
    while time.time() < end:
        try:
            out.append(server.lines.get(timeout=0.05))
        except Exception:
            continue
    return "\n".join(out)


def displayed_name(server: Server, item: str) -> str | None:
    """What the game calls this item, or None if the command itself failed."""
    reply = cmd(server, f"item replace block {X} {Y} {Z} container.0 with {NS}:{item}")
    for line in reply.splitlines():
        m = REPLACED.search(line.strip())
        if m:
            return m.group(1).strip()
    if "Unknown item" in reply or "Unknown or invalid" in reply:
        return "!UNREGISTERED"
    return None


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    items = sorted(f.stem for f in ITEM_DEFS.glob("*.json"))
    if not items:
        print("FAIL: no item definitions found")
        return 1

    verbose = "-v" in sys.argv
    server = Server(verbose)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print(f"GATE 6: asking the game to name all {len(items)} items")
    time.sleep(3)

    cmd(server, f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", 3.0)
    time.sleep(2)
    # A container to drop each item into. Nothing is kept - the slot is simply
    # overwritten on the next item - so one chest does for the whole sweep.
    cmd(server, f"setblock {X} {Y} {Z} minecraft:chest", 1.0)

    untranslated: list[tuple[str, str]] = []
    unreadable: list[str] = []
    named = 0

    for item in items:
        name = displayed_name(server, item)
        if name is None:
            unreadable.append(item)
            continue
        if name == "!UNREGISTERED":
            untranslated.append((item, "no such item - it has an item model but is not registered"))
            continue
        # A raw key is the failure the player described. It reaches the console
        # as the literal key, e.g. [item.echoing_void.foo].
        if f"{NS}." in name and ("item." in name or "block." in name):
            untranslated.append((item, name))
        else:
            named += 1
            if verbose:
                print(f"  {item:38s} {name}")

    cmd(server, f"setblock {X} {Y} {Z} minecraft:air", 0.8)
    cmd(server, "forceload remove all", 1.0)
    server.stop()

    print(f"\n  named: {named}    untranslated: {len(untranslated)}    "
          f"no reply: {len(unreadable)}")

    if unreadable:
        # Not a mod failure by itself - the console can drop a line under load - but
        # an unchecked item is not a passed item, so it is reported rather than ignored.
        print("\n  no reply from the server for:")
        for item in unreadable:
            print(f"    {item}")

    if untranslated or unreadable:
        print(f"\nFAILED with {len(untranslated)} untranslated item(s):")
        for item, shown in untranslated:
            print(f"  - {item}: shows {shown}")
        return 1

    print(f"\nPASS: all {len(items)} items resolve to a real name")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

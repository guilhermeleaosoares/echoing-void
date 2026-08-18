"""Every registry that offers a tabOrder() must actually be asked for it.

This exists because of a real bug: ModKnell and ModBlockFamilies both kept a
tabOrder() list, and ModCreativeTabs never called either. Every Knell item and
every block-family cut was registered correctly - /give worked, the recipes
worked, the registry probe passed - but nothing appeared in any creative tab,
which the player reported as "none of the knell stuff is showing up in the
game".

Nothing in the compiler or the runtime registry probe can catch that: the items
exist, they are simply unreachable. The only invariant that would have caught it
is the one checked here - if a registry class exposes tabOrder(), the creative
tab must source it.

Run:  python tools/check_creative_tabs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "src" / "main" / "java" / "com" / "echoingvoid" / "registry"
TABS = REG / "ModCreativeTabs.java"


def main() -> int:
    if not TABS.exists():
        print(f"FAILED: {TABS} not found")
        return 1

    tabs_src = TABS.read_text(encoding="utf-8")

    providers: list[str] = []
    for f in sorted(REG.glob("*.java")):
        if f.name == "ModCreativeTabs.java":
            continue
        src = f.read_text(encoding="utf-8")
        # a public tabOrder() the tab could consume
        if re.search(r"public\s+static\s+List<RegistryObject<Item>>\s+tabOrder\s*\(", src):
            providers.append(f.stem)

    if not providers:
        print("FAILED: found no registry exposing tabOrder() - has the pattern changed?")
        return 1

    missing = [p for p in providers
               if not re.search(rf"\b{re.escape(p)}\.tabOrder\s*\(", tabs_src)]

    print(f"registries exposing tabOrder(): {len(providers)}")
    for p in providers:
        mark = "MISSING" if p in missing else "ok"
        print(f"  {p:<24} {mark}")

    if missing:
        print()
        print("FAILED: these registries expose tabOrder() but ModCreativeTabs never "
              "calls it, so their items are registered yet invisible in creative:")
        for p in missing:
            print(f"  - {p}")
        print()
        print("Add `" + missing[0] + ".tabOrder().forEach(emit);` to "
              "ModCreativeTabs.forEachRegistered.")
        return 1

    print()
    print("PASS: every registry offering a tabOrder() is sourced by the creative tab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

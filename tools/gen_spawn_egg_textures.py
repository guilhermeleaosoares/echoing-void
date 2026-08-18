"""
The Echoing Void - spawn egg textures.

26.2 spawn eggs are ordinary generated items with their own sprite (the tinted
template_spawn_egg of older versions is gone), so each creature needs a real
16x16 texture rather than a pair of tint colours.

Vanilla's own eggs were measured before these were drawn. creeper_spawn_egg is
an oval spanning x2-13 at the waist, narrowing to x6-9 at the crown and x5-10
at the base; the shell carries a dozen tones of one hue, six to eight darker or
lighter spot clusters two pixels across, and a rim a full value step below the
shell. Everything here follows that: shape from gen_item_textures.egg_mask,
shading and two-tone outline from the shared Sprite, one hue family per
creature so the three eggs never get confused in a creative tab.

Run:  python tools/gen_spawn_egg_textures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from ev_palette import unique_colors  # noqa: E402
from gen_item_textures import (  # noqa: E402
    EGGS,
    MAX_COLOURS,
    MIN_COLOURS,
    ITEM_DIR,
    PREVIEW_DIR,
    contact_sheet,
    spawn_egg,
)


def main() -> int:
    ITEM_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    gallery = []

    print(f"{'egg':<34} {'size':<9} colours")
    for name, shell, spot, seed in EGGS:
        img = spawn_egg(shell, spot, seed).save(ITEM_DIR / f"{name}.png")
        gallery.append((name, img))
        n = len(unique_colors(img))
        status = "" if MIN_COLOURS <= n <= MAX_COLOURS else "  OUT OF RANGE"
        print(f"{name:<34} {img.size[0]}x{img.size[1]:<6} {n}{status}")
        if status:
            failures.append(f"{name}: {n} colours")

    if "--preview" in sys.argv:
        contact_sheet(gallery, PREVIEW_DIR / "spawn_eggs.png", columns=3)
        print(f"\ncontact sheet written to {PREVIEW_DIR / 'spawn_eggs.png'}")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

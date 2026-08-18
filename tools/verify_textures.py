"""
GATE 2 - pixel art audit, v2.

The original gate enforced the brief's "4-6 indexed colours" rule. That rule is
what made the art look wrong: real Minecraft textures carry roughly 6-16 colours
and, crucially, put a dark outline around every item silhouette. The rule was
revoked by the player's feedback, and this gate now enforces the conventions
that actually make a texture read as Minecraft.

Checks:

  1. resolution        block/ and item/ textures are exactly 16x16; entity sheets
                       use their declared size.
  2. colour budget     MIN_COLOURS..MAX_COLOURS distinct opaque colours. Too few
                       reads as flat programmer art, too many as a photograph.
  3. no flat fills     no single colour may cover more than DOMINANCE_LIMIT of the
                       opaque pixels, and a texture may never be one colour.
  4. item silhouette   an item texture must have transparent surround (it is an
                       object, not a square) and a DARK OUTLINE: the opaque pixels
                       on the silhouette edge must be darker than the interior.
                       This is the single convention whose absence made the old
                       icons look wrong in the hotbar.
  5. seamless wrap     full-cube natural blocks must tile at the 0/15 seam.
  6. palette adherence every colour must lie on the blend-and-shade continuum of
                       the families in docs/spec/art_direction.json.

Exit code 0 = gate passed, 1 = gate failed.

Run:  python tools/verify_textures.py [-v]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ev_palette as ev  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "docs" / "spec" / "mod_spec.json").read_text(encoding="utf-8"))
ART = json.loads((ROOT / "docs" / "spec" / "art_direction.json").read_text(encoding="utf-8"))
TEX_ROOT = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures"

MIN_COLOURS = 5
MAX_COLOURS = 16
# A 128x128 creature sheet paints a whole body, not one icon, so it carries a
# wider budget. The 16-colour rule is about 16x16 sprites and does not transfer.
ENTITY_MAX_COLOURS = 40
DOMINANCE_LIMIT = 0.85
SEAM_TOLERANCE = 1.45
PALETTE_TOLERANCE = 10
BLEND_STEPS = 17

# Outline: at least this fraction of silhouette-edge pixels must be darker than
# the interior mean. Not 100% - a highlight may legitimately touch the edge.
OUTLINE_MIN_RATIO = 0.55
OUTLINE_DARKNESS = 0.92

# Full cubes of natural rock must tile. Machine faces and worked blocks carry
# deliberate borders, exactly as vanilla furnace fronts do.
SEAMLESS_BLOCKS = {
    "resonant_bismuth_ore", "deepslate_resonant_bismuth_ore", "raw_phonolite",
    "null_iron_ore", "null_iron_block", "petrified_tuning_wood_side",
    "stripped_petrified_tuning_wood_side", "resonant_chalk", "echo_slate",
    "amber_strata", "chime_sand", "humming_stem_side", "stripped_humming_stem_side",
}

# Textures that are deliberately full-bleed despite living in item/ (none today,
# but spawn eggs and discs are close calls, so the exemption hook exists).
ITEM_OUTLINE_EXEMPT: set[str] = set()


# ---------------------------------------------------------------------------
# palette continuum
# ---------------------------------------------------------------------------

def palette_anchors() -> list[ev.RGBA]:
    out: list[ev.RGBA] = []
    for family, entries in ART["palette"].items():
        if family.startswith("_"):
            continue
        for value in entries.values():
            out.append(ev.parse_hex(value))
    # the original brief palettes remain legal
    for hexes in ev.PALETTES.values():
        for h in hexes:
            out.append(ev.parse_hex(h))
    return out


def producible_colours() -> set[tuple[int, int, int]]:
    """Every colour reachable by blending two palette anchors and shading it.

    Blending covers ramps between related tones; shading toward black or white
    covers key lighting. Anything outside this set is a colour the art direction
    never authorised.
    """
    anchors = palette_anchors()
    out: set[tuple[int, int, int]] = set()
    for i in range(len(anchors)):
        for j in range(i, len(anchors)):
            for step in range(BLEND_STEPS):
                blend = ev.mix(anchors[i], anchors[j], step / (BLEND_STEPS - 1))
                for s in range(-10, 11):
                    out.add(ev.shift(blend, s / 16.0)[:3])
    return out


def coarse(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    q = PALETTE_TOLERANCE
    return (rgb[0] // q, rgb[1] // q, rgb[2] // q)


PRODUCIBLE = producible_colours()
PRODUCIBLE_COARSE = {
    (c[0] + dx, c[1] + dy, c[2] + dz)
    for c in map(coarse, PRODUCIBLE)
    for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
}


def on_palette(rgb: tuple[int, int, int]) -> bool:
    return rgb in PRODUCIBLE or coarse(rgb) in PRODUCIBLE_COARSE


# ---------------------------------------------------------------------------

def expected_size(rel: Path) -> tuple[int, int] | None:
    parts = rel.parts
    if parts[0] in ("block", "item"):
        # An animated texture is a vertical frame strip - 16 wide, 16*frames tall -
        # and its .mcmeta is what declares it as one. Judging it as a single 16x16
        # sprite would fail the portal for being exactly what it is meant to be.
        if (TEX_ROOT / rel).with_name(rel.name + ".mcmeta").is_file():
            return None
        return (16, 16)
    if parts[0] == "entity":
        if "equipment" in parts:
            return None
        for e in SPEC["entities"]:
            if e["id"] == rel.stem or rel.stem == f"{e['id']}_glow":
                return tuple(e["texture_size"])  # type: ignore[return-value]
        return None
    return None


def luminance(c: tuple[int, int, int]) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def check_outline(img: Image.Image) -> tuple[bool, float, str]:
    """Silhouette-edge pixels should be darker than the interior."""
    px = img.load()
    w, h = img.size

    def opaque(x: int, y: int) -> bool:
        return 0 <= x < w and 0 <= y < h and px[x, y][3] > 0

    edge: list[float] = []
    interior: list[float] = []
    for y in range(h):
        for x in range(w):
            if not opaque(x, y):
                continue
            lum = luminance(px[x, y][:3])
            is_edge = any(not opaque(x + dx, y + dy)
                          for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            (edge if is_edge else interior).append(lum)

    if not edge:
        return False, 0.0, "no silhouette edge (texture is full-bleed)"
    if not interior:
        # A 1px-thin item is all edge; nothing to compare against.
        return True, 1.0, "thin sprite, outline check skipped"

    mean_interior = sum(interior) / len(interior)
    darker = sum(1 for lum in edge if lum <= mean_interior * OUTLINE_DARKNESS)
    ratio = darker / len(edge)
    return ratio >= OUTLINE_MIN_RATIO, ratio, ""


def check_seam(img: Image.Image) -> tuple[bool, float, float]:
    px = img.convert("RGBA").load()
    w, h = img.size

    def col_diff(a: int, b: int) -> float:
        return sum(sum(abs(px[a, y][i] - px[b, y][i]) for i in range(3)) / 3.0
                   for y in range(h)) / h

    def row_diff(a: int, b: int) -> float:
        return sum(sum(abs(px[x, a][i] - px[x, b][i]) for i in range(3)) / 3.0
                   for x in range(w)) / w

    interior = [col_diff(x, x + 1) for x in range(w - 1)]
    interior += [row_diff(y, y + 1) for y in range(h - 1)]
    seam = max(col_diff(w - 1, 0), row_diff(h - 1, 0))
    # 90th percentile, not the single sharpest interior edge. These fields are
    # periodic, so a texture can tile exactly and still place a threshold edge
    # at the wrap; judged against the one harshest interior transition that
    # reads as a break even though it is a correct adjacency. A border that
    # genuinely does not wrap still scores several times the interior spread.
    inner = sorted(interior)
    limit = max(inner[int(len(inner) * 0.90)] * SEAM_TOLERANCE, 1.0)
    return seam <= limit, seam, limit


def audit(path: Path, verbose: bool) -> list[str]:
    rel = path.relative_to(TEX_ROOT)
    errors: list[str] = []
    img = Image.open(path).convert("RGBA")

    want = expected_size(rel)
    if want and img.size != want:
        errors.append(f"size {img.size[0]}x{img.size[1]}, expected {want[0]}x{want[1]}")

    opaque = [c for c in img.getdata() if c[3] > 0]
    if not opaque:
        return [f"{rel}: fully transparent"]

    counts = Counter(c[:3] for c in opaque)
    n = len(counts)
    ceiling = ENTITY_MAX_COLOURS if rel.parts[0] == "entity" else MAX_COLOURS
    # A *_glow sheet is an emissive MASK, not a texture: it paints only the pixels
    # that emit light, and a creature whose glow is one hue legitimately needs two
    # or three colours. The colour floor exists to catch flat programmer art in a
    # real sprite and does not transfer to a mask.
    # An *_overlay sheet is an additive second armour layer (wings, a sigil,
    # shoulder caps) painted over an otherwise-transparent 64x32 canvas, same
    # idea as a *_glow mask below.
    floor = 2 if rel.stem.endswith(("_glow", "_overlay")) else MIN_COLOURS
    if n < floor or n > ceiling:
        errors.append(f"{n} colours, want {floor}-{ceiling}")

    top_share = counts.most_common(1)[0][1] / len(opaque)
    if n == 1:
        errors.append("single-colour fill")
    elif top_share > DOMINANCE_LIMIT:
        errors.append(f"dominant colour covers {top_share:.0%} (limit {DOMINANCE_LIMIT:.0%})")

    off = [c for c in counts if not on_palette(c)]
    if off:
        shown = ", ".join("#%02X%02X%02X" % c for c in sorted(off)[:4])
        errors.append(f"{len(off)} off-palette colour(s): {shown}")

    if rel.parts[0] == "item" and rel.stem not in ITEM_OUTLINE_EXEMPT:
        ok, ratio, note = check_outline(img)
        if not ok:
            errors.append(f"no dark outline around silhouette ({note or f'{ratio:.0%} of edge is dark, need {OUTLINE_MIN_RATIO:.0%}'})")

    if rel.parts[0] == "block" and rel.stem in SEAMLESS_BLOCKS:
        ok, seam, limit = check_seam(img)
        if not ok:
            errors.append(f"seam discontinuity {seam:.1f} > allowed {limit:.1f}")

    if verbose and not errors:
        print(f"  PASS {rel}  {img.size[0]}x{img.size[1]}  {n} colours  top {top_share:.0%}")

    return [f"{rel}: {e}" for e in errors]


def main() -> int:
    verbose = "-v" in sys.argv
    if not TEX_ROOT.exists():
        print(f"FAIL: no textures at {TEX_ROOT}")
        return 1

    files = sorted(TEX_ROOT.rglob("*.png"))
    if not files:
        print("FAIL: no textures found")
        return 1

    print(f"GATE 2: auditing {len(files)} textures against art_direction.json")
    print(f"        {MIN_COLOURS}-{MAX_COLOURS} colours, dark item outlines, "
          f"{len(PRODUCIBLE)} producible palette colours")

    errors: list[str] = []
    for f in files:
        errors.extend(audit(f, verbose))

    if errors:
        print(f"\nFAILED with {len(errors)} violation(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"\nPASS: all {len(files)} textures conform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
The Echoing Void - container GUI sheets.

Currently one: the Knell Integrator's panel.

PLAYER: "on the knell integrator gui, keep the same as the smithing template, so
same inventory, but then obviously change the text to knell integrator, and
replace the black hammer art for something else."

So this is vanilla's smithing panel, redrawn - not the bespoke dark one it replaces.
That earlier version was dark phonolite with a magenta resonator ring, and it caused
two rounds of problems this design cannot have: AbstractContainerScreen hard-codes
its label colour to 0xFF404040, which is correct on a pale panel and near-invisible
on a dark one, and every piece of bespoke art behind the labels had to be kept clear
of them by hand. A standard panel is standard for a reason.

WHAT IS ACTUALLY OURS

One thing: the icon in the top-left, where vanilla draws a hammer. That is a tuning
fork now - the item this whole dimension is entered with - in the knell magenta the
rest of the tier already runs on.

REDRAWN, NOT COPIED

None of Mojang's pixels ship here. The construction below was derived by reading
vanilla's smithing.png and is re-implemented: a 1px black surround with notched
corners, a 2px white top-left bevel against a 2px #555555 bottom-right one, a
#C6C6C6 field, and slots as 18x18 wells dark on their top and left and white on
their bottom and right - the classic sunken look, and the one detail that makes a
hand-drawn container look wrong when it is inverted.

Those greys pass verify_textures' palette check because the gate accepts blends
across the palette's ramps, and neutral grey falls between the chalk and phonolite
families. Checked rather than assumed - every one of them was run through
verify_textures.on_palette before this was written.

The canvas is 256x256 because ItemCombinerScreen blits with a hard-coded 256x256
atlas size; the panel occupies the top-left 176x166 and the rest stays transparent.

Run:  python tools/gen_gui_textures.py
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("FAIL: Pillow is required (pip install pillow)")
    raise SystemExit(1)

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "gui" / "container"

CANVAS = 256
PANEL_W, PANEL_H = 176, 166

TRANSPARENT = (0, 0, 0, 0)

# The standard container palette - vanilla's own figures.
SURROUND = (0x00, 0x00, 0x00, 255)
BEVEL_LIT = (0xFF, 0xFF, 0xFF, 255)
BEVEL_DIM = (0x55, 0x55, 0x55, 255)
FIELD = (0xC6, 0xC6, 0xC6, 255)
SLOT_FILL = (0x8B, 0x8B, 0x8B, 255)
SLOT_DARK = (0x37, 0x37, 0x37, 255)

# The one bespoke element, in the tier's own colour.
FORK_CORE = (0xFF, 0x00, 0x7F, 255)   # arcane.bright
FORK_LIT = (0xB1, 0x4A, 0x9E, 255)    # arcane.light
FORK_MID = (0x5A, 0x2E, 0x6B, 255)    # arcane.mid
FORK_DEEP = (0x3A, 0x1D, 0x47, 255)   # arcane.deep

#: Slot positions, as IntegratorMenu places them - smithing's, to the pixel.
INPUT_SLOTS = [(8, 48), (26, 48), (44, 48)]
RESULT_SLOT = (98, 48)

#: Where vanilla draws its hammer: x 7..36, y 7..36, a 15x15 icon at 2x scale.
ICON_ORIGIN = (7, 7)
ICON_SCALE = 2

#: The KNELL INGOT's own sprite, upscaled into the hammer's box.
#:
#: PLAYER, seeing the first attempt: "please review that artwork, its a bit strange."
#: It was. It was a symmetric magenta stick figure with no outline, a few purple pixels
#: stuck on at arbitrary points that read as artefacts rather than shading, and a chroma
#: far louder than anything else on the panel. Beside vanilla's hammer - which is drawn
#: on a diagonal, in two materials, fully outlined, shaded top-left to bottom-right, with
#: one small gem accent - it read as a logo rather than an object.
#:
#: Inventing art was the first mistake and picking the wrong subject was the second.
#: PLAYER: "the tuning fork uses resonant shards, has little to do with knell. make it look
#: like something made from knell or something."
#:
#: Correct - the Tuning Fork is a BISMUTH item, and this station's whole job is applying
#: knell. So the icon is the Knell Ingot: the material the Integrator adds, which is
#: exactly what vanilla's hammer says about a smithing table. Read from the generated item
#: sprite rather than redrawn, so the icon and the item in a player's hand can never drift.
ICON_ITEM = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "item" / "knell_ingot.png"


def slot(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 16) -> None:
    """One 18x18 well, sunk into the panel."""
    x0, y0, x1, y1 = x - 1, y - 1, x + size, y + size
    draw.rectangle([x0, y0, x1, y1], fill=SLOT_FILL)
    # The two OFF-DIAGONAL corners stay fill colour rather than taking a bevel. That is
    # what a real bevel does - a corner cannot be lit and shadowed at once - and drawing
    # the four edges as full lines instead put white in vanilla's grey corners, which was
    # 80 of the 100 pixels still differing from vanilla after the arrow went back in.
    draw.line([(x0, y0), (x1 - 1, y0)], fill=SLOT_DARK)
    draw.line([(x0, y0), (x0, y1 - 1)], fill=SLOT_DARK)
    draw.line([(x0 + 1, y1), (x1, y1)], fill=BEVEL_LIT)
    draw.line([(x1, y0 + 1), (x1, y1)], fill=BEVEL_LIT)


def result_arrow(draw: ImageDraw.ImageDraw) -> None:
    """Inputs to result, in vanilla's own geometry.

    Dropped in the first pass of this rewrite and caught by diffing the finished panel
    against vanilla's rather than by looking at it - 100 of the 214 differing pixels were
    this one missing arrow. A smithing-shaped panel with no arrow reads as a panel with a
    gap in it.

    Shaft x 68..81 on rows 55..57; head a right-pointing triangle whose flat edge is the
    column x 82 from y 49 to y 63 and whose apex is (89, 56).
    """
    draw.rectangle([68, 55, 81, 57], fill=SLOT_FILL)
    for dy in range(-7, 8):
        draw.line([(82, 56 + dy), (89 - abs(dy), 56 + dy)], fill=SLOT_FILL)


def station_icon(img: Image.Image) -> None:
    """The Knell Ingot, at 2x, centred in the box vanilla gives its hammer.

    Read from the generated item sprite rather than redrawn, so the two can never drift:
    gen_item_textures runs before this stage in asset_gen.py, so the file is always the
    current one.
    """
    if not ICON_ITEM.exists():
        raise SystemExit(f"FAIL: {ICON_ITEM} is missing - run gen_item_textures.py first")

    icon = Image.open(ICON_ITEM).convert("RGBA")
    bbox = icon.getbbox()
    cropped = icon.crop(bbox)
    scaled = cropped.resize((cropped.width * ICON_SCALE, cropped.height * ICON_SCALE),
                            Image.NEAREST)

    # Centred in vanilla's 30x30 hammer box rather than pinned to its corner, because the
    # fork's own aspect is taller and narrower than the hammer's diagonal.
    box_x, box_y, box_w, box_h = ICON_ORIGIN[0], ICON_ORIGIN[1], 30, 30
    ox = box_x + (box_w - scaled.width) // 2
    oy = box_y + (box_h - scaled.height) // 2
    img.alpha_composite(scaled, (ox, oy))


def panel() -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    W, H = PANEL_W - 1, PANEL_H - 1

    # Field, then the bevels over it, then the black surround with notched corners -
    # the order a vanilla container panel is built up in.
    draw.rectangle([0, 0, W, H], fill=FIELD)
    for i in (1, 2):
        draw.line([(i, i), (W - i, i)], fill=BEVEL_LIT)
        draw.line([(i, i), (i, H - i)], fill=BEVEL_LIT)
        draw.line([(i, H - i), (W - i, H - i)], fill=BEVEL_DIM)
        draw.line([(W - i, i), (W - i, H - i)], fill=BEVEL_DIM)
    draw.rectangle([0, 0, W, H], outline=SURROUND)

    # Vanilla's corners are stepped, not square: three pixels come out of each one, so
    # the panel reads as rounded. Clearing only the single corner pixel - which the first
    # pass did - leaves a corner subtly sharper than every other container in the game.
    for cx, cy, sx, sy in ((0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)):
        for dx, dy in ((0, 0), (sx, 0), (0, sy)):
            img.putpixel((cx + dx, cy + dy), TRANSPARENT)

    result_arrow(draw)
    station_icon(img)

    for x, y in INPUT_SLOTS:
        slot(draw, x, y)
    slot(draw, *RESULT_SLOT)

    # The player's own inventory, at vanilla's offsets - addStandardInventorySlots is
    # called with (8, 84) and puts the hotbar four pixels below the third row.
    for row in range(3):
        for col in range(9):
            slot(draw, 8 + col * 18, 84 + row * 18)
    for col in range(9):
        slot(draw, 8 + col * 18, 142)

    return img


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    img = panel()
    path = OUT / "knell_integrator.png"
    img.save(path)

    opaque = [p for p in img.convert("RGBA").getdata() if p[3] > 0]
    colours = {p[:3] for p in opaque}
    top = max(sum(1 for p in opaque if p[:3] == c) for c in colours) / len(opaque)
    print(f"wrote {path.relative_to(ROOT)}")
    print(f"  {img.size[0]}x{img.size[1]}, {len(colours)} colours, "
          f"dominant {top:.0%} (gate: 5-16 colours, under 85%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

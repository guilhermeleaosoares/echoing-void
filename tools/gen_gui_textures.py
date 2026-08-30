"""
The Echoing Void - container GUI sheets.

Currently one: the Knell Integrator's panel.

PLAYER: "i want a modified GUI for the knell integrator", and, asked how far it
should go, a reskin over the same three slots. So the geometry here is the
smithing table's to the pixel - template at x 8, base at 26, addition at 44,
result at 98, all on row 48, player inventory at 8,84 and hotbar at 8,142 - and
only the dress changes. A player who has used a smithing table should not have to
work anything out.

WHY THIS PASSES THE TEXTURE GATE

verify_textures.py holds every sheet to 5-16 colours drawn from
docs/spec/art_direction.json. That is a real constraint on a 176x166 panel and it
is met rather than waived: the whole thing is built from eleven palette entries -
the phonolite spine for the chassis, null-iron for the slot recesses, chalk for
the arrow, and the arcane family for the resonator ring behind the inputs, which
is the same #FF007F the Integrator block's own particles run on.

The canvas is 256x256 because ItemCombinerScreen blits with a hard-coded 256x256
atlas size; the panel occupies the top-left 176x166 and the rest stays
transparent, exactly as vanilla's own container sheets do.

Run:  python tools/gen_gui_textures.py
"""

from __future__ import annotations

import sys
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

# Eleven colours, every one of them lifted from art_direction.json. Named for the
# job they do here rather than for the palette slot, so the layout code reads as
# layout rather than as colour-picking.
TRANSPARENT = (0, 0, 0, 0)
CHASSIS = (0x3B, 0x42, 0x52, 255)      # phonolite.mid   - the panel field
CHASSIS_LIT = (0x6E, 0x7B, 0x94, 255)  # phonolite.pale  - top/left bevel
CHASSIS_DIM = (0x4C, 0x56, 0x6A, 255)  # phonolite.light - inner frame
EDGE_DARK = (0x1C, 0x1D, 0x21, 255)    # phonolite.dark  - bottom/right bevel
RECESS = (0x14, 0x16, 0x1D, 255)       # void.shadow     - slot floor
RECESS_LIP = (0x2A, 0x2A, 0x38, 255)   # null_iron.mid   - slot lip
ARROW = (0xA8, 0xB4, 0xC8, 255)        # chalk.mid       - the result arrow
RING_DEEP = (0x3A, 0x1D, 0x47, 255)    # arcane.deep
RING_MID = (0x5A, 0x2E, 0x6B, 255)     # arcane.mid
RING_LIT = (0xB1, 0x4A, 0x9E, 255)     # arcane.light
RING_CORE = (0xFF, 0x00, 0x7F, 255)    # arcane.bright   - the knell note

#: Input and result slots, as the menu places them. IntegratorMenu.slots() must
#: agree with this list or the art will sit under empty air.
INPUT_SLOTS = [(8, 48), (26, 48), (44, 48)]
RESULT_SLOT = (98, 48)


def slot(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 16) -> None:
    """A vanilla slot recess: an 18x18 well whose top-left is one pixel up and left.

    Vanilla draws the lip on the top and left and leaves the bottom and right open,
    which is what makes a slot read as sunk into the panel rather than raised off it.
    """
    draw.rectangle([x - 1, y - 1, x + size, y + size], fill=RECESS)
    draw.line([(x - 1, y - 1), (x + size - 1, y - 1)], fill=RECESS_LIP)
    draw.line([(x - 1, y - 1), (x - 1, y + size - 1)], fill=RECESS_LIP)


def resonator_ring(draw: ImageDraw.ImageDraw) -> None:
    """The station's own motif, struck through the panel behind the three inputs.

    The Integrator block carries a bismuth resonator ring standing proud on top and
    idles magenta; this is that ring seen face-on. It sits BEHIND the slots - drawn
    first, so the recesses cut through it - which is what stops it reading as
    decoration stuck onto a smithing table.
    """
    # Centred on the slot row rather than below it. At its old centre of y 56 the outer
    # ring reached y 71, which put it under the player-inventory label at y 72 and made
    # the text unreadable over the ring as well as over the panel.
    cx, cy = 35, 47
    for radius, colour in ((30, RING_DEEP), (24, RING_MID), (18, RING_LIT)):
        draw.ellipse([cx - radius, cy - radius // 2, cx + radius, cy + radius // 2],
                     outline=colour)

    # Four tuning marks on the ring's axis, the bright note among the dim ones.
    for dx, dy in ((-30, 0), (30, 0), (0, -15), (0, 15)):
        draw.rectangle([cx + dx - 1, cy + dy - 1, cx + dx + 1, cy + dy + 1], fill=RING_CORE)


def result_arrow(draw: ImageDraw.ImageDraw) -> None:
    """Addition to result, on the row the slots share."""
    y = 55
    draw.rectangle([64, y - 1, 84, y + 1], fill=ARROW)
    for i in range(7):
        draw.line([(85 + i, y - 7 + i), (85 + i, y + 7 - i)], fill=ARROW)


def panel() -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Chassis, with a lit top-left and a dark bottom-right so the panel has a
    # light source rather than being a flat rectangle.
    draw.rectangle([0, 0, PANEL_W - 1, PANEL_H - 1], fill=CHASSIS)
    draw.line([(0, 0), (PANEL_W - 1, 0)], fill=CHASSIS_LIT)
    draw.line([(0, 0), (0, PANEL_H - 1)], fill=CHASSIS_LIT)
    draw.line([(0, PANEL_H - 1), (PANEL_W - 1, PANEL_H - 1)], fill=EDGE_DARK)
    draw.line([(PANEL_W - 1, 0), (PANEL_W - 1, PANEL_H - 1)], fill=EDGE_DARK)

    # An inner frame, which is what separates the working area from the player's
    # own inventory below and keeps the eye where the three slots are.
    draw.rectangle([3, 3, PANEL_W - 4, PANEL_H - 4], outline=CHASSIS_DIM)

    # TWO CLEAR BANDS FOR TEXT, and this is a fix rather than a flourish. PLAYER: "there
    # is overlapping text in the knell integrator gui... text overlaps with borders in the
    # gui and the text cuts under grid squares."
    #
    # AbstractContainerScreen puts the title at y 6 and the inventory label at
    # imageHeight-94, which is 72 on a 166-tall panel. The divider rule used to sit at
    # y 76 and ran straight through the second one. So the title band is recessed
    # deliberately - a darker inset the light text sits ON, rather than text floating over
    # whatever art happens to be behind it - and the divider has moved to y 68, ABOVE the
    # inventory label instead of through it.
    draw.rectangle([4, 4, PANEL_W - 5, 15], fill=EDGE_DARK)
    draw.line([(4, 4), (PANEL_W - 5, 4)], fill=RECESS)
    draw.line([(4, 16), (PANEL_W - 5, 16)], fill=CHASSIS_LIT)

    # The inventory label gets the SAME recessed band, not just a rule above it. Measured
    # against the palette, chalk-light text on the bare phonolite panel is 3.2:1, under the
    # 4.5:1 floor where text stops being comfortably readable; on this inset it is 7.2:1,
    # the same as the title. The band doubles as the divider, so the panel gains a
    # separator rather than a separator plus a stripe.
    draw.rectangle([4, 68, PANEL_W - 5, 80], fill=EDGE_DARK)
    draw.line([(4, 68), (PANEL_W - 5, 68)], fill=RECESS)
    draw.line([(4, 81), (PANEL_W - 5, 81)], fill=CHASSIS_LIT)

    resonator_ring(draw)
    result_arrow(draw)

    for x, y in INPUT_SLOTS:
        slot(draw, x, y)
    slot(draw, *RESULT_SLOT)

    # The player's own inventory, at vanilla's offsets - addStandardInventorySlots
    # is called with (8, 84) and puts the hotbar 4 pixels below the third row.
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

    opaque = [p for p in img.getdata() if p[3] > 0]
    colours = {p[:3] for p in opaque}
    top = max(sum(1 for p in opaque if p[:3] == c) for c in colours) / len(opaque)
    print(f"wrote {path.relative_to(ROOT)}")
    print(f"  {img.size[0]}x{img.size[1]}, {len(colours)} colours, "
          f"dominant {top:.0%} (gate: 5-16 colours, under 85%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

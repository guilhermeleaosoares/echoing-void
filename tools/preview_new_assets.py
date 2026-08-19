"""
Contact sheets for everything this round added, at a size a person can judge.

Three sheets, because the three things are judged differently:

  build/preview/hushwater.png   the fluid: a strip of the still animation, a
                                strip of the flow animation, the glass overlay
                                and the bucket. An animation has to be seen as
                                FRAMES side by side or the only thing you can
                                say about it is what colour it is.
  build/preview/void_farming.png every crop at every growth stage, in stage
                                order, plus the soil and the item icons. Growth
                                stages are a sequence and only read as one when
                                they are laid out as one.
  build/preview/farm_pieces.png isometric renders of the two new encampment
                                pieces, via tools/render_structure_preview.py.

Run:  python tools/preview_new_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

TEX = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures"
OUT = ROOT / "build" / "preview"

SCALE = 6
PAD = 10
LABEL = 14
BG = (32, 34, 40)
INK = (200, 210, 225)


def _font():
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=12)
    except TypeError:
        return ImageFont.load_default()


def frames(path: Path, width: int) -> list[Image.Image]:
    """Split an animation strip into its square frames."""
    img = Image.open(path).convert("RGBA")
    n = img.height // width
    return [img.crop((0, i * width, width, (i + 1) * width)) for i in range(n)]


def sheet(rows: list[tuple[str, list[Image.Image]]], path: Path, title: str) -> None:
    font = _font()
    cell = max(im.width for _, ims in rows for im in ims) * SCALE
    cols = max(len(ims) for _, ims in rows)
    w = PAD * 2 + cols * (cell + PAD)
    h = PAD * 2 + 18 + sum(cell + LABEL + PAD for _, _ in rows)
    out = Image.new("RGBA", (w, h), BG)
    draw = ImageDraw.Draw(out)
    draw.text((PAD, PAD - 2), title, fill=INK, font=font)

    y = PAD + 18
    for label, images in rows:
        draw.text((PAD, y), label, fill=INK, font=font)
        y += LABEL
        x = PAD
        for im in images:
            big = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)
            # Checkerboard behind, so alpha is visible rather than guessed at.
            tile = Image.new("RGBA", big.size, (58, 60, 68, 255))
            for cx in range(0, big.width, 16):
                for cy in range(0, big.height, 16):
                    if ((cx // 16) + (cy // 16)) % 2:
                        tile.paste((46, 48, 56, 255), (cx, cy, min(cx + 16, big.width),
                                                       min(cy + 16, big.height)))
            tile.alpha_composite(big)
            out.paste(tile, (x, y))
            x += cell + PAD
        y += cell + PAD
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    print(f"  {path.relative_to(ROOT)}  {out.width}x{out.height}")


def load(rel: str) -> Image.Image:
    return Image.open(TEX / rel).convert("RGBA")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    still = frames(TEX / "block" / "hushwater_still.png", 16)
    flow = frames(TEX / "block" / "hushwater_flow.png", 32)
    sheet([
        ("still, frames 1-8 of 16 (frametime 3)", still[:8]),
        ("flow, frames 1-8 of 16 (frametime 2)", flow[:8]),
        ("overlay against glass, and the bucket",
         [load("block/hushwater_overlay.png"), load("item/hushwater_bucket.png")]),
    ], OUT / "hushwater.png", "HUSHWATER - the Hollow Horizon's fluid")

    sheet([
        ("resonant wheat, stages 0-7",
         [load(f"block/resonant_wheat_stage{i}.png") for i in range(8)]),
        ("chime roots, stages 0-3   |   void tubers, stages 0-3",
         [load(f"block/chime_roots_stage{i}.png") for i in range(4)]
         + [load(f"block/void_tubers_stage{i}.png") for i in range(4)]),
        ("echo gourd side/top, stem, attached stem, farmland dry/moist",
         [load("block/echo_gourd_side.png"), load("block/echo_gourd_top.png"),
          load("block/echo_gourd_stem.png"), load("block/attached_echo_gourd_stem.png"),
          load("block/void_farmland.png"), load("block/void_farmland_moist.png")]),
        ("grain, wheat seeds, gourd seeds, chime root, void tuber, resonant bread",
         [load("item/resonant_grain.png"), load("item/resonant_wheat_seeds.png"),
          load("item/echo_gourd_seeds.png"), load("item/chime_root.png"),
          load("item/void_tuber.png"), load("item/resonant_bread.png")]),
    ], OUT / "void_farming.png", "VOID FARMING - crops, soil and food")

    # The structure renders come from the existing isometric renderer rather
    # than being reimplemented here.
    import render_structure_preview as rsp
    made = []
    for piece in ("tuner_encampment/camp_field", "tuner_encampment/camp_granary",
                  "outpost_of_the_tuners/forge_hall",
                  "outpost_of_the_tuners/tuner_lodge"):
        result = rsp.render(rsp.STRUCT_DIR / f"{piece}.nbt")
        if result:
            made.append(result)
    if made:
        rsp.sheet(made, OUT / "new_pieces.png")
        print(f"  {(OUT / 'new_pieces.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

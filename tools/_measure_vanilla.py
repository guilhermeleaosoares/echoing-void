"""Throwaway measurement harness: quantify vanilla texture conventions.

Not part of the build. Prints colour counts, value histograms, alpha-gap
statistics and character-grid renderings of vanilla blocks so our own
generators can imitate the conventions rather than guess at them.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from PIL import Image

VAN = Path(r"C:\Projects\mcref-26.2\assets\assets\minecraft\textures\block")


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def analyse(name: str, grid: bool = False, top: int = 12):
    p = VAN / f"{name}.png"
    img = Image.open(p).convert("RGBA")
    w, h = img.size
    px = img.load()
    # animated textures are Nx16 strips: only look at the first frame
    frame_h = w if h > w else h
    data = [px[x, y] for y in range(frame_h) for x in range(w)]
    opaque = [c for c in data if c[3] > 0]
    counts = Counter(opaque)
    n_alpha0 = sum(1 for c in data if c[3] == 0)
    print(f"\n=== {name}  size={w}x{h} frame={w}x{frame_h} ===")
    print(f"  distinct opaque colours: {len(counts)}   fully transparent px: "
          f"{n_alpha0}/{len(data)} ({n_alpha0/len(data):.0%})")
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    for c, n in ordered[:top]:
        print(f"    #{c[0]:02X}{c[1]:02X}{c[2]:02X} a{c[3]:<3} x{n:<4} "
              f"({n/len(data):5.1%})  lum={lum(c):6.1f}")
    if len(ordered) > top:
        print(f"    ... {len(ordered)-top} more")
    if opaque:
        ls = sorted({round(lum(c)) for c in counts})
        print(f"  luminance span: {ls[0]} .. {ls[-1]}  (delta {ls[-1]-ls[0]})")
    if grid:
        # map each colour to a character ranked by luminance
        uniq = sorted(counts, key=lum)
        chars = " .:-=+*#%@$&WM0123456789ABCDEFGHIJK"
        cmap = {}
        for i, c in enumerate(uniq):
            cmap[c] = chars[min(len(chars) - 1, int(i * len(chars) / max(1, len(uniq))))]
        print("  grid (dark->light = ' '->'K',  '_' = alpha 0):")
        print("      " + "".join(f"{x%10}" for x in range(w)))
        for y in range(frame_h):
            row = "".join("_" if px[x, y][3] == 0 else cmap[px[x, y]] for x in range(w))
            print(f"   {y:2} {row}")
    return img


def alpha_clumps(name: str):
    """How the alpha gaps in leaves are distributed - clumped or scattered?"""
    img = Image.open(VAN / f"{name}.png").convert("RGBA")
    w, h = img.size
    fh = min(w, h)
    px = img.load()
    seen = set()
    sizes = []
    for y in range(fh):
        for x in range(w):
            if px[x, y][3] != 0 or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            n = 0
            while stack:
                cx, cy = stack.pop()
                n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < fh and (nx, ny) not in seen \
                            and px[nx, ny][3] == 0:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            sizes.append(n)
    print(f"  {name}: {len(sizes)} alpha clumps, sizes {sorted(sizes, reverse=True)}")


def hue_spread(name: str):
    import colorsys
    img = Image.open(VAN / f"{name}.png").convert("RGBA")
    w, h = img.size
    fh = min(w, h)
    px = img.load()
    hs = []
    for y in range(fh):
        for x in range(w):
            c = px[x, y]
            if c[3] == 0:
                continue
            hh, ll, ss = colorsys.rgb_to_hls(c[0]/255, c[1]/255, c[2]/255)
            hs.append((hh * 360, ss, ll))
    if not hs:
        return
    print(f"  {name}: hue {min(h_ for h_,_,_ in hs):.0f}..{max(h_ for h_,_,_ in hs):.0f} "
          f"sat {min(s for _,s,_ in hs):.2f}..{max(s for _,s,_ in hs):.2f} "
          f"lit {min(l for _,_,l in hs):.2f}..{max(l for _,_,l in hs):.2f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "ores"
    if mode == "ores":
        for n in ("stone", "coal_ore", "gold_ore", "diamond_ore", "deepslate",
                  "deepslate_gold_ore"):
            analyse(n, grid=(n in ("coal_ore", "gold_ore", "deepslate_gold_ore", "stone")))
    elif mode == "leaves":
        for n in ("oak_leaves", "azalea_leaves", "cherry_leaves", "flowering_azalea_leaves"):
            analyse(n, grid=(n in ("oak_leaves", "azalea_leaves")))
            alpha_clumps(n)
            hue_spread(n)
    elif mode == "stones":
        for n in ("calcite", "tuff", "deepslate", "sand", "moss_block",
                  "pale_moss_block", "sandstone", "polished_deepslate",
                  "deepslate_bricks", "stone_bricks", "polished_tuff"):
            analyse(n, grid=(n in ("calcite", "sand", "moss_block", "tuff")))
    elif mode == "plants":
        for n in ("short_grass", "nether_sprouts", "glow_lichen", "amethyst_cluster",
                  "large_amethyst_bud", "spore_blossom", "lantern", "sea_lantern",
                  "budding_amethyst", "amethyst_block"):
            analyse(n, grid=(n in ("short_grass", "amethyst_cluster", "lantern",
                                   "glow_lichen", "nether_sprouts")))
    elif mode == "wood":
        for n in ("cherry_log", "warped_stem", "warped_stem_top", "stripped_warped_stem",
                  "crimson_stem", "oak_log", "oak_log_top"):
            analyse(n, grid=(n in ("warped_stem", "warped_stem_top", "oak_log")))
    else:
        for n in sys.argv[1:]:
            analyse(n, grid=True)

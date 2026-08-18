"""
Vanilla item silhouettes, measured once and baked in.

PLAYER: "make the raw materials and ingots (null iron and knell) look closer to
vanilla ingots and raw materials, could their shapes be more similar?"

An ingot is one of the most recognisable shapes in the game, and a player reads
it by outline before colour. Our procedural blobs were the right palette in the
wrong silhouette - 95 painted pixels against vanilla's 135, narrower, and with a
stray tail at the bottom right that vanilla does not have.

So the form comes from vanilla and only the colour is ours. Each table below is
the real 26.2 sprite reduced to two things:

  '.'   transparent
  '0'-'9'  relative luminance within that sprite, 0 darkest, 9 brightest

That captures both the outline AND the internal structure - on the ingot, the
bright top face, the one-pixel specular along the crease, and the darker front
face below and to the right. Painting our own material ramp through those levels
keeps vanilla's reading while leaving the material unmistakably ours, which is
the same trick netherite plays against iron.

Measured with:
    luminance = 0.2126R + 0.7152G + 0.0722B, normalised per sprite across its
    own opaque pixels only.

Regenerate by reading the sprite out of C:/Projects/mcref-26.2/assets/assets/
minecraft/textures/item/. Do not hand-edit.
"""

from __future__ import annotations

# iron_ingot.png - 135 opaque px, luminance 53-255
INGOT = (
    "................",
    "................",
    "..........22....",
    ".......222553...",
    "....2225888853..",
    ".22258888888853.",
    "2988888888889983",
    "2598888889998350",
    "2559889998333350",
    "2555998333335550",
    "235583333355300.",
    ".235833333000...",
    "..23531000......",
    "...2200.........",
    "................",
    "................",
)

# raw_iron.png - 168 opaque px, luminance 53-246
RAW = (
    "................",
    "..11111.........",
    ".169976111......",
    ".199999796111...",
    "17999999999761..",
    "176799997976761.",
    "074476443346461.",
    "063464443113441.",
    "063364431111130.",
    "043331111997440.",
    "0443311177796430",
    ".043330047763110",
    "..0000..04443110",
    ".........044110.",
    "..........0000..",
    "................",
)


def levels(form: tuple[str, ...], lo: float = 0.26, hi: float = 1.0
           ) -> dict[tuple[int, int], float]:
    """Map a form table to {(x, y): tone level} over the caller's own ramp.

    `lo` and `hi` are where this material's darkest and brightest tones sit, so
    a material with little internal contrast (Null-Iron) and one with a lot
    (Knell) can both use the same silhouette without either going flat or
    blowing out.
    """
    out: dict[tuple[int, int], float] = {}
    for y, row in enumerate(form):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            out[(x, y)] = lo + (hi - lo) * (int(ch) / 9.0)
    return out


def body(form: tuple[str, ...]) -> set[tuple[int, int]]:
    """Just the silhouette, for callers that do their own shading."""
    return {(x, y) for y, row in enumerate(form)
            for x, ch in enumerate(row) if ch != "."}


def top_face(form: tuple[str, ...], threshold: int = 6) -> set[tuple[int, int]]:
    """The lit upper surface - where an accent mark reads as struck into metal.

    Anything at or above `threshold` on the sprite's own luminance scale is
    facing the light, which on the ingot is exactly the top plane and the
    specular crease.
    """
    return {(x, y) for y, row in enumerate(form)
            for x, ch in enumerate(row) if ch != "." and int(ch) >= threshold}


# ---------------------------------------------------------------------------
# Tool forms
#
# PLAYER: "the axe shovel and hoe look nothing like those tools when compared
# to the vanilla and knell tools."
#
# They did not, and hand-authored polygons were never going to get there: an
# axe reads as an axe because of a specific bit shape sitting a specific way on
# the haft, and at 16x16 there is no room to approximate it.
#
# So these are the real iron tools, measured, in the same two-part encoding as
# the ingots above but with one extra channel. Vanilla draws every tool as a
# warm wooden haft against a cool metal head, and that split is measurable
# rather than guessed: a haft pixel has R - B > 24, a head pixel does not.
#
#   '.'        transparent
#   '0'-'9'    head - relative luminance, 0 darkest
#   'a'-'j'    haft - relative luminance, 'a' darkest
#
# Painting our own two materials through those two regions gives a tool that
# reads correctly at a glance and is still unmistakably ours, because every
# colour is still ours. Measured from
# C:/Projects/mcref-26.2/assets/assets/minecraft/textures/item/iron_*.png.
# ---------------------------------------------------------------------------

AXE = (
    "................",
    ".........11.....",
    "........1991....",
    ".......19781....",
    "......19777bc...",
    "......098757a...",
    ".......00b7570..",
    "........bca770..",
    ".......bda.00...",
    "......bca.......",
    ".....bca........",
    "....bda.........",
    "...bca..........",
    "..bda...........",
    "..aa............",
    "................",
)

SHOVEL = (
    "................",
    "................",
    "...........110..",
    "..........19970.",
    ".........198790.",
    "........1987890.",
    ".........b7890..",
    "........bda90...",
    ".......bda.0....",
    "......bca.......",
    ".....bda........",
    "....bca.........",
    "..bbda..........",
    "..bda...........",
    "...aa...........",
    "................",
)

HOE = (
    "................",
    ".......111......",
    "......19881.....",
    ".......00781bc..",
    ".........077d0..",
    "..........b870..",
    ".........bc00...",
    "........bd0.....",
    ".......bc0......",
    "......bd0.......",
    ".....bc0........",
    "....bd0.........",
    "...bc0..........",
    "..bd0...........",
    "..00............",
    "................",
)

SWORD = (
    ".............111",
    "............1990",
    "...........19790",
    "..........19790.",
    ".........19780..",
    "........19780...",
    "..11...18780....",
    "..131.18780.....",
    "...1508580......",
    "...155380.......",
    "....1310........",
    "...bc0110.......",
    "..bda.0010......",
    "11ca....00......",
    "130.............",
    "000.............",
)

PICKAXE = (
    "................",
    "................",
    "......11111.....",
    ".....1987781bc..",
    "......100077da..",
    "..........b870..",
    ".........bca780.",
    "........bda.070.",
    ".......bca..070.",
    "......bda...080.",
    ".....bca....090.",
    "....bda......0..",
    "...bca..........",
    "..bda...........",
    "..aa............",
    "................",
)


def tool_levels(form: tuple[str, ...],
                head_lo: float = 0.24, head_hi: float = 1.0,
                haft_lo: float = 0.28, haft_hi: float = 0.86):
    """Split a tool form into (head, haft) level maps.

    Returned as two {(x, y): level} dicts so a caller can paint each with a
    different material - which is the whole point of the split, and the one
    vanilla convention whose absence makes a dark head on a dark haft read as
    a single undifferentiated stick in the hotbar.
    """
    head: dict[tuple[int, int], float] = {}
    haft: dict[tuple[int, int], float] = {}
    for y, row in enumerate(form):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            if ch.isdigit():
                head[(x, y)] = head_lo + (head_hi - head_lo) * (int(ch) / 9.0)
            else:
                haft[(x, y)] = haft_lo + (haft_hi - haft_lo) * ((ord(ch) - 97) / 9.0)
    return head, haft

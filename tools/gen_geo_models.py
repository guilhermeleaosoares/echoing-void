"""
The Echoing Void - Blockbench (.geo.json) geometry generator.

Writes the three creature models. The brief for this pass was that the mobs
"are all just grey blocks" and need to be larger, livelier and more commanding,
so every creature here was re-proportioned rather than retextured:

  echo_weaver      3.7-block leg span, arched spider legs three segments long,
                   a two-part body with a raised dorsal plate and four tall
                   acoustic crests that carry the ambush telegraph
  strata_golem     a tower: heavy low chassis on short thick legs, slab
                   shoulders overhanging the body, a jawed head slung forward,
                   and three clusters of crystal spires reaching 3.7 blocks up
  resonance_wraith much wider than tall - a bright layered core inside a
                   translucent shell, a wide resonance disc, and four two-layer
                   ribbon bands reaching 2.1 blocks out on each side

BONE NAMES ARE A CONTRACT. tools/gen_entity_models.py resolves animation fields
by bone name (crest_1..4, leg_l1_femur, cluster_fore, ribbon_2_mid, ...), so the
names below cannot be renamed without editing that generator. Extra bones and
extra cubes on an existing bone are free; renames are not.

UV ALLOCATION
-------------
UVs are allocated by a shelf packer rather than hand-typed, and allocation is
DEFERRED to finalise(): every cube is recorded first, then the distinct
rectangles are packed tallest-first. Packing in call order wastes most of a
sheet on a model whose first cube happens to be short, and it makes the layout
depend on the order the builder happens to write its bones in.

The pack key is (size, group), not size alone. Two cubes of the same size in the
same material group deliberately share one rectangle - that is how eight legs
fit on one sheet - but a crystal spire that happens to be the same size as a leg
segment gets its own rectangle, because it has to be painted as crystal.

tools/gen_entity_textures.py imports BUILDERS from this module and paints the
sheets straight from the allocation, so the texture and the geometry cannot
drift apart.

Box UV unwrap for a cube of size (w, h, d) occupies (2d + 2w) x (d + h) pixels.

Run:  python tools/gen_geo_models.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "geo"

Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# UV allocation
# ---------------------------------------------------------------------------

class UvAtlas:
    """Shelf packer that assigns one UV origin per (cube size, material group)."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.placement: dict[tuple[tuple[int, int, int], str], tuple[int, int]] = {}
        self.rects: list[tuple[int, int, int, int]] = []
        self._shelves: list[dict[str, int]] = []
        self._next_y = 0

    @staticmethod
    def footprint(size: Vec3) -> tuple[int, int]:
        w, h, d = (int(round(v)) for v in size)
        return (2 * d + 2 * w, d + h)

    def pack(self, keys: list[tuple[tuple[int, int, int], str]]) -> None:
        """First-fit-decreasing across shelves.

        Tallest rectangle first, and each one is offered to every shelf already
        open before a new one is started. Next-fit (only ever filling the
        newest shelf) strands the tail of every shelf behind it, which on these
        models was the difference between fitting in 128x128 and not.
        """
        ordered = sorted(keys, key=lambda k: (-self.footprint(k[0])[1],
                                              -self.footprint(k[0])[0], k))
        for key in ordered:
            self._place(key)

    def _place(self, key: tuple[tuple[int, int, int], str]) -> None:
        fw, fh = self.footprint(key[0])
        if fw > self.width:
            raise ValueError(
                f"cube {key} needs {fw}px of UV width, atlas is {self.width}px")

        for shelf in self._shelves:
            if shelf["x"] + fw <= self.width and fh <= shelf["h"]:
                self._commit(key, shelf["x"], shelf["y"], fw, fh)
                shelf["x"] += fw
                return

        y = self._next_y
        if y + fh > self.height:
            raise ValueError(
                f"UV atlas overflow: {key} ({fw}x{fh}) does not fit in "
                f"{self.width}x{self.height} (next shelf y={y})")
        self._shelves.append({"y": y, "h": fh, "x": fw})
        self._next_y = y + fh
        self._commit(key, 0, y, fw, fh)

    def _commit(self, key, x: int, y: int, fw: int, fh: int) -> None:
        self.placement[key] = (x, y)
        self.rects.append((x, y, fw, fh))

    def used_pixels(self) -> int:
        return sum(w * h for _, _, w, h in self.rects)


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------

class Model:
    """A bedrock geometry under construction.

    Cubes are recorded with a material `group`; `finalise()` packs the UVs and
    stamps them back onto the recorded cube dicts.
    """

    def __init__(self, identifier: str, tex_w: int, tex_h: int):
        self.identifier = identifier
        self.tex_w = tex_w
        self.tex_h = tex_h
        self.atlas = UvAtlas(tex_w, tex_h)
        self.bones: list[dict] = []
        # (cube dict, size key, group) in creation order
        self._pending: list[tuple[dict, tuple[int, int, int], str]] = []
        self._finalised = False

    def bone(self, name: str, pivot: Vec3, parent: str | None = None,
             rotation: Vec3 | None = None) -> dict:
        b: dict = {"name": name, "pivot": [round(v, 2) for v in pivot]}
        if parent:
            b["parent"] = parent
        if rotation:
            b["rotation"] = [round(v, 2) for v in rotation]
        b["cubes"] = []
        self.bones.append(b)
        return b

    def cube(self, bone: dict, origin: Vec3, size: Vec3, group: str,
             inflate: float | None = None, mirror: bool = False) -> dict:
        c: dict = {
            "origin": [round(o, 2) for o in origin],
            "size": [int(round(s)) for s in size],
            "uv": [0, 0],                       # filled in by finalise()
        }
        if inflate:
            c["inflate"] = inflate
        if mirror:
            c["mirror"] = True
        bone["cubes"].append(c)
        key = (int(round(size[0])), int(round(size[1])), int(round(size[2])))
        self._pending.append((c, key, group))
        return c

    def finalise(self) -> None:
        if self._finalised:
            return
        self.atlas.pack(sorted({(key, group) for _, key, group in self._pending}))
        for cube, key, group in self._pending:
            u, v = self.atlas.placement[(key, group)]
            cube["uv"] = [u, v]
        self._finalised = True

    def regions(self) -> list[tuple[int, int, tuple[int, int, int], str]]:
        """(u, v, size, group) for every distinct rectangle. Used by the
        texture generator so the sheet is painted exactly where the model
        samples it."""
        self.finalise()
        return sorted(
            ((uv[0], uv[1], key, group) for (key, group), uv in self.atlas.placement.items()),
            key=lambda r: (r[1], r[0]),
        )

    def to_json(self, bounds_w: float, bounds_h: float, bounds_off: Vec3) -> dict:
        self.finalise()
        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": f"geometry.{self.identifier}",
                        "texture_width": self.tex_w,
                        "texture_height": self.tex_h,
                        "visible_bounds_width": bounds_w,
                        "visible_bounds_height": bounds_h,
                        "visible_bounds_offset": list(bounds_off),
                    },
                    "bones": self.bones,
                }
            ],
        }


# ---------------------------------------------------------------------------
# echo_weaver
# ---------------------------------------------------------------------------

def build_echo_weaver() -> Model:
    """A ceiling predator with a 3.7-block leg span.

    Leg chains are authored STRAIGHT, running outward along x at hip height,
    each segment starting exactly where its parent ends. The arch comes from the
    joint rotations, which compose down the hierarchy - building it pre-bent
    tears the segments apart the moment the parent rotations apply, because the
    child is carried by them too.
    """
    m = Model("echo_weaver", 128, 128)

    m.bone("root", (0, 0, 0))

    # Cephalothorax: the fused head-thorax, plus a forward clypeus and fangs.
    ceph = m.bone("cephalothorax", (0, 16, -4), parent="root")
    m.cube(ceph, (-7, 10, -14), (14, 11, 16), "carapace")
    # The clypeus sits low and well clear of the crest sweep, so the eye cluster
    # is never buried behind the sails.
    m.cube(ceph, (-5, 10, -21), (10, 8, 7), "face")
    m.cube(ceph, (-4, 6, -21), (3, 5, 4), "fang", mirror=True)
    m.cube(ceph, (1, 6, -21), (3, 5, 4), "fang")

    thorax = m.bone("thorax_segment", (0, 16, 4), parent="cephalothorax")
    m.cube(thorax, (-6, 11, 2), (12, 9, 9), "carapace")

    # Abdomen: the mass at the back. Slung a little lower than the thorax, with
    # a raised dorsal plate, so the profile steps down instead of reading as one
    # long table top.
    abdomen = m.bone("abdomen", (0, 16, 12), parent="thorax_segment")
    m.cube(abdomen, (-9, 7, 10), (18, 14, 17), "carapace")
    m.cube(abdomen, (-7, 20, 12), (14, 3, 13), "plate")
    m.cube(abdomen, (-3, 8, 27), (6, 5, 4), "spinneret")

    # Four acoustic crests. They sweep BACKWARDS over the thorax - leaning them
    # forward puts them straight over the eyes, which is what the first pass
    # did, and the animal loses its face from every angle that matters.
    for i, (dx, yaw) in enumerate(((-6, -24), (-2, -9), (2, 9), (6, 24)), start=1):
        crest = m.bone(f"crest_{i}", (dx, 21, -4), parent="cephalothorax",
                       rotation=(26, yaw, 0))
        m.cube(crest, (dx - 1, 21, -6), (2, 13, 6), "crest")

    # Eight legs, four per side: femur up and out, tibia down and out, tarsus
    # nearly vertical. The chain lands the foot on y=0 from a hip at y=16.
    FEMUR, TIBIA, TARSUS = 14, 20, 10
    for side, sign in (("l", -1), ("r", 1)):
        for i, z in enumerate((-10, -3, 4, 11), start=1):
            hip_x = 8 * sign

            def seg(x_start: float, length: float, thickness: float):
                """Cube spanning `length` outward from x_start on this side."""
                x0 = x_start if sign > 0 else x_start - length
                return ((x0, 16 - thickness / 2, z - thickness / 2),
                        (length, thickness, thickness))

            femur = m.bone(f"leg_{side}{i}_femur", (hip_x, 16, z),
                           parent="cephalothorax", rotation=(0, 0, 50 * sign))
            origin, size = seg(hip_x, FEMUR, 4)
            m.cube(femur, origin, size, "limb", mirror=(sign < 0))

            knee_x = hip_x + FEMUR * sign
            tibia = m.bone(f"leg_{side}{i}_tibia", (knee_x, 16, z),
                           parent=f"leg_{side}{i}_femur", rotation=(0, 0, -105 * sign))
            origin, size = seg(knee_x, TIBIA, 3)
            m.cube(tibia, origin, size, "limb", mirror=(sign < 0))

            ankle_x = knee_x + TIBIA * sign
            tarsus = m.bone(f"leg_{side}{i}_tarsus", (ankle_x, 16, z),
                            parent=f"leg_{side}{i}_tibia", rotation=(0, 0, -30 * sign))
            origin, size = seg(ankle_x, TARSUS, 2)
            m.cube(tarsus, origin, size, "claw", mirror=(sign < 0))

    return m


# ---------------------------------------------------------------------------
# strata_golem
# ---------------------------------------------------------------------------

def build_strata_golem() -> Model:
    """A tower of rock: low heavy chassis, slab shoulders, tall spires.

    Presence here is mass and silhouette rather than height alone - the
    shoulders overhang the legs by five pixels on each side, so the thing reads
    as top-heavy and slow even in a single frame.
    """
    m = Model("strata_golem", 128, 128)

    m.bone("root", (0, 0, 0))

    # Chassis: the body block plus a keel that reaches down towards the hips.
    # It is carried a clear nine pixels off the ground so there is daylight
    # under the animal - without that gap the whole thing reads as a cairn
    # rather than as something standing on legs.
    chassis = m.bone("chassis", (0, 24, 0), parent="root")
    m.cube(chassis, (-13, 22, -10), (26, 16, 20), "rock")
    m.cube(chassis, (-9, 17, -7), (18, 6, 14), "rock")

    # Slab shoulders. The pauldrons are what make the silhouette read, and the
    # plate stops short of the head so it never overhangs the face.
    plate = m.bone("chassis_plate", (0, 38, 0), parent="chassis")
    m.cube(plate, (-15, 38, -8), (30, 6, 20), "rock")
    m.cube(plate, (-19, 35, -5), (4, 9, 14), "pauldron", mirror=True)
    m.cube(plate, (15, 35, -5), (4, 9, 14), "pauldron")

    # Head: slung well forward and low off the front of the chassis, iron-golem
    # fashion, with a separate jaw so the face has a shadow line in it. It
    # protrudes sixteen pixels past the shoulder plate, which is what makes the
    # silhouette read as an animal facing you rather than as a stack.
    head = m.bone("head", (0, 36, -10), parent="chassis")
    m.cube(head, (-7, 23, -24), (14, 13, 12), "head")
    m.cube(head, (-6, 19, -23), (12, 4, 10), "jaw")

    # Three crystal spire clusters, each its own bone so a shed cluster can be
    # hidden independently. The tallest reaches y=64 - four blocks up.
    clusters = (
        ("cluster_fore", (0, 44, -6),
         (((-5, 44, -8), (5, 20, 5)), ((1, 44, -5), (3, 13, 3)), ((-8, 44, -4), (2, 8, 2)))),
        ("cluster_mid", (0, 44, 1),
         (((0, 44, -1), (5, 20, 5)), ((-5, 44, 1), (3, 13, 3)), ((6, 44, 2), (2, 8, 2)))),
        ("cluster_aft", (0, 44, 7),
         (((-6, 44, 5), (3, 13, 3)), ((0, 44, 6), (5, 20, 5)), ((-2, 44, 3), (2, 8, 2)))),
    )
    for name, pivot, cubes in clusters:
        bone = m.bone(name, pivot, parent="chassis_plate")
        for origin, size in cubes:
            m.cube(bone, origin, size, "spire")

    # Quadruped: short thick legs, set wide so the gap between them is as broad
    # as the legs themselves.
    for side, sx in (("l", -10), ("r", 10)):
        for name, z in (("front", -8), ("back", 8)):
            upper = m.bone(f"leg_{side}_{name}_upper", (sx, 24, z), parent="chassis")
            m.cube(upper, (sx - 5, 9, z - 5), (10, 13, 10), "rock")
            lower = m.bone(f"leg_{side}_{name}_lower", (sx, 9, z),
                           parent=f"leg_{side}_{name}_upper")
            m.cube(lower, (sx - 6, 0, z - 6), (12, 9, 12), "rock")

    return m


# ---------------------------------------------------------------------------
# resonance_wraith
# ---------------------------------------------------------------------------

def build_resonance_wraith() -> Model:
    """Much wider than tall: a bright core inside a translucent shell, ringed by
    a resonance disc and four two-layer ribbon bands.

    Each band is inner -> mid -> outer, and each segment carries a second thin
    "echo" cube raised above it. The model renders translucent, so the echo
    cubes read as the ribbon smearing rather than as extra geometry.
    """
    m = Model("resonance_wraith", 128, 128)

    m.bone("root", (0, 0, 0))

    core = m.bone("core", (0, 18, 0), parent="root")
    m.cube(core, (-6, 12, -6), (12, 12, 12), "shell")
    m.cube(core, (-3, 15, -3), (6, 6, 6), "core")

    # A flat disc riding ABOVE the core rather than through its waist, where the
    # ribbons buried it. The texture punches an alpha hole in the middle of the
    # top and bottom faces, so it reads as a ring, not a slab.
    halo = m.bone("core_halo", (0, 24, 0), parent="core")
    m.cube(halo, (-14, 23, -14), (28, 2, 28), "halo")

    for i, yaw in enumerate((0, 90, 180, 270), start=1):
        m.bone(f"ribbon_{i}", (0, 18, 0), parent="core", rotation=(0, yaw, 0))

        inner = m.bone(f"ribbon_{i}_inner", (0, 18, 6), parent=f"ribbon_{i}",
                       rotation=(16, 0, 0))
        m.cube(inner, (-9, 17, 6), (18, 2, 11), "ribbon")
        m.cube(inner, (-7, 20, 7), (14, 1, 9), "ribbon")

        mid = m.bone(f"ribbon_{i}_mid", (0, 17, 17), parent=f"ribbon_{i}_inner",
                     rotation=(-28, 0, 0))
        m.cube(mid, (-7, 16, 17), (14, 2, 11), "ribbon")
        m.cube(mid, (-5, 19, 18), (10, 1, 9), "ribbon")

        outer = m.bone(f"ribbon_{i}_outer", (0, 16, 28), parent=f"ribbon_{i}_mid",
                       rotation=(32, 0, 0))
        m.cube(outer, (-5, 15, 28), (10, 2, 6), "ribbon")
        m.cube(outer, (-3, 18, 29), (6, 1, 5), "ribbon")

    return m


# ---------------------------------------------------------------------------

BUILDERS = {
    "echo_weaver": (build_echo_weaver, 4.5, 2.5, (0, 1.0, 0)),
    "strata_golem": (build_strata_golem, 3.5, 4.0, (0, 1.75, 0)),
    "resonance_wraith": (build_resonance_wraith, 5.0, 2.0, (0, 1.0, 0)),
}


def build_all() -> dict[str, Model]:
    """Every model, finalised. Imported by tools/gen_entity_textures.py."""
    out = {}
    for name, (builder, _, _, _) in BUILDERS.items():
        model = builder()
        model.finalise()
        out[name] = model
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (builder, bw, bh, off) in BUILDERS.items():
        model = builder()
        data = model.to_json(bw, bh, off)
        path = OUT_DIR / f"{name}.geo.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        bones = data["minecraft:geometry"][0]["bones"]
        cubes = sum(len(b["cubes"]) for b in bones)
        used = model.atlas.used_pixels()
        total = model.tex_w * model.tex_h
        print(f"{name}.geo.json: {len(bones)} bones, {cubes} cubes, "
              f"{len(model.atlas.rects)} uv rects, "
              f"atlas {used}/{total} px ({used * 100 // total}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

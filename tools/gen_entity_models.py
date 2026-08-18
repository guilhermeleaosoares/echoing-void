"""
The Echoing Void - Blockbench (.geo.json) -> Java entity model generator.

Vanilla Java entity rendering cannot read .geo.json. It bakes a ModelPart tree out of a
LayerDefinition built by hand in Java. Typing the geometry a second time would guarantee that the
Java models and the .geo.json the asset gate checks drift apart, so this script derives the Java
models from the geometry files instead. tools/gen_geo_models.py owns the geometry; this script owns
the translation of that geometry into src/main/java/com/echoingvoid/client/model/.

COORDINATE CONVERSION
---------------------
Bedrock model space is Y-up with the cube origin at the cube's MINIMUM corner, and both bone pivots
and cube origins are absolute. Java entity model space is Y-DOWN, cube coordinates are relative to
the owning part's pivot, and PartPose offsets are relative to the PARENT part's pivot. So, writing
p for a bone's bedrock pivot, o for a cube's bedrock origin and s for its size:

    part offset   = (p.x - parent.x,  parent.y - p.y,  p.z - parent.z)
    top-level     = (p.x,             24 - p.y,        p.z)
    addBox origin = (o.x - p.x,       p.y - o.y - s.y, o.z - p.z)
    addBox size   = (s.x, s.y, s.z)                     unchanged

The 24 is the vanilla convention: a root part at PartPose.offset(0, 24, 0) puts model y=24 on the
ground, so a creature standing on y=0 in Blockbench also stands on the ground in game. Vanilla does
exactly this - see FrogModel.createBodyLayer in the 26.2 sources.

Bone rotations need a sign flip, not just a copy. Java model space is bedrock space reflected
through the y=0 plane, and a reflection reverses the sense of any rotation whose axis survives it.
Rotation about Y is preserved (the axis itself is negated, which cancels the reversal); rotation
about X and Z is negated:

    xRot = -radians(rot.x)      yRot = +radians(rot.y)      zRot = -radians(rot.z)

Both engines compose bone rotation in Z-Y-X order (net.minecraft.client.model.geom.ModelPart#
translateAndRotate uses Quaternionf.rotationZYX), so no reordering is needed - conjugating a
product by a reflection converts each factor independently and leaves the order alone.

Cube-level "mirror" becomes CubeListBuilder#mirror and "inflate" becomes the CubeDeformation
argument to addBox. texture_width/texture_height become the LayerDefinition.create sizes.

The animation for each creature lives in ANIMATIONS below, next to the field list it needs; the
generator resolves each field to the right root.getChild(...) chain from the bone tree so a rename
in the geometry surfaces here as a generation error rather than as a crash at bake time.

Run:  python tools/gen_entity_models.py
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEO_DIR = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "geo"
OUT_DIR = ROOT / "src" / "main" / "java" / "com" / "echoingvoid" / "client" / "model"
PACKAGE = "com.echoingvoid.client.model"

# Vanilla convention: a top-level part sits 24 pixels (1.5 blocks) below the model origin so that
# bedrock y=0 lands on the ground.
GROUND_Y = 24.0

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Names the generated createBodyLayer() uses for itself, and so cannot be used by a bone.
RESERVED_LOCALS = {"mesh", "parts"}


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------

def flt(value: float) -> str:
    """Java float literal, normalised so the output is byte-stable across runs."""
    value = round(float(value), 4)
    if value == 0.0:
        value = 0.0  # collapse -0.0
    if value == int(value):
        return f"{int(value)}.0F"
    return f"{value:.4f}".rstrip("0") + "F"


def rad(degrees: float) -> str:
    value = round(math.radians(degrees), 6)
    if value == 0.0:
        value = 0.0
    if value == int(value):
        return f"{int(value)}.0F"
    return f"{value:.6f}".rstrip("0") + "F"


def to_int(value: float) -> int:
    return int(round(float(value)))


# ---------------------------------------------------------------------------
# geometry model
# ---------------------------------------------------------------------------

class Bone:
    def __init__(self, raw: dict):
        self.name: str = raw["name"]
        self.parent: str | None = raw.get("parent")
        self.pivot: list[float] = [float(v) for v in raw["pivot"]]
        self.rotation: list[float] | None = (
            [float(v) for v in raw["rotation"]] if raw.get("rotation") else None
        )
        self.cubes: list[dict] = raw.get("cubes") or []
        self.children: list[Bone] = []

        if not IDENTIFIER.match(self.name):
            raise ValueError(f"bone name {self.name!r} is not a legal Java identifier")
        if self.name in RESERVED_LOCALS:
            raise ValueError(f"bone name {self.name!r} collides with a generator local")


class Geometry:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        geo = data["minecraft:geometry"][0]
        desc = geo["description"]

        self.path = path
        self.identifier: str = desc["identifier"]
        self.tex_w = to_int(desc["texture_width"])
        self.tex_h = to_int(desc["texture_height"])

        self.bones: list[Bone] = [Bone(b) for b in geo["bones"]]
        self.by_name: dict[str, Bone] = {}
        for bone in self.bones:
            if bone.name in self.by_name:
                raise ValueError(f"duplicate bone {bone.name!r} in {path.name}")
            self.by_name[bone.name] = bone

        for bone in self.bones:
            if bone.parent is None:
                continue
            if bone.parent not in self.by_name:
                raise ValueError(f"bone {bone.name!r} names unknown parent {bone.parent!r}")
            self.by_name[bone.parent].children.append(bone)

        # Bones must appear after their parent so the emitted locals are always already in scope.
        seen: set[str] = set()
        for bone in self.bones:
            if bone.parent is not None and bone.parent not in seen:
                raise ValueError(f"bone {bone.name!r} precedes its parent in {path.name}")
            seen.add(bone.name)

    @property
    def cube_count(self) -> int:
        return sum(len(b.cubes) for b in self.bones)

    def chain(self, name: str) -> list[str]:
        """Bone names from the outermost ancestor down to `name`, inclusive."""
        bone = self.by_name.get(name)
        if bone is None:
            raise KeyError(f"{self.path.name} has no bone named {name!r}")
        path = []
        while bone is not None:
            path.append(bone.name)
            bone = self.by_name[bone.parent] if bone.parent else None
        return list(reversed(path))

    def lookup_expr(self, name: str) -> str:
        return "root" + "".join(f'.getChild("{part}")' for part in self.chain(name))


# ---------------------------------------------------------------------------
# geometry -> Java
# ---------------------------------------------------------------------------

def part_pose(bone: Bone, parent: Bone | None) -> str:
    if parent is None:
        x = bone.pivot[0]
        y = GROUND_Y - bone.pivot[1]
        z = bone.pivot[2]
    else:
        x = bone.pivot[0] - parent.pivot[0]
        y = parent.pivot[1] - bone.pivot[1]
        z = bone.pivot[2] - parent.pivot[2]

    if not bone.rotation or not any(bone.rotation):
        return f"PartPose.offset({flt(x)}, {flt(y)}, {flt(z)})"

    rx, ry, rz = bone.rotation
    return (
        "PartPose.offsetAndRotation("
        f"{flt(x)}, {flt(y)}, {flt(z)}, {rad(-rx)}, {rad(ry)}, {rad(-rz)})"
    )


def cube_list(bone: Bone) -> tuple[list[str], bool]:
    """Emit the CubeListBuilder chain for a bone. Returns (lines, uses_deformation)."""
    lines = ["CubeListBuilder.create()"]
    mirrored = False
    deformed = False

    for cube in bone.cubes:
        if cube.get("rotation"):
            raise ValueError(
                f"bone {bone.name!r} has a per-cube rotation; Java entity models cannot express "
                "one - give the cube its own bone in tools/gen_geo_models.py instead"
            )

        ox, oy, oz = (float(v) for v in cube["origin"])
        sx, sy, sz = (float(v) for v in cube["size"])
        u, v = (to_int(n) for n in cube["uv"])
        px, py, pz = bone.pivot

        want_mirror = bool(cube.get("mirror", False))
        if want_mirror != mirrored:
            lines.append("        .mirror()" if want_mirror else "        .mirror(false)")
            mirrored = want_mirror

        args = (
            f"{flt(ox - px)}, {flt(py - oy - sy)}, {flt(oz - pz)}, "
            f"{flt(sx)}, {flt(sy)}, {flt(sz)}"
        )
        inflate = float(cube.get("inflate", 0.0) or 0.0)
        if inflate:
            args += f", new CubeDeformation({flt(inflate)})"
            deformed = True

        lines.append(f"        .texOffs({u}, {v})")
        lines.append(f"        .addBox({args})")

    return lines, deformed


def create_body_layer(geo: Geometry) -> tuple[list[str], bool]:
    lines: list[str] = [
        "    public static LayerDefinition createBodyLayer() {",
        "        MeshDefinition mesh = new MeshDefinition();",
        "        PartDefinition parts = mesh.getRoot();",
    ]
    deformed = False

    for bone in geo.bones:
        parent = geo.by_name[bone.parent] if bone.parent else None
        parent_var = parent.name if parent else "parts"
        cubes, bone_deformed = cube_list(bone)
        deformed = deformed or bone_deformed

        # Only bones with children need a local; a leaf's PartDefinition is never referenced.
        assign = f"PartDefinition {bone.name} = " if bone.children else ""

        lines.append("")
        lines.append(f"        {assign}{parent_var}.addOrReplaceChild(")
        lines.append(f'                "{bone.name}",')
        if len(cubes) == 1:
            lines.append(f"                {cubes[0]},")
        else:
            lines.append(f"                {cubes[0]}")
            for extra in cubes[1:-1]:
                lines.append(f"                {extra}")
            lines.append(f"                {cubes[-1]},")
        lines.append(f"                {part_pose(bone, parent)});")

    lines.append("")
    lines.append(f"        return LayerDefinition.create(mesh, {geo.tex_w}, {geo.tex_h});")
    lines.append("    }")

    return lines, deformed


def imports(deformed: bool, extra: tuple[str, ...]) -> list[str]:
    names = {
        "com.echoingvoid.EchoingVoid",
        "net.minecraft.client.model.EntityModel",
        "net.minecraft.client.model.geom.ModelLayerLocation",
        "net.minecraft.client.model.geom.ModelPart",
        "net.minecraft.client.model.geom.PartPose",
        "net.minecraft.client.model.geom.builders.CubeListBuilder",
        "net.minecraft.client.model.geom.builders.LayerDefinition",
        "net.minecraft.client.model.geom.builders.MeshDefinition",
        "net.minecraft.client.model.geom.builders.PartDefinition",
        "net.minecraft.client.renderer.entity.state.LivingEntityRenderState",
    }
    if deformed:
        names.add("net.minecraft.client.model.geom.builders.CubeDeformation")
    names.update(extra)
    return [f"import {n};" for n in sorted(names)]


def render_fields(geo: Geometry, spec: dict) -> tuple[list[str], list[str]]:
    """Field declarations and the constructor lines that resolve them."""
    decls: list[str] = []
    init: list[str] = []

    for field in spec["fields"]:
        name = field["name"]
        comment = field.get("comment")
        if comment:
            decls.append(f"    /** {comment} */")

        if isinstance(field["bone"], str):
            decls.append(f"    private final ModelPart {name};")
            init.append(f"        this.{name} = {geo.lookup_expr(field['bone'])};")
        else:
            bones = field["bone"]
            decls.append(f"    private final ModelPart[] {name};")
            init.append(f"        this.{name} = new ModelPart[] {{")
            for i, bone in enumerate(bones):
                tail = "," if i < len(bones) - 1 else ""
                init.append(f"                {geo.lookup_expr(bone)}{tail}")
            init.append("        };")

    return decls, init


def render_class(geo: Geometry, spec: dict) -> str:
    body_layer, deformed = create_body_layer(geo)
    decls, init = render_fields(geo, spec)

    out: list[str] = []
    out.append(f"package {PACKAGE};")
    out.append("")
    out.extend(imports(deformed, tuple(spec.get("imports", ()))))
    out.append("")
    out.append("/**")
    for line in spec["javadoc"]:
        out.append(f" * {line}" if line else " *")
    out.append(" *")
    out.append(f" * <p>The geometry in this class is generated by {{@code tools/gen_entity_models.py}}")
    out.append(f" * from {{@code assets/echoing_void/geo/{geo.path.name}}}. Edit the geometry, then re-run")
    out.append(" * the generator; hand edits to {@code createBodyLayer} will be overwritten.")
    out.append(" */")
    out.append(f"public class {spec['class_name']} extends EntityModel<LivingEntityRenderState> {{")
    out.append("    /**")
    out.append("     * Where the baked mesh is filed. Registered against {@link #createBodyLayer()} in")
    out.append("     * {@code EchoingVoidClient} and looked up again by the renderer.")
    out.append("     */")
    out.append("    public static final ModelLayerLocation LAYER =")
    out.append(f'            new ModelLayerLocation(EchoingVoid.id("{spec["model_id"]}"), "main");')
    out.append("")
    out.extend(decls)
    out.append("")
    out.append(f"    public {spec['class_name']}(ModelPart root) {{")
    render_type = spec.get("render_type")
    out.append(f"        super(root, RenderTypes::{render_type});" if render_type else "        super(root);")
    out.extend(init)
    out.append("    }")
    out.append("")
    out.extend(body_layer)
    out.append("")
    out.append("    @Override")
    out.append("    public void setupAnim(LivingEntityRenderState state) {")
    out.append("        super.setupAnim(state);")
    for line in spec["anim"]:
        out.append(f"        {line}" if line else "")
    out.append("    }")
    out.append("}")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# per-creature animation
# ---------------------------------------------------------------------------

WEAVER_LEGS = [f"leg_{side}{i}" for side in ("l", "r") for i in (1, 2, 3, 4)]

ANIMATIONS: dict[str, dict] = {
    "echo_weaver": {
        "class_name": "EchoWeaverModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The echo weaver: a ceiling-dwelling ambusher built around a segmented cephalothorax,",
            "four acoustic crests and eight three-jointed legs.",
            "",
            "<p>The walk cycle is the vanilla spider's, extended to eight legs: legs a quarter cycle",
            "apart in each rank, ranks half a cycle out of phase, so four feet are always planted.",
            "The crests keep moving when the body is still, because listening is what the weaver",
            "does between ambushes.",
            "",
            "<p>Head tracking is deliberately absent. The cephalothorax carries every leg, so turning",
            "it to face the player would swing the whole animal off its feet.",
        ],
        "fields": [
            {
                "name": "legFemurs",
                "bone": [f"{leg}_femur" for leg in WEAVER_LEGS],
                "comment": "Hip segments, left rank first. Index order matches legTibias.",
            },
            {
                "name": "legTibias",
                "bone": [f"{leg}_tibia" for leg in WEAVER_LEGS],
                "comment": "Knee segments; they counter-flex against the femur's lift.",
            },
            {
                "name": "crests",
                "bone": [f"crest_{i}" for i in (1, 2, 3, 4)],
                "comment": "The four acoustic crests.",
            },
            {"name": "abdomen", "bone": "abdomen", "comment": "Rear segment."},
        ],
        "anim": [
            "float pos = state.walkAnimationPos * 0.6662F;",
            "float speed = state.walkAnimationSpeed;",
            "",
            "for (int i = 0; i < this.legFemurs.length; i++) {",
            "    boolean left = i < 4;",
            "    float phase = (i % 4) * ((float) Math.PI / 2.0F) + (left ? 0.0F : (float) Math.PI);",
            "    float side = left ? -1.0F : 1.0F;",
            "    float swing = -(Mth.cos(pos * 2.0F + phase) * 0.4F) * speed;",
            "    float lift = Math.abs(Mth.sin(pos + phase) * 0.4F) * speed;",
            "    this.legFemurs[i].yRot += swing * side;",
            "    this.legFemurs[i].zRot += lift * side;",
            "    this.legTibias[i].zRot -= lift * 0.6F * side;",
            "}",
            "",
            "for (int i = 0; i < this.crests.length; i++) {",
            "    this.crests[i].xRot += Mth.cos(state.ageInTicks * 0.12F + i * 0.7F) * 0.06F;",
            "}",
            "",
            "this.abdomen.xRot += Mth.cos(state.ageInTicks * 0.05F) * 0.03F;",
        ],
    },
    "strata_golem": {
        "class_name": "StrataGolemModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The strata golem: a slow, territorial quadruped with a low centre of mass and three",
            "clusters of crystal spires on its back.",
            "",
            "<p>It rolls into a step rather than bobbing over it. The cadence is deliberately slower",
            "than a vanilla quadruped's and the swing amplitude is capped, so a golem that has been",
            "shoved does not windmill its legs. Diagonal pairs move together, which is what keeps a",
            "heavy animal upright.",
        ],
        "fields": [
            {"name": "chassis", "bone": "chassis", "comment": "The whole body above the hips."},
            {"name": "head", "bone": "head", "comment": "Tracks the golem's look direction."},
            {
                "name": "legUppers",
                "bone": [
                    "leg_l_front_upper",
                    "leg_l_back_upper",
                    "leg_r_front_upper",
                    "leg_r_back_upper",
                ],
                "comment": "Thighs, ordered left-front, left-back, right-front, right-back.",
            },
            {
                "name": "legLowers",
                "bone": [
                    "leg_l_front_lower",
                    "leg_l_back_lower",
                    "leg_r_front_lower",
                    "leg_r_back_lower",
                ],
                "comment": "Feet, in the same order as legUppers.",
            },
            {
                "name": "clusters",
                "bone": ["cluster_fore", "cluster_mid", "cluster_aft"],
                "comment": "Detachable crystal spire clusters.",
            },
        ],
        "anim": [
            "float pos = state.walkAnimationPos * 0.4F;",
            "// Cap the input: a golem knocked around should still move like a golem.",
            "float speed = Math.min(state.walkAnimationSpeed, 0.6F);",
            "",
            "this.head.xRot += state.xRot * ((float) Math.PI / 180.0F);",
            "this.head.yRot += state.yRot * ((float) Math.PI / 180.0F);",
            "",
            "this.chassis.zRot += Mth.cos(pos) * 0.05F * speed;",
            "this.chassis.y += Mth.sin(pos * 2.0F) * 0.4F * speed;",
            "",
            "for (int i = 0; i < this.legUppers.length; i++) {",
            "    // Left-front with right-back, left-back with right-front.",
            "    float phase = (i == 0 || i == 3) ? 0.0F : (float) Math.PI;",
            "    float swing = Mth.cos(pos + phase) * 0.6F * speed;",
            "    this.legUppers[i].xRot += swing;",
            "    // The foot only folds under on the recovery half of the stride.",
            "    this.legLowers[i].xRot += Math.max(0.0F, -swing) * 0.5F;",
            "}",
            "",
            "for (int i = 0; i < this.clusters.length; i++) {",
            "    float t = state.ageInTicks * 0.03F + i * 1.1F;",
            "    this.clusters[i].zRot += Mth.cos(t) * 0.04F;",
            "    this.clusters[i].xRot += Mth.sin(t * 0.7F) * 0.03F;",
            "}",
        ],
    },
    "resonance_wraith": {
        "class_name": "ResonanceWraithModel",
        "imports": ("net.minecraft.util.Mth", "net.minecraft.client.renderer.rendertype.RenderTypes"),
        # Incorporeal: the ribbons read as sound, so they have to be see-through.
        "render_type": "entityTranslucent",
        "javadoc": [
            "The resonance wraith: a floating core wrapped in four bands of layered ribbon.",
            "",
            "<p>Nothing here is driven by the walk cycle, because the wraith has no gait - it drifts.",
            "Each band carries a travelling wave outward from the core, with every segment lagging",
            "the one inboard of it and swinging wider, so the silhouette reads as sound leaving the",
            "body. Movement speed only widens the wave; it never starts it.",
        ],
        "fields": [
            {"name": "core", "bone": "core", "comment": "The body proper. Bobs on the spot."},
            {"name": "halo", "bone": "core_halo", "comment": "The flat ring around the core."},
            {
                "name": "bands",
                "bone": [f"ribbon_{i}" for i in (1, 2, 3, 4)],
                "comment": "Band roots, one per quadrant.",
            },
            {
                "name": "bandInner",
                "bone": [f"ribbon_{i}_inner" for i in (1, 2, 3, 4)],
                "comment": "First ribbon segment of each band.",
            },
            {
                "name": "bandMid",
                "bone": [f"ribbon_{i}_mid" for i in (1, 2, 3, 4)],
                "comment": "Second ribbon segment of each band.",
            },
            {
                "name": "bandOuter",
                "bone": [f"ribbon_{i}_outer" for i in (1, 2, 3, 4)],
                "comment": "Outermost ribbon segment of each band.",
            },
        ],
        "anim": [
            "float age = state.ageInTicks;",
            "float agitation = 1.0F + state.walkAnimationSpeed * 1.5F;",
            "",
            "this.core.y += Mth.sin(age * 0.08F) * 0.8F;",
            "this.halo.yRot += age * 0.02F;",
            "",
            "for (int i = 0; i < this.bands.length; i++) {",
            "    float phase = i * ((float) Math.PI / 2.0F);",
            "    this.bands[i].yRot += Mth.cos(age * 0.03F + phase) * 0.08F;",
            "    this.bandInner[i].xRot += Mth.cos(age * 0.15F + phase) * 0.1F * agitation;",
            "    this.bandMid[i].xRot += Mth.cos(age * 0.15F + phase - 0.9F) * 0.16F * agitation;",
            "    this.bandOuter[i].xRot += Mth.cos(age * 0.15F + phase - 1.8F) * 0.22F * agitation;",
            "}",
        ],
    },
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name in sorted(ANIMATIONS):
        geo = Geometry(GEO_DIR / f"{name}.geo.json")
        if geo.identifier != f"geometry.{name}":
            raise ValueError(
                f"{geo.path.name} declares {geo.identifier!r}, expected 'geometry.{name}'"
            )

        # The model id doubles as the ModelLayerLocation path and the texture file name.
        spec = dict(ANIMATIONS[name], model_id=name)
        source = render_class(geo, spec)
        out_path = OUT_DIR / f"{spec['class_name']}.java"
        out_path.write_text(source, encoding="utf-8")

        depth = max(len(geo.chain(b.name)) for b in geo.bones)
        print(
            f"{spec['class_name']}.java: {len(geo.bones)} parts, {geo.cube_count} cubes, "
            f"{geo.tex_w}x{geo.tex_h} sheet, tree depth {depth}, "
            f"{len(source.splitlines())} lines"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

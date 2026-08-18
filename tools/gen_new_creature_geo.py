"""
The Echoing Void - geometry for the three expansion creatures.

tools/gen_geo_models.py owns the original three (echo_weaver, strata_golem,
resonance_wraith) and is not touched here. This script owns the round-two
creatures and reuses that module's Model/UvAtlas so both sets share one shelf
packer, one bedrock JSON writer and one set of conventions:

  chime_mote       a small drifting lantern - a null-iron cage around a lit
                   core, four vanes that fan as it moves, and a wisp of tail.
                   Neutral ambient life, so it has to read as a lamp with a
                   creature in it rather than as a threat.
  tuner_shade      a hooded, robed caster holding a resonator ring in front of
                   its chest. Player-sized, and deliberately silhouetted like a
                   person - the blink is only unsettling if the thing that
                   vanishes looks like it could have been talked to.
  strata_burrower  a low armoured digger: wedge head, paired mandibles, three
                   body segments and six stubby claws. Long and flat, because
                   the whole creature has to read as "something moving under
                   the floor" from the ridge line alone.

BONE NAMES ARE A CONTRACT, exactly as they are for the original three: the
ANIMATIONS table at the bottom of this file resolves animation fields by bone
name, and the resolution happens at generation time, so a rename surfaces here
as an error rather than as a crash at bake time.

WHY THIS FILE ALSO EMITS JAVA
-----------------------------
tools/gen_entity_models.py turns a .geo.json into a Java LayerDefinition, but
its creature table is a module constant listing the original three, and that
file is not ours to edit. So the translation is driven from here instead: this
script imports that module and calls its Geometry parser and render_class
writer on our geometry with our animation table. There is still exactly one
implementation of the bedrock-to-Java coordinate conversion, and the geometry
still has exactly one source.

Run:  python tools/gen_new_creature_geo.py
Outputs:
  src/main/resources/assets/echoing_void/geo/<creature>.geo.json
  src/main/java/com/echoingvoid/client/model/<Creature>Model.java
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_geo_models import Model, OUT_DIR                       # noqa: E402
import gen_entity_models                                        # noqa: E402

Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# chime_mote
# ---------------------------------------------------------------------------

def build_chime_mote() -> Model:
    """A lantern that drifts.

    The cage is built as four corner posts and two caps rather than as one
    hollow box, because a box cannot be seen through and the whole point of the
    creature is the lit core inside it. The vanes hang off the cage at the four
    quadrants so the silhouette changes as it turns, and the tail wisp gives the
    thing a down direction - without it a symmetric lamp reads as an item drop.
    """
    m = Model("chime_mote", 64, 64)

    m.bone("root", (0, 0, 0))

    shell = m.bone("shell", (0, 8, 0), parent="root")
    for dx, dz in ((-3, -3), (2, -3), (-3, 2), (2, 2)):
        m.cube(shell, (dx, 4, dz), (1, 7, 1), "frame")
    m.cube(shell, (-3, 11, -3), (6, 1, 6), "frame")      # top cap
    m.cube(shell, (-3, 3, -3), (6, 1, 6), "frame")       # bottom cap
    m.cube(shell, (-1, 12, -1), (2, 2, 2), "frame")      # the hanging hook

    core = m.bone("core", (0, 8, 0), parent="shell")
    m.cube(core, (-2, 5, -2), (4, 5, 4), "core")

    # Four vanes, one per quadrant. They sit at the height of the lower cap
    # rather than at the core's, because a vane level with the core hides it
    # from every angle the creature is actually seen from - and the lit core is
    # the entire silhouette. They fan on the same phase offset the model
    # animates, so a mote in motion opens out and a settled one folds in.
    for i, yaw in enumerate((0, 90, 180, 270), start=1):
        fin = m.bone(f"fin_{i}", (0, 8, 0), parent="shell", rotation=(0, yaw, 0))
        m.cube(fin, (-2, 3, 3), (4, 1, 4), "vane")

    tail = m.bone("tail", (0, 3, 0), parent="shell")
    m.cube(tail, (-1, 0, -1), (2, 3, 2), "wisp")

    return m


# ---------------------------------------------------------------------------
# tuner_shade
# ---------------------------------------------------------------------------

def build_tuner_shade() -> Model:
    """A hooded caster with a resonator ring held out in front of it.

    There are no legs. The robe is a two-stage taper down to a hem that reaches
    the ground, which is both cheaper than a leg rig and the right read for
    something that blinks rather than walks. The mantle across the shoulders is
    what stops the torso from looking like a plank, and the hood peak gives the
    head a direction from behind as well as from the front.

    The ring is a real four-bar frame rather than a painted disc, because it is
    the casting tell: it spins constantly and the player needs to see it edge-on
    as well as face-on.
    """
    m = Model("tuner_shade", 128, 128)

    m.bone("root", (0, 0, 0))

    robe = m.bone("robe", (0, 13, 0), parent="root")
    m.cube(robe, (-6, 0, -4), (12, 7, 8), "robe")        # hem, on the ground
    m.cube(robe, (-5, 7, -3), (10, 6, 6), "robe")        # the taper up to the waist

    torso = m.bone("torso", (0, 13, 0), parent="robe")
    m.cube(torso, (-5, 13, -3), (10, 9, 6), "cloth")

    mantle = m.bone("mantle", (0, 22, 0), parent="torso")
    m.cube(mantle, (-7, 19, -4), (14, 3, 8), "mantle")

    head = m.bone("head", (0, 22, 0), parent="torso")
    m.cube(head, (-4, 22, -4), (8, 7, 8), "hood")

    peak = m.bone("peak", (0, 29, 0), parent="head")
    m.cube(peak, (-2, 28, -2), (4, 3, 4), "hood")

    # Arms: the left hangs, the right is cocked forward to carry the ring.
    for side, sign, fore in (("l", -1, -14.0), ("r", 1, -42.0)):
        shoulder_x = 6 * sign
        upper = m.bone(f"arm_{side}_upper", (shoulder_x, 21, 0), parent="torso",
                       rotation=(0, 0, -5 * sign))
        x0 = shoulder_x - 2 if sign < 0 else shoulder_x - 2
        m.cube(upper, (x0, 15, -2), (4, 6, 4), "limb", mirror=(sign < 0))

        lower = m.bone(f"arm_{side}_lower", (shoulder_x, 15, 0),
                       parent=f"arm_{side}_upper", rotation=(fore, 0, 0))
        m.cube(lower, (x0, 9, -2), (4, 6, 4), "limb", mirror=(sign < 0))

    ring = m.bone("ring", (0, 13, -7), parent="torso")
    m.cube(ring, (-5, 16, -8), (10, 1, 2), "ring")       # top bar
    m.cube(ring, (-5, 10, -8), (10, 1, 2), "ring")       # bottom bar
    m.cube(ring, (-5, 11, -8), (1, 5, 2), "ring", mirror=True)
    m.cube(ring, (4, 11, -8), (1, 5, 2), "ring")

    spark = m.bone("spark", (0, 13, -7), parent="ring")
    m.cube(spark, (-1, 12, -8), (2, 2, 2), "spark")

    return m


# ---------------------------------------------------------------------------
# strata_burrower
# ---------------------------------------------------------------------------

def build_strata_burrower() -> Model:
    """A low armoured digger, three and a half blocks long and barely one tall.

    Everything about the proportions serves the one thing the player has to be
    able to spot: the dorsal ridge. The body is flat and wide so the ridge
    plates are the tallest thing on it, and they sit on separate bones so they
    keep moving while the animal is otherwise still.

    Leg chains are authored STRAIGHT along x from the hip and bent by the joint
    rotations, the same way the weaver's are - a pre-bent chain tears apart the
    moment the parent rotation applies.
    """
    m = Model("strata_burrower", 128, 128)

    m.bone("root", (0, 0, 0))

    body = m.bone("body", (0, 9, -2), parent="root")
    m.cube(body, (-9, 2, -8), (18, 13, 12), "carapace")

    # The skull is its own material group so it can carry the eye cluster; the
    # generic carapace painter treats every face the same, which is right for a
    # body segment and wrong for the end the player meets first.
    head = m.bone("head", (0, 9, -8), parent="body")
    m.cube(head, (-8, 3, -21), (16, 11, 13), "skull")
    m.cube(head, (-6, 13, -19), (12, 3, 10), "plate")     # brow shield

    # Mandibles reach eight pixels past the snout and splay outward, so the
    # first thing out of the ground is a pair of jaws rather than a nose.
    for side, sign in (("l", -1), ("r", 1)):
        jaw = m.bone(f"mandible_{side}", (7 * sign, 7, -20), parent="head",
                     rotation=(0, -16 * sign, 0))
        x0 = -12 if sign < 0 else 7
        m.cube(jaw, (x0, 4, -29), (5, 6, 10), "mandible", mirror=(sign < 0))

    ridge_fore = m.bone("ridge_fore", (0, 15, -3), parent="body")
    m.cube(ridge_fore, (-3, 15, -6), (6, 4, 8), "ridge")

    segment_mid = m.bone("segment_mid", (0, 9, 4), parent="body")
    m.cube(segment_mid, (-8, 2, 4), (16, 11, 11), "carapace")

    ridge_aft = m.bone("ridge_aft", (0, 13, 8), parent="segment_mid")
    m.cube(ridge_aft, (-3, 13, 6), (6, 4, 7), "ridge")

    segment_tail = m.bone("segment_tail", (0, 9, 15), parent="segment_mid")
    m.cube(segment_tail, (-6, 3, 15), (12, 9, 8), "carapace")

    tail_spur = m.bone("tail_spur", (0, 8, 23), parent="segment_tail")
    m.cube(tail_spur, (-3, 4, 23), (6, 6, 6), "plate")

    # Six stubby digging legs. Three per side, the rearmost pair carried by the
    # middle segment so the back of the animal still has feet under it when the
    # yaw wave swings it out.
    UPPER, CLAW = 7, 8
    for side, sign in (("l", -1), ("r", 1)):
        for i, (z, parent) in enumerate(((-4, "body"), (1, "body"), (10, "segment_mid")), start=1):
            hip_x = 9 * sign

            def seg(x_start: float, length: float, thickness: float) -> tuple[Vec3, Vec3]:
                """Cube spanning `length` outward from x_start on this side."""
                x0 = x_start if sign > 0 else x_start - length
                return ((x0, 6 - thickness / 2, z - thickness / 2),
                        (length, thickness, thickness))

            upper = m.bone(f"leg_{side}{i}_upper", (hip_x, 6, z), parent=parent,
                           rotation=(0, 0, 25 * sign))
            origin, size = seg(hip_x, UPPER, 4)
            m.cube(upper, origin, size, "limb", mirror=(sign < 0))

            knee_x = hip_x + UPPER * sign
            claw = m.bone(f"leg_{side}{i}_claw", (knee_x, 6, z),
                          parent=f"leg_{side}{i}_upper", rotation=(0, 0, -105 * sign))
            origin, size = seg(knee_x, CLAW, 3)
            m.cube(claw, origin, size, "claw", mirror=(sign < 0))

    return m


# ---------------------------------------------------------------------------
# tuner_trader
# ---------------------------------------------------------------------------

def build_tuner_trader() -> Model:
    """A robed trader, standing rather than floating: two legs, a satchel of
    goods slung on one hip, and a wide-brimmed hat rather than a hood - the
    one silhouette in the dimension that reads as "safe to approach" instead
    of "caster" or "digger". The satchel is the tell that says trader before
    the player is close enough to see a face.
    """
    m = Model("tuner_trader", 64, 64)

    m.bone("root", (0, 0, 0))

    legs = m.bone("legs", (0, 12, 0), parent="root")
    for side, sign in (("l", -1), ("r", 1)):
        m.cube(legs, (2 * sign - 2, 0, -2), (4, 12, 4), "robe", mirror=(sign < 0))

    torso = m.bone("torso", (0, 12, 0), parent="legs")
    m.cube(torso, (-4, 12, -3), (8, 12, 6), "robe")

    satchel = m.bone("satchel", (5, 17, 0), parent="torso", rotation=(0, 0, -8))
    m.cube(satchel, (4, 13, -3), (3, 6, 6), "satchel")
    strap = m.bone("strap", (0, 24, 0), parent="torso")
    m.cube(strap, (-4, 20, -1), (8, 2, 2), "strap")

    head = m.bone("head", (0, 24, 0), parent="torso")
    m.cube(head, (-4, 24, -4), (8, 8, 8), "head")

    brim = m.bone("brim", (0, 32, 0), parent="head")
    m.cube(brim, (-6, 31, -6), (12, 1, 12), "hat")
    crown = m.bone("crown", (0, 32, 0), parent="brim")
    m.cube(crown, (-3, 32, -3), (6, 3, 6), "hat")

    for side, sign in (("l", -1), ("r", 1)):
        shoulder_x = 6 * sign
        upper = m.bone(f"arm_{side}_upper", (shoulder_x, 23, 0), parent="torso")
        x0 = shoulder_x - 2 if sign < 0 else shoulder_x - 2
        m.cube(upper, (x0, 17, -2), (4, 6, 4), "robe", mirror=(sign < 0))
        lower = m.bone(f"arm_{side}_lower", (shoulder_x, 17, 0), parent=f"arm_{side}_upper")
        m.cube(lower, (x0, 12, -2), (4, 5, 4), "hand", mirror=(sign < 0))

    return m


# ---------------------------------------------------------------------------
# tuners_protector
# ---------------------------------------------------------------------------

def build_tuners_protector() -> Model:
    """An imposing forged iron guardian: a massive broad chest chassis (18w x 11h x 10d),
    a tapered waist (12w x 5h x 6d), heavy pauldron collar cradling the Tuner's Mask
    head, massive articulated arms with clenched fists reaching past the knee,
    and heavy pillar legs planted with a wide stance."""
    m = Model("tuners_protector", 128, 128)

    m.bone("root", (0, 0, 0))

    # Heavy pillar legs (y=0..12) with a 4-unit stance gap between them
    legs = m.bone("legs", (0, 12, 0), parent="root")
    for side, sign in (("l", -1), ("r", 1)):
        x0 = 2 if sign > 0 else -8
        m.cube(legs, (x0, 0, -4), (6, 12, 8), "leg", mirror=(sign < 0))

    # Torso: articulated waist (y=12..17), massive broad chest (y=17..28), and collar rim (y=27..29)
    torso = m.bone("torso", (0, 12, 0), parent="legs")
    m.cube(torso, (-6, 12, -3), (12, 5, 6), "waist")
    m.cube(torso, (-9, 17, -5), (18, 11, 10), "torso")
    m.cube(torso, (-5, 27, -4), (10, 2, 8), "collar")

    # Head: Tuner's Mask (8x8x8) nestled firmly into the shoulder collar at y=28..36
    head = m.bone("head", (0, 28, 0), parent="torso")
    m.cube(head, (-4, 28, -5), (8, 8, 8), "head")

    # Massive articulated arms: upper arms attached at wide shoulders, long forearms & fists
    for side, sign in (("l", -1), ("r", 1)):
        sh_x = 12 * sign
        upper = m.bone(f"arm_{side}_upper", (sh_x, 26, 0), parent="torso")
        ux0 = 9 if sign > 0 else -15
        m.cube(upper, (ux0, 17, -3.5), (6, 10, 7), "arm", mirror=(sign < 0))

        lower = m.bone(f"arm_{side}_lower", (sh_x, 17, 0), parent=f"arm_{side}_upper")
        lx0 = 9 if sign > 0 else -15
        m.cube(lower, (lx0, 2, -4), (6, 15, 8), "fist", mirror=(sign < 0))

    return m


# ---------------------------------------------------------------------------

BUILDERS = {
    "chime_mote": (build_chime_mote, 1.5, 1.5, (0, 0.5, 0)),
    "tuner_shade": (build_tuner_shade, 2.0, 2.5, (0, 1.0, 0)),
    "strata_burrower": (build_strata_burrower, 4.0, 2.0, (0, 0.75, 0)),
    "tuner_trader": (build_tuner_trader, 0.9, 2.5, (0, 0.0, 0)),
    "tuners_protector": (build_tuners_protector, 1.8, 3.4, (0, 0.0, 0)),
}


def build_all() -> dict[str, Model]:
    """Every model, finalised. Imported by tools/gen_new_creature_textures.py."""
    out = {}
    for name, (builder, _, _, _) in BUILDERS.items():
        model = builder()
        model.finalise()
        out[name] = model
    return out


# ---------------------------------------------------------------------------
# animation, fed to gen_entity_models.render_class
# ---------------------------------------------------------------------------

BURROWER_LEGS = [f"leg_{side}{i}" for side in ("l", "r") for i in (1, 2, 3)]

ANIMATIONS: dict[str, dict] = {
    "chime_mote": {
        "class_name": "ChimeMoteModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The chime mote: a null-iron cage around a lit core, four vanes and a tail wisp.",
            "",
            "<p>Nothing here reads the walk cycle. The mote has no gait and never touches the",
            "ground, so every motion is driven by age alone: the cage turns slowly, the core",
            "breathes inside it, the vanes fan a quarter cycle apart and the tail trails behind",
            "on a slower period than everything else. The result is that a stationary mote is",
            "still visibly alive, which is the entire reason the creature exists.",
        ],
        "fields": [
            {"name": "shell", "bone": "shell", "comment": "The cage. Turns on its own axis."},
            {"name": "core", "bone": "core", "comment": "The lit centre; it rises and falls inside the cage."},
            {
                "name": "fins",
                "bone": [f"fin_{i}" for i in (1, 2, 3, 4)],
                "comment": "The four vanes, one per quadrant.",
            },
            {"name": "tail", "bone": "tail", "comment": "Trailing wisp. Gives the lamp a down direction."},
        ],
        "anim": [
            "float age = state.ageInTicks;",
            "",
            "this.shell.yRot += age * 0.03F;",
            "this.core.y += Mth.sin(age * 0.14F) * 0.6F;",
            "this.tail.xRot += Mth.cos(age * 0.09F) * 0.18F;",
            "this.tail.zRot += Mth.sin(age * 0.07F) * 0.14F;",
            "",
            "for (int i = 0; i < this.fins.length; i++) {",
            "    float phase = i * ((float) Math.PI / 2.0F);",
            "    this.fins[i].xRot += Mth.cos(age * 0.18F + phase) * 0.35F;",
            "    this.fins[i].y += Mth.sin(age * 0.18F + phase) * 0.4F;",
            "}",
        ],
    },
    "tuner_shade": {
        "class_name": "TunerShadeModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The tuner shade: a hooded robed caster carrying a spinning resonator ring.",
            "",
            "<p>The head tracks, because the shade is the one creature in the dimension that",
            "looks at you rather than at where you are going. Below the waist there is only",
            "robe: it leads the walk cycle by half a beat and swings on a longer period than",
            "the shoulders, which is what makes cloth read as cloth on a rig with no legs.",
            "",
            "<p>The ring never stops turning, at a rate unrelated to anything else on the model.",
            "It is the creature's tell - a shade with its ring up is about to fire - so it has to",
            "be legible at the distance the bolt is fired from.",
        ],
        "fields": [
            {"name": "head", "bone": "head", "comment": "Hood. Tracks the look direction."},
            {"name": "torso", "bone": "torso", "comment": "Upper body above the waist."},
            {"name": "robe", "bone": "robe", "comment": "The skirt and hem; there are no legs under it."},
            {"name": "mantle", "bone": "mantle", "comment": "Shoulder mantle. Breathes on a slow idle."},
            {
                "name": "armUppers",
                "bone": ["arm_l_upper", "arm_r_upper"],
                "comment": "Upper arms, left then right.",
            },
            {
                "name": "armLowers",
                "bone": ["arm_l_lower", "arm_r_lower"],
                "comment": "Forearms, in the same order as armUppers.",
            },
            {"name": "ring", "bone": "ring", "comment": "The resonator. Spins constantly."},
            {"name": "spark", "bone": "spark", "comment": "The mote held inside the ring."},
        ],
        "anim": [
            "float pos = state.walkAnimationPos * 0.6F;",
            "float speed = Math.min(state.walkAnimationSpeed, 0.8F);",
            "float age = state.ageInTicks;",
            "",
            "this.head.xRot += state.xRot * ((float) Math.PI / 180.0F);",
            "this.head.yRot += state.yRot * ((float) Math.PI / 180.0F);",
            "",
            "// The robe leads the shoulders and swings wider, so it reads as cloth.",
            "this.robe.yRot += Mth.cos(pos * 0.5F) * 0.10F * speed;",
            "this.robe.xRot += Mth.cos(pos) * 0.06F * speed;",
            "this.mantle.zRot += Mth.cos(age * 0.05F) * 0.03F;",
            "this.torso.xRot += Mth.cos(pos) * 0.04F * speed;",
            "",
            "for (int i = 0; i < this.armUppers.length; i++) {",
            "    float side = i == 0 ? -1.0F : 1.0F;",
            "    float phase = i == 0 ? 0.0F : (float) Math.PI;",
            "    this.armUppers[i].xRot += Mth.cos(pos + phase) * 0.5F * speed;",
            "    this.armUppers[i].zRot += side * (0.05F + Mth.cos(age * 0.07F) * 0.03F);",
            "    this.armLowers[i].xRot -= Math.abs(Mth.sin(pos + phase)) * 0.3F * speed;",
            "}",
            "",
            "this.ring.zRot += age * 0.09F;",
            "this.ring.y += Mth.sin(age * 0.11F) * 0.5F;",
            "this.spark.yRot += age * 0.22F;",
        ],
    },
    "strata_burrower": {
        "class_name": "StrataBurrowerModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The strata burrower: wedge head, paired mandibles, three body segments and six",
            "stubby digging claws.",
            "",
            "<p>The body carries a yaw wave that starts at the snout and lags a fixed amount per",
            "segment, so the animal swims through the ground rather than sliding over it. Only",
            "the amplitude scales with movement speed; the wave itself is always running,",
            "because a burrower that has stopped is still chewing.",
            "",
            "<p>The legs use the weaver's gait with the ranks re-phased for three pairs instead",
            "of four, which keeps three feet planted at all times. The dorsal ridges move on",
            "their own slow idle - they are what the player is meant to be watching for, so they",
            "must never be perfectly still.",
        ],
        "fields": [
            {"name": "head", "bone": "head", "comment": "Wedge head. Tracks, but only partly - the neck is armour."},
            {
                "name": "mandibles",
                "bone": ["mandible_l", "mandible_r"],
                "comment": "The digging jaws. They chew on an idle of their own.",
            },
            {
                "name": "segments",
                "bone": ["segment_mid", "segment_tail"],
                "comment": "Body segments behind the shoulders, front to back.",
            },
            {"name": "tailSpur", "bone": "tail_spur", "comment": "The anchoring spur at the very back."},
            {
                "name": "ridges",
                "bone": ["ridge_fore", "ridge_aft"],
                "comment": "Dorsal plates - the part visible above ground while it is burrowed.",
            },
            {
                "name": "legUppers",
                "bone": [f"{leg}_upper" for leg in BURROWER_LEGS],
                "comment": "Hip segments, left rank first. Index order matches legClaws.",
            },
            {
                "name": "legClaws",
                "bone": [f"{leg}_claw" for leg in BURROWER_LEGS],
                "comment": "Digging claws; they counter-flex against the hip's lift.",
            },
        ],
        "anim": [
            "float pos = state.walkAnimationPos * 0.7F;",
            "float speed = Math.min(state.walkAnimationSpeed, 0.9F);",
            "float age = state.ageInTicks;",
            "",
            "// A yaw wave from snout to tail, each segment lagging the one ahead of it.",
            "this.head.yRot += state.yRot * ((float) Math.PI / 180.0F) * 0.35F",
            "        + Mth.cos(pos) * 0.12F * speed;",
            "this.head.xRot += state.xRot * ((float) Math.PI / 180.0F) * 0.25F;",
            "this.segments[0].yRot += Mth.cos(pos - 0.8F) * 0.18F * speed;",
            "this.segments[1].yRot += Mth.cos(pos - 1.6F) * 0.26F * speed;",
            "this.tailSpur.yRot += Mth.cos(pos - 2.4F) * 0.32F * speed;",
            "",
            "for (int i = 0; i < this.mandibles.length; i++) {",
            "    float side = i == 0 ? -1.0F : 1.0F;",
            "    this.mandibles[i].yRot += side * (0.18F + Mth.cos(age * 0.25F) * 0.18F);",
            "}",
            "",
            "for (int i = 0; i < this.ridges.length; i++) {",
            "    this.ridges[i].xRot += Mth.cos(age * 0.06F + i * 0.9F) * 0.05F;",
            "}",
            "",
            "for (int i = 0; i < this.legUppers.length; i++) {",
            "    boolean left = i < 3;",
            "    float phase = (i % 3) * ((float) Math.PI * 2.0F / 3.0F)",
            "            + (left ? 0.0F : (float) Math.PI);",
            "    float side = left ? -1.0F : 1.0F;",
            "    float swing = Mth.cos(pos * 2.0F + phase) * 0.5F * speed;",
            "    float lift = Math.abs(Mth.sin(pos + phase)) * 0.35F * speed;",
            "    this.legUppers[i].yRot += swing * side;",
            "    this.legUppers[i].zRot += lift * side;",
            "    this.legClaws[i].zRot -= lift * 0.7F * side;",
            "}",
        ],
    },
    "tuner_trader": {
        "class_name": "TunerTraderModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The tuner trader: a robed, hatted figure with a satchel of goods.",
            "",
            "<p>A plain walk cycle - the whole point of the silhouette is that it reads as",
            "an ordinary person, so the gait has to look ordinary too, unlike every other",
            "creature down here which is deliberately built not to walk like one.",
        ],
        "fields": [
            {"name": "head", "bone": "head", "comment": "Tracks the look direction."},
            {"name": "legs", "bone": "legs", "comment": "Both legs swing together as one bone - a robe hem, not a stride."},
            {"name": "satchel", "bone": "satchel", "comment": "Sways a beat behind the torso."},
            {
                "name": "armUppers",
                "bone": ["arm_l_upper", "arm_r_upper"],
                "comment": "Upper arms, left then right.",
            },
        ],
        "anim": [
            "float pos = state.walkAnimationPos;",
            "float speed = Math.min(state.walkAnimationSpeed, 1.0F);",
            "float age = state.ageInTicks;",
            "",
            "this.head.xRot += state.xRot * ((float) Math.PI / 180.0F);",
            "this.head.yRot += state.yRot * ((float) Math.PI / 180.0F);",
            "",
            "this.legs.xRot += Mth.cos(pos) * 0.15F * speed;",
            "this.satchel.zRot += Mth.cos(age * 0.08F) * 0.06F;",
            "",
            "for (int i = 0; i < this.armUppers.length; i++) {",
            "    float side = i == 0 ? -1.0F : 1.0F;",
            "    this.armUppers[i].xRot += Mth.cos(pos + (i == 0 ? 0.0F : (float) Math.PI)) * 0.3F * speed;",
            "}",
        ],
    },
    "tuners_protector": {
        "class_name": "TunersProtectorModel",
        "imports": ("net.minecraft.util.Mth",),
        "javadoc": [
            "The tuner's protector: an iron-golem-shaped guardian built from oversized",
            "plate limbs.",
            "",
            "<p>The walk is heavy and slightly delayed - each arm trails the opposite leg",
            "rather than swinging with it, which is what makes something this wide read as",
            "SLOW and DANGEROUS rather than comically stiff. The head barely moves; it is a",
            "block of plate, not a face, and over-animating it undercuts the whole design.",
        ],
        "fields": [
            {"name": "head", "bone": "head", "comment": "Minimal tracking - this is armour, not a face."},
            {"name": "legs", "bone": "legs", "comment": "Both legs, stepping together as a single heavy bone."},
            {
                "name": "armUppers",
                "bone": ["arm_l_upper", "arm_r_upper"],
                "comment": "The oversized upper arms, left then right.",
            },
        ],
        "anim": [
            "float pos = state.walkAnimationPos * 0.7F;",
            "float speed = Math.min(state.walkAnimationSpeed, 0.8F);",
            "",
            "this.head.yRot += state.yRot * ((float) Math.PI / 180.0F) * 0.15F;",
            "this.legs.xRot += Mth.cos(pos) * 0.10F * speed;",
            "",
            "for (int i = 0; i < this.armUppers.length; i++) {",
            "    float phase = i == 0 ? (float) Math.PI : 0.0F;",
            "    this.armUppers[i].xRot -= Mth.cos(pos + phase) * 0.25F * speed;",
            "}",
        ],
    },
}


# ---------------------------------------------------------------------------

def write_geometry() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (builder, bw, bh, off) in BUILDERS.items():
        model = builder()
        data = model.to_json(bw, bh, off)
        (OUT_DIR / f"{name}.geo.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")

        bones = data["minecraft:geometry"][0]["bones"]
        cubes = sum(len(b["cubes"]) for b in bones)
        used = model.atlas.used_pixels()
        total = model.tex_w * model.tex_h
        print(f"{name}.geo.json: {len(bones)} bones, {cubes} cubes, "
              f"{len(model.atlas.rects)} uv rects, "
              f"atlas {used}/{total} px ({used * 100 // total}%)")


def write_model_classes() -> None:
    """Drive gen_entity_models' Java writer over our geometry and animations."""
    out_dir = gen_entity_models.OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in sorted(ANIMATIONS):
        geo = gen_entity_models.Geometry(gen_entity_models.GEO_DIR / f"{name}.geo.json")
        if geo.identifier != f"geometry.{name}":
            raise ValueError(
                f"{geo.path.name} declares {geo.identifier!r}, expected 'geometry.{name}'")

        spec = dict(ANIMATIONS[name], model_id=name)
        source = gen_entity_models.render_class(geo, spec)
        (out_dir / f"{spec['class_name']}.java").write_text(source, encoding="utf-8")

        depth = max(len(geo.chain(b.name)) for b in geo.bones)
        print(f"{spec['class_name']}.java: {len(geo.bones)} parts, {geo.cube_count} cubes, "
              f"{geo.tex_w}x{geo.tex_h} sheet, tree depth {depth}, "
              f"{len(source.splitlines())} lines")


def main() -> int:
    write_geometry()
    write_model_classes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

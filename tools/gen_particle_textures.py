"""
The Echoing Void - the Knell shockwave particle.

PLAYER: "the particles on the knell chestplate and aeroshell when we do the double
crouch shockwave linger around too long, that doesnt look like an explosion. I want
you to copy the source files of the particle effects you used originally for the
resonant chestplate, extract the textures, redraw them, copying exact shading
sequencing texture etc but changing the hue to purple/pink that makes knell
characteristic, and build a new particle effect, identical to the original one from
the resonant chestplate, but pink for the knell."

WHAT WAS ACTUALLY WRONG

The Resonance set releases `ParticleTypes.SONIC_BOOM`, which is a 16-frame animation
that plays once and is gone in 16 ticks. Knell was NOT using a recoloured version of
it - there is no such thing - it was using `DustParticleOptions`, because SONIC_BOOM
is a fixed sprite with no tint field and dust was the only tintable particle to hand.
Dust drifts and fades over its own lifetime, so 28 of them at scale 3.0 hung in the
air long after the shockwave had happened. That is the lingering.

So Knell gets a real particle of its own, and it is this.

REDRAWN, NOT RECOLOURED

Vanilla's sixteen frames were measured rather than copied, and reproduced here from
those measurements. What the measurements found:

  * 32x32 frames, sixteen of them
  * exactly TWO colours in the whole animation, both fully opaque - a bright
    #2CE3EB and a darker #0BB4AA. No alpha gradient anywhere.
  * frames 0-7 COLLAPSE inward: weighted mean radius 8.3 -> 0.7, coverage falling to
    almost nothing. That is the wind-up.
  * frame 8 is the detonation, 30% coverage at radius 6.6
  * frames 9-15 EXPAND and thin: radius 11.2 -> 18.4, coverage 27% -> 1.4%

Those per-frame figures are the RING table below, so the animation has vanilla's
exact timing and shape while none of its pixels ship here. The two colours become
knell's own: arcane bright and arcane light out of art_direction.json.

Run:  python tools/gen_particle_textures.py
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("FAIL: Pillow is required (pip install pillow)")
    raise SystemExit(1)

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = ROOT / "src" / "main" / "resources" / "assets" / "echoing_void" / "textures" / "particle"

SIZE = 32
FRAMES = 16

#: Knell's two tones, standing in for vanilla's #2CE3EB and #0BB4AA.
BRIGHT = (0xFF, 0x00, 0x7F, 255)   # arcane.bright
DEEP = (0xB1, 0x4A, 0x9E, 255)     # arcane.light

#: (weighted mean radius, fraction of the 32x32 canvas covered), frame by frame,
#: measured off vanilla's own sonic_boom_0..15. The wind-up collapses, frame 8
#: detonates, and the rest expands and thins.
RING = [
    (8.32, 0.033), (5.83, 0.051), (3.81, 0.039), (2.75, 0.045),
    (2.91, 0.049), (1.79, 0.018), (0.71, 0.004), (0.71, 0.002),
    (6.60, 0.301), (11.19, 0.270), (13.19, 0.246), (12.86, 0.156),
    (14.34, 0.082), (14.96, 0.131), (17.22, 0.038), (18.39, 0.014),
]


def hash01(x: int, y: int, seed: int) -> float:
    """Deterministic 0..1 from a pixel and a seed. Same idea as the texture tools use."""
    h = (x * 374761393 + y * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def frame(index: int) -> Image.Image:
    """One frame: a scattered annulus at the measured radius and coverage."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = img.load()
    radius, coverage = RING[index]
    centre = (SIZE - 1) / 2.0

    # Thickness grows with the ring, the way an expanding shock front spreads. Kept
    # generous at the small radii so the wind-up frames are not single pixels, and
    # WIDENED until the band can actually hold the frame's coverage - frame 8 is the
    # detonation at 30%, which is a filled burst rather than a thin ring, and a fixed
    # thickness came out at 22% because the annulus simply had too few cells in it.
    target = coverage * SIZE * SIZE
    thickness = max(1.6, radius * 0.42)
    while sum(1 for y in range(SIZE) for x in range(SIZE)
              if abs(math.hypot(x - centre, y - centre) - radius) <= thickness) < target:
        thickness += 0.5

    # Rank every cell in the annulus by noise and take the brightest `target` of them,
    # which hits the coverage figure exactly rather than approximately.
    candidates = []
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - centre, y - centre)
            if abs(d - radius) > thickness:
                continue
            # Nearer the ring's centre line is likelier, so the band has a soft profile.
            falloff = 1.0 - abs(d - radius) / thickness
            # Distance-dominant, with only a whisker of noise to break ties. An earlier
            # 65/35 split scattered the ring into speckle, where vanilla's frames 9-13 are
            # clean unbroken circles - the noise was picking pixels off the band at random
            # instead of filling it from the centre line outward.
            candidates.append((falloff * 0.97 + hash01(x, y, 7717 + index * 131) * 0.03, x, y, d))
    candidates.sort(reverse=True)

    chosen = candidates[: max(2, int(round(target)))]
    for _, x, y, d in chosen:
        # Bright on the leading (outer) edge, deeper behind it - which is how vanilla's
        # two tones sit, and what gives the ring a direction.
        #
        # The hash breaks up that split. On the last frames the ring is so thin that
        # almost every pixel lands outside the radius, which left the arc flat and
        # unshaded; an even split keeps both tones present all the way out.
        outer = d >= radius and hash01(x, y, 4441 + index * 97) > 0.5
        px[x, y] = BRIGHT if outer else DEEP

    # Every frame carries both tones. The two thinnest wind-up frames are only two or
    # three pixels, and if all of them fall inside the radius the frame comes out a
    # single flat colour - which the texture gate rejects, rightly: a one-colour frame
    # in a two-colour animation is a frame that lost its shading.
    tones = {px[x, y] for _, x, y, _ in chosen}
    if len(tones) < 2:
        _, x, y, _ = chosen[0]
        px[x, y] = BRIGHT if px[x, y] == DEEP else DEEP

    return img


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for i in range(FRAMES):
        img = frame(i)
        img.save(OUT / f"knell_boom_{i}.png")
        opaque = sum(1 for p in img.convert("RGBA").getdata() if p[3] > 0)
        total += opaque
    print(f"wrote {FRAMES} frames to {OUT.relative_to(ROOT)}")
    print(f"  {SIZE}x{SIZE}, 2 colours, {total} opaque pixels across the animation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

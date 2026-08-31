package com.echoingvoid.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.SingleQuadParticle;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.util.RandomSource;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.api.distmarker.OnlyIn;

/**
 * The Knell shockwave, drawn exactly as vanilla draws its sonic boom.
 *
 * <p>Every figure here is {@code SonicBoomParticle}'s, which is itself a {@code
 * HugeExplosionParticle} with three fields changed: a lifetime of 16 ticks, a quad size of 1.5,
 * full brightness regardless of the light where it spawned, and the sprite chosen from the
 * particle's AGE rather than at random, so the sixteen frames play in order as an animation.
 *
 * <p>PLAYER: "the particles... linger around too long, that doesnt look like an explosion." They
 * did, and this is why. Knell was releasing {@code DustParticleOptions}, because
 * {@code ParticleTypes.SONIC_BOOM} is a fixed sprite with no tint field and dust was the only
 * tintable particle to hand. Dust drifts and fades on its own schedule, so twenty-eight of them at
 * triple scale hung in the air long after the shockwave was over. A boom that plays sixteen frames
 * and stops is what an explosion looks like.
 *
 * <p>It does not subclass {@code SonicBoomParticle} or {@code HugeExplosionParticle}: both have
 * protected constructors in another package. The behaviour is reimplemented instead, and it is
 * four numbers.
 */
@OnlyIn(Dist.CLIENT)
public class KnellBoomParticle extends SingleQuadParticle {

    private final SpriteSet sprites;

    protected KnellBoomParticle(ClientLevel level, double x, double y, double z, SpriteSet sprites) {
        super(level, x, y, z, 0.0, 0.0, 0.0, sprites.first());
        this.sprites = sprites;
        this.lifetime = 16;
        this.quadSize = 1.5F;
        this.setSpriteFromAge(sprites);
    }

    /**
     * Full-bright. A shockwave lights itself, and without this the release looks dim in the very
     * caves it is most likely to go off in.
     */
    @Override
    public int getLightCoords(float partialTick) {
        return 15728880;
    }

    @Override
    public void tick() {
        this.xo = this.x;
        this.yo = this.y;
        this.zo = this.z;
        if (this.age++ >= this.lifetime) {
            this.remove();
        } else {
            // The front expands because the ARTWORK expands, frame by frame - the particle
            // itself never moves. That is what keeps it one clean ring instead of a cloud
            // drifting apart, and it is how vanilla's boom does it too.
            this.setSpriteFromAge(this.sprites);
        }
    }

    @Override
    public SingleQuadParticle.Layer getLayer() {
        return SingleQuadParticle.Layer.OPAQUE;
    }

    @OnlyIn(Dist.CLIENT)
    public static class Provider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites;

        public Provider(SpriteSet sprites) {
            this.sprites = sprites;
        }

        @Override
        public Particle createParticle(SimpleParticleType options, ClientLevel level,
                                       double x, double y, double z,
                                       double xa, double ya, double za, RandomSource random) {
            return new KnellBoomParticle(level, x, y, z, this.sprites);
        }
    }
}

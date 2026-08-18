package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.TunerShadeModel;
import com.echoingvoid.entity.TunerShadeEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the tuner shade.
 *
 * <p>A normal humanoid shadow, sized to the robe rather than to the shoulders, because the hem is
 * what actually meets the floor. The glow pass carries the two hood eyes, the chest sigil and the
 * resonator ring - between them they are the whole read at distance, which matters for a creature
 * the player is supposed to identify before it starts casting.
 */
public class TunerShadeRenderer extends MobRenderer<TunerShadeEntity, LivingEntityRenderState, TunerShadeModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/tuner_shade.png");

    public TunerShadeRenderer(EntityRendererProvider.Context context) {
        super(context, new TunerShadeModel(context.bakeLayer(TunerShadeModel.LAYER)), 0.45F);
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/tuner_shade_glow.png")));
    }

    @Override
    public Identifier getTextureLocation(LivingEntityRenderState state) {
        return TEXTURE;
    }

    @Override
    public LivingEntityRenderState createRenderState() {
        return new LivingEntityRenderState();
    }
}

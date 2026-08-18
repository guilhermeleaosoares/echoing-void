package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.ResonanceWraithModel;
import com.echoingvoid.entity.ResonanceWraithEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the resonance wraith.
 *
 * <p>The model itself asks for the translucent render type, so nothing extra is needed here. The
 * shadow is kept small and the light level is not overridden: a wraith should be genuinely hard to
 * see coming in an unlit cavern, and the only reliable warning is the sound it attacks with.
 */
public class ResonanceWraithRenderer extends MobRenderer<ResonanceWraithEntity, LivingEntityRenderState, ResonanceWraithModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/resonance_wraith.png");

    public ResonanceWraithRenderer(EntityRendererProvider.Context context) {
        super(context, new ResonanceWraithModel(context.bakeLayer(ResonanceWraithModel.LAYER)), 0.4F);
        // Emissive pass: draws resonance_wraith_glow.png at full brightness so the creature
        // reads in an unlit cave rather than vanishing into the rock.
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/resonance_wraith_glow.png")));
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

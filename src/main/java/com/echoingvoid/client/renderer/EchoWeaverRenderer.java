package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.EchoWeaverModel;
import com.echoingvoid.entity.EchoWeaverEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the echo weaver.
 *
 * <p>The shadow is deliberately wide for the weaver's hitbox: the animal is mostly leg, and a
 * shadow sized to the body alone makes a ceiling ambusher hard to spot as it drops. The death
 * flip is the spider's - a weaver rolls onto its back rather than toppling sideways.
 */
public class EchoWeaverRenderer extends MobRenderer<EchoWeaverEntity, LivingEntityRenderState, EchoWeaverModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/echo_weaver.png");

    public EchoWeaverRenderer(EntityRendererProvider.Context context) {
        super(context, new EchoWeaverModel(context.bakeLayer(EchoWeaverModel.LAYER)), 0.7F);
        // Emissive pass: draws echo_weaver_glow.png at full brightness so the creature
        // reads in an unlit cave rather than vanishing into the rock.
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/echo_weaver_glow.png")));
    }

    @Override
    protected float getFlipDegrees() {
        return 180.0F;
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

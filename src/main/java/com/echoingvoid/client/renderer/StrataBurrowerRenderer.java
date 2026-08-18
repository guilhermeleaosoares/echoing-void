package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.StrataBurrowerModel;
import com.echoingvoid.entity.StrataBurrowerEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the strata burrower.
 *
 * <p>A wide shadow, matching the creature's footprint rather than its height: it is three and a half
 * blocks long and barely one tall, and a shadow sized to the height would leave the back half of a
 * surfaced burrower floating.
 *
 * <p>Nothing here has to handle the burrowed state. While the creature is under the floor the server
 * marks it invisible, so the body is simply not submitted, and the tell the player follows is the
 * plume of rock the entity throws out at the surface above itself.
 *
 * <p>The glow pass draws the dorsal ridges and the eye cluster. Those are the two things that have
 * to be identifiable the instant it comes up, and both are dim by design - the burrower is made of
 * the same rock as the floor and is meant to be hard to see once it has stopped moving.
 */
public class StrataBurrowerRenderer
        extends MobRenderer<StrataBurrowerEntity, LivingEntityRenderState, StrataBurrowerModel> {

    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/strata_burrower.png");

    public StrataBurrowerRenderer(EntityRendererProvider.Context context) {
        super(context, new StrataBurrowerModel(context.bakeLayer(StrataBurrowerModel.LAYER)), 1.1F);
        this.addLayer(new CreatureGlowLayer<>(this,
                EchoingVoid.id("textures/entity/strata_burrower_glow.png")));
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

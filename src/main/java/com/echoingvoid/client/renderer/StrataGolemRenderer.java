package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.StrataGolemModel;
import com.echoingvoid.entity.StrataGolemEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the strata golem.
 *
 * <p>The shadow is sized to the chassis rather than the hitbox. A golem is a territorial marker as
 * much as a mob, and a broad shadow is the first thing a player reads at range in a dim dimension.
 */
public class StrataGolemRenderer extends MobRenderer<StrataGolemEntity, LivingEntityRenderState, StrataGolemModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/strata_golem.png");

    public StrataGolemRenderer(EntityRendererProvider.Context context) {
        super(context, new StrataGolemModel(context.bakeLayer(StrataGolemModel.LAYER)), 1.1F);
        // Emissive pass: draws strata_golem_glow.png at full brightness so the creature
        // reads in an unlit cave rather than vanishing into the rock.
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/strata_golem_glow.png")));
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

package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.TunersProtectorModel;
import com.echoingvoid.entity.ProtectorMob;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the tuner's protector.
 *
 * <p>Iron-golem-radius shadow (0.9F, matching vanilla's own golem), which is noticeably wider
 * than any of the other new creatures - the point is that its footprint reads as heavy from
 * across the outpost, well before the player is close enough to see the plating.
 *
 * <p>The glow pass carries the lit eye slits painted in {@code gen_new_creature_textures.py}'s
 * {@code protector_head} - the one feature this deliberately face-less guardian has.
 */
public class ProtectorMobRenderer
        extends MobRenderer<ProtectorMob, LivingEntityRenderState, TunersProtectorModel> {

    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/tuners_protector.png");

    public ProtectorMobRenderer(EntityRendererProvider.Context context) {
        super(context, new TunersProtectorModel(context.bakeLayer(TunersProtectorModel.LAYER)), 0.9F);
        this.addLayer(new CreatureGlowLayer<>(this,
                EchoingVoid.id("textures/entity/tuners_protector_glow.png")));
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

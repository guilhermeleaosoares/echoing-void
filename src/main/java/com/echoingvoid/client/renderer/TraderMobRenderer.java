package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.TunerTraderModel;
import com.echoingvoid.entity.TraderMob;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the tuner trader.
 *
 * <p>One look for both settlements - what tells outpost and camp traders apart is the trade
 * table {@link TraderMob#variety()} selects, not the texture. A second robe colour per variety
 * is a reasonable future addition, but not one to invent unasked in the middle of an already
 * large art pass.
 */
public class TraderMobRenderer extends MobRenderer<TraderMob, LivingEntityRenderState, TunerTraderModel> {

    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/tuner_trader.png");

    public TraderMobRenderer(EntityRendererProvider.Context context) {
        super(context, new TunerTraderModel(context.bakeLayer(TunerTraderModel.LAYER)), 0.5F);
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

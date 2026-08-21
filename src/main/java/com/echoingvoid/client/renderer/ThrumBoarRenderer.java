package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.ThrumBoarModel;
import com.echoingvoid.entity.ThrumBoarEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the thrum boar.
 *
 * <p>A grazing animal that stands on the ground, so unlike the drifting creatures in this mod it
 * gets a real shadow - a floating farm animal reads as a bug immediately.
 *
 * <p>The emissive pass is what ties it to the dimension: the body is muted stone-and-hide, and the
 * resonating parts only read as lit because {@code thrum_boar_glow.png} draws them at full brightness.
 */
public class ThrumBoarRenderer extends MobRenderer<ThrumBoarEntity, LivingEntityRenderState, ThrumBoarModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/thrum_boar.png");

    public ThrumBoarRenderer(EntityRendererProvider.Context context) {
        super(context, new ThrumBoarModel(context.bakeLayer(ThrumBoarModel.LAYER)), 0.5F);
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/thrum_boar_glow.png")));
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

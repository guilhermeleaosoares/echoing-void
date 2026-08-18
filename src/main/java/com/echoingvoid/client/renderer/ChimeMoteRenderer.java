package com.echoingvoid.client.renderer;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.client.model.ChimeMoteModel;
import com.echoingvoid.entity.ChimeMoteEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.resources.Identifier;

/**
 * Draws the chime mote.
 *
 * <p>Almost no shadow. The mote never touches the ground, and a lantern that casts a hard disc under
 * itself reads as an object resting on the floor rather than as something hanging in the air.
 *
 * <p>Most of what the player sees is the emissive pass: the cage is null-iron and nearly black, and
 * the core, vanes and tail wisp only exist as a shape because {@code chime_mote_glow.png} draws them
 * at full brightness. That is the point of the creature - it is a light first and an animal second.
 */
public class ChimeMoteRenderer extends MobRenderer<ChimeMoteEntity, LivingEntityRenderState, ChimeMoteModel> {
    private static final Identifier TEXTURE = EchoingVoid.id("textures/entity/chime_mote.png");

    public ChimeMoteRenderer(EntityRendererProvider.Context context) {
        super(context, new ChimeMoteModel(context.bakeLayer(ChimeMoteModel.LAYER)), 0.2F);
        this.addLayer(new CreatureGlowLayer<>(this, EchoingVoid.id("textures/entity/chime_mote_glow.png")));
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

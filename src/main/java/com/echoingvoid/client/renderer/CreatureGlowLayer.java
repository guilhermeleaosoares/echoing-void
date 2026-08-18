package com.echoingvoid.client.renderer;

import net.minecraft.client.model.EntityModel;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.EyesLayer;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;

/**
 * The emissive pass that makes the creatures glow in the dark.
 *
 * <p>Each creature ships a second sheet - {@code <id>_glow.png} - painted only where light should
 * come out of it: the weaver's chitin seams, the golem's crystal spires, the wraith's core. This
 * layer draws that sheet at full brightness over the body, which is the same trick vanilla uses
 * for spider and enderman eyes, so the glow survives being in an unlit cave.
 *
 * <p>Sharing one layer across all three creatures is deliberate: they differ only by texture, and
 * {@link EyesLayer} already submits the parent model, so there is nothing per-creature to write.
 */
public class CreatureGlowLayer<M extends EntityModel<LivingEntityRenderState>>
        extends EyesLayer<LivingEntityRenderState, M> {

    private final RenderType renderType;

    public CreatureGlowLayer(RenderLayerParent<LivingEntityRenderState, M> renderer, Identifier glowTexture) {
        super(renderer);
        this.renderType = RenderTypes.eyes(glowTexture);
    }

    @Override
    public RenderType renderType() {
        return this.renderType;
    }
}

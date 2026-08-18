package com.echoingvoid.client;

import com.echoingvoid.client.model.ChimeMoteModel;
import com.echoingvoid.client.model.EchoWeaverModel;
import com.echoingvoid.client.model.ResonanceWraithModel;
import com.echoingvoid.client.model.StrataBurrowerModel;
import com.echoingvoid.client.model.StrataGolemModel;
import com.echoingvoid.client.model.TunerShadeModel;
import com.echoingvoid.client.model.TunerTraderModel;
import com.echoingvoid.client.model.TunersProtectorModel;
import com.echoingvoid.client.renderer.ChimeMoteRenderer;
import com.echoingvoid.client.renderer.EchoWeaverRenderer;
import com.echoingvoid.client.renderer.ProtectorMobRenderer;
import com.echoingvoid.client.renderer.ResonanceWraithRenderer;
import com.echoingvoid.client.renderer.StrataBurrowerRenderer;
import com.echoingvoid.client.renderer.StrataGolemRenderer;
import com.echoingvoid.client.renderer.TraderMobRenderer;
import com.echoingvoid.client.renderer.TunerShadeRenderer;
import com.echoingvoid.registry.ModEntities;
import com.echoingvoid.registry.ModNewEntities;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.fml.loading.FMLEnvironment;

/**
 * Client-side wiring for the five creatures: which mesh belongs to which model layer, and which
 * renderer draws which entity type.
 *
 * <p>Call {@link #register(BusGroup)} unconditionally from the mod constructor. It is a no-op on a
 * dedicated server. The client-only work lives in the nested {@link Wiring} class purely so that
 * nothing on a server's code path so much as names a client type - a static field of type
 * {@code ModelLayerLocation} on this class would be enough to fail class loading there, because
 * Forge strips {@code @OnlyIn(Dist.CLIENT)} classes out of the server runtime.
 */
public final class EchoingVoidClient {
    private EchoingVoidClient() {}

    /**
     * Attaches the client render listeners. Safe to call from the mod constructor on either side.
     *
     * @param modBusGroup the mod bus group from {@code FMLJavaModLoadingContext#getModBusGroup()}.
     *                    The two events used here are static-bus events rather than mod-bus ones,
     *                    so it is currently unused; it is taken anyway because every other
     *                    {@code register} in the mod takes it and because any future mod-bus
     *                    listener added here will need it.
     */
    public static void register(BusGroup modBusGroup) {
        if (FMLEnvironment.dist != Dist.CLIENT) {
            return;
        }
        Wiring.attach();
    }

    /**
     * The part that touches client classes. Loaded only once {@link #register(BusGroup)} has
     * confirmed it is running on a client.
     */
    private static final class Wiring {
        private Wiring() {}

        static void attach() {
            // EventBus 7: these are SelfDestructing static-bus events, not mod bus events, so they
            // are reached through the event class's own BUS field rather than through the mod bus
            // group. Forge posts both from ForgeHooksClient during client startup, after every mod
            // constructor has run.
            EntityRenderersEvent.RegisterLayerDefinitions.BUS.addListener(Wiring::onRegisterLayers);
            EntityRenderersEvent.RegisterRenderers.BUS.addListener(Wiring::onRegisterRenderers);
        }

        private static void onRegisterLayers(EntityRenderersEvent.RegisterLayerDefinitions event) {
            event.registerLayerDefinition(EchoWeaverModel.LAYER, EchoWeaverModel::createBodyLayer);
            event.registerLayerDefinition(StrataGolemModel.LAYER, StrataGolemModel::createBodyLayer);
            event.registerLayerDefinition(ResonanceWraithModel.LAYER, ResonanceWraithModel::createBodyLayer);
            event.registerLayerDefinition(ChimeMoteModel.LAYER, ChimeMoteModel::createBodyLayer);
            event.registerLayerDefinition(TunerShadeModel.LAYER, TunerShadeModel::createBodyLayer);
            event.registerLayerDefinition(StrataBurrowerModel.LAYER, StrataBurrowerModel::createBodyLayer);
            event.registerLayerDefinition(TunerTraderModel.LAYER, TunerTraderModel::createBodyLayer);
            event.registerLayerDefinition(TunersProtectorModel.LAYER, TunersProtectorModel::createBodyLayer);
        }

        private static void onRegisterRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(ModEntities.ECHO_WEAVER.get(), EchoWeaverRenderer::new);
            event.registerEntityRenderer(ModEntities.STRATA_GOLEM.get(), StrataGolemRenderer::new);
            event.registerEntityRenderer(ModEntities.RESONANCE_WRAITH.get(), ResonanceWraithRenderer::new);
            event.registerEntityRenderer(ModNewEntities.CHIME_MOTE.get(), ChimeMoteRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNER_SHADE.get(), TunerShadeRenderer::new);
            event.registerEntityRenderer(ModNewEntities.STRATA_BURROWER.get(), StrataBurrowerRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNER_TRADER.get(), TraderMobRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNERS_PROTECTOR.get(), ProtectorMobRenderer::new);
        }
    }
}

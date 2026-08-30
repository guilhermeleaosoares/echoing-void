package com.echoingvoid.client;

import com.echoingvoid.client.model.ChimeMoteModel;
import com.echoingvoid.client.model.DroneAurochModel;
import com.echoingvoid.client.model.ThrumBoarModel;
import com.echoingvoid.client.model.EchoWeaverModel;
import com.echoingvoid.client.model.ResonanceWraithModel;
import com.echoingvoid.client.model.StrataBurrowerModel;
import com.echoingvoid.client.model.StrataGolemModel;
import com.echoingvoid.client.model.TunerShadeModel;
import com.echoingvoid.client.model.TunerTraderModel;
import com.echoingvoid.client.model.TunersProtectorModel;
import com.echoingvoid.client.renderer.ChimeMoteRenderer;
import com.echoingvoid.client.renderer.DroneAurochRenderer;
import com.echoingvoid.client.renderer.ThrumBoarRenderer;
import com.echoingvoid.client.renderer.EchoWeaverRenderer;
import com.echoingvoid.client.renderer.ProtectorMobRenderer;
import com.echoingvoid.client.renderer.ResonanceWraithRenderer;
import com.echoingvoid.client.renderer.StrataBurrowerRenderer;
import com.echoingvoid.client.renderer.StrataGolemRenderer;
import com.echoingvoid.client.renderer.TraderMobRenderer;
import com.echoingvoid.client.renderer.TunerShadeRenderer;
import com.echoingvoid.EchoingVoid;
import com.echoingvoid.registry.ModEntities;
import com.echoingvoid.registry.ModFluids;
import com.echoingvoid.registry.ModKnell;
import com.echoingvoid.registry.ModMenus;
import com.echoingvoid.registry.ModNewEntities;
import com.echoingvoid.client.screen.IntegratorScreen;
import net.minecraft.client.gui.screens.MenuScreens;
import net.minecraft.client.renderer.block.FluidModel;
import net.minecraft.client.resources.model.sprite.Material;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RegisterItemDecorationsEvent;
import net.minecraftforge.client.event.ModelEvent;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;

/**
 * Client-side wiring: which mesh belongs to which model layer, which renderer draws which entity
 * type, and what hushwater is painted with.
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
        Wiring.attach(modBusGroup);
    }

    /**
     * The part that touches client classes. Loaded only once {@link #register(BusGroup)} has
     * confirmed it is running on a client.
     */
    private static final class Wiring {
        private Wiring() {}

        static void attach(BusGroup modBusGroup) {
            // EventBus 7: these are SelfDestructing static-bus events, not mod bus events, so they
            // are reached through the event class's own BUS field rather than through the mod bus
            // group. Forge posts both from ForgeHooksClient during client startup, after every mod
            // constructor has run.
            EntityRenderersEvent.RegisterLayerDefinitions.BUS.addListener(Wiring::onRegisterLayers);
            EntityRenderersEvent.RegisterRenderers.BUS.addListener(Wiring::onRegisterRenderers);
            // Not SelfDestructing, unlike the two above: this one is re-posted on every model
            // bake, so the listener has to survive the first one.
            ModelEvent.BakeFluidModels.BUS.addListener(Wiring::onBakeFluidModels);
            // The Aeroshell's second durability bar. A slot hosts one built-in bar, so the
            // wings get a decorator drawn over the top of the stock one.
            RegisterItemDecorationsEvent.BUS.addListener(Wiring::onRegisterDecorations);

            // Screens are the exception: Forge 26.2 has no RegisterMenuScreensEvent, so the
            // binding goes on the MOD bus at client setup. MenuScreens.SCREENS is a plain HashMap
            // with no synchronisation, so this must be enqueued onto the main thread rather than
            // written from the parallel dispatch worker.
            FMLClientSetupEvent.getBus(modBusGroup).addListener(Wiring::onClientSetup);
        }

        private static void onRegisterDecorations(RegisterItemDecorationsEvent event) {
            event.register(ModKnell.AEROSHELL.get(), new AeroshellBarDecorator());
        }

        /** Binds the Knell Integrator's menu to the screen that draws it. */
        private static void onClientSetup(FMLClientSetupEvent event) {
            event.enqueueWork(() ->
                    MenuScreens.register(ModMenus.KNELL_INTEGRATOR.get(), IntegratorScreen::new));
        }

        /**
         * PLAYER: "fix the hushwawter as none of the textures load, its just black and purple".
         *
         * <p>This is the whole fix, and the handed-down diagnosis it replaces was wrong, so both
         * halves are worth writing down.
         *
         * <p>The lead said the three sprites were never stitched into the block atlas, and that the
         * mod needed an {@code assets/echoing_void/atlases/blocks.json} to put them there. It does
         * not. Vanilla's own {@code minecraft:blocks} atlas opens with a {@code minecraft:directory}
         * source over {@code textures/block}, and {@code DirectoryLister} runs that through
         * {@code ResourceManager#listResources}, which enumerates EVERY namespace - so
         * {@code echoing_void:block/hushwater_still} was already on the atlas. The proof is that
         * every other block this mod adds has a texture: if that lister were namespace-limited, the
         * whole mod would be chequerboard rather than one fluid.
         *
         * <p>What actually changed in 26.2 is that fluids stopped being drawn from
         * {@code IClientFluidTypeExtensions} at all. {@code FluidRenderer} asks
         * {@code FluidStateModelSet}, which {@code ModelManager} bakes from
         * {@code FluidStateModelSet.bake} - and that method returns a hard-coded four-entry map of
         * water and lava. Every other fluid in the game falls through to
         * {@code missingModels().fluid()}, which IS the black and purple. Forge's one seam is
         * {@code ModelEvent.BakeFluidModels}, posted immediately after that bake, and a fluid that
         * does not register there cannot be drawn. Grepping the 26.2 sources for
         * {@code getStillTexture} finds it in exactly two places, neither of them a renderer:
         * {@code DynamicFluidContainerModel}, for bucket items, and {@code ForgeMod}'s defaults.
         *
         * <p>Both the source and the flowing fluid are registered, to the same baked model -
         * {@code FluidStateModelSet#get} keys on the exact {@code Fluid} instance and a flowing
         * fluid is a different instance, which is why vanilla's map lists water twice too. The tint
         * source is left null rather than white: {@code BlockTintSource} is the per-position biome
         * tint, hushwater has none, and its sprites are already painted on the bismuth ramp.
         */
        private static void onBakeFluidModels(ModelEvent.BakeFluidModels event) {
            FluidModel model = new FluidModel.Unbaked(
                    new Material(EchoingVoid.id("block/hushwater_still")),
                    new Material(EchoingVoid.id("block/hushwater_flow")),
                    new Material(EchoingVoid.id("block/hushwater_overlay")),
                    null
            ).bake(event.materials(), () -> "Hushwater");
            event.register(ModFluids.HUSHWATER.get(), model);
            event.register(ModFluids.FLOWING_HUSHWATER.get(), model);
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
            event.registerLayerDefinition(DroneAurochModel.LAYER, DroneAurochModel::createBodyLayer);
            event.registerLayerDefinition(ThrumBoarModel.LAYER, ThrumBoarModel::createBodyLayer);
        }

        private static void onRegisterRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(ModEntities.ECHO_WEAVER.get(), EchoWeaverRenderer::new);
            event.registerEntityRenderer(ModEntities.STRATA_GOLEM.get(), StrataGolemRenderer::new);
            event.registerEntityRenderer(ModEntities.RESONANCE_WRAITH.get(), ResonanceWraithRenderer::new);
            event.registerEntityRenderer(ModNewEntities.CHIME_MOTE.get(), ChimeMoteRenderer::new);
            event.registerEntityRenderer(ModNewEntities.DRONE_AUROCH.get(), DroneAurochRenderer::new);
            event.registerEntityRenderer(ModNewEntities.THRUM_BOAR.get(), ThrumBoarRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNER_SHADE.get(), TunerShadeRenderer::new);
            event.registerEntityRenderer(ModNewEntities.STRATA_BURROWER.get(), StrataBurrowerRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNER_TRADER.get(), TraderMobRenderer::new);
            event.registerEntityRenderer(ModNewEntities.TUNERS_PROTECTOR.get(), ProtectorMobRenderer::new);
        }
    }
}

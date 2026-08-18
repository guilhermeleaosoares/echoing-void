package com.echoingvoid.client;

import com.echoingvoid.registry.ModBlocks;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.resources.Identifier;
import net.minecraft.util.ARGB;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.equipment.Equippable;
import net.minecraft.world.level.block.Block;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.AddGuiOverlayLayersEvent;
import net.minecraftforge.client.gui.overlay.ForgeLayeredDraw;
import net.minecraftforge.fml.loading.FMLEnvironment;

/**
 * Replaces the nether portal's purple screen tint while travelling through a Hollow Horizon portal.
 *
 * <p>Vanilla draws that tint in {@code Hud#extractPortalOverlay}, which blits the particle sprite of
 * {@code Blocks.NETHER_PORTAL} across the whole screen at an alpha driven by
 * {@code LocalPlayer#portalEffectIntensity}. Nothing about it asks which portal you are standing in,
 * so any block implementing {@code Portal} - including ours - gets the Nether's purple.
 *
 * <p>26.2 has no event around that single overlay. What it does have is Forge's layered HUD:
 * {@code Hud#extractCameraOverlays} is registered as the layer {@code minecraft:camera_overlay}
 * inside the {@code minecraft:pre_sleep_phase} stack, and {@link AddGuiOverlayLayersEvent} hands
 * every mod that stack before it is baked. So the layer is replaced rather than the overlay: our
 * replacement delegates straight back to vanilla in every case except the one we care about - a
 * player inside <em>our</em> portal - and paints the void effect for that case instead. The spyglass,
 * pumpkin and powder-snow overlays are still drawn on that path; only the purple is dropped.
 *
 * <p>Call {@link #register()} unconditionally; it is a no-op on a dedicated server. Every client
 * type is confined to the nested {@link Hooks} class so that loading this class on a server never
 * initialises one, exactly as {@link EchoingVoidClient} does.
 */
public final class VoidTravelOverlay {
    private VoidTravelOverlay() {}

    /** Attaches the HUD layer listener. Safe to call from the mod constructor on either side. */
    public static void register() {
        if (FMLEnvironment.dist != Dist.CLIENT) {
            return;
        }
        Hooks.attach();
    }

    /** The part that touches client classes; loaded only once {@link #register()} says it is safe. */
    private static final class Hooks {
        private Hooks() {}

        /** The dimension's ground tone: deep blue-black, the colour under everything else. */
        private static final int VOID_BLACK = 0x0B0D12;

        /** The cold harmonic. */
        private static final int BISMUTH_CYAN = 0x00E5FF;

        /** The warm one running against it. */
        private static final int ARCANE_MAGENTA = 0xFF007F;

        private static final Identifier POWDER_SNOW_OUTLINE =
                Identifier.withDefaultNamespace("textures/misc/powder_snow_outline.png");

        /**
         * Latched so the effect does not flip back to vanilla's purple half way through.
         * {@code portalEffectIntensity} keeps decaying for a second after the player steps out of
         * the sheet, by which point the block at their eyes is air again; without the latch the
         * overlay would change colour during the fade.
         */
        private static boolean inOurPortal;

        /** Our copy of the private field of the same name in {@link Hud}. */
        private static float scopeScale = 0.5F;

        static void attach() {
            // EventBus 7 static bus. Forge posts this from ForgeLayeredDraw#resolveLayers, which
            // runs when the Hud is constructed - after every mod constructor.
            AddGuiOverlayLayersEvent.BUS.addListener(Hooks::onAddLayers);
        }

        private static void onAddLayers(AddGuiOverlayLayersEvent event) {
            event.getLayeredDraw().replace(
                    ForgeLayeredDraw.PRE_SLEEP_STACK, ForgeLayeredDraw.CAMERA_OVERLAY, Hooks::extract);
        }

        private static void extract(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker) {
            Minecraft minecraft = Minecraft.getInstance();
            LocalPlayer player = minecraft.player;
            if (player == null) {
                minecraft.gui.hud.extractCameraOverlays(graphics, deltaTracker);
                return;
            }

            float partialTicks = deltaTracker.getGameTimeDeltaPartialTick(false);
            float intensity = Mth.lerp(partialTicks, player.oPortalEffectIntensity, player.portalEffectIntensity);

            if (intensity <= 0.0F) {
                inOurPortal = false;
                minecraft.gui.hud.extractCameraOverlays(graphics, deltaTracker);
                return;
            }

            if (isInsideOurPortal(player)) {
                inOurPortal = true;
            }

            if (!inOurPortal) {
                minecraft.gui.hud.extractCameraOverlays(graphics, deltaTracker);
                return;
            }

            // Everything vanilla's camera overlay layer draws, minus its portal branch. Reproduced
            // rather than delegated because the purple blit sits in the middle of that one method;
            // the pieces around it are all public.
            extractHeldOverlays(graphics, deltaTracker, minecraft, player);
            drawVoidTravel(graphics, minecraft, intensity, partialTicks);
        }

        /**
         * True while the camera is inside one of our portal blocks.
         *
         * <p>Eye first, feet second: a player crouching in a two-high frame has their eyes in the
         * lower block, and one walking in upright has them in the upper one.
         */
        private static boolean isInsideOurPortal(LocalPlayer player) {
            Block portal = ModBlocks.HOLLOW_HORIZON_PORTAL.get();
            BlockPos eye = BlockPos.containing(player.getEyePosition());
            return player.level().getBlockState(eye).is(portal)
                    || player.level().getBlockState(player.blockPosition()).is(portal);
        }

        private static void extractHeldOverlays(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker,
                                                Minecraft minecraft, LocalPlayer player) {
            Hud hud = minecraft.gui.hud;
            scopeScale = Mth.lerp(0.5F * deltaTracker.getGameTimeDeltaTicks(), scopeScale, 1.125F);

            if (minecraft.options.getCameraType().isFirstPerson()) {
                if (player.isScoping()) {
                    hud.extractSpyglassOverlay(graphics, scopeScale);
                } else {
                    scopeScale = 0.5F;
                    for (EquipmentSlot slot : EquipmentSlot.values()) {
                        ItemStack worn = player.getItemBySlot(slot);
                        Equippable equippable = worn.get(DataComponents.EQUIPPABLE);
                        if (equippable != null && equippable.slot() == slot && equippable.cameraOverlay().isPresent()) {
                            hud.extractTextureOverlay(graphics,
                                    equippable.cameraOverlay().get().withPath(p -> "textures/" + p + ".png"), 1.0F);
                        }
                    }
                }
            }

            if (player.getTicksFrozen() > 0) {
                hud.extractTextureOverlay(graphics, POWDER_SNOW_OUTLINE, player.getPercentFrozen());
            }
        }

        /**
         * The replacement effect: deep blue-black ground, the portal's own moving wave over it, and
         * two harmonics beating against each other at incommensurate rates so the screen never
         * settles into one flat colour.
         */
        private static void drawVoidTravel(GuiGraphicsExtractor graphics, Minecraft minecraft,
                                           float intensity, float partialTicks) {
            // Vanilla's own alpha ramp: quartic, so the screen stays nearly clear for the first half
            // of the dwell and then closes in fast, with a 0.2 floor once it has started at all.
            float alpha = intensity;
            if (alpha < 1.0F) {
                alpha *= alpha;
                alpha *= alpha;
                alpha = alpha * 0.8F + 0.2F;
            }

            int width = graphics.guiWidth();
            int height = graphics.guiHeight();

            graphics.fill(0, 0, width, height, ARGB.color(alpha * 0.9F, VOID_BLACK));

            // The animated sheet the player actually walked into, stretched over the screen. Taking
            // it from the block's particle material means it follows the .mcmeta animation, so the
            // wave on the screen is the same wave, at the same frame, as the one in the frame behind.
            TextureAtlasSprite sprite = minecraft.getModelManager()
                    .getBlockStateModelSet()
                    .getParticleMaterial(ModBlocks.HOLLOW_HORIZON_PORTAL.get().defaultBlockState())
                    .sprite();
            graphics.blitSprite(RenderPipelines.GUI_TEXTURED, sprite, 0, 0, width, height,
                    ARGB.white(alpha * 0.85F));

            float time = (minecraft.level == null ? 0L : minecraft.level.getGameTime()) + partialTicks;
            // Two rates that do not divide into each other, so the pair never lands back in phase
            // during the couple of seconds a player spends inside the portal.
            float cyan = 0.34F + 0.26F * Mth.sin(time * 0.17F);
            float magenta = 0.34F + 0.26F * Mth.sin(time * 0.11F + 2.2F);

            graphics.fillGradient(0, 0, width, height / 2,
                    ARGB.color(alpha * cyan, BISMUTH_CYAN), ARGB.color(0.0F, BISMUTH_CYAN));
            graphics.fillGradient(0, height / 2, width, height,
                    ARGB.color(0.0F, ARCANE_MAGENTA), ARGB.color(alpha * magenta, ARCANE_MAGENTA));
        }
    }
}

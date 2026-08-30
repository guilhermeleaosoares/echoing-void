package com.echoingvoid.client.screen;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.inventory.IntegratorMenu;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.inventory.ItemCombinerScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.player.Inventory;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.api.distmarker.OnlyIn;

/**
 * The Knell Integrator's screen.
 *
 * <p>PLAYER: "i want a modified GUI for the knell integrator", and, asked how far it should go, a
 * reskin over the same three slots. So this is a change of dress and nothing else: the slot
 * geometry in {@link IntegratorMenu} is the smithing table's to the pixel, and everything a player
 * already knows about template-base-addition still holds. The panel is phonolite with a magenta
 * resonator ring behind the slots, which is the station's own material and its own colour rather
 * than a recoloured smithing table.
 *
 * <p>Almost all of the work is {@link ItemCombinerScreen}'s: it blits the background from the
 * identifier handed to the constructor and drives the slot listener. Only the error icon is left to
 * implement, and this station has none to draw - the result slot simply stays empty when the three
 * inputs do not make anything, which is the same feedback the smithing table gives.
 */
@OnlyIn(Dist.CLIENT)
public class IntegratorScreen extends ItemCombinerScreen<IntegratorMenu> {

    private static final Identifier BACKGROUND =
            EchoingVoid.id("textures/gui/container/knell_integrator.png");

    public IntegratorScreen(IntegratorMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title, BACKGROUND);
        // Vanilla SmithingScreen's own title offset, and for vanilla's own reason: the
        // top-left of the panel is taken by the station's icon - a hammer there, a tuning
        // fork here - so a title at the default x 8 would sit on top of it. The inventory
        // label keeps its default.
        //
        // Nothing overrides the label COLOUR any more. The panel is pale again, so
        // AbstractContainerScreen's hard-coded 0xFF404040 is the right colour for it -
        // that override only existed because the previous dark panel made vanilla's grey
        // unreadable, which was a problem the dark panel created rather than solved.
        this.titleLabelX = 44;
        this.titleLabelY = 15;
    }

    @Override
    protected void extractErrorIcon(GuiGraphicsExtractor graphics, int xo, int yo) {
        // Nothing to draw. The vanilla smithing screen puts a red cross here when all three slots
        // are full and no recipe matched, which needs a DataSlot synced from the server for the
        // client to know. An empty result slot already says the same thing, so the station does
        // not pay for the extra sync.
    }
}

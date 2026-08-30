package com.echoingvoid.client;

import com.echoingvoid.item.KnellAeroshellItem;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.api.distmarker.OnlyIn;
import net.minecraftforge.client.IItemDecorator;

/**
 * The Aeroshell's SECOND durability bar - the wings.
 *
 * <p>PLAYER: "the knell aeroshell should have two different durability bars. 1 for wings, 1 for the
 * chestplate."
 *
 * <p>A slot hosts exactly one built-in bar, and that one stays the plate's so it means what it means
 * on every other piece of armour. This draws the wings' bar one row above it, which is the only
 * place in a 16x16 slot where a second bar fits without covering the item.
 *
 * <p>It is magenta rather than the stock green-to-red, for two reasons: it distinguishes the two
 * bars at a glance without needing a tooltip, and it is the knell note the rest of the tier already
 * runs on. The bar dims towards red as the wings wear, so a glance still reads as urgency.
 */
@OnlyIn(Dist.CLIENT)
public final class AeroshellBarDecorator implements IItemDecorator {

    /** Vanilla's bar geometry: 13 pixels wide, inset one from the slot's left edge. */
    private static final int BAR_WIDTH = 13;

    /** One row above the stock bar, which vanilla draws at y offset 13. */
    private static final int BAR_Y = 11;

    private static final int BACKING = 0xFF000000;

    @Override
    public boolean render(GuiGraphicsExtractor graphics, Font font, ItemStack stack,
                          int xOffset, int yOffset) {
        if (!KnellAeroshellItem.isAeroshell(stack)) {
            return false;
        }
        int left = KnellAeroshellItem.wingsLeft(stack);
        if (left >= KnellAeroshellItem.WING_MAX) {
            // A full pool draws nothing, exactly as an undamaged item shows no bar - a bar that is
            // always present stops carrying information.
            return false;
        }

        float fraction = (float) left / KnellAeroshellItem.WING_MAX;
        int width = Mth.clamp(Math.round(BAR_WIDTH * fraction), 0, BAR_WIDTH);

        // Magenta at full, sliding to red as it goes, so colour carries the same warning the
        // length does.
        int r = 0xFF;
        int g = Math.round(0x30 * fraction);
        int b = Math.round(0x7F * fraction);
        int colour = 0xFF000000 | (r << 16) | (g << 8) | b;

        graphics.fill(xOffset + 2, yOffset + BAR_Y, xOffset + 15, yOffset + BAR_Y + 2, BACKING);
        graphics.fill(xOffset + 2, yOffset + BAR_Y, xOffset + 2 + width, yOffset + BAR_Y + 1, colour);
        return true;
    }
}

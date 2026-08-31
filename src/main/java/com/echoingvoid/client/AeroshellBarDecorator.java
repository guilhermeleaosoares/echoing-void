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

    /**
     * Vanilla's own bar geometry, read off GuiGraphicsExtractor: left is x+2, the bar is 13
     * wide, its black backing occupies rows 13 and 14 and the coloured fill sits on row 13.
     */
    private static final int BAR_LEFT = 2;
    private static final int BAR_WIDTH = 13;

    /**
     * Row 15 - directly under vanilla's, and the last row the 16x16 slot has.
     *
     * <p>PLAYER: "the pink durability bar for the aeroshell needs to render below the green
     * durability bar." It was at row 11, ABOVE it. There is exactly one row left beneath
     * vanilla's two, so this bar is one pixel tall rather than two; the black backing and the
     * coloured fill share it, which still reads because the unfilled remainder stays black
     * exactly as vanilla's does.
     */
    private static final int BAR_Y = 15;

    private static final int BACKING = 0xFF000000;

    @Override
    public boolean render(GuiGraphicsExtractor graphics, Font font, ItemStack stack,
                          int xOffset, int yOffset) {
        if (!KnellAeroshellItem.isAeroshell(stack)) {
            return false;
        }
        int left = KnellAeroshellItem.wingsLeft(stack);

        // Hidden at full, exactly as vanilla hides an undamaged item's bar. PLAYER: "they
        // should only show up after each of their durabilities is below full, just like
        // vanilla. normal knell chestplate for instance, the durability bar only shows from
        // 943 durability below."
        //
        // This reverses what I did last round, when the complaint was that only one bar
        // showed - I made both permanent, which was the wrong fix for the right problem. The
        // problem was the pink bar being ABOVE the green one and easy to miss, not its being
        // hidden when there was nothing to report.
        if (left >= KnellAeroshellItem.WING_MAX) {
            return false;
        }

        float fraction = (float) left / KnellAeroshellItem.WING_MAX;
        int width = Mth.clamp(Math.round(BAR_WIDTH * fraction), 0, BAR_WIDTH);

        int r = 0xFF;
        int g = Math.round(0x30 * fraction);
        int b = Math.round(0x7F * fraction);
        int colour = 0xFF000000 | (r << 16) | (g << 8) | b;

        graphics.fill(xOffset + BAR_LEFT, yOffset + BAR_Y,
                xOffset + BAR_LEFT + BAR_WIDTH, yOffset + BAR_Y + 1, BACKING);
        graphics.fill(xOffset + BAR_LEFT, yOffset + BAR_Y,
                xOffset + BAR_LEFT + width, yOffset + BAR_Y + 1, colour);
        return true;
    }
}

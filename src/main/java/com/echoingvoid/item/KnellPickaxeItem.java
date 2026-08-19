package com.echoingvoid.item;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ToolMaterial;

/**
 * The Harmonic Pickaxe's rhythm-shatter, amplified: PLAYER - "the area break of the knell
 * pickaxe is amplified... 4x5, 5 wide 4 tall", correcting an earlier 4x4 square that never
 * actually delivered the rectangle. Same beat, same tolerance, same streak requirement as
 * {@link HarmonicPickaxeItem} - only the plane's shape changes.
 */
public class KnellPickaxeItem extends HarmonicPickaxeItem {

    public KnellPickaxeItem(Item.Properties properties) {
        super(properties);
    }

    @Override
    protected int widthLo() {
        return -2;
    }

    @Override
    protected int widthHi() {
        return 2; // -2..2 inclusive is five values: 5 wide, with an exact centre (5 is odd)
    }

    @Override
    protected int heightLo() {
        return -1;
    }

    @Override
    protected int heightHi() {
        // -1..2 inclusive is four values: 4 tall, no exact centre since 4 is even - biased
        // one step positive rather than symmetric, same call the previous 4x4 made and for
        // the same reason: "wider" reads better than "shifted" once the blocks are gone.
        return 2;
    }
}

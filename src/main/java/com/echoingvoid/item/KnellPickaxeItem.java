package com.echoingvoid.item;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ToolMaterial;

/**
 * The Harmonic Pickaxe's rhythm-shatter, amplified: PLAYER, on the Knell upgrade - "the area
 * break of the knell pickaxe is amplified to a 4x4 area from 3x3." Same beat, same tolerance,
 * same streak requirement as {@link HarmonicPickaxeItem} - only the plane widens.
 */
public class KnellPickaxeItem extends HarmonicPickaxeItem {

    public KnellPickaxeItem(Item.Properties properties) {
        super(properties);
    }

    @Override
    protected int loOffset() {
        return -1;
    }

    @Override
    protected int hiOffset() {
        return 2; // -1..2 inclusive is four values on each axis: a 4x4 plane
    }
}

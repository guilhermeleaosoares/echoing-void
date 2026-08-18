package com.echoingvoid.item;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ToolMaterial;

/**
 * Fells a whole tree in one swing - but only struck at its base. A single trunk gives way when its
 * bottom log is cut; a 2x2 "large" trunk gives way when any of its four ground-level logs is, since
 * {@link TreeFellerAxeItem#isBaseLog} checks each of those the same way. Higher up the trunk, or on
 * a branch, it is an ordinary axe. See {@link TreeFellerAxeItem} for the shared felling logic and
 * {@link KnellAxeItem} for the tier that drops the base requirement entirely.
 */
public class HarmonicAxeItem extends TreeFellerAxeItem {

    public HarmonicAxeItem(ToolMaterial material, float attackDamageBaseline, float attackSpeedBaseline,
                            Item.Properties properties) {
        super(material, attackDamageBaseline, attackSpeedBaseline, properties);
    }

    @Override
    protected boolean requiresBase() {
        return true;
    }
}

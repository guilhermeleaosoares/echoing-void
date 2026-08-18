package com.echoingvoid.item;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ToolMaterial;

/**
 * The Harmonic Axe's felling ability, amplified: PLAYER, on the Knell upgrade - "the axe chopping
 * down any tree by chopping just one log of it down." No base check - cut anywhere in the trunk or
 * a branch and the whole connected cluster comes down. See {@link TreeFellerAxeItem}.
 */
public class KnellAxeItem extends TreeFellerAxeItem {

    public KnellAxeItem(ToolMaterial material, float attackDamageBaseline, float attackSpeedBaseline,
                         Item.Properties properties) {
        super(material, attackDamageBaseline, attackSpeedBaseline, properties);
    }

    @Override
    protected boolean requiresBase() {
        return false;
    }
}

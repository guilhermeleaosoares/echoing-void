package com.echoingvoid.item;

import net.minecraft.world.item.Item;

/**
 * The Harmonic Sword's sonic discharge, amplified: PLAYER, on the Knell upgrade - "the sword
 * disturbing with the noise for longer in a larger radius." Everything else - the cooldown, the
 * passive kinetic-bank feed on hit, the trigger - carries over unchanged from
 * {@link HarmonicSwordItem}; only the two numbers grow.
 */
public class KnellSwordItem extends HarmonicSwordItem {

    public KnellSwordItem(Properties properties) {
        super(properties);
    }

    @Override
    protected int sonicRadius() {
        return 9;
    }

    @Override
    protected int sonicDurationTicks() {
        return 200; // 10 seconds
    }
}

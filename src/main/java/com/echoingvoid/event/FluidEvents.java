package com.echoingvoid.event;

import com.echoingvoid.registry.ModFluids;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.entity.living.LivingEvent;

/**
 * Hushwater's one gameplay effect: standing in it mends you.
 *
 * <p>Why this is an event listener and not {@code Fluid#entityInside}: the fluid's own hook is
 * called once per intersecting block per tick, so a swimmer submerged in two blocks of hushwater
 * would heal at twice the rate of one wading in the shallows, and a tall mob at three times.
 * {@code LivingTickEvent} fires exactly once per living entity per tick, which makes the rate a
 * rate rather than a function of how deep you are.
 *
 * <p>It applies to every {@link LivingEntity}, not only players. A pool that visibly mends the
 * dimension's own creatures is the read the fluid is meant to have, and it costs one float
 * comparison per living tick to get - the fluid-height probe is only reached on the ticks the
 * modulo lets through.
 */
public final class FluidEvents {
    private FluidEvents() {}

    /** Ticks between mends. Two seconds - noticeably slower than a Regeneration I beat. */
    private static final int HEAL_INTERVAL = 40;

    /** Half a heart per mend, so a full bar takes about forty seconds of swimming. */
    private static final float HEAL_AMOUNT = 1.0F;

    public static void register() {
        LivingEvent.LivingTickEvent.BUS.addListener(FluidEvents::onLivingTick);
    }

    private static void onLivingTick(LivingEvent.LivingTickEvent event) {
        LivingEntity entity = event.getEntity();
        // The cheap tests first: client levels never heal, and 39 ticks in 40 do nothing.
        if (entity.level().isClientSide() || entity.tickCount % HEAL_INTERVAL != 0) {
            return;
        }
        if (entity.getHealth() >= entity.getMaxHealth() || entity.isDeadOrDying()) {
            return;
        }
        if (entity.getFluidTypeHeight(ModFluids.HUSHWATER_TYPE.get()) > 0.0D) {
            entity.heal(HEAL_AMOUNT);
        }
    }
}

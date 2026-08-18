package com.echoingvoid.entity;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.phys.AABB;

import java.util.EnumSet;
import java.util.List;

/**
 * PLAYER: "this protector mob is also neutral but attacks when the neutral trader mobs are
 * attacked."
 *
 * <p>Every tick, looks for the nearest {@link TraderMob} still {@linkplain TraderMob#isRetaliating
 * retaliating} within range and, if it has one, adopts whoever hurt it as a target. This is
 * deliberately simpler than vanilla's persistent-anger system (no anger timer that survives a
 * relog) because the trigger it is watching - {@code isRetaliating()} - is itself only a
 * few-second window; there is nothing longer-lived here worth persisting.
 */
public class DefendTraderGoal extends Goal {

    private static final double WATCH_RADIUS = 16.0;

    private final Mob protector;

    public DefendTraderGoal(Mob protector) {
        this.protector = protector;
        this.setFlags(EnumSet.of(Goal.Flag.TARGET));
    }

    @Override
    public boolean canUse() {
        if (protector.getTarget() != null) {
            return false; // already fighting something
        }
        return findAttacker() != null;
    }

    @Override
    public void start() {
        LivingEntity attacker = findAttacker();
        if (attacker != null) {
            protector.setTarget(attacker);
        }
    }

    private LivingEntity findAttacker() {
        AABB area = protector.getBoundingBox().inflate(WATCH_RADIUS);
        List<TraderMob> traders = protector.level().getEntitiesOfClass(TraderMob.class, area,
                TraderMob::isRetaliating);
        for (TraderMob trader : traders) {
            LivingEntity attacker = trader.getLastHurtByMob();
            if (attacker != null && attacker.isAlive()) {
                return attacker;
            }
        }
        return null;
    }
}

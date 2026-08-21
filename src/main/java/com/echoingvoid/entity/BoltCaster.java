package com.echoingvoid.entity;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;

/**
 * Something that can cast a {@link ResonanceBolt}.
 *
 * <p>Exists so {@link ResonanceBoltGoal} can drive a Tuner Shade and an angered Tuner Trader with
 * the same code. The goal previously named {@code TunerShadeEntity} directly and touched exactly
 * three things on it beyond the ordinary {@code Mob} surface - these three - so this interface is
 * the whole of what the goal actually needed.
 */
public interface BoltCaster {

    /** True while a bolt is still travelling; the goal will not fire a second one over it. */
    boolean hasBoltInFlight();

    /** Launch one, now, at {@code target}. */
    void fireBolt(ServerLevel level, LivingEntity target);

    /** Where the resonator sits, for the wind-up particles to gather at. */
    Vec3 resonatorPosition();
}

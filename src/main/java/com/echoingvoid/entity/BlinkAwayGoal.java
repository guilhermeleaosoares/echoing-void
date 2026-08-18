package com.echoingvoid.entity;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;

import java.util.EnumSet;

/**
 * The Tuner Shade's signature move: it will not let you reach it.
 *
 * <p>The trigger is pure proximity. Anything the shade is hunting that gets inside
 * {@value #TRIGGER_RANGE} blocks makes it jump, and it jumps in the direction that puts the most
 * ground between the two of them - see {@link TunerShadeEntity#tryBlinkAwayFrom}.
 *
 * <p>The move is not a dodge and does not need to be reacted to; it is a positioning puzzle. A
 * shade in a cavern will blink forever and a player chasing it will never land a swing. A shade
 * with a wall at its back has nowhere on its candidate list that passes, so the blink silently
 * fails and it eats the hit. Herding one is the whole fight, and it is why the shade is a threat
 * outdoors and a nuisance indoors.
 *
 * <p>A failed blink takes a short cooldown of its own rather than none at all. That matters: this
 * goal outranks the casting goal, so a cornered shade retrying every tick would stand there failing
 * to escape and never fight back. With the short lockout it turns, casts, and tests the walls again
 * every second or so - which is both better to fight and a clearer signal that the corner is
 * working.
 */
class BlinkAwayGoal extends Goal {
    /** Inside this, the shade wants out. Comfortably beyond a sword's reach. */
    private static final double TRIGGER_RANGE = 4.0;

    private final TunerShadeEntity shade;

    BlinkAwayGoal(TunerShadeEntity shade) {
        this.shade = shade;
        // Both flags, so this preempts the bolt goal rather than fighting it for the look control.
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (!this.shade.isBlinkReady()) {
            return false;
        }

        LivingEntity target = this.shade.getTarget();
        return target != null
                && target.isAlive()
                && this.shade.distanceToSqr(target) <= TRIGGER_RANGE * TRIGGER_RANGE;
    }

    @Override
    public boolean canContinueToUse() {
        // One tick. Either the blink landed and the shade is somewhere else, or it did not and the
        // bolt goal should have the shade back immediately rather than watching it stand still.
        return false;
    }

    @Override
    public void start() {
        LivingEntity target = this.shade.getTarget();
        if (target == null || !(this.shade.level() instanceof ServerLevel level)) {
            return;
        }

        if (this.shade.tryBlinkAwayFrom(level, target)) {
            // Land facing the thing it ran from. A shade that blinks and then has to turn around
            // loses the tempo the blink bought it.
            this.shade.getLookControl().setLookAt(target, 60.0F, 60.0F);
        }
    }
}

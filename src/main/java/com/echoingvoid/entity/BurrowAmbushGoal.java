package com.echoingvoid.entity;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;

import java.util.EnumSet;

/**
 * The Strata Burrower's signature move: it fights from under the floor.
 *
 * <p>The goal's job is narrow and deliberately so. The dive itself, the underground travel, the
 * plume and the eruption all live on {@link StrataBurrowerEntity}, because they have to keep running
 * whether or not the creature currently has a target - a burrower that loses its quarry mid-tunnel
 * still has to come back up. What the goal owns is the decision to start an unprovoked dive, and
 * the movement lock that stops every other goal from trying to path a creature that is currently
 * inside a wall.
 *
 * <p>The unprovoked dive is the offensive half of the behaviour: a burrower whose target is more
 * than a dozen blocks away would rather tunnel than trudge, because tunnelling is faster and comes
 * out behind them. The defensive half - diving because it just took a hit - is triggered straight
 * from {@code hurtServer} and does not go through here, so it cannot be delayed by goal arbitration
 * on the tick it matters.
 *
 * <p>Holding {@link Goal.Flag#MOVE}, {@link Goal.Flag#LOOK} and {@link Goal.Flag#JUMP} for the whole
 * dive is the point of running this as a goal at all. Without the lock, the melee goal would keep
 * issuing paths through solid rock for the entire time the burrower is under it.
 */
class BurrowAmbushGoal extends Goal {
    private final StrataBurrowerEntity burrower;

    BurrowAmbushGoal(StrataBurrowerEntity burrower) {
        this.burrower = burrower;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK, Goal.Flag.JUMP));
    }

    @Override
    public boolean canUse() {
        // Two entry points into the same lock: a dive already in progress (started by taking a hit)
        // and a dive this goal is about to start itself.
        return this.burrower.isDigging() || this.burrower.wantsToAmbush();
    }

    @Override
    public boolean canContinueToUse() {
        return this.burrower.isDigging();
    }

    @Override
    public void start() {
        // A no-op when the dive is already under way, which is the case whenever the creature got
        // here by being hurt rather than by choosing to hunt.
        this.burrower.beginDive();
        this.burrower.getNavigation().stop();
    }

    @Override
    public void stop() {
        this.burrower.getNavigation().stop();
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        // Movement while underground is driven from the entity; all that is needed here is to keep
        // the navigator quiet and to keep the head pointed at the quarry for the moment it comes up.
        this.burrower.getNavigation().stop();

        LivingEntity target = this.burrower.getTarget();
        if (target != null && !this.burrower.isUnderground()) {
            this.burrower.getLookControl().setLookAt(target, 30.0F, 30.0F);
        }
    }
}

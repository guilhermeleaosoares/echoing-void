package com.echoingvoid.entity;

import com.echoingvoid.registry.ModItems;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.EnumSet;

/**
 * The Chime Mote's one learnable behaviour: it comes when a Tuning Fork is out.
 *
 * <p>The fork is already the mod's key item - it opens the portal and it opens acoustic lock boxes -
 * so this costs the player nothing to discover and nothing to use. Hold it, and the motes in earshot
 * drift over and orbit; put it away, and they go back to wandering within a second or two.
 *
 * <p>The mote does not sit on the player. It holds an orbit at {@value #ORBIT_RADIUS} blocks and
 * {@value #ORBIT_HEIGHT} above their feet, turning slowly, which keeps it out of the way in a fight
 * and out of first person. Steering goes straight through the flying move control rather than the
 * path finder, exactly as the wraith's does: there is nothing to path around in open air, and a
 * per-tick path request for a creature this common is not worth what it costs.
 *
 * <p>Nothing here scans the world. The carrier is found with a single bounded
 * {@code getNearestPlayer} call, and only once every {@value #SEARCH_INTERVAL} ticks; between
 * searches the goal re-validates the player it already has, which is two field reads.
 */
class AttuneToForkGoal extends Goal {
    /** How far a mote can hear a fork. */
    private static final double HEARING_RANGE = 18.0;

    /** Ticks between attempts to find a carrier. Only paid while no carrier is held. */
    private static final int SEARCH_INTERVAL = 20;

    /** Radius of the orbit the mote settles into, in blocks. */
    private static final double ORBIT_RADIUS = 2.4;

    /** Height above the carrier's feet that the orbit sits at. */
    private static final double ORBIT_HEIGHT = 1.9;

    /** Radians per tick around the carrier. Slow: this is company, not a swarm. */
    private static final double ORBIT_RATE = 0.045;

    /** Beyond this the mote gives up on a carrier it had already attached to. */
    private static final double LEASH_RANGE = 24.0;

    private final ChimeMoteEntity mote;

    /** The carrier, or null when there is none. Re-validated every tick, re-found periodically. */
    private Player carrier;

    private int nextSearch;

    /** Phase offset around the orbit, so a cloud spreads around the player instead of stacking. */
    private double orbitPhase;

    AttuneToForkGoal(ChimeMoteEntity mote) {
        this.mote = mote;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (this.mote.isStartled()) {
            return false;
        }
        if (--this.nextSearch > 0) {
            return false;
        }

        this.nextSearch = this.adjustedTickDelay(SEARCH_INTERVAL);
        Player found = this.mote.level().getNearestPlayer(this.mote, HEARING_RANGE);
        if (!holdsFork(found)) {
            return false;
        }

        this.carrier = found;
        return true;
    }

    @Override
    public boolean canContinueToUse() {
        return !this.mote.isStartled()
                && holdsFork(this.carrier)
                && this.mote.distanceToSqr(this.carrier) <= LEASH_RANGE * LEASH_RANGE;
    }

    @Override
    public void start() {
        // Spread the cloud by entity id rather than randomly, so a mote that briefly loses its
        // carrier returns to the same place in the ring instead of jumping across it.
        this.orbitPhase = (this.mote.getId() * 0.61803) % 1.0 * Math.PI * 2.0;

        if (this.mote.level() instanceof ServerLevel level) {
            level.playSound(null, this.mote.getX(), this.mote.getY(), this.mote.getZ(),
                    SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.NEUTRAL, 0.6F, 1.6F);
        }
    }

    @Override
    public void stop() {
        this.carrier = null;
        this.mote.getNavigation().stop();
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public void tick() {
        Player target = this.carrier;
        if (target == null) {
            return;
        }

        this.orbitPhase += ORBIT_RATE;
        double wantX = target.getX() + Math.cos(this.orbitPhase) * ORBIT_RADIUS;
        double wantZ = target.getZ() + Math.sin(this.orbitPhase) * ORBIT_RADIUS;
        double wantY = target.getY() + ORBIT_HEIGHT;

        // Close the gap quickly when far out and gently once in the ring, so a mote crossing a
        // cavern to reach a fork does not then overshoot and oscillate around the player.
        double speed = this.mote.distanceToSqr(wantX, wantY, wantZ) > 9.0 ? 1.5 : 0.8;
        this.mote.getMoveControl().setWantedPosition(wantX, wantY, wantZ, speed);
        this.mote.getLookControl().setLookAt(target, 30.0F, 30.0F);

        // A thread of light between the mote and the fork, drawn thinly enough that a dozen motes
        // is a constellation rather than a fog bank.
        if (this.mote.tickCount % 10 == 0 && this.mote.level() instanceof ServerLevel level) {
            double t = 0.35 + (Mth.sin((float) this.orbitPhase) + 1.0) * 0.15;
            level.sendParticles(ParticleTypes.END_ROD,
                    Mth.lerp(t, this.mote.getX(), target.getX()),
                    Mth.lerp(t, this.mote.getY(0.5), target.getEyeY() - 0.3),
                    Mth.lerp(t, this.mote.getZ(), target.getZ()),
                    1, 0.02, 0.02, 0.02, 0.0);
        }
    }

    /** Either hand counts: a player mid-fight with a sword out can still keep their escort. */
    private static boolean holdsFork(Player player) {
        if (player == null || !player.isAlive() || player.isSpectator()) {
            return false;
        }

        return isFork(player.getMainHandItem()) || isFork(player.getOffhandItem());
    }

    private static boolean isFork(ItemStack stack) {
        return !stack.isEmpty() && stack.is(ModItems.TUNING_FORK.get());
    }
}

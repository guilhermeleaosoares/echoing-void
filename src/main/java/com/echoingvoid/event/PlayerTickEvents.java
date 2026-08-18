package com.echoingvoid.event;

import com.echoingvoid.item.AeroStrideGreavesItem;
import com.echoingvoid.item.HarmonicPickaxeItem;
import com.echoingvoid.item.ResonanceArmorItem;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Input;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Per-tick behaviour for the movement gear: the Aero-Stride wall run and the Resonance
 * double-crouch release.
 *
 * <p>The listener is written so that a player wearing none of it pays for two equipment-slot
 * reads and returns - no map touch, no block lookup, no allocation. Everything past that gate
 * works through one shared mutable cursor and one small state object per player, created when
 * the player first needs it and dropped when they log out.
 *
 * <p>Input is read from {@link ServerPlayer#getLastClientInput()} rather than from key state,
 * which keeps the whole thing server-authoritative.
 */
public final class PlayerTickEvents {
    private PlayerTickEvents() {}

    /** Ticks allowed between two crouch presses for them to count as a double tap. */
    private static final int DOUBLE_TAP_WINDOW = 8;

    /** Per-player movement state. Looked up by UUID, never iterated. */
    private static final Map<UUID, GearState> STATE = new HashMap<>();

    /** Shared wall probe. Player ticks run one at a time on the server thread. */
    private static final BlockPos.MutableBlockPos CURSOR = new BlockPos.MutableBlockPos();

    public static void register() {
        TickEvent.PlayerTickEvent.Post.BUS.addListener(PlayerTickEvents::onPlayerTick);
        PlayerEvent.PlayerLoggedOutEvent.BUS.addListener(PlayerTickEvents::onLoggedOut);
    }

    private static void onPlayerTick(TickEvent.PlayerTickEvent.Post event) {
        if (!(event.player() instanceof ServerPlayer player)) {
            return;
        }

        boolean greaves = AeroStrideGreavesItem.isWorn(player);
        boolean resonance = !ResonanceArmorItem.resonator(player).isEmpty();
        if (!greaves && !resonance) {
            return;
        }

        GearState state = STATE.get(player.getUUID());
        if (state == null) {
            state = new GearState();
            STATE.put(player.getUUID(), state);
        }

        Input input = player.getLastClientInput();

        if (greaves) {
            tickWallRun(player, input, state);
        }
        if (resonance) {
            tickCrouchRelease(player, input, state);
        }
    }

    /**
     * Airborne, holding forward and next to a wall: arrest the fall and let the wearer carry
     * their speed along the face. The clock only resets on the ground, so a wall run cannot be
     * chained indefinitely by hopping between faces.
     */
    private static void tickWallRun(ServerPlayer player, Input input, GearState state) {
        if (player.onGround()) {
            state.wallTicks = 0;
            state.wallSpent = false;
            return;
        }
        if (state.wallSpent || !input.forward() || player.getAbilities().flying) {
            return;
        }

        if (AeroStrideGreavesItem.clingToWall(player.level(), player, CURSOR)) {
            state.wallTicks++;
            if (state.wallTicks >= AeroStrideGreavesItem.WALL_RUN_TICKS) {
                state.wallSpent = true;
            }
        } else {
            state.wallTicks = 0;
        }
    }

    /** Two crouch presses inside the window dump the Resonance set's banked damage. */
    private static void tickCrouchRelease(ServerPlayer player, Input input, GearState state) {
        boolean crouching = input.shift();
        if (crouching && !state.wasCrouching) {
            int now = player.tickCount;
            if (now - state.lastCrouchPressTick <= DOUBLE_TAP_WINDOW) {
                // Consume the pair so a third press does not immediately re-fire.
                state.lastCrouchPressTick = now - DOUBLE_TAP_WINDOW - 1;
                ResonanceArmorItem.releaseShockwave(player.level(), player);
            } else {
                state.lastCrouchPressTick = now;
            }
        }
        state.wasCrouching = crouching;
    }

    /** Keeps the per-player maps sized to the online roster rather than to history. */
    private static void onLoggedOut(PlayerEvent.PlayerLoggedOutEvent event) {
        UUID id = event.getEntity().getUUID();
        STATE.remove(id);
        HarmonicPickaxeItem.forget(id);
    }

    /** Mutable holder so a wall-running tick writes fields instead of boxing integers. */
    private static final class GearState {
        int wallTicks;
        boolean wallSpent;
        int lastCrouchPressTick = -1000;
        boolean wasCrouching;
    }
}

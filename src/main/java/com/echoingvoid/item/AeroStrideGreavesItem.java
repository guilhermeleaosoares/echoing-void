package com.echoingvoid.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * The Aero-Stride Greaves - void-glass soles that refuse to acknowledge terminal velocity.
 *
 * <p>The wearer never takes fall damage. Instead, the moment of impact opens a brief
 * zero-gravity drift zone: for a couple of seconds afterwards they sink like a feather,
 * which turns a long drop into a controlled descent rather than a landing.
 *
 * <p>Airborne and pressed against a wall with forward held, the soles bite. Downward
 * velocity is arrested and horizontal speed is preserved, so the wearer runs along the
 * face for a short window before gravity reasserts itself. The window is deliberately
 * short - the greaves are a traversal tool, not flight.
 *
 * <p>All wall probing goes through a caller-supplied mutable cursor and a fixed direction
 * array; nothing here allocates on a tick where the wearer is not actually clinging.
 */
public class AeroStrideGreavesItem extends Item {

    /**
     * How many consecutive ticks the wearer may cling before the soles let go.
     *
     * <p>Deliberately long. The first version cut the run off after 26 ticks, which in play read
     * as the boots repeatedly failing rather than as a designed limit - you would get a second of
     * wall, drop, catch again, drop again. The run is now self-limiting instead: it ends the
     * moment you stop holding forward or turn away from the wall, which is a limit the player
     * controls and understands.
     */
    public static final int WALL_RUN_TICKS = 400;

    /**
     * Horizontal speed along the wall, in blocks per tick. Matched to a ground sprint so running
     * along a wall feels like running, not like sliding down one.
     */
    private static final double WALL_RUN_SPEED = 0.28;

    /**
     * How directly the wearer must be facing the wall, as the dot product of their look direction
     * and the direction to the wall. About 0.15 is a wide cone - "pointing slightly towards the
     * wall" is enough, and looking along the face still counts.
     */
    private static final double WALL_LOOK_THRESHOLD = 0.15;

    /** Length of the post-landing drift zone, in ticks. */
    private static final int DRIFT_TICKS = 50;

    /** Fall further than this and the landing is worth a drift zone. */
    private static final double DRIFT_TRIGGER_DISTANCE = 3.0;

    /** How much of the downward velocity survives a clinging tick. */
    private static final double CLING_FALL_DAMPING = 0.12;

    /** Floor on vertical speed while clinging, so the wearer creeps rather than hovers. */
    private static final double CLING_MIN_RISE = -0.06;

    /** Slight forward bias so a wall run carries the wearer along the face. */
    private static final double CLING_GLIDE = 1.06;

    /** Fixed order avoids the iterator {@code Direction.Plane.HORIZONTAL} would allocate. */
    private static final Direction[] HORIZONTALS = {
            Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST
    };

    public AeroStrideGreavesItem(Item.Properties properties) {
        super(properties);
    }

    /** True when the greaves are on the wearer's feet. One slot read, no allocation. */
    public static boolean isWorn(LivingEntity wearer) {
        ItemStack boots = wearer.getItemBySlot(EquipmentSlot.FEET);
        return !boots.isEmpty() && boots.getItem() instanceof AeroStrideGreavesItem;
    }

    /** True if the fall was long enough to be worth opening a drift zone. */
    public static boolean shouldDrift(double fallDistance) {
        return fallDistance > DRIFT_TRIGGER_DISTANCE;
    }

    /**
     * Opens the zero-gravity drift zone. Called from the fall handler once the greaves have
     * eaten the damage, so this only runs on an actual landing.
     */
    public static void openDriftZone(ServerLevel level, LivingEntity wearer) {
        wearer.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, DRIFT_TICKS, 0, true, false), wearer);
        level.sendParticles(ParticleTypes.CLOUD, wearer.getX(), wearer.getY() + 0.1, wearer.getZ(),
                8, 0.35, 0.05, 0.35, 0.02);
        level.playSound(null, wearer.getX(), wearer.getY(), wearer.getZ(),
                SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 0.5F, 1.6F);
    }

    /**
     * Probes the four horizontal neighbours at chest height and, if one presents a sturdy
     * face, cancels the fall and lets the wearer carry their horizontal speed along it.
     *
     * <p>The caller owns {@code cursor} and is expected to hand back the same instance every
     * tick, so a clinging tick costs four block lookups and one velocity write.
     *
     * @return true if a wall was found and the wearer is now clinging to it
     */
    public static boolean clingToWall(Level level, Player wearer, BlockPos.MutableBlockPos cursor) {
        int x = Mth.floor(wearer.getX());
        int y = Mth.floor(wearer.getY() + 1.0);
        int z = Mth.floor(wearer.getZ());

        Vec3 look = wearer.getLookAngle();
        double lookX = look.x;
        double lookZ = look.z;
        double lookLen = Math.sqrt(lookX * lookX + lookZ * lookZ);
        if (lookLen < 1.0E-4) {
            return false;
        }
        lookX /= lookLen;
        lookZ /= lookLen;

        for (int i = 0; i < HORIZONTALS.length; i++) {
            Direction face = HORIZONTALS[i];
            cursor.set(x + face.getStepX(), y, z + face.getStepZ());
            BlockState state = level.getBlockState(cursor);
            if (state.isAir() || !state.isFaceSturdy(level, cursor, face.getOpposite())) {
                continue;
            }

            // Only cling to a wall the wearer is actually facing into. Without this the boots
            // grab whichever wall happens to be nearest and drag the player sideways.
            double intoWall = lookX * face.getStepX() + lookZ * face.getStepZ();
            if (intoWall < WALL_LOOK_THRESHOLD) {
                continue;
            }

            // Run ALONG the face: strip the into-the-wall component out of the look direction and
            // drive at sprint speed down what is left. Scaling the existing velocity instead - as
            // the first version did - meant arriving slowly left you crawling.
            double alongX = lookX - face.getStepX() * intoWall;
            double alongZ = lookZ - face.getStepZ() * intoWall;
            double alongLen = Math.sqrt(alongX * alongX + alongZ * alongZ);

            double vx;
            double vz;
            if (alongLen < 0.15) {
                // Looking straight at the wall: hold position on it rather than sliding off.
                vx = face.getStepX() * 0.02;
                vz = face.getStepZ() * 0.02;
            } else {
                vx = (alongX / alongLen) * WALL_RUN_SPEED + face.getStepX() * 0.04;
                vz = (alongZ / alongLen) * WALL_RUN_SPEED + face.getStepZ() * 0.04;
            }

            Vec3 motion = wearer.getDeltaMovement();
            double rise = motion.y < 0.0 ? Math.max(motion.y * CLING_FALL_DAMPING, CLING_MIN_RISE) : motion.y;
            wearer.setDeltaMovement(vx, rise, vz);
            wearer.resetFallDistance();
            // The server moved the player, so the client needs telling.
            wearer.hurtMarked = true;
            return true;
        }
        return false;
    }
}

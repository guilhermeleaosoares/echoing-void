package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import org.jspecify.annotations.Nullable;

/**
 * Void Glass - a pane of solidified nothing that the Hollow Horizon uses as flooring.
 *
 * <p>Two gameplay promises, both honoured here:
 * <ul>
 *   <li><b>No fall damage.</b> {@link #fallOn} deliberately does not call {@code super}, so nothing
 *       that lands on void glass is ever hurt by the landing - no height cap, no partial mitigation.
 *   <li><b>Zero-gravity walk surface.</b> Horizontal friction is damped almost to ice levels so
 *       momentum carries instead of bleeding off, and anything standing on the block gets a small
 *       upward nudge each tick it is grounded. The result is a slow bob rather than a solid stance,
 *       which is what "walking in free fall" should feel like.
 * </ul>
 *
 * <p>The block is translucent; {@code noOcclusion()} is already set on the properties in
 * {@code ModBlocks}, so nothing is needed here for rendering.
 */
public class VoidGlassBlock extends Block {
    /**
     * Vanilla friction is 0.6 and ice is 0.98; higher means less deceleration per tick. 0.96 keeps
     * a little grip so the player is not literally uncontrollable, but momentum plainly carries.
     */
    private static final float DRIFT_FRICTION = 0.96F;

    /** Upward impulse applied per grounded tick. Small enough to read as buoyancy, not a jump pad. */
    private static final double BUOYANCY = 0.035;

    /** Ceiling on the accumulated lift, so a long stand does not launch anyone. */
    private static final double MAX_LIFT = 0.12;

    public VoidGlassBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    /** Swallows the landing entirely - no {@code super} call means no fall damage is ever dealt. */
    @Override
    public void fallOn(Level level, BlockState state, BlockPos pos, Entity entity, double fallDistance) {
    }

    /**
     * Forge's position-sensitive friction hook. The vanilla {@code Block#getFriction()} is deprecated
     * in favour of this one.
     */
    @Override
    public float getFriction(BlockState state, LevelReader level, BlockPos pos, @Nullable Entity entity) {
        return DRIFT_FRICTION;
    }

    @Override
    public void stepOn(Level level, BlockPos pos, BlockState onState, Entity entity) {
        // Crouching is the deliberate opt-out: sneak to stand still on the glass.
        if (!entity.isSteppingCarefully()) {
            Vec3 motion = entity.getDeltaMovement();
            if (motion.y <= MAX_LIFT) {
                entity.setDeltaMovement(motion.x, Math.min(motion.y + BUOYANCY, MAX_LIFT), motion.z);
            }
        }

        super.stepOn(level, pos, onState, entity);
    }

    /** Void glass is see-through, so it must not shade the block behind it. */
    @Override
    protected float getShadeBrightness(BlockState state, BlockGetter level, BlockPos pos) {
        return 1.0F;
    }
}

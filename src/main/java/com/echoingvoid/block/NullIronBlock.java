package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Null Iron - the blast sink of the mod. It eats detonations instead of reflecting them.
 *
 * <p>The absorption works through the explosion ray-caster: {@link #getExplosionResistance} reports
 * a resistance no blast can chew through, so the block itself never breaks and, because the ray
 * accumulates resistance as it travels, everything shadowed behind a null iron pane survives too.
 * That is the whole mechanic - there is no ticking, no scheduled work, and no listener.
 *
 * <p>The "within 3 blocks" half of the brief cannot be done from a block class: a block has no say
 * over an explosion centred somewhere else. {@link #shieldsFromBlast} is the cheap query an
 * explosion event handler uses to answer that question, and {@link #dampenedRadius} is the
 * reduction to apply when the answer is yes. Both are pure functions with no allocation.
 */
public class NullIronBlock extends Block {
    /** Chebyshev-ish reach of the blast sink, in blocks, as specified in the block matrix. */
    public static final int ABSORPTION_RADIUS = 3;

    /** Well past any vanilla blast power; matches the magnitude vanilla uses for bedrock. */
    private static final float BLAST_ABSORPTION = 3_600_000.0F;

    /** How much of an explosion's radius survives contact with null iron. */
    private static final float RESIDUAL_RADIUS = 0.3F;

    public NullIronBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    /**
     * Forge's position-sensitive resistance hook. Returning a huge value both makes the block
     * blast-proof and drains the explosion ray that passes through it.
     */
    @Override
    public float getExplosionResistance(BlockState state, BlockGetter level, BlockPos pos, Explosion explosion) {
        return BLAST_ABSORPTION;
    }

    /**
     * True when a null iron block sits within {@link #ABSORPTION_RADIUS} of {@code origin}.
     *
     * <p>Only the six axial rays are probed - eighteen block lookups rather than the ~123 a full
     * sphere would cost - which is accurate enough for a blast sink and cheap enough to call once
     * per explosion. The caller supplies the scratch position so nothing is allocated here.
     */
    public static boolean shieldsFromBlast(BlockGetter level, BlockPos origin, BlockPos.MutableBlockPos scratch) {
        for (Direction direction : Direction.values()) {
            for (int step = 1; step <= ABSORPTION_RADIUS; step++) {
                scratch.setWithOffset(origin, direction.getStepX() * step, direction.getStepY() * step, direction.getStepZ() * step);
                if (level.getBlockState(scratch).getBlock() instanceof NullIronBlock) {
                    return true;
                }
            }
        }

        return false;
    }

    /** The radius an explosion is left with after null iron has drunk its share. */
    public static float dampenedRadius(float radius) {
        return radius * RESIDUAL_RADIUS;
    }
}

package com.echoingvoid.block;

import net.minecraft.core.BlockPos;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Null Iron Ore - the vein the blast-sink metal comes out of.
 *
 * <p>Raw null iron drops come from the block's loot table, not from code, so nothing here touches
 * drops.
 *
 * <p><b>On "diminishes adjacent block light by 1".</b> The 26.2 lighting engine has no per-neighbour
 * emission hook: a block can state how much light it dampens as light passes <em>through</em> it
 * ({@link #getLightDampening}), but it cannot reach sideways and subtract a level from a torch next
 * door. Truly decrementing neighbouring emission would mean mixing into {@code LightEngine} /
 * {@code LevelReader#getLightDampening}, which this mod does not do. The honest approximation is
 * implemented instead: the ore is fully opaque to light, so it casts the deepest shadow the engine
 * allows and a lit space next to a null iron seam reads as one notch darker than it otherwise would.
 */
public class NullIronOreBlock extends Block {
    private static final int MIN_XP = 3;
    private static final int MAX_XP = 7;

    public NullIronOreBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    /** Full opacity - the maximum the light engine accepts, same value tinted glass uses. */
    @Override
    protected int getLightDampening(BlockState state) {
        return 15;
    }

    @Override
    protected boolean propagatesSkylightDown(BlockState state) {
        return false;
    }

    /**
     * Forge routes block experience through this hook rather than the vanilla
     * {@code spawnAfterBreak} path, so ore XP has to be declared here.
     */
    @Override
    public int getExpDrop(BlockState state, LevelReader level, RandomSource randomSource, BlockPos pos, int fortuneLevel, int silkTouchLevel) {
        return silkTouchLevel == 0 ? Mth.nextInt(randomSource, MIN_XP, MAX_XP) : 0;
    }
}

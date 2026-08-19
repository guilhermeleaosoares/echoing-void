package com.echoingvoid.worldgen;

import com.echoingvoid.registry.ModBlocks;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureProcessor;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * PLAYER: "structures are still floating. To fix this we can use the Ohana way which is extend the
 * bottom most blocks of floating structures until they meet the ground."
 *
 * <p>And then, after seeing the first version in game: "the structure generation to meet the ground
 * is wrong. it should extend an entire column of raw phonolite below all bottom layer blocks, not
 * just an outer shell. because now it is generating hollow space below the structure".
 *
 * <p>So: for EVERY column the piece occupies, this finds the piece's own lowest block and grows a
 * solid pillar downward from it until it lands on something solid. Two things the first version got
 * wrong and this one does not:
 *
 * <ul>
 *   <li>It legged only the perimeter columns, behind an {@code edges_only} flag. That left the whole
 *       interior of the footprint hanging over a hole - a rim of legs around an empty shell. The
 *       flag is gone rather than defaulted to false, because there is no case for it.
 *   <li>It filled each leg with a copy of whatever block happened to be lowest in that column. Under
 *       {@code bridge_stair} the lowest block in the kerb columns is a slab, so the legs came out as
 *       stacked half-blocks. The fill is now a constant {@code echoing_void:raw_phonolite}, which is
 *       both the right material for exposed bedrock-side masonry and immune to that class of bug.
 * </ul>
 *
 * <p>It runs in {@link #finalizeProcessing}, not {@link #processBlock}, because the fix ADDS blocks
 * that were never in the template. {@code processBlock} may only transform or delete the block it
 * is handed; {@code finalizeProcessing} returns the whole list and may append to it, which is the
 * only hook in the {@code StructureProcessor} interface that can create geometry.
 *
 * <p>{@code maxDepth} survives as the one deliberate limit: a piece placed over genuine void must
 * not drill a pillar to the bottom of the world, so past that depth the column is simply left short.
 */
public class GroundSupportProcessor implements StructureProcessor {

    public static final MapCodec<GroundSupportProcessor> MAP_CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    Codec.INT.optionalFieldOf("max_depth", 24).forGetter(p -> p.maxDepth)
            ).apply(i, GroundSupportProcessor::new));

    /**
     * Resolved on first use rather than in a field initialiser: this class is loaded when the
     * processor registry is built, which is before {@code ModBlocks} has handed out its blocks.
     */
    private static BlockState supportState;

    private final int maxDepth;

    public GroundSupportProcessor(int maxDepth) {
        this.maxDepth = maxDepth;
    }

    private static BlockState support() {
        BlockState state = supportState;
        if (state == null) {
            state = ModBlocks.RAW_PHONOLITE.get().defaultBlockState();
            supportState = state;
        }
        return state;
    }

    @Override
    public List<StructureTemplate.StructureBlockInfo> finalizeProcessing(
            ServerLevelAccessor level,
            BlockPos position,
            BlockPos referencePos,
            List<StructureTemplate.StructureBlockInfo> originalBlockInfoList,
            List<StructureTemplate.StructureBlockInfo> processedBlockInfoList,
            StructurePlaceSettings settings) {

        // Lowest real block the piece places in each column, keyed by (x, z). Air and structure void
        // are what the piece carves its interior out with, not part of its underside.
        Map<Long, BlockPos> lowest = new HashMap<>();

        for (StructureTemplate.StructureBlockInfo info : processedBlockInfoList) {
            if (info.state().isAir() || info.state().is(Blocks.STRUCTURE_VOID)) {
                continue;
            }
            BlockPos p = info.pos();
            long key = columnKey(p.getX(), p.getZ());
            BlockPos current = lowest.get(key);
            if (current == null || p.getY() < current.getY()) {
                lowest.put(key, p);
            }
        }
        if (lowest.isEmpty()) {
            return processedBlockInfoList;
        }

        BlockState fill = support();
        List<StructureTemplate.StructureBlockInfo> out = new ArrayList<>(processedBlockInfoList);
        BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();

        for (BlockPos foot : lowest.values()) {
            for (int drop = 1; drop <= maxDepth; drop++) {
                cursor.set(foot.getX(), foot.getY() - drop, foot.getZ());
                if (cursor.getY() <= level.getMinY()) {
                    break;
                }
                // Already standing on something - nothing left to bridge in this column.
                if (level.getBlockState(cursor).isSolid()) {
                    break;
                }
                out.add(new StructureTemplate.StructureBlockInfo(cursor.immutable(), fill, null));
            }
        }
        return out;
    }

    private static long columnKey(int x, int z) {
        return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
    }

    @Override
    public MapCodec<? extends StructureProcessor> codec() {
        return MAP_CODEC;
    }
}

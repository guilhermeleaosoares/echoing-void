package com.echoingvoid.worldgen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ServerLevelAccessor;
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
 * <p>Exactly that. For every column the piece occupies, this finds the piece's own lowest block and
 * grows a pillar of that same block downward until it lands on something solid - so a building that
 * would otherwise hang in the air over a gap between islands gets legs down to the rock.
 *
 * <p>It runs in {@link #finalizeProcessing}, not {@link #processBlock}, because the fix ADDS blocks
 * that were never in the template. {@code processBlock} may only transform or delete the block it
 * is handed; {@code finalizeProcessing} returns the whole list and may append to it, which is the
 * only hook in the {@code StructureProcessor} interface that can create geometry.
 *
 * <p>Two deliberate limits. {@code maxDepth} caps how far a leg may reach, so a piece placed over
 * genuine void does not drill a pillar to the bottom of the world - past that depth the piece is
 * simply left as it was. And only the OUTER columns of the footprint are extended: filling every
 * interior column would bury the underside of a bridge deck in a solid block of stone, where what
 * is actually wanted is legs at the edges.
 */
public class GroundSupportProcessor implements StructureProcessor {

    public static final MapCodec<GroundSupportProcessor> MAP_CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                    Codec.INT.optionalFieldOf("max_depth", 24).forGetter(p -> p.maxDepth),
                    Codec.BOOL.optionalFieldOf("edges_only", true).forGetter(p -> p.edgesOnly)
            ).apply(i, GroundSupportProcessor::new));

    private final int maxDepth;
    private final boolean edgesOnly;

    public GroundSupportProcessor(int maxDepth, boolean edgesOnly) {
        this.maxDepth = maxDepth;
        this.edgesOnly = edgesOnly;
    }

    @Override
    public List<StructureTemplate.StructureBlockInfo> finalizeProcessing(
            ServerLevelAccessor level,
            BlockPos position,
            BlockPos referencePos,
            List<StructureTemplate.StructureBlockInfo> originalBlockInfoList,
            List<StructureTemplate.StructureBlockInfo> processedBlockInfoList,
            StructurePlaceSettings settings) {

        // Lowest solid block the piece places in each column, keyed by (x, z).
        Map<Long, StructureTemplate.StructureBlockInfo> lowest = new HashMap<>();
        int minX = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE;
        int minZ = Integer.MAX_VALUE, maxZ = Integer.MIN_VALUE;

        for (StructureTemplate.StructureBlockInfo info : processedBlockInfoList) {
            if (info.state().isAir()) {
                continue;
            }
            BlockPos p = info.pos();
            long key = columnKey(p.getX(), p.getZ());
            StructureTemplate.StructureBlockInfo current = lowest.get(key);
            if (current == null || p.getY() < current.pos().getY()) {
                lowest.put(key, info);
            }
            minX = Math.min(minX, p.getX());
            maxX = Math.max(maxX, p.getX());
            minZ = Math.min(minZ, p.getZ());
            maxZ = Math.max(maxZ, p.getZ());
        }
        if (lowest.isEmpty()) {
            return processedBlockInfoList;
        }

        List<StructureTemplate.StructureBlockInfo> out = new ArrayList<>(processedBlockInfoList);
        BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();

        for (StructureTemplate.StructureBlockInfo foot : lowest.values()) {
            BlockPos p = foot.pos();
            if (edgesOnly && p.getX() != minX && p.getX() != maxX
                    && p.getZ() != minZ && p.getZ() != maxZ) {
                continue;
            }
            // The block the piece rests on. If it is already solid there is
            // nothing to bridge and the column is left alone.
            BlockState support = foot.state();
            for (int drop = 1; drop <= maxDepth; drop++) {
                cursor.set(p.getX(), p.getY() - drop, p.getZ());
                if (level.getBlockState(cursor).isSolid()) {
                    break;
                }
                if (cursor.getY() <= level.getMinY()) {
                    break;
                }
                out.add(new StructureTemplate.StructureBlockInfo(cursor.immutable(), support, null));
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

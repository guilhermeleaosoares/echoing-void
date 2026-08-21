package com.echoingvoid.worldgen;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.HollowHorizonPortalBlock;
import com.echoingvoid.registry.ModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.LevelChunkSection;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.portal.TeleportTransition;
import net.minecraft.world.phys.Vec3;

/**
 * Everything the Hollow Horizon portal needs on the far side of a transition.
 *
 * <p>Vanilla's {@code PortalForcer} cannot be borrowed for this: it only ever places obsidian and
 * {@code minecraft:nether_portal}, and {@code PortalShape} is likewise hard-wired to those blocks.
 * So the search for an existing portal, the platform carving and the frame building are all done
 * here, against phonolite bricks and our own portal block.
 *
 * <p>The Hollow Horizon is a void dimension. If we dropped a traveller at the scaled coordinates
 * and walked away they would fall forever, so an arrival always ends with solid phonolite under
 * foot and a lit frame to walk back through.
 */
public final class HollowHorizonTeleporter {
    private HollowHorizonTeleporter() {}

    /** Declared by {@code data/echoing_void/dimension/the_hollow_horizon.json}. */
    public static final ResourceKey<Level> HOLLOW_HORIZON =
            ResourceKey.create(Registries.DIMENSION, EchoingVoid.id("the_hollow_horizon"));

    /** Interior of the frame we raise on arrival: the smallest legal shape, 2 wide by 3 tall. */
    private static final int EXIT_WIDTH = 2;
    private static final int EXIT_HEIGHT = 3;

    /**
     * How far around the scaled destination we look before deciding to build a new portal.
     *
     * <p>PLAYER: "the portals dont connect, like the nether portals... every time a portal is
     * used, a new one is created in the other dimension... another portal generates in the exact
     * xz coordinates but above in y, and thats where the player spawns."
     *
     * <p>Two things caused that, and the vertical one was the killer. The search used to run only
     * {@code +-8} blocks around the traveller's ARRIVAL altitude, but the two portals of a pair
     * almost never sit at the same height: the far-side portal is built on whatever ground
     * {@link #findGround} finds, which in a floating-island dimension is routinely a hundred
     * blocks off the altitude the traveller left from. So the return trip looked in a narrow
     * slab that did not contain the original portal, found nothing, and built another one - and
     * because the coordinate scale round-trips X and Z exactly, "another one" landed at the same
     * XZ and a different Y. Hence the stack of portals.
     *
     * <p>The height window is gone entirely now: every candidate column is searched over its
     * whole height, which is what vanilla effectively does via the portal POI index.
     *
     * <p>The radius has to cover the rounding drift the coordinate scale introduces. Going out at
     * scale {@code s} floors to {@code floor(x / s)}; coming back multiplies by {@code s}, so the
     * return can land up to {@code s - 1} blocks short of where it started - 23 blocks at the
     * Hollow Horizon's scale of 24. 32 clears that with room to spare, on both axes.
     */
    private static final int SEARCH_RADIUS = 32;

    /** How far down we will look for ground to stand the exit portal on. */
    private static final int GROUND_PROBE = 24;

    /** Same flags vanilla uses for portal cells: tell clients, but do not re-run shape updates. */
    private static final int PORTAL_FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE;

    /**
     * One scratch position for every scan and every placement below. Portal transitions are driven
     * from {@code Entity#handlePortal} on the server thread, so a single shared cursor is safe;
     * anything that has to outlive a call takes an {@code immutable()} copy first.
     */
    private static final BlockPos.MutableBlockPos CURSOR = new BlockPos.MutableBlockPos();

    /**
     * Works out where the traveller comes out and hands back the transition that puts them there.
     * Returns null when the destination level is missing, which leaves the entity where it is.
     */
    public static TeleportTransition destinationFor(final ServerLevel currentLevel, final Entity entity, final BlockPos portalEntryPos) {
        MinecraftServer server = currentLevel.getServer();
        ResourceKey<Level> targetKey = currentLevel.dimension() == HOLLOW_HORIZON ? Level.OVERWORLD : HOLLOW_HORIZON;
        ServerLevel target = server.getLevel(targetKey);
        if (target == null) {
            EchoingVoid.LOGGER.warn("No level registered for {}; the Hollow Horizon portal cannot resolve a destination.", targetKey.identifier());
            return null;
        }

        // Carry the plane of the portal we walked into over to the one we build.
        Direction.Axis entryAxis = currentLevel.getBlockState(portalEntryPos)
                .getOptionalValue(HollowHorizonPortalBlock.AXIS)
                .orElse(Direction.Axis.X);

        double scale = DimensionType.getTeleportationScale(currentLevel.dimensionType(), target.dimensionType());
        BlockPos approximate = target.getWorldBorder()
                .clampToBounds(entity.getX() * scale, entity.getY(), entity.getZ() * scale);

        int x = approximate.getX();
        int z = approximate.getZ();
        int y = Mth.clamp(approximate.getY(), target.getMinY() + 1, target.getMaxY() - EXIT_HEIGHT - 1);

        BlockPos exit = findExistingPortal(target, x, y, z);
        if (exit == null) {
            exit = buildExitPortal(target, x, y, z, entryAxis);
        }

        if (exit == null) {
            EchoingVoid.LOGGER.warn("Could not place a Hollow Horizon exit portal near {} {} {}.", x, y, z);
            return null;
        }

        Vec3 landing = Vec3.atBottomCenterOf(exit);
        return new TeleportTransition(
                target,
                landing,
                Vec3.ZERO,
                entity.getYRot(),
                entity.getXRot(),
                TeleportTransition.PLAY_PORTAL_SOUND.then(TeleportTransition.PLACE_PORTAL_TICKET)
        );
    }

    // ------------------------------------------------------------------ search

    /**
     * Returns the portal cell nearest the scaled destination, or null if there is none in range.
     *
     * <p>Scans every chunk within {@link #SEARCH_RADIUS} over its FULL height. Reading a million
     * individual block states to do that would be far too slow for something that runs inside a
     * portal transition, so the work is skipped a whole 16x16x16 section at a time: a section
     * that {@code hasOnlyAir}, or whose palette {@code maybeHas} says cannot contain the portal
     * block, is never opened. In practice that leaves a handful of sections to actually walk.
     *
     * <p>Every candidate is compared rather than returning the first hit, because "first" depends
     * on iteration order and would happily link a portal further away than one right next to the
     * traveller. Distance is measured in three dimensions from the scaled destination.
     */
    private static BlockPos findExistingPortal(final ServerLevel level, final int x, final int y, final int z) {
        Block portal = ModBlocks.HOLLOW_HORIZON_PORTAL.get();
        int minChunkX = SectionPos.blockToSectionCoord(x - SEARCH_RADIUS);
        int maxChunkX = SectionPos.blockToSectionCoord(x + SEARCH_RADIUS);
        int minChunkZ = SectionPos.blockToSectionCoord(z - SEARCH_RADIUS);
        int maxChunkZ = SectionPos.blockToSectionCoord(z + SEARCH_RADIUS);

        BlockPos best = null;
        long bestDistance = Long.MAX_VALUE;

        for (int cx = minChunkX; cx <= maxChunkX; cx++) {
            for (int cz = minChunkZ; cz <= maxChunkZ; cz++) {
                ChunkAccess chunk = level.getChunk(cx, cz);
                LevelChunkSection[] sections = chunk.getSections();

                for (int index = 0; index < sections.length; index++) {
                    LevelChunkSection section = sections[index];
                    if (section == null || section.hasOnlyAir()
                            || !section.maybeHas(state -> state.is(portal))) {
                        continue;
                    }

                    int sectionBottom = SectionPos.sectionToBlockCoord(
                            chunk.getSectionYFromSectionIndex(index));

                    for (int ly = 0; ly < 16; ly++) {
                        for (int lx = 0; lx < 16; lx++) {
                            for (int lz = 0; lz < 16; lz++) {
                                if (!section.getBlockState(lx, ly, lz).is(portal)) {
                                    continue;
                                }

                                int bx = SectionPos.sectionToBlockCoord(cx) + lx;
                                int by = sectionBottom + ly;
                                int bz = SectionPos.sectionToBlockCoord(cz) + lz;
                                if (Math.abs(bx - x) > SEARCH_RADIUS || Math.abs(bz - z) > SEARCH_RADIUS) {
                                    continue;
                                }

                                long dx = bx - x;
                                long dy = by - y;
                                long dz = bz - z;
                                long distance = dx * dx + dy * dy + dz * dz;
                                if (distance < bestDistance) {
                                    bestDistance = distance;
                                    best = new BlockPos(bx, by, bz);
                                }
                            }
                        }
                    }
                }
            }
        }

        return best == null ? null : bottomOfPortal(level, best, portal);
    }

    /**
     * Walks down the portal sheet to its lowest cell.
     *
     * <p>The nearest cell found above can be anywhere in the sheet, including its top row. Landing
     * a traveller there drops them from the frame's full height, and on the return trip they are
     * standing in a cell whose own nearest match is a different row again - which is its own slow
     * drift. The bottom cell is the one sitting on the frame's floor, and it is stable.
     */
    private static BlockPos bottomOfPortal(final ServerLevel level, final BlockPos found, final Block portal) {
        BlockPos.MutableBlockPos walk = found.mutable();
        while (walk.getY() > level.getMinY()
                && level.getBlockState(walk.move(Direction.DOWN)).is(portal)) {
            // keep descending
        }
        return walk.move(Direction.UP).immutable();
    }

    // ------------------------------------------------------------------- build

    /**
     * Carves a pocket, lays a phonolite platform and raises a lit frame in it. Returns the
     * bottom-left interior cell - the block the traveller is dropped into.
     */
    private static BlockPos buildExitPortal(final ServerLevel level, final int x, final int y, final int z, final Direction.Axis axis) {
        int groundY = findGround(level, x, y, z);
        int baseY = Mth.clamp(groundY + 1, level.getMinY() + 1, level.getMaxY() - EXIT_HEIGHT - 1);
        if (baseY + EXIT_HEIGHT > level.getMaxY()) {
            return null;
        }

        Direction right = Direction.get(Direction.AxisDirection.POSITIVE, axis);
        Direction through = right.getClockWise();
        BlockState frameState = ModBlocks.PHONOLITE_BRICKS.get().defaultBlockState();
        BlockState air = Blocks.AIR.defaultBlockState();
        BlockState portalState = ModBlocks.HOLLOW_HORIZON_PORTAL.get().defaultBlockState()
                .setValue(HollowHorizonPortalBlock.AXIS, axis);

        // A pocket one block deep on either side of the plane, so nobody arrives inside a wall.
        for (int depth = -1; depth <= 1; depth++) {
            for (int u = -1; u <= EXIT_WIDTH; u++) {
                for (int v = 0; v <= EXIT_HEIGHT; v++) {
                    offset(x, baseY, z, right, through, u, v, depth);
                    level.setBlock(CURSOR, air, Block.UPDATE_ALL);
                }
            }
        }

        // A landing you cannot fall off, one course below the frame.
        for (int depth = -1; depth <= 1; depth++) {
            for (int u = -1; u <= EXIT_WIDTH; u++) {
                offset(x, baseY, z, right, through, u, -1, depth);
                level.setBlock(CURSOR, frameState, Block.UPDATE_ALL);
            }
        }

        // The frame ring itself. Built before the portal cells so their shape update sees a
        // complete frame and does not immediately unravel the sheet.
        for (int u = -1; u <= EXIT_WIDTH; u++) {
            for (int v = -1; v <= EXIT_HEIGHT; v++) {
                if (u != -1 && u != EXIT_WIDTH && v != -1 && v != EXIT_HEIGHT) {
                    continue;
                }

                offset(x, baseY, z, right, through, u, v, 0);
                level.setBlock(CURSOR, frameState, Block.UPDATE_ALL);
            }
        }

        for (int u = 0; u < EXIT_WIDTH; u++) {
            for (int v = 0; v < EXIT_HEIGHT; v++) {
                offset(x, baseY, z, right, through, u, v, 0);
                level.setBlock(CURSOR, portalState, PORTAL_FLAGS);
            }
        }

        offset(x, baseY, z, right, through, 0, 0, 0);
        return CURSOR.immutable();
    }

    /**
     * Finds a floor with open sky above it.
     *
     * <p>The previous implementation searched only downward from the arrival height and accepted
     * the first sturdy face it met. Arriving inside solid rock - which is the normal case when
     * the scaled destination lands in a mountain - it therefore declared the traveller's own
     * altitude to be "ground" and built the portal hundreds of blocks underground, sealed in
     * stone. That is the bug behind portals spawning buried.
     *
     * <p>This asks the world for its surface height at the column instead, then only accepts a
     * floor that actually has {@link #EXIT_HEIGHT} + 2 blocks of clear air above it. If the
     * column is solid all the way up, it climbs to the surface; if the column is empty void, it
     * returns the arrival height so a platform gets built in open air.
     */
    private static int findGround(final ServerLevel level, final int x, final int y, final int z) {
        int headroom = EXIT_HEIGHT + 2;

        // The surface heightmap is the cheap, correct answer nearly every time.
        int surface = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z);
        if (surface > level.getMinY() && hasHeadroom(level, x, surface, z, headroom)) {
            return surface - 1;
        }

        // Otherwise walk the column for the highest sturdy floor that is genuinely open above.
        int top = Math.min(level.getMaxY(), Math.max(y, surface) + GROUND_PROBE);
        int floor = Math.max(level.getMinY(), Math.min(y, surface) - GROUND_PROBE);
        for (int sy = top; sy >= floor; sy--) {
            CURSOR.set(x, sy, z);
            if (!level.getBlockState(CURSOR).isFaceSturdy(level, CURSOR, Direction.UP)) {
                continue;
            }
            if (hasHeadroom(level, x, sy + 1, z, headroom)) {
                return sy;
            }
        }

        // Nothing solid and open anywhere in range: hang the platform where they arrived.
        return y - 1;
    }

    /** True when {@code count} blocks straight up from (x, y, z) are all replaceable air. */
    private static boolean hasHeadroom(
            final ServerLevel level, final int x, final int y, final int z, final int count) {
        for (int i = 0; i < count; i++) {
            CURSOR.set(x, y + i, z);
            if (CURSOR.getY() > level.getMaxY()) {
                return true;
            }
            if (!level.getBlockState(CURSOR).isAir()) {
                return false;
            }
        }
        return true;
    }

    /**
     * Puts {@link #CURSOR} at the cell {@code u} along the portal plane, {@code v} above the
     * interior floor and {@code depth} through the plane, measured from the bottom-left interior
     * cell at ({@code x}, {@code baseY}, {@code z}).
     */
    private static void offset(
            final int x,
            final int baseY,
            final int z,
            final Direction right,
            final Direction through,
            final int u,
            final int v,
            final int depth
    ) {
        CURSOR.set(
                x + right.getStepX() * u + through.getStepX() * depth,
                baseY + v,
                z + right.getStepZ() * u + through.getStepZ() * depth
        );
    }
}

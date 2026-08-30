package com.echoingvoid.block;

import com.echoingvoid.inventory.IntegratorMenu;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.stats.Stats;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * The Knell Integrator - the station that fuses Knell onto finished netherite gear.
 *
 * <p>Right-clicking opens {@link IntegratorMenu}, whose slot layout is the smithing table's to the
 * pixel - template, base, addition - because a knell upgrade is the same operation as a netherite
 * one and there is nothing to be gained by making a player learn a second grammar for it. What has
 * changed is who may perform it: the upgrades are {@code echoing_void:integration} recipes now, not
 * {@code minecraft:smithing_transform}, so a smithing table no longer finds them and this station
 * is a real gate rather than a shortcut a player can skip.
 *
 * <p>Passing {@link ContainerLevelAccess#NULL} to the menu would compile and would be a bug:
 * {@code ItemCombinerMenu.removed} returns the input slots through that same accessor, so a player
 * closing the screen with items in it would simply lose them.
 *
 * <p>The block is a real machine shape rather than a cube - a squat null-iron chassis on four
 * corner conduits, a deck, and a bismuth resonator ring standing proud on top. The model in
 * {@code tools/gen_knell_data.py} carries the geometry; {@link #SHAPE} is the matching collision
 * so the silhouette a player sees is the silhouette they bump into.
 */
public class KnellIntegratorBlock extends Block {
    public static final MapCodec<KnellIntegratorBlock> CODEC = simpleCodec(KnellIntegratorBlock::new);

    /** Shown as the smithing screen's title, so the station names itself while it is open. */
    private static final Component CONTAINER_TITLE =
            Component.translatable("container.echoing_void.knell_integrator");

    /** Magenta harmonic, the arcane family's bright tone - the same note the knell gear carries. */
    private static final int RING_COLOR = 0xFF007F;

    /**
     * Chassis, deck, the four corner conduits, and the resonator ring.
     *
     * <p>These are the same boxes {@code tools/gen_knell_data.py} writes as the model's
     * elements, in the same order. The ring is filled rather than hollow: a player is never going
     * to try to stand in a two-pixel gap, and a hollow collision shape here would only cost
     * intersection tests.
     */
    private static final VoxelShape SHAPE = Shapes.or(
            Block.box(2.0, 0.0, 2.0, 14.0, 10.0, 14.0),
            Block.box(3.0, 10.0, 3.0, 13.0, 12.0, 13.0),
            Block.box(0.0, 0.0, 0.0, 2.0, 9.0, 2.0),
            Block.box(14.0, 0.0, 0.0, 16.0, 9.0, 2.0),
            Block.box(0.0, 0.0, 14.0, 2.0, 9.0, 16.0),
            Block.box(14.0, 0.0, 14.0, 16.0, 9.0, 16.0),
            Block.box(4.0, 12.0, 4.0, 12.0, 15.0, 12.0));

    public KnellIntegratorBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<KnellIntegratorBlock> codec() {
        return CODEC;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPE;
    }

    @Override
    protected boolean useShapeForLightOcclusion(BlockState state) {
        return true;
    }

    @Override
    protected MenuProvider getMenuProvider(BlockState state, Level level, BlockPos pos) {
        return new SimpleMenuProvider(
                (containerId, inventory, player) ->
                        new IntegratorMenu(containerId, inventory,
                                ContainerLevelAccess.create(level, pos)),
                CONTAINER_TITLE);
    }

    @Override
    protected InteractionResult useWithoutItem(
        BlockState state,
        Level level,
        BlockPos pos,
        Player player,
        BlockHitResult hitResult
    ) {
        if (!level.isClientSide()) {
            player.openMenu(state.getMenuProvider(level, pos));
            // The station is a smithing table as far as the player's hands are concerned, so it
            // advances the same statistic. A private counter would only fragment the stats screen.
            player.awardStat(Stats.INTERACT_WITH_SMITHING_TABLE);
        }

        return InteractionResult.SUCCESS;
    }

    /**
     * Idle running lights: a slow magenta drift out of the resonator ring, and the occasional spark
     * off the deck. This is the only cue that the block is powered, so it is deliberately sparse -
     * a constant plume would read as damage rather than standby.
     */
    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if (random.nextInt(8) == 0) {
            // On the ring itself, which spans 3..13 in x and z at y 12..15.
            double angle = random.nextDouble() * Math.PI * 2.0;
            double radius = 0.31;
            level.addParticle(
                new DustParticleOptions(RING_COLOR, 1.0F),
                pos.getX() + 0.5 + Math.cos(angle) * radius,
                pos.getY() + 0.9,
                pos.getZ() + 0.5 + Math.sin(angle) * radius,
                0.0,
                0.015,
                0.0
            );
        }

        if (random.nextInt(24) == 0) {
            level.addParticle(
                ParticleTypes.ELECTRIC_SPARK,
                pos.getX() + 0.25 + random.nextDouble() * 0.5,
                pos.getY() + 0.75,
                pos.getZ() + 0.25 + random.nextDouble() * 0.5,
                0.0,
                0.0,
                0.0
            );
        }
    }

}

package com.echoingvoid.block;

import com.echoingvoid.block.entity.AcousticLockBoxBlockEntity;
import com.echoingvoid.registry.ModItems;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.gameevent.GameEvent;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;

/**
 * The Acoustic Lock Box - the safe at the heart of a Sound Vault.
 *
 * <p>There is no keyhole and no key. Each of the four sides is a tine with its own pitch; strike
 * them with a Tuning Fork and the box answers. Strike the four in the right order and it opens and
 * gives up what it was holding. Strike a wrong one and the run resets, silently except for a flat
 * bass note - the player learns the combination by ear and by patience, not by reading it anywhere.
 *
 * <p>Striking the top or bottom does nothing but thud: there is no tine on those faces. The order
 * itself lives in {@link AcousticLockBoxBlockEntity}, derived from the block's coordinates so the
 * same vault always has the same answer.
 */
public class AcousticLockBoxBlock extends BaseEntityBlock {
    public static final MapCodec<AcousticLockBoxBlock> CODEC = simpleCodec(AcousticLockBoxBlock::new);

    public AcousticLockBoxBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<? extends BaseEntityBlock> codec() {
        return CODEC;
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos worldPosition, BlockState blockState) {
        return new AcousticLockBoxBlockEntity(worldPosition, blockState);
    }

    @Override
    protected InteractionResult useItemOn(
        ItemStack itemStack,
        BlockState state,
        Level level,
        BlockPos pos,
        Player player,
        InteractionHand hand,
        BlockHitResult hitResult
    ) {
        if (!itemStack.is(ModItems.TUNING_FORK.get())) {
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        if (!(level.getBlockEntity(pos) instanceof AcousticLockBoxBlockEntity box) || box.isUnlocked()) {
            return InteractionResult.TRY_WITH_EMPTY_HAND;
        }

        if (level instanceof ServerLevel serverLevel) {
            int tine = AcousticLockBoxBlockEntity.tineFor(hitResult.getDirection());
            if (tine < 0) {
                // No tine on the top or bottom face - a dead strike, and no penalty for it either.
                note(serverLevel, pos, SoundEvents.NOTE_BLOCK_BASS, 0.5F, 0.5F);
            } else {
                strike(serverLevel, pos, player, box, tine);
            }
        }

        return InteractionResult.SUCCESS;
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        if (level.getBlockEntity(pos) instanceof AcousticLockBoxBlockEntity box && !box.isUnlocked()) {
            if (level instanceof ServerLevel serverLevel) {
                // A bare hand only tells you it is shut.
                serverLevel.playSound(null, pos, SoundEvents.NETHERITE_BLOCK_HIT, SoundSource.BLOCKS, 0.6F, 0.5F);
            }

            return InteractionResult.SUCCESS;
        }

        return InteractionResult.PASS;
    }

    private static void strike(ServerLevel level, BlockPos pos, Player player, AcousticLockBoxBlockEntity box, int tine) {
        boolean correct = box.strike(tine);

        // The tine always sounds, right or wrong - that is how the combination is learnt.
        note(level, pos, SoundEvents.NOTE_BLOCK_BELL, 1.0F, AcousticLockBoxBlockEntity.pitchFor(tine));
        level.sendParticles(ParticleTypes.NOTE, pos.getX() + 0.5, pos.getY() + 1.1, pos.getZ() + 0.5, 0, tine / 4.0, 0.0, 0.0, 1.0);

        if (!correct) {
            note(level, pos, SoundEvents.NOTE_BLOCK_BASS, 0.8F, 0.5F);
            return;
        }

        if (box.isComplete()) {
            box.open(level);
            note(level, pos, SoundEvents.NOTE_BLOCK_CHIME, 1.0F, 2.0F);
            level.playSound(null, pos, SoundEvents.IRON_DOOR_OPEN, SoundSource.BLOCKS, 0.9F, 1.4F);
            level.gameEvent(player, GameEvent.BLOCK_OPEN, pos);
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK, pos.getX() + 0.5, pos.getY() + 1.05, pos.getZ() + 0.5, 12, 0.35, 0.1, 0.35, 0.06);
        }
    }

    /** Note block sounds are registered as holders, so the holder overload is the direct route. */
    private static void note(ServerLevel level, BlockPos pos, Holder<SoundEvent> sound, float volume, float pitch) {
        level.playSound(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, sound, SoundSource.BLOCKS, volume, pitch);
    }
}

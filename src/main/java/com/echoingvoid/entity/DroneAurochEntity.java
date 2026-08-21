package com.echoingvoid.entity;

import com.echoingvoid.registry.ModCrops;
import com.echoingvoid.registry.ModNewEntities;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.jspecify.annotations.Nullable;

/**
 * The Drone Auroch - this dimension's cow, and the source of Drone Loin.
 *
 * <p>A "drone" is a sustained low note, and that is the whole brief for the animal: big, slow,
 * and constantly sounding. It is the heavier and slower of the two, exactly as a cow is to a pig,
 * so a player choosing what to farm is making the same trade they already understand.
 *
 * <p>It is tempted and bred by Resonant Grain - the harvest crop, the one thing on the farm that is
 * not itself a meal - which keeps the grain worth growing beyond bread.
 */
public class DroneAurochEntity extends VoidLivestockEntity {

    public DroneAurochEntity(EntityType<? extends DroneAurochEntity> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return createLivestockAttributes(0.20);
    }

    @Override
    public @Nullable AgeableMob getBreedOffspring(ServerLevel level, AgeableMob mate) {
        return ModNewEntities.DRONE_AUROCH.get().create(level, net.minecraft.world.entity.EntitySpawnReason.BREEDING);
    }

    @Override
    public boolean isFood(ItemStack stack) {
        return stack.is(ModCrops.RESONANT_GRAIN.get());
    }

    /** Low and slow, and pitched down so it reads as the drone it is named for. */
    @Override
    protected @Nullable SoundEvent getAmbientSound() {
        return SoundEvents.AMETHYST_BLOCK_RESONATE;
    }

    @Override
    public float getVoicePitch() {
        return 0.55F + this.random.nextFloat() * 0.15F;
    }
}

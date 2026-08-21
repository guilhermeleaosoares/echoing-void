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
 * The Thrum Boar - this dimension's pig, and the source of Thrum Ribs.
 *
 * <p>A "thrum" is a rhythmic hum rather than a held note, so where the Drone Auroch is slow and
 * continuous this one is quicker and pulses. Smaller and faster than the auroch, which is the same
 * relationship a pig has to a cow.
 *
 * <p>Tempted and bred by Void Tubers - the root a player has the least other use for, which gives
 * the weakest crop on the farm a reason to exist.
 */
public class ThrumBoarEntity extends VoidLivestockEntity {

    public ThrumBoarEntity(EntityType<? extends ThrumBoarEntity> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return createLivestockAttributes(0.25);
    }

    @Override
    public @Nullable AgeableMob getBreedOffspring(ServerLevel level, AgeableMob mate) {
        return ModNewEntities.THRUM_BOAR.get().create(level, net.minecraft.world.entity.EntitySpawnReason.BREEDING);
    }

    @Override
    public boolean isFood(ItemStack stack) {
        return stack.is(ModCrops.VOID_TUBER.get());
    }

    /** Higher and shorter than the auroch's, so the two are told apart with eyes shut. */
    @Override
    protected @Nullable SoundEvent getAmbientSound() {
        return SoundEvents.AMETHYST_BLOCK_CHIME;
    }

    @Override
    public float getVoicePitch() {
        return 0.9F + this.random.nextFloat() * 0.3F;
    }
}

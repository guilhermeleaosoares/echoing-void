package com.echoingvoid.entity;

import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.BreedGoal;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.FollowParentGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.PanicGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.TemptGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.jspecify.annotations.Nullable;

/**
 * Shared behaviour for the Hollow Horizon's two grazing animals.
 *
 * <p>PLAYER: "add two mobs, equivilent to overworld cows and pigs, passive mobs that can be killed
 * for their meat."
 *
 * <p>So both are {@link Animal}s and behave like one: they wander, they flee when struck, they can
 * be led and bred with the dimension's own crops, and they drop meat. Everything a player already
 * knows about a cow transfers, which is the point - this dimension has had nothing to farm for
 * meat, and the fix should not need explaining.
 *
 * <p>What separates the two is small and lives in the subclasses: size, speed, what tempts them,
 * and the note they make. This class exists so the goal list and the breeding rules are written
 * once - two near-identical AI setups drifting apart is exactly the kind of thing that produces a
 * pig that can be bred and a cow that silently cannot.
 *
 * <p>Sounds are vanilla's. Shipping new {@code SoundEvent}s would mean shipping {@code .ogg} audio,
 * which this project cannot synthesise; on-theme vanilla sounds are used throughout the mod for the
 * same reason.
 */
public abstract class VoidLivestockEntity extends Animal {

    protected VoidLivestockEntity(EntityType<? extends VoidLivestockEntity> type, Level level) {
        super(type, level);
    }

    /** Cow and pig figures: ten health, and a walk that a player can outrun. */
    public static AttributeSupplier.Builder createLivestockAttributes(double speed) {
        return Animal.createAnimalAttributes()
                .add(Attributes.MAX_HEALTH, 10.0)
                .add(Attributes.MOVEMENT_SPEED, speed)
                .add(Attributes.FOLLOW_RANGE, 16.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        // Panic before anything else: a struck animal running is what makes it read as prey
        // rather than as furniture.
        this.goalSelector.addGoal(1, new PanicGoal(this, 2.0));
        this.goalSelector.addGoal(2, new BreedGoal(this, 1.0));
        this.goalSelector.addGoal(3, new TemptGoal(this, 1.2, stack -> this.isFood(stack), false));
        this.goalSelector.addGoal(4, new FollowParentGoal(this, 1.1));
        this.goalSelector.addGoal(5, new WaterAvoidingRandomStrollGoal(this, 1.0));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 6.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.AMETHYST_BLOCK_HIT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.AMETHYST_BLOCK_BREAK;
    }

    @Override
    protected void playStepSound(net.minecraft.core.BlockPos pos,
                                 net.minecraft.world.level.block.state.BlockState state) {
        this.playSound(SoundEvents.AMETHYST_BLOCK_STEP, 0.12F, 1.0F);
    }

    /** Both are ageable, so both need a child form; the subclass names its own type. */
    @Override
    public abstract @Nullable AgeableMob getBreedOffspring(net.minecraft.server.level.ServerLevel level,
                                                           AgeableMob mate);

    @Override
    public abstract boolean isFood(ItemStack stack);
}

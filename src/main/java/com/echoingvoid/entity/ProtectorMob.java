package com.echoingvoid.entity;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

/**
 * PLAYER: "the outpost could have a village iron golem equivalent creature that spawns naturally
 * in inhabited outposts, or can be naturally built with a carved pumpkin head and body structure
 * different but similar to that of an iron golem... this protector mob is also neutral but
 * attacks when the neutral trader mobs are attacked, and it only exists in outposts, not the
 * camps."
 *
 * <p>Neutral by default: no goal here ever targets anything on its own initiative. Two things can
 * give it a target - being struck directly ({@link HurtByTargetGoal}, so it is not free damage),
 * or a nearby {@link TraderMob} being struck ({@link DefendTraderGoal}) - and once it has a
 * target it does not let go until that fight is over, exactly like an iron golem.
 *
 * <p>Built via {@link com.echoingvoid.block.TunersMaskBlock}, which checks for this same body
 * shape in null-iron blocks under a placed mask, mirroring {@code CarvedPumpkinBlock}. Also
 * placed naturally at the outpost - see {@code tools/gen_worldgen.py}'s structure-scoped spawn
 * wiring, since the biome-level spawn tables this mod otherwise uses cannot express "only near
 * this one structure".
 */
public class ProtectorMob extends PathfinderMob {

    public ProtectorMob(EntityType<? extends ProtectorMob> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 90.0)
                .add(Attributes.MOVEMENT_SPEED, 0.24)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.ATTACK_DAMAGE, 12.0)
                .add(Attributes.ATTACK_KNOCKBACK, 1.2)
                .add(Attributes.ARMOR, 6.0)
                .add(Attributes.FOLLOW_RANGE, 24.0);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new MeleeAttackGoal(this, 1.0, true));
        this.goalSelector.addGoal(2, new WaterAvoidingRandomStrollGoal(this, 0.3));
        this.goalSelector.addGoal(3, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(4, new RandomLookAroundGoal(this));

        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        // Covers both a player and a hostile mob attacking a nearby trader -
        // DefendTraderGoal reads TraderMob.getLastHurtByMob(), which vanilla
        // sets for any LivingEntity attacker, not only players.
        this.targetSelector.addGoal(2, new DefendTraderGoal(this));
    }
}

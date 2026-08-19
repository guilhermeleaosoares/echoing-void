package com.echoingvoid.fluid;

import com.echoingvoid.EchoingVoid;
import net.minecraft.resources.Identifier;
import net.minecraft.sounds.SoundEvents;
import net.minecraftforge.client.extensions.common.IClientFluidTypeExtensions;
import net.minecraftforge.common.SoundActions;
import net.minecraftforge.fluids.FluidType;

import java.util.function.Consumer;

/**
 * Hushwater - the Hollow Horizon's liquid.
 *
 * <p>Named for the dimension's voice rather than for what it looks like: a "hush" is the silence
 * this world is made of, and the fluid soothes rather than harms, which is the one thing every
 * other liquid in the game does not do.
 *
 * <p>Every physical constant here sits deliberately between water and lava, because that is the
 * body the fluid is meant to have - heavier and slower than water, nothing like as sluggish as
 * lava:
 *
 * <table>
 *   <tr><th></th><th>water</th><th>hushwater</th><th>lava</th></tr>
 *   <tr><td>density</td><td>1000</td><td>1600</td><td>3000</td></tr>
 *   <tr><td>viscosity</td><td>1000</td><td>2400</td><td>6000</td></tr>
 *   <tr><td>motionScale</td><td>0.014</td><td>0.010</td><td>0.007</td></tr>
 *   <tr><td>tick delay</td><td>5</td><td>12</td><td>30</td></tr>
 * </table>
 *
 * <p>Two properties are not a blend of the two and are the point of the fluid:
 *
 * <ul>
 *   <li>{@code fallDistanceModifier(0)} - a fall into hushwater is free. A stream spilling off a
 *       floating island is the intended way down from one, so it must not be a way to die.
 *   <li>{@code canDrown(false)} - swimming in it is the reward, not the risk. The healing itself
 *       lives in {@link com.echoingvoid.event.FluidEvents}, which sees each entity exactly once a
 *       tick; doing it from the fluid's own {@code entityInside} would heal once per intersecting
 *       block and so scale with how deep the swimmer is.
 * </ul>
 *
 * <p>{@code canHydrate(true)} is what lets a lake water the void farmland beside it - Forge routes
 * {@code FarmlandBlock.isNearWater} through {@code BlockState#canBeHydrated}, which asks the fluid.
 */
public final class HushwaterFluidType extends FluidType {

    /**
     * ARGB tint multiplied into the still and flowing sprites. Left at plain white: the
     * sprites are already painted on the bismuth ramp from {@code docs/spec/art_direction.json},
     * and multiplying a second cyan over them would push them off that palette.
     */
    public static final int TINT = 0xFFFFFFFF;

    public HushwaterFluidType() {
        super(FluidType.Properties.create()
                .descriptionId("fluid." + EchoingVoid.MODID + ".hushwater")
                .density(1600)
                .viscosity(2400)
                .temperature(285)
                .lightLevel(6)
                .motionScale(0.010D)
                .fallDistanceModifier(0.0F)
                .canPushEntity(true)
                .canSwim(true)
                .canDrown(false)
                .canExtinguish(true)
                .canConvertToSource(false)
                .canHydrate(true)
                .supportsBoating(true)
                .sound(SoundActions.BUCKET_FILL, SoundEvents.BUCKET_FILL)
                .sound(SoundActions.BUCKET_EMPTY, SoundEvents.BUCKET_EMPTY));
    }

    /**
     * The still/flow sprites and the tint.
     *
     * <p>Written as an anonymous class inside this method on purpose: {@code FluidType#initClient}
     * only calls it when {@code FMLEnvironment.dist == Dist.CLIENT}, so the anonymous class - the
     * only thing here that touches a client-side type - is never loaded on a dedicated server.
     * Extending {@code IClientFluidTypeExtensions} on this class instead is explicitly rejected by
     * Forge at runtime.
     */
    @Override
    public void initializeClient(Consumer<IClientFluidTypeExtensions> consumer) {
        consumer.accept(new IClientFluidTypeExtensions() {
            private final Identifier still = EchoingVoid.id("block/hushwater_still");
            private final Identifier flowing = EchoingVoid.id("block/hushwater_flow");
            private final Identifier overlay = EchoingVoid.id("block/hushwater_overlay");

            @Override
            public Identifier getStillTexture() {
                return still;
            }

            @Override
            public Identifier getFlowingTexture() {
                return flowing;
            }

            @Override
            public Identifier getOverlayTexture() {
                return overlay;
            }

            @Override
            public int getTintColor() {
                return TINT;
            }
        });
    }
}

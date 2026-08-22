package com.echoingvoid.item;

/**
 * The Resonance set's kinetic bank and shockwave, amplified.
 *
 * <p>PLAYER: "fix knell armor please" - the four Knell plates were registered as plain
 * {@code Item}s, so a player who had done the whole ladder (netherite kit, portal, dimension,
 * the rarest ore in the mod) was handed armour that had <em>lost</em> an ability their previous
 * set had. Nothing announced it; the pieces looked identical, wore identically, and simply never
 * banked or released.
 *
 * <p>What this tier changes is the ability and only the ability, which is the rule the rest of
 * the Knell gear already follows - {@link KnellSwordItem} grows the sonic radius and duration and
 * leaves the damage baseline at netherite's, {@link KnellPickaxeItem} grows the shatter plane and
 * leaves the mining stats alone. So the mitigation figures here are deliberately <em>identical</em>
 * to Resonance's. The passive step between the two sets is already paid by
 * {@link KnellMaterials#RESONANT}: +2 toughness and +0.1 knockback resistance over netherite,
 * applied by the game before any of this code runs. Stacking a bigger flat pre-armour cut on top
 * of a stronger material is how a set stops being armour and starts being immunity.
 *
 * <p>The bank is where the tier is spent instead, and it is spent roughly where the pickaxe
 * spends it - that tool goes from a 9-block face to a 20-block one, about double:
 *
 * <table border="1">
 *   <caption>Resonance against Knell</caption>
 *   <tr><th></th><th>Resonance</th><th>Knell</th></tr>
 *   <tr><td>banked share of a hit</td><td>50%</td><td>65%</td></tr>
 *   <tr><td>capacity</td><td>60</td><td>100</td></tr>
 *   <tr><td>ring radius</td><td>6.0</td><td>9.0</td></tr>
 *   <tr><td>returned share</td><td>40%</td><td>55%</td></tr>
 *   <tr><td>damage at a full bank</td><td>24</td><td>55</td></tr>
 *   <tr><td>knockback</td><td>0.6 - 2.2</td><td>0.9 - 3.0</td></tr>
 * </table>
 *
 * <p>{@link #minRelease()} is left alone on purpose. It is the floor that stops a player wasting
 * a charge on nothing, not a difficulty knob, and raising it with the capacity would have made
 * the better armour the one that refuses to fire more often.
 */
public class KnellArmorItem extends ResonanceArmorItem {

    public KnellArmorItem(Properties properties) {
        super(properties);
    }

    @Override
    public float bankRate() {
        return 0.65F;
    }

    @Override
    public float bankCapacity() {
        return 100.0F;
    }

    @Override
    public double shockwaveRadius() {
        return 9.0;
    }

    @Override
    public float damageReturn() {
        return 0.55F;
    }

    @Override
    public double minKnockback() {
        return 0.9;
    }

    @Override
    public double maxKnockback() {
        return 3.0;
    }
}

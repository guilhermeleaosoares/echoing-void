package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.recipe.IntegrationRecipe;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SmithingRecipe;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

/**
 * The mod's own recipe type, and the only reason it exists.
 *
 * <p>A recipe's TYPE is what decides which station can run it. {@code SmithingMenu} asks the recipe
 * manager for everything of {@code RecipeType.SMITHING} and never checks which block it was opened
 * over, so while the knell upgrades were {@code minecraft:smithing_transform} recipes, every
 * smithing table in the world could perform them - and the Knell Integrator, the station that is
 * supposed to gate the whole tier, could simply be skipped.
 *
 * <p>Nothing hides a recipe from a menu that queries by type, so the upgrades get a type of their
 * own instead. See {@link IntegrationRecipe}.
 *
 * <p>Note the registry keys: {@code ForgeRegistries} has no entry for either recipe registry, so
 * both go through the vanilla {@link Registries} keys - the same route
 * {@link ModComponents} takes for data components.
 */
public final class ModRecipes {
    private ModRecipes() {}

    public static final DeferredRegister<RecipeType<?>> TYPES =
            DeferredRegister.create(Registries.RECIPE_TYPE, EchoingVoid.MODID);

    public static final DeferredRegister<RecipeSerializer<?>> SERIALIZERS =
            DeferredRegister.create(Registries.RECIPE_SERIALIZER, EchoingVoid.MODID);

    /**
     * Upgrades only the Knell Integrator can perform.
     *
     * <p>Typed {@code RecipeType<SmithingRecipe>} rather than {@code RecipeType<IntegrationRecipe>}
     * because {@link SmithingRecipe#getType()} declares that signature and an override may not
     * narrow it. It costs nothing: the menu casts back through {@code RecipeHolder} anyway.
     */
    public static final RegistryObject<RecipeType<SmithingRecipe>> INTEGRATION =
            TYPES.register("integration", () -> RecipeType.simple(EchoingVoid.id("integration")));

    public static final RegistryObject<RecipeSerializer<IntegrationRecipe>> INTEGRATION_SERIALIZER =
            SERIALIZERS.register("integration",
                    () -> new RecipeSerializer<>(IntegrationRecipe.MAP_CODEC,
                            IntegrationRecipe.STREAM_CODEC));

    public static void register(BusGroup modBus) {
        TYPES.register(modBus);
        SERIALIZERS.register(modBus);
    }
}

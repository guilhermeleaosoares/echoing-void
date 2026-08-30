package com.echoingvoid.recipe;

import com.echoingvoid.registry.ModKnell;
import com.echoingvoid.registry.ModRecipes;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemStackTemplate;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.PlacementInfo;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SimpleSmithingRecipe;
import net.minecraft.world.item.crafting.SmithingRecipe;
import net.minecraft.world.item.crafting.SmithingRecipeInput;
import net.minecraft.world.item.crafting.TransmuteRecipe;
import net.minecraft.world.item.crafting.display.RecipeDisplay;
import net.minecraft.world.item.crafting.display.SlotDisplay;
import net.minecraft.world.item.crafting.display.SmithingRecipeDisplay;

import java.util.List;
import java.util.Optional;

/**
 * An upgrade that only the Knell Integrator can perform.
 *
 * <p>PLAYER: "the smithing table should be unable to make knell tools with the knell template,
 * which it currently can, as this defeats the purpose of making the knell integrator."
 *
 * <p>They were right, and the reason is structural rather than a missing check. The nine knell
 * upgrades were ordinary {@code minecraft:smithing_transform} recipes, and a recipe's type is what
 * decides who can run it: {@code SmithingMenu.createResult} asks for every recipe of
 * {@code RecipeType.SMITHING} and does not care which block the menu was opened over. So any
 * smithing table in the world could perform them, and the Integrator - the whole point of which is
 * to be the gate on the tier - was a decoration you could skip.
 *
 * <p>There is no way to hide a recipe from a menu that queries by type, so this class gives the
 * upgrades a type of their own: {@link ModRecipes#INTEGRATION}. A vanilla smithing table now finds
 * no knell recipes at all, because as far as {@code RecipeType.SMITHING} is concerned there are
 * none.
 *
 * <p>Everything else is deliberately {@link net.minecraft.world.item.crafting.SmithingTransformRecipe}
 * verbatim - the same three optional/required ingredients, the same codecs, the same
 * component-preserving assemble. Behaving differently from a smithing upgrade was never the goal;
 * being performable somewhere else was.
 */
public class IntegrationRecipe extends SimpleSmithingRecipe {

    public static final MapCodec<IntegrationRecipe> MAP_CODEC = RecordCodecBuilder.mapCodec(
            i -> i.group(
                            Recipe.CommonInfo.MAP_CODEC.forGetter(o -> o.commonInfo),
                            Ingredient.CODEC.optionalFieldOf("template").forGetter(o -> o.template),
                            Ingredient.CODEC.fieldOf("base").forGetter(o -> o.base),
                            Ingredient.CODEC.optionalFieldOf("addition").forGetter(o -> o.addition),
                            ItemStackTemplate.CODEC.fieldOf("result").forGetter(o -> o.result))
                    .apply(i, IntegrationRecipe::new));

    public static final StreamCodec<RegistryFriendlyByteBuf, IntegrationRecipe> STREAM_CODEC =
            StreamCodec.composite(
                    Recipe.CommonInfo.STREAM_CODEC, o -> o.commonInfo,
                    Ingredient.OPTIONAL_CONTENTS_STREAM_CODEC, o -> o.template,
                    Ingredient.CONTENTS_STREAM_CODEC, o -> o.base,
                    Ingredient.OPTIONAL_CONTENTS_STREAM_CODEC, o -> o.addition,
                    ItemStackTemplate.STREAM_CODEC, o -> o.result,
                    IntegrationRecipe::new);

    private final Optional<Ingredient> template;
    private final Ingredient base;
    private final Optional<Ingredient> addition;
    private final ItemStackTemplate result;

    public IntegrationRecipe(Recipe.CommonInfo commonInfo, Optional<Ingredient> template,
                             Ingredient base, Optional<Ingredient> addition,
                             ItemStackTemplate result) {
        super(commonInfo);
        this.template = template;
        this.base = base;
        this.addition = addition;
        this.result = result;
    }

    /**
     * The whole point of the class.
     *
     * <p>The return type must stay {@code RecipeType<SmithingRecipe>} rather than narrowing to this
     * class, because that is what the {@link SmithingRecipe} interface declares and Java will not
     * let an override narrow it. {@link ModRecipes#INTEGRATION} is registered at that type for the
     * same reason.
     */
    @Override
    public RecipeType<SmithingRecipe> getType() {
        return ModRecipes.INTEGRATION.get();
    }

    /**
     * Keeps the base item's components, so an upgrade carries enchantments, a name, a trim and any
     * banked charge across rather than handing back a factory-fresh item.
     */
    public ItemStack assemble(SmithingRecipeInput input) {
        return TransmuteRecipe.createWithOriginalComponents(this.result, input.base());
    }

    @Override
    public Optional<Ingredient> templateIngredient() {
        return this.template;
    }

    @Override
    public Ingredient baseIngredient() {
        return this.base;
    }

    @Override
    public Optional<Ingredient> additionIngredient() {
        return this.addition;
    }

    @Override
    public RecipeSerializer<IntegrationRecipe> getSerializer() {
        return ModRecipes.INTEGRATION_SERIALIZER.get();
    }

    @Override
    protected PlacementInfo createPlacementInfo() {
        return PlacementInfo.createFromOptionals(
                List.of(this.template, Optional.of(this.base), this.addition));
    }

    /**
     * The station icon is the Integrator rather than a smithing table - this is the one display
     * detail that must not be copied verbatim, since showing a smithing table beside a recipe no
     * smithing table can perform is exactly the confusion this change exists to remove.
     */
    @Override
    public List<RecipeDisplay> display() {
        return List.of(new SmithingRecipeDisplay(
                Ingredient.optionalIngredientToDisplay(this.template),
                this.base.display(),
                Ingredient.optionalIngredientToDisplay(this.addition),
                new SlotDisplay.ItemStackSlotDisplay(this.result),
                new SlotDisplay.ItemSlotDisplay(ModKnell.RESONANCE_INTEGRATOR_ITEM.get())));
    }
}

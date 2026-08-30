package com.echoingvoid.inventory;

import com.echoingvoid.recipe.IntegrationRecipe;
import com.echoingvoid.registry.ModKnell;
import com.echoingvoid.registry.ModMenus;
import com.echoingvoid.registry.ModRecipes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.inventory.ItemCombinerMenu;
import net.minecraft.world.inventory.ItemCombinerMenuSlotDefinition;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.SmithingRecipe;
import net.minecraft.world.item.crafting.SmithingRecipeInput;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;
import java.util.Optional;

/**
 * The Knell Integrator's own menu.
 *
 * <p>This used to be a two-line subclass of {@code SmithingMenu} that changed only
 * {@link #isValidBlock}, which was the right call while the upgrades were ordinary smithing
 * recipes. They are not any more - see {@link IntegrationRecipe} - and {@code SmithingMenu} is
 * welded to {@code RecipeType.SMITHING} in {@code createResult}, so the station needs a menu of its
 * own to look up the type that its recipes actually have.
 *
 * <p>The layout is deliberately identical to the smithing table's, down to the pixel: template at
 * x 8, base at 26, addition at 44, result at 98, all on row 48. A player who has used a smithing
 * table should not have to work anything out here, and the custom screen is a change of dress, not
 * of grammar.
 *
 * <p>Note {@link ContainerLevelAccess} rather than {@code NULL} in the block's provider:
 * {@code ItemCombinerMenu.removed} returns the input slots through that same accessor, so a menu
 * opened with NULL would quietly eat any items left in it when the player closes the screen.
 */
public class IntegratorMenu extends ItemCombinerMenu {

    public static final int TEMPLATE_SLOT = 0;
    public static final int BASE_SLOT = 1;
    public static final int ADDITION_SLOT = 2;
    public static final int RESULT_SLOT = 3;

    private final Level level;

    /** Client-side constructor: the factory {@code MenuType} calls when the screen opens. */
    public IntegratorMenu(int containerId, Inventory inventory) {
        this(containerId, inventory, ContainerLevelAccess.NULL);
    }

    public IntegratorMenu(int containerId, Inventory inventory, ContainerLevelAccess access) {
        super(ModMenus.KNELL_INTEGRATOR.get(), containerId, inventory, access, slots());
        this.level = inventory.player.level();
    }

    /**
     * Smithing's exact slot geometry.
     *
     * <p>The predicates are permissive on purpose. Vanilla filters these slots through
     * {@code RecipePropertySet.SMITHING_*}, which the recipe manager builds by scanning
     * {@code RecipeType.SMITHING} - so it would be empty for this station's type and would reject
     * every item a player tried to insert. Rebuilding an equivalent index would buy nothing:
     * {@link #createResult()} is the real arbiter, and a slot that accepts an item which turns out
     * not to fit costs a player one click, where a slot that silently refuses a valid item costs
     * them the afternoon.
     */
    private static ItemCombinerMenuSlotDefinition slots() {
        return ItemCombinerMenuSlotDefinition.create()
                .withSlot(TEMPLATE_SLOT, 8, 48, stack -> true)
                .withSlot(BASE_SLOT, 26, 48, stack -> true)
                .withSlot(ADDITION_SLOT, 44, 48, stack -> true)
                .withResultSlot(RESULT_SLOT, 98, 48)
                .build();
    }

    @Override
    protected boolean isValidBlock(BlockState state) {
        return state.is(ModKnell.RESONANCE_INTEGRATOR.get());
    }

    @Override
    public void createResult() {
        SmithingRecipeInput input = new SmithingRecipeInput(
                this.inputSlots.getItem(TEMPLATE_SLOT),
                this.inputSlots.getItem(BASE_SLOT),
                this.inputSlots.getItem(ADDITION_SLOT));

        Optional<RecipeHolder<SmithingRecipe>> found = this.level instanceof ServerLevel serverLevel
                ? serverLevel.recipeAccess().getRecipeFor(ModRecipes.INTEGRATION.get(), input, serverLevel)
                : Optional.empty();

        // The cast is safe by construction - IntegrationRecipe is the only class registered
        // against this type - but it is written as a pattern match rather than a cast so that a
        // datapack declaring something else under echoing_void:integration produces an empty
        // result slot instead of a ClassCastException in the middle of a menu tick.
        found.filter(holder -> holder.value() instanceof IntegrationRecipe)
                .ifPresentOrElse(holder -> {
                    ItemStack result = ((IntegrationRecipe) holder.value()).assemble(input);
                    this.resultSlots.setRecipeUsed(holder);
                    this.resultSlots.setItem(0, result);
                }, () -> {
                    this.resultSlots.setRecipeUsed(null);
                    this.resultSlots.setItem(0, ItemStack.EMPTY);
                });
    }

    @Override
    protected void onTake(Player player, ItemStack carried) {
        carried.onCraftedBy(player, carried.getCount());
        this.resultSlots.awardUsedRecipes(player, List.of(
                this.inputSlots.getItem(TEMPLATE_SLOT),
                this.inputSlots.getItem(BASE_SLOT),
                this.inputSlots.getItem(ADDITION_SLOT)));
        shrink(TEMPLATE_SLOT);
        shrink(BASE_SLOT);
        shrink(ADDITION_SLOT);
        // 1044 is the smithing table's use sound. The station is a smithing table as far as the
        // player's hands are concerned, so it should sound like one.
        this.access.execute((level, pos) -> level.levelEvent(1044, pos, 0));
    }

    private void shrink(int slot) {
        ItemStack stack = this.inputSlots.getItem(slot);
        if (!stack.isEmpty()) {
            stack.shrink(1);
            this.inputSlots.setItem(slot, stack);
        }
    }

    @Override
    public boolean canTakeItemForPickAll(ItemStack carried, Slot target) {
        return target.container != this.resultSlots && super.canTakeItemForPickAll(carried, target);
    }

    /** Shift-click fills the first free input slot, left to right. */
    @Override
    public boolean canMoveIntoInputSlots(ItemStack stack) {
        return !this.getSlot(TEMPLATE_SLOT).hasItem()
                || !this.getSlot(BASE_SLOT).hasItem()
                || !this.getSlot(ADDITION_SLOT).hasItem();
    }
}

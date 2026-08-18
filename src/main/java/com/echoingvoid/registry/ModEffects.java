package com.echoingvoid.registry;

import com.echoingvoid.EchoingVoid;
import com.echoingvoid.block.NullIronJukeboxBlock;
import com.echoingvoid.block.entity.NullIronJukeboxBlockEntity;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.JukeboxSong;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Registry for the audio-visual side of the mod: the Null-Iron Jukebox and the sound events its
 * discs play.
 *
 * <p>Kept apart from {@link ModBlocks} deliberately. The jukebox arrived with the effects work
 * rather than with the original block matrix, it needs a block, a block item, a block entity type
 * and three sound events registered together, and none of those belong in a class whose javadoc
 * promises "the twelve headline blocks".
 *
 * <p>The three {@link JukeboxSong} keys below are <em>not</em> registered here. Jukebox songs are a
 * datapack registry in 26.2 - the entries live in {@code data/echoing_void/jukebox_song/}, and Java
 * only ever names them. {@code ModItems} attaches one to each disc with
 * {@code Item.Properties#jukeboxPlayable}, which resolves the key at component-binding time.
 */
public final class ModEffects {
    private ModEffects() {}

    public static final DeferredRegister<Block> BLOCKS =
            DeferredRegister.create(ForgeRegistries.BLOCKS, EchoingVoid.MODID);

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, EchoingVoid.MODID);

    public static final DeferredRegister<BlockEntityType<?>> BLOCK_ENTITIES =
            DeferredRegister.create(ForgeRegistries.BLOCK_ENTITY_TYPES, EchoingVoid.MODID);

    public static final DeferredRegister<SoundEvent> SOUNDS =
            DeferredRegister.create(ForgeRegistries.SOUND_EVENTS, EchoingVoid.MODID);

    /** Items registered here, for {@code ModCreativeTabs} to walk alongside the other registries. */
    private static final List<RegistryObject<Item>> TAB_ORDER = new ArrayList<>();

    // ------------------------------------------------------------- jukebox

    /**
     * Hardness 4.0 / Blast 6.0 | METAL | Light 3 | plays any music disc.
     *
     * <p>Deliberately without {@code requiresCorrectToolForDrops}: vanilla's jukebox, note block and
     * furniture blocks all come back to a bare hand, and gating this one on a tool would make its
     * drop depend on a tag file in a generator this registry does not own. A pickaxe entry in
     * {@code mineable/pickaxe} is still worth having for the mining speed, but nothing breaks
     * without it.
     */
    public static final RegistryObject<Block> NULL_IRON_JUKEBOX = BLOCKS.register("null_iron_jukebox",
            () -> new NullIronJukeboxBlock(BlockBehaviour.Properties.of()
                    .setId(BLOCKS.key("null_iron_jukebox"))
                    .mapColor(MapColor.COLOR_BLACK)
                    .strength(4.0F, 6.0F)
                    .sound(SoundType.METAL)
                    .lightLevel(state -> 3)));

    public static final RegistryObject<Item> NULL_IRON_JUKEBOX_ITEM = track(ITEMS.register("null_iron_jukebox",
            () -> new BlockItem(NULL_IRON_JUKEBOX.get(),
                    new Item.Properties().setId(ITEMS.key("null_iron_jukebox")))));

    public static final RegistryObject<BlockEntityType<NullIronJukeboxBlockEntity>> NULL_IRON_JUKEBOX_ENTITY =
            BLOCK_ENTITIES.register("null_iron_jukebox",
                    () -> new BlockEntityType<>(NullIronJukeboxBlockEntity::new,
                            Set.of(NULL_IRON_JUKEBOX.get())));

    // --------------------------------------------------------- disc audio

    /**
     * One sound event per disc.
     *
     * <p>A jukebox song entry names a sound event, and a sound event is only a name until
     * {@code assets/echoing_void/sounds.json} maps it to an .ogg file. Ours currently point at
     * vanilla record files so the discs are audible from the first launch; swapping in composed
     * tracks is a change to sounds.json alone and touches no code.
     */
    public static final RegistryObject<SoundEvent> MUSIC_DISC_HARMONIC_ALPHA = sound("music_disc.harmonic_alpha");
    public static final RegistryObject<SoundEvent> MUSIC_DISC_HARMONIC_BETA = sound("music_disc.harmonic_beta");
    public static final RegistryObject<SoundEvent> MUSIC_DISC_HARMONIC_GAMMA = sound("music_disc.harmonic_gamma");

    // ---------------------------------------------------------- song keys

    /** Attach to {@code harmonic_tuning_disc_alpha} with {@code Item.Properties#jukeboxPlayable}. */
    public static final ResourceKey<JukeboxSong> SONG_HARMONIC_ALPHA = song("harmonic_alpha");
    public static final ResourceKey<JukeboxSong> SONG_HARMONIC_BETA = song("harmonic_beta");
    public static final ResourceKey<JukeboxSong> SONG_HARMONIC_GAMMA = song("harmonic_gamma");

    // ------------------------------------------------------------ helpers

    /**
     * Music is streamed rather than played as a point sound, so range is left variable - a fixed
     * range would cut the track off at a hard radius instead of fading it.
     */
    private static RegistryObject<SoundEvent> sound(String path) {
        return SOUNDS.register(path, () -> SoundEvent.createVariableRangeEvent(EchoingVoid.id(path)));
    }

    private static ResourceKey<JukeboxSong> song(String path) {
        return ResourceKey.create(Registries.JUKEBOX_SONG, EchoingVoid.id(path));
    }

    private static RegistryObject<Item> track(RegistryObject<Item> item) {
        TAB_ORDER.add(item);
        return item;
    }

    public static List<RegistryObject<Item>> tabOrder() {
        return TAB_ORDER;
    }

    public static void register(BusGroup modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
        BLOCK_ENTITIES.register(modBus);
        SOUNDS.register(modBus);
    }
}

package com.echoingvoid.worldgen;

import com.echoingvoid.EchoingVoid;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureProcessor;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureProcessorType;
import net.minecraftforge.eventbus.api.bus.BusGroup;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

/**
 * Structure processors this mod adds.
 *
 * <p>The registry is {@code worldgen/structure_processor}, and what it actually holds is the
 * {@link MapCodec} for each processor type rather than the processor itself - a processor instance
 * is created per use, from the JSON in a template pool's processor list.
 */
public final class ModProcessors {
    private ModProcessors() {}

    public static final DeferredRegister<MapCodec<? extends StructureProcessor>> PROCESSORS =
            DeferredRegister.create(Registries.STRUCTURE_PROCESSOR, EchoingVoid.MODID);

    /** Grows legs down from a piece's lowest blocks until they reach solid ground. */
    public static final RegistryObject<MapCodec<? extends StructureProcessor>> GROUND_SUPPORT =
            PROCESSORS.register("ground_support", () -> GroundSupportProcessor.MAP_CODEC);

    public static void register(BusGroup modBus) {
        PROCESSORS.register(modBus);
    }
}

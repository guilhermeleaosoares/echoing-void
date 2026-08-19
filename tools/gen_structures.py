"""
The Echoing Void - jigsaw structure templates (.nbt) and their template pools.

Two structures are emitted:

  outpost_of_the_tuners   a walled terrace with a gabled forge hall, reached by
                          bridges that land in framed gate arches, plus an
                          observatory, a strongroom, a signal tower and a lodge
  tuner_encampment        a cheap scattered camp for the Shattered Octaves

Craft rules, measured off vanilla templates with tools/ev_nbt.py rather than
guessed at:

  * A jigsaw block sits in the MIDDLE of a 3 wide x 3 tall opening on the piece's
    outer face, final_state air - trial_chambers/corridor/entrance_1.nbt places
    its connector at [9,4,18] with the floor at y=2 and air at y=3..5. Two
    connected jigsaw blocks end up adjacent and facing each other
    (JigsawBlock.canAttach: source.front == target.front.opposite and
    source.target == target.name), so a connector in an archway guarantees the
    bridge lands in a doorway and never against a wall.
  * Roofs step in by one block per level, an outward-facing stair row over a
    solid row - village/plains/houses/plains_medium_house_1.nbt for a gable,
    plains_small_house_1.nbt for a hip. Corners of a hip ring use shape
    outer_left; the four facings are south/west/east/north clockwise from NW.
  * Pools use minecraft:single_pool_element, NOT legacy. LegacySinglePoolElement
    swaps BlockIgnoreProcessor.STRUCTURE_BLOCK for STRUCTURE_AND_AIR, which
    means every air block in the template is skipped - the piece never carves
    its own interior and any terrain it lands in stays put. That is exactly the
    "bridges lead to walls that need to be broken" bug. Air must be placed.
  * Nothing floats. verify() walks the 6-connected block graph of every emitted
    template and reports isolated blocks and disconnected clusters.

DataVersion 4903 is Minecraft 26.2, read back out of the vanilla templates in
the client jar.

Run:  python tools/gen_structures.py
"""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import ev_nbt as nbt  # noqa: E402

NS = "echoing_void"
DATA_VERSION = 4903
ROOT = TOOLS.parent
DATA = ROOT / "src" / "main" / "resources" / "data" / NS
STRUCT_DIR = DATA / "structure"
POOL_DIR = DATA / "worldgen" / "template_pool"

OUTPOST = "outpost_of_the_tuners"
ENCAMP = "tuner_encampment"

# ---------------------------------------------------------------- block ids
# Only ids that are registered, or that ModBlockFamilies guarantees:
# <base>_slab/_stairs/_wall for the seven stone bases and
# <wood>_planks/_slab/_stairs/_fence/_fence_gate/_door/_trapdoor for four woods.
# Cut-variant ids go through variant() rather than string concatenation, because
# the brick bases singularise on the way.

AIR = "minecraft:air"
VOID = "minecraft:structure_void"

RAW = f"{NS}:raw_phonolite"
POLISHED = f"{NS}:polished_phonolite"
BRICKS = f"{NS}:phonolite_bricks"
RESONANT_CHALK = f"{NS}:resonant_chalk"
CHALK_BRICK = f"{NS}:chalk_bricks"
SLATE = f"{NS}:echo_slate"
AMBER = f"{NS}:amber_strata"

GLASS = f"{NS}:void_glass"
NULL_IRON = f"{NS}:null_iron_block"
LANTERN = f"{NS}:harmonic_lantern"
CRYSTAL = f"{NS}:humming_crystal"
MOSS = f"{NS}:resonance_moss"

FARMLAND = f"{NS}:void_farmland"
HUSHWATER = f"{NS}:hushwater"
WHEAT = f"{NS}:resonant_wheat"
CHIME_ROOTS = f"{NS}:chime_roots"
VOID_TUBERS = f"{NS}:void_tubers"
GOURD = f"{NS}:echo_gourd"
GOURD_STEM = f"{NS}:echo_gourd_stem"
COMPOSTER = "minecraft:composter"

SIPHON = f"{NS}:frequency_siphon"
ANVIL = f"{NS}:inversion_anvil"
LOCKBOX = f"{NS}:acoustic_lock_box"

TUNING = "petrified_tuning"   # dark wood - decks, rails, bars
BOUGH = "amber_bough"         # warm wood - doors, furniture
ASH = "echo_ash"              # pale wood - camp frames

LOG = f"{NS}:petrified_tuning_wood"
STRIPPED_LOG = f"{NS}:stripped_petrified_tuning_wood"

CHAIN = "minecraft:chain"
HANGING = "minecraft:soul_lantern"
CAMPFIRE = "minecraft:soul_campfire"
BARREL = "minecraft:barrel"
CRAFTING = "minecraft:crafting_table"
SMITHING = "minecraft:smithing_table"
LECTERN = "minecraft:lectern"
CANVAS = "minecraft:light_gray_wool"
CANVAS_TRIM = "minecraft:cyan_wool"

LOOT_FORGE = f"{NS}:chests/resonance_forge"
LOOT_DOME = f"{NS}:chests/observatory_dome"
LOOT_VAULT = f"{NS}:chests/sound_vault"

STONES = (RAW, POLISHED, BRICKS, RESONANT_CHALK, CHALK_BRICK, SLATE, AMBER)
WOODS = (TUNING, BOUGH, ASH)


def variant(mat: str, suffix: str) -> str:
    """Full id of a cut variant, from a base block id or a bare family prefix.

    Two traps live here. A bare wood name has to gain the mod namespace or the
    game reads it as minecraft:amber_bough_stairs and drops the block. And
    ModBlockFamilies singularises brick bases the way vanilla does -
    stone_bricks cuts to stone_brick_slab - so chalk_bricks gives
    chalk_brick_wall, not chalk_bricks_wall.
    """
    prefix = mat if ":" in mat else f"{NS}:{mat}"
    if prefix.endswith("_bricks"):
        prefix = prefix[:-1]
    return f"{prefix}_{suffix}"


# Full cubes, for working out which faces a fence or a wall connects to.
FULL_CUBE = set(STONES) | {
    GLASS, NULL_IRON, LANTERN, CRYSTAL, MOSS, LOG, STRIPPED_LOG,
    CANVAS, CANVAS_TRIM, CRAFTING, SMITHING, BARREL,
    SIPHON, ANVIL, LOCKBOX,
} | {f"{NS}:{w}_planks" for w in WOODS}

# ------------------------------------------------------------- connector names
# One piece's `name` must equal the other piece's `target`.
GATE = f"{NS}:outpost_gate"        # on the outpost side of a span
BRIDGE_IN = f"{NS}:bridge_start"   # the end of a bridge that meets a gate
BRIDGE_OUT = f"{NS}:bridge_end"    # the far end of a bridge
DOOR_IN = f"{NS}:building_gate"    # a building's one entrance
CAMP_LINK = f"{NS}:camp_link"
CAMP_TENT = f"{NS}:camp_tent"
PROP_ON = f"{NS}:outpost_prop"

POOL_EMPTY = "minecraft:empty"
P_BRIDGES = f"{NS}:{OUTPOST}/bridges"
P_BUILDINGS = f"{NS}:{OUTPOST}/buildings"
P_TERMINATORS = f"{NS}:{OUTPOST}/terminators"
P_GATE_CAPS = f"{NS}:{OUTPOST}/gate_caps"
P_PROPS = f"{NS}:{OUTPOST}/props"
P_TENTS = f"{NS}:{ENCAMP}/tents"


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------

class Template:
    """A structure template grid that serialises to a vanilla .nbt file.

    Every position in the volume is written, air included, so that a piece
    placed with minecraft:single_pool_element carves out its own interior.
    Pieces that must not disturb what they land on (the loose props) fill
    themselves with structure_void instead, which the placer always skips.
    """

    def __init__(self, sx: int, sy: int, sz: int, background: str = AIR):
        self.size = (sx, sy, sz)
        self._palette: list[tuple[str, tuple[tuple[str, str], ...]]] = []
        self._index: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._blocks: dict[tuple[int, int, int], tuple[int, dict | None]] = {}
        self._deferred: dict[tuple[int, int, int], tuple[str, str]] = {}
        self._entities: list[tuple[tuple[int, int, int], str, dict]] = []
        bg = self.state(background)
        for x in range(sx):
            for y in range(sy):
                for z in range(sz):
                    self._blocks[(x, y, z)] = (bg, None)

    # -- primitives ---------------------------------------------------------

    def state(self, name: str, props: dict[str, str] | None = None) -> int:
        key = (name, tuple(sorted((props or {}).items())))
        if key not in self._index:
            self._index[key] = len(self._palette)
            self._palette.append(key)
        return self._index[key]

    def inside(self, x: int, y: int, z: int) -> bool:
        sx, sy, sz = self.size
        return 0 <= x < sx and 0 <= y < sy and 0 <= z < sz

    def set(self, x: int, y: int, z: int, name: str,
            props: dict[str, str] | None = None, block_nbt: dict | None = None) -> None:
        if not self.inside(x, y, z):
            raise IndexError(f"({x},{y},{z}) outside {self.size}")
        self._deferred.pop((x, y, z), None)
        self._blocks[(x, y, z)] = (self.state(name, props), block_nbt)

    def get(self, x: int, y: int, z: int) -> str:
        """Block name at a position, or air for anything outside the volume."""
        if not self.inside(x, y, z):
            return AIR
        return self._palette[self._blocks[(x, y, z)][0]][0]

    def fill(self, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int,
             name: str, props: dict[str, str] | None = None) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name, props)

    def ring(self, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int,
             name: str, props: dict[str, str] | None = None) -> None:
        """The four vertical wall planes of a box, floor and ceiling left open."""
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    self.fill(x, y0, z, x, y1, z, name, props)

    # -- shaped blocks ------------------------------------------------------

    def stairs(self, x: int, y: int, z: int, mat: str, facing: str,
               half: str = "bottom", shape: str = "straight") -> None:
        self.set(x, y, z, variant(mat, "stairs"),
                 {"facing": facing, "half": half, "shape": shape, "waterlogged": "false"})

    def slab(self, x: int, y: int, z: int, mat: str, kind: str = "bottom") -> None:
        self.set(x, y, z, variant(mat, "slab"), {"type": kind, "waterlogged": "false"})

    def wall(self, x: int, y: int, z: int, mat: str) -> None:
        """A stone wall. Its side connections are resolved in finish()."""
        name = variant(mat, "wall")
        self.set(x, y, z, name)
        self._deferred[(x, y, z)] = ("wall", name)

    def fence(self, x: int, y: int, z: int, wood: str) -> None:
        """A wood fence. Its side connections are resolved in finish()."""
        name = variant(wood, "fence")
        self.set(x, y, z, name)
        self._deferred[(x, y, z)] = ("fence", name)

    def gate(self, x: int, y: int, z: int, wood: str, facing: str,
             in_wall: str = "false") -> None:
        self.set(x, y, z, variant(wood, "fence_gate"),
                 {"facing": facing, "open": "true", "powered": "false", "in_wall": in_wall})

    def trapdoor(self, x: int, y: int, z: int, wood: str, facing: str,
                 half: str = "top", open_: str = "false") -> None:
        self.set(x, y, z, variant(wood, "trapdoor"),
                 {"facing": facing, "half": half, "open": open_,
                  "powered": "false", "waterlogged": "false"})

    def door(self, x: int, y: int, z: int, wood: str, facing: str,
             hinge: str = "left") -> None:
        for half, dy in (("lower", 0), ("upper", 1)):
            self.set(x, y + dy, z, variant(wood, "door"),
                     {"facing": facing, "half": half, "hinge": hinge,
                      "open": "false", "powered": "false"})

    def chain(self, x: int, y: int, z: int, axis: str = "y") -> None:
        self.set(x, y, z, CHAIN, {"axis": axis, "waterlogged": "false"})

    def hang(self, x: int, ceiling_y: int, z: int, drop: int = 1) -> None:
        """Chain down from the block under `ceiling_y`, lantern on the end.

        The complaint was floating lanterns, so a lamp is only ever placed with
        a chain above it and something solid above that.
        """
        for i in range(drop):
            self.chain(x, ceiling_y - 1 - i, z)
        self.set(x, ceiling_y - 1 - drop, z, HANGING,
                 {"hanging": "true", "waterlogged": "false"})

    def campfire(self, x: int, y: int, z: int, facing: str = "north") -> None:
        self.set(x, y, z, CAMPFIRE,
                 {"facing": facing, "lit": "true", "signal_fire": "false",
                  "waterlogged": "false"})

    def chest(self, x: int, y: int, z: int, facing: str, loot: str) -> None:
        self.set(x, y, z, "minecraft:chest",
                 {"facing": facing, "type": "single", "waterlogged": "false"},
                 {"id": "minecraft:chest", "LootTable": loot})

    def barrel(self, x: int, y: int, z: int, facing: str, loot: str | None = None) -> None:
        self.set(x, y, z, BARREL, {"facing": facing, "open": "false"},
                 {"id": "minecraft:barrel", "LootTable": loot} if loot else None)

    def jigsaw(self, x: int, y: int, z: int, orientation: str, name: str,
               target: str, pool: str, final_state: str = AIR,
               joint: str = "aligned") -> None:
        self.set(x, y, z, "minecraft:jigsaw", {"orientation": orientation}, {
            "id": "minecraft:jigsaw",
            "name": name,
            "target": target,
            "pool": pool,
            "final_state": final_state,
            "joint": joint,
        })

    # -- composite --------------------------------------------------------

    def archway(self, x: int, y: int, z: int, facing: str, jamb: str, band: str,
                name: str, target: str, pool: str, lamps: bool = True) -> None:
        """A framed 3x3 gateway on an outer face, with the connector in the hole.

        (x, y, z) is the connector cell: the middle of the opening, two above the
        floor it stands on. The opening runs one block either side of it and one
        below to one above. Jambs flank it, a lintel caps it, and above that sits
        the lamp head: two piers off the ends of the lintel, a beam across them,
        and a soul lantern chained to that beam either side of the centre line.
        """
        du, dv = (1, 0) if facing in ("north", "south") else (0, 1)

        def at(o: int, dy: int) -> tuple[int, int, int]:
            return (x + du * o, y + dy, z + dv * o)

        for o in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.set(*at(o, dy), AIR)
        for o in (-2, 2):
            for dy in range(-1, 3):
                self.set(*at(o, dy), jamb)
        for o in range(-2, 3):
            self.set(*at(o, 2), band)
        if lamps:
            for o in (-2, 2):
                self.wall(*at(o, 3), band)
                self.set(*at(o, 4), LANTERN)

            # PLAYER: "soul lanterns are still floating, we need to connect those
            # with a chain to the archways."
            #
            # What the gate used to be, read straight off a voxel dump of all
            # thirteen archways rather than off the code: at the three middle
            # columns, dy=3 and dy=4 were AIR in seven of the eight pieces. So
            # each gate carried two glowing cubes on one-block stalks with open
            # sky above them and beside them, which is what reads as a floating
            # lamp from any distance at all.
            #
            # Now the two stalks become piers - each cube gains a beam directly
            # on top of it and keeps its post underneath - the beam spans the
            # gate, and a soul lantern hangs from it on a chain on each side of
            # the connector. Every lamp on the gate is held by a full block and
            # both hanging ones are chained to the arch, which is the ask.
            #
            # The observatory is the eighth piece. Its gates are cut into the
            # drum wall, so those columns are already masonry and its lamps are
            # already bedded in it; the guard skips the whole head there rather
            # than punching a chain shaft through the wall.
            head = [at(o, dy) for o in (-1, 0, 1) for dy in (3, 4)]
            head += [at(o, 5) for o in (-2, -1, 0, 1, 2)]
            if all(self.inside(*c) and self.get(*c) == AIR for c in head):
                for o in range(-2, 3):
                    self.set(*at(o, 5), band)
                for o in (-1, 1):
                    self.chain(*at(o, 4))
                    self.set(*at(o, 3), HANGING,
                             {"hanging": "true", "waterlogged": "false"})
        self.jigsaw(x, y, z, f"{facing}_up", name, target, pool, AIR)

    def window(self, x: int, y: int, z: int, facing: str, frame: str,
               height: int = 2, hood: bool = False) -> None:
        """A void-glass light with a stone sill, head and jambs.

        `facing` is the direction the wall looks out in; the glass runs along the
        perpendicular axis. `hood` adds a trapdoor awning outside the head.
        """
        du, dv = (1, 0) if facing in ("north", "south") else (0, 1)
        nx, nz = (0, -1) if facing == "north" else (0, 1) if facing == "south" \
            else (-1, 0) if facing == "west" else (1, 0)
        for dy in range(height):
            self.set(x, y + dy, z, GLASS)
        self.set(x, y - 1, z, frame)
        self.set(x, y + height, z, frame)
        for o in (-1, 1):
            for dy in range(-1, height + 1):
                px, pz = x + du * o, z + dv * o
                if self.inside(px, y + dy, pz):
                    self.set(px, y + dy, pz, frame)
        if hood and self.inside(x + nx, y + height, z + nz):
            self.trapdoor(x + nx, y + height, z + nz, BOUGH,
                          {"north": "south", "south": "north",
                           "east": "west", "west": "east"}[facing], "top", "false")

    def gable_roof(self, x0: int, x1: int, z0: int, z1: int, y: int,
                   stair_mat: str, solid_mat: str, ridge_mat: str | None = None) -> int:
        """Pitched roof, ridge running along X. Returns the ridge height.

        Each level is an outward-facing stair row over a solid row, stepping in
        one block per level, which is how vanilla builds every village gable.
        """
        i = 0
        while z0 + i < z1 - i:
            level = y + i
            for x in range(x0, x1 + 1):
                self.stairs(x, level, z0 + i, stair_mat, "south")
                self.stairs(x, level, z1 - i, stair_mat, "north")
                if z0 + i + 1 <= z1 - i - 1:
                    self.set(x, level, z0 + i + 1, solid_mat)
                    self.set(x, level, z1 - i - 1, solid_mat)
            i += 1
        ridge = y + i
        if z0 + i == z1 - i:
            for x in range(x0, x1 + 1):
                self.set(x, ridge, z0 + i, ridge_mat or solid_mat)
        return ridge

    def hip_roof(self, x0: int, x1: int, z0: int, z1: int, y: int,
                 stair_mat: str, solid_mat: str) -> int:
        """Pyramidal roof over a rectangular footprint. Returns the apex height.

        Corner cells take shape=outer_left; the four facings clockwise from the
        north-west corner are south, west, north, east, which is exactly what
        plains_small_house_1.nbt stores.
        """
        i = 0
        while True:
            ax0, ax1, az0, az1 = x0 + i, x1 - i, z0 + i, z1 - i
            if ax0 > ax1 or az0 > az1:
                return y + i - 1
            level = y + i
            if ax0 == ax1 and az0 == az1:
                self.set(ax0, level, az0, solid_mat)
                return level
            for x in range(ax0, ax1 + 1):
                for z in range(az0, az1 + 1):
                    on_x, on_z = x in (ax0, ax1), z in (az0, az1)
                    if on_x and on_z:
                        facing = {(True, True): "south", (False, True): "west",
                                  (True, False): "east", (False, False): "north"}[
                            (x == ax0, z == az0)]
                        self.stairs(x, level, z, stair_mat, facing, shape="outer_left")
                    elif on_z:
                        self.stairs(x, level, z, stair_mat,
                                    "south" if z == az0 else "north")
                    elif on_x:
                        self.stairs(x, level, z, stair_mat,
                                    "east" if x == ax0 else "west")
                    else:
                        self.set(x, level, z, solid_mat)
            i += 1

    # -- finishing ---------------------------------------------------------

    def _connects(self, name: str, kind: str, facing: str) -> bool:
        if name in FULL_CUBE:
            return True
        if kind == "fence":
            return name.endswith("_fence") or name.endswith("_fence_gate")
        return name.endswith("_wall")

    def finish(self) -> None:
        """Resolve fence and wall side connections.

        SinglePoolElement sets knownShape, so StructureTemplate skips its
        neighbour-shape pass entirely: whatever connection state is written here
        is what the player sees. Vanilla templates store them explicitly too.
        """
        sides = {"north": (0, 0, -1), "south": (0, 0, 1),
                 "west": (-1, 0, 0), "east": (1, 0, 0)}
        for (x, y, z), (kind, name) in list(self._deferred.items()):
            props: dict[str, str] = {"waterlogged": "false"}
            linked = []
            for side, (dx, dy, dz) in sides.items():
                hit = self._connects(self.get(x + dx, y + dy, z + dz), kind, side)
                if hit:
                    linked.append(side)
                props[side] = ("low" if kind == "wall" else "true") if hit else \
                              ("none" if kind == "wall" else "false")
            if kind == "wall":
                above = self.get(x, y + 1, z) not in (AIR, VOID)
                straight = set(linked) in ({"north", "south"}, {"east", "west"})
                props["up"] = "true" if (above or not straight) else "false"
            self._blocks[(x, y, z)] = (self.state(name, props), None)
        self._deferred.clear()

    def entity(self, x: int, y: int, z: int, entity_id: str, **data) -> None:
        """Place a live entity in this piece, the way vanilla village templates
        carry their villagers and their cats.

        This exists because spawn_overrides alone is not enough for a
        settlement. MobCategory.CREATURE is only offered a spawn when
        gameTime % 400 == 0 (ServerChunkCache.tickChunks), only in chunks near
        a player, and only while the global creature cap has room - so a player
        walking into a freshly generated outpost would routinely find it
        deserted, and might never see it fill. Writing the inhabitants into the
        template makes the settlement populated the moment it generates, and
        leaves spawn_overrides to do what it is actually good at: replacing
        them over time.

        PersistenceRequired is set for the same reason vanilla sets it on its
        template cats - a villager that despawns is a settlement that empties.
        No UUID is written: vanilla templates carry one only because they were
        saved from a live world, and copying a fixed UUID into every generated
        copy would mean every outpost's trader shared an identity.
        """
        self._entities.append(((x, y, z), entity_id, data))

    # -- serialisation -----------------------------------------------------

    def to_nbt(self) -> nbt.Compound:
        self.finish()
        palette = nbt.List([
            nbt.Compound(
                {"Name": name} if not props else
                {"Name": name, "Properties": nbt.Compound(dict(props))}
            )
            for name, props in self._palette
        ], element_id=nbt.TAG_COMPOUND)

        # PLAYER: "make sure that the structure void blocks do not remain after
        # generation, as they currently generate."
        #
        # They were being written into the NBT on the belief that the placer
        # skips them. It does not: BlockIgnoreProcessor ships presets for
        # STRUCTURE_BLOCK, AIR and STRUCTURE_AND_AIR and none for STRUCTURE_VOID,
        # and StructureTemplate never names it - so a structure_void in the block
        # list is placed as a real, solid, invisible block.
        #
        # Vanilla's answer is not a processor, it is to never store them: 60 of
        # 60 village templates checked have no structure_void in their palette,
        # because fillFromWorld drops the ignored block at save time. A position
        # absent from the list is simply left alone by the placer, which is
        # exactly the "don't touch this cell" semantics we wanted. So drop them
        # here, at the one place that writes the file.
        void_index = self._index.get((VOID, ()))
        blocks = []
        for (x, y, z), (state, block_nbt) in sorted(self._blocks.items()):
            if void_index is not None and state == void_index:
                continue
            entry: dict = {
                "pos": nbt.List([nbt.Int(x), nbt.Int(y), nbt.Int(z)], element_id=nbt.TAG_INT),
                "state": nbt.Int(state),
            }
            if block_nbt:
                entry["nbt"] = nbt.Compound(block_nbt)
            blocks.append(nbt.Compound(entry))

        entities = []
        for (ex, ey, ez), entity_id, data in self._entities:
            body: dict = {"id": nbt.String(entity_id), "PersistenceRequired": nbt.Byte(1)}
            body.update(data)
            entities.append(nbt.Compound({
                # Centred in the block, and standing on its floor, so the mob
                # does not spawn clipped into the wall behind it.
                "pos": nbt.List([nbt.Double(ex + 0.5), nbt.Double(ey), nbt.Double(ez + 0.5)],
                                element_id=nbt.TAG_DOUBLE),
                "blockPos": nbt.List([nbt.Int(ex), nbt.Int(ey), nbt.Int(ez)],
                                     element_id=nbt.TAG_INT),
                "nbt": nbt.Compound(body),
            }))

        return nbt.Compound({
            "DataVersion": nbt.Int(DATA_VERSION),
            "size": nbt.List([nbt.Int(v) for v in self.size], element_id=nbt.TAG_INT),
            "palette": palette,
            "blocks": nbt.List(blocks, element_id=nbt.TAG_COMPOUND),
            "entities": nbt.List(entities, element_id=nbt.TAG_COMPOUND),
        })


# ---------------------------------------------------------------------------
# shape helpers
# ---------------------------------------------------------------------------

def octagon(cx: int, cz: int, r: int) -> set[tuple[int, int]]:
    """A filled octagon: a square with its corners cut back on the diagonal."""
    diag = r + max(1, r // 2)
    return {(cx + dx, cz + dz)
            for dx in range(-r, r + 1) for dz in range(-r, r + 1)
            if abs(dx) + abs(dz) <= diag}


def oct_ring(cx: int, cz: int, r: int) -> set[tuple[int, int]]:
    """The one-cell-thick edge of octagon(r).

    Because ring(r) is exactly octagon(r) minus octagon(r-1), the cells of
    ring(r+1) sit directly under the cells of ring(r) at the level below - which
    is what lets the observatory dome step outward without floating.
    """
    return octagon(cx, cz, r) - (octagon(cx, cz, r - 1) if r > 0 else set())


def rim(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Cells of a footprint that have at least one orthogonal neighbour outside."""
    return {(x, z) for (x, z) in cells
            if any((x + dx, z + dz) not in cells
                   for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


# ---------------------------------------------------------------------------
# outpost pieces
# ---------------------------------------------------------------------------

def forge_hall() -> Template:
    """Start piece: an octagonal walled terrace carrying the gabled forge hall.

    Four gate arches on the terrace rim are where bridges attach, so a span
    always ends in a doorway on a walkable deck rather than against masonry. The
    hall itself is entered through a stone archway on one side and a wooden door
    on the other, and is open to the underside of its roof.
    """
    t = Template(17, 15, 17)
    deck = octagon(8, 8, 8)
    edge = rim(deck)

    for (x, z) in deck:
        t.set(x, 0, z, RAW)
        far = max(abs(x - 8), abs(z - 8))
        if far == 8:
            floor = RESONANT_CHALK                          # unworked kerb at the very edge
        elif far == 7:
            floor = CHALK_BRICK
        elif abs(x - 8) == abs(z - 8):
            floor = AMBER                          # the diagonal inlay
        else:
            floor = POLISHED
        # A fixed hash rather than a random: the same weathering every seed.
        if far >= 5 and (x * 7 + z * 13) % 11 == 0:
            floor = MOSS
        t.set(x, 1, z, floor)

    # parapet, with a taller post at each of the eight octagon vertices
    for (x, z) in edge:
        t.wall(x, 2, z, CHALK_BRICK)
    for (x, z) in ((4, 0), (12, 0), (16, 4), (16, 12), (12, 16), (4, 16), (0, 12), (0, 4)):
        t.fill(x, 2, z, x, 3, z, POLISHED)
        t.set(x, 4, z, LANTERN)

    # ---- the hall: walls x 4..12, z 5..11, standing on the deck
    t.ring(4, 2, 5, 12, 6, 11, CHALK_BRICK)
    t.ring(4, 2, 5, 12, 2, 11, POLISHED)          # plinth course
    t.ring(4, 7, 5, 12, 7, 11, POLISHED)          # cornice course
    for (cx, cz) in ((4, 5), (12, 5), (4, 11), (12, 11)):
        t.fill(cx, 2, cz, cx, 7, cz, POLISHED)    # corner pilasters
    t.fill(5, 1, 6, 11, 1, 10, POLISHED)          # interior floor

    # north archway into the hall, south door out of it
    t.fill(7, 2, 5, 9, 4, 5, AIR)
    t.fill(6, 2, 5, 6, 5, 5, POLISHED)
    t.fill(10, 2, 5, 10, 5, 5, POLISHED)
    t.fill(7, 5, 5, 9, 5, 5, POLISHED)
    t.fill(8, 2, 11, 8, 3, 11, AIR)
    t.door(8, 2, 11, BOUGH, "south")
    t.fill(7, 2, 11, 7, 4, 11, POLISHED)
    t.fill(9, 2, 11, 9, 4, 11, POLISHED)
    t.fill(8, 4, 11, 8, 4, 11, POLISHED)

    # windows: two per long wall, two on the east gable wall
    t.window(5, 4, 5, "north", POLISHED, hood=True)
    t.window(11, 4, 5, "north", POLISHED, hood=True)
    t.window(6, 4, 11, "south", POLISHED, hood=True)
    t.window(10, 4, 11, "south", POLISHED, hood=True)
    t.window(12, 4, 7, "east", POLISHED, hood=True)
    t.window(12, 4, 9, "east", POLISHED, hood=True)

    # ---- roof: gable along X, overhanging one block on every side
    ridge = t.gable_roof(3, 13, 4, 12, 8, SLATE, SLATE, POLISHED)
    for gx in (4, 12):                            # close the gable ends
        t.fill(gx, 8, 6, gx, 8, 10, CHALK_BRICK)
        t.fill(gx, 9, 7, gx, 9, 9, CHALK_BRICK)
        t.set(gx, 10, 8, CHALK_BRICK)
        t.fill(gx, 8, 7, gx, 8, 9, GLASS)         # gable light
        t.set(gx, 9, 8, GLASS)

    # Tie beam ENDS only. Both of these land on a course gable_roof() also lays
    # solid (z=5 and z=11 on its first pass), so they are part of the roof seen
    # from outside and must stay exactly where they are. The span between them
    # was under the pitch and invisible; it is the attic floor now, and the
    # hall's lamps have come down onto its underside - they used to chain up
    # through what is now that floor.
    for bx in (6, 10):
        t.set(bx, 8, 5, LOG, {"axis": "z"})
        t.set(bx, 8, 11, LOG, {"axis": "z"})

    # ---- forge hearth against the west wall, flue out through the ridge
    t.fill(4, 2, 7, 4, 5, 9, POLISHED)
    t.fill(5, 1, 7, 5, 1, 9, AMBER)
    t.campfire(5, 2, 8, "east")
    for hz in (7, 8, 9):
        t.stairs(5, 4, hz, POLISHED, "east", half="top")
    t.fill(5, 5, 8, 5, 12, 8, POLISHED)
    t.wall(5, 13, 8, POLISHED)
    # PLAYER, ruling directly on this one: the chimney cap "caps the flue and
    # belongs in the lower position". It was listed as deliberately top-half.
    t.slab(5, 14, 8, POLISHED, "bottom")

    # ---- interior: a forge below, quarters in the roof
    _forge_ground(t)
    _forge_attic(t)
    for (lx, lz) in ((4, 6), (4, 10), (12, 6), (12, 10)):
        t.set(lx, 4, lz, LANTERN)                 # lamps recessed into the wall

    # ---- four gates on the rim, then loose props on the open deck
    t.archway(8, 3, 0, "north", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    t.archway(8, 3, 16, "south", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    t.archway(0, 3, 8, "west", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    t.archway(16, 3, 8, "east", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    for (px, pz) in ((4, 4), (12, 4), (4, 12), (12, 12)):
        t.jigsaw(px, 1, pz, "up_north", PROP_ON, PROP_ON, P_PROPS, POLISHED, "rollable")

    # ---- the people who live here
    #
    # Written into the template rather than left to spawn_overrides alone.
    # MobCategory.CREATURE is offered a spawn only when gameTime % 400 == 0,
    # only near a player, and only under the global creature cap, so relying on
    # it meant a freshly generated outpost was usually deserted when the player
    # first walked in. Vanilla has the same problem and solves it the same way -
    # its village templates carry their villagers. spawn_overrides stays, and
    # now does the job it is good at: replacing losses over time.
    #
    # Every coordinate here was checked against the finished piece for solid
    # ground below and clear headroom above, rather than eyeballed off the
    # layout: (5,3,6) and (11,3,6) are the hall floor, (8,2,12) the south deck.
    # Variety is written here rather than worked out at spawn time. TraderMob
    # used to derive it by asking the StructureManager which structure it was
    # standing in - which is fine on the NaturalSpawner path it was written for,
    # but SinglePoolElement sets finalizeEntities(true), so finalizeSpawn now
    # also runs inside chunk generation on the worldgen thread, where that
    # lookup becomes a synchronous cross-thread chunk request from inside
    # ChunkStatus.FEATURES. Stating the variety in the template removes the
    # need for the lookup entirely on this path.
    t.entity(5, 3, 6, f"{NS}:tuner_trader", Variety=nbt.String("OUTPOST"))
    t.entity(11, 3, 6, f"{NS}:tuner_trader", Variety=nbt.String("OUTPOST"))
    # The guardian stands out on the deck where it can see the gates - and it
    # is the reason the outpost gets one and the encampment does not.
    t.entity(8, 2, 12, f"{NS}:tuners_protector")
    return t


def bridge_span() -> Template:
    """A level timber span with chained lamp gantries at the quarter points."""
    t = Template(5, 8, 13)
    for z in range(13):
        t.fill(1, 1, z, 3, 1, z, f"{NS}:{TUNING}_planks")
        t.set(2, 1, z, STRIPPED_LOG, {"axis": "z"})   # worn centre timber
        for kx in (0, 4):
            # top: kerb, standing half a block proud of the deck (ruled)
            t.slab(kx, 1, z, POLISHED, "top")
        t.set(2, 0, z, LOG, {"axis": "z"})        # main beam under the deck
    for z in range(13):
        for rx in (0, 4):
            t.fence(rx, 2, z, TUNING)
    for z in range(0, 13, 4):                     # corbels under the kerbs
        t.stairs(0, 0, z, POLISHED, "east", half="top")
        t.stairs(4, 0, z, POLISHED, "west", half="top")
    for z in (3, 9):                              # gantries
        for px in (0, 4):
            t.fill(px, 2, z, px, 6, z, POLISHED)
            t.set(px, 4, z, LANTERN)              # lamp behind a glazed panel
            t.set(px, 5, z, GLASS)
        t.fill(0, 7, z, 4, 7, z, LOG, {"axis": "x"})
        t.hang(2, 7, z, drop=1)
    t.jigsaw(2, 3, 0, "north_up", BRIDGE_IN, GATE, POOL_EMPTY)
    t.jigsaw(2, 3, 12, "south_up", BRIDGE_OUT, DOOR_IN, P_BUILDINGS)
    return t


def bridge_stair() -> Template:
    """A span that climbs four blocks, so the outpost is not all one altitude."""
    t = Template(5, 12, 11)
    deck = f"{NS}:{TUNING}_planks"

    def kerb(z: int, y: int) -> None:
        for kx in (0, 4):
            # top: kerb, standing half a block proud of the deck (ruled)
            t.slab(kx, y, z, POLISHED, "top")
            t.fence(kx, y + 1, z, TUNING)

    for z in (0, 1, 2):
        t.fill(1, 1, z, 3, 1, z, deck)
        kerb(z, 1)
    # PLAYER: "the highest block of should be stairs is replaced by solid wood
    # block which means the next structure block is generating one block too
    # high up." The flight was three steps while the docstring - and the exit
    # jigsaw - both assume a climb of four, so the last step was a plank and
    # the deck began a block early.
    for i, z in enumerate((3, 4, 5, 6)):          # the flight
        y = 2 + i
        for x in range(1, 4):
            t.stairs(x, y, z, CHALK_BRICK, "south")
            t.fill(x, 1, z, x, y - 1, z, CHALK_BRICK)
        kerb(z, y)
    for z in range(7, 11):                        # deck starts after the 4th step
        t.fill(1, 5, z, 3, 5, z, deck)
        kerb(z, 5)
    t.fill(1, 0, 8, 3, 4, 8, POLISHED)            # pier under the upper deck
    for px in (0, 4):                             # lamp posts at the top landing
        t.fill(px, 6, 7, px, 9, 7, POLISHED)
        t.set(px, 8, 7, LANTERN)
        t.set(px, 9, 7, GLASS)
    for z in (1, 9):
        t.stairs(0, 0 if z == 1 else 4, z, POLISHED, "east", half="top")
        t.stairs(4, 0 if z == 1 else 4, z, POLISHED, "west", half="top")
    t.fill(0, 10, 7, 4, 10, 7, LOG, {"axis": "x"})
    t.hang(2, 10, 7, drop=1)
    t.jigsaw(2, 3, 0, "north_up", BRIDGE_IN, GATE, POOL_EMPTY)
    t.jigsaw(2, 7, 10, "south_up", BRIDGE_OUT, DOOR_IN, P_BUILDINGS)
    return t


def observatory() -> Template:
    """An octagonal drum under a ribbed void-glass dome, with a real gallery.

    The dome steps outward one ring per level and lays a slab lip directly over
    the ring below, so every pane rests on something; the old version was a
    stack of detached glass squares.
    """
    t = Template(15, 20, 15)
    cx = cz = 7
    base = octagon(cx, cz, 7)
    wall = oct_ring(cx, cz, 7)

    for (x, z) in base:
        t.set(x, 0, z, RAW)
        t.set(x, 1, z, CHALK_BRICK if max(abs(x - cx), abs(z - cz)) >= 6 else POLISHED)
    for (x, z) in wall:
        t.fill(x, 2, z, x, 10, z, CHALK_BRICK)
        t.set(x, 2, z, POLISHED)
        t.set(x, 10, z, POLISHED)
    pilasters = {(0, 7), (14, 7), (7, 0), (7, 14),
                 (2, 2), (12, 2), (2, 12), (12, 12)}
    for (x, z) in pilasters & wall:
        t.fill(x, 2, z, x, 10, z, POLISHED)

    # lancet windows down the two flanks, and a pair flanking each gate
    for (wx, wz, face) in ((0, 6, "west"), (0, 8, "west"),
                           (14, 6, "east"), (14, 8, "east"),
                           (4, 0, "north"), (10, 0, "north"),
                           (4, 14, "south"), (10, 14, "south")):
        t.window(wx, 5, wz, face, POLISHED, height=3)

    # gallery over the southern half, reached by a flight against the east wall
    gallery = {(x, z) for (x, z) in octagon(cx, cz, 6) if z >= 9}
    for (x, z) in gallery:
        t.set(x, 6, z, POLISHED)
    for (x, z) in gallery:
        if z == 9 and x != 11:                    # gap where the stair arrives
            t.fence(x, 7, z, TUNING)
    for i in range(5):
        t.stairs(11, 2 + i, 4 + i, CHALK_BRICK, "south")
        if i:
            t.fill(11, 2, 4 + i, 11, 1 + i, 4 + i, CHALK_BRICK)
    t.set(11, 6, 9, POLISHED)
    t.fill(11, 7, 9, 11, 9, 9, AIR)

    # dome: glass ring plus a slab lip standing on the ring below
    # PLAYER: "the slabs on the observatory roof instead of spawning in the
    # lower half of the block space they are generating in the upper half."
    # These sit on the glass ring below them, so they belong in the bottom half;
    # in the top half each one left a half-block band of air under the lip.
    # The dome was the first of these to be corrected and the rest followed in
    # round 2, the chimney cap among them. What is still "top" in this file is
    # only what has to be: the workbench and table tops, the bridge kerbs, the
    # vault's shelf plates and the granary eave, each carrying a one-line reason
    # at its own call.
    #
    # ONE MEASUREMENT TO PUT IN FRONT OF THE PLAYER BEFORE THE NEXT ROUND, since
    # the ruling that the table tops stay "top" was made without it. A table here
    # is a fence post at Y with a top slab at Y+1. A fence RENDERS one block
    # tall - minecraft:block/fence_post is a box from [6,0,6] to [10,16,10], and
    # it is only the COLLISION box that is 24 high - so the post ends at Y+1.0
    # and a top slab begins at Y+1.5. Every table top in this file therefore
    # floats half a block above its own leg, which is the same thing the player
    # described in this round's complaint. A bottom slab would sit on the post.
    # The rule stands until the player rules again; this is only the number.
    y = 11
    for r in (6, 5, 4, 3, 2, 1):
        for (x, z) in oct_ring(cx, cz, r):
            t.set(x, y, z, GLASS)
        for (x, z) in oct_ring(cx, cz, r + 1):
            t.slab(x, y, z, POLISHED, "bottom")
        y += 1
    for (x, z) in oct_ring(cx, cz, 1):
        t.slab(x, y, z, POLISHED, "bottom")
    # The finial. The lamp used to be the top block, balanced on a wall post
    # with nothing over it - a cube on a spike, and the same defect as the old
    # gate lamps. It sits on the dome cap now and the post became the spire.
    t.set(cx, y, cz, POLISHED)
    t.set(cx, y + 1, cz, LANTERN)
    t.wall(cx, y + 2, cz, POLISHED)

    # instrument dais under the dome
    for (x, z) in octagon(cx, cz, 2):
        t.set(x, 2, z, BRICKS)
    for (x, z) in oct_ring(cx, cz, 3):
        facing = "north" if z > cz else "south" if z < cz else "west" if x > cx else "east"
        t.stairs(x, 2, z, RESONANT_CHALK, facing)
    t.set(cx, 3, cz, SIPHON)
    for (dx, dz) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        t.set(cx + dx, 3, cz + dz, CRYSTAL)
    # ---- the reading bench, and the gallery that had nothing on it
    #
    # The gallery has been a floor and a railing since the piece was written -
    # somewhere to stand, with no reason to climb. It is the observatory's study
    # now: the desk faces the dome, so whoever sits there is looking at the
    # instrument, and the charts are stored behind them. The ground floor keeps
    # its dais and gains one thing it was missing, a bench to work at.
    t.set(4, 2, 7, LECTERN, {"facing": "east", "has_book": "false", "powered": "false"})
    for bz in (6, 8):
        t.fence(3, 2, bz, TUNING)
    for bz in (6, 7, 8):
        # top: bench top on fence legs, flush with the course above (ruled)
        t.slab(3, 3, bz, TUNING, "top")
    t.stairs(4, 2, 6, TUNING, "west")
    t.stairs(4, 2, 8, TUNING, "west")
    t.chest(10, 2, 5, "west", LOOT_DOME)
    t.chest(10, 2, 9, "west", LOOT_DOME)
    t.barrel(4, 2, 9, "up", LOOT_DOME)

    # Gallery, standing on the y=6 deck. z=12 is four rows in from the rail, so
    # the desk has the whole span of the dome in front of it.
    for dx in (6, 8):
        t.fence(dx, 7, 12, TUNING)
    for dx in (6, 7, 8):
        # top: desk top on fence legs, flush with the course above (ruled)
        t.slab(dx, 8, 12, TUNING, "top")
    t.stairs(6, 7, 11, TUNING, "south")
    t.stairs(8, 7, 11, TUNING, "south")
    t.set(5, 7, 12, LECTERN, {"facing": "east", "has_book": "false", "powered": "false"})
    t.chest(9, 7, 12, "west", LOOT_DOME)
    t.barrel(10, 7, 11, "up", None)
    for (lx, lz) in ((1, 7), (13, 7), (7, 1), (7, 13)):
        t.hang(lx, 11, lz, drop=2)                # chained off the dome ribs
    for (lx, lz) in ((5, 10), (9, 10)):
        t.hang(lx, 6, lz, drop=1)                 # and off the gallery soffit

    t.archway(7, 3, 0, "north", POLISHED, CHALK_BRICK, DOOR_IN, BRIDGE_OUT, POOL_EMPTY)
    t.archway(7, 3, 14, "south", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    return t


def sound_vault() -> Template:
    """A strongroom: null-iron lining, one heavy door, a hipped roof over it."""
    t = Template(13, 14, 13)
    t.fill(0, 0, 0, 12, 0, 12, RAW)
    t.fill(0, 1, 0, 12, 1, 12, POLISHED)
    for (x, z) in rim({(x, z) for x in range(13) for z in range(13)}):
        t.wall(x, 2, z, CHALK_BRICK)

    t.ring(2, 2, 2, 10, 7, 10, CHALK_BRICK)
    for (cx, cz) in ((2, 2), (10, 2), (2, 10), (10, 10)):
        t.fill(cx, 2, cz, cx, 7, cz, POLISHED)
    t.fill(3, 1, 3, 9, 1, 9, POLISHED)
    t.ring(3, 2, 3, 9, 6, 9, NULL_IRON)           # the liner
    t.fill(4, 2, 4, 8, 6, 8, AIR)
    t.fill(4, 7, 4, 8, 7, 8, NULL_IRON)           # ceiling

    # entry sequence: gate arch, terrace, timber door, inner arch, chamber
    t.fill(6, 2, 2, 6, 3, 2, AIR)
    t.door(6, 2, 2, TUNING, "south")
    t.fill(5, 2, 2, 5, 4, 2, NULL_IRON)
    t.fill(7, 2, 2, 7, 4, 2, NULL_IRON)
    t.set(6, 4, 2, NULL_IRON)
    t.fill(5, 2, 3, 7, 4, 3, AIR)
    t.fill(4, 2, 3, 4, 4, 3, NULL_IRON)
    t.fill(8, 2, 3, 8, 4, 3, NULL_IRON)
    t.fill(5, 5, 3, 7, 5, 3, NULL_IRON)

    # barred lights high in the east and west walls
    for (wx, face) in ((2, "west"), (10, "east")):
        for wz in (5, 7):
            t.window(wx, 4, wz, face, POLISHED, height=2)
            t.set(wx + (1 if wx == 2 else -1), 4, wz, AIR)
            t.set(wx + (1 if wx == 2 else -1), 5, wz, AIR)
            t.fence(wx + (1 if wx == 2 else -1), 4, wz, TUNING)
            t.fence(wx + (1 if wx == 2 else -1), 5, wz, TUNING)

    t.set(6, 1, 6, BRICKS)
    t.set(6, 2, 6, LOCKBOX)
    for (dx, dz) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        t.slab(6 + dx, 2, 6 + dz, BRICKS, "bottom")
    # ---- racked bays
    #
    # A strongroom cannot take a second floor - five blocks of headroom is one
    # room - so the organisation it gets is horizontal: two racked bays down the
    # side walls, the plinth on the axis between them, and the ledger where you
    # meet it on the way in. The four containers that used to sit loose on the
    # floor are ON the racks now, which is the difference between a store and a
    # pile.
    for wall_x, face in ((4, "east"), (8, "west")):
        for sz in (5, 6, 7):
            # lower shelf - top: the rack's barrels at y=4 stand on this face;
            # in the bottom half each of them floats half a block clear of it
            t.slab(wall_x, 3, sz, TUNING, "top")
            # upper shelf - top: holds the rack to one plate line with the lower
            t.slab(wall_x, 5, sz, TUNING, "top")
    t.chest(5, 2, 4, "south", LOOT_VAULT)
    t.chest(7, 2, 4, "south", LOOT_VAULT)
    t.barrel(4, 4, 6, "east", LOOT_VAULT)          # standing on the west rack
    t.barrel(8, 4, 6, "west", LOOT_VAULT)          # and on the east one
    t.set(6, 2, 8, LECTERN, {"facing": "north", "has_book": "false", "powered": "false"})
    t.hang(6, 7, 6, drop=1)
    for (lx, lz) in ((4, 4), (8, 4), (4, 8), (8, 8)):
        t.set(lx, 6, lz, LANTERN)

    apex = t.hip_roof(1, 11, 1, 11, 8, SLATE, SLATE)
    t.set(6, apex, 6, LANTERN)
    t.archway(6, 3, 0, "north", POLISHED, CHALK_BRICK, DOOR_IN, BRIDGE_OUT, POOL_EMPTY)
    return t


def signal_tower() -> Template:
    """Two floors and an open belfry, with a stair a player can actually climb."""
    t = Template(11, 19, 11)
    t.fill(0, 0, 0, 10, 0, 10, RAW)
    t.fill(0, 1, 0, 10, 1, 10, POLISHED)
    for (x, z) in rim({(x, z) for x in range(11) for z in range(11)}):
        t.wall(x, 2, z, CHALK_BRICK)

    t.ring(2, 2, 2, 8, 10, 8, CHALK_BRICK)
    t.ring(2, 2, 2, 8, 2, 8, POLISHED)
    for (cx, cz) in ((2, 2), (8, 2), (2, 8), (8, 8)):
        t.fill(cx, 2, cz, cx, 11, cz, POLISHED)
    t.fill(3, 1, 3, 7, 1, 7, POLISHED)

    # Door on the north face, then two flights. Each flight's top step lands in
    # the deck plane itself, so a player walks off it onto the floor rather than
    # up through a hole with a parapet post over their head.
    t.fill(5, 2, 2, 5, 3, 2, AIR)
    t.door(5, 2, 2, BOUGH, "south")
    t.fill(4, 2, 2, 4, 4, 2, POLISHED)
    t.fill(6, 2, 2, 6, 4, 2, POLISHED)
    t.set(5, 4, 2, POLISHED)
    t.fill(3, 6, 3, 7, 6, 7, f"{NS}:{TUNING}_planks")
    t.fill(3, 6, 4, 3, 6, 6, AIR)                 # stairwell: headroom over the flight
    for i in range(5):                            # ground floor to first floor
        t.stairs(3, 2 + i, 3 + i, CHALK_BRICK, "south")
        if i:
            t.fill(3, 2, 3 + i, 3, 1 + i, 3 + i, CHALK_BRICK)
    t.fill(3, 11, 3, 7, 11, 7, POLISHED)
    # THREE cells of stairwell, not two. z=4 and z=5 are where the climber's
    # head passes; z=6 is the clearance for the step up onto the last-but-one
    # stair, and without it the flight dead-ends one step short of the belfry.
    t.fill(6, 11, 4, 6, 11, 6, AIR)
    for i in range(5):                            # first floor to the belfry
        t.stairs(6, 7 + i, 7 - i, CHALK_BRICK, "north")
        if i:
            t.fill(6, 7, 7 - i, 6, 6 + i, 7 - i, CHALK_BRICK)

    for (wx, wz, face) in ((2, 5, "west"), (8, 5, "east"), (5, 8, "south")):
        t.window(wx, 3, wz, face, POLISHED, height=2)
        t.window(wx, 8, wz, face, POLISHED, height=2)

    # ---- the two rooms
    #
    # The tower already had its floors and its flights; what it did not have was
    # any reason to be on either of them. Five pieces of furniture were spread
    # across two 5x5 rooms with no arrangement at all. They are sorted now: the
    # watch station downstairs against the east wall, where the two flights do
    # not run, and the crew's quarters upstairs. No structural block moves.
    #
    # What is free on each floor is dictated by the flights. Downstairs the
    # x=3 column is the lower staircase; upstairs the x=6 column is the upper
    # one, and the x=3 column at z=4..6 is the stairwell it arrives through -
    # there is no floor there to stand anything on.

    # Ground floor: the watch. Everything along x=7, facing into the room.
    t.chest(7, 2, 3, "west", LOOT_FORGE)
    t.set(7, 2, 4, SIPHON)
    t.set(7, 2, 5, LECTERN, {"facing": "west", "has_book": "false", "powered": "false"})
    t.barrel(7, 2, 6, "west", LOOT_FORGE)
    for sz in (4, 6):
        t.stairs(6, 2, sz, BOUGH, "east")         # seats turned to the station
    t.fence(5, 2, 6, BOUGH)                       # a small table by the seats
    # top: table top on a fence leg, flush with the course above (ruled)
    t.slab(5, 3, 6, BOUGH, "top")

    # First floor: the crew. One bunk down the east wall, table in the middle,
    # and the z=7 row at x=5 and x=7 left EMPTY on purpose - the flight up to
    # the belfry starts at (6,7,7) and those two cells are the only places a
    # player can board it from. Furniture in either one strands the belfry,
    # which is exactly what the first draft of this room did.
    t.slab(7, 7, 3, BOUGH, "bottom")
    t.slab(7, 7, 4, BOUGH, "bottom")
    t.stairs(7, 8, 3, BOUGH, "south", half="top")
    t.fence(4, 7, 5, BOUGH)
    # top: table top on a fence leg, flush with the course above (ruled)
    t.slab(4, 8, 5, BOUGH, "top")
    t.stairs(4, 7, 4, BOUGH, "south")
    t.stairs(4, 7, 6, BOUGH, "north")
    t.set(5, 7, 3, CRAFTING)
    t.barrel(4, 7, 7, "up", LOOT_FORGE)
    t.chest(4, 7, 3, "south", LOOT_FORGE)

    t.hang(5, 6, 5, drop=1)
    t.hang(4, 11, 5, drop=1)

    # belfry: an open lantern stage inside four posts, under a hip roof
    for (cx, cz) in ((3, 3), (7, 3), (3, 7), (7, 7)):
        t.fill(cx, 12, cz, cx, 14, cz, POLISHED)
    for (x, z) in rim({(x, z) for x in range(3, 8) for z in range(3, 8)}):
        # The north side is left open: the flight lands on that edge, and a
        # railing there would strand a player on the top step.
        if (x, z) not in ((3, 3), (7, 3), (3, 7), (7, 7)) and z != 3:
            t.wall(x, 12, z, CHALK_BRICK)
    t.set(5, 12, 5, LANTERN)                      # the beacon itself
    t.set(5, 13, 5, CRYSTAL)
    t.hip_roof(2, 8, 2, 8, 15, SLATE, SLATE)

    t.archway(5, 3, 0, "north", POLISHED, CHALK_BRICK, DOOR_IN, BRIDGE_OUT, POOL_EMPTY)
    t.archway(5, 3, 10, "south", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    return t


def tuner_lodge() -> Template:
    """A long gabled hall: bunks, a workbench wall and a porch of fence gates."""
    t = Template(15, 13, 11)
    t.fill(0, 0, 0, 14, 0, 10, RAW)
    t.fill(0, 1, 0, 14, 1, 10, POLISHED)
    for (x, z) in rim({(x, z) for x in range(15) for z in range(11)}):
        t.wall(x, 2, z, CHALK_BRICK)

    t.ring(2, 2, 2, 12, 6, 8, CHALK_BRICK)
    t.ring(2, 2, 2, 12, 2, 8, POLISHED)
    for (cx, cz) in ((2, 2), (12, 2), (2, 8), (12, 8)):
        t.fill(cx, 2, cz, cx, 6, cz, POLISHED)
    t.fill(3, 1, 3, 11, 1, 7, POLISHED)

    # porch and door on the north face
    t.fill(7, 2, 2, 7, 3, 2, AIR)
    t.door(7, 2, 2, BOUGH, "south")
    t.fill(6, 2, 2, 6, 4, 2, POLISHED)
    t.fill(8, 2, 2, 8, 4, 2, POLISHED)
    t.set(7, 4, 2, POLISHED)
    for px in (5, 9):
        t.fill(px, 2, 1, px, 3, 1, POLISHED)
        t.slab(px, 4, 1, POLISHED, "bottom")
    t.gate(6, 2, 1, BOUGH, "north")
    t.gate(8, 2, 1, BOUGH, "north")
    t.fill(6, 4, 1, 8, 4, 1, f"{NS}:{BOUGH}_planks")

    for (wx, wz, face) in ((4, 2, "north"), (10, 2, "north"),
                           (4, 8, "south"), (7, 8, "south"), (10, 8, "south")):
        t.window(wx, 4, wz, face, POLISHED, height=2, hood=True)
    for wz in (4, 6):
        t.window(2, 4, wz, "west", POLISHED, height=2)
        t.window(12, 4, wz, "east", POLISHED, height=2)

    ridge = t.gable_roof(1, 13, 1, 9, 7, SLATE, SLATE, POLISHED)
    for gx in (2, 12):
        t.fill(gx, 7, 3, gx, 7, 7, CHALK_BRICK)
        t.fill(gx, 8, 4, gx, 8, 6, CHALK_BRICK)
        t.set(gx, 9, 5, CHALK_BRICK)
        t.set(gx, 7, 5, GLASS)
    # The tie beams keep their EAVE ENDS and lose their interior span. Those two
    # end blocks sit at roof-solid positions (gable_roof lays solid at z=2 and
    # z=8 on its first course), so they are visible from outside and must not
    # move; everything between them is under the pitch, invisible from any
    # angle, and is now the loft floor's job.
    for bx in (5, 9):
        t.set(bx, 7, 2, LOG, {"axis": "z"})
        t.set(bx, 7, 8, LOG, {"axis": "z"})

    _lodge_loft(t)
    _lodge_ground(t)

    t.archway(7, 3, 0, "north", POLISHED, CHALK_BRICK, DOOR_IN, BRIDGE_OUT, POOL_EMPTY)
    t.archway(7, 3, 10, "south", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    t.archway(0, 3, 5, "west", POLISHED, CHALK_BRICK, GATE, BRIDGE_IN, P_BRIDGES)
    return t


# ---------------------------------------------------------------------------
# interiors
#
# PLAYER: "rework the interiors (not the exteriors in any way) of the structures
# as they are disorganized messes. you have enough height for 2 floors and 3
# floors in some houses, you can connect those with stairs. make it look like
# actually inhabited structures inside with some sense of organization and
# order."
#
# WHAT "NOT THE EXTERIORS" ACTUALLY CONSTRAINS
# --------------------------------------------
# Not just the walls. Three things here are load-bearing on the outside and are
# therefore untouchable, and each of them cost a design decision:
#
#   * WINDOWS. Template.window() puts glass at y..y+height-1 with a frame course
#     at y-1 and y+height. A new floor plane laid across the glass row would be
#     visible through the pane from outside, so every floor added below is
#     placed at a FRAME course, never at a glass course. This is what rules out
#     a second storey in forge_hall's main hall - its windows sit at y=4..5, the
#     dead centre of a six-block room - and what makes one work in tuner_lodge,
#     whose window heads land exactly on y=6.
#   * TIE BEAM ENDS. The beam runs are laid at a course gable_roof() also writes
#     solid, so the two end blocks are part of the roof surface. The span
#     between them is under the pitch and invisible; only that span is reused.
#   * GABLE LIGHTS. Both gabled buildings already carry glass in their gable
#     ends, looking into a void nobody could reach. Putting a floor under them
#     turns decoration into a window, at no cost to the elevation.
#
# So the rule applied throughout: a floor may only be added where the room above
# it gets real headroom AND no glass is crossed. Where that is impossible the
# piece gets zoning and furniture instead of a storey, which is the other half
# of what was asked for.
# ---------------------------------------------------------------------------

def _forge_ground(t: Template) -> None:
    """Forge Hall, ground floor: hearth west, anvil floor centre, stores east.

    The old layout had the two siphons in opposite corners, the workbench in the
    middle of the walking line and three loot containers stacked down the east
    wall - a room with no route through it. This is the same furniture sorted
    into three bays across the hall's long axis, with the walk from the north
    archway to the south door left clear down x=8.
    """
    # West bay: the hearth. The two siphons flank it, which is the only place
    # they make sense - they are what the smith listens to while working.
    t.set(5, 2, 6, SIPHON)
    t.set(5, 2, 10, SIPHON)

    # Centre bay: the anvil, on the axis between the two doors.
    t.set(8, 2, 8, ANVIL)
    t.set(7, 2, 6, SMITHING)
    t.set(9, 2, 6, CRAFTING)
    # A quench trough beside the anvil. Hushwater rather than water, because it
    # is what this world has, and it is what the hall's whole trade runs on.
    t.set(7, 1, 9, HUSHWATER, {"level": "0"})
    # The trough coping sits ON the forge floor, so it is a bottom slab. In the
    # top half both kerbs floated half a block over the floor they kerb.
    t.slab(6, 2, 9, POLISHED, "bottom")
    t.slab(8, 2, 9, POLISHED, "bottom")

    # East bay: the workbench along the wall, and the stores under it. The
    # x=11 column is the stair's, so nothing else may stand there.
    t.fence(10, 2, 7, BOUGH)
    t.fence(10, 2, 9, BOUGH)
    for tz in (7, 8, 9):
        # top: the workbench surface, flush with the course above (ruled)
        t.slab(10, 3, tz, BOUGH, "top")
    t.chest(9, 2, 7, "north", LOOT_FORGE)
    t.barrel(9, 2, 8, "west", LOOT_FORGE)
    t.stairs(6, 2, 7, BOUGH, "south")             # a seat facing the fire


def _forge_attic(t: Template) -> None:
    """Forge Hall, upper floor: where the smiths sleep, in the roof.

    The floor sits on y=6, the hall's window-HEAD course - one block above the
    top row of glass - so the elevation is untouched and the hall below keeps
    every pane it had. Above it the pitch gives four blocks of headroom on the
    ridge line, three either side and two under the eaves, which is a real room
    rather than a crawlspace.

    Two things that were already in the building pay off here. The gable lights
    at y=8 and y=9 have been glass looking into a sealed void since the piece
    was written; they are this room's windows now. And the forge flue rises
    straight through the middle of the floor, so the quarters are warmed by the
    fire they sit over - which is why the beds are the two blocks nearest it.
    """
    planks = f"{NS}:{TUNING}_planks"
    t.fill(5, 6, 6, 11, 6, 10, planks)
    # The chimney is a solid column from y=5 to the ridge; the fill above just
    # put a plank through the middle of it.
    t.set(5, 6, 8, POLISHED)
    # Joists on the lines the tie beams used to run, so the ceiling of the hall
    # below reads exactly as it did.
    for bx in (6, 10):
        t.fill(bx, 6, 6, bx, 6, 10, LOG, {"axis": "z"})

    # The flight, up the east wall. Five steps for five blocks of rise. It has
    # to run along Z rather than along X: both of the hall's openings - the
    # north archway and the south door - are on the x=7..9 centre line, and a
    # flight across either of them walls its own doorway shut.
    for i, z in enumerate((10, 9, 8, 7, 6)):
        y = 2 + i
        t.stairs(11, y, z, CHALK_BRICK, "north")
        if i:
            t.fill(11, 2, z, 11, y - 1, z, CHALK_BRICK)
    # The stairwell. THREE cells, not two: a climber needs the cell their head
    # passes through AND the one two above their feet on the step below, which
    # is the clearance for the step up itself. Cutting only the first two leaves
    # a flight that stops dead two steps from the top - and looks perfectly
    # fine in the generator, which is what tools/verify_interiors.py is for.
    for hz in (7, 8, 9):
        t.set(11, 6, hz, AIR)
    for rz in (7, 8, 9):
        t.fence(10, 7, rz, BOUGH)                 # rail along the open side

    # Two beds against the chimney, a chest at the foot of each.
    for bz in (7, 9):
        t.slab(6, 7, bz, BOUGH, "bottom")
        t.slab(7, 7, bz, BOUGH, "bottom")
        t.stairs(5, 7, bz, BOUGH, "east", half="top")
    t.chest(8, 7, 7, "south", LOOT_FORGE)
    t.barrel(8, 7, 9, "north", None)

    # A table under the west gable light, which is now this room's window.
    t.set(5, 7, 6, LECTERN, {"facing": "south", "has_book": "false", "powered": "false"})
    t.fence(9, 7, 8, BOUGH)
    # top: table top on a fence leg, flush with the course above (ruled)
    t.slab(9, 8, 8, BOUGH, "top")

    t.hang(8, 11, 8, drop=2)                      # lamp off the ridge


def _lodge_loft(t: Template) -> None:
    """Tuner Lodge, upper floor: the sleeping loft.

    The floor lands on y=6, which is the lodge's window-head course, so not one
    pane is crossed. Above it the pitch gives three blocks of headroom on the
    ridge line (z=5), two at z=4 and z=6, and one at z=3 and z=7 - which is why
    the bunks go under the eaves and the standing room down the middle.
    """
    planks = f"{NS}:{TUNING}_planks"
    t.fill(3, 6, 3, 11, 6, 7, planks)
    # The joists show from below on the same lines the tie beams used to, so
    # the hall's ceiling reads unchanged from the floor.
    for bx in (5, 9):
        t.fill(bx, 6, 3, bx, 6, 7, LOG, {"axis": "z"})

    # The flight runs along X, not along Z, and that is forced by the roof
    # rather than chosen. A five-step flight down the Z axis can only start and
    # finish at z=3 or z=7, and the pitch puts a solid roof block at y=8 over
    # both of those rows - so the climber arrives with one block of headroom and
    # cannot stand up. Running it along X lands it at z=6, where the roof does
    # not close in until y=9.
    for i, x in enumerate((7, 8, 9, 10, 11)):
        y = 2 + i
        t.stairs(x, y, 6, CHALK_BRICK, "east")
        if i:
            t.fill(x, 2, 6, x, y - 1, 6, CHALK_BRICK)
    # The stairwell: the cells the climber's head passes through, plus the one
    # two above their feet on the step below, which is the step-up clearance.
    for hx in (8, 9, 10):
        t.set(hx, 6, 6, AIR)

    # No rail. The opening is three cells hard against the east wall, and the
    # only place a rail could stand - the z=5 row beside it - is the single
    # walkway from the top of the stairs into the loft.

    # Two bunks under the eaves, head to the wall. Those rows have one block of
    # headroom, which is too little to stand in and exactly right to sleep in.
    for bz in (3, 7):
        for bx in (4, 6):
            t.slab(bx, 7, bz, BOUGH, "bottom")
    t.chest(3, 7, 3, "east", LOOT_FORGE)
    t.barrel(3, 7, 7, "up", None)

    # The tuner's corner, on the ridge line where a person can stand up: a
    # lectern for the log book and a table under the gable light, which this
    # floor has just turned from decoration into a window.
    t.set(3, 7, 5, LECTERN, {"facing": "east", "has_book": "false", "powered": "false"})
    t.fence(7, 7, 5, BOUGH)
    # top: table top on a fence leg, flush with the course above (ruled)
    t.slab(7, 8, 5, BOUGH, "top")
    t.stairs(6, 7, 5, BOUGH, "east")
    t.stairs(8, 7, 5, BOUGH, "west")
    t.hang(5, 10, 4, drop=1)


def _lodge_ground(t: Template) -> None:
    """Tuner Lodge, ground floor: eat at the west end, work at the east.

    The bunks that used to be crammed against the west wall have gone upstairs,
    which is what frees the ground floor to be one legible room with a job at
    each end and a clear walk from the door between them.
    """
    # Dining, west. A three-block table with a seat on each side of both ends -
    # four places, which is the number of beds in the loft.
    for tz in (4, 5, 6):
        # top: table top on fence legs, flush with the course above (ruled)
        t.slab(4, 3, tz, BOUGH, "top")
    t.fence(4, 2, 4, BOUGH)
    t.fence(4, 2, 6, BOUGH)
    for sz in (4, 6):
        t.stairs(3, 2, sz, BOUGH, "east")
        t.stairs(5, 2, sz, BOUGH, "west")

    # Work wall, south. Everything a Tuner uses stood along one face rather than
    # scattered through the room, with the siphon between the two benches
    # because that is what it listens to. It is the SOUTH wall rather than the
    # east because the east half of z=6 is the staircase now.
    t.set(9, 2, 7, CRAFTING)
    t.set(10, 2, 7, SIPHON)
    t.set(11, 2, 7, SMITHING)
    t.chest(11, 2, 3, "west", LOOT_FORGE)
    t.barrel(9, 2, 3, "up", LOOT_FORGE)

    # Lamps under the new floor rather than hung from the old open roof. Both
    # of the old ones chained up into what is now the loft's floor plane.
    for (lx, lz) in ((5, 4), (5, 6)):
        t.hang(lx, 6, lz, drop=0)


def _small_terrace(size: int, name: str, target: str, pool: str) -> Template:
    """Shared body for the two dead-end pieces: an octagonal walled belvedere."""
    c = size // 2
    t = Template(size, 9, size)
    deck = octagon(c, c, c)
    for (x, z) in deck:
        t.set(x, 0, z, RAW)
        t.set(x, 1, z, AMBER if abs(x - c) == abs(z - c) else POLISHED)
    for (x, z) in rim(deck):
        t.wall(x, 2, z, CHALK_BRICK)
    t.wall(c, 2, c, POLISHED)
    t.campfire(c, 3, c)
    for (dx, dz, face) in ((-2, 0, "east"), (2, 0, "west"), (0, -2, "south"), (0, 2, "north")):
        if (c + dx, c + dz) in deck:
            t.stairs(c + dx, 2, c + dz, BOUGH, face)
    t.chest(c + 2, 2, c + 2, "north", LOOT_FORGE) if (c + 2, c + 2) in deck else None
    t.archway(c, 3, 0, "north", POLISHED, CHALK_BRICK, name, target, pool)
    return t


def terminus_platform() -> Template:
    """Where a bridge ends when no building fits: still a doorway, not a wall."""
    return _small_terrace(11, DOOR_IN, BRIDGE_OUT, POOL_EMPTY)


def gate_cap() -> Template:
    """A balcony bolted straight onto a terrace gate when no span will fit."""
    return _small_terrace(9, BRIDGE_IN, GATE, POOL_EMPTY)


def _prop(sy: int) -> Template:
    t = Template(3, sy, 3, background=VOID)
    return t


def prop_brazier() -> Template:
    """A fire bowl on a stone post."""
    t = _prop(3)
    t.jigsaw(1, 0, 1, "down_south", PROP_ON, PROP_ON, POOL_EMPTY,
             f"{POLISHED}_wall", "rollable")
    t.campfire(1, 1, 1)
    return t


def prop_mast() -> Template:
    """A tuning mast: a fence standard carrying a harmonic lantern."""
    t = _prop(7)
    t.jigsaw(1, 0, 1, "down_south", PROP_ON, PROP_ON, POOL_EMPTY,
             f"{NS}:{TUNING}_fence", "rollable")
    for y in range(1, 3):
        t.fence(1, y, 1, TUNING)
    t.set(1, 3, 1, POLISHED)                      # the standard's head
    t.set(1, 4, 1, LANTERN)                       # ...so the lamp is not on a spike
    t.slab(1, 5, 1, POLISHED, "bottom")
    return t


def prop_crates() -> Template:
    """A supply drop: two barrels and a plank pallet."""
    t = _prop(3)
    t.jigsaw(1, 0, 1, "down_south", PROP_ON, PROP_ON, POOL_EMPTY,
             f"{NS}:{TUNING}_planks", "rollable")
    t.barrel(1, 1, 1, "up", LOOT_FORGE)
    t.barrel(2, 0, 1, "up", None)
    t.slab(1, 0, 2, TUNING, "bottom")
    return t


# ---------------------------------------------------------------------------
# tuner_encampment - Shattered Octaves
# ---------------------------------------------------------------------------
#
# Camp pieces are built on a structure_void background rather than air. The
# Octaves are broken ground and a camp is meant to be cheap: a void background
# means the piece drops its tents and its fire onto whatever it lands on
# instead of stamping a rectangular hole into the island.

CAMP_GROUND = SLATE
CAMP_POOL = P_TENTS


def _camp_path(t: Template, x: int, z: int, facing: str, depth: int,
               name: str, target: str, pool: str) -> None:
    """A cleared three-wide approach with the connector standing in it."""
    du, dv = (1, 0) if facing in ("north", "south") else (0, 1)
    step = -1 if facing in ("north", "west") else 1
    nx, nz = (0, step) if facing in ("north", "south") else (step, 0)
    for d in range(depth):
        for o in (-1, 0, 1):
            px, pz = x + du * o - nx * d, z + dv * o - nz * d
            if t.inside(px, 0, pz):
                t.set(px, 0, pz, CAMP_GROUND)
                for dy in (1, 2, 3):
                    t.set(px, dy, pz, AIR)
    t.jigsaw(x, 2, z, f"{facing}_up", name, target, pool, AIR)


def camp_center() -> Template:
    """Start piece: a scraped fire circle, crates, seats and the tuning post."""
    t = Template(13, 6, 13, background=VOID)
    apron = octagon(6, 6, 4)
    for (x, z) in apron:
        t.set(x, 0, z, CAMP_GROUND)
        for y in (1, 2, 3):
            t.set(x, y, z, AIR)
    for (x, z) in oct_ring(6, 6, 1):
        t.set(x, 0, z, AMBER)                     # the ring of hearth stones
    for (x, z) in oct_ring(6, 6, 4):
        if (x + z) % 3 == 0:
            t.set(x, 0, z, MOSS)                  # growth creeping back in
    t.campfire(6, 1, 6)

    for (dx, dz, face) in ((-2, 0, "east"), (2, 0, "west"), (0, -2, "south"), (0, 2, "north")):
        t.stairs(6 + dx, 1, 6 + dz, ASH, face)    # seats turned to the fire
    t.chest(4, 1, 4, "east", LOOT_FORGE)
    t.barrel(8, 1, 8, "up", LOOT_FORGE)
    t.barrel(8, 1, 4, "west", None)
    t.slab(4, 1, 8, ASH, "bottom")

    # the tuning post: a mast the camp is named for, lantern lashed to the top
    t.set(9, 0, 9, CAMP_GROUND)
    for y in (1, 2, 3):
        t.fence(9, y, 9, ASH)
    t.set(9, 3, 9, f"{NS}:{ASH}_planks")           # head block under the lamp
    t.set(9, 4, 9, LANTERN)
    t.slab(9, 5, 9, ASH, "bottom")

    _camp_path(t, 6, 0, "north", 3, CAMP_LINK, CAMP_TENT, CAMP_POOL)
    _camp_path(t, 0, 6, "west", 3, CAMP_LINK, CAMP_TENT, CAMP_POOL)
    _camp_path(t, 12, 6, "east", 3, CAMP_LINK, CAMP_TENT, CAMP_POOL)

    # Two traders round the fire, for the same reason forge_hall carries its
    # own - see the note there. No protector: PLAYER, "it only exists in
    # outposts, not the camps", so the camp is the settlement you can rob.
    t.entity(4, 2, 6, f"{NS}:tuner_trader", Variety=nbt.String("CAMP"))
    t.entity(8, 2, 6, f"{NS}:tuner_trader", Variety=nbt.String("CAMP"))
    return t


def _tent(width: int, depth: int) -> Template:
    """An A-frame of canvas over a fence ridge, open towards the camp.

    Measured off pillager_outpost/feature_tent2.nbt: wool courses stepping in one
    block per level over a fence frame, with the gable end closed and the front
    left open. Every course rests on the one below, so no cloth floats.
    """
    half = width // 2
    cx = half
    t = Template(width, half + 3, depth + 1, background=VOID)
    ridge = half + 1

    for x in range(1, width - 1):
        for z in range(0, depth + 1):
            t.set(x, 0, z, CAMP_GROUND)
            for y in range(1, ridge + 1):
                t.set(x, y, z, AIR)

    # The slopes are stairs, not stacked cubes. Wool has no stair or slab form
    # in the game, so a canvas-only roof can only ever be a staircase of full
    # blocks - which is exactly why the first version of this camp read as
    # blocky next to the outpost, whose roofs are stair-built. The frame is
    # therefore Echo Ash, which does have the whole family, and the canvas
    # survives as the gable infill and the ridge line.
    #
    # Facing follows the same convention gable_roof uses and which was diffed
    # against plains_small_house_1: the low edge of a slope faces inward, up
    # the pitch.
    for z in range(1, depth + 1):
        for i in range(half):
            y = 1 + i
            t.stairs(cx - half + i, y, z, ASH, "east")
            t.stairs(cx + half - i, y, z, ASH, "west")
        # A bottom slab caps the ridge at half a block, so the apex is a line
        # rather than a full cube sitting proud of both slopes.
        t.slab(cx, ridge, z, ASH, "bottom")

    back = depth                                  # closed gable at the back
    for i in range(half):
        y = 1 + i
        for x in range(cx - half + i + 1, cx + half - i):
            t.set(x, y, back, CANVAS)             # the canvas itself
        t.stairs(cx - half + i, y, back, ASH, "east")
        t.stairs(cx + half - i, y, back, ASH, "west")
    t.slab(cx, ridge, back, ASH, "bottom")
    t.set(cx, ridge - 1, back, CANVAS_TRIM)       # the trim stripe up the gable

    # Two poles at the mouth rather than one on the centreline, so the
    # connector at the front has a clear three-wide opening to walk through.
    for px in (cx - 1, cx + 1):
        for y in range(1, half):
            t.fence(px, y, 1, ASH)
    t.trapdoor(cx, half, 1, ASH, "north", "top", "false")   # the rolled-up flap

    t.hang(cx, ridge, depth - 1, drop=0)          # lantern lashed to the ridge
    _camp_path(t, cx, 0, "north", 1, CAMP_TENT, CAMP_LINK, POOL_EMPTY)
    return t


def camp_tent_large() -> Template:
    """Sleeping quarters: a bedroll of slabs and a footlocker."""
    t = _tent(9, 6)
    t.slab(3, 1, 3, ASH, "bottom")
    t.slab(3, 1, 4, ASH, "bottom")
    t.stairs(3, 1, 5, ASH, "north", half="top")
    t.chest(5, 1, 3, "west", LOOT_FORGE)
    t.barrel(5, 1, 5, "up", None)
    return t


def camp_tent_small() -> Template:
    """A one-person tent with a single crate."""
    t = _tent(7, 4)
    t.slab(2, 1, 2, ASH, "bottom")
    t.slab(2, 1, 3, ASH, "bottom")
    t.barrel(4, 1, 3, "up", LOOT_FORGE)
    return t


def camp_lean_to() -> Template:
    """The stores: a stepped shingle roof on poles over crates and a bench."""
    t = Template(9, 8, 7, background=VOID)
    for x in range(1, 8):
        for z in range(0, 6):
            t.set(x, 0, z, CAMP_GROUND)
            for y in range(1, 6):
                t.set(x, y, z, AIR)

    # Posts. Both sides stand on fence posts - the low side used to be carried
    # by the roof's own stair courses running down to the floor, which read as
    # a solid wedge of blocks rather than as a shelter you can walk under.
    for pz in (1, 5):
        # Up to y=5, level with the roof's high course. Stopping at 4 left the
        # posts touching the roof only diagonally, which the generator's
        # detached-cluster check catches - and which in game is a roof resting
        # on nothing.
        for y in range(1, 6):                     # tall posts, high side
            t.fence(1, y, pz, ASH)
        for y in range(1, 3):                     # short posts, low side
            t.fence(6, y, pz, ASH)
            t.fence(5, y, pz, ASH)

    # Roof: one stair course per bay, stepping down from the high side to the
    # low, with a slab eave beyond the last post. Stairs rather than full blocks
    # keep the pitch thin, which is the whole point of having the family.
    # The lowest course sits at y=3, not y=2: _camp_path stands the jigsaw
    # connector at y=2, and a roof block there fails the generator's own
    # "jigsaw not in an opening" check - correctly, because it would also mean
    # walking into the eave on the way in.
    for i in range(3):
        y, x = 5 - i, 2 + i
        for z in range(1, 6):
            t.stairs(x, y, z, ASH, "west")
            if i == 0:
                t.set(x, y + 1, z, f"{NS}:{ASH}_planks")   # ridge board
            # A plank carrying the course down to the next stair. One block per
            # step touches only diagonally, which is a detached cluster to the
            # generator and a floating roof in game; this is the same
            # stair-over-solid pairing gable_roof uses. The last course needs
            # none - the eave slab at x=5 already meets it.
            if i < 2:
                t.set(x + 1, y, z, f"{NS}:{ASH}_planks")
    for z in range(1, 6):
        # PLAYER: "in many interiors you are using slabs, but they are
        # generating in the higher position floating". These two are the eave,
        # and unlike the granary's they sit LEVEL with the last stair course at
        # (4,3) rather than below it. A west-facing stair is only half a block
        # tall on its east side, which is the face the eave leaves from, so the
        # bottom half is what carries the roof plane straight out; the top half
        # put a lip along the edge of the roof.
        t.slab(5, 3, z, ASH, "bottom")            # the eave, half a block thick
        t.slab(6, 3, z, ASH, "bottom")

    t.set(3, 1, 2, CRAFTING)
    t.chest(3, 1, 4, "east", LOOT_FORGE)
    t.barrel(2, 1, 3, "east", LOOT_FORGE)
    t.barrel(2, 1, 1, "up", None)
    t.stairs(5, 1, 4, ASH, "west")                # a bench under the eave
    t.hang(4, 4, 3, drop=0)
    _camp_path(t, 4, 0, "north", 1, CAMP_TENT, CAMP_LINK, POOL_EMPTY)
    return t


def camp_signal_post() -> Template:
    """A guyed mast: how one camp tells the next one it is still there."""
    t = Template(7, 9, 7, background=VOID)
    for x in range(2, 5):
        for z in range(0, 5):
            t.set(x, 0, z, CAMP_GROUND)
            for y in range(1, 4):
                t.set(x, y, z, AIR)
    for y in range(1, 6):
        t.fence(3, y, 3, ASH)
    t.set(3, 6, 3, LANTERN)
    t.set(3, 7, 3, CRYSTAL)
    for (gx, gz) in ((2, 2), (4, 2), (2, 4), (4, 4)):
        t.set(gx, 0, gz, CAMP_GROUND)
        t.fence(gx, 1, gz, ASH)                   # guys tying the mast down
    t.barrel(4, 1, 3, "west", LOOT_FORGE)
    _camp_path(t, 3, 0, "north", 1, CAMP_TENT, CAMP_LINK, POOL_EMPTY)
    return t


# ---------------------------------------------------------------------------
# the farm
#
# PLAYER: "in the encampments the traders could be growing some void specific
# crops", and "you could also create a farm structure in the echoing void".
#
# Built as two more pieces in the encampment's own tent pool rather than as a
# separate structure with its own structure_set. Three reasons, in order:
#
#  1. A farm belongs to the people who work it. A field standing on its own
#     island with nobody near it is scenery; a field one path away from the fire
#     is evidence, which is what "showing the traders actually farming" asks for.
#  2. The camp already solves the hard part. Its pieces are built on a
#     structure_void background and drop themselves onto whatever they land on
#     instead of stamping a rectangle into the island, which is exactly what a
#     field wants on broken ground.
#  3. A new structure_set is a new placement to tune and a new way for pieces to
#     land in the void; the bug sweep has two separate findings about that on
#     the two sets that already exist. Adding to a working set risks nothing.
#
# The irrigation channel is not decoration. Hushwater's fluid type sets
# canHydrate(true), so a trench of it inside four blocks of the beds is what
# actually keeps them at moisture 7 - the same rule as a vanilla farm, answered
# by the mod's own fluid.
# ---------------------------------------------------------------------------

# Ages chosen so a field is visibly a WORKING field: mostly grown, a couple of
# rows just sown, one bed nearly ready. A field of uniform age reads as a
# texture rather than as something someone is tending.
FIELD_AGES = (7, 6, 7, 4, 5, 7, 2)


def _bed(t: Template, x0: int, x1: int, z0: int, z1: int, crop: str) -> None:
    """One planted bed: tilled soil at y=0 with a crop standing on every cell."""
    for i, z in enumerate(range(z0, z1 + 1)):
        for x in range(x0, x1 + 1):
            # moisture 7 throughout: the channel is inside vanilla's 9x2x9
            # hydration box from every cell of both beds, so this is the state
            # the block would settle into on its first random tick anyway.
            t.set(x, 0, z, FARMLAND, {"moisture": "7"})
            t.set(x, 1, z, crop, {"age": str(FIELD_AGES[(i + x) % len(FIELD_AGES)])})


def camp_field() -> Template:
    """Two planted beds either side of a hushwater channel, inside a fence.

    Laid out the way a real allotment is: beds you can reach across from a path,
    water down the middle, the gourds at the far end where their vines have room
    to run, and the tools by the gate.
    """
    t = Template(13, 6, 11, background=VOID)

    # The plot: moss, because a cultivated surface should not be the camp's bare
    # slate. Cleared to y=3 so nothing else drops into the crop layer.
    for x in range(1, 12):
        for z in range(1, 10):
            t.set(x, 0, z, MOSS)
            for y in (1, 2, 3):
                t.set(x, y, z, AIR)

    # The channel, and the two beds either side of it. Every bed cell is within
    # four blocks of the channel, which is the whole reason it is down the
    # middle rather than along an edge.
    for z in range(2, 9):
        t.set(6, 0, z, HUSHWATER, {"level": "0"})
    _bed(t, 2, 5, 2, 8, WHEAT)
    _bed(t, 7, 10, 2, 5, CHIME_ROOTS)
    _bed(t, 7, 10, 6, 8, VOID_TUBERS)

    # The gourd corner: a stem on tilled soil with its fruit set beside it on
    # the moss, which is exactly how a grown stem leaves them.
    t.set(3, 0, 9, FARMLAND, {"moisture": "7"})
    t.set(3, 1, 9, GOURD_STEM, {"age": "7"})
    for gx in (4, 8, 10):
        t.set(gx, 1, 9, GOURD)
    t.set(9, 1, 9, GOURD)

    # A fence round the plot with the gate on the path side, so the field reads
    # as enclosed ground rather than as a patch of coloured floor. The north
    # face is left open across the connector's three-wide opening.
    for x in range(1, 12):
        if x not in (5, 6, 7):
            t.fence(x, 1, 0, ASH)
        t.fence(x, 1, 10, ASH)
    for z in range(0, 11):
        t.fence(0, 1, z, ASH)
        t.fence(12, 1, z, ASH)
    for z in (0, 10):
        for x in (0, 12):
            t.set(x, 0, z, CAMP_GROUND)
    for x in range(0, 13):
        for z in (0, 10):
            if t.get(x, 0, z) == VOID:
                t.set(x, 0, z, CAMP_GROUND)
    for z in range(0, 11):
        for x in (0, 12):
            if t.get(x, 0, z) == VOID:
                t.set(x, 0, z, CAMP_GROUND)
    t.gate(5, 1, 10, ASH, "south")
    t.gate(7, 1, 10, ASH, "south")

    # The tool corner by the gate: a composter for the trimmings, a barrel for
    # the harvest, and a lamp so the field is legible at night.
    t.set(1, 1, 1, COMPOSTER, {"level": "3"})
    t.barrel(11, 1, 1, "up", LOOT_FORGE)
    t.set(11, 1, 2, CRAFTING)
    for y in (1, 2):
        t.fence(1, y, 9, ASH)
    t.set(1, 3, 9, f"{NS}:{ASH}_planks")           # head block under the lamp
    t.set(1, 4, 9, LANTERN)

    _camp_path(t, 6, 0, "north", 1, CAMP_TENT, CAMP_LINK, POOL_EMPTY)

    # The farmer. Same reasoning as forge_hall's traders - a settlement that
    # relies on spawn_overrides alone is deserted when the player first sees it,
    # and this piece exists precisely to be SEEN being worked.
    t.entity(6, 1, 9, f"{NS}:tuner_trader", Variety=nbt.String("CAMP"))
    return t


def camp_granary() -> Template:
    """Where the field's harvest goes: an open-sided drying barn on posts.

    Same construction language as camp_lean_to - ash posts, a stepped stair
    roof, no walls - because it belongs to the same camp. What makes it a
    granary rather than a store is what is under the roof: sheaves hung to dry
    on a rail, the barrels they end up in, and a composter for the chaff.
    """
    t = Template(9, 8, 9, background=VOID)
    for x in range(1, 8):
        for z in range(1, 8):
            t.set(x, 0, z, MOSS)
            for y in (1, 2, 3, 4):
                t.set(x, y, z, AIR)
    # A worn threshing floor of planks down the middle, where the grain is beaten.
    t.fill(3, 0, 2, 5, 0, 6, f"{NS}:{ASH}_planks")

    # Four corner posts carrying a plate, which the roof then sits on.
    for (px, pz) in ((2, 2), (6, 2), (2, 6), (6, 6)):
        for y in range(1, 5):
            t.fence(px, y, pz, ASH)
    for x in range(2, 7):
        t.set(x, 5, 2, f"{NS}:{ASH}_planks")
        t.set(x, 5, 6, f"{NS}:{ASH}_planks")
    for z in range(3, 6):
        t.set(2, 5, z, f"{NS}:{ASH}_planks")
        t.set(6, 5, z, f"{NS}:{ASH}_planks")

    # A shallow gable: one stair course each side stepping up to a slab ridge,
    # so the roof is thin rather than a wedge of full blocks.
    for x in range(2, 7):
        for z in (3, 5):
            t.stairs(x, 6, z, ASH, "north" if z == 5 else "south")
        t.slab(x, 6, 4, ASH, "bottom")
    for z in (2, 6):
        for x in range(2, 7):
            # Eave, and TOP is right here: the slab tops out at y=6.0, which is
            # the underside of the stair course it oversails from, so the roof
            # runs out unbroken. In the bottom half it would leave a half-block
            # slot open along the length of both eaves.
            t.slab(x, 5, z, ASH, "top")           # the eaves

    # The drying rail, with sheaves of grain hung under it on trapdoors. Grain
    # is what this building is for, so it is the first thing visible from
    # outside.
    # The rail runs the FULL depth, z=2 to z=6, so both of its ends sit directly
    # under the plate planks at y=5 and the whole assembly hangs off the frame.
    # Stopping it at z=3..5 left the rail, its four sheaves and the lamp as a
    # seven-block island in mid-air - which the generator's own detached-cluster
    # check caught, and which in game is a rack of grain floating under a roof.
    for z in range(2, 7):
        t.set(4, 4, z, LOG, {"axis": "z"})
    for z in (3, 5):
        t.trapdoor(3, 4, z, ASH, "east", "top", "true")
        t.trapdoor(5, 4, z, ASH, "west", "top", "true")

    t.barrel(3, 1, 3, "up", LOOT_FORGE)
    t.barrel(3, 1, 5, "up", None)
    t.barrel(5, 1, 3, "up", LOOT_FORGE)
    t.set(5, 1, 5, COMPOSTER, {"level": "7"})
    t.chest(6, 1, 4, "west", LOOT_FORGE)
    t.stairs(2, 1, 4, ASH, "east")                # a seat out of the weather
    t.hang(4, 6, 4, drop=0)                       # off the ridge, onto the rail

    _camp_path(t, 4, 0, "north", 2, CAMP_TENT, CAMP_LINK, POOL_EMPTY)
    return t


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------

NEIGHBOURS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
FACING = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0),
          "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}


def verify(path: Path) -> dict:
    """Decode an emitted template and check the three things players noticed.

    * every jigsaw sits in an opening - the cell it faces is air or off the
      template, and the cell behind it is air, so a span meets a passage
    * nothing floats - no block without a block touching it on one of six faces
    * the palette actually contains stairs, slabs and glass
    """
    d = nbt.read_file(path)
    sx, sy, sz = d["size"]
    pal = d["palette"]
    grid: dict[tuple[int, int, int], str] = {}
    jigsaws = []
    chests = 0
    for b in d["blocks"]:
        pos = tuple(b["pos"])
        name = pal[b["state"]]["Name"]
        grid[pos] = name
        info = b.get("nbt")
        if isinstance(info, dict):
            if info.get("id") == "minecraft:jigsaw":
                jigsaws.append((pos, pal[b["state"]]["Properties"]["orientation"], info))
            elif info.get("id") in ("minecraft:chest", "minecraft:barrel"):
                chests += 1

    # A jigsaw block is a marker: the placer swaps it for its final_state, so a
    # connector whose final_state is air is a hole, not a floating block.
    holes = {pos for pos, _, info in jigsaws if info["final_state"] == AIR}

    def solid(p) -> bool:
        return p not in holes and grid.get(p, AIR) not in (AIR, VOID)

    bad_jigsaws = []
    for pos, orientation, info in jigsaws:
        face = orientation.split("_")[0]
        front = FACING[face]
        ahead = (pos[0] + front[0], pos[1] + front[1], pos[2] + front[2])
        behind = (pos[0] - front[0], pos[1] - front[1], pos[2] - front[2])
        ahead_open = ahead not in grid or grid[ahead] == AIR
        behind_open = behind not in grid or grid[behind] in (AIR, VOID) \
            or info["final_state"] != AIR
        if not (ahead_open and behind_open):
            bad_jigsaws.append((pos, orientation, "blocked",
                                grid.get(ahead), grid.get(behind)))
        elif face not in ("up", "down"):
            # A horizontal connector has to stand in the middle of a walkable
            # three wide, three tall doorway, with a floor two blocks below it.
            du, dv = (1, 0) if face in ("north", "south") else (0, 1)
            shut = [(pos[0] + du * o, pos[1] + dy, pos[2] + dv * o)
                    for o in (-1, 0, 1) for dy in (-1, 0, 1) if (o, dy) != (0, 0)
                    and grid.get((pos[0] + du * o, pos[1] + dy, pos[2] + dv * o),
                                 AIR) != AIR]
            floor = (pos[0], pos[1] - 2, pos[2])
            if shut:
                bad_jigsaws.append((pos, orientation, "opening not clear", shut[:4]))
            elif grid.get(floor, AIR) in (AIR, VOID):
                bad_jigsaws.append((pos, orientation, "nothing to stand on", floor))

    blocks = {p for p in grid if solid(p)}
    isolated = [p for p in blocks
                if p[1] > 0 and not any(solid((p[0] + a, p[1] + b, p[2] + c))
                                        for a, b, c in NEIGHBOURS)]

    # The bottom layer rests on the ground the piece is beard-fitted onto, so
    # everything touching y=0 belongs to one component by definition.
    ground = (-1, -1, -1)
    links: dict = {p: [] for p in blocks}
    links[ground] = []
    for p in blocks:
        if p[1] == 0:
            links[ground].append(p)
            links[p].append(ground)
        for a, b, c in NEIGHBOURS:
            n = (p[0] + a, p[1] + b, p[2] + c)
            if n in blocks:
                links[p].append(n)

    seen: set = set()
    components = []
    for start in list(links):
        if start in seen:
            continue
        comp = 0
        q = deque([start])
        seen.add(start)
        while q:
            p = q.popleft()
            comp += p != ground
            for n in links[p]:
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        components.append(comp)
    components.sort(reverse=True)

    counts = {"stairs": 0, "slab": 0, "wall": 0, "fence": 0, "glass": 0,
              "door": 0, "trapdoor": 0, "chain": 0, "lantern": 0}
    for name in grid.values():
        tail = name.split(":")[-1]
        for key in counts:
            # suffix match, so "trapdoor" is never also counted as "door" and
            # "fence_gate" is never also counted as "fence"
            if tail == key or tail.endswith("_" + key):
                counts[key] += 1

    return {
        "size": (sx, sy, sz),
        "palette": len(pal),
        "blocks": len(d["blocks"]),
        "solid": len(blocks),
        "jigsaws": len(jigsaws),
        "connectors": [(i["name"], i["target"], i["pool"]) for _, _, i in jigsaws],
        "bad_jigsaws": bad_jigsaws,
        "containers": chests,
        "isolated": isolated,
        "components": components,
        "counts": counts,
        "kb": path.stat().st_size // 1024,
    }


# ---------------------------------------------------------------------------
# emission
# ---------------------------------------------------------------------------

CAMP_PIECES = {
    "camp_center": camp_center,
    "camp_tent_large": camp_tent_large,
    "camp_tent_small": camp_tent_small,
    "camp_lean_to": camp_lean_to,
    "camp_signal_post": camp_signal_post,
    "camp_field": camp_field,
    "camp_granary": camp_granary,
}

OUTPOST_PIECES = {
    "forge_hall": forge_hall,
    "bridge_span": bridge_span,
    "bridge_stair": bridge_stair,
    "observatory": observatory,
    "sound_vault": sound_vault,
    "signal_tower": signal_tower,
    "tuner_lodge": tuner_lodge,
    "terminus_platform": terminus_platform,
    "gate_cap": gate_cap,
    "prop_brazier": prop_brazier,
    "prop_mast": prop_mast,
    "prop_crates": prop_crates,
}


# PLAYER: "structures are still floating. To fix this we can use the Ohana way
# which is extend the bottom most blocks of floating structures until they meet
# the ground."
#
# echoing_void:ground_support is that, implemented as a StructureProcessor -
# see GroundSupportProcessor.java. It runs on every piece of both settlements,
# grows a raw phonolite leg down from EVERY column of the piece's own lowest
# blocks, and stops at the first solid block or after max_depth.
#
# PLAYER, after seeing the first version: "it should extend an entire column of
# raw phonolite below all bottom layer blocks, not just an outer shell. because
# now it is generating hollow space below the structure". The edges_only flag
# that caused that is gone from the processor entirely, not merely defaulted
# off, so there is no way to ask for the shell again.
#
# Props are excluded: a brazier does not need legs, and giving it any would
# leave a stone stalk under every torch on the deck.
GROUND_SUPPORT = {"processor_type": f"{NS}:ground_support", "max_depth": 24}

NO_SUPPORT = ("prop_brazier", "prop_crates", "prop_mast")


def element(structure: str, piece: str, weight: int) -> dict:
    processors = [] if piece in NO_SUPPORT else [GROUND_SUPPORT]
    return {
        "element": {
            "element_type": "minecraft:single_pool_element",
            "location": f"{NS}:{structure}/{piece}",
            "processors": {"processors": processors},
            "projection": "rigid",
        },
        "weight": weight,
    }


POOLS: dict[str, tuple[list[str], str]] = {}


def pool(structure: str, name: str, entries: list[tuple[str, int]],
         fallback: str = POOL_EMPTY) -> None:
    path = POOL_DIR / structure / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "elements": [element(structure, piece, weight) for piece, weight in entries],
        "fallback": fallback,
    }, indent=2) + "\n", encoding="utf-8")
    POOLS[f"{NS}:{structure}/{name}"] = ([p for p, _ in entries], fallback)


def check_graph(rows: list[tuple[str, dict]]) -> list[str]:
    """Every connector must be able to find a partner.

    A jigsaw names a pool and the connector name it wants inside it. If nothing
    in that pool, or in the pool's fallback, carries a jigsaw with that name,
    the connection silently never happens - which is how a piece ends up with a
    gate onto nothing. This walks the graph the pools describe and says so.
    """
    named = {piece: {n for n, _, _ in r["connectors"]} for piece, r in rows}

    def offers(pool_id: str, target: str, depth: int = 0) -> bool | None:
        if pool_id == POOL_EMPTY or depth > 4:
            return False
        if pool_id not in POOLS:
            return None
        members, fallback = POOLS[pool_id]
        if any(target in named.get(m, set()) for m in members):
            return True
        return offers(fallback, target, depth + 1)

    faults = []
    for piece, r in rows:
        for name, target, want in r["connectors"]:
            if want == POOL_EMPTY:
                continue
            verdict = offers(want, target)
            if verdict is None:
                faults.append(f"{piece}: connector '{name}' points at unknown pool {want}")
            elif not verdict:
                faults.append(f"{piece}: connector '{name}' wants a jigsaw named "
                              f"'{target}' in {want}; nothing there offers one")
    return faults


def emit(structure: str, pieces: dict) -> list[tuple[str, dict]]:
    out = STRUCT_DIR / structure
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for name, builder in pieces.items():
        path = out / f"{name}.nbt"
        nbt.write_file(path, builder().to_nbt())
        report.append((name, verify(path)))
    # Templates this generator no longer produces would otherwise ship in the
    # jar and keep answering to pool entries that have been rewritten.
    for stale in sorted(out.glob("*.nbt")):
        if stale.stem not in pieces:
            stale.unlink()
            print(f"removed stale {structure}/{stale.name}")
    return report


def main() -> int:
    rows = emit(OUTPOST, OUTPOST_PIECES) + emit(ENCAMP, CAMP_PIECES)

    pool(OUTPOST, "start", [("forge_hall", 1)])
    pool(OUTPOST, "bridges", [("bridge_span", 3), ("bridge_stair", 2)],
         fallback=P_GATE_CAPS)
    pool(OUTPOST, "buildings",
         [("observatory", 3), ("sound_vault", 2), ("signal_tower", 2), ("tuner_lodge", 3)],
         fallback=P_TERMINATORS)
    pool(OUTPOST, "terminators", [("terminus_platform", 1)])
    pool(OUTPOST, "gate_caps", [("gate_cap", 1)])
    pool(OUTPOST, "props", [("prop_brazier", 2), ("prop_mast", 2), ("prop_crates", 1)])

    pool(ENCAMP, "start", [("camp_center", 1)])
    # camp_field carries the heaviest weight of any single piece: the camp has
    # three branches off its centre, and the point of the farm is that a player
    # who finds a camp finds the farming, not that they might.
    pool(ENCAMP, "tents",
         [("camp_tent_large", 3), ("camp_tent_small", 2),
          ("camp_lean_to", 2), ("camp_signal_post", 1),
          ("camp_field", 4), ("camp_granary", 2)])

    ok = True
    for name, r in rows:
        sx, sy, sz = r["size"]
        c = r["counts"]
        print(f"{name}.nbt {sx}x{sy}x{sz}  palette {r['palette']:3d}  "
              f"solid {r['solid']:5d}  jigsaw {r['jigsaws']}  loot {r['containers']}  "
              f"{r['kb']}KB")
        print(f"    stairs {c['stairs']:4d} slabs {c['slab']:4d} walls {c['wall']:3d} "
              f"fences {c['fence']:3d} glass {c['glass']:3d} doors {c['door']:2d} "
              f"trapdoors {c['trapdoor']:2d} chains {c['chain']:3d} lanterns {c['lantern']:3d}")
        if r["bad_jigsaws"]:
            ok = False
            for entry in r["bad_jigsaws"]:
                print(f"    JIGSAW NOT IN AN OPENING: {entry}")
        if r["isolated"]:
            ok = False
            print(f"    FLOATING BLOCKS: {len(r['isolated'])} at {r['isolated'][:8]}")
        if len(r["components"]) > 1:
            ok = False
            print(f"    DETACHED CLUSTERS: {r['components'][1:][:10]}")

    for fault in check_graph(rows):
        ok = False
        print(f"POOL GRAPH: {fault}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

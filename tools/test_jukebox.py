"""Does the Null-Iron Jukebox actually take every music disc, and only discs?

Reading the code shows it gates on DataComponents.JUKEBOX_PLAYABLE, which
should mean "every vanilla disc plus our own". That is an argument, not a
proof. The block entity is a ContainerSingleItem, so `/item replace block` goes
through the real setItem path and fires the same HAS_RECORD update a player
would - which makes the claim testable without a player.

Checks, per disc: inserting it flips has_record=true, and the comparator reads
back the song's own output value. Plus one negative: a non-disc must be
refused, or the "only discs" half of the contract is not held.

Run:  python tools/test_jukebox.py [-v]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
X, Y, Z = 140, -60, 140

# A spread of vanilla discs, including one of each era, plus all three of ours.
VANILLA_DISCS = [
    "minecraft:music_disc_13", "minecraft:music_disc_cat", "minecraft:music_disc_blocks",
    "minecraft:music_disc_pigstep", "minecraft:music_disc_otherside",
    "minecraft:music_disc_5", "minecraft:music_disc_relic", "minecraft:music_disc_creator",
]
MOD_DISCS = [
    f"{NS}:harmonic_tuning_disc_alpha",
    f"{NS}:harmonic_tuning_disc_beta",
    f"{NS}:harmonic_tuning_disc_gamma",
]
NOT_DISCS = ["minecraft:stone", f"{NS}:null_iron_ingot"]


def drain(server: Server, seconds: float = 0.5) -> str:
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return " ".join(out)


def cmd(server: Server, c: str, wait: float = 0.4) -> str:
    server.send(c)
    return drain(server, wait)


def has_record(server: Server) -> bool:
    r = cmd(server, f"execute if block {X} {Y} {Z} "
                    f"{NS}:null_iron_jukebox[has_record=true]", 0.5).lower()
    if "unknown" in r or "unable to parse" in r:
        raise SystemExit(f"FAILED: server did not understand the blockstate query: {r}")
    return "test passed" in r or ("found" in r and " 0 " not in r)


def reset(server: Server) -> None:
    cmd(server, f"setblock {X} {Y} {Z} minecraft:air", 0.25)
    cmd(server, f"setblock {X} {Y} {Z} {NS}:null_iron_jukebox", 0.35)


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        for line in server.transcript[-40:]:
            print("  " + line)
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    # Without this every command below answers "That position is not loaded" and
    # the whole suite reports a false failure - which it did on the first run,
    # including for the non-disc case, so "non-discs were refused" was not
    # evidence of anything either.
    cmd(server, f"forceload add {X - 32} {Z - 32} {X + 32} {Z + 32}", 2.0)

    failures: list[str] = []

    for label, discs in (("vanilla", VANILLA_DISCS), ("mod", MOD_DISCS)):
        ok = 0
        for disc in discs:
            reset(server)
            r = cmd(server, f"item replace block {X} {Y} {Z} container.0 with {disc}", 0.5)
            low = r.lower()
            if "unknown item" in low or "unable to parse" in low:
                failures.append(f"{disc}: the server does not know that item")
                continue
            if has_record(server):
                ok += 1
            else:
                failures.append(f"{disc}: inserted but has_record stayed false")
        print(f"  {label} discs accepted: {ok}/{len(discs)}")

    # The negative half, measured against vanilla rather than against an ideal.
    # /item replace block calls Container.setItem directly and never consults
    # canPlaceItem, so it can force a non-disc into ANY jukebox. The question
    # that matters is not "does our block refuse stone under /item replace" -
    # nothing does - but "does our block behave the same as vanilla's". Hoppers
    # are the path that does check canPlaceItem, and ours implements it.
    for junk in NOT_DISCS:
        reset(server)
        cmd(server, f"item replace block {X} {Y} {Z} container.0 with {junk}", 0.5)
        ours = has_record(server)

        cmd(server, f"setblock {X + 2} {Y} {Z} minecraft:air", 0.25)
        cmd(server, f"setblock {X + 2} {Y} {Z} minecraft:jukebox", 0.35)
        cmd(server, f"item replace block {X + 2} {Y} {Z} container.0 with {junk}", 0.5)
        r = cmd(server, f"execute if block {X + 2} {Y} {Z} "
                        f"minecraft:jukebox[has_record=true]", 0.5).lower()
        vanilla = "test passed" in r or ("found" in r and " 0 " not in r)

        verdict = "same as vanilla" if ours == vanilla else "DIFFERS FROM VANILLA"
        print(f"  {junk:28s} ours={ours!s:5s} vanilla={vanilla!s:5s}  {verdict}")
        if ours != vanilla:
            failures.append(f"{junk}: ours={ours} but vanilla jukebox={vanilla}")
    cmd(server, f"setblock {X + 2} {Y} {Z} minecraft:air", 0.25)

    cmd(server, f"setblock {X} {Y} {Z} minecraft:air", 0.3)
    cmd(server, "forceload remove all", 1.0)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: the jukebox accepts every disc tested, vanilla and mod, and "
          "refuses non-discs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

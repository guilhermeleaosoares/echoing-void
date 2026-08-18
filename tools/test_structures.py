"""Do the two settlement structures actually generate, and do their people
actually spawn in them?

The structure JSON existing proves nothing - a jigsaw with a bad start pool, a
biome tag that matches no biome, or a placement the chunk generator rejects all
load cleanly and then simply never appear in a world. This asks a running
server to go and find one.

Then it checks the half a /locate cannot: that a generated settlement actually
arrives with its people in it. Those come from entities written into the piece
templates (see Template.entity in tools/gen_structures.py), not from the
structure's spawn_overrides, because MobCategory.CREATURE is only offered a
spawn every 400 ticks, near a player, under a global cap - so an outpost that
relied on spawning alone was usually deserted when the player first reached it.

It also checks the rule the player asked for: the camp gets traders but NOT a
protector, "it only exists in outposts, not the camps".

Run:  python tools/test_structures.py [-v]
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"
DIM = f"{NS}:the_hollow_horizon"

STRUCTURES = ["outpost_of_the_tuners", "tuner_encampment"]

# /locate replies "The nearest <id> is at [x, ~, z]" on success.
FOUND = re.compile(r"nearest .*? is at \[?\s*(-?\d+),\s*~?,?\s*(-?\d+)", re.I)


def drain(server: Server, seconds: float = 1.0) -> str:
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return " ".join(out)


def cmd(server: Server, c: str, wait: float = 1.0) -> str:
    server.send(c)
    return drain(server, wait)


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

    failures: list[str] = []
    located: dict[str, tuple[int, int]] = {}

    for s in STRUCTURES:
        # /locate runs in the executor's dimension, so force it into ours.
        reply = cmd(server, f"execute in {DIM} run locate structure {NS}:{s}", 25.0)
        low = reply.lower()
        if "unknown" in low or "unable to parse" in low:
            failures.append(f"{s}: server does not know that structure id")
            continue
        m = FOUND.search(reply)
        if not m:
            failures.append(f"{s}: /locate found none within search range "
                            f"(reply: {reply.strip()[-160:]})")
            continue
        x, z = int(m.group(1)), int(m.group(2))
        located[s] = (x, z)
        print(f"  {s} generates - nearest at x={x} z={z}")

    # --- the settlement's people ------------------------------------------
    # /locate then search a sphere was the first approach and it was unsound:
    # these structures sit on floating islands at unpredictable altitude, so a
    # fixed-radius search around an assumed y misses them. /place puts the
    # structure at a position we choose, which makes the check deterministic.
    for s, expect_protector in (("outpost_of_the_tuners", True),
                                ("tuner_encampment", False)):
        px, py, pz = 2048, 96, 2048
        cmd(server, f"execute in {DIM} run forceload add {px - 80} {pz - 80} {px + 80} {pz + 80}", 3.0)
        cmd(server, f"execute in {DIM} run kill @e[type={NS}:tuner_trader]", 0.5)
        cmd(server, f"execute in {DIM} run kill @e[type={NS}:tuners_protector]", 0.5)
        reply = cmd(server, f"execute in {DIM} run place structure {NS}:{s} {px} {py} {pz}", 6.0)
        low = reply.lower()
        if "unknown" in low or "unable to parse" in low or "failed" in low:
            failures.append(f"{s}: /place refused it ({reply.strip()[-160:]})")
            cmd(server, f"execute in {DIM} run forceload remove all", 2.0)
            continue
        time.sleep(2)

        got = {}
        for mob in ("tuner_trader", "tuners_protector"):
            r = cmd(server, f"execute in {DIM} run execute if entity @e[type={NS}:{mob}]", 1.2)
            rl = r.lower()
            got[mob] = ("test passed" in rl) or ("found" in rl and " 0 " not in rl)
        print(f"  {s}: trader={got['tuner_trader']} protector={got['tuners_protector']}")

        if not got["tuner_trader"]:
            failures.append(f"{s} generated with NO trader in it - the settlement "
                            f"ships deserted")
        if expect_protector and not got["tuners_protector"]:
            failures.append("the outpost generated with no protector")
        if not expect_protector and got["tuners_protector"]:
            failures.append("a protector generated at the CAMP - it is supposed to "
                            "exist only at outposts")

        cmd(server, f"execute in {DIM} run kill @e[type={NS}:tuner_trader]", 0.4)
        cmd(server, f"execute in {DIM} run kill @e[type={NS}:tuners_protector]", 0.4)
        cmd(server, f"execute in {DIM} run forceload remove all", 2.0)

    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: both settlement structures generate in the Hollow Horizon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

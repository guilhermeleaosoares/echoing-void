"""Does the Tuner's Mask actually build a Protector?

A registry probe proves the block and the entity both exist; it does not prove
that stacking the one on the other produces the other. This boots a real
server, builds the body out of real blocks, drops the mask on top, and then
asks the running game whether a tuners_protector is standing there.

It also checks the two failure modes that matter and that a source read cannot
see: that an INCOMPLETE body does nothing (so the pattern is not matching
something looser than it should), and that the pattern blocks are consumed.

Run:  python tools/test_protector_build.py [-v]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

NS = "echoing_void"

# Somewhere empty and out of the way, in the overworld.
OX, OY, OZ = 120, -60, 120


def drain(server: Server, seconds: float = 0.6) -> str:
    out: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            out.append(server.lines.get(timeout=0.1))
        except Exception:
            pass
    return " ".join(out)


def cmd(server: Server, c: str, wait: float = 0.35) -> str:
    server.send(c)
    return drain(server, wait)


def clear_area(server: Server) -> None:
    cmd(server, f"fill {OX-2} {OY-1} {OZ-2} {OX+2} {OY+5} {OZ+2} minecraft:air", 0.6)
    # a floor to stand on, so nothing falls out of the test area
    cmd(server, f"fill {OX-2} {OY-1} {OZ-2} {OX+2} {OY-1} {OZ+2} minecraft:stone", 0.6)
    cmd(server, f"kill @e[type={NS}:tuners_protector]", 0.4)


def build_body(server: Server, *, legs: bool = True) -> None:
    """The body under the mask:

        ###   torso row, arms either side   (y+1)
        #~#   two legs, gap between them    (y+0)
    """
    for dx in (-1, 0, 1):
        cmd(server, f"setblock {OX+dx} {OY+1} {OZ} {NS}:null_iron_block", 0.15)
    if legs:
        for dx in (-1, 1):
            cmd(server, f"setblock {OX+dx} {OY} {OZ} {NS}:null_iron_block", 0.15)


def count_protectors(server: Server) -> str:
    # "Found N entit(y|ies)" on success, or a failure message when there are none.
    return cmd(server, f"execute if entity @e[type={NS}:tuners_protector]", 0.5)


def alive(reply: str) -> bool:
    low = reply.lower()
    if "unknown" in low or "unable to parse" in low:
        raise SystemExit(f"FAILED: command not understood by the server: {reply}")
    return "test passed" in low or "found 1" in low or "found" in low and "0" not in low


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

    # ---- 1. the negative case: body with NO legs must NOT build -----------
    clear_area(server)
    build_body(server, legs=False)
    cmd(server, f"setblock {OX} {OY+2} {OZ} {NS}:tuners_mask", 0.8)
    reply = count_protectors(server)
    if alive(reply):
        failures.append("an INCOMPLETE body (no legs) still built a protector - "
                        "the pattern is matching something looser than it should")
    else:
        print("  incomplete body correctly builds nothing")

    # ---- 2. the real case -------------------------------------------------
    clear_area(server)
    build_body(server, legs=True)
    # the mask goes on last, which is what fires onPlace
    cmd(server, f"setblock {OX} {OY+2} {OZ} {NS}:tuners_mask", 1.2)
    reply = count_protectors(server)
    if not alive(reply):
        failures.append(f"the full pattern did NOT build a protector (reply: {reply.strip()[:200]})")
    else:
        print("  full pattern builds a protector")

        # ---- 3. the pattern blocks must be consumed ----------------------
        left = cmd(server, f"execute if block {OX-1} {OY+1} {OZ} {NS}:null_iron_block", 0.4)
        if alive(left):
            failures.append("the torso block was left behind - the pattern blocks "
                            "are not being cleared")
        else:
            print("  pattern blocks consumed")

    cmd(server, f"kill @e[type={NS}:tuners_protector]", 0.3)
    server.stop()

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: the Tuner's Mask builds a Tuner's Protector, and only from the "
          "complete body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

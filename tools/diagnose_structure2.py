"""
Structure diagnostic, second pass.

Rather than hunting the world for blocks, this asks the game to place the pieces
directly. Each /place variant fails with a specific message, so whichever one
breaks tells us exactly which layer is at fault:

  /place template  - can the .nbt be found and read at all?
  /place jigsaw    - does the pool assemble and connect?
  /place structure - does the whole structure feature place?

Run:  python tools/diagnose_structure2.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from test_tps import Server, ensure_eula, ensure_server_properties  # noqa: E402

DIM = "echoing_void:the_hollow_horizon"

COMMANDS = [
    ("forceload", f"execute in {DIM} run forceload add -64 -64 64 64"),
    ("wait", None),
    ("template: resonance_forge",
     f"execute in {DIM} run place template echoing_void:outpost_of_the_tuners/resonance_forge 0 140 0"),
    ("template: connecting_chain_bridge",
     f"execute in {DIM} run place template echoing_void:outpost_of_the_tuners/connecting_chain_bridge 40 140 0"),
    ("template: observatory_dome",
     f"execute in {DIM} run place template echoing_void:outpost_of_the_tuners/observatory_dome 60 140 0"),
    ("template: sound_vault",
     f"execute in {DIM} run place template echoing_void:outpost_of_the_tuners/sound_vault 80 140 0"),
    ("jigsaw from start pool",
     f"execute in {DIM} run place jigsaw echoing_void:outpost_of_the_tuners/start "
     f"echoing_void:forge_exit 7 0 170 0"),
    ("structure feature",
     f"execute in {DIM} run place structure echoing_void:outpost_of_the_tuners 0 200 0"),
]


def main() -> int:
    if not ensure_eula(True):
        return 1
    ensure_server_properties()

    server = Server("-v" in sys.argv)
    server.start()
    if not server.wait_for_boot(900):
        print("FAILED: server did not boot")
        server.stop()
        return 1
    print("  server up")
    time.sleep(3)

    marks: list[tuple[str, int]] = []
    for label, cmd in COMMANDS:
        if cmd is None:
            print("  waiting for chunk generation")
            time.sleep(25)
            continue
        marks.append((label, len(server.transcript)))
        server.send(cmd)
        time.sleep(3.5)

    time.sleep(5)
    marks.append(("end", len(server.transcript)))

    print("\n--- results ---")
    for i in range(len(marks) - 1):
        label, start = marks[i]
        _, end = marks[i + 1]
        lines = [ln for ln in server.transcript[start:end]
                 if "]: " in ln and "Saving" not in ln]
        reply = " | ".join(ln.split("]: ", 1)[1].strip() for ln in lines[-3:]) or "(no reply)"
        print(f"  {label:<34} -> {reply[:180]}")

    server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

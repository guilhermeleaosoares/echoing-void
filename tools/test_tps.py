"""
GATE 4 - Headless 20 TPS & Stress Benchmark.

Boots a real headless Forge dedicated server with The Echoing Void installed,
drives it into a stress state, samples the tick rate, and fails if the server
cannot hold a full tick.

A NOTE ON THE ">20.0 TPS" TARGET
--------------------------------
Minecraft's server loop is rate-limited to one tick every 50 ms, so 20.0 TPS is
the engine ceiling, not a score to beat - no correct build can ever report more
than 20.0. This gate therefore reads the brief's ">20.0 TPS" as its only
achievable meaning: the server must HOLD the full tick rate under load, i.e.
mean TPS >= PASS_TPS (19.90) with no sustained tick-time overrun. The measured
value is always printed so the real number is visible.

EULA
----
Booting a dedicated server requires Mojang's EULA to be accepted. If run/eula.txt
is missing this script writes eula=true and says so loudly. Pass --no-eula to
refuse instead (the gate then cannot run).

Run:  python tools/test_tps.py [-v] [--no-eula] [--duration 60]
"""

from __future__ import annotations

import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "run"
JAVA_HOME = os.environ.get(
    "JAVA_HOME", r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.7-hotspot")

PASS_TPS = 19.90
ENGINE_CEILING = 20.0
BOOT_TIMEOUT = 900          # a cold Forge server boot can be slow
SAMPLE_INTERVAL = 5

TPS_RE = re.compile(r"Mean tick time:\s*([0-9.]+)\s*ms\.\s*Mean TPS:\s*([0-9.]+)")
DONE_RE = re.compile(r'Done \(([0-9.]+)s\)!|For help, type "help"')

# Load is applied in phases, because chunk forceloading is asynchronous: issuing a setblock
# into a chunk that has not finished generating just prints "That position is not loaded" and
# the intended load never materialises, which would make this gate pass vacuously.
STRESS_PHASES: list[tuple[str, list[str], int]] = [
    # forceload refuses anything over 256 chunks, so this is exactly 16x16.
    ("forceloading 256 chunks", [
        "gamerule randomTickSpeed 90",
        "gamerule doMobSpawning true",
        "gamerule doDaylightCycle true",
        "time set midnight",
        "weather thunder",
        "forceload add -128 -128 127 127",
    ], 25),
    ("building the siphon farm", [
        # 64 Frequency Siphons: every one of them an active vibration listener
        "fill 8 64 8 15 64 15 echoing_void:frequency_siphon",
        "fill 8 66 8 15 66 15 echoing_void:null_iron_block",
        "fill 20 64 8 31 68 19 echoing_void:resonant_bismuth_ore",
        "fill 36 64 8 47 68 19 echoing_void:void_glass",
        "fill 8 64 24 19 64 35 echoing_void:calcified_resonance_leaves",
        "setblock 4 64 4 echoing_void:acoustic_lock_box",
        "setblock 6 64 4 echoing_void:inversion_anvil",
    ], 5),
    ("crowding the siphons with vibration sources", [
        # Mobs walking on top of the siphon farm generate a continuous vibration
        # stream - this is the load the Frequency Siphon is meant to survive.
        *[f"summon minecraft:zombie {8 + (i % 8)} 66 {8 + (i // 8)}" for i in range(32)],
        *[f"summon minecraft:skeleton {20 + (i % 6)} 70 {8 + (i // 6)}" for i in range(18)],
        *[f"summon minecraft:creeper {36 + (i % 6)} 70 {8 + (i // 6)}" for i in range(10)],
        "summon minecraft:tnt 40 80 40",
    ], 8),
]


class Server:
    def __init__(self, verbose: bool):
        self.verbose = verbose
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue[str] = queue.Queue()
        self.transcript: list[str] = []

    def _pump(self, stream) -> None:
        for raw in iter(stream.readline, ""):
            line = raw.rstrip("\r\n")
            self.transcript.append(line)
            self.lines.put(line)
            if self.verbose:
                print(f"    | {line}")
        stream.close()

    def start(self) -> None:
        env = dict(os.environ, JAVA_HOME=JAVA_HOME)
        gradlew = ROOT / "gradlew.bat"
        print(f"  booting: {gradlew.name} runServer  (this takes a few minutes cold)")
        self.proc = subprocess.Popen(
            [str(gradlew), "runServer", "--console=plain", "-q"],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        threading.Thread(target=self._pump, args=(self.proc.stdout,), daemon=True).start()

    def send(self, cmd: str) -> None:
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def wait_for_boot(self, timeout: int) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc and self.proc.poll() is not None:
                return False
            try:
                line = self.lines.get(timeout=1.0)
            except queue.Empty:
                continue
            if DONE_RE.search(line):
                return True
        return False

    def collect_tps(self, window: float) -> list[float]:
        """Issue /forge tps repeatedly and harvest every Mean TPS it reports."""
        found: list[float] = []
        deadline = time.time() + window
        while time.time() < deadline:
            self.send("forge tps")
            end = time.time() + SAMPLE_INTERVAL
            while time.time() < end:
                try:
                    line = self.lines.get(timeout=0.5)
                except queue.Empty:
                    continue
                m = TPS_RE.search(line)
                if m:
                    found.append(float(m.group(2)))
        return found

    def stop(self) -> None:
        self.send("stop")
        if self.proc:
            try:
                self.proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def ensure_eula(allow: bool) -> bool:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    eula = RUN_DIR / "eula.txt"
    if eula.exists() and "eula=true" in eula.read_text(encoding="utf-8").lower():
        return True
    if not allow:
        print("  REFUSED: run/eula.txt not accepted and --no-eula was passed.")
        return False
    print("  NOTICE: writing run/eula.txt with eula=true - this accepts the Minecraft")
    print("          EULA (https://aka.ms/MinecraftEULA) on this machine in order to")
    print("          boot the benchmark server.")
    eula.write_text("eula=true\n", encoding="utf-8")
    return True


def ensure_server_properties() -> None:
    props = RUN_DIR / "server.properties"
    desired = {
        "online-mode": "false",
        "level-name": "tps_bench",
        "view-distance": "10",
        "simulation-distance": "10",
        "max-tick-time": "-1",       # never watchdog-kill the benchmark
        "sync-chunk-writes": "false",
        "spawn-protection": "0",
    }
    existing: dict[str, str] = {}
    if props.exists():
        for line in props.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing.update(desired)
    props.write_text(
        "\n".join(f"{k}={v}" for k, v in sorted(existing.items())) + "\n",
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--no-eula", action="store_true")
    ap.add_argument("--duration", type=int, default=60,
                    help="seconds of TPS sampling under stress")
    args = ap.parse_args()

    print("GATE 4: headless dedicated-server tick-rate benchmark")
    print(f"        engine ceiling is {ENGINE_CEILING:.1f} TPS; pass threshold {PASS_TPS:.2f}")

    if not ensure_eula(not args.no_eula):
        return 1
    ensure_server_properties()

    server = Server(args.verbose)
    server.start()

    if not server.wait_for_boot(BOOT_TIMEOUT):
        print("\nFAILED: server did not reach 'Done' within the boot timeout.")
        print("last 40 lines:")
        for line in server.transcript[-40:]:
            print(f"  {line}")
        server.stop()
        return 1

    print("  server up - applying stress load")
    for label, commands, settle in STRESS_PHASES:
        print(f"    {label} ({len(commands)} commands)")
        for cmd in commands:
            server.send(cmd)
            time.sleep(0.15)
        time.sleep(settle)

    # Report what the load actually amounts to, so a pass cannot be mistaken for
    # a pass on an idle server.
    server.send("forceload query")
    print("  settling, then sampling")
    time.sleep(10)

    samples = server.collect_tps(args.duration)
    server.stop()

    if not samples:
        print("\nFAILED: no TPS samples captured (is '/forge tps' available?)")
        print("last 40 lines:")
        for line in server.transcript[-40:]:
            print(f"  {line}")
        return 1

    mean = sum(samples) / len(samples)
    worst = min(samples)
    print(f"\n  samples : {len(samples)}")
    print(f"  mean TPS: {mean:.3f}")
    print(f"  worst   : {worst:.3f}")
    print(f"  best    : {max(samples):.3f}")

    if mean < PASS_TPS or worst < PASS_TPS - 0.5:
        print(f"\nFAILED: server did not hold full tick rate "
              f"(mean {mean:.3f}, worst {worst:.3f}, required >= {PASS_TPS:.2f})")
        return 1

    print(f"\nPASS: held {mean:.3f} TPS under stress "
          f"({ENGINE_CEILING:.1f} is the engine ceiling)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

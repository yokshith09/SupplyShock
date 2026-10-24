"""Run D2's four agents (Sentinel, Exposure, Sourcing, Strategy) in one service. Owner: D2.

    python scripts/run_d2_agents.py

Seeds the ERP database if it is missing, starts each agent as its own process and restarts
any that exit. Use this as the start command of one always-on host (Railway / Render worker / VM).
Agents use their mailbox (connect each once via the Agentverse inspector), so no public port is needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ["sentinel", "exposure", "sourcing", "strategy"]
RESTART_DELAY_S = 5


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from data import db, seed_generator

    if not db.db_path().exists():
        print(f"Seeding {seed_generator.build()}", flush=True)

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    procs: dict[str, subprocess.Popen] = {}

    def start(name: str) -> None:
        procs[name] = subprocess.Popen([sys.executable, "-m", f"agents.{name}.agent"], cwd=ROOT, env=env)
        print(f"started {name} (pid {procs[name].pid})", flush=True)

    for name in AGENTS:
        start(name)
    try:
        while True:
            time.sleep(RESTART_DELAY_S)
            for name, proc in list(procs.items()):
                if proc.poll() is not None:
                    print(f"{name} exited with {proc.returncode}; restarting", flush=True)
                    start(name)
    except KeyboardInterrupt:
        for proc in procs.values():
            proc.terminate()


if __name__ == "__main__":
    main()

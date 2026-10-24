"""One-command start for hosting the SupplyShock Orchestrator.

    python scripts/run_all.py            # seed DB if missing, check settings, run the agent (Ctrl+C to stop)
    python scripts/run_all.py --check    # same checks, print the agent address, do NOT start

The five services (Sentinel, Exposure, Sourcing, Strategy, Action) run inside this process
(DISPATCH_LOCAL_AGENTS). The address is derived from ORCH_SEED: use the SAME seed as the original
deployment to keep the same Agentverse address, profile and shared chat.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

EXPECTED_ADDRESS = "agent1qgt7x0cakv0htfapv9yecj8mqw28jsyramh03aqztfquzlavcadc7nczfdz"
FIVE = "sentinel,exposure,sourcing,strategy,action"


def ensure_db() -> None:
    from data.db import db_path
    if db_path().exists():
        print(f"[ok]   ERP database present: {db_path()}")
        return
    print("[do]   ERP database missing, seeding it ...")
    subprocess.run([sys.executable, str(ROOT / "data" / "seed_generator.py")], check=True)


def check_env() -> bool:
    ok = True
    if not os.getenv("ORCH_SEED", "").strip():
        print("[FAIL] ORCH_SEED is not set. Use the SAME seed as the original deployment, "
              "otherwise the agent gets a different address.")
        ok = False
    else:
        print("[ok]   ORCH_SEED is set")
    if os.getenv("REPLAY_MODE", "").lower() != "true":
        print("[warn] REPLAY_MODE is not 'true': the demo will call live GDACS, which is slow/unreliable")
    local = {a.strip() for a in os.getenv("DISPATCH_LOCAL_AGENTS", "").split(",") if a.strip()}
    missing = set(FIVE.split(",")) - local
    if missing:
        print(f"[warn] DISPATCH_LOCAL_AGENTS lacks {sorted(missing)}: those steps will use fixtures, not real services. "
              f"Recommended: DISPATCH_LOCAL_AGENTS={FIVE}")
    else:
        print("[ok]   all five services run for real")
    for k in ("RESEND_API_KEY", "RFQ_FROM_EMAIL", "DEMO_SUPPLIER_INBOX"):
        print(f"[ok]   {k} is set" if os.getenv(k, "").strip() else
              f"[warn] {k} is empty: the Action agent will return drafts instead of sending email")
    return ok


def main() -> int:
    check_only = "--check" in sys.argv
    ensure_db()
    if not check_env():
        return 2
    from agents.orchestrator.agent import agent  # imported late so .env is already loaded
    print(f"[info] agent address: {agent.address}")
    if agent.address != EXPECTED_ADDRESS:
        print("[warn] this is NOT the address in the README/Agentverse profile "
              f"({EXPECTED_ADDRESS}). Check ORCH_SEED matches the original.")
    if check_only:
        return 0
    print("[run]  starting the Orchestrator (Ctrl+C to stop). If the log says 'mailbox not found', "
          "open the inspector link it prints and click Connect -> Mailbox.")
    agent.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

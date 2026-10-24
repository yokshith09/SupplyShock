# Hosting the SupplyShock Orchestrator (handoff to D2)

The Orchestrator is one process. Sentinel, Exposure, Sourcing, Strategy and Action run **inside** it, so this is the only thing that has to stay running for the demo to work in ASI:One.

## The one rule: keep the same address
The agent's address comes from `ORCH_SEED`. Use the **same seed** as the original deployment and the agent keeps
`agent1qgt7x0cakv0htfapv9yecj8mqw28jsyramh03aqztfquzlavcadc7nczfdz`, so the Agentverse profile, README and shared chat keep working. A different seed means a new address, a new profile and a new shared chat.
**Only one process may run with that seed at a time.** Stop the old one (Ctrl+C) before or right after the new one is up.

## Secrets (share privately, never in git or public chat)
You need the original `.env` values: `ORCH_SEED`, `RESEND_API_KEY`, `RFQ_FROM_EMAIL`, `DEMO_SUPPLIER_INBOX`. Ask D1 to send them privately. `.env` is git-ignored.

## Steps (Windows PowerShell; macOS/Linux in brackets)
```bash
git clone https://github.com/yokshith09/SupplyShock.git
cd SupplyShock
git checkout main
python -m venv .venv
.venv\Scripts\activate            # [source .venv/bin/activate]
pip install -r requirements.txt
copy .env.example .env            # [cp .env.example .env]  then paste the real values into .env
```
Set these in `.env` (besides the secrets above):
```
REPLAY_MODE=true
DISPATCH_LOCAL_AGENTS=sentinel,exposure,sourcing,strategy,action
```
Check everything without starting (it seeds the demo database if missing and prints the address):
```bash
python scripts/run_all.py --check
```
You should see `[ok]` lines and `agent address: agent1qgt7x0...czfdz`. If it prints a different address, `ORCH_SEED` is wrong. If it says `[FAIL] ORCH_SEED is not set`, fill `.env`.

Start it:
```bash
python scripts/run_all.py
```
Leave it running. Expected log: "Starting server on http://0.0.0.0:8000", "Agent registration status updated to active", "Manifest published successfully: AgentChatProtocol".
If it says **"Agent mailbox not found"**, open the inspector link it prints, sign in to Agentverse, click **Connect -> Mailbox**, and restart. (The mailbox belongs to the Agentverse account that connected the agent; ask D1 if the agent was connected under their account.)

## Keep it alive
- **Windows PC:** disable sleep while plugged in (`powercfg /change standby-timeout-ac 0`), keep the terminal window open.
- **Linux server:** `nohup python scripts/run_all.py > orchestrator.log 2>&1 &` or a systemd service.
- If port 8000 is busy, set `ORCH_PORT=8010` in `.env` (the mailbox works on any port).

## Verify
1. In ASI:One (Agents enabled), chat with the agent and send: `Cyclone warning on the Tamil Nadu coast, are we exposed?`
2. Expect the exposure text and an options carousel. Select OPT-C, review, approve. An email should land in `DEMO_SUPPLIER_INBOX`.
3. Only then tell D1 to stop their own copy.

## Not included
No Docker/cloud deploy files are provided or tested. The Orchestrator is a normal Python process; any always-on machine works.

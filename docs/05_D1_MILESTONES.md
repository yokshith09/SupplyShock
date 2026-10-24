# D1 — What We Build, Rules, Milestones & Prompts

> **Final outcome (24 Oct):** M0-M4 done and verified (hello agent, intents/planner/mock dispatch, executor/local dispatch/store, Action agent with real email, cards and approval in ASI:One). M5 reduced to: merge d1+d2 into main, README, shared chat, submission. Hosting, Payment Protocol and Watchtower were cut. See [06_FINAL_STATUS.md](06_FINAL_STATUS.md).

> Owner: **D1 (Conversation & Execution)**. Event day: 24 Oct 2026, submit by **17:50 IST**.
> Status: FINAL (13:15 IST). Times shifted +25 min from the first draft because M0 started late; M5/M6 unchanged.
> Source of truth: [04_TEAM_PLAN.md](04_TEAM_PLAN.md) §B (tasks), §E (contracts), [TRD](TRD.md), [PRD](PRD.md). Hackpack: https://innovationlab.fetch.ai/events/hackathons/fetch-a-thon-3/hackpack

## 1. What D1 builds (in one paragraph)
Everything the user sees and every outward action. The **Orchestrator** agent speaks the Agent Chat Protocol to ASI:One, understands intent, builds a plan, calls D2's specialists (Sentinel, Exposure, Sourcing, Strategy), shows results as Interactive Cards, takes the user's approval, and hands the approved option to the **Action** agent, which really sends RFQ/expedite emails and generates a PO PDF. D1 also owns deployment (always-on), Agentverse profiles, the README, the shared chat, the demo video and the submission.

## 2. Hackpack requirements D1 is responsible for
| Mandatory requirement | D1 deliverable |
|---|---|
| Agent registered on Agentverse | Orchestrator + Action (+ D2's agents registered by D2) |
| Agent Chat Protocol | `agents/orchestrator/agent.py` with `chat_protocol_spec` |
| Discoverable and usable in ASI:One | `README_AGENTVERSE.md` with keywords + example prompts |
| Meaningful tool execution / multi-agent orchestration | Planner + executor + dispatch, real emails + PDF |
| Whole workflow inside ASI:One | Cards + text fallback, no frontend |
| Public repo with run instructions | README quick start, `.env.example`, badges |
| Badges `tag:innovationlab` + `tag:hackathon` | Already in README; also put them in **every** Agentverse README |
| Always-on agents | `deploy/` + hosting before 16:30 |
| Demo video **3–5 min**, shared chat URL, description, dashboard submission | M6 |

## 3. Rules (apply to every milestone)
1. Edit only D1-owned paths (04_TEAM_PLAN §B.1). Contract changes go in `shared/models.py` and must be additive and agreed with D2.
2. No outward action (email/PO/payment) without explicit user approval on a card.
3. All demo emails go to `DEMO_SUPPLIER_INBOX`. Never real suppliers.
4. Money fields end in `_inr`, distances `_km`, durations `_days`/`_s`. Every request/response carries `incident_id` and `task_id`.
5. Every card has a non-empty text fallback.
6. Secrets only in `.env` (git-ignored). Never print keys.
7. Verify `uagents` / `uagents-core` / card / payment APIs against the installed package and the Fetch.ai docs, not memory.
8. Small commits, pull before push, run only the narrowest relevant tests.
9. Collision rules with D2: never create or edit `tests/fixtures/contracts/`, `data/` (except `data/migrations/2xx_*`), `shared/llm.py`, `shared/geo.py` or `requirements/analytics.txt` content. Stage only your own paths (`git add <paths>`, never `git add -A`), work only on branch `d1` (see 4d), `git pull --rebase origin d1` before every push, and push `shared/models.py` to `d1` within minutes of M0 so D2 can copy it (D2's T0 fixtures wait on it).
10. Anything not needed for the demo flow waits. Payment and Watchtower are stretch.

## 4. Milestones (one after the other; do not start the next until the gate passes)

| # | Time (IST) | Milestone | D1 tasks | Gate (must be true to move on) |
|---|---|---|---|---|
| **M0** | 13:15–13:50 | Skeleton + hello agent live in ASI:One | 0.1, 0.2, 0.4, D1-1 | Message typed in ASI:One gets an echo reply from your Orchestrator on Agentverse |
| **M1** | 13:50–14:30 | Brain: intents, session, template plans, mock dispatch | D1-2, 3, 4, 6 | `chat_cli.py` runs the EVENT_IMPACT text flow end to end in `mock` mode; tests green |
| **M2** | 14:30–15:10 | Executor + first real specialist | D1-5, store.py, logging | Flow runs in `local` mode with D2's real Sentinel (due ~14:50) while other tasks stay `mock`; timeout/retry/degraded tests green |
| **M3** | 15:10–15:50 | Action agent sends real emails | D1-10 | Approving an option sends RFQ/expedite emails to the demo inbox and writes a PO PDF; `ActionReceipt` correct |
| **M4** | 15:50–16:30 | Cards + approval routing in ASI:One | D1-7, D1-8, Agentverse READMEs | Cards work in ASI:One using real Exposure (due ~15:25) and Sourcing (~15:45); Strategy is real from ~16:05, mock before; clicking Approve triggers M3 |
| **M5** | 16:30–17:10 | Always-on + remote + shared chat | D1-12 | Agents hosted; `remote` mode works (D2's agents register ~16:35; if not, the hosted Orchestrator runs D2 services in `local` mode); a full run recorded as a public ASI:One shared chat |
| **M6** | 17:10–17:50 | Video + submit | D1-13 | 3–5 min video; dashboard submission accepted; every link opens while logged out |
| *Stretch* | only if M4 done early | Payment (D1-9), Watchtower (D1-11) | | Never at the cost of M5/M6 |

## 4b. Final D1 task list (every D1 task has exactly one milestone)

| Task | What | Milestone | Done when |
|---|---|---|---|
| 0.1 / 0.2 | Skeleton, `shared/models.py`, `shared/constants.py` | M0 | models on `main`; imports work |
| D1-1 | Orchestrator + Chat Protocol + mailbox + Agentverse | M0 | echo reply in ASI:One |
| D1-2 | `session.py` | M1 | state survives between messages |
| D1-3 | `intents.py` + `prompts.py` (ASI1 + keyword fallback) | M1 | 6 intents classify; works without API key |
| D1-4 | `planner.py` (template plan first, LLM plan optional) | M1 | `build_plan(intent)` returns a valid Plan |
| D1-6 | `shared/dispatch.py` (mock; local added in M2; remote in M5) | M1/M2/M5 | same code runs in all 3 modes |
| `scripts/chat_cli.py` | local text chat | M1 | full text flow in mock mode |
| D1-5 | `executor.py` + `dispatcher.py` + `store.py` + `shared/logging.py` | M2 | parallel, timeout, retry, degraded, HUMAN gate tests green |
| D1-10 | Action agent: emails, PDF, receipt | M3 | real emails in demo inbox |
| D1-7 | `cards.py` + text fallbacks | M4 | cards render in ASI:One |
| D1-8 | card-response routing | M4 | Approve triggers Action |
| Agentverse READMEs (Orchestrator, Action) | badges, keywords, prompts | M4 | profiles discoverable |
| D1-12 | `run_all.py`, deploy, remote dispatch, `config/agents.json`, README run steps | M5 | works with laptop off |
| D1-13 | shared chat, video (3-5 min), description, submission | M6 | dashboard accepted |
| D1-9 / D1-11 | Payment / Watchtower | Stretch | only if M4 done before 16:00 |

## 4c. Handshake with D2 (so nothing collides)

| D2 task (their time) | What D1 needs from it | D1 action |
|---|---|---|
| T0 fixtures (to 13:30) | needs your `shared/models.py` | push models.py to `main` first thing in M0 |
| T1 `shared/llm.py` (13:45) | ASI1 client for intents | M1 uses a keyword stub; switch to `complete_json` after it merges |
| T2 `data/db.py` (14:10) | `get_supplier`, `get_connection` | M2 `store.py` and M3 Action rely on it |
| T3 Sentinel (14:50) | first real specialist | M2 gate |
| T4 Exposure (15:25), T5 Sourcing (15:45), T6 Strategy (16:05) | real data for cards/options | M4 swaps mock for real as each merges |
| T7 agents registered (16:35) | their 4 Agentverse addresses | put in `config/agents.json`; if late, local fallback |
| T8 integration (16:35-17:30) | fixes on their side | D1 leads M5 integration |

Ownership never overlaps: D1 = `agents/orchestrator`, `agents/action`, `agents/watchtower`, `shared/{models,constants,config,logging,dispatch}.py`, `scripts/{run_all,chat_cli}.py`, `deploy/`, `config/`, root README, `requirements.txt`, `pyproject.toml`, `.gitignore`, `.env.example`, `data/migrations/2xx_*`. D2 owns everything else; ask in chat before touching a D2 path.

## 4d. Branch workflow (decided: two long-lived branches, merged into `main` at checkpoints)

- D1 works only on branch **`d1`**, D2 only on **`d2`**. `main` holds docs until the first checkpoint merge.
- Ownership is disjoint (4c), so merging `d1` and `d2` should be conflict-free. Shared files each have one owner; the other side never edits them.
- **Checkpoint merges** (D1 does them, D2 confirms): after M2 (about 15:10), after M4 (about 16:30), final at M5 start. Steps: `git fetch origin`, `git checkout main`, `git pull`, `git merge origin/d2`, `git merge origin/d1`, run `pytest`, `git push origin main`, then both `git rebase origin/main` (or merge main) on their branches.
- **Cross-branch needs before a merge:** D2 needs `shared/models.py` and `shared/constants.py` from `d1` (copy with `git checkout origin/d1 -- shared/models.py shared/constants.py` into the `d2` working tree, then drop it before committing, or wait for the checkpoint). D1 needs fixtures, `data/db.py` and the D2 services from `d2` (same read-only copy: `git checkout origin/d2 -- <path>`, and do not commit those paths on `d1`).
- No force-push. Never merge a branch into `main` without running `pytest`.
- Final: tag after the last merge, and the public repo's `main` is what goes in the submission.

If a milestone slips by more than 20 minutes, cut scope inside it (text instead of a card, one email instead of three) rather than moving the gate.

## 5. Prompts (paste into Claude Code opened in the repo folder)

### Prompt 0: context, paste once at the start
```
We are D1 in the SupplyShock repo for Fetch-A-Thon 3.0 (deadline today 17:50 IST). Read docs/04_TEAM_PLAN.md (§B, §E), docs/TRD.md, docs/PRD.md and docs/05_D1_MILESTONES.md. You only edit D1-owned paths. Rules: contracts in shared/models.py are additive only; money fields end in _inr; every message carries incident_id and task_id; no outward action without approval; demo emails go to DEMO_SUPPLIER_INBOX; secrets only in .env; every card has a text fallback. Verify uagents/uagents-core APIs from the installed package and Fetch.ai docs (https://innovationlab.fetch.ai), not memory. Keep code minimal, run only narrow tests, report Changed | Verified | Remaining. Confirm you understand, then wait for the milestone prompt.
```

### M0 prompt
```
Milestone M0. Create the minimal skeleton for D1 paths only (agents/orchestrator, agents/action, shared/, scripts/, deploy/, tests/orchestrator, pyproject.toml, .gitignore with .env and *.db, requirements/orchestration.txt, a placeholder requirements/analytics.txt containing only a comment so `-r` works, root requirements.txt with the two -r lines, pinned uagents/uagents-core versions, and .env.example with the two marked blocks `# --- D1: orchestration ---` and `# --- D2: analytics ---`). Do NOT create data/, tests/fixtures/ or any D2 folder; D2 creates them. Work on branch d1. Commit and push shared/models.py to origin/d1 as soon as it is written because D2's fixtures depend on it. Write shared/models.py (all schemas from TRD §5, envelope rules from §E.1) and shared/constants.py (§E.2). Then build agents/orchestrator/agent.py: a uAgent with mailbox=True that includes chat_protocol_spec (publish_manifest=True), acknowledges every ChatMessage, and replies with an echo plus the text "SupplyShock online". Add a short README_AGENTVERSE.md with the two badges (tag:innovationlab, tag:hackathon), keywords and 3 example prompts. Give me the exact commands to install, run, and connect the mailbox to Agentverse so I can test it from ASI:One. Gate: echo reply visible in ASI:One.
```

### M1 prompt
```
Milestone M1. Build in agents/orchestrator: session.py (per-sender state: active incident, plan state, last options), intents.py + prompts.py (ASI1 classification into the 6 Intents with entity extraction, and a keyword fallback that works with no API key), planner.py (template plan per intent first; LLM JSON plan validated by pydantic is optional, falls back to the template). Build shared/dispatch.py with DISPATCH_MODE=mock loading tests/fixtures/contracts/<ResponseType>.json reading D2's fixtures from tests/fixtures/contracts/ (fetch origin/d2 and copy the files you need read-only, or wait for the checkpoint merge; if they are not available yet, put temporary D1-only fixtures in tests/orchestrator/fixtures/ matching the demo story: 3 suppliers, 12 orders, ₹1.82 Cr, 3 options with OPT-C recommended, and never touch tests/fixtures/). Build scripts/chat_cli.py to run the full EVENT_IMPACT text flow locally. Add tests/orchestrator for intents, planner and dispatch. Gate: chat_cli completes the flow in mock mode and pytest tests/orchestrator passes.
```

### M2 prompt
```
Milestone M2. Build executor.py + dispatcher.py: run the plan in dependency order with asyncio, run independent tasks in parallel, 20 s timeout, 2 retries with backoff, degraded mode (mark result degraded and continue), a re-plan hook that can append tasks, and a HUMAN gate that pauses the plan and resumes on the next user message. Add store.py (save_incident, log_action using data.db.get_connection, with an incidents/actions_log migration in data/migrations/2xx) and shared/logging.py (JSON logs with incident_id, task_id, agent, latency_ms, status). Add DISPATCH_MODE=local that imports agents.<agent>.service.handle. Tests: parallel run, timeout then retry then fallback, invalid LLM plan then template plan, HUMAN gate pause/resume. Gate: full flow works with D2's real Sentinel and Exposure in local mode; tests green.
```

### M3 prompt
```
Milestone M3. Build the Action agent in agents/action: service.py handle(ActionRequest)->ActionReceipt executing each Option.actions item (rfq_email, expedite_email, draft_po, customer_notice per §E.4), email_sender.py (Resend API or SMTP from env; ALL mail goes to DEMO_SUPPLIER_INBOX with the real supplier name in the body), po_pdf.py (reportlab PO-2026-xxxx), templates/ for RFQ, expedite and customer notices (ASI1 may draft the body, with a static template fallback). Use data.db functions for supplier lookups, never raw SQL. Per-action status in {done, failed, draft}; if email fails, retry once then return a draft with the copy-ready text. Wrap it as a uAgent with the Chat Protocol and register it on Agentverse. Tests with a fake email transport and a non-empty PDF check. Gate: approving option C sends real emails to the demo inbox and returns a correct receipt.
```

### M4 prompt
```
Milestone M4. First check the ASI1 Interactive Cards docs (https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards) and the installed uagents-core for the exact card payload and button-response format, then do a hello-card test in ASI:One. Then build cards.py: plan, event, exposure, options carousel, approval and receipt builders. Each takes a response model and returns (card_payload, text_fallback), and the fallback is never empty. Add card-response routing in the Orchestrator so a button click or form submit resumes the paused plan and, on Approve, calls the Action agent. Write README_AGENTVERSE.md for Orchestrator and Action (badges, keywords, example prompts, agent name + address placeholders). Snapshot tests for cards. Gate: the full flow runs inside ASI:One through the approval and receipt cards.
```

### M5 prompt
```
Milestone M5. Make everything always-on and remote. Implement DISPATCH_MODE=remote (with automatic per-agent fallback to local if an address is missing or unreachable, so the demo cannot depend on D2's registration timing) using ctx.send with addresses from config/agents.json and replies matched by task_id. Add scripts/run_all.py and deploy/ configs for Agentverse-hosted or Render/Railway (pick the fastest path that keeps agents running without my laptop). Update the README quick start with exact run/test steps, the four agent names and Agentverse addresses, and keep both badges. Give me a checklist to deploy, plus a smoke test that sends one message to the Orchestrator and checks the receipt arrives. Gate: with my laptop's agents stopped, the flow still works in ASI:One.
```

### M6 prompt
```
Milestone M6. Prepare submission material: a 3–5 minute demo script (hook, live ASI:One flow, real email in the inbox, architecture, one fallback demonstration), the project description (problem, target users, outcome) using docs/03, and a final checklist of every deliverable: public shared-chat URL, Agentverse profile URL per submitted agent, public repo with badges and run steps, video, dashboard submission through the Project Submission Agent. Verify each link opens logged-out. Do not submit anything yourself; tell me exactly what to paste where.
```

### Stretch prompts (only if M4 finished before 16:00)
```
Stretch S1: build payment.py using the Payment Protocol from the installed uagents-core (RequestPayment, CommitPayment, CompletePayment, RejectPayment), testnet FET, behind PAYMENT_ENABLED. Block execution until CompletePayment; on reject or timeout, keep the free summary. Verify field names from the package first.
```
```
Stretch S2: build the Watchtower agent: subscribe(WatchSubscribe), check(incident_id) re-querying Sentinel every N minutes, change detection, and pushing WatchAlert to the user; plus the STATUS intent.
```

## 6. D1 end-of-day definition of done
- [ ] Orchestrator + Action registered on Agentverse, always-on, badges + address in READMEs
- [ ] Full flow in ASI:One: intent, plan, exposure, options, approval, real emails, receipt
- [ ] Public shared-chat URL, 3–5 min video, description
- [ ] Public repo with run/test instructions
- [ ] Dashboard submission verified

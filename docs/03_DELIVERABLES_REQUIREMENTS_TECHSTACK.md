# SupplyShock — Deliverables, Requirements & Tech Stack

## 1. Hackathon deliverables checklist

| # | Deliverable | What we submit | Owner | Status |
|---|---|---|---|---|
| 1 | ASI:One Shared Chat URL | One chat that runs the full flow: trigger → exposure → options → approve → pay → receipt | | ☐ |
| 2 | Agentverse Agent Profile URLs | All 7 agents (Orchestrator is the main one) | | ☐ |
| 3 | Public GitHub repo | Code, README with setup and test steps, `.env.example`, seed data | | ☐ |
| 4 | Demo video (2–3 min) | Problem (20 s) → live chat demo (2 min) → architecture and bonus features (30 s) | | ☐ |
| 5 | Project description | Problem, target users, outcome (see below) | | ☐ |
| 6 | Dashboard submission | Through the Project Submission Agent on the Fetch-A-Thon 3.0 dashboard | | ☐ |

### Short description (ready to paste)
> **SupplyShock** is a multi-agent supply-chain disruption responder for manufacturers, especially SMEs. Disruptions like cyclones, port strikes and supplier fires are usually noticed days late, and impact analysis is done by hand in spreadsheets. In one ASI:One conversation, SupplyShock's 7 agents pick up live disruptions (GDACS, GDELT, Open-Meteo), map them across the company's supplier → material → product → order graph, calculate the revenue at risk and stock-out dates, find and rank alternate suppliers, suggest scored mitigation options, and, after the user approves and pays per incident, send RFQs and expedite requests and draft POs. It then keeps watching the event. **Target users:** procurement managers, operations heads and SME owners. **Outcome:** response time cut from days to minutes, with real actions taken.

## 2. Mandatory requirement mapping

| Challenge requirement | How SupplyShock meets it |
|---|---|
| Solves a defined real-world problem | Late detection and slow response to supply disruptions |
| Multi-step planning, reasoning, orchestration | LLM-generated, validated task DAG; parallel steps; re-planning; human approval step |
| Uses tools / APIs / other agents | GDACS, GDELT, Open-Meteo, Frankfurter, email, PDF, 6 specialist agents |
| Registered on Agentverse | 7 agents, mailbox / hosted |
| Implements the Agent Chat Protocol | Orchestrator (and every specialist) includes `chat_protocol_spec` |
| Discoverable and usable in ASI:One | Rich Agentverse README with keywords and example prompts |
| Full workflow inside ASI:One | Cards for every step, text fallback, no frontend |
| Public GitHub repo | ✓ |

## 3. Bonus criteria mapping

| Bonus | Our feature |
|---|---|
| Multi-agent collaboration | 7 agents with typed contracts and correlation IDs |
| Payment Protocol + monetization | Pay-per-incident FET for execution; free analysis |
| Interactive Cards | Form, detail, review, carousel, approval, receipt |
| Reliability and error recovery | Retries, fallbacks, degraded mode, chaos-tested |
| Real-time data | GDACS, GDELT, Open-Meteo, live FX |
| Keeps running after the hackathon | Watchtower plus a clear SaaS path (ERP connectors, Pro tier) |

## 4. Prerequisites (accounts & keys)

- [ ] Agentverse account + API key — https://agentverse.ai
- [ ] ASI:One account + ASI1 API key — https://asi1.ai
- [ ] Fetch.ai wallet with testnet FET (for the Payment Protocol)
- [ ] Resend account (free tier) or a Gmail app password for SMTP
- [ ] A demo inbox (e.g. supplyshock.demo@…) acting as the "suppliers"
- [ ] GitHub repo (public)
- [ ] Optional: Render / Railway account for always-on hosting

## 5. Software requirements

- Python **3.11+**
- `pip` / `uv`
- Git

### requirements.txt (initial)
```
uagents
uagents-core
httpx
tenacity
pydantic
networkx
haversine
python-dotenv
reportlab
resend
pytest
pytest-asyncio
respx
```

## 6. Tech stack summary

| Layer | Tech |
|---|---|
| Agents | Fetch.ai **uAgents** (Python), Agentverse mailbox / hosted |
| Protocols | Agent Chat Protocol, Payment Protocol, custom task protocol |
| LLM | **ASI1** API (intent, planning, relevance, drafting) |
| Reasoning core | Deterministic Python: graph traversal (NetworkX), scoring |
| Data | SQLite seeded ERP dataset; CSV import |
| Live data | GDACS, GDELT DOC 2.0, Open-Meteo (+ geocoding), Frankfurter FX |
| Actions | Resend / SMTP email, ReportLab PDF POs, ERP webhook (stub) |
| UI | ASI1 Interactive Cards inside ASI:One (no frontend) |
| Quality | pytest, respx, structured JSON logging |
| Hosting | Agentverse hosted agents or Render / Railway with mailbox |

## 7. 3-day build plan

| Day | Tasks | Exit criteria |
|---|---|---|
| **Day 1** | Repo skeleton, shared models, seed data; Orchestrator with Chat Protocol on Agentverse; Sentinel (GDACS + Open-Meteo); Exposure; "hello card" test | "Are we exposed to Chennai cyclone?" returns a text exposure report in ASI:One |
| **Day 2** | Planner + DAG executor; Sourcing; Strategy; Action (email + PDF); all cards; GDELT | Full flow works up to the receipt |
| **Day 3** | Payment Protocol; Watchtower; failure handling and chaos test; Agentverse READMEs; replay mode; demo video; submission | Shared chat URL recorded, everything submitted |

## 8. Demo script (video)
1. **Hook (15 s):** "In Dec 2023 Cyclone Michaung shut down Chennai's auto belt. Most suppliers' customers found out days later."
2. **Ask (ASI:One):** "Cyclone warning on the Tamil Nadu coast, are we exposed?"
3. Show the plan card → event card → exposure card (₹ at risk, stock-out date).
4. Options carousel → pick C → approval → pay 0.5 FET.
5. Receipt → switch to the inbox showing the real RFQ emails.
6. "Update on Chennai?" → Watchtower status.
7. **Architecture slide:** 7 agents, a recovery demo (Sourcing killed → degraded but completed).

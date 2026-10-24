# SupplyShock — Product Requirements Document (PRD)

| Field | Value |
|---|---|
| Product | SupplyShock: Supply-Chain Disruption Response Agents |
| Event | Fetch-A-Thon 3.0, ASI:One Agent Challenge |
| Version | 1.0 (Hackathon MVP) |
| Date | 2026-10-24 |
| Status | Draft |

---

## 1. Overview
SupplyShock helps manufacturers, especially SMEs, find supply-chain disruptions early and respond to them, all inside an ASI:One conversation. A team of specialist agents detects real-world events, calculates the effect on the company's suppliers, materials and orders, suggests ranked mitigation options, and carries out the approved plan.

## 2. Goals & non-goals

### Goals
- G1: Go from a user's question about a disruption to a **quantified exposure report in under 2 minutes**.
- G2: Go from exposure to **executed actions (RFQs, expedite request, draft PO)** in the same chat.
- G3: Show **real multi-agent orchestration** with planning, parallel tasks, recovery and human approval.
- G4: A **credible monetization model** through the Payment Protocol.
- G5: Run the entire primary workflow in **ASI:One with Interactive Cards** and no custom frontend.

### Non-goals (MVP)
- Live integration with SAP or Oracle ERP (a seeded dataset and a CSV upload stand in).
- Multi-tier (Tier-2/3) supplier discovery from outside data.
- Automated price negotiation.
- Placing final, binding POs (only drafts plus emails are produced).

## 3. Target users & personas
See [01_PROBLEM_STATEMENT.md](01_PROBLEM_STATEMENT.md#2-target-users). Primary user: **procurement manager at a 50–500 employee manufacturer.**

## 4. User stories

| ID | As a… | I want to… | So that… | Priority |
|---|---|---|---|---|
| US-1 | Procurement manager | ask "are we exposed to anything right now?" | I find risks before they hit | P0 |
| US-2 | Procurement manager | ask about a specific event or location | I get my exact exposure | P0 |
| US-3 | Ops head | see which customer orders slip and when | I can re-plan production | P0 |
| US-4 | Procurement manager | see ranked alternate suppliers | I can switch quickly | P0 |
| US-5 | Manager | compare options by cost, risk and orders saved | I can justify my decision | P0 |
| US-6 | Manager | approve a plan with one click | actions get done right away | P0 |
| US-7 | Manager | have RFQs and expedite emails sent for me | I save days of work | P0 |
| US-8 | SME owner | pay only when I use the execution feature | it stays affordable | P1 |
| US-9 | Manager | get follow-up alerts if the event gets worse | I'm not caught off guard | P1 |
| US-10 | Manager | check a single supplier's risk | I can make onboarding decisions | P1 |
| US-11 | New user | upload my supplier list or BOM as CSV | I can use my own data | P2 |

## 5. Functional requirements

### FR-1 Conversation & intent (Orchestrator)
- FR-1.1 Accept natural-language messages through the Agent Chat Protocol.
- FR-1.2 Classify the intent into SCAN / EVENT_IMPACT / SUPPLIER_CHECK / SOURCE_ALT / STATUS / HELP.
- FR-1.3 Extract entities: location, event type, supplier, material, horizon.
- FR-1.4 Show the plan to the user before running long tasks.
- FR-1.5 Keep session state per user (active incident, last options).

### FR-2 Disruption detection (Sentinel)
- FR-2.1 Query GDACS for active disasters (cyclones, floods, earthquakes, volcanoes, droughts, wildfires).
- FR-2.2 Query GDELT for news on strikes, port closures, fires and sanctions near supplier locations.
- FR-2.3 Query Open-Meteo for severe weather forecasts at supplier coordinates.
- FR-2.4 Turn all of these into a standard `Event` object (type, geo, radius, severity, start, sources, confidence).
- FR-2.5 Remove duplicate events found by multiple sources.

### FR-3 Exposure analysis (Exposure)
- FR-3.1 Find suppliers within the event's impact radius (haversine distance).
- FR-3.2 Walk the graph Supplier → Material → BOM → Product → Open Order.
- FR-3.3 Calculate per material: stock on hand, daily consumption, **cover days**, and **stock-out date**.
- FR-3.4 Calculate the orders at risk and **revenue at risk** (₹, plus USD using live FX).
- FR-3.5 Give each material a severity rating (LOW / MED / HIGH / CRITICAL).

### FR-4 Alternate sourcing (Sourcing)
- FR-4.1 Find qualified alternate suppliers for each at-risk material.
- FR-4.2 Leave out suppliers that are inside the event zone.
- FR-4.3 Rank them on price, lead time, distance, quality rating and historical risk.
- FR-4.4 If none are found nearby, widen the search radius step by step.

### FR-5 Strategy (Strategy)
- FR-5.1 Generate at least 3 options from: expedite, switch, split, safety stock, production reschedule, customer delay notice.
- FR-5.2 Score each option on cost Δ, risk reduction %, orders saved and time to effect.
- FR-5.3 Mark one option as recommended and explain why in plain language.

### FR-6 Execution (Action)
- FR-6.1 Run only after the user explicitly approves on a card.
- FR-6.2 Send RFQ emails to the selected alternates.
- FR-6.3 Send an expedite request to the affected supplier.
- FR-6.4 Generate a draft PO as a PDF or JSON.
- FR-6.5 Draft customer delay or assurance notices.
- FR-6.6 Return a receipt showing the status of each action; failed actions offer a retry.

### FR-7 Monitoring (Watchtower)
- FR-7.1 Subscribe to an incident and re-check it every N minutes.
- FR-7.2 Alert the user in chat when severity, track or radius changes significantly.

### FR-8 Payment
- FR-8.1 Free: scan, event impact and exposure report.
- FR-8.2 Paid: execution (sourcing, RFQs, PO) per incident, through the Payment Protocol.
- FR-8.3 Execution is blocked until `CompletePayment` is received. A rejected payment shows a polite message and the free summary.

### FR-9 Interactive Cards
| Card | Type | Used at |
|---|---|---|
| Plan Preview | detail view | after intent |
| Event Card | detail view | after Sentinel |
| Exposure Report | review / table | after Exposure |
| Options | carousel | after Strategy |
| Approval | review + confirm button | before Action |
| Payment | payment request | before execution |
| Execution Receipt | detail view | after Action |
| Company Setup | form | onboarding / CSV upload |

Every card also has a **plain-text fallback** for clients that don't render cards.

## 6. Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | Exposure report in ≤ 60 s (p90) |
| NFR-2 | Any single external API failure must not end the workflow (degraded mode) |
| NFR-3 | No outward action without approval |
| NFR-4 | All agents always reachable through Agentverse mailbox / hosted |
| NFR-5 | Secrets kept in environment variables, never in the repo |
| NFR-6 | Every recommendation includes an explanation trace |
| NFR-7 | Agent logs are structured and keyed by incident_id |

## 7. Monetization model
| Tier | Price | Includes |
|---|---|---|
| Free | 0 | Scans, exposure reports, 1 supplier check a day |
| Pay-per-incident | small FET fee (e.g. 0.5 FET on testnet) | Sourcing + RFQs + PO + 7-day watch |
| Pro (post-hackathon) | monthly subscription | Continuous monitoring, ERP connector, team alerts |

**Why it's credible:** enterprise tools cost $100k+ a year. One avoided stock-out saves an SME lakhs of rupees, so paying per incident is an easy decision.

## 8. Success metrics (demo)
- Complete workflow in a single shared ASI:One chat in ≤ 5 minutes.
- At least 6 agents involved, with at least 1 parallel step and at least 1 recovered failure shown.
- Real emails received in the demo inbox.
- At least 1 real payment transaction on testnet.

## 9. Risks & mitigations
| Risk | Mitigation |
|---|---|
| No live disaster near seeded suppliers on demo day | "Replay mode": a recorded real past GDACS event (e.g. Cyclone Michaung, Dec 2023, Chennai) plus a live scan |
| GDELT rate limits | Cache for 15 min, fall back to GDACS-only |
| Card rendering differences | Text fallback for every card |
| LLM produces an invalid plan | Schema validation, then a template plan for that intent |

## 10. Release plan
| Phase | Scope |
|---|---|
| Day 1 | Orchestrator + Chat Protocol + Sentinel + Exposure, registered on Agentverse |
| Day 2 | Sourcing + Strategy + Action + cards |
| Day 3 | Payment, Watchtower, error handling, demo video, submission |

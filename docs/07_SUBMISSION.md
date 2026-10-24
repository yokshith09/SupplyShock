# SupplyShock — Submission Pack (Fetch-A-Thon 3.0)

Submit through the ASI:One dashboard → **Project Submission Agent**. Paste the items below. Verify every link opens while logged out.

## Links (fill in)
| Deliverable | Value |
|---|---|
| GitHub (public) | https://github.com/yokshith09/SupplyShock |
| ASI:One shared chat URL | _paste after a clean run_ |
| Agentverse profile URL (Orchestrator) | _open the agent in Agentverse, copy the page URL_ |
| Agentverse profile URL (Action, if submitted) | _optional_ |
| Demo video (3–5 min) | _paste_ |
| Orchestrator address | `agent1qgt7x0cakv0htfapv9yecj8mqw28jsyramh03aqztfquzlavcadc7nczfdz` |
| Action address | `agent1q0tl4ypgxlsdw3srtkt46g96dec0kdes4qefj5clqz70ngwytekxq0qr5v2` |

## Project description (paste this)
**SupplyShock** is a multi-agent supply-chain disruption responder for manufacturers, built on Fetch.ai uAgents, registered on Agentverse and used entirely inside ASI:One.

**Problem.** Disruptions like cyclones, port strikes and supplier fires are usually noticed days late. Procurement teams then spend days in spreadsheets working out which suppliers, materials and customer orders are exposed, and more days asking for quotes. Small and mid-size manufacturers cannot afford enterprise risk platforms.

**Target users.** Procurement managers, plant and operations heads, and SME owners.

**What the agent does.** In one ASI:One conversation, a user types something like "Cyclone warning on the Tamil Nadu coast, are we exposed?". SupplyShock plans the work and runs it with parallel steps, retries and fallbacks: it finds the event, maps it across the supplier → material → bill of materials → customer order graph, computes cover days, stock-out dates and revenue at risk (3 suppliers, 12 orders, ₹1.82 Cr in the demo), finds and ranks alternate suppliers, and generates scored response options. The user picks a plan on an interactive card carousel, reviews it on a review card and approves. Only then does the Action agent execute: it sends real RFQ and expedite emails, generates a draft purchase-order PDF and drafts customer notices, and returns a receipt card.

**Outcome.** From a one-line question to an approved, executed response plan in minutes instead of days, with every number computed in code and nothing sent without explicit approval.

**Agentverse / ASI:One features used.** Agent Chat Protocol, ASI Interactive Cards (carousel, review, detail) with full text fallbacks, mailbox registration, task-DAG orchestration with timeouts, retries, degraded-mode fallbacks and a human approval gate. 145 automated tests.

**Honest scope.** ERP data is a seeded dataset for a fictional manufacturer; the event is a recorded real cyclone replayed for a repeatable demo; emails are redirected to a controlled demo inbox. Payment Protocol and follow-up alerts are designed but not built.

## Video script (target 4 minutes)
| Time | Show | Say |
|---|---|---|
| 0:00–0:30 | Title / README | The problem: disruptions are noticed days late; analysis is manual; SMEs cannot afford enterprise tools |
| 0:30–1:00 | ASI:One chat, type the cyclone message | One sentence in, no frontend |
| 1:00–2:00 | Exposure text and options carousel | 3 suppliers, 12 orders, ₹1.82 Cr at risk; worst material M-12 has 6 days of cover; options scored on cost, risk, orders saved |
| 2:00–2:45 | Select OPT-C → review card → Approve | Nothing is sent until approval; the review card lists exactly what will happen |
| 2:45–3:30 | Receipt card, then the demo inbox with the RFQ email | Real emails, redirected to a demo inbox; PO PDF and customer notices drafted |
| 3:30–4:00 | Architecture / README / terminal log | Orchestrator plans a task DAG; Sentinel, Exposure, Sourcing, Strategy, Action; retries and fallbacks; 145 tests; seeded ERP data + replayed real event |

## Last-minute checklist
- [ ] Agent running (terminal open, laptop awake) while judges may test
- [ ] Shared chat shows the full flow: request → carousel → review → approval → receipt
- [ ] README on `main` shows both badges and agent addresses
- [ ] Agentverse profile README pasted (badges included)
- [ ] Repo is public and `main` is pushed
- [ ] Dashboard submission confirmed

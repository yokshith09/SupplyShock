# SupplyShock — Problem Statement

> **One line:** SupplyShock is a multi-agent system, used entirely inside ASI:One, that spots real-world supply-chain disruptions as they happen, works out exactly which of a manufacturer's suppliers, materials and customer orders are at risk, and turns that into an approved, executed response plan (RFQs sent, POs expedited, customers notified) in minutes instead of days.

---

## 1. The real-world problem

Manufacturers depend on multi-tier supply networks spread across ports, regions and countries. Disruptions are now routine:

- **Natural events:** cyclones, floods, earthquakes, heatwaves (e.g. Bay of Bengal cyclones closing Chennai and Vizag ports).
- **Logistics events:** port strikes, Red Sea / Suez rerouting, container shortages, rail blockades.
- **Supplier events:** factory fires, insolvency, quality recalls, export bans, sanctions.
- **Geopolitical and price events:** tariffs, FX swings, commodity price spikes.

### What happens today (the pain)
1. **Late detection.** Procurement teams usually learn about a disruption from the news or when a shipment simply doesn't arrive, often **3–10 days after** the event started.
2. **Manual impact analysis.** Someone has to cross-check spreadsheets: *Which suppliers are in that region? Which materials do they supply? Which finished goods use those materials? Which customer orders are due?* This takes **1–3 days** of Excel and phone calls.
3. **Slow sourcing response.** Finding alternate suppliers, asking for quotes and comparing them takes **another 3–7 days**.
4. **Decisions with no numbers.** Managers pick an option without a clear view of cost vs. risk vs. delivery impact.
5. **Poor follow-through.** Customers are told late, POs aren't expedited, and nothing is learned for next time.

### Cost of the problem
- Supply disruptions lasting a month or longer now hit most manufacturers every few years, and a single major disruption can wipe out a large share of a year's profit (figures widely reported by McKinsey and the Business Continuity Institute).
- Small and mid-size manufacturers (SMEs) are hit hardest: they **can't afford** enterprise tools like Resilinc, Everstream or Interos (often $100k+ a year) and have no dedicated risk team.

## 2. Target users

| Persona | Role | What they need |
|---|---|---|
| **Priya, Procurement Manager** (primary) | Mid-size auto-parts maker, 40 suppliers, 6 countries | Know early, act fast, justify the decision |
| **Rahul, Plant / Operations Head** | Owns the production schedule | Which lines and orders slip, and by how much |
| **Anita, SME Owner** | 50–300 employee factory | Affordable "risk team in a chat", pay per use |
| **Supply-chain consultants** | Serve many SMEs | Run fast exposure reports for clients |

Industries: auto components, electronics assembly, pharma API sourcing, textiles, FMCG packaging, steel fabrication.

## 3. Why existing solutions fall short

| Option | Gap |
|---|---|
| Enterprise risk platforms | Expensive, months to set up, built only for large enterprises |
| News alerts / Google Alerts | No link to *your* suppliers, BOM or orders; no action |
| ERP systems (SAP, Tally, Odoo) | Hold the data but don't watch the outside world or reason about it |
| Plain chatbots | Can summarise news but can't calculate exposure or act on it |

## 4. Our solution

SupplyShock is a team of specialist AI agents on **Agentverse**, reached through one **Orchestrator agent in ASI:One**. In a single conversation it:

1. **Detects:** pulls live disruption signals (GDACS disasters, GDELT news, Open-Meteo weather) and matches them to the user's supplier locations.
2. **Assesses:** walks the supply graph (Supplier → Material → BOM → Product → Customer Order) to put a number on exposure: orders at risk, revenue at risk, days of stock cover left.
3. **Plans:** builds several response options (expedite, switch supplier, split order, use safety stock, reschedule production) and scores each on cost, risk and delivery.
4. **Sources:** finds and ranks alternate suppliers, then drafts and sends RFQs.
5. **Acts:** after the user approves on an interactive card, it executes: sends RFQs and expedite requests, creates draft POs, and drafts customer notifications.
6. **Learns:** records the incident, the decision and the outcome to improve future supplier risk scores.

## 5. Outcome produced (what "done" looks like)

At the end of one ASI:One conversation the user has:
- A **quantified exposure report** (for example: *"3 suppliers, 5 materials, 12 open orders, ₹1.8 Cr revenue at risk, stock-out in 6 days"*).
- A **chosen mitigation plan** with cost delta and risk reduction.
- **Executed actions:** RFQs emailed to alternate suppliers, an expedite request to the current supplier, a draft PO, and a customer notice.
- A **live watch** on the event that sends follow-up alerts if things get worse.

## 6. Success metrics

| Metric | Today | Target with SupplyShock |
|---|---|---|
| Time to detect | 3–10 days | < 1 hour |
| Time to quantify impact | 1–3 days | < 2 minutes |
| Time to send RFQs to alternates | 3–7 days | < 5 minutes |
| Revenue at risk, visible before stock-out | rarely | always |

## 7. Scope for the hackathon

- **Real data:** GDACS, GDELT, Open-Meteo, live FX rates (Frankfurter), real email sending for RFQs.
- **Simulated data:** the company's ERP data (suppliers, BOM, inventory, orders) as a realistic seeded dataset for a fictional auto-parts maker, "Apex Components Pvt Ltd". It can be swapped for a real ERP connector later.
- **Fully usable inside ASI:One** with no custom frontend.

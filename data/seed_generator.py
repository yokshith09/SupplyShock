"""Build the demo ERP database for "Apex Components Pvt Ltd". Owner: D2.

Run:  python data/seed_generator.py            (writes DB_PATH or data/supplyshock.db)
      SEED_TODAY=2026-10-24 python data/seed_generator.py   (pin "today" for a repeatable demo)

The data is fixed (no randomness) and reproduces the demo story in docs/d2/TASKS.md for the
Cyclone Michaung replay event (centre 13.08, 80.27, radius 150 km x 1.2 buffer):
  - exactly S-03, S-07, S-11 inside the zone
  - they are primary suppliers for 5 materials (M-04, M-07, M-12, M-15, M-22)
  - 12 open orders on products using them, due within 14 days, worth Rs 1.82 Cr
  - M-12 has 6 days of cover; S-21 Pune Diecast and S-14 Coimbatore Alloys are alternates
Dates are relative to "today" so the story works on any demo day.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_DIR.parent))

from data.db import db_path  # noqa: E402

# id, name, city, country, lat, lon, quality_rating, risk_score, lead_time_days
SUPPLIERS = [
    ("S-01", "Deccan Forgings", "Pune", "IN", 18.62, 73.80, 0.86, 0.15, 8),
    ("S-02", "Gujarat Polymers", "Vadodara", "IN", 22.31, 73.18, 0.82, 0.18, 7),
    ("S-03", "Chennai Castings", "Chennai", "IN", 13.11, 80.16, 0.90, 0.22, 4),
    ("S-04", "Shenzhen MicroTech", "Shenzhen", "CN", 22.54, 114.06, 0.88, 0.30, 21),
    ("S-05", "Penang Semicon", "Penang", "MY", 5.41, 100.33, 0.91, 0.20, 18),
    ("S-06", "Stuttgart Precision GmbH", "Stuttgart", "DE", 48.78, 9.18, 0.95, 0.10, 28),
    ("S-07", "Sriperumbudur Electronics", "Sriperumbudur", "IN", 12.97, 79.94, 0.89, 0.24, 5),
    ("S-08", "Monterrey Metals", "Monterrey", "MX", 25.69, -100.32, 0.84, 0.25, 30),
    ("S-09", "Rajkot Fasteners", "Rajkot", "IN", 22.30, 70.80, 0.80, 0.15, 6),
    ("S-10", "Nashik Rubber Works", "Nashik", "IN", 19.99, 73.79, 0.81, 0.17, 6),
    ("S-11", "Ennore Port Forwarding", "Ennore", "IN", 13.21, 80.32, 0.85, 0.35, 3),
    ("S-12", "Bengaluru Plastics", "Bengaluru", "IN", 12.97, 77.59, 0.83, 0.16, 5),
    ("S-13", "Hyderabad Alloys", "Hyderabad", "IN", 17.39, 78.49, 0.84, 0.18, 7),
    ("S-14", "Coimbatore Alloys", "Coimbatore", "IN", 11.02, 76.96, 0.86, 0.20, 7),
    ("S-15", "Aurangabad Stampings", "Aurangabad", "IN", 19.88, 75.34, 0.82, 0.16, 6),
    ("S-16", "Pune Wiring Systems", "Pune", "IN", 18.73, 73.85, 0.87, 0.14, 6),
    ("S-17", "Shenzhen Connectors", "Shenzhen", "CN", 22.60, 113.95, 0.83, 0.32, 20),
    ("S-18", "Surat Coatings", "Surat", "IN", 21.17, 72.83, 0.80, 0.15, 5),
    ("S-19", "Ahmedabad Electronics Works", "Ahmedabad", "IN", 23.02, 72.57, 0.85, 0.17, 10),
    ("S-20", "Stuttgart Sensorik GmbH", "Stuttgart", "DE", 48.74, 9.10, 0.94, 0.11, 25),
    ("S-21", "Pune Diecast Pvt Ltd", "Pune", "IN", 18.52, 73.86, 0.92, 0.12, 9),
    ("S-22", "Kolhapur Foundry", "Kolhapur", "IN", 16.70, 74.24, 0.83, 0.16, 8),
    ("S-23", "Monterrey Plasticos", "Monterrey", "MX", 25.67, -100.31, 0.81, 0.26, 30),
    ("S-24", "Penang Sensors", "Penang", "MY", 5.35, 100.30, 0.88, 0.21, 12),
    ("S-25", "Jamshedpur Steel Coils", "Jamshedpur", "IN", 22.80, 86.18, 0.85, 0.19, 9),
]

# id, name, category, unit, unit_cost_inr
MATERIALS = [
    ("M-01", "Aluminium ingot ADC12", "raw metal", "kg", 230.0),
    ("M-02", "Cold-rolled steel coil", "raw metal", "kg", 72.0),
    ("M-03", "PA66 engineering plastic granules", "polymer", "kg", 310.0),
    ("M-04", "Grey iron brake bracket casting", "casting", "pcs", 145.0),
    ("M-05", "PBT sensor housing", "moulded part", "pcs", 38.0),
    ("M-06", "M8 flange bolt", "fastener", "pcs", 4.5),
    ("M-07", "Wiring harness connector", "electrical", "pcs", 41.0),
    ("M-08", "Rubber grommet", "rubber", "pcs", 6.0),
    ("M-09", "Brake bracket bushing", "machined part", "pcs", 22.0),
    ("M-10", "32-bit automotive microcontroller", "electronics", "pcs", 210.0),
    ("M-11", "Power MOSFET", "electronics", "pcs", 48.0),
    ("M-12", "ECU housing (aluminium die-cast)", "casting", "pcs", 380.0),
    ("M-13", "Steel forging blank", "forging", "pcs", 95.0),
    ("M-14", "Copper wire 0.5 mm2", "electrical", "m", 18.0),
    ("M-15", "ECU control PCB assembly", "electronics", "pcs", 1700.0),
    ("M-16", "Thermal interface paste", "chemical", "g", 12.0),
    ("M-17", "Gasket seal", "rubber", "pcs", 9.0),
    ("M-18", "Powder coat paint", "chemical", "kg", 140.0),
    ("M-19", "Steel stamping bracket", "stamping", "pcs", 28.0),
    ("M-20", "Connector terminal pin", "electrical", "pcs", 1.2),
    ("M-21", "Hall-effect IC", "electronics", "pcs", 65.0),
    ("M-22", "Imported Hall-effect speed sensor (via Ennore port)", "electronics", "pcs", 520.0),
    ("M-23", "Precision drive shaft", "machined part", "pcs", 340.0),
    ("M-24", "Ball bearing 6202", "bearing", "pcs", 75.0),
    ("M-25", "Injection-moulded cover", "moulded part", "pcs", 44.0),
    ("M-26", "QR traceability label", "consumable", "pcs", 0.8),
    ("M-27", "Packaging carton", "consumable", "pcs", 15.0),
    ("M-28", "Die-cast gear lever", "casting", "pcs", 60.0),
    ("M-29", "Spring clip", "fastener", "pcs", 2.5),
    ("M-30", "Conformal coating", "chemical", "l", 90.0),
]

# supplier_id, material_id, price_inr, moq, capacity_per_week, is_primary
SUPPLIER_MATERIALS = [
    ("S-13", "M-01", 230.0, 500, 20000, 1),
    ("S-25", "M-02", 72.0, 1000, 50000, 1),
    ("S-02", "M-03", 310.0, 200, 8000, 1),
    ("S-03", "M-04", 145.0, 500, 6000, 1),
    ("S-22", "M-04", 160.0, 500, 4000, 0),
    ("S-12", "M-05", 38.0, 1000, 20000, 1),
    ("S-09", "M-06", 4.5, 5000, 200000, 1),
    ("S-07", "M-07", 41.0, 2000, 30000, 1),
    ("S-16", "M-07", 46.0, 2000, 25000, 0),
    ("S-10", "M-08", 6.0, 2000, 50000, 1),
    ("S-15", "M-09", 22.0, 1000, 20000, 1),
    ("S-04", "M-10", 210.0, 500, 10000, 1),
    ("S-05", "M-10", 225.0, 500, 8000, 0),
    ("S-05", "M-11", 48.0, 1000, 30000, 1),
    ("S-03", "M-12", 380.0, 500, 7000, 1),
    ("S-21", "M-12", 412.5, 500, 6000, 0),
    ("S-14", "M-12", 428.0, 500, 4000, 0),
    ("S-01", "M-13", 95.0, 500, 10000, 1),
    ("S-16", "M-14", 18.0, 5000, 100000, 1),
    ("S-07", "M-15", 1700.0, 100, 3000, 1),
    ("S-19", "M-15", 1850.0, 100, 2500, 0),
    ("S-20", "M-16", 12.0, 1000, 50000, 1),
    ("S-10", "M-17", 9.0, 2000, 40000, 1),
    ("S-18", "M-18", 140.0, 100, 5000, 1),
    ("S-15", "M-19", 28.0, 1000, 20000, 1),
    ("S-17", "M-20", 1.2, 10000, 500000, 1),
    ("S-20", "M-21", 65.0, 1000, 20000, 1),
    ("S-11", "M-22", 520.0, 200, 3000, 1),
    ("S-24", "M-22", 560.0, 200, 2500, 0),
    ("S-06", "M-23", 340.0, 100, 2000, 1),
    ("S-08", "M-24", 75.0, 1000, 20000, 1),
    ("S-23", "M-25", 44.0, 1000, 15000, 1),
    ("S-12", "M-26", 0.8, 10000, 500000, 1),
    ("S-02", "M-27", 15.0, 1000, 30000, 1),
    ("S-22", "M-28", 60.0, 500, 8000, 1),
    ("S-09", "M-29", 2.5, 5000, 200000, 1),
    ("S-05", "M-30", 90.0, 50, 2000, 1),
]

# id, name, sell_price_inr
PRODUCTS = [
    ("P-01", "ECU assembly", 4500.0),
    ("P-02", "Brake caliper bracket kit", 1250.0),
    ("P-03", "ABS wheel speed sensor module", 2100.0),
    ("P-04", "Gear shift lever assembly", 900.0),
    ("P-05", "Steering column bracket", 1600.0),
    ("P-06", "Motor controller board", 6200.0),
    ("P-07", "Drive shaft subassembly", 3800.0),
    ("P-08", "Dashboard sensor cluster", 2800.0),
]

# product_id, material_id, qty_per_unit
BOM = [
    ("P-01", "M-12", 1), ("P-01", "M-15", 1), ("P-01", "M-07", 4), ("P-01", "M-06", 4),
    ("P-01", "M-16", 2), ("P-01", "M-26", 1), ("P-01", "M-27", 1),
    ("P-02", "M-04", 2), ("P-02", "M-09", 2), ("P-02", "M-06", 4), ("P-02", "M-18", 0.1),
    ("P-03", "M-22", 1), ("P-03", "M-07", 2), ("P-03", "M-05", 1), ("P-03", "M-20", 4),
    ("P-04", "M-28", 1), ("P-04", "M-29", 2), ("P-04", "M-24", 1), ("P-04", "M-25", 1),
    ("P-05", "M-13", 1), ("P-05", "M-19", 2), ("P-05", "M-06", 6), ("P-05", "M-18", 0.2),
    ("P-06", "M-10", 1), ("P-06", "M-11", 6), ("P-06", "M-30", 0.05), ("P-06", "M-14", 3),
    ("P-07", "M-23", 1), ("P-07", "M-24", 2), ("P-07", "M-02", 4), ("P-07", "M-17", 2),
    ("P-08", "M-21", 3), ("P-08", "M-03", 0.2), ("P-08", "M-25", 1), ("P-08", "M-20", 8),
]  # fmt: skip

# material_id -> (on_hand_qty, daily_consumption). Demo materials first: cover = on_hand / daily.
INVENTORY_DEMO = {
    "M-12": (6000, 1000),  # 6 days  -> CRITICAL
    "M-07": (18000, 2000),  # 9 days  -> HIGH
    "M-15": (5500, 500),  # 11 days -> HIGH
    "M-04": (9000, 500),  # 18 days -> MED
    "M-22": (10000, 400),  # 25 days -> MED
}
OTHER_COVER_DAYS = [20, 24, 28, 32, 36, 40, 45, 50, 55, 60]

# The 12 at-risk orders: id -> (customer, product_id, qty, due in N days). Total Rs 1.82 Cr.
AT_RISK_ORDERS = {
    "O-1003": ("Orion Motors", "P-01", 600, 2),
    "O-1005": ("Vega Two-Wheelers", "P-03", 800, 3),
    "O-1007": ("Kestrel EV", "P-01", 500, 4),
    "O-1008": ("Atlas Trucks", "P-02", 1200, 5),
    "O-1011": ("Orion Motors", "P-01", 400, 6),
    "O-1014": ("Nova Tractors", "P-03", 600, 7),
    "O-1016": ("Atlas Trucks", "P-02", 800, 8),
    "O-1019": ("Kestrel EV", "P-01", 300, 9),
    "O-1022": ("Vega Two-Wheelers", "P-03", 500, 10),
    "O-1025": ("Nova Tractors", "P-02", 1000, 11),
    "O-1028": ("Orion Motors", "P-01", 200, 12),
    "O-1031": ("Atlas Trucks", "P-02", 1168, 13),
}
CUSTOMERS = ["Orion Motors", "Vega Two-Wheelers", "Kestrel EV", "Atlas Trucks", "Nova Tractors"]
SAFE_PRODUCTS = ["P-04", "P-05", "P-06", "P-07", "P-08"]
AFFECTED_PRODUCTS = ["P-01", "P-02", "P-03"]


def _today() -> date:
    pinned = os.getenv("SEED_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()


def _inventory_rows() -> list[tuple]:
    rows, i = [], 0
    for mat_id, *_ in MATERIALS:
        if mat_id in INVENTORY_DEMO:
            on_hand, daily = INVENTORY_DEMO[mat_id]
        else:
            daily = 200 + 50 * (i % 7)
            on_hand = daily * OTHER_COVER_DAYS[i % len(OTHER_COVER_DAYS)]
            i += 1
        rows.append((mat_id, float(on_hand), float(daily), round(daily * 3.0, 1)))
    return rows


def _order_rows(today: date) -> list[tuple]:
    price = {pid: p for pid, _, p in PRODUCTS}
    rows, other = [], 0
    for n in range(1001, 1041):
        oid = f"O-{n}"
        if oid in AT_RISK_ORDERS:
            customer, pid, qty, due_in = AT_RISK_ORDERS[oid]
        else:
            customer = CUSTOMERS[other % len(CUSTOMERS)]
            if other < 6:  # affected products, but due after the 14-day disruption window
                pid, due_in = AFFECTED_PRODUCTS[other % 3], 16 + 2 * other
            else:
                pid, due_in = SAFE_PRODUCTS[other % 5], 1 + (other * 3) % 30
            qty = 100 + 50 * (other % 9)
            other += 1
        due = (today + timedelta(days=due_in)).isoformat()
        rows.append((oid, customer, pid, qty, due, qty * price[pid], "open"))
    return rows


def build(path: str | Path | None = None, today: date | None = None) -> Path:
    """(Re)create the database at path and fill it. Returns the path."""
    path = Path(path or db_path())
    today = today or _today()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))
    try:
        conn.executescript((DATA_DIR / "schema.sql").read_text(encoding="utf-8"))
        for migration in sorted((DATA_DIR / "migrations").glob("*.sql")):
            conn.executescript(migration.read_text(encoding="utf-8"))

        conn.executemany(
            "INSERT INTO suppliers (id, name, city, country, lat, lon, tier, quality_rating,"
            " risk_score, email, lead_time_days) VALUES (?,?,?,?,?,?,1,?,?,?,?)",
            [
                (sid, name, city, country, lat, lon, q, r, f"{sid.lower().replace('-', '')}@supplyshock.demo", lt)
                for sid, name, city, country, lat, lon, q, r, lt in SUPPLIERS
            ],
        )
        conn.executemany("INSERT INTO materials VALUES (?,?,?,?,?)", MATERIALS)
        conn.executemany("INSERT INTO supplier_materials VALUES (?,?,?,?,?,?)", SUPPLIER_MATERIALS)
        conn.executemany("INSERT INTO products VALUES (?,?,?)", PRODUCTS)
        conn.executemany("INSERT INTO bom VALUES (?,?,?)", BOM)
        conn.executemany("INSERT INTO inventory VALUES (?,?,?,?)", _inventory_rows())
        conn.executemany("INSERT INTO customer_orders VALUES (?,?,?,?,?,?,?)", _order_rows(today))
        conn.commit()
    finally:
        conn.close()
    return path


if __name__ == "__main__":
    out = build()
    print(f"Seeded {out} (today = {_today().isoformat()})")

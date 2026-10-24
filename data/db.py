"""SQLite access for the ERP dataset. Owner: D2.

Everyone reads ERP data through these functions; nobody writes raw SQL elsewhere.
D1's own tables (incidents, actions_log) are written by agents/orchestrator/store.py
using get_connection().

Env: DB_PATH (default data/supplyshock.db). Build the DB with `python data/seed_generator.py`.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "supplyshock.db"


def db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH)))


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _one(sql: str, params: tuple = ()) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _all(sql: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_supplier(supplier_id: str) -> dict | None:
    return _one("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))


def list_suppliers() -> list[dict]:
    return _all("SELECT * FROM suppliers ORDER BY id")


def get_material(material_id: str) -> dict | None:
    return _one("SELECT * FROM materials WHERE id = ?", (material_id,))


def get_order(order_id: str) -> dict | None:
    return _one("SELECT * FROM customer_orders WHERE id = ?", (order_id,))


def suppliers_for_material(material_id: str) -> list[dict]:
    """Every supplier of a material, with its price/MOQ/capacity/is_primary."""
    return _all(
        """
        SELECT s.*, sm.material_id, sm.price_inr, sm.moq, sm.capacity_per_week, sm.is_primary
        FROM supplier_materials sm JOIN suppliers s ON s.id = sm.supplier_id
        WHERE sm.material_id = ?
        ORDER BY sm.is_primary DESC, sm.price_inr
        """,
        (material_id,),
    )


def materials_for_supplier(supplier_id: str, primary_only: bool = True) -> list[dict]:
    sql = """
        SELECT m.*, sm.price_inr, sm.is_primary
        FROM supplier_materials sm JOIN materials m ON m.id = sm.material_id
        WHERE sm.supplier_id = ?
    """
    if primary_only:
        sql += " AND sm.is_primary = 1"
    return _all(sql + " ORDER BY m.id", (supplier_id,))


def products_using_material(material_id: str) -> list[dict]:
    return _all(
        """
        SELECT p.*, b.qty_per_unit
        FROM bom b JOIN products p ON p.id = b.product_id
        WHERE b.material_id = ?
        ORDER BY p.id
        """,
        (material_id,),
    )


def open_orders_for_products(product_ids: list[str]) -> list[dict]:
    if not product_ids:
        return []
    marks = ",".join("?" for _ in product_ids)
    return _all(
        f"SELECT * FROM customer_orders WHERE status = 'open' AND product_id IN ({marks}) "
        "ORDER BY due_date, id",
        tuple(product_ids),
    )


def inventory_for(material_id: str) -> dict | None:
    return _one("SELECT * FROM inventory WHERE material_id = ?", (material_id,))

-- SupplyShock core ERP schema (SQLite). Owner: D2. See docs/TRD.md §4.
-- Do not edit after Phase 0: add numbered migrations in data/migrations/
-- (D2: 100-199, D1: 200-299). D1's incidents/actions_log tables live in 2xx migrations.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    id              TEXT PRIMARY KEY,          -- S-01
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    country         TEXT NOT NULL,
    lat             REAL NOT NULL,
    lon             REAL NOT NULL,
    tier            INTEGER NOT NULL DEFAULT 1,
    quality_rating  REAL NOT NULL DEFAULT 0.8, -- 0..1
    risk_score      REAL NOT NULL DEFAULT 0.2, -- 0..1, higher = riskier
    email           TEXT NOT NULL,
    lead_time_days  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS materials (
    id              TEXT PRIMARY KEY,          -- M-01
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit            TEXT NOT NULL DEFAULT 'pcs',
    unit_cost_inr   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_materials (
    supplier_id       TEXT NOT NULL REFERENCES suppliers(id),
    material_id       TEXT NOT NULL REFERENCES materials(id),
    price_inr         REAL NOT NULL,
    moq               INTEGER NOT NULL DEFAULT 1,
    capacity_per_week INTEGER NOT NULL,
    is_primary        INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    PRIMARY KEY (supplier_id, material_id)
);

CREATE TABLE IF NOT EXISTS products (
    id              TEXT PRIMARY KEY,          -- P-01
    name            TEXT NOT NULL,
    sell_price_inr  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS bom (
    product_id      TEXT NOT NULL REFERENCES products(id),
    material_id     TEXT NOT NULL REFERENCES materials(id),
    qty_per_unit    REAL NOT NULL,
    PRIMARY KEY (product_id, material_id)
);

CREATE TABLE IF NOT EXISTS inventory (
    material_id       TEXT PRIMARY KEY REFERENCES materials(id),
    on_hand_qty       REAL NOT NULL,
    daily_consumption REAL NOT NULL CHECK (daily_consumption > 0),
    safety_stock      REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS customer_orders (
    id              TEXT PRIMARY KEY,          -- O-1001
    customer        TEXT NOT NULL,
    product_id      TEXT NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    due_date        TEXT NOT NULL,             -- ISO date
    value_inr       REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS idx_supplier_materials_material ON supplier_materials(material_id);
CREATE INDEX IF NOT EXISTS idx_bom_material ON bom(material_id);
CREATE INDEX IF NOT EXISTS idx_orders_product_status ON customer_orders(product_id, status);

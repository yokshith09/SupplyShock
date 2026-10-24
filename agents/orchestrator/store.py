"""Persistence for D1's tables (incidents, actions_log). Uses data.db.get_connection (D2) by default;
tests inject any sqlite3 connection factory. Never edits D2's schema."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

MIGRATION = Path(__file__).resolve().parents[2] / "data" / "migrations" / "200_incidents_actions_log.sql"
_DDL = """
CREATE TABLE IF NOT EXISTS incidents(
  id TEXT PRIMARY KEY, event_json TEXT, status TEXT, created_at TEXT,
  chosen_option_json TEXT, outcome TEXT);
CREATE TABLE IF NOT EXISTS actions_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT, type TEXT, target TEXT,
  status TEXT, payload_json TEXT, ts TEXT);
"""


def _default_conn() -> sqlite3.Connection:
    from data.db import get_connection  # D2-owned; imported lazily so d1 works standalone
    return get_connection()


class Store:
    def __init__(self, conn_factory: Callable[[], sqlite3.Connection] | None = None):
        self._factory = conn_factory or _default_conn

    def _conn(self) -> sqlite3.Connection:
        conn = self._factory()
        conn.executescript(_DDL)
        return conn

    def save_incident(self, incident: dict) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO incidents(id,event_json,status,created_at,chosen_option_json,outcome) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET event_json=excluded.event_json, "
            "status=excluded.status, chosen_option_json=excluded.chosen_option_json, outcome=excluded.outcome",
            (incident["id"], json.dumps(incident.get("event")), incident.get("status", "OPEN"),
             incident.get("created_at") or datetime.now(timezone.utc).isoformat(),
             json.dumps(incident.get("chosen_option")), incident.get("outcome")))
        conn.commit()

    def log_action(self, incident_id: str, result: dict) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO actions_log(incident_id,type,target,status,payload_json,ts) VALUES(?,?,?,?,?,?)",
            (incident_id, result.get("type"), result.get("target"), result.get("status"),
             json.dumps(result), datetime.now(timezone.utc).isoformat()))
        conn.commit()

    def list_actions(self, incident_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("SELECT payload_json FROM actions_log WHERE incident_id=? ORDER BY id",
                            (incident_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]


# module-level helpers matching the contract in 04_TEAM_PLAN E.5
def save_incident(incident: dict) -> None:
    Store().save_incident(incident)


def log_action(incident_id: str, result: dict) -> None:
    Store().log_action(incident_id, result)

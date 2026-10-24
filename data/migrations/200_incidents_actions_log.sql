-- D1 tables (200-299 range). Applied by data/seed_generator.py after schema.sql and the 1xx migrations.
CREATE TABLE IF NOT EXISTS incidents(
  id TEXT PRIMARY KEY, event_json TEXT, status TEXT, created_at TEXT,
  chosen_option_json TEXT, outcome TEXT);
CREATE TABLE IF NOT EXISTS actions_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT, type TEXT, target TEXT,
  status TEXT, payload_json TEXT, ts TEXT);

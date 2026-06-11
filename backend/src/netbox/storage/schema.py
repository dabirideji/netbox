"""SQLite schema for monitor persistence."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS ping_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checked_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  host TEXT NOT NULL,
  label TEXT NOT NULL,
  scope TEXT NOT NULL,
  ok INTEGER NOT NULL,
  latency_ms REAL,
  error TEXT,
  status TEXT NOT NULL,
  severity INTEGER NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_ping_results_checked_at ON ping_results (checked_at);
CREATE INDEX IF NOT EXISTS idx_ping_results_target_checked ON ping_results (target_id, checked_at);

CREATE TABLE IF NOT EXISTS monitor_targets (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  host TEXT NOT NULL,
  scope TEXT NOT NULL,
  target_type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  group_name TEXT NOT NULL,
  environment TEXT NOT NULL,
  enabled INTEGER NOT NULL,
  interval_ms INTEGER NOT NULL,
  timeout_ms INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_favorite INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_monitor_targets_enabled ON monitor_targets (enabled);

CREATE TABLE IF NOT EXISTS check_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checked_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  host TEXT NOT NULL,
  label TEXT NOT NULL,
  scope TEXT NOT NULL,
  target_type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  ok INTEGER NOT NULL,
  latency_ms REAL,
  error TEXT,
  status TEXT NOT NULL,
  severity INTEGER NOT NULL,
  duration_ms INTEGER,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_check_results_checked_at ON check_results (checked_at);
CREATE INDEX IF NOT EXISTS idx_check_results_target_checked ON check_results (target_id, checked_at);

CREATE TABLE IF NOT EXISTS status_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  target_label TEXT NOT NULL,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  UNIQUE(event_at, target_id, from_status, to_status)
);

CREATE INDEX IF NOT EXISTS idx_status_events_event_at ON status_events (event_at);

CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_id TEXT NOT NULL,
  target_label TEXT NOT NULL,
  opened_at INTEGER NOT NULL,
  resolved_at INTEGER,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_incidents_target_status ON incidents (target_id, status);
CREATE INDEX IF NOT EXISTS idx_incidents_opened_at ON incidents (opened_at);

CREATE TABLE IF NOT EXISTS speed_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tested_at INTEGER NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  download_mbps REAL,
  upload_mbps REAL,
  latency_ms REAL,
  jitter_ms REAL,
  packet_loss_pct REAL,
  retransmission_pct REAL,
  duration_ms INTEGER,
  server_name TEXT,
  server_location TEXT,
  server_host TEXT,
  error TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_speed_tests_tested_at ON speed_tests (tested_at);

CREATE TABLE IF NOT EXISTS platform_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  data TEXT NOT NULL DEFAULT '{}',
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE TABLE IF NOT EXISTS storage_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  data TEXT NOT NULL DEFAULT '{}',
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE TABLE IF NOT EXISTS ui_preferences (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  data TEXT NOT NULL DEFAULT '{}',
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE TABLE IF NOT EXISTS smtp_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  provider TEXT NOT NULL DEFAULT 'custom',
  host TEXT NOT NULL DEFAULT '',
  port INTEGER NOT NULL DEFAULT 587,
  username TEXT NOT NULL DEFAULT '',
  password_encrypted TEXT NOT NULL DEFAULT '',
  from_email TEXT NOT NULL DEFAULT '',
  from_name TEXT NOT NULL DEFAULT 'Netbox',
  use_tls INTEGER NOT NULL DEFAULT 1,
  configured INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE TABLE IF NOT EXISTS target_alerts (
  target_id TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  notification INTEGER NOT NULL DEFAULT 1,
  sound INTEGER NOT NULL DEFAULT 1,
  email INTEGER NOT NULL DEFAULT 0,
  email_to TEXT NOT NULL DEFAULT '',
  on_degraded INTEGER NOT NULL DEFAULT 1,
  on_down INTEGER NOT NULL DEFAULT 1,
  cooldown_ms INTEGER NOT NULL DEFAULT 300000,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  FOREIGN KEY (target_id) REFERENCES monitor_targets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alert_dispatch_state (
  target_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  last_sent_at INTEGER NOT NULL,
  next_due_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  PRIMARY KEY (target_id, channel),
  FOREIGN KEY (target_id) REFERENCES monitor_targets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alert_dispatch_next_due ON alert_dispatch_state (next_due_at);
"""

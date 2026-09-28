import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    display_name TEXT,
    subscription_url_encrypted TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    last_updated_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS servers (
    id TEXT PRIMARY KEY,
    provider_id TEXT,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    host TEXT,
    port INTEGER,
    transport TEXT,
    security TEXT,
    metadata_json TEXT,
    FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS server_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    expression TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'exclude',
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    scheduling_mode TEXT NOT NULL,
    planned_seconds REAL NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    total_servers INTEGER NOT NULL,
    completed_servers INTEGER NOT NULL DEFAULT 0,
    failed_servers INTEGER NOT NULL DEFAULT 0,
    current_server_id TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS test_run_servers (
    run_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (run_id, server_id),
    FOREIGN KEY(run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    server_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    success INTEGER NOT NULL,
    latency_ms REAL,
    jitter_ms REAL,
    packet_loss_percent REAL,
    download_mbps REAL,
    upload_mbps REAL,
    dns_ok INTEGER,
    http_ok INTEGER,
    details_json TEXT,
    FOREIGN KEY(run_id) REFERENCES test_runs(id) ON DELETE SET NULL,
    FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    context_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_test_results_server_time
ON test_results(server_id, started_at);

CREATE INDEX IF NOT EXISTS idx_test_results_run
ON test_results(run_id);

CREATE INDEX IF NOT EXISTS idx_logs_time
ON logs(created_at);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)
        _ensure_column(connection, "servers", "provider_id", "TEXT")
        _ensure_column(connection, "servers", "transport", "TEXT")
        _ensure_column(connection, "servers", "security", "TEXT")
        _ensure_column(connection, "test_results", "run_id", "TEXT")


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def get_meta(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO app_meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def json_loads(value: str | None) -> dict[str, Any]:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}

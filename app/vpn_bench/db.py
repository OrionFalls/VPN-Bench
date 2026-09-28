import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS servers (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    host TEXT,
    port INTEGER,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    FOREIGN KEY(server_id) REFERENCES servers(id)
);

CREATE INDEX IF NOT EXISTS idx_test_results_server_time
ON test_results(server_id, started_at);
"""


def initialize(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)

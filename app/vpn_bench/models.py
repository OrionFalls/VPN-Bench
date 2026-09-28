from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Server:
    id: str
    provider: str
    name: str
    protocol: str
    host: str | None = None
    port: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class TestResult:
    server_id: str
    started_at: datetime
    duration_seconds: float
    success: bool
    latency_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_percent: float | None = None
    download_mbps: float | None = None
    upload_mbps: float | None = None
    dns_ok: bool | None = None
    http_ok: bool | None = None
    details: dict[str, Any] | None = None

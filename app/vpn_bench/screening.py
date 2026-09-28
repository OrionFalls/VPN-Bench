"""Screening policy for fast VPN candidate selection.

The screening stage is intentionally conservative: it removes only clearly
unusable servers. A server that is merely slow is kept for the full test so
that the screening stage does not hide useful historical data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ScreeningPolicy:
    min_success_rate: float = 0.60
    max_packet_loss_percent: float = 20.0
    max_latency_ms: float = 2500.0
    min_samples: int = 1
    repeat_passes: int = 2

    def keep(self, samples: Iterable[dict[str, Any]]) -> bool:
        rows = list(samples)
        if len(rows) < self.min_samples:
            return False

        successful = sum(bool(row.get("success")) for row in rows)
        success_rate = successful / len(rows)
        if success_rate < self.min_success_rate:
            return False

        packet_losses = [
            float(row["packet_loss_percent"])
            for row in rows
            if row.get("packet_loss_percent") is not None
        ]
        if packet_losses and sum(packet_losses) / len(packet_losses) > self.max_packet_loss_percent:
            return False

        latencies = [
            float(row["latency_ms"])
            for row in rows
            if row.get("latency_ms") is not None
        ]
        if latencies and sum(latencies) / len(latencies) > self.max_latency_ms:
            return False

        return True


def shortlist(
    samples_by_server: dict[str, list[dict[str, Any]]],
    policy: ScreeningPolicy | None = None,
) -> list[str]:
    """Return server IDs that survived the screening policy.

    Only servers with enough usable observations are returned. Ordering is
    deterministic and follows server ID; this stage deliberately does not
    rank providers or declare a single "best" server.
    """

    policy = policy or ScreeningPolicy()
    return sorted(
        server_id
        for server_id, samples in samples_by_server.items()
        if policy.keep(samples)
    )


def summarize(samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(samples)
    if not rows:
        return {
            "samples": 0,
            "success_rate": 0.0,
            "avg_latency_ms": None,
            "avg_packet_loss_percent": None,
        }

    def average(key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return sum(values) / len(values) if values else None

    return {
        "samples": len(rows),
        "success_rate": sum(bool(row.get("success")) for row in rows) / len(rows),
        "avg_latency_ms": average("latency_ms"),
        "avg_packet_loss_percent": average("packet_loss_percent"),
    }

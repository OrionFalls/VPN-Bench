from __future__ import annotations

import threading

from vpn_bench.screening_campaign import ScreeningCampaignManager
from vpn_bench.screening_plan import ScreeningPlan


class FakeWorker:
    def __init__(self):
        self.calls = []

    def run_server(self, server, allocation_seconds, stop_event, on_result=None):
        self.calls.append((server["id"], allocation_seconds))
        result = {
            "server_id": server["id"],
            "started_at": "2026-01-01T00:00:00+00:00",
            "duration_seconds": allocation_seconds,
            "success": server["id"] != "bad",
            "latency_ms": 50 if server["id"] != "slow" else 4000,
            "jitter_ms": 2,
            "packet_loss_percent": 0,
            "dns_ok": True,
            "http_ok": True,
            "details": {},
        }
        if on_result:
            on_result(result)
        return result["success"]


def test_screening_runs_two_passes_for_survivors():
    worker = FakeWorker()
    manager = ScreeningCampaignManager(
        worker,
        plan=ScreeningPlan(first_pass_seconds=2, second_pass_seconds=3, repeat_passes=2),
    )
    state = manager.start(
        "run-1",
        {key: {"id": key} for key in ("good", "bad")},
    )

    # The fake worker is synchronous through the manager's background thread.
    for _ in range(100):
        final = manager.get("run-1")
        if final and final.status not in {"running", "stopping"}:
            break
        threading.Event().wait(0.01)

    assert final.status == "completed"
    assert final.shortlisted_servers == ["good"]
    assert worker.calls == [
        ("good", 2),
        ("bad", 2),
        ("good", 3),
    ]


def test_screening_can_stop_before_next_server():
    worker = FakeWorker()
    manager = ScreeningCampaignManager(
        worker,
        plan=ScreeningPlan(first_pass_seconds=2, second_pass_seconds=2, repeat_passes=2),
    )
    state = manager.start("run-2", {"good": {"id": "good"}})
    assert manager.stop("run-2") is True
    assert manager.get("run-2").status in {"stopping", "stopped", "completed"}

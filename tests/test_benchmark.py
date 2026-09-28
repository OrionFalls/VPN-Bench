from vpn_bench.capabilities import detect_capabilities, preferred_cores


def test_xhttp_prefers_lx_then_extended_then_xray():
    assert preferred_cores("vless", "xhttp") == (
        "sing-box-lx",
        "sing-box-extended",
        "xray",
    )


def test_unknown_protocol_is_not_claimed_supported():
    caps = detect_capabilities("tuic", "udp")
    assert all(not item.supported for item in caps)


import threading

from vpn_bench.benchmark import BenchmarkEngine
from vpn_bench.proxied_probes import ProxyProbeResult


class FakeAdapter:
    def connect(self, server):
        return type("Handle", (), {"metadata": {"proxy_url": "http://127.0.0.1:1"}})()

    def disconnect(self, handle):
        pass


def test_engine_connects_probes_and_disconnects(monkeypatch):
    engine = BenchmarkEngine(probe_interval_seconds=2)
    engine.lx_adapter = FakeAdapter()
    monkeypatch.setattr(
        "vpn_bench.benchmark.run_proxy_probe",
        lambda *args, **kwargs: ProxyProbeResult(
            success=True,
            latency_ms=10.0,
            jitter_ms=1.0,
            packet_loss_percent=0.0,
            dns_ok=True,
            http_ok=True,
            details={},
        ),
    )
    results = []
    ok = engine.run_server(
        {"id": "s1", "metadata": {"uri": "vless://x@example.com:443"}},
        allocation_seconds=0,
        stop_event=threading.Event(),
        on_result=results.append,
    )
    assert ok
    assert len(results) == 1
    assert results[0]["server_id"] == "s1"

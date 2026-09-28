from vpn_bench.probes import run_probe


def test_probe_result_has_expected_shape(monkeypatch):
    monkeypatch.setattr("vpn_bench.probes.dns_probe", lambda host, timeout: (True, 2.0))
    monkeypatch.setattr(
        "vpn_bench.probes.tcp_probe",
        lambda host, port, timeout: (True, 10.0),
    )
    result = run_probe("example.com", 443, attempts=3)
    assert result.success
    assert result.latency_ms == 10.0
    assert result.jitter_ms == 0.0
    assert result.packet_loss_percent == 0.0
    assert result.http_ok is None

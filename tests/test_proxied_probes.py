from vpn_bench.proxied_probes import run_proxy_probe


def test_proxy_probe_collects_latency_jitter_and_loss(monkeypatch):
    values = iter([(True, 10.0, 200), (True, 12.0, 200), (False, None, None), (True, 11.0, 200)])

    def fake_http(*args, **kwargs):
        return next(values)

    monkeypatch.setattr("vpn_bench.proxied_probes.http_head", fake_http)
    monkeypatch.setattr(
        "vpn_bench.proxied_probes.dns_over_https",
        lambda *args, **kwargs: (True, 15.0, 200),
    )
    result = run_proxy_probe(
        "http://127.0.0.1:12345",
        ["https://example.com/"],
        attempts=3,
    )
    assert result.success
    assert result.packet_loss_percent == 33.33333333333333
    assert result.latency_ms == 11.0
    assert result.jitter_ms == 2.0

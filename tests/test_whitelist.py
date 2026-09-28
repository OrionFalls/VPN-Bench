from vpn_bench.proxied_probes import run_proxy_probe


def test_whitelist_requires_blocked_baseline(monkeypatch):
    responses = iter([
        (True, 20.0, 200),
        (True, 20.0, 200),
    ])

    monkeypatch.setattr(
        "vpn_bench.proxied_probes.http_head",
        lambda *args, **kwargs: next(responses),
    )
    monkeypatch.setattr(
        "vpn_bench.proxied_probes.dns_over_https",
        lambda *args, **kwargs: (True, 10.0, 200),
    )

    result = run_proxy_probe(
        "http://127.0.0.1:1080",
        ["https://example.com/"],
        attempts=1,
        whitelist_targets=["https://blocked.example/"],
        whitelist_baseline=[
            {"target": "https://blocked.example/", "reachable_without_vpn": False}
        ],
    )
    assert result.details["whitelist_ok"] is True
    assert result.details["whitelist"][0]["bypass_ok"] is True

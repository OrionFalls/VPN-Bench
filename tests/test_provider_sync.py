from vpn_bench.api import build_app
from vpn_bench.config import AppConfig, BenchmarkConfig, Config


def test_provider_sync_route_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_BENCH_SECRET", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    config = Config(
        app=AppConfig("127.0.0.1", 8080, str(tmp_path / "db.sqlite3")),
        providers=(),
        benchmark=BenchmarkConfig(),
    )
    app = build_app(config)
    paths = {route.path for route in app.routes}
    assert "/api/v1/providers/{provider_id}/sync" in paths

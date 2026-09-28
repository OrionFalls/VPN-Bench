import sqlite3

from vpn_bench.api import build_app
from vpn_bench.config import AppConfig, BenchmarkConfig, Config


def test_api_builds_and_contains_setup_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_BENCH_SECRET", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    config = Config(
        app=AppConfig("127.0.0.1", 8080, str(tmp_path / "db.sqlite3")),
        providers=(),
        benchmark=BenchmarkConfig(),
    )

    app = build_app(config)
    paths = {route.path for route in app.routes}

    assert "/" in paths
    assert "/health" in paths
    assert "/api/v1/setup" in paths
    assert "/api/v1/auth/login" in paths

    connection = sqlite3.connect(config.app.database)
    assert connection.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0
    connection.close()

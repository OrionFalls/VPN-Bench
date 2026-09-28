import os

from fastapi.testclient import TestClient

from vpn_bench.api import build_app
from vpn_bench.config import AppConfig, BenchmarkConfig, Config


def test_first_run_setup_and_login(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_BENCH_SECRET", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    config = Config(
        app=AppConfig("127.0.0.1", 8080, str(tmp_path / "db.sqlite3")),
        providers=(),
        benchmark=BenchmarkConfig(),
    )
    client = TestClient(build_app(config))

    assert client.get("/api/v1/setup/status").json()["configured"] is False
    response = client.post("/api/v1/setup", json={"password": "a-strong-test-password"})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/").status_code == 200

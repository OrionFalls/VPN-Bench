from __future__ import annotations

import hashlib
import secrets
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Config
from .capabilities import detect_capabilities
from .worker_client import WorkerClient
from cryptography.fernet import Fernet
from .db import connect, get_meta, initialize, json_loads, set_meta
from .security import create_session_token, hash_password, verify_password
from .screening import ScreeningPolicy
from .screening_campaign import ScreeningCampaignManager
from .screening_plan import ScreeningPlan
from .subscription import SubscriptionError, fetch_subscription, parse_subscription
from .test_runner import TestRunManager
from .ui import page


SESSION_DAYS = 7


def _secret_box() -> Fernet:
    key = os.environ.get("VPN_BENCH_SECRET")
    if not key:
        raise RuntimeError("VPN_BENCH_SECRET is not configured")
    return Fernet(key.encode())


def encrypt_subscription_url(url: str) -> str:
    return _secret_box().encrypt(url.encode()).decode()


def decrypt_subscription_url(value: str) -> str:
    return _secret_box().decrypt(value.encode()).decode()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SetupRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class ProviderRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    subscription_url: str = Field(min_length=1, max_length=4096)
    enabled: bool = True


class TestStartRequest(BaseModel):
    server_ids: list[str] = Field(min_length=1)
    duration_seconds: int = Field(gt=0)
    scheduling_mode: str = Field(pattern="^(equal_time|sequential)$")


class FilterRequest(BaseModel):
    scope: str = "test"
    mode: str = Field(default="exclude", pattern="^(exclude|include)$")
    expressions: list[str] = Field(default_factory=list)


class ScreeningStartRequest(BaseModel):
    server_ids: list[str] = Field(min_length=1)
    first_pass_seconds: int = Field(default=30, gt=0, le=300)
    second_pass_seconds: int = Field(default=30, gt=0, le=300)
    repeat_passes: int = Field(default=2, ge=1, le=3)
    max_shortlist: int | None = Field(default=None, gt=0)


def build_app(config: Config) -> FastAPI:
    initialize(config.app.database)
    manager = TestRunManager()
    worker = WorkerClient(poll_interval=max(0.5, min(2.0, config.benchmark.probe_interval_seconds / 4)))
    screening = ScreeningCampaignManager(worker)
    app = FastAPI(title="VPN-Bench API", version=config.app.version)
    app.mount("/static", StaticFiles(directory=Path(__file__).with_name("static")), name="static")

    def db() -> sqlite3.Connection:
        return connect(config.app.database)

    def require_auth(vpn_bench_session: str | None = Cookie(default=None)) -> str:
        if not vpn_bench_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        with db() as connection:
            row = connection.execute(
                "SELECT expires_at FROM sessions WHERE token_hash = ?", (token_hash(vpn_bench_session),)
            ).fetchone()
            if not row or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
        return vpn_bench_session

    @app.get("/", response_class=HTMLResponse)
    def root() -> HTMLResponse:
        return page()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": config.app.version}

    @app.get("/api/v1/setup/status")
    def setup_status() -> dict:
        with db() as connection:
            configured = connection.execute("SELECT 1 FROM admins WHERE id = 1").fetchone() is not None
        return {"configured": configured}

    @app.post("/api/v1/setup")
    def setup(payload: SetupRequest, response: Response) -> dict:
        with db() as connection:
            if connection.execute("SELECT 1 FROM admins WHERE id = 1").fetchone():
                raise HTTPException(status_code=409, detail="Administrator already configured")
            connection.execute(
                "INSERT INTO admins(id, password_hash, created_at) VALUES(1, ?, ?)",
                (hash_password(payload.password), utc_now()),
            )
            return _create_session(connection, response)

    @app.post("/api/v1/auth/login")
    def login(payload: LoginRequest, response: Response) -> dict:
        with db() as connection:
            row = connection.execute("SELECT password_hash FROM admins WHERE id = 1").fetchone()
            if not row or not verify_password(payload.password, row["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return _create_session(connection, response)

    @app.post("/api/v1/auth/logout")
    def logout(response: Response, vpn_bench_session: str | None = Cookie(default=None)) -> dict:
        if vpn_bench_session:
            with db() as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(vpn_bench_session),))
        response.delete_cookie("vpn_bench_session", httponly=True, samesite="lax")
        return {"ok": True}

    @app.post("/api/v1/auth/change-password")
    def change_password(payload: ChangePasswordRequest, response: Response, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            row = connection.execute("SELECT password_hash FROM admins WHERE id = 1").fetchone()
            if not row or not verify_password(payload.current_password, row["password_hash"]):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
            connection.execute(
                "UPDATE admins SET password_hash = ? WHERE id = 1",
                (hash_password(payload.new_password),),
            )
            connection.execute("DELETE FROM sessions")
            return _create_session(connection, response)

    @app.get("/api/v1/auth/me")
    def me(_: str = Depends(require_auth)) -> dict:
        return {"authenticated": True, "role": "admin"}

    @app.get("/api/v1/providers")
    def providers(_: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, name, display_name, enabled, metadata_json, last_updated_at, created_at "
                "FROM providers ORDER BY COALESCE(display_name, name)"
            ).fetchall()
        return [dict(row) | {"metadata": json_loads(row["metadata_json"])} for row in rows]

    @app.post("/api/v1/providers")
    def add_provider(payload: ProviderRequest, _: str = Depends(require_auth)) -> dict:
        provider_id = uuid4().hex
        with db() as connection:
            connection.execute(
                "INSERT INTO providers(id, name, display_name, subscription_url_encrypted, enabled, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (
                    provider_id,
                    payload.name,
                    payload.display_name,
                    encrypt_subscription_url(payload.subscription_url),
                    int(payload.enabled),
                    utc_now(),
                ),
            )
        return {"id": provider_id, "name": payload.name, "display_name": payload.display_name}

    @app.put("/api/v1/providers/{provider_id}")
    def update_provider(provider_id: str, payload: ProviderRequest, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            row = connection.execute("SELECT id FROM providers WHERE id = ?", (provider_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")
            connection.execute(
                "UPDATE providers SET name = ?, display_name = ?, subscription_url_encrypted = ?, enabled = ? WHERE id = ?",
                (payload.name, payload.display_name, encrypt_subscription_url(payload.subscription_url), int(payload.enabled), provider_id),
            )
        return {"id": provider_id, "name": payload.name, "display_name": payload.display_name, "enabled": payload.enabled}

    @app.post("/api/v1/providers/{provider_id}/sync")
    def sync_provider(provider_id: str, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            provider = connection.execute(
                "SELECT id, name, display_name, subscription_url_encrypted FROM providers WHERE id = ?",
                (provider_id,),
            ).fetchone()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        try:
            url = decrypt_subscription_url(provider["subscription_url_encrypted"])
            body, headers = fetch_subscription(url)
            imported = parse_subscription(body)
        except SubscriptionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        provider_name = provider["name"]
        if not provider_name or provider_name == "Определяется":
            from urllib.parse import urlsplit
            provider_name = urlsplit(url).hostname or "Provider"

        metadata = _subscription_metadata(headers)
        now = utc_now()
        with db() as connection:
            connection.execute(
                "UPDATE servers SET active = 0 WHERE provider_id = ?",
                (provider_id,),
            )
            for server in imported:
                import json
                existing = connection.execute(
                    "SELECT provider_id FROM servers WHERE id = ?",
                    (server.id,),
                ).fetchone()
                server_id = (
                    server.id
                    if not existing or existing["provider_id"] == provider_id
                    else uuid5(NAMESPACE_URL, f"{provider_id}:{server.id}").hex
                )
                connection.execute(
                    "INSERT INTO servers(id, provider_id, provider, name, protocol, host, port, transport, security, metadata_json, active, last_seen_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "provider_id=excluded.provider_id, provider=excluded.provider, name=excluded.name, "
                    "protocol=excluded.protocol, host=excluded.host, port=excluded.port, "
                    "transport=excluded.transport, security=excluded.security, metadata_json=excluded.metadata_json, "
                    "active=1, last_seen_at=excluded.last_seen_at",
                    (
                        server_id,
                        provider_id,
                        provider_name,
                        server.name,
                        server.protocol,
                        server.host,
                        server.port,
                        server.transport,
                        server.security,
                        json.dumps(server.raw, ensure_ascii=False),
                        1,
                        now,
                    ),
                )
            connection.execute(
                "UPDATE providers SET name = ?, metadata_json = ?, last_updated_at = ? WHERE id = ?",
                (provider_name, json.dumps(metadata, ensure_ascii=False), now, provider_id),
            )
        return {
            "provider_id": provider_id,
            "name": provider_name,
            "servers": len(imported),
            "metadata": metadata,
            "updated_at": now,
        }

    @app.get("/api/v1/servers")
    def servers(_: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, provider, provider_id, name, protocol, host, port, transport, security, active, last_seen_at, metadata_json "
                "FROM servers ORDER BY active DESC, provider, name"
            ).fetchall()
        return [
            dict(row)
            | {"metadata": json_loads(row["metadata_json"])}
            | {"capabilities": [item.__dict__ for item in detect_capabilities(row["protocol"], row["transport"])]}
            for row in rows
        ]

    @app.get("/api/v1/servers/{server_id}")
    def server_detail(server_id: str, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            row = connection.execute(
                "SELECT id, provider_id, provider, name, protocol, host, port, transport, security, active, last_seen_at, metadata_json FROM servers WHERE id = ?",
                (server_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Server not found")
            results = connection.execute(
                "SELECT started_at, duration_seconds, success, latency_ms, jitter_ms, packet_loss_percent, download_mbps, upload_mbps, dns_ok, http_ok, whitelist_ok, details_json FROM test_results WHERE server_id = ? ORDER BY started_at DESC LIMIT 200",
                (server_id,),
            ).fetchall()
        data = dict(row) | {"metadata": json_loads(row["metadata_json"])}
        data["capabilities"] = [item.__dict__ for item in detect_capabilities(row["protocol"], row["transport"])]
        data["results"] = [dict(item) | {"details": json_loads(item["details_json"])} for item in results]
        return data

    @app.get("/api/v1/filters")
    def filters(scope: str = "test", _: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, scope, expression, mode, position FROM server_filters "
                "WHERE scope = ? ORDER BY position, id", (scope,)
            ).fetchall()
        return [dict(row) for row in rows]

    @app.put("/api/v1/filters")
    def replace_filters(payload: FilterRequest, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            connection.execute("DELETE FROM server_filters WHERE scope = ?", (payload.scope,))
            for position, expression in enumerate(payload.expressions):
                if expression.strip():
                    connection.execute(
                        "INSERT INTO server_filters(scope, expression, mode, position) VALUES(?, ?, ?, ?)",
                        (payload.scope, expression.strip(), payload.mode, position),
                    )
        return {"scope": payload.scope, "mode": payload.mode, "expressions": payload.expressions}

    @app.get("/api/v1/tests/latest")
    def latest_test(_: str = Depends(require_auth)) -> dict:
        state = manager.latest()
        return state.as_dict() if state else {"status": "idle"}

    @app.get("/api/v1/tests/{run_id}")
    def test_status(run_id: str, _: str = Depends(require_auth)) -> dict:
        state = manager.get(run_id)
        if not state:
            raise HTTPException(status_code=404, detail="Test run not found")
        return state.as_dict()

    @app.post("/api/v1/tests")
    def start_test(payload: TestStartRequest, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            placeholders = ",".join("?" for _ in payload.server_ids)
            rows = connection.execute(
                f"SELECT id, name, provider, protocol, host, port, transport, security, metadata_json "
                f"FROM servers WHERE active = 1 AND id IN ({placeholders})", payload.server_ids
            ).fetchall()
        if len(rows) != len(set(payload.server_ids)):
            raise HTTPException(status_code=400, detail="One or more selected servers do not exist")
        if manager.latest() and manager.latest().status in {"running", "stopping"}:
            raise HTTPException(status_code=409, detail="A test campaign is already running")

        run_id = uuid4().hex
        names = {row["id"]: row["name"] for row in rows}
        server_data = {
            row["id"]: {
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "protocol": row["protocol"],
                "host": row["host"],
                "port": row["port"],
                "transport": row["transport"],
                "security": row["security"],
                "metadata": json_loads(row["metadata_json"]),
            }
            for row in rows
        }

        with db() as connection:
            started_at = utc_now()
            connection.execute(
                "INSERT INTO test_runs(id,status,scheduling_mode,planned_seconds,started_at,total_servers,message) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    run_id,
                    "running",
                    payload.scheduling_mode,
                    payload.duration_seconds,
                    started_at,
                    len(payload.server_ids),
                    "Test campaign started.",
                ),
            )
            for position, server_id in enumerate(payload.server_ids):
                connection.execute(
                    "INSERT INTO test_run_servers(run_id,server_id,position) VALUES(?,?,?)",
                    (run_id, server_id, position),
                )

        def on_server(server_id: str, allocation: float, stop_event) -> bool:
            def on_result(result: dict) -> None:
                with db() as connection:
                    import json
                    connection.execute(
                        "INSERT INTO test_results(run_id,server_id,started_at,duration_seconds,success,latency_ms,jitter_ms,"
                        "packet_loss_percent,download_mbps,upload_mbps,dns_ok,http_ok,whitelist_ok,details_json) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            run_id,
                            result["server_id"],
                            result["started_at"],
                            result["duration_seconds"],
                            int(result["success"]),
                            result["latency_ms"],
                            result["jitter_ms"],
                            result["packet_loss_percent"],
                            (result.get("details", {}).get("throughput") or {}).get("mbps"),
                            (result.get("details", {}).get("upload") or {}).get("mbps"),
                            int(result["dns_ok"]) if result["dns_ok"] is not None else None,
                            int(result["http_ok"]) if result["http_ok"] is not None else None,
                            (
                                None
                                if result.get("details", {}).get("whitelist_ok") is None
                                else int(bool(result.get("details", {}).get("whitelist_ok")))
                            )
                            if result.get("details", {}).get("whitelist")
                            else None,
                            json.dumps(result["details"], ensure_ascii=False),
                        ),
                    )

            return worker.run_server(
                server_data[server_id],
                allocation,
                stop_event,
                on_result=on_result,
            )

        state = manager.create(
            run_id,
            payload.server_ids,
            payload.duration_seconds,
            payload.scheduling_mode,
            names,
            on_server=on_server,
        )
        return state.as_dict()

    @app.get("/api/v1/screening/latest")
    def latest_screening(_: str = Depends(require_auth)) -> dict:
        state = screening.latest()
        return state.as_dict() if state else {"status": "idle"}

    @app.get("/api/v1/screening/{run_id}")
    def screening_status(run_id: str, _: str = Depends(require_auth)) -> dict:
        state = screening.get(run_id)
        if state:
            return state.as_dict()
        with db() as connection:
            row = connection.execute(
                "SELECT id, status, started_at, finished_at, total_servers, shortlisted_servers, message, shortlist_json "
                "FROM screening_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Screening run not found")
        return dict(row) | {"shortlist": json_loads(row["shortlist_json"])}

    @app.get("/api/v1/screening/{run_id}/results")
    def screening_results(run_id: str, _: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, server_id, pass_no, started_at, duration_seconds, success, latency_ms, "
                "jitter_ms, packet_loss_percent, dns_ok, http_ok, whitelist_ok, details_json "
                "FROM screening_results WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [dict(row) | {"details": json_loads(row["details_json"])} for row in rows]

    @app.post("/api/v1/screening")
    def start_screening(payload: ScreeningStartRequest, _: str = Depends(require_auth)) -> dict:
        with db() as connection:
            placeholders = ",".join("?" for _ in payload.server_ids)
            rows = connection.execute(
                f"SELECT id, name, provider, protocol, host, port, transport, security, metadata_json "
                f"FROM servers WHERE active = 1 AND id IN ({placeholders})",
                payload.server_ids,
            ).fetchall()
        if len(rows) != len(set(payload.server_ids)):
            raise HTTPException(status_code=400, detail="One or more selected servers are inactive or do not exist")

        current = screening.latest()
        if current and current.status in {"running", "stopping"}:
            raise HTTPException(status_code=409, detail="A screening campaign is already running")

        server_data = {
            row["id"]: {
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "protocol": row["protocol"],
                "host": row["host"],
                "port": row["port"],
                "transport": row["transport"],
                "security": row["security"],
                "metadata": json_loads(row["metadata_json"]),
            }
            for row in rows
        }
        run_id = uuid4().hex
        plan = ScreeningPlan(
            first_pass_seconds=payload.first_pass_seconds,
            second_pass_seconds=payload.second_pass_seconds,
            repeat_passes=payload.repeat_passes,
            max_shortlist=payload.max_shortlist,
        )
        screening.plan = plan

        with db() as connection:
            started_at = utc_now()
            connection.execute(
                "INSERT INTO screening_runs(id,status,started_at,total_servers,message) VALUES(?,?,?,?,?)",
                (run_id, "running", started_at, len(server_data), "Screening campaign started."),
            )

        def save_result(server_id: str, pass_no: int, result: dict) -> None:
            with db() as connection:
                import json
                connection.execute(
                    "INSERT INTO screening_results(run_id,server_id,pass_no,started_at,duration_seconds,success,"
                    "latency_ms,jitter_ms,packet_loss_percent,dns_ok,http_ok,whitelist_ok,details_json) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        run_id, server_id, pass_no, result["started_at"], result["duration_seconds"],
                        int(result["success"]), result["latency_ms"], result["jitter_ms"],
                        result["packet_loss_percent"],
                        int(result["dns_ok"]) if result["dns_ok"] is not None else None,
                        int(result["http_ok"]) if result["http_ok"] is not None else None,
                        (
                            int(bool(result.get("details", {}).get("whitelist_ok")))
                            if result.get("details", {}).get("whitelist_ok") is not None else None
                        ),
                        json.dumps(result.get("details", {}), ensure_ascii=False),
                    ),
                )

        def finish(state, samples) -> None:
            with db() as connection:
                import json
                connection.execute(
                    "UPDATE screening_runs SET status=?, finished_at=?, shortlisted_servers=?, message=?, shortlist_json=? WHERE id=?",
                    (
                        state.status, utc_now(), len(state.shortlisted_servers), state.message,
                        json.dumps(state.shortlisted_servers), run_id,
                    ),
                )

        state = screening.start(
            run_id,
            server_data,
            on_result=save_result,
            on_finish=finish,
        )
        return state.as_dict()

    @app.post("/api/v1/screening/{run_id}/start-test")
    def start_test_from_screening(
        run_id: str,
        payload: TestStartRequest,
        _: str = Depends(require_auth),
    ) -> dict:
        state = screening.get(run_id)
        if not state or state.status != "completed":
            raise HTTPException(status_code=409, detail="Screening run is not completed")
        if not state.shortlisted_servers:
            raise HTTPException(status_code=409, detail="Screening produced no shortlist")
        with db() as connection:
            placeholders = ",".join("?" for _ in state.shortlisted_servers)
            rows = connection.execute(
                f"SELECT id FROM servers WHERE active = 1 AND id IN ({placeholders})",
                state.shortlisted_servers,
            ).fetchall()
        if len(rows) != len(state.shortlisted_servers):
            raise HTTPException(status_code=409, detail="One or more shortlisted servers are no longer active")

        return start_test(
            TestStartRequest(
                server_ids=state.shortlisted_servers,
                duration_seconds=payload.duration_seconds,
                scheduling_mode=payload.scheduling_mode,
            ),
            "",
        )

    @app.post("/api/v1/screening/{run_id}/stop")
    def stop_screening(run_id: str, _: str = Depends(require_auth)) -> dict:
        if not screening.stop(run_id):
            raise HTTPException(status_code=404, detail="Active screening run not found")
        return {"ok": True}

    @app.post("/api/v1/tests/{run_id}/stop")
    def stop_test(run_id: str, _: str = Depends(require_auth)) -> dict:
        if not manager.stop(run_id):
            raise HTTPException(status_code=404, detail="Active test run not found")
        return {"ok": True}

    @app.get("/api/v1/tests/{run_id}/results")
    def test_results(run_id: str, _: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, server_id, started_at, duration_seconds, success, latency_ms, jitter_ms, "
                "packet_loss_percent, download_mbps, upload_mbps, dns_ok, http_ok, whitelist_ok, details_json "
                "FROM test_results WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [
            dict(row) | {"details": json_loads(row["details_json"])}
            for row in rows
        ]

    @app.get("/api/v1/analytics")
    def analytics(_: str = Depends(require_auth)) -> dict:
        with db() as connection:
            rows = connection.execute(
                "SELECT s.id, s.provider, s.name, s.protocol, s.transport, "
                "COUNT(r.id) AS samples, "
                "AVG(CASE WHEN r.success = 1 THEN 1.0 ELSE 0.0 END) * 100 AS availability, "
                "AVG(r.latency_ms) AS latency_ms, "
                "AVG(r.jitter_ms) AS jitter_ms, "
                "AVG(r.packet_loss_percent) AS packet_loss_percent, "
                "AVG(r.download_mbps) AS download_mbps, "
                "AVG(r.upload_mbps) AS upload_mbps "
                "FROM servers s LEFT JOIN test_results r ON r.server_id = s.id "
                "GROUP BY s.id ORDER BY availability DESC, latency_ms ASC, s.provider, s.name"
            ).fetchall()
        return [dict(row) for row in rows]

    @app.get("/api/v1/dashboard")
    def dashboard(_: str = Depends(require_auth)) -> dict:
        latest = manager.latest()
        with db() as connection:
            provider_count = connection.execute("SELECT COUNT(*) FROM providers WHERE enabled = 1").fetchone()[0]
            server_count = connection.execute("SELECT COUNT(*) FROM servers").fetchone()[0]
            result_count = connection.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]
        return {
            "providers": provider_count,
            "servers": server_count,
            "results": result_count,
            "test": latest.as_dict() if latest else {"status": "idle"},
        }

    return app


def _subscription_metadata(headers: dict[str, str]) -> dict:
    raw = headers.get("subscription-userinfo", "")
    values = {}
    for item in raw.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            values[key.strip()] = value.strip()
    metadata = {}
    for key in ("upload", "download", "total", "expire"):
        if key in values:
            try:
                metadata[key] = int(values[key])
            except ValueError:
                metadata[key] = values[key]
    for key in ("profile-title", "profile-update-interval"):
        if key in headers:
            metadata[key] = headers[key]
    return metadata


def _create_session(connection: sqlite3.Connection, response: Response) -> dict:
    token = create_session_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    connection.execute(
        "INSERT INTO sessions(token_hash, created_at, expires_at) VALUES(?,?,?)",
        (token_hash(token), utc_now(), expires.isoformat()),
    )
    response.set_cookie(
        "vpn_bench_session",
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {"ok": True, "expires_at": expires.isoformat()}

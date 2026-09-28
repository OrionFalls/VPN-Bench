from __future__ import annotations

import hashlib
import secrets
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import Config
from cryptography.fernet import Fernet
from .db import connect, get_meta, initialize, json_loads, set_meta
from .security import create_session_token, hash_password, verify_password
from .test_runner import TestRunManager
from .ui import page


SESSION_DAYS = 7


def encrypt_subscription_url(url: str) -> str:
    key = os.environ.get("VPN_BENCH_SECRET")
    if not key:
        raise RuntimeError("VPN_BENCH_SECRET is not configured")
    return Fernet(key.encode()).encrypt(url.encode()).decode()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SetupRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class ProviderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
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


def build_app(config: Config) -> FastAPI:
    initialize(config.app.database)
    manager = TestRunManager()
    app = FastAPI(title="VPN-Bench API", version=config.app.version)

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

    @app.get("/api/v1/servers")
    def servers(_: str = Depends(require_auth)) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, provider, provider_id, name, protocol, host, port, transport, security, metadata_json "
                "FROM servers ORDER BY provider, name"
            ).fetchall()
        return [dict(row) | {"metadata": json_loads(row["metadata_json"])} for row in rows]

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
                f"SELECT id, name FROM servers WHERE id IN ({placeholders})", payload.server_ids
            ).fetchall()
        if len(rows) != len(set(payload.server_ids)):
            raise HTTPException(status_code=400, detail="One or more selected servers do not exist")
        if manager.latest() and manager.latest().status in {"running", "stopping"}:
            raise HTTPException(status_code=409, detail="A test campaign is already running")

        run_id = uuid4().hex
        names = {row["id"]: row["name"] for row in rows}
        state = manager.create(
            run_id,
            payload.server_ids,
            payload.duration_seconds,
            payload.scheduling_mode,
            names,
        )
        with db() as connection:
            connection.execute(
                "INSERT INTO test_runs(id,status,scheduling_mode,planned_seconds,started_at,total_servers,message) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    run_id,
                    state.status,
                    state.scheduling_mode,
                    state.planned_seconds,
                    datetime.fromtimestamp(state.started_at, timezone.utc).isoformat(),
                    state.total_servers,
                    state.message,
                ),
            )
            for position, server_id in enumerate(payload.server_ids):
                connection.execute(
                    "INSERT INTO test_run_servers(run_id,server_id,position) VALUES(?,?,?)",
                    (run_id, server_id, position),
                )
        return state.as_dict()

    @app.post("/api/v1/tests/{run_id}/stop")
    def stop_test(run_id: str, _: str = Depends(require_auth)) -> dict:
        if not manager.stop(run_id):
            raise HTTPException(status_code=404, detail="Active test run not found")
        return {"ok": True}

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

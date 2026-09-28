"""Isolated sing-box process adapter.

The adapter exposes a local mixed HTTP/SOCKS proxy instead of changing the
host's default route. Each connection gets its own temporary config and
process. The container itself is the isolation boundary.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .base import ConnectionHandle, VPNAdapter


class SingBoxError(RuntimeError):
    pass


class SingBoxAdapter(VPNAdapter):
    def __init__(self, binary: str = "sing-box", work_dir: str = "/tmp/vpn-bench") -> None:
        self.binary = binary
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def import_servers(self, source: str):
        from .subscription import parse_subscription
        for server in parse_subscription(source):
            yield {
                "id": server.id,
                "name": server.name,
                "protocol": server.protocol,
                "host": server.host,
                "port": server.port,
                "transport": server.transport,
                "security": server.security,
                "metadata": server.raw,
            }

    def connect(self, server: dict[str, Any]) -> ConnectionHandle:
        if not shutil.which(self.binary):
            raise SingBoxError(
                f"sing-box binary not found: {self.binary}. "
                "Install it in the benchmark image or configure VPN_BENCH_SING_BOX."
            )

        raw = server.get("metadata") or {}
        uri = raw.get("uri") if isinstance(raw, dict) else None
        if not uri:
            raise SingBoxError("Server does not contain a source URI")

        config = build_config(uri)
        proxy_port = _free_port()
        config["inbounds"][0]["listen_port"] = proxy_port

        directory = Path(tempfile.mkdtemp(prefix="vpn-bench-", dir=self.work_dir))
        config_path = directory / "config.json"
        log_path = directory / "sing-box.log"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        log_file = log_path.open("w", encoding="utf-8")

        check = subprocess.run(
            [self.binary, "check", "-c", str(config_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check.returncode != 0:
            log_file.close()
            shutil.rmtree(directory, ignore_errors=True)
            raise SingBoxError(f"sing-box rejected config: {check.stderr.strip() or check.stdout.strip()}")

        process = subprocess.Popen(
            [self.binary, "run", "-c", str(config_path)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=directory,
        )

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                log_file.close()
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                shutil.rmtree(directory, ignore_errors=True)
                raise SingBoxError(f"sing-box exited during startup: {detail}")
            if _port_open("127.0.0.1", proxy_port):
                return ConnectionHandle(
                    server_id=str(server["id"]),
                    metadata={
                        "process": process,
                        "proxy_url": f"http://127.0.0.1:{proxy_port}",
                        "socks_url": f"socks5://127.0.0.1:{proxy_port}",
                        "directory": str(directory),
                        "log_path": str(log_path),
                        "log_file": log_file,
                    },
                )
            time.sleep(0.1)

        process.terminate()
        log_file.close()
        shutil.rmtree(directory, ignore_errors=True)
        raise SingBoxError("Timed out waiting for sing-box proxy")

    def disconnect(self, handle: ConnectionHandle) -> None:
        process = handle.metadata.get("process")
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        log_file = handle.metadata.get("log_file")
        if log_file:
            log_file.close()
        directory = handle.metadata.get("directory")
        if directory:
            shutil.rmtree(directory, ignore_errors=True)


def build_config(uri: str) -> dict[str, Any]:
    parsed = urlsplit(uri)
    scheme = parsed.scheme.lower()
    if scheme == "vmess":
        return _vmess_config(uri)
    if scheme not in {"vless", "trojan", "ss", "hysteria2", "hy2"}:
        raise SingBoxError(f"Unsupported sing-box URI scheme: {scheme}")

    query = parse_qs(parsed.query)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        raise SingBoxError("Server host and port are required")

    outbound: dict[str, Any] = {
        "type": "hysteria2" if scheme == "hy2" else scheme,
        "tag": "proxy",
        "server": host,
        "server_port": port,
    }

    username = parsed.username or ""
    password = parsed.password or ""
    if scheme == "vless":
        outbound["uuid"] = username
        if query.get("flow"):
            outbound["flow"] = query["flow"][0]
    elif scheme == "trojan":
        outbound["password"] = username or password
    elif scheme == "ss":
        outbound["method"] = username
        outbound["password"] = password
    else:
        outbound["password"] = username or password

    _apply_tls(outbound, query, parsed.hostname)
    _apply_transport(outbound, query)

    return _base_config(outbound)


def _apply_tls(outbound: dict[str, Any], query: dict[str, list[str]], fallback_sni: str | None) -> None:
    security = (query.get("security", [""])[0] or "").lower()
    if security != "tls" and not query.get("sni") and not query.get("fp") and not query.get("pbk"):
        return

    tls: dict[str, Any] = {"enabled": True}
    sni = query.get("sni", query.get("servername", [fallback_sni or ""]))[0]
    if sni:
        tls["server_name"] = sni
    if query.get("allowInsecure", ["0"])[0].lower() in {"1", "true"}:
        tls["insecure"] = True
    if query.get("alpn"):
        tls["alpn"] = [x for x in query["alpn"][0].split(",") if x]
    if query.get("fp"):
        tls["utls"] = {"enabled": True, "fingerprint": query["fp"][0]}
    if query.get("pbk"):
        reality = {"enabled": True, "public_key": query["pbk"][0]}
        if query.get("sid"):
            reality["short_id"] = query["sid"][0]
        tls["reality"] = reality
    outbound["tls"] = tls


def _apply_transport(outbound: dict[str, Any], query: dict[str, list[str]]) -> None:
    transport = (query.get("type", query.get("network", ["tcp"]))[0] or "tcp").lower()
    if transport in {"tcp", "none"}:
        return
    if transport == "xhttp":
        raise SingBoxError("XHTTP requires an adapter for a core that supports XHTTP")
    mapping = {"ws": "ws", "websocket": "ws", "grpc": "grpc", "http": "http", "httpupgrade": "httpupgrade", "quic": "quic"}
    if transport not in mapping:
        raise SingBoxError(f"Unsupported V2Ray transport: {transport}")
    item: dict[str, Any] = {"type": mapping[transport]}
    if transport in {"ws", "websocket", "httpupgrade"} and query.get("path"):
        item["path"] = query["path"][0]
    if transport == "grpc" and query.get("serviceName"):
        item["service_name"] = query["serviceName"][0]
    if transport == "http":
        if query.get("path"):
            item["path"] = query["path"][0]
        if query.get("host"):
            item["host"] = query["host"]
    outbound["transport"] = item


def _vmess_config(uri: str) -> dict[str, Any]:
    from .subscription import _parse_vmess_uri
    server = _parse_vmess_uri(uri)
    if not server:
        raise SingBoxError("Invalid VMess URI")
    raw = server.raw
    outbound: dict[str, Any] = {
        "type": "vmess",
        "tag": "proxy",
        "server": server.host,
        "server_port": server.port,
        "uuid": raw.get("id", ""),
        "security": raw.get("scy", "auto"),
        "alter_id": int(raw.get("aid", 0) or 0),
        "network": raw.get("net", "tcp"),
    }
    query = {key: [str(value)] for key, value in raw.items() if value is not None}
    if str(raw.get("tls", "")).lower() == "tls":
        query["security"] = ["tls"]
        if raw.get("sni"):
            query["sni"] = [raw["sni"]]
        _apply_tls(outbound, query, server.host)
    _apply_transport(outbound, query)
    return _base_config(outbound)


def _base_config(outbound: dict[str, Any]) -> dict[str, Any]:
    return {
        "log": {"level": "warn"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "proxy-in",
                "listen": "127.0.0.1",
                "listen_port": 0,
            }
        ],
        "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
        "route": {"final": "proxy"},
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False

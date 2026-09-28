"""Xray adapter for transports that sing-box does not cover, notably XHTTP."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from ..network_namespace import NamespaceManager

from .base import ConnectionHandle, VPNAdapter


class XrayError(RuntimeError):
    pass


class XrayAdapter(VPNAdapter):
    def __init__(self, binary: str = "xray", work_dir: str = "/tmp/vpn-bench") -> None:
        self.binary = binary
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.namespace_manager = NamespaceManager()

    def import_servers(self, source: str):
        from ..subscription import parse_subscription
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
            raise XrayError(f"Xray binary not found: {self.binary}")

        raw = server.get("metadata") or {}
        uri = raw.get("uri") if isinstance(raw, dict) else None
        if not uri:
            raise XrayError("Server does not contain a source URI")

        config = build_config(uri)
        proxy_port = _free_port()
        namespace = self.namespace_manager.create(str(server["id"]))
        config["inbounds"][0]["listen"] = namespace.namespace_ip
        config["inbounds"][0]["port"] = proxy_port

        directory = Path(tempfile.mkdtemp(prefix="vpn-bench-xray-", dir=self.work_dir))
        config_path = directory / "config.json"
        log_path = directory / "xray.log"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        log_file = log_path.open("w", encoding="utf-8")

        command_prefix = self.namespace_manager.exec_prefix(namespace)
        check = subprocess.run(
            command_prefix + [self.binary, "run", "-test", "-config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if check.returncode != 0:
            log_file.close()
            shutil.rmtree(directory, ignore_errors=True)
            self.namespace_manager.destroy(namespace)
            raise XrayError(f"Xray rejected config: {check.stderr.strip() or check.stdout.strip()}")

        process = subprocess.Popen(
            command_prefix + [self.binary, "run", "-c", str(config_path)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=directory,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                log_file.close()
                shutil.rmtree(directory, ignore_errors=True)
                self.namespace_manager.destroy(namespace)
                raise XrayError(f"Xray exited during startup: {detail}")
            if _port_open(namespace.namespace_ip, proxy_port):
                self.namespace_manager.enable_kill_switch(
                    namespace,
                    [(str(server["host"]), int(server["port"]), "tcp")],
                )
                return ConnectionHandle(
                    server_id=str(server["id"]),
                    metadata={
                        "process": process,
                        "proxy_url": f"http://{namespace.namespace_ip}:{proxy_port}",
                        "socks_url": f"socks5://{namespace.namespace_ip}:{proxy_port}",
                        "directory": str(directory),
                        "log_file": log_file,
                        "namespace": namespace,
                    },
                )
            time.sleep(0.1)

        process.terminate()
        log_file.close()
        shutil.rmtree(directory, ignore_errors=True)
        raise XrayError("Timed out waiting for Xray proxy")

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
        namespace = handle.metadata.get("namespace")
        if namespace:
            self.namespace_manager.destroy(namespace)


def build_config(uri: str) -> dict[str, Any]:
    parsed = urlsplit(uri)
    scheme = parsed.scheme.lower()
    if scheme != "vless":
        raise XrayError(f"Xray adapter currently supports VLESS URIs, got {scheme}")

    host = parsed.hostname
    port = parsed.port
    uuid = parsed.username
    if not host or not port or not uuid:
        raise XrayError("VLESS host, port and UUID are required")

    query = parse_qs(parsed.query)
    transport = query.get("type", ["tcp"])[0]
    security = query.get("security", ["none"])[0]

    user: dict[str, Any] = {
        "id": uuid,
        "encryption": "none",
        "level": 0,
    }
    if query.get("flow"):
        user["flow"] = query["flow"][0]

    outbound: dict[str, Any] = {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": host,
                "port": port,
                "users": [user],
            }]
        },
        "streamSettings": {
            "network": transport,
            "security": security,
        },
    }

    stream = outbound["streamSettings"]
    if security == "reality":
        stream["realitySettings"] = {
            "serverName": query.get("sni", query.get("servername", [host]))[0],
            "fingerprint": query.get("fp", ["chrome"])[0],
            "publicKey": query.get("pbk", [""])[0],
            "shortId": query.get("sid", [""])[0],
            "spiderX": query.get("spx", [""])[0],
        }
    elif security == "tls":
        stream["tlsSettings"] = {
            "serverName": query.get("sni", query.get("servername", [host]))[0],
            "allowInsecure": query.get("allowInsecure", ["0"])[0].lower() in {"1", "true"},
        }

    _apply_transport(stream, query, transport)

    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": 0,
            "protocol": "socks",
            "settings": {"udp": True},
        }],
        "outbounds": [outbound],
    }


def _apply_transport(stream: dict[str, Any], query: dict[str, list[str]], transport: str) -> None:
    if transport in {"tcp", "raw", "none"}:
        stream["network"] = "tcp"
        return

    if transport == "xhttp":
        extra: dict[str, Any] = {}
        if query.get("extra"):
            try:
                extra = json.loads(query["extra"][0])
            except json.JSONDecodeError:
                extra = {}
        stream["xhttpSettings"] = {
            "path": query.get("path", ["/"])[0],
            "host": query.get("host", [""])[0],
            "mode": query.get("mode", ["auto"])[0],
            "extra": extra,
        }
        return

    if transport == "grpc":
        stream["grpcSettings"] = {
            "serviceName": query.get("serviceName", [""])[0],
        }
        return

    if transport in {"ws", "websocket"}:
        stream["network"] = "ws"
        stream["wsSettings"] = {
            "path": query.get("path", ["/"])[0],
            "headers": {"Host": query.get("host", [""])[0]} if query.get("host") else {},
        }
        return

    if transport == "httpupgrade":
        stream["httpupgradeSettings"] = {
            "path": query.get("path", ["/"])[0],
            "host": query.get("host", [""])[0],
        }
        return

    raise XrayError(f"Unsupported Xray transport: {transport}")


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

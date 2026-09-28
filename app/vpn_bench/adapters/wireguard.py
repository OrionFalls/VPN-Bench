"""Standard WireGuard adapter using wg-quick inside a per-job namespace."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import ConnectionHandle, VPNAdapter
from ..network_namespace import NamespaceManager


class WireGuardError(RuntimeError):
    pass


class WireGuardAdapter(VPNAdapter):
    def __init__(
        self,
        binary: str = "wg-quick",
        proxy_binary: str = "sing-box-lx",
        work_dir: str = "/tmp/vpn-bench",
    ) -> None:
        self.binary = binary
        self.proxy_binary = proxy_binary
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.namespace_manager = NamespaceManager()

    def import_servers(self, source: str):
        from .subscription import parse_subscription

        for server in parse_subscription(source):
            if server.protocol not in {"wireguard", "amneziawg"}:
                continue
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
        if server.get("protocol") != "wireguard":
            raise WireGuardError("Only standard WireGuard is supported by this adapter")

        if not shutil.which(self.binary):
            raise WireGuardError("wg-quick is not installed")
        if not shutil.which(self.proxy_binary):
            raise WireGuardError(f"sing-box binary not found: {self.proxy_binary}")

        raw = server.get("metadata") or {}
        config_text = build_wireguard_config(raw)
        namespace = self.namespace_manager.create(str(server["id"]))
        directory = Path(tempfile.mkdtemp(prefix="vpn-bench-wg-", dir=self.work_dir))
        config_path = directory / "wg0.conf"
        proxy_config_path = directory / "proxy.json"
        log_path = directory / "proxy.log"
        config_path.write_text(config_text, encoding="utf-8")

        try:
            self._run(namespace, [self.binary, "up", str(config_path)], timeout=20)

            proxy_port = _free_port()
            proxy_config_path.write_text(
                _proxy_config(namespace.namespace_ip, proxy_port),
                encoding="utf-8",
            )
            log_file = log_path.open("w", encoding="utf-8")
            command = self.namespace_manager.exec_prefix(namespace) + [
                self.proxy_binary, "run", "-c", str(proxy_config_path)
            ]
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=directory,
            )

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                    log_file.close()
                    raise WireGuardError(f"sing-box probe proxy exited: {detail}")
                if _port_open(namespace.namespace_ip, proxy_port):
                    return ConnectionHandle(
                        server_id=str(server["id"]),
                        metadata={
                            "process": process,
                            "proxy_url": f"http://{namespace.namespace_ip}:{proxy_port}",
                            "socks_url": f"socks5://{namespace.namespace_ip}:{proxy_port}",
                            "directory": str(directory),
                            "log_file": log_file,
                            "namespace": namespace,
                            "wg_config": str(config_path),
                            "wg_up": True,
                        },
                    )
                time.sleep(0.1)

            raise WireGuardError("Timed out waiting for WireGuard probe proxy")
        except Exception:
            self._cleanup_partial(namespace, directory)
            raise

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

        namespace = handle.metadata.get("namespace")
        config = handle.metadata.get("wg_config")
        if namespace and config:
            self._run(namespace, [self.binary, "down", config], timeout=20, check=False)
        directory = handle.metadata.get("directory")
        if directory:
            shutil.rmtree(directory, ignore_errors=True)
        if namespace:
            self.namespace_manager.destroy(namespace)

    def _cleanup_partial(self, namespace, directory: Path) -> None:
        config = directory / "wg0.conf"
        if config.exists():
            self._run(namespace, [self.binary, "down", str(config)], timeout=20, check=False)
        shutil.rmtree(directory, ignore_errors=True)
        self.namespace_manager.destroy(namespace)

    def _run(self, namespace, command: list[str], timeout: float, check: bool = True):
        args = self.namespace_manager.exec_prefix(namespace) + command
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode != 0:
            raise WireGuardError(result.stderr.strip() or result.stdout.strip() or "WireGuard command failed")
        return result


def build_wireguard_config(raw: dict[str, Any]) -> str:
    private_key = raw.get("private_key")
    addresses = raw.get("address") or raw.get("addresses") or raw.get("local_address")
    peers = raw.get("peers") or []
    if not private_key or not addresses or not isinstance(peers, list) or not peers:
        raise WireGuardError("Incomplete WireGuard configuration")

    if isinstance(addresses, str):
        addresses = [addresses]

    lines = ["[Interface]"]
    lines.append(f"PrivateKey = {private_key}")
    for address in addresses:
        lines.append(f"Address = {address}")

    for peer in peers:
        if not isinstance(peer, dict):
            continue
        public_key = peer.get("public_key") or peer.get("publicKey")
        endpoint_host = peer.get("address") or peer.get("server")
        endpoint_port = peer.get("port") or peer.get("server_port")
        allowed_ips = peer.get("allowed_ips") or peer.get("allowedIPs") or []
        if not public_key or not endpoint_host or not endpoint_port:
            continue
        if isinstance(allowed_ips, str):
            allowed_ips = [allowed_ips]
        if not allowed_ips:
            allowed_ips = ["0.0.0.0/0"]

        lines.extend(["", "[Peer]", f"PublicKey = {public_key}"])
        if peer.get("pre_shared_key") or peer.get("preshared_key"):
            lines.append(f"PresharedKey = {peer.get('pre_shared_key') or peer.get('preshared_key')}")
        lines.append(f"AllowedIPs = {', '.join(str(x) for x in allowed_ips)}")
        lines.append(f"Endpoint = {endpoint_host}:{int(endpoint_port)}")
        keepalive = peer.get("persistent_keepalive_interval") or peer.get("persistent_keepalive")
        if keepalive:
            lines.append(f"PersistentKeepalive = {int(keepalive)}")

    if not any(line.startswith("Endpoint = ") for line in lines):
        raise WireGuardError("WireGuard peer endpoint is missing")

    return "\n".join(lines) + "\n"


def _proxy_config(host: str, port: int) -> str:
    import json

    return json.dumps(
        {
            "log": {"level": "warn"},
            "inbounds": [
                {
                    "type": "mixed",
                    "tag": "probe-in",
                    "listen": host,
                    "listen_port": port,
                }
            ],
            "outbounds": [{"type": "direct", "tag": "direct"}],
            "route": {"final": "direct"},
        },
        indent=2,
    )


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_open(host: str, port: int) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False

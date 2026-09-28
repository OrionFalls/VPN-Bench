"""WireGuard and AmneziaWG adapters using isolated per-job namespaces."""

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
        if server.get("protocol") == "amneziawg":
            return self._connect_amneziawg(server)
        if server.get("protocol") != "wireguard":
            raise WireGuardError("Only WireGuard and AmneziaWG are supported by this adapter")

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
                    self.namespace_manager.enable_kill_switch(
                        namespace,
                        _wireguard_endpoints(raw),
                        interfaces=["wg0"],
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
                            "wg_config": str(config_path),
                            "wg_up": True,
                        },
                    )
                time.sleep(0.1)

            raise WireGuardError("Timed out waiting for WireGuard probe proxy")
        except Exception:
            self._cleanup_partial(namespace, directory)
            raise


    def _connect_amneziawg(self, server: dict[str, Any]) -> ConnectionHandle:
        """Run AWG through sing-box-lx's userspace WireGuard endpoint."""
        if not shutil.which(self.proxy_binary):
            raise WireGuardError(f"sing-box binary not found: {self.proxy_binary}")
        raw = server.get("metadata") or {}
        proxy_port = _free_port()
        config = build_amneziawg_config(raw, proxy_port)
        namespace = self.namespace_manager.create(str(server["id"]))
        directory = Path(tempfile.mkdtemp(prefix="vpn-bench-awg-", dir=self.work_dir))
        config_path = directory / "config.json"
        log_path = directory / "proxy.log"
        config_path.write_text(config, encoding="utf-8")
        log_file = None
        process = None
        try:
            self._run(namespace, [self.proxy_binary, "check", "-c", str(config_path)], timeout=15)
            log_file = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                self.namespace_manager.exec_prefix(namespace) + [
                    self.proxy_binary, "run", "-c", str(config_path)
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=directory,
            )
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                    raise WireGuardError(f"sing-box AWG proxy exited: {detail}")
                if _port_open("127.0.0.1", proxy_port, namespace):
                    self.namespace_manager.enable_kill_switch(
                        namespace, _wireguard_endpoints(raw)
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
            raise WireGuardError("Timed out waiting for AmneziaWG probe proxy")
        except Exception:
            if log_file:
                log_file.close()
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            shutil.rmtree(directory, ignore_errors=True)
            self.namespace_manager.destroy(namespace)
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


def _wireguard_endpoints(raw: dict[str, Any]) -> list[tuple[str, int, str]]:
    endpoints: list[tuple[str, int, str]] = []
    for peer in raw.get("peers") or []:
        if not isinstance(peer, dict):
            continue
        host = peer.get("address") or peer.get("server")
        port = peer.get("port") or peer.get("server_port")
        if host and port:
            endpoints.append((str(host), int(port), "udp"))
    return endpoints


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


def build_amneziawg_config(raw: dict[str, Any], proxy_port: int) -> str:
    import json

    private_key = raw.get("private_key")
    addresses = raw.get("address") or raw.get("addresses")
    peers = raw.get("peers") or []
    if not private_key or not addresses or not isinstance(peers, list) or not peers:
        raise WireGuardError("Incomplete AmneziaWG configuration")
    if isinstance(addresses, str):
        addresses = [addresses]

    normalized_peers = []
    for peer in peers:
        if not isinstance(peer, dict):
            continue
        address = peer.get("address") or peer.get("server")
        port = peer.get("port") or peer.get("server_port")
        public_key = peer.get("public_key") or peer.get("publicKey")
        if not address or not port or not public_key:
            continue
        allowed = peer.get("allowed_ips") or peer.get("allowedIPs") or ["0.0.0.0/0", "::/0"]
        if isinstance(allowed, str):
            allowed = [allowed]
        item = {
            "address": address,
            "port": int(port),
            "public_key": public_key,
            "allowed_ips": allowed,
        }
        psk = peer.get("pre_shared_key") or peer.get("preshared_key")
        if psk:
            item["pre_shared_key"] = psk
        keepalive = peer.get("persistent_keepalive_interval") or peer.get("persistent_keepalive")
        if keepalive:
            item["persistent_keepalive_interval"] = int(keepalive)
        normalized_peers.append(item)

    if not normalized_peers:
        raise WireGuardError("AmneziaWG peer endpoint is missing")

    endpoint = {
        "type": "wireguard",
        "tag": "awg-endpoint",
        "system": False,
        "mtu": int(raw.get("mtu") or 1280),
        "address": addresses,
        "private_key": private_key,
        "peers": normalized_peers,
    }
    for key in (
        "jc", "jmin", "jmax", "s1", "s2", "s3", "s4", "h1", "h2", "h3", "h4",
        "i1", "i2", "i3", "i4", "i5", "header_protection_key",
        "content_padding_addition", "rekey_after_time", "rekey_timeout",
        "reject_after_time", "keepalive_timeout", "max_handshake_attempts",
        "random_trailers", "disable_cookies", "id", "ip", "ib",
    ):
        if raw.get(key) is not None:
            endpoint[key] = raw[key]

    return json.dumps({
        "log": {"level": "warn"},
        "inbounds": [{
            "type": "mixed",
            "tag": "probe-in",
            "listen": "0.0.0.0",
            "listen_port": proxy_port,
        }],
        "endpoints": [endpoint],
        "route": {"final": "awg-endpoint"},
    }, indent=2)



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


def _port_open(host: str, port: int, namespace=None) -> bool:
    import socket
    if namespace is not None:
        result = subprocess.run(
            ["ip", "netns", "exec", namespace.name, "sh", "-c",
             f"python -c 'import socket; s=socket.create_connection((\"127.0.0.1\", {port}), .2); s.close()'"],
            capture_output=True,
        )
        return result.returncode == 0
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False

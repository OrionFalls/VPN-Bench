"""Per-job Linux network namespace management for the privileged worker."""

from __future__ import annotations

import ipaddress
import os
import re
import subprocess
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkNamespace:
    name: str
    host_ip: str
    namespace_ip: str
    prefix: int
    subnet: str
    host_veth: str
    namespace_veth: str
    proxy_url: str
    uplink: str


class NamespaceError(RuntimeError):
    pass


class NamespaceManager:
    """Create a small routed namespace without touching the Docker host route.

    The worker container owns both ends of the veth pair. The namespace gets
    a private default route through the worker namespace and NATs through the
    worker's existing Docker interface. VPN cores and their TUN devices stay
    inside this namespace.
    """

    def __init__(self, base_network: str = "10.250.0.0/16") -> None:
        self.base = ipaddress.ip_network(base_network, strict=False)
        if self.base.prefixlen > 24:
            raise NamespaceError("Namespace base network must be at least /24")
        self._lock = threading.Lock()
        self._counter = 0
        self._names: set[str] = set()

    def create(self, job_id: str) -> NetworkNamespace:
        self._require_commands()
        safe_id = re.sub(r"[^a-zA-Z0-9]", "", job_id)[:8] or "job"
        with self._lock:
            index = self._counter
            self._counter += 1

        # /30 per namespace: network, worker side, namespace side, broadcast.
        subnet_size = 4
        subnet_index = index % (self.base.num_addresses // subnet_size)
        network_int = int(self.base.network_address) + subnet_index * subnet_size
        subnet = ipaddress.ip_network((network_int, 30))
        addresses = list(subnet.hosts())
        host_ip, namespace_ip = str(addresses[0]), str(addresses[1])

        name = f"vbn-{safe_id}-{index:x}"[:15]
        host_veth = f"vbh-{safe_id}-{index:x}"[:15]
        namespace_veth = f"vbn-{safe_id}-{index:x}"[:15]
        if name in self._names:
            raise NamespaceError(f"Namespace name collision: {name}")
        self._names.add(name)

        uplink = self._default_interface()
        ns = NetworkNamespace(
            name=name,
            host_ip=host_ip,
            namespace_ip=namespace_ip,
            prefix=subnet.prefixlen,
            subnet=str(subnet),
            host_veth=host_veth,
            namespace_veth=namespace_veth,
            proxy_url=f"http://{namespace_ip}:0",
            uplink=uplink,
        )
        try:
            self._run(["ip", "netns", "add", name])
            self._run(["ip", "link", "add", host_veth, "type", "veth",
                       "peer", "name", namespace_veth])
            self._run(["ip", "link", "set", namespace_veth, "netns", name])
            self._run(["ip", "addr", "add", f"{host_ip}/{subnet.prefixlen}", "dev", host_veth])
            self._run(["ip", "link", "set", host_veth, "up"])
            self._run(["ip", "netns", "exec", name, "ip", "link", "set", "lo", "up"])
            self._run(["ip", "netns", "exec", name, "ip", "addr", "add",
                       f"{namespace_ip}/{subnet.prefixlen}", "dev", namespace_veth])
            self._run(["ip", "netns", "exec", name, "ip", "link", "set", namespace_veth, "up"])
            self._run(["ip", "netns", "exec", name, "ip", "route", "add",
                       "default", "via", host_ip])
            self._enable_forwarding()
            self._add_nat(ns)
            return ns
        except Exception:
            self.destroy(ns)
            raise

    def destroy(self, ns: NetworkNamespace) -> None:
        try:
            self._delete_nat(ns)
        except Exception:
            pass
        try:
            self._run(["ip", "link", "del", ns.host_veth], check=False)
        except Exception:
            pass
        try:
            self._run(["ip", "netns", "del", ns.name], check=False)
        except Exception:
            pass
        with self._lock:
            self._names.discard(ns.name)

    def exec_prefix(self, ns: NetworkNamespace) -> list[str]:
        return ["ip", "netns", "exec", ns.name]

    def enable_kill_switch(self, ns: NetworkNamespace) -> None:
        """Fail closed after the VPN core has established its upstream session.

        Existing connections remain usable; new namespace egress is limited to
        the currently observed VPN upstream peers. This prevents a dead or
        misconfigured proxy process from falling back to the namespace's plain
        NAT route.
        """
        peers = self._upstream_peers(ns)
        if not peers:
            raise NamespaceError("Could not identify VPN upstream peer for kill-switch")
        for protocol, address, port in peers:
            self._run([
                "ip", "netns", "exec", ns.name, "iptables", "-A", "OUTPUT",
                "-p", protocol, "-d", address, "--dport", str(port), "-j", "ACCEPT",
            ])
        self._run([
            "ip", "netns", "exec", ns.name, "iptables", "-A", "OUTPUT",
            "-m", "conntrack", "--ctstate", "ESTABLISHED,RELATED", "-j", "ACCEPT",
        ])
        self._run([
            "ip", "netns", "exec", ns.name, "iptables", "-A", "OUTPUT",
            "-o", "lo", "-j", "ACCEPT",
        ])
        self._run([
            "ip", "netns", "exec", ns.name, "iptables", "-A", "OUTPUT",
            "-j", "DROP",
        ])

    def _upstream_peers(self, ns: NetworkNamespace) -> list[tuple[str, str, int]]:
        result = self._run([
            "ip", "netns", "exec", ns.name, "ss", "-H", "-n", "-t", "-u",
        ], check=False)
        peers: set[tuple[str, str, int]] = set()
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) < 5:
                continue
            state = fields[0]
            local = fields[3]
            remote = fields[4]
            if remote in {"*", "*:*", "0.0.0.0:*", "[::]:*"}:
                continue
            parsed = _parse_peer(remote)
            if parsed is None:
                continue
            protocol = "udp" if "udp" in line.lower() else "tcp"
            address, port = parsed
            if address in {ns.host_ip, ns.namespace_ip, "127.0.0.1"}:
                continue
            peers.add((protocol, address, port))
        return sorted(peers)

    def _add_nat(self, ns: NetworkNamespace) -> None:
        uplink = ns.uplink
        self._run([
            "iptables", "-t", "nat", "-A", "POSTROUTING",
            "-s", ns.subnet, "-o", uplink, "-j", "MASQUERADE",
        ])

    def _delete_nat(self, ns: NetworkNamespace) -> None:
        uplink = ns.uplink
        self._run([
            "iptables", "-t", "nat", "-D", "POSTROUTING",
            "-s", ns.subnet, "-o", uplink, "-j", "MASQUERADE",
        ], check=False)

    def _enable_forwarding(self) -> None:
        self._run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

    def _default_interface(self) -> str:
        result = self._run(["ip", "route", "show", "default"])
        match = re.search(r"\bdev\s+(\S+)", result.stdout)
        if not match:
            raise NamespaceError("Could not determine worker default network interface")
        return match.group(1)

    @staticmethod
    def _require_commands() -> None:
        for command in ("ip", "iptables", "sysctl"):
            if not _which(command):
                raise NamespaceError(f"Required command not found: {command}")

    @staticmethod
    def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        except OSError as exc:
            raise NamespaceError(f"Failed to execute {' '.join(args)}: {exc}") from exc
        if check and result.returncode != 0:
            raise NamespaceError(
                f"Command failed ({result.returncode}): {' '.join(args)}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result


def _parse_peer(value: str) -> tuple[str, int] | None:
    value = value.strip()
    if value.startswith("["):
        end = value.rfind("]")
        if end < 0:
            return None
        address = value[1:end]
        port_text = value[end + 2:] if value[end + 1:end + 2] == ":" else ""
    else:
        if ":" not in value:
            return None
        address, port_text = value.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError:
        return None
    return address, port


def _which(command: str) -> bool:
    return any(
        os.access(os.path.join(path, command), os.X_OK)
        for path in os.environ.get("PATH", "").split(os.pathsep)
        if path
    )

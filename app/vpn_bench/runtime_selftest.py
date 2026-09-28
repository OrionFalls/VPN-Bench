"""Privileged runtime self-test for Linux network namespaces and kill-switch rules.

Run inside the worker container with NET_ADMIN/SYS_ADMIN and /dev/net/tun.
No VPN credentials or external network access are required.
"""

from __future__ import annotations

import socket
import threading
from .network_namespace import NamespaceManager, NamespaceError


def _run_in_namespace(manager: NamespaceManager, ns, script: str) -> None:
    result = manager._run(manager.exec_prefix(ns) + ["python", "-c", script], check=False)
    if result.returncode != 0:
        raise NamespaceError(result.stderr.strip() or result.stdout.strip() or "namespace command failed")


def main() -> int:
    manager = NamespaceManager()
    ns = None
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("0.0.0.0", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    first_accepted = threading.Event()
    accepted = threading.Event()
    accepted_count = 0
    accepted_lock = threading.Lock()

    def accept_twice() -> None:
        nonlocal accepted_count
        try:
            for _ in range(2):
                conn, _ = listener.accept()
                with conn:
                    conn.recv(1)
                with accepted_lock:
                    accepted_count += 1
                    if accepted_count == 1:
                        first_accepted.set()
            accepted.set()
        finally:
            listener.close()

    thread = threading.Thread(target=accept_twice, daemon=True)
    thread.start()

    try:
        ns = manager.create("selftest")

        # Before the kill switch, the namespace can reach the worker-side
        # veth. This proves the routed namespace/NAT plumbing is alive.
        _run_in_namespace(
            manager,
            ns,
            f"import socket; s=socket.create_connection(({ns.host_ip!r}, {port}), 1); s.send(b'x'); s.close()",
        )
        if not first_accepted.wait(2):
            raise NamespaceError("Namespace could not reach worker-side veth")

        # Once the kill switch is active, only the explicitly allowed endpoint,
        # established connections, and loopback are permitted.
        manager.enable_kill_switch(ns, [(ns.host_ip, port, "tcp")])

        _run_in_namespace(
            manager,
            ns,
            f"import socket; s=socket.create_connection(({ns.host_ip!r}, {port}), 1); s.send(b'y'); s.close()",
        )

        if not accepted.wait(2):
            raise NamespaceError("Allowed endpoint was blocked by the kill-switch")

        blocked = manager._run(
            manager.exec_prefix(ns)
            + [
                "python",
                "-c",
                "import socket; s=socket.socket(); s.settimeout(.5); "
                "rc=s.connect_ex(('1.1.1.1', 443)); raise SystemExit(2 if rc == 0 else 0)",
            ],
            check=False,
        )
        if blocked.returncode == 2:
            raise NamespaceError("Kill-switch did not block an unlisted egress destination")

        print("VPN-Bench runtime self-test: PASS")
        return 0
    finally:
        if ns is not None:
            manager.destroy(ns)
        else:
            listener.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""Benchmark orchestration around isolated VPN adapters and probes."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .adapters.extended import SingBoxExtendedAdapter, SingBoxLXAdapter
from .adapters.xray import XrayAdapter
from .proxied_probes import run_proxy_probe


class BenchmarkEngine:
    def __init__(
        self,
        probe_interval_seconds: int = 15,
        http_targets: list[str] | None = None,
        dns_domain: str = "example.com",
    ) -> None:
        self.probe_interval_seconds = max(2, probe_interval_seconds)
        self.http_targets = http_targets or ["https://example.com/"]
        self.dns_domain = dns_domain
        self.extended_adapter = SingBoxExtendedAdapter(
            binary=os.environ.get("VPN_BENCH_SING_BOX_EXTENDED", "sing-box-extended")
        )
        self.lx_adapter = SingBoxLXAdapter(
            binary=os.environ.get("VPN_BENCH_SING_BOX_LX", "sing-box-lx")
        )
        self.xray_adapter = XrayAdapter(
            binary=os.environ.get("VPN_BENCH_XRAY", "xray")
        )

    def _adapters_for(self, server: dict[str, Any]):
        transport = str(server.get("transport") or "").lower()
        protocol = str(server.get("protocol") or "").lower()
        if transport == "xhttp" or protocol in {"masque", "mieru", "trusttunnel", "ssh", "tuic", "anytls"}:
            return (self.extended_adapter, self.lx_adapter, self.xray_adapter)
        return (self.lx_adapter, self.extended_adapter, self.xray_adapter)

    def run_server(
        self,
        server: dict[str, Any],
        allocation_seconds: float,
        stop_event: threading.Event,
        on_result: Callable[[dict[str, Any]], None] | None = None,
    ) -> bool:
        started = time.time()
        handle = None
        last_success = False
        adapters = self._adapters_for(server)
        adapter = None
        connect_errors: list[str] = []
        try:
            for candidate in adapters:
                try:
                    handle = candidate.connect(server)
                    adapter = candidate
                    break
                except Exception as exc:
                    connect_errors.append(f"{candidate.__class__.__name__}: {exc}")
            if handle is None or adapter is None:
                raise RuntimeError("All compatible VPN cores failed: " + " | ".join(connect_errors))
            proxy_url = str(handle.metadata["proxy_url"])
            while not stop_event.is_set():
                elapsed = time.time() - started
                if allocation_seconds > 0 and elapsed >= allocation_seconds:
                    break

                result = run_proxy_probe(
                    proxy_url,
                    self.http_targets,
                    dns_domain=self.dns_domain,
                )
                last_success = result.success
                payload = {
                    "server_id": server["id"],
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": round(time.time() - started, 3),
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "jitter_ms": result.jitter_ms,
                    "packet_loss_percent": result.packet_loss_percent,
                    "dns_ok": result.dns_ok,
                    "http_ok": result.http_ok,
                    "details": result.details,
                }
                if on_result:
                    on_result(payload)

                if allocation_seconds <= 0:
                    break
                remaining = allocation_seconds - (time.time() - started)
                stop_event.wait(min(self.probe_interval_seconds, max(0.0, remaining)))

            return last_success
        except Exception as exc:
            if on_result:
                on_result({
                    "server_id": server["id"],
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": round(time.time() - started, 3),
                    "success": False,
                    "latency_ms": None,
                    "jitter_ms": None,
                    "packet_loss_percent": 100.0,
                    "dns_ok": False,
                    "http_ok": False,
                    "details": {"error": str(exc)},
                })
            return False
        finally:
            if handle is not None:
                adapter.disconnect(handle)

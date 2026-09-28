"""Lightweight real-world network probes.

The probes intentionally use standard-library networking primitives so the
benchmark engine can run them inside an isolated worker without depending on
the host's network tooling.
"""

from __future__ import annotations

import socket
import ssl
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    latency_ms: float | None
    jitter_ms: float | None
    packet_loss_percent: float | None
    dns_ok: bool
    http_ok: bool
    details: dict[str, Any]


def tcp_probe(host: str, port: int, timeout: float = 5.0) -> tuple[bool, float | None]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, (time.perf_counter() - started) * 1000
    except OSError:
        return False, None


def dns_probe(host: str, timeout: float = 5.0) -> tuple[bool, float | None]:
    started = time.perf_counter()
    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        socket.getaddrinfo(host, None)
        return True, (time.perf_counter() - started) * 1000
    except OSError:
        return False, None
    finally:
        socket.setdefaulttimeout(previous)


def http_probe(url: str, timeout: float = 8.0) -> tuple[bool, float | None, int | None]:
    started = time.perf_counter()
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "VPN-Bench/0.2"},
            method="HEAD",
        )
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            response.read(1)
            return True, (time.perf_counter() - started) * 1000, response.status
    except Exception:
        return False, None, None


def run_probe(
    host: str,
    port: int,
    http_url: str | None = None,
    attempts: int = 5,
    timeout: float = 5.0,
) -> ProbeResult:
    dns_ok, dns_latency = dns_probe(host, timeout)
    samples: list[float] = []
    failures = 0

    for _ in range(max(1, attempts)):
        ok, latency = tcp_probe(host, port, timeout)
        if ok and latency is not None:
            samples.append(latency)
        else:
            failures += 1

    latency_ms = statistics.median(samples) if samples else None
    jitter_ms = (
        statistics.mean(abs(a - b) for a, b in zip(samples, samples[1:]))
        if len(samples) >= 2
        else None
    )
    packet_loss = failures / max(1, attempts) * 100

    http_ok = False
    http_latency = None
    http_status = None
    if http_url:
        http_ok, http_latency, http_status = http_probe(http_url, timeout)

    success = dns_ok and bool(samples) and (http_ok if http_url else True)
    return ProbeResult(
        success=success,
        latency_ms=latency_ms,
        jitter_ms=jitter_ms,
        packet_loss_percent=packet_loss,
        dns_ok=dns_ok,
        http_ok=http_ok if http_url else None,
        details={
            "dns_latency_ms": dns_latency,
            "tcp_samples_ms": samples,
            "http_latency_ms": http_latency,
            "http_status": http_status,
            "attempts": attempts,
        },
    )


def as_dict(result: ProbeResult) -> dict[str, Any]:
    return asdict(result)

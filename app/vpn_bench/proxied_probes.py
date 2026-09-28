"""Probes executed through an HTTP proxy exposed by a VPN adapter."""

from __future__ import annotations

import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .throughput import download_sample


@dataclass(frozen=True)
class ProxyProbeResult:
    success: bool
    latency_ms: float | None
    jitter_ms: float | None
    packet_loss_percent: float
    dns_ok: bool
    http_ok: bool
    details: dict[str, Any]


def http_head(url: str, proxy_url: str, timeout: float = 8.0) -> tuple[bool, float | None, int | None]:
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VPN-Bench/0.2"},
        method="HEAD",
    )
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=timeout) as response:
            response.read(1)
            return True, (time.perf_counter() - started) * 1000, response.status
    except Exception:
        return False, None, None


def dns_over_https(
    domain: str,
    proxy_url: str,
    resolver_url: str = "https://cloudflare-dns.com/dns-query",
    timeout: float = 8.0,
) -> tuple[bool, float | None, int | None]:
    query = urllib.parse.urlencode({"name": domain, "type": "A"})
    url = f"{resolver_url}?{query}"
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VPN-Bench/0.2",
            "Accept": "application/dns-message",
        },
    )
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=timeout) as response:
            response.read(64)
            return True, (time.perf_counter() - started) * 1000, response.status
    except Exception:
        return False, None, None


def run_proxy_probe(
    proxy_url: str,
    http_targets: list[str],
    dns_domain: str = "example.com",
    attempts: int = 5,
    timeout: float = 8.0,
    throughput_url: str | None = None,
    throughput_duration_seconds: float = 0.0,
    whitelist_targets: list[str] | None = None,
) -> ProxyProbeResult:
    latency_samples: list[float] = []
    failures = 0

    target = http_targets[0] if http_targets else "https://example.com/"
    for _ in range(max(1, attempts)):
        ok, latency, _ = http_head(target, proxy_url, timeout)
        if ok and latency is not None:
            latency_samples.append(latency)
        else:
            failures += 1

    dns_ok, dns_latency, dns_status = dns_over_https(
        dns_domain,
        proxy_url,
        timeout=timeout,
    )
    http_ok, http_latency, http_status = http_head(target, proxy_url, timeout)
    whitelist_results: list[dict[str, Any]] = []
    for whitelist_target in whitelist_targets or []:
        ok, latency, status = http_head(whitelist_target, proxy_url, timeout)
        whitelist_results.append({"target": whitelist_target, "ok": ok, "latency_ms": latency, "status": status})

    throughput = None
    if throughput_url and throughput_duration_seconds > 0:
        throughput = download_sample(
            throughput_url,
            proxy_url,
            duration_seconds=throughput_duration_seconds,
            timeout=max(timeout, throughput_duration_seconds + 4),
        )

    median = statistics.median(latency_samples) if latency_samples else None
    jitter = (
        statistics.mean(abs(a - b) for a, b in zip(latency_samples, latency_samples[1:]))
        if len(latency_samples) >= 2
        else None
    )
    loss = failures / max(1, attempts) * 100

    return ProxyProbeResult(
        success=dns_ok and http_ok and bool(latency_samples),
        latency_ms=median,
        jitter_ms=jitter,
        packet_loss_percent=loss,
        dns_ok=dns_ok,
        http_ok=http_ok,
        details={
            "dns_latency_ms": dns_latency,
            "dns_status": dns_status,
            "http_latency_ms": http_latency,
            "http_status": http_status,
            "target": target,
            "attempts": attempts,
            "latency_samples_ms": latency_samples,
            "throughput": throughput,
            "whitelist": whitelist_results,
            "whitelist_ok": bool(whitelist_results) and all(item["ok"] for item in whitelist_results),
        },
    )

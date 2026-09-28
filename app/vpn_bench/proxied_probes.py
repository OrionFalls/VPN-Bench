"""Probes executed through an HTTP proxy exposed by a VPN adapter."""

from __future__ import annotations

import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .throughput import download_sample, upload_sample


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


def direct_http_head(url: str, timeout: float = 8.0) -> tuple[bool, float | None, int | None]:
    """Check a target without using a proxy."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
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


def measure_whitelist_baseline(
    targets: list[str],
    timeout: float = 8.0,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for target in targets:
        reachable, latency, status = direct_http_head(target, timeout=timeout)
        results.append(
            {
                "target": target,
                "reachable_without_vpn": reachable,
                "latency_ms": latency,
                "status": status,
            }
        )
    return results


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
    throughput_upload_url: str | None = None,
    throughput_duration_seconds: float = 0.0,
    whitelist_targets: list[str] | None = None,
    whitelist_baseline: list[dict[str, Any]] | None = None,
) -> ProxyProbeResult:
    latency_samples: list[float] = []
    failures = 0
    last_http_ok = False
    last_http_latency: float | None = None
    last_http_status: int | None = None

    target = http_targets[0] if http_targets else "https://example.com/"
    for _ in range(max(1, attempts)):
        ok, latency, status = http_head(target, proxy_url, timeout)
        last_http_ok = ok
        last_http_latency = latency
        last_http_status = status
        if ok and latency is not None:
            latency_samples.append(latency)
        else:
            failures += 1

    dns_ok, dns_latency, dns_status = dns_over_https(
        dns_domain,
        proxy_url,
        timeout=timeout,
    )
    if whitelist_targets:
        http_ok, http_latency, http_status = last_http_ok, last_http_latency, last_http_status
    else:
        http_ok, http_latency, http_status = http_head(target, proxy_url, timeout)
    whitelist_results: list[dict[str, Any]] = []
    baseline_by_target = {
        item["target"]: item
        for item in (whitelist_baseline or [])
        if isinstance(item, dict) and item.get("target")
    }
    for whitelist_target in whitelist_targets or []:
        ok, latency, status = http_head(whitelist_target, proxy_url, timeout)
        baseline = baseline_by_target.get(whitelist_target, {})
        baseline_reachable = baseline.get("reachable_without_vpn")
        if baseline_reachable is False:
            bypass_ok = ok
        else:
            bypass_ok = None
        whitelist_results.append(
            {
                "target": whitelist_target,
                "ok": ok,
                "latency_ms": latency,
                "status": status,
                "reachable_without_vpn": baseline_reachable,
                "bypass_ok": bypass_ok,
            }
        )
    applicable = [item["bypass_ok"] for item in whitelist_results if item["bypass_ok"] is not None]
    whitelist_ok = all(applicable) if applicable else None

    throughput = None
    if throughput_url and throughput_duration_seconds > 0:
        throughput = download_sample(
            throughput_url,
            proxy_url,
            duration_seconds=throughput_duration_seconds,
            timeout=max(timeout, throughput_duration_seconds + 4),
        )
    upload = None
    if throughput_upload_url and throughput_duration_seconds > 0:
        upload = upload_sample(
            throughput_upload_url,
            proxy_url,
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
            "upload": upload,
            "whitelist": whitelist_results,
            "whitelist_ok": whitelist_ok,
            "whitelist_baseline": whitelist_baseline or [],
        },
    )

"""Throughput probes executed through the VPN proxy.

The probe is intentionally endpoint-driven: production deployments should point
it at a controlled VPS endpoint rather than an arbitrary public speed-test.
"""

from __future__ import annotations

import time
import urllib.request
from typing import Any


def download_sample(
    url: str,
    proxy_url: str,
    duration_seconds: float = 8.0,
    max_bytes: int = 64 * 1024 * 1024,
    timeout: float = 12.0,
) -> dict[str, Any]:
    if not url:
        return {"ok": False, "mbps": None, "bytes": 0, "duration_seconds": 0}

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    )
    request = urllib.request.Request(url, headers={"User-Agent": "VPN-Bench/0.2"})
    started = time.perf_counter()
    total = 0
    try:
        with opener.open(request, timeout=timeout) as response:
            while total < max_bytes:
                chunk = response.read(min(1024 * 1024, max_bytes - total))
                if not chunk:
                    break
                total += len(chunk)
                if time.perf_counter() - started >= duration_seconds:
                    break
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return {
            "ok": False,
            "mbps": None,
            "bytes": total,
            "duration_seconds": round(elapsed, 3),
            "error": str(exc),
        }

    elapsed = max(0.001, time.perf_counter() - started)
    return {
        "ok": total > 0,
        "mbps": round(total * 8 / elapsed / 1_000_000, 3) if total else None,
        "bytes": total,
        "duration_seconds": round(elapsed, 3),
    }

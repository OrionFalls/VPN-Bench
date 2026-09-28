"""HTTP client used by the controller to delegate VPN work to the worker."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class WorkerClientError(RuntimeError):
    pass


class WorkerClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("VPN_BENCH_WORKER_URL", "http://vpn-bench-worker:8090")).rstrip("/")
        self.token = token or os.environ.get("VPN_BENCH_WORKER_TOKEN", "")
        self.poll_interval = max(0.2, poll_interval)

    def health(self) -> bool:
        try:
            return self._request("GET", "/health").get("status") == "ok"
        except WorkerClientError:
            return False

    def run_server(
        self,
        server: dict[str, Any],
        allocation_seconds: float,
        stop_event,
        on_result=None,
    ) -> bool:
        payload = self._request(
            "POST",
            "/jobs",
            {"server": server, "duration_seconds": allocation_seconds},
        )
        job_id = payload["job_id"]
        delivered = 0

        while not stop_event.is_set():
            status = self._request("GET", f"/jobs/{job_id}")
            results = status.get("results", [])
            for result in results[delivered:]:
                delivered += 1
                if on_result:
                    on_result(result)

            if status.get("status") in {"completed", "failed"}:
                return status.get("status") == "completed" and any(
                    item.get("success") for item in results
                )
            time.sleep(self.poll_interval)

        return False

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None
        headers = {
            "Accept": "application/json",
            "X-Worker-Token": self.token,
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise WorkerClientError(f"Worker request failed: {exc}") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkerClientError("Worker returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise WorkerClientError("Worker returned an invalid response")
        return data

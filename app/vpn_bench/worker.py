"""VPN-Bench worker service.

The worker is the only runtime component that launches VPN cores. It is kept
behind an internal Docker network and can receive NET_ADMIN/TUN privileges
without exposing those privileges to the web controller.
"""

from __future__ import annotations

import os
import threading
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .benchmark import BenchmarkEngine
from .config import load_config


class WorkerJob(BaseModel):
    server: dict
    duration_seconds: float = Field(default=0, ge=0)


class Worker:
    def __init__(self) -> None:
        config_path = os.environ.get("VPN_BENCH_CONFIG", "/app/config/config.yaml")
        config = load_config(config_path)
        self.engine = BenchmarkEngine(
            probe_interval_seconds=config.probe_interval_seconds,
            http_targets=list(config.http_targets),
            dns_domain=config.dns_domain,
            throughput_download_url=config.throughput_download_url,
            throughput_upload_url=config.throughput_upload_url,
            throughput_sample_seconds=config.throughput_sample_seconds,
            whitelist_targets=list(config.whitelist_targets),
        )
        self.jobs: dict[str, dict] = {}
        self.stop_events: dict[str, threading.Event] = {}
        self.lock = threading.Lock()

    def start(self, job: WorkerJob) -> str:
        job_id = uuid4().hex
        stop_event = threading.Event()
        with self.lock:
            self.jobs[job_id] = {"status": "running", "results": [], "error": None}
            self.stop_events[job_id] = stop_event

        def run() -> None:
            def on_result(result: dict) -> None:
                with self.lock:
                    self.jobs[job_id]["results"].append(result)

            try:
                ok = self.engine.run_server(
                    job.server,
                    job.duration_seconds,
                    stop_event,
                    on_result=on_result,
                )
                with self.lock:
                    self.jobs[job_id]["status"] = "completed" if ok else "failed"
            except Exception as exc:
                with self.lock:
                    self.jobs[job_id]["status"] = "failed"
                    self.jobs[job_id]["error"] = str(exc)
            finally:
                with self.lock:
                    self.stop_events.pop(job_id, None)

        threading.Thread(
            target=run,
            name=f"vpn-bench-worker-{job_id[:8]}",
            daemon=True,
        ).start()
        return job_id

    def stop(self, job_id: str) -> bool:
        with self.lock:
            event = self.stop_events.get(job_id)
            if event is None:
                return False
            event.set()
            self.jobs[job_id]["status"] = "stopping"
            return True

    def get(self, job_id: str) -> dict | None:
        with self.lock:
            job = self.jobs.get(job_id)
            return dict(job) if job else None


worker = Worker()
app = FastAPI(
    title="VPN-Bench Worker",
    version=os.environ.get("VPN_BENCH_VERSION", "0.2.0"),
)


def authorize(x_worker_token: str | None) -> None:
    expected = os.environ.get("VPN_BENCH_WORKER_TOKEN")
    if not expected or x_worker_token != expected:
        raise HTTPException(status_code=401, detail="Worker authentication required")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "worker": True}


@app.post("/jobs")
def create_job(
    payload: WorkerJob,
    x_worker_token: str | None = Header(default=None),
) -> dict:
    authorize(x_worker_token)
    job_id = worker.start(payload)
    return {"job_id": job_id, "status": "running"}


@app.get("/jobs/{job_id}")
def job_status(
    job_id: str,
    x_worker_token: str | None = Header(default=None),
) -> dict:
    authorize(x_worker_token)
    result = worker.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Worker job not found")
    return result


@app.delete("/jobs/{job_id}")
def stop_job(
    job_id: str,
    x_worker_token: str | None = Header(default=None),
) -> dict:
    authorize(x_worker_token)
    if not worker.stop(job_id):
        result = worker.get(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Worker job not found")
        return {"job_id": job_id, "status": result["status"]}
    return {"job_id": job_id, "status": "stopping"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("VPN_BENCH_WORKER_PORT", "8090")),
    )

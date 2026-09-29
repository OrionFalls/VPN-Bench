"""Test campaign state and scheduling primitives."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass
class TestRunState:
    run_id: str
    status: str
    scheduling_mode: str
    planned_seconds: float
    started_at: float
    total_servers: int
    completed_servers: int = 0
    failed_servers: int = 0
    current_server_id: str | None = None
    current_server_name: str | None = None
    current_server_started_at: float | None = None
    current_server_elapsed: float = 0.0
    message: str = ""
    stopped_at: float | None = None
    max_parallel: int = 1

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, (self.stopped_at or time.time()) - self.started_at)

    @property
    def progress(self) -> float:
        if self.total_servers <= 0:
            return 0.0
        return min(1.0, self.completed_servers / self.total_servers)

    @property
    def remaining_seconds(self) -> float | None:
        if self.status not in {"running", "stopping"}:
            return 0.0
        if self.completed_servers <= 0:
            return None
        per_server = self.elapsed_seconds / self.completed_servers
        return max(0.0, per_server * (self.total_servers - self.completed_servers))

    @property
    def eta(self) -> str | None:
        seconds = self.remaining_seconds
        if seconds is None:
            return None
        return datetime.fromtimestamp(time.time() + seconds, tz=timezone.utc).isoformat()

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "scheduling_mode": self.scheduling_mode,
            "planned_seconds": self.planned_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "remaining_seconds": None if self.remaining_seconds is None else round(self.remaining_seconds, 1),
            "eta": self.eta,
            "total_servers": self.total_servers,
            "completed_servers": self.completed_servers,
            "failed_servers": self.failed_servers,
            "progress": round(self.progress * 100, 2),
            "current_server_id": self.current_server_id,
            "current_server_name": self.current_server_name,
            "current_server_elapsed": round(self.current_server_elapsed, 1),
            "message": self.message,
            "max_parallel": self.max_parallel,
        }


class TestRunManager:
    def __init__(self) -> None:
        self._runs: dict[str, TestRunState] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def create(
        self,
        run_id: str,
        server_ids: list[str],
        planned_seconds: float,
        scheduling_mode: str,
        server_names: dict[str, str] | None = None,
        on_server: Callable[[str, float, threading.Event], bool] | None = None,
        max_parallel: int = 1,
    ) -> TestRunState:
        if not server_ids:
            raise ValueError("At least one server must be selected.")
        if planned_seconds <= 0:
            raise ValueError("Test duration must be greater than zero.")
        if scheduling_mode not in {"equal_time", "sequential"}:
            raise ValueError("Unsupported scheduling mode.")
        max_parallel = max(1, min(16, int(max_parallel)))

        state = TestRunState(
            run_id=run_id,
            status="running",
            scheduling_mode=scheduling_mode,
            planned_seconds=planned_seconds,
            started_at=time.time(),
            total_servers=len(server_ids),
            message="Test campaign started.",
            max_parallel=max_parallel,
        )
        stop_event = threading.Event()
        with self._lock:
            self._runs[run_id] = state
            self._stop_events[run_id] = stop_event

        thread = threading.Thread(
            target=self._worker,
            args=(state, stop_event, server_ids, server_names or {}, on_server),
            daemon=True,
            name=f"vpn-bench-run-{run_id}",
        )
        thread.start()
        return state

    def stop(self, run_id: str) -> bool:
        with self._lock:
            event = self._stop_events.get(run_id)
            state = self._runs.get(run_id)
            if not event or not state or state.status not in {"running", "stopping"}:
                return False
            state.status = "stopping"
            state.message = "Stopping after the current safe step."
            event.set()
            return True

    def get(self, run_id: str) -> TestRunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def latest(self) -> TestRunState | None:
        with self._lock:
            return next(reversed(self._runs.values()), None) if self._runs else None

    def _worker(
        self,
        state: TestRunState,
        stop_event: threading.Event,
        server_ids: list[str],
        server_names: dict[str, str],
        on_server: Callable[[str, float, threading.Event], bool] | None,
    ) -> None:
        slot_seconds = state.planned_seconds / len(server_ids)
        try:
            if state.scheduling_mode == "equal_time" and state.max_parallel > 1:
                for offset in range(0, len(server_ids), state.max_parallel):
                    if stop_event.is_set():
                        break
                    batch = server_ids[offset:offset + state.max_parallel]
                    with self._lock:
                        state.current_server_id = batch[0]
                        state.current_server_name = ", ".join(server_names.get(item, item) for item in batch)
                        state.current_server_started_at = time.time()
                        state.current_server_elapsed = 0.0
                        state.message = f"Testing {len(batch)} servers in parallel"
                    with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix=f"vpn-bench-batch-{state.run_id}") as pool:
                        futures = {
                            pool.submit(self._run_one, server_id, slot_seconds, stop_event, on_server): server_id
                            for server_id in batch
                        }
                        for future in as_completed(futures):
                            success = future.result()
                            with self._lock:
                                if success:
                                    state.completed_servers += 1
                                else:
                                    state.failed_servers += 1
                    with self._lock:
                        state.current_server_elapsed = time.time() - (state.current_server_started_at or time.time())
                        state.message = f"Completed {len(batch)} servers"
            else:
                for server_id in server_ids:
                    if stop_event.is_set():
                        break
                    with self._lock:
                        state.current_server_id = server_id
                        state.current_server_name = server_names.get(server_id, server_id)
                        state.current_server_started_at = time.time()
                        state.current_server_elapsed = 0.0
                        state.message = f"Testing {state.current_server_name}"
                    if on_server is not None:
                        allocation = (
                            slot_seconds
                            if state.scheduling_mode == "equal_time"
                            else max(0.0, state.planned_seconds - state.elapsed_seconds)
                        )
                        success = on_server(server_id, allocation, stop_event)
                    else:
                        success = self._wait_slot(stop_event, slot_seconds)
                    with self._lock:
                        state.current_server_elapsed = time.time() - (state.current_server_started_at or time.time())
                        if success:
                            state.completed_servers += 1
                        else:
                            state.failed_servers += 1
                        state.message = f"Completed {state.current_server_name}"

            with self._lock:
                state.status = "stopped" if stop_event.is_set() else "completed"
                state.stopped_at = time.time()
                state.current_server_id = None
                state.current_server_name = None
        except Exception as exc:
            with self._lock:
                state.status = "failed"
                state.stopped_at = time.time()
                state.message = f"Test campaign failed: {exc}"
        finally:
            with self._lock:
                self._stop_events.pop(state.run_id, None)

    @staticmethod
    def _run_one(server_id, allocation, stop_event, on_server):
        if on_server is not None:
            return on_server(server_id, allocation, stop_event)
        return TestRunManager._wait_slot(stop_event, allocation)

    @staticmethod
    def _wait_slot(stop_event: threading.Event, seconds: float) -> bool:
        end = time.time() + min(seconds, 5.0)
        while time.time() < end:
            if stop_event.wait(min(0.25, end - time.time())):
                return False
        return True

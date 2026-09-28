"""Two-pass VPN screening campaign orchestration."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .screening import ScreeningPolicy
from .screening_plan import ScreeningPlan


@dataclass
class ScreeningState:
    run_id: str
    status: str
    total_servers: int
    current_pass: int = 0
    current_server_id: str | None = None
    current_server_name: str | None = None
    completed_servers: int = 0
    pass_completed: int = 0
    pass_total: int = 0
    shortlisted_servers: list[str] = field(default_factory=list)
    failed_servers: int = 0
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        elapsed = (self.finished_at or time.time()) - self.started_at
        return {
            "run_id": self.run_id,
            "status": self.status,
            "total_servers": self.total_servers,
            "current_pass": self.current_pass,
            "current_server_id": self.current_server_id,
            "current_server_name": self.current_server_name,
            "completed_servers": self.completed_servers,
            "pass_completed": self.pass_completed,
            "pass_total": self.pass_total,
            "shortlisted_servers": list(self.shortlisted_servers),
            "shortlist_count": len(self.shortlisted_servers),
            "shortlist": list(self.shortlisted_servers),
            "failed_servers": self.failed_servers,
            "elapsed_seconds": round(max(0.0, elapsed), 1),
            "progress": round(
                (self.pass_completed / self.pass_total) * 100, 2
            ) if self.pass_total else 100.0,
            "message": self.message,
        }


class ScreeningCampaignManager:
    """Runs cheap first-pass checks, then rechecks only survivors."""

    def __init__(self, worker, policy: ScreeningPolicy | None = None,
                 plan: ScreeningPlan | None = None) -> None:
        self.worker = worker
        self.policy = policy or ScreeningPolicy()
        self.plan = plan or ScreeningPlan()
        self._states: dict[str, ScreeningState] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._samples: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._plans: dict[str, ScreeningPlan] = {}

    def start(
        self,
        run_id: str,
        servers: dict[str, dict[str, Any]],
        on_result: Callable[[str, int, dict[str, Any]], None] | None = None,
        on_finish: Callable[[ScreeningState, dict[str, list[dict[str, Any]]]], None] | None = None,
    ) -> ScreeningState:
        if not servers:
            raise ValueError("At least one server is required.")
        with self._lock:
            if any(state.status in {"running", "stopping"} for state in self._states.values()):
                raise RuntimeError("A screening campaign is already running.")
            state = ScreeningState(
                run_id=run_id,
                status="running",
                total_servers=len(servers),
                message="Screening pass 1 started.",
            )
            self._states[run_id] = state
            self._plans[run_id] = self.plan
            stop_event = threading.Event()
            self._stop_events[run_id] = stop_event

        threading.Thread(
            target=self._run,
            args=(state, stop_event, servers, on_result, on_finish),
            daemon=True,
            name=f"vpn-bench-screening-{run_id}",
        ).start()
        return state

    def get(self, run_id: str) -> ScreeningState | None:
        with self._lock:
            return self._states.get(run_id)

    def latest(self) -> ScreeningState | None:
        with self._lock:
            return next(reversed(self._states.values()), None) if self._states else None

    def stop(self, run_id: str) -> bool:
        with self._lock:
            event = self._stop_events.get(run_id)
            state = self._states.get(run_id)
            if not event or not state or state.status not in {"running", "stopping"}:
                return False
            state.status = "stopping"
            state.message = "Stopping screening after the current server."
            event.set()
            return True

    def samples(self, run_id: str) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {key: list(value) for key, value in self._samples.get(run_id, {}).items()}

    def _run(self, state, stop_event, servers, on_result, on_finish) -> None:
        all_ids = list(servers)
        plan = self._plans.get(state.run_id, self.plan)
        try:
            survivors = all_ids
            for pass_no in range(1, plan.repeat_passes + 1):
                if stop_event.is_set():
                    break
                state.current_pass = pass_no
                candidates = plan.next_candidates(all_ids, survivors)
                state.pass_total = len(candidates)
                state.pass_completed = 0
                state.message = f"Screening pass {pass_no}: {len(candidates)} servers."
                pass_samples: dict[str, list[dict[str, Any]]] = {}

                for server_id in candidates:
                    if stop_event.is_set():
                        break
                    state.current_server_id = server_id
                    state.current_server_name = servers[server_id].get("name")
                    samples: list[dict[str, Any]] = []
                    pass_samples[server_id] = samples

                    def receive(result: dict[str, Any]) -> None:
                        samples.append(result)
                        with self._lock:
                            self._samples.setdefault(state.run_id, {}).setdefault(server_id, []).append(result)
                        if on_result:
                            on_result(server_id, pass_no, result)

                    ok = self.worker.run_server(
                        servers[server_id],
                        plan.first_pass_duration if pass_no == 1 else plan.repeat_pass_duration,
                        stop_event,
                        on_result=receive,
                    )
                    if not ok:
                        state.failed_servers += 1
                    state.completed_servers += 1
                    state.pass_completed += 1

                if stop_event.is_set():
                    break

                survivors = [
                    server_id
                    for server_id in candidates
                    if self.policy.keep(pass_samples.get(server_id, []))
                ]
                state.shortlisted_servers = survivors
                state.message = (
                    f"Pass {pass_no} complete: {len(survivors)} survivors."
                )

                if not survivors:
                    break

            with self._lock:
                if stop_event.is_set():
                    state.status = "stopped"
                else:
                    state.status = "completed"
                state.current_server_id = None
                state.current_server_name = None
                state.finished_at = time.time()
                state.message = (
                    f"Screening complete: {len(state.shortlisted_servers)} servers shortlisted."
                )
            if on_finish:
                on_finish(state, self.samples(state.run_id))
        except Exception as exc:
            with self._lock:
                state.status = "failed"
                state.finished_at = time.time()
                state.current_server_id = None
                state.current_server_name = None
                state.message = f"Screening failed: {exc}"
            if on_finish:
                on_finish(state, self.samples(state.run_id))
        finally:
            with self._lock:
                self._stop_events.pop(state.run_id, None)
                self._plans.pop(state.run_id, None)

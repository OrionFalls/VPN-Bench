import time

from vpn_bench.test_runner import TestRunManager


def test_equal_time_run_reports_progress():
    manager = TestRunManager()
    state = manager.create(
        "run-1",
        ["a", "b"],
        planned_seconds=2,
        scheduling_mode="equal_time",
        server_names={"a": "A", "b": "B"},
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        current = manager.get("run-1")
        if current and current.status == "completed":
            break
        time.sleep(0.05)
    current = manager.get("run-1")
    assert current is not None
    assert current.status == "completed"
    assert current.completed_servers == 2

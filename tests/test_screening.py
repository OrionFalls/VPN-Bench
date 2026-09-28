from vpn_bench.screening import ScreeningPolicy, shortlist, summarize


def test_screening_keeps_usable_server():
    rows = [
        {"success": True, "latency_ms": 40, "packet_loss_percent": 0},
        {"success": True, "latency_ms": 55, "packet_loss_percent": 0},
    ]
    assert ScreeningPolicy().keep(rows)


def test_screening_removes_unreliable_server():
    rows = [
        {"success": False, "latency_ms": None, "packet_loss_percent": 100},
        {"success": True, "latency_ms": 3000, "packet_loss_percent": 30},
    ]
    assert not ScreeningPolicy().keep(rows)


def test_shortlist_is_deterministic():
    samples = {
        "b": [{"success": True, "latency_ms": 20, "packet_loss_percent": 0}],
        "a": [{"success": True, "latency_ms": 30, "packet_loss_percent": 0}],
        "dead": [{"success": False, "latency_ms": None, "packet_loss_percent": 100}],
    }
    assert shortlist(samples) == ["a", "b"]


def test_summarize_empty_and_values():
    assert summarize([])["samples"] == 0
    result = summarize(
        [
            {"success": True, "latency_ms": 20, "packet_loss_percent": 0},
            {"success": False, "latency_ms": 40, "packet_loss_percent": 10},
        ]
    )
    assert result["success_rate"] == 0.5
    assert result["avg_latency_ms"] == 30
    assert result["avg_packet_loss_percent"] == 5

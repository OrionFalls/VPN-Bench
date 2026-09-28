from vpn_bench.screening_plan import ScreeningPlan


def test_screening_plan_defaults_to_two_passes():
    plan = ScreeningPlan()
    assert plan.repeat_passes == 2
    assert plan.first_pass_duration == 30
    assert plan.repeat_pass_duration == 30


def test_screening_plan_uses_survivors_for_next_pass():
    plan = ScreeningPlan()
    assert plan.next_candidates(["a", "b"], ["b"]) == ["b"]


def test_screening_plan_can_cap_shortlist():
    plan = ScreeningPlan(max_shortlist=2)
    assert plan.next_candidates(["a", "b", "c"]) == ["a", "b"]


def test_screening_plan_rejects_invalid_duration():
    try:
        ScreeningPlan(first_pass_seconds=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

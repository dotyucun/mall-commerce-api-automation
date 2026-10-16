from pathlib import Path
from types import SimpleNamespace

import pytest

from mall_api_test.common.performance_steps import (
    assess_step,
    compare_steps,
    load_step_settings,
    summarize_entry,
)

CONFIG = Path(__file__).resolve().parents[1] / "performance" / "steps.yaml"


def entry(name="Aggregated", requests=100, failures=0, p95=10):
    return {
        "name": name,
        "requests": requests,
        "failures": failures,
        "failure_ratio": failures / requests if requests else 0,
        "p95_ms": p95,
        "success_rps": requests - failures,
    }


def summary():
    return {
        "users": 10,
        "ready_users": 10,
        "user_exceptions": 0,
        "started_requests": 100,
        "tail_requests": 0,
        "incomplete_requests": 0,
        "total": entry(),
        "endpoints": [
            entry(name)
            for name in ("GET /product/search", "GET /product/detail/:id", "GET /cart/list")
        ],
        "resource_errors": [],
        "resource_samples": 5,
        "generator_cpu_median_percent": 20,
        "stop_reasons": [],
    }


def test_settings_keep_baseline_separate_and_validate_profiles():
    config = load_step_settings(CONFIG, "explore")
    assert config.users == (10, 20, 40, 80)
    assert config.wait_seconds == 0.1
    assert load_step_settings(CONFIG, "confirm").measure_seconds == 300
    with pytest.raises(ValueError, match="Unknown"):
        load_step_settings(CONFIG, "missing")


@pytest.mark.parametrize("users", [[], [20, 10], [10, 10], [0], [True], [2001]])
def test_invalid_user_levels_are_rejected(users):
    with pytest.raises(ValueError, match="User levels"):
        load_step_settings(CONFIG, "explore", users)


def test_rps_uses_exact_measured_window_not_configured_runtime():
    sample = SimpleNamespace(
        name="Aggregated",
        num_requests=100,
        num_failures=5,
        fail_ratio=0.05,
        avg_response_time=8,
        max_response_time=100,
        get_response_time_percentile=lambda percentile: 14 if percentile == 0.95 else 20,
    )
    result = summarize_entry(sample, 2.5)
    assert result["rps"] == 40
    assert result["success_rps"] == 38
    assert result["p95_ms"] == 14
    with pytest.raises(ValueError):
        summarize_entry(sample, 0)


def test_healthy_step_passes():
    assert assess_step(summary(), load_step_settings(CONFIG, "explore")) == []


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("ready_users", 9, "user_count_mismatch"),
        ("user_exceptions", 1, "user_exception"),
        ("incomplete_requests", 1, "incomplete_requests"),
        ("started_requests", 101, "request_accounting_mismatch"),
        ("resource_samples", 0, "incomplete_resource_evidence"),
        ("resource_errors", ["docker unavailable"], "incomplete_resource_evidence"),
        ("generator_cpu_median_percent", 90, "generator_cpu_limit"),
    ],
)
def test_incomplete_or_generator_limited_steps_are_not_capacity_evidence(field, value, expected):
    result = summary()
    result[field] = value
    assert expected in assess_step(result, load_step_settings(CONFIG, "explore"))


def test_per_endpoint_failure_is_not_hidden_by_aggregate():
    result = summary()
    result["endpoints"][0] = entry("GET /product/search", failures=1)
    assert "failure_threshold:GET /product/search" in assess_step(
        result, load_step_settings(CONFIG, "explore")
    )


def test_empty_or_missing_endpoints_fail():
    result = summary()
    result["total"] = entry(requests=0)
    result["endpoints"] = []
    reasons = assess_step(result, load_step_settings(CONFIG, "explore"))
    assert "no_requests" in reasons
    assert "missing_endpoint_samples" in reasons


def test_knee_requires_both_throughput_flattening_and_latency_growth():
    previous = summary()
    current = summary()
    current["users"] = 20
    current["total"]["success_rps"] = 110
    assert compare_steps(previous, current) == "no_knee_observed"
    current["total"]["p95_ms"] = 20
    assert compare_steps(previous, current) == "candidate_knee_requires_confirmation"
    current["stop_reasons"] = ["generator_cpu_limit"]
    assert compare_steps(previous, current) == "not_comparable"

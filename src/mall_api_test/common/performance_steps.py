import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass(frozen=True)
class StepSettings:
    portal_base_url: str
    users: tuple[int, ...]
    wait_seconds: float
    spawn_rate: float
    ready_timeout_seconds: float
    sample_interval_seconds: float
    cooldown_seconds: float
    warmup_seconds: float
    measure_seconds: float
    repeats: int
    max_failure_ratio: float
    max_p95_ms: float
    generator_cpu_warning_percent: float


def load_step_settings(path: Path, profile: str, users: list[int] | None = None) -> StepSettings:
    with path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    if not isinstance(raw, dict) or profile not in raw.get("profiles", {}):
        raise ValueError(f"Unknown performance profile: {profile}")
    selected = {key: value for key, value in raw.items() if key != "profiles"}
    selected.update(raw["profiles"][profile])
    selected["users"] = tuple(users if users is not None else selected["users"])
    settings = StepSettings(**selected)
    target = urlparse(settings.portal_base_url)
    if (
        target.scheme != "http"
        or target.hostname not in {"localhost", "127.0.0.1"}
        or target.username is not None
        or target.password is not None
        or target.path not in {"", "/"}
        or target.query
        or target.fragment
    ):
        raise ValueError("Step load is restricted to local HTTP targets")
    if (
        not settings.users
        or any(type(value) is not int or not 1 <= value <= 2000 for value in settings.users)
        or tuple(sorted(set(settings.users))) != settings.users
    ):
        raise ValueError("User levels must be unique, increasing integers between 1 and 2000")
    if type(settings.repeats) is not int or not 1 <= settings.repeats <= 5:
        raise ValueError("Repeats must be an integer between 1 and 5")
    for field in (
        "wait_seconds",
        "spawn_rate",
        "ready_timeout_seconds",
        "sample_interval_seconds",
        "warmup_seconds",
        "measure_seconds",
        "max_p95_ms",
        "generator_cpu_warning_percent",
    ):
        value = getattr(settings, field)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{field} must be finite and positive")
    if (
        type(settings.cooldown_seconds) not in (int, float)
        or not math.isfinite(settings.cooldown_seconds)
        or settings.cooldown_seconds < 0
        or not 0 < settings.max_failure_ratio < 1
    ):
        raise ValueError("Invalid cooldown or failure ratio")
    return settings


def summarize_entry(entry, duration: float) -> dict:
    if duration <= 0:
        raise ValueError("The measured window must be positive")
    return {
        "name": entry.name,
        "requests": entry.num_requests,
        "failures": entry.num_failures,
        "rps": entry.num_requests / duration,
        "success_rps": (entry.num_requests - entry.num_failures) / duration,
        "failure_ratio": entry.fail_ratio,
        "average_ms": entry.avg_response_time,
        "max_ms": entry.max_response_time,
        "p95_ms": entry.get_response_time_percentile(0.95),
        "p99_ms": entry.get_response_time_percentile(0.99),
    }


def assess_step(summary: dict, settings: StepSettings) -> list[str]:
    reasons = []
    if summary["total"]["requests"] == 0:
        reasons.append("no_requests")
    if summary["ready_users"] != summary["users"]:
        reasons.append("user_count_mismatch")
    if summary["user_exceptions"]:
        reasons.append("user_exception")
    if summary["incomplete_requests"]:
        reasons.append("incomplete_requests")
    if summary["started_requests"] != (
        summary["total"]["requests"] + summary["tail_requests"] + summary["incomplete_requests"]
    ):
        reasons.append("request_accounting_mismatch")
    expected = {"GET /product/search", "GET /product/detail/:id", "GET /cart/list"}
    if {item["name"] for item in summary["endpoints"] if item["requests"]} != expected:
        reasons.append("missing_endpoint_samples")
    for entry in [summary["total"], *summary["endpoints"]]:
        if entry["failure_ratio"] >= settings.max_failure_ratio:
            reasons.append(f"failure_threshold:{entry['name']}")
        if (entry["p95_ms"] or 0) >= settings.max_p95_ms:
            reasons.append(f"latency_threshold:{entry['name']}")
    if summary["resource_errors"] or not summary["resource_samples"]:
        reasons.append("incomplete_resource_evidence")
    if summary["generator_cpu_median_percent"] >= settings.generator_cpu_warning_percent:
        reasons.append("generator_cpu_limit")
    return reasons


def compare_steps(previous: dict, current: dict) -> str:
    if previous["stop_reasons"] or current["stop_reasons"]:
        return "not_comparable"
    throughput_gain = current["total"]["success_rps"] / max(previous["total"]["success_rps"], 0.001)
    latency_gain = (current["total"]["p95_ms"] or 0) / max(previous["total"]["p95_ms"] or 0, 1)
    if (
        current["users"] >= previous["users"] * 1.5
        and throughput_gain < 1.2
        and latency_gain >= 1.5
    ):
        return "candidate_knee_requires_confirmation"
    return "no_knee_observed"

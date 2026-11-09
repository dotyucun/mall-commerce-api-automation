import json

import pytest

from performance.audit import audit


@pytest.fixture
def saved_campaign(tmp_path):
    total = {"requests": 100, "failures": 2, "rps": 10, "success_rps": 9.8}
    summary = {
        "repeat": 1,
        "users": 10,
        "start_utc": "2026-10-16T00:00:00+00:00",
        "end_utc": "2026-10-16T00:00:10+00:00",
        "measured_seconds": 10,
        "total": total,
        "endpoints": [dict(total)],
        "started_requests": 103,
        "tail_requests": 3,
        "incomplete_requests": 0,
        "resource_samples": 1,
        "generator_cpu_median_percent": 12.3,
        "stop_reasons": [],
    }
    stage = tmp_path / "repeat-1-users-10"
    stage.mkdir()
    (stage / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (stage / "resources.json").write_text('[{"generator_cpu_percent":12.3}]', encoding="utf-8")
    (stage / "endpoints.csv").write_text("requests\n100\n", encoding="utf-8")
    (stage / "report.html").write_text("<!doctype html>", encoding="utf-8")
    (tmp_path / "campaign.json").write_text(json.dumps([summary]), encoding="utf-8")
    (tmp_path / "environment.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_consistent_saved_campaign_passes(saved_campaign):
    assert audit(saved_campaign) == {
        "stages": 1,
        "requests": 100,
        "stopped_stages": 0,
        "source_checked": False,
    }


def test_changed_saved_rate_is_detected(saved_campaign):
    stage = saved_campaign / "repeat-1-users-10" / "summary.json"
    summary = json.loads(stage.read_text(encoding="utf-8"))
    summary["total"]["rps"] = 11
    stage.write_text(json.dumps(summary), encoding="utf-8")
    (saved_campaign / "campaign.json").write_text(json.dumps([summary]), encoding="utf-8")
    with pytest.raises(ValueError, match="denominator"):
        audit(saved_campaign)


def test_empty_campaign_cannot_be_claimed_as_verified(tmp_path):
    (tmp_path / "campaign.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty"):
        audit(tmp_path)


def test_lost_request_cannot_be_claimed_as_verified(tmp_path):
    summary = {
        "repeat": 1,
        "users": 10,
        "start_utc": "2026-10-16T00:00:00+00:00",
        "end_utc": "2026-10-16T00:01:00+00:00",
        "measured_seconds": 60,
        "total": {"requests": 100},
        "started_requests": 101,
        "tail_requests": 0,
        "incomplete_requests": 0,
    }
    stage = tmp_path / "repeat-1-users-10"
    stage.mkdir()
    (stage / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (tmp_path / "campaign.json").write_text(json.dumps([summary]), encoding="utf-8")
    (tmp_path / "environment.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="accounting"):
        audit(tmp_path)

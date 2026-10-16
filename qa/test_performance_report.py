import json
import xml.etree.ElementTree as ET
from unittest.mock import Mock

import pytest

from mall_api_test.repositories.performance_repository import PerformanceRepository
from performance.report import chart, render


def test_chart_handles_a_single_level_and_zero_measurements():
    result = [{"users": 10, "repeat": 1, "total": {"p95_ms": 0}}]
    svg = chart(result, "p95_ms", "P95 <test>", "ms")
    ET.fromstring(svg)
    assert "&lt;test&gt;" in svg
    assert "nan" not in svg.lower()
    assert "inf" not in svg.lower()


def test_report_preserves_each_repeat_and_does_not_average_percentiles(tmp_path):
    results = []
    for repeat, p95 in [(1, 10), (2, 90)]:
        results.append(
            {
                "users": 10,
                "repeat": repeat,
                "measured_seconds": 300,
                "total": {
                    "requests": 100000,
                    "failures": repeat - 1,
                    "success_rps": (100000 - (repeat - 1)) / 300,
                    "p95_ms": p95,
                    "p99_ms": 100,
                    "failure_ratio": (repeat - 1) / 100000,
                },
                "generator_cpu_median_percent": 5,
                "stop_reasons": [],
                "comparison": "first_level",
            }
        )
    (tmp_path / "campaign.json").write_text(json.dumps(results), encoding="utf-8")
    render(tmp_path)
    svg = (tmp_path / "p95_ms.svg").read_text(encoding="utf-8")
    assert "p95_ms=10" in svg
    assert "p95_ms=90" in svg
    assert "p95_ms=50" not in svg
    assert (tmp_path / "index.html").is_file()
    assert "0.00100%" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_empty_campaign_is_not_rendered_as_success(tmp_path):
    (tmp_path / "campaign.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        render(tmp_path)


def test_stopped_level_is_visibly_distinguished_from_valid_measurements():
    result = [
        {
            "users": 160,
            "repeat": 1,
            "total": {"p95_ms": 130},
            "stop_reasons": ["generator_cpu_limit"],
        }
    ]
    root = ET.fromstring(chart(result, "p95_ms", "P95", "ms"))
    circle = root.find(".//{http://www.w3.org/2000/svg}circle")
    assert circle.attrib["fill"] == "#b02020"
    assert "generator_cpu_limit" in "".join(root.itertext())


def test_database_telemetry_only_reads_status_counters():
    db = Mock()
    db.query_all.return_value = [{"Variable_name": "Threads_running", "Value": "2"}]
    assert PerformanceRepository(db).snapshot() == {"Threads_running": 2}
    db.execute.assert_not_called()
    assert "SHOW GLOBAL STATUS" in db.query_all.call_args.args[0]

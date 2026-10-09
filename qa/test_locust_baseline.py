from unittest.mock import Mock

import pytest

from performance.locustfile import MallPortalUser, enforce_baseline


@pytest.mark.parametrize(
    "status,body",
    [
        (500, {"code": 200, "data": []}),
        (200, {"code": 401, "data": []}),
        (200, {"code": 200, "data": {}}),
    ],
)
def test_invalid_responses_are_recorded_as_locust_failures(status, body):
    response = Mock(status_code=status)
    response.json.return_value = body
    assert MallPortalUser._validate(response, "cart") is None
    response.failure.assert_called_once()
    response.success.assert_not_called()


def test_valid_response_is_recorded_as_success():
    response = Mock(status_code=200)
    response.json.return_value = {"code": 200, "data": []}
    assert MallPortalUser._validate(response, "cart") == response.json.return_value
    response.success.assert_called_once()
    response.failure.assert_not_called()


@pytest.mark.parametrize(
    "requests,fail_ratio,p95,expected",
    [(0, 0, None, 1), (100, 0.01, 10, 1), (100, 0, 1000, 1), (100, 0, 10, 0)],
)
def test_baseline_thresholds_and_empty_runs(requests, fail_ratio, p95, expected):
    environment = Mock(process_exit_code=0)
    environment.stats.total.num_requests = requests
    environment.stats.total.fail_ratio = fail_ratio
    environment.stats.total.get_response_time_percentile.return_value = p95
    enforce_baseline(environment)
    assert environment.process_exit_code == expected

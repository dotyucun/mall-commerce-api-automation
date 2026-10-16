import pytest

from mall_api_test.common.performance_window import RequestWindow


def test_warmup_and_requests_after_deadline_are_excluded():
    window = RequestWindow()
    assert window.start_request(0) is None
    window.begin(100, 60)
    assert window.start_request(99) is None
    assert window.start_request(160) is None
    assert window.start_request(161) is None
    assert window.started_requests == 0


def test_request_token_zero_is_valid_and_completes_in_window():
    window = RequestWindow()
    window.begin(100, 60)
    token = window.start_request(100)
    assert token == 0
    assert window.finish_request(token, 101) == "steady"
    assert not window.pending


def test_late_completion_is_recorded_as_tail_not_lost_or_added_to_window():
    window = RequestWindow()
    window.begin(0, 90)
    token = window.start_request(89)
    assert window.finish_request(token, 92) == "tail"
    assert window.started_requests == 1


def test_cancelled_request_remains_visible_in_pending_accounting():
    window = RequestWindow()
    window.begin(0, 90)
    window.start_request(89)
    assert window.started_requests == 1
    assert len(window.pending) == 1


def test_duplicate_completion_and_second_begin_are_rejected():
    window = RequestWindow()
    window.begin(0, 90)
    token = window.start_request(1)
    window.finish_request(token, 2)
    with pytest.raises(ValueError, match="duplicate"):
        window.finish_request(token, 3)
    with pytest.raises(ValueError):
        window.begin(4, 90)

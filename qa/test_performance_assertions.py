import pytest

from mall_api_test.common.performance_assertions import validate_read_payload


@pytest.mark.parametrize(
    "operation,data",
    [
        ("login", {"tokenHead": "Bearer ", "token": "placeholder"}),
        ("search", {"list": [{"id": 26}]}),
        ("detail", {"product": {"id": 26}}),
        ("cart", []),
    ],
)
def test_successful_baseline_payloads(operation, data):
    validate_read_payload({"code": 200, "data": data}, operation, 26)


@pytest.mark.parametrize(
    "operation,body",
    [
        ("cart", {"code": 401, "data": []}),
        ("cart", {"code": 200, "data": {}}),
        ("search", {"code": 200, "data": {"list": []}}),
        ("detail", {"code": 200, "data": {"product": {"id": 99}}}),
        ("login", {"code": 200, "data": {"tokenHead": "Bearer ", "token": ""}}),
        ("login", []),
    ],
)
def test_http_success_does_not_hide_business_or_content_failure(operation, body):
    with pytest.raises(AssertionError):
        validate_read_payload(body, operation, 26)

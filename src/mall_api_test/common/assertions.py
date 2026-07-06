from decimal import Decimal
from typing import Any


def assert_api_success(body: dict, expected_code: int = 200) -> None:
    assert isinstance(body, dict), f"Response body is not an object: {body!r}"
    assert body.get("code") == expected_code, f"API failed: {body}"


def assert_business_error(
    body: dict,
    expected_code: int = 500,
    message_contains: str | None = None,
) -> None:
    assert isinstance(body, dict), f"Response body is not an object: {body!r}"
    assert body.get("code") == expected_code, f"Expected business error {expected_code}: {body}"
    if message_contains is not None:
        assert message_contains in str(body.get("message", "")), body


def get_data(body: dict) -> Any:
    assert_api_success(body)
    return body.get("data")


def as_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def assert_decimal_equal(actual: Any, expected: Any) -> None:
    assert as_decimal(actual) == as_decimal(expected), f"Expected {expected}, got {actual}"

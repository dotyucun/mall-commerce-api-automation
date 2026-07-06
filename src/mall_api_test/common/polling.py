import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(
    operation: Callable[[], T],
    predicate: Callable[[T], bool],
    *,
    timeout: float,
    interval: float = 2.0,
    description: str,
) -> T:
    deadline = time.monotonic() + timeout
    last_value: T | None = None
    while time.monotonic() < deadline:
        last_value = operation()
        if predicate(last_value):
            return last_value
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for {description}; last value: {last_value!r}")

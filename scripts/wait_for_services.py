import sys
import time

import requests

URLS = [
    "http://localhost:8080/actuator/health",
    "http://localhost:8085/actuator/health",
]


def main() -> int:
    deadline = time.monotonic() + 180
    pending = set(URLS)
    while pending and time.monotonic() < deadline:
        for url in list(pending):
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200 and response.json().get("status") == "UP":
                    pending.remove(url)
                    print(f"ready: {url}")
            except (requests.RequestException, ValueError):
                pass
        if pending:
            time.sleep(3)
    if pending:
        print(f"services not ready: {sorted(pending)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

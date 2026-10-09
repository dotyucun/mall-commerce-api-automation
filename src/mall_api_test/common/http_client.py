import json
import logging
from typing import Any
from urllib.parse import urljoin

import allure
import requests

from mall_api_test.common.redaction import sanitize
from mall_api_test.config.settings import SETTINGS

LOGGER = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, base_url: str, name: str, timeout: int | None = None):
        self.base_url = base_url.rstrip("/") + "/"
        self.name = name
        self.timeout = timeout or SETTINGS.request_timeout
        self.session = requests.Session()

    def set_authorization(self, token: str) -> None:
        self.session.headers.update({"Authorization": token})

    def clear_authorization(self) -> None:
        self.session.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        path: str,
        *,
        expected_http_status: int = 200,
        **kwargs: Any,
    ) -> dict:
        timeout = kwargs.pop("timeout", self.timeout)
        url = urljoin(self.base_url, path.lstrip("/"))
        response = self.session.request(method, url, timeout=timeout, **kwargs)

        try:
            body = response.json()
        except ValueError as exc:
            self._attach_exchange(method, url, kwargs, response.status_code, "<non-JSON body>")
            raise AssertionError(f"{self.name} response is not JSON") from exc

        self._attach_exchange(method, url, kwargs, response.status_code, body)
        assert response.status_code == expected_http_status, (
            f"{self.name} HTTP status expected {expected_http_status}, "
            f"got {response.status_code}: {sanitize(body)}"
        )
        assert isinstance(body, dict), (
            f"{self.name} response body is not an object: {sanitize(body)!r}"
        )
        return body

    def _attach_exchange(
        self,
        method: str,
        url: str,
        kwargs: dict,
        status_code: int,
        body: Any,
    ) -> None:
        exchange = {
            "request": {
                "method": method.upper(),
                "url": url,
                "params": sanitize(kwargs.get("params")),
                "json": sanitize(kwargs.get("json")),
                "data": sanitize(kwargs.get("data")),
            },
            "response": {"status_code": status_code, "body": sanitize(body)},
        }
        payload = json.dumps(exchange, ensure_ascii=False, indent=2, default=str)
        LOGGER.info("%s %s -> %s", method.upper(), url, status_code)
        allure.attach(payload, f"{self.name} {method.upper()} {url}", allure.attachment_type.JSON)

    def get(self, path: str, **kwargs: Any) -> dict:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict:
        return self.request("POST", path, **kwargs)

    def close(self) -> None:
        self.session.close()

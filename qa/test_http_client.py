from unittest.mock import Mock

import pytest

from mall_api_test.common.assertions import assert_api_success
from mall_api_test.common.http_client import HttpClient
from mall_api_test.config.settings import AccountSettings


def test_unexpected_http_response_does_not_leak_password_or_token(monkeypatch):
    client = HttpClient("http://example.invalid", "test-client")
    response = Mock(status_code=500)
    response.json.return_value = {"password": "private-password", "token": "private-token"}
    monkeypatch.setattr(client.session, "request", Mock(return_value=response))
    with pytest.raises(AssertionError) as error:
        client.get("/login")
    assert "private-password" not in str(error.value)
    assert "private-token" not in str(error.value)
    client.close()


def test_business_error_does_not_leak_sensitive_values():
    with pytest.raises(AssertionError) as error:
        assert_api_success({"code": 500, "data": {"token": "private-token"}})
    assert "private-token" not in str(error.value)


def test_account_representation_does_not_contain_password():
    assert "private-password" not in repr(AccountSettings("autotest_a", "private-password"))

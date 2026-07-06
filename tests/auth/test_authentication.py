import allure
import pytest

from mall_api_test.api.admin.admin_auth_api import AdminAuthApi
from mall_api_test.api.portal.cart_api import CartApi
from mall_api_test.api.portal.member_api import MemberApi
from mall_api_test.common.assertions import assert_business_error


@pytest.mark.smoke
@allure.feature("登录鉴权")
def test_protected_cart_requires_login(portal_client):
    body = CartApi(portal_client).list_raw()
    assert body["code"] == 401
    assert "Full authentication is required" in body["data"]


@pytest.mark.smoke
@allure.feature("登录鉴权")
def test_member_login_identity(portal_user_a, settings):
    info = MemberApi(portal_user_a).info()
    assert info["username"] == settings.user_a.username
    assert info["status"] == 1


@pytest.mark.negative
@allure.feature("登录鉴权")
def test_member_login_rejects_wrong_password(portal_client, settings):
    body = MemberApi(portal_client).login_raw(settings.user_a.username, "invalid-password")
    assert_business_error(body, expected_code=404, message_contains="用户名或密码错误")


@pytest.mark.smoke
@allure.feature("登录鉴权")
def test_admin_login_identity(authorized_admin, settings):
    info = AdminAuthApi(authorized_admin).info()
    assert info["username"] == settings.admin_account.username
    assert info["roles"]

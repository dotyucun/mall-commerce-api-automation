import allure
import pytest

from mall_api_test.api.admin.admin_product_api import AdminProductApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.api.portal.product_api import ProductApi
from mall_api_test.common.assertions import assert_business_error, assert_decimal_equal
from mall_api_test.workflows.cart_workflow import CartWorkflow
from mall_api_test.workflows.order_workflow import OrderWorkflow


@pytest.mark.regression
@allure.feature("商品可售状态")
def test_fixture_product_and_sku_match_database(
    portal_client,
    product_repository,
    settings,
    clean_test_data,
):
    products = ProductApi(portal_client).search(keyword=settings.fixture.product_keyword)
    assert [product["id"] for product in products] == [settings.fixture.product_id]

    detail = ProductApi(portal_client).detail(settings.fixture.product_id)
    api_sku = next(sku for sku in detail["skuStockList"] if sku["id"] == settings.fixture.sku_id)
    db_product = product_repository.get_product(settings.fixture.product_id)
    db_sku = product_repository.get_sku(settings.fixture.sku_id)
    assert db_product["publish_status"] == 1
    assert api_sku["stock"] == db_sku["stock"]
    assert_decimal_equal(api_sku["price"], db_sku["price"])


@pytest.mark.e2e
@allure.feature("商品可售状态")
def test_admin_unpublish_removes_product_from_portal_search(
    portal_client,
    authorized_admin,
    settings,
    product_repository,
    clean_test_data,
):
    admin_product_api = AdminProductApi(authorized_admin)
    admin_product_api.set_publish_status([settings.fixture.product_id], 0)

    assert ProductApi(portal_client).search(keyword=settings.fixture.product_keyword) == []
    assert product_repository.get_product(settings.fixture.product_id)["publish_status"] == 0


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-5: 下架商品仍可通过旧购物车生成订单",
    strict=True,
)
@allure.feature("商品可售状态")
def test_unpublished_product_cannot_be_ordered_from_stale_cart(
    portal_user_a,
    authorized_admin,
    settings,
    clean_test_data,
):
    cart_entry = CartWorkflow(portal_user_a, settings.fixture).add_fixture_item()
    AdminProductApi(authorized_admin).set_publish_status([settings.fixture.product_id], 0)

    order_api = OrderApi(portal_user_a)
    confirm = order_api.generate_confirm_order([cart_entry["id"]])
    address = OrderWorkflow._choose_address(confirm["memberReceiveAddressList"])
    body = order_api.generate_order_raw([cart_entry["id"]], address["id"])
    assert_business_error(body)

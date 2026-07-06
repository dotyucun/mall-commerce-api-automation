import allure
import pytest

from mall_api_test.api.portal.cart_api import CartApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import assert_business_error
from mall_api_test.workflows.cart_workflow import CartWorkflow
from mall_api_test.workflows.order_workflow import OrderWorkflow


@pytest.mark.regression
@allure.feature("购物车规则")
def test_adding_same_sku_merges_quantity(portal_user_a, settings, clean_test_data):
    workflow = CartWorkflow(portal_user_a, settings.fixture)
    workflow.add_fixture_item(quantity=1)
    CartApi(portal_user_a).add(workflow.build_item(quantity=2))

    cart_items = CartApi(portal_user_a).list()
    assert len(cart_items) == 1
    assert cart_items[0]["quantity"] == 3


@pytest.mark.regression
@allure.feature("购物车规则")
def test_quantity_update_is_used_by_promotion_calculation(
    portal_user_a,
    settings,
    clean_test_data,
):
    cart_entry = CartWorkflow(portal_user_a, settings.fixture).add_fixture_item()
    cart_api = CartApi(portal_user_a)
    cart_api.update_quantity(cart_entry["id"], 3)

    promotion_items = cart_api.list_promotion([cart_entry["id"]])
    assert len(promotion_items) == 1
    assert promotion_items[0]["quantity"] == 3


@pytest.mark.negative
@allure.feature("购物车数据隔离")
def test_user_cannot_delete_another_users_cart_item(
    portal_user_a,
    portal_user_b,
    settings,
    clean_test_data,
):
    cart_entry = CartWorkflow(portal_user_a, settings.fixture).add_fixture_item()

    body = CartApi(portal_user_b).delete_raw([cart_entry["id"]])
    assert_business_error(body)
    assert [item["id"] for item in CartApi(portal_user_a).list()] == [cart_entry["id"]]


@pytest.mark.negative
@allure.feature("购物车数据隔离")
def test_clearing_one_users_cart_does_not_clear_another_users_cart(
    portal_user_a,
    portal_user_b,
    settings,
    clean_test_data,
):
    CartWorkflow(portal_user_a, settings.fixture).add_fixture_item()
    cart_b = CartWorkflow(portal_user_b, settings.fixture).add_fixture_item()

    CartApi(portal_user_a).clear()
    assert CartApi(portal_user_a).list() == []
    assert [item["id"] for item in CartApi(portal_user_b).list()] == [cart_b["id"]]


@pytest.mark.negative
@allure.feature("购物车库存边界")
def test_order_rejects_quantity_above_real_stock(
    portal_user_a,
    settings,
    product_repository,
    clean_test_data,
):
    before = product_repository.stock_snapshot(settings.fixture.sku_id)
    cart_entry = CartWorkflow(portal_user_a, settings.fixture).add_fixture_item(
        quantity=before.stock + 1
    )
    order_api = OrderApi(portal_user_a)
    confirm = order_api.generate_confirm_order([cart_entry["id"]])
    address = OrderWorkflow._choose_address(confirm["memberReceiveAddressList"])

    body = order_api.generate_order_raw([cart_entry["id"]], address["id"])
    assert_business_error(body, message_contains="库存不足")
    assert product_repository.stock_snapshot(settings.fixture.sku_id) == before

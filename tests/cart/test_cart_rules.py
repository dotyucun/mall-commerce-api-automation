import allure
import pytest

from mall_api_test.api.portal.cart_api import CartApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import assert_business_error
from mall_api_test.common.known_defects import KnownDefectError
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


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-11: 修改购物车规格接口缺少会员所有权校验",
    strict=True,
    raises=KnownDefectError,
)
@allure.feature("购物车数据隔离")
def test_user_cannot_replace_another_users_cart_item_attributes(
    portal_user_a,
    portal_user_b,
    settings,
    clean_test_data,
):
    workflow_a = CartWorkflow(portal_user_a, settings.fixture)
    cart_entry = workflow_a.add_fixture_item()
    cart_api_b = CartApi(portal_user_b)
    cart_api_b.clean()

    body = cart_api_b.update_attr_raw(workflow_a.build_item() | {"id": cart_entry["id"]})
    cart_a = CartApi(portal_user_a).list()
    cart_b = cart_api_b.list()
    if body["code"] == 200:
        assert cart_a == []
        assert [item["productSkuId"] for item in cart_b] == [cart_entry["productSkuId"]]
        raise KnownDefectError("GH-11: user B removed user A's cart item via /cart/update/attr")
    assert_business_error(body)
    assert [item["id"] for item in cart_a] == [cart_entry["id"]]
    assert cart_b == []


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-12: 购物车接受非正数量",
    strict=True,
    raises=KnownDefectError,
)
@pytest.mark.parametrize("quantity", [0, -1])
@allure.feature("购物车数量边界")
def test_cart_rejects_non_positive_quantity(
    quantity,
    portal_user_a,
    settings,
    clean_test_data,
):
    workflow = CartWorkflow(portal_user_a, settings.fixture)
    workflow.cart_api.clean()

    body = workflow.cart_api.add_raw(workflow.build_item(quantity=quantity))
    cart_items = workflow.cart_api.list()
    if body["code"] == 200:
        assert [item["quantity"] for item in cart_items] == [quantity]
        raise KnownDefectError(f"GH-12: cart accepted quantity {quantity}")
    assert_business_error(body)
    assert cart_items == []


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-12: 负数量购物车项可生成负金额订单并减少锁定库存",
    strict=True,
    raises=KnownDefectError,
)
@allure.feature("购物车数量边界")
def test_negative_cart_quantity_cannot_produce_order(
    portal_user_a,
    settings,
    order_repository,
    product_repository,
    clean_test_data,
):
    before = product_repository.stock_snapshot(settings.fixture.sku_id)
    workflow = CartWorkflow(portal_user_a, settings.fixture)
    cart_entry = workflow.add_fixture_item()

    update_body = workflow.cart_api.update_quantity_raw(cart_entry["id"], -2)
    if update_body["code"] != 200:
        assert_business_error(update_body)
        return
    order_api = OrderApi(portal_user_a)
    confirm = order_api.generate_confirm_order([cart_entry["id"]])
    address = OrderWorkflow._choose_address(confirm["memberReceiveAddressList"])

    body = order_api.generate_order_raw([cart_entry["id"]], address["id"])
    after = product_repository.stock_snapshot(settings.fixture.sku_id)
    if body["code"] == 200:
        order = order_repository.get(body["data"]["order"]["id"])
        items = order_repository.get_items(order["id"])
        assert order["pay_amount"] < 0
        assert [item["product_quantity"] for item in items] == [-2]
        assert after.stock == before.stock
        assert after.lock_stock == before.lock_stock - 2
        raise KnownDefectError("GH-12: quantity -2 produced a negative order and lock_stock")
    assert_business_error(body)
    assert after == before


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

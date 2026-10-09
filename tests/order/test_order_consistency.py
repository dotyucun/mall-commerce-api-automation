import allure
import pytest

from mall_api_test.api.admin.admin_order_api import AdminOrderApi
from mall_api_test.api.portal.cart_api import CartApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import as_decimal, assert_decimal_equal
from mall_api_test.common.known_defects import KnownDefectError
from mall_api_test.common.order_assertions import (
    assert_order_amounts_match_items,
    assert_order_created,
)


@pytest.mark.regression
@allure.feature("订单金额与快照")
def test_generated_order_matches_database_and_item_amounts(
    order_workflow_a,
    order_repository,
    portal_user_a,
    settings,
    clean_test_data,
):
    context = order_workflow_a.create(quantity=2)
    assert_order_created(context.order, settings.user_a.username)

    db_order = order_repository.get(context.order_id)
    db_items = order_repository.get_items(context.order_id)
    assert db_order is not None
    assert len(db_items) == 1
    assert_order_amounts_match_items(db_order, db_items)
    assert db_items[0]["product_id"] == context.product_id
    assert db_items[0]["product_sku_id"] == context.sku_id
    assert db_items[0]["product_quantity"] == context.quantity
    assert_decimal_equal(db_items[0]["product_price"], context.cart_item["price"])
    promotion_item = context.confirm["cartPromotionItemList"][0]
    assert_decimal_equal(
        db_items[0]["real_amount"],
        as_decimal(promotion_item["price"]) - as_decimal(promotion_item["reduceAmount"]),
    )
    assert_decimal_equal(db_order["pay_amount"], context.confirm["calcAmount"]["payAmount"])
    assert CartApi(portal_user_a).list() == []


@pytest.mark.regression
@allure.feature("订单库存一致性")
def test_cancel_releases_locked_stock_without_deducting_real_stock(
    order_workflow_a,
    order_repository,
    product_repository,
    portal_user_a,
    settings,
    clean_test_data,
):
    before = product_repository.stock_snapshot(settings.fixture.sku_id)
    context = order_workflow_a.create(quantity=2)
    after_create = product_repository.stock_snapshot(context.sku_id)
    assert after_create.stock == before.stock
    assert after_create.lock_stock == before.lock_stock + context.quantity

    OrderApi(portal_user_a).cancel(context.order_id)
    assert order_repository.get(context.order_id)["status"] == 4
    assert product_repository.stock_snapshot(context.sku_id) == before


@pytest.mark.e2e
@allure.feature("订单跨端生命周期")
def test_order_lifecycle_updates_stock_logistics_and_history(
    order_workflow_a,
    order_repository,
    product_repository,
    portal_user_a,
    authorized_admin,
    settings,
    clean_test_data,
):
    portal_order_api = OrderApi(portal_user_a)
    admin_order_api = AdminOrderApi(authorized_admin)
    before = product_repository.stock_snapshot(settings.fixture.sku_id)
    context = order_workflow_a.create(quantity=2)

    portal_order_api.pay(context.order_id, pay_type=0)
    paid = order_repository.get(context.order_id)
    after_pay = product_repository.stock_snapshot(context.sku_id)
    assert paid["status"] == 1
    assert paid["payment_time"] is not None
    assert after_pay.stock == before.stock - context.quantity
    assert after_pay.lock_stock == before.lock_stock

    admin_orders = admin_order_api.list(order_sn=context.order_sn, status=1)
    assert [order["id"] for order in admin_orders] == [context.order_id]
    admin_order_api.delivery(context.order_id, "AUTO_EXPRESS", "AUTO-LIFECYCLE")
    delivered = admin_order_api.detail(context.order_id)
    assert delivered["status"] == 2
    assert delivered["deliveryCompany"] == "AUTO_EXPRESS"
    assert delivered["deliverySn"] == "AUTO-LIFECYCLE"

    portal_order_api.confirm_receive(context.order_id)
    completed = order_repository.get(context.order_id)
    assert completed["status"] == 3
    assert completed["confirm_status"] == 1
    assert completed["receive_time"] is not None
    delivery_histories = [
        item
        for item in order_repository.get_histories(context.order_id)
        if item["order_status"] == 2
    ]
    assert len(delivery_histories) == 1
    assert delivery_histories[0]["operate_man"] == "后台管理员"
    assert delivery_histories[0]["note"] == "完成发货"


@pytest.mark.regression
@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-7: 后台关闭待付款订单未释放锁定库存",
    strict=True,
    raises=KnownDefectError,
)
@allure.feature("订单关闭")
def test_admin_close_cancels_unpaid_order_and_records_history(
    order_workflow_a,
    order_repository,
    authorized_admin,
    product_repository,
    settings,
    clean_test_data,
):
    before_stock = product_repository.stock_snapshot(settings.fixture.sku_id)
    context = order_workflow_a.create()
    AdminOrderApi(authorized_admin).close([context.order_id], "自动化关闭待付款订单")

    order = order_repository.get(context.order_id)
    histories = order_repository.get_histories(context.order_id)
    assert order["status"] == 4
    assert any(
        history["order_status"] == 4 and "自动化关闭待付款订单" in history["note"]
        for history in histories
    )
    after_close = product_repository.stock_snapshot(context.sku_id)
    assert after_close.stock == before_stock.stock
    if after_close.lock_stock != before_stock.lock_stock:
        assert after_close.lock_stock == before_stock.lock_stock + context.quantity
        raise KnownDefectError("GH-7: admin close left the unpaid order's stock locked")
    assert after_close == before_stock

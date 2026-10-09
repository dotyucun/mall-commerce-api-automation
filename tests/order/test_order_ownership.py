import allure
import pytest

from mall_api_test.api.admin.admin_order_api import AdminOrderApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import assert_business_error
from mall_api_test.common.known_defects import KnownDefectError


@pytest.mark.negative
@allure.feature("订单用户隔离")
def test_user_cannot_confirm_another_users_delivered_order(
    order_workflow_a,
    order_repository,
    portal_user_a,
    portal_user_b,
    authorized_admin,
    clean_test_data,
):
    context = order_workflow_a.create()
    OrderApi(portal_user_a).pay(context.order_id)
    AdminOrderApi(authorized_admin).delivery(context.order_id, "AUTO_EXPRESS", "OWNERSHIP-CONFIRM")

    body = OrderApi(portal_user_b).confirm_receive_raw(context.order_id)
    assert_business_error(body, message_contains="不能确认他人订单")
    assert order_repository.get(context.order_id)["status"] == 2


@pytest.mark.negative
@allure.feature("订单用户隔离")
def test_user_cannot_delete_another_users_closed_order(
    order_workflow_a,
    order_repository,
    portal_user_a,
    portal_user_b,
    clean_test_data,
):
    context = order_workflow_a.create()
    OrderApi(portal_user_a).cancel(context.order_id)

    body = OrderApi(portal_user_b).delete_raw(context.order_id)
    assert_business_error(body, message_contains="不能删除他人订单")
    assert order_repository.get(context.order_id)["delete_status"] == 0


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-3: 订单详情、取消和支付接口缺少会员所有权校验",
    strict=True,
    raises=KnownDefectError,
)
@pytest.mark.parametrize("operation", ["detail", "cancel", "pay"])
@allure.feature("订单用户隔离")
def test_user_cannot_access_or_mutate_another_users_order(
    operation,
    order_workflow_a,
    order_repository,
    product_repository,
    portal_user_b,
    clean_test_data,
):
    context = order_workflow_a.create()
    before_order = order_repository.get(context.order_id)
    before_stock = product_repository.stock_snapshot(context.sku_id)
    order_api_b = OrderApi(portal_user_b)
    operations = {
        "detail": lambda: order_api_b.detail_raw(context.order_id),
        "cancel": lambda: order_api_b.cancel_raw(context.order_id),
        "pay": lambda: order_api_b.pay_raw(context.order_id),
    }

    body = operations[operation]()
    after_order = order_repository.get(context.order_id)
    after_stock = product_repository.stock_snapshot(context.sku_id)
    if body["code"] == 200:
        if operation == "detail":
            assert body["data"]["id"] == context.order_id
            assert body["data"]["memberId"] == before_order["member_id"]
            assert after_order == before_order
            assert after_stock == before_stock
        elif operation == "cancel":
            assert after_order["status"] == 4
            assert after_stock.stock == before_stock.stock
            assert after_stock.lock_stock == before_stock.lock_stock - context.quantity
        else:
            assert after_order["status"] == 1
            assert after_stock.stock == before_stock.stock - context.quantity
            assert after_stock.lock_stock == before_stock.lock_stock - context.quantity
        raise KnownDefectError(f"GH-3: user B successfully executed {operation} on user A's order")
    assert_business_error(body)
    assert after_order == before_order
    assert after_stock == before_stock

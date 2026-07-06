import allure
import pytest

from mall_api_test.api.admin.admin_order_api import AdminOrderApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import assert_business_error


@pytest.mark.negative
@allure.feature("订单状态保护")
def test_unpaid_order_cannot_be_delivered(
    order_workflow_a,
    order_repository,
    authorized_admin,
    clean_test_data,
):
    context = order_workflow_a.create()
    body = AdminOrderApi(authorized_admin).delivery_raw(
        context.order_id, "AUTO_EXPRESS", "INVALID-UNPAID"
    )
    assert_business_error(body)
    order = order_repository.get(context.order_id)
    assert order["status"] == 0
    assert order["delivery_sn"] is None


@pytest.mark.negative
@allure.feature("订单状态保护")
def test_unshipped_order_cannot_be_confirmed(
    order_workflow_a,
    order_repository,
    portal_user_a,
    clean_test_data,
):
    context = order_workflow_a.create()
    body = OrderApi(portal_user_a).confirm_receive_raw(context.order_id)
    assert_business_error(body, message_contains="还未发货")
    assert order_repository.get(context.order_id)["status"] == 0


@pytest.mark.negative
@allure.feature("订单状态保护")
def test_completed_order_cannot_be_confirmed_twice(
    order_workflow_a,
    order_repository,
    portal_user_a,
    clean_test_data,
):
    context = order_workflow_a.complete()
    body = OrderApi(portal_user_a).confirm_receive_raw(context.order_id)
    assert_business_error(body, message_contains="还未发货")
    assert order_repository.get(context.order_id)["status"] == 3


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-1: 发货更新失败仍写入完成发货操作记录",
    strict=True,
)
@allure.feature("订单状态保护")
def test_failed_delivery_does_not_write_delivery_history(
    order_workflow_a,
    order_repository,
    authorized_admin,
    clean_test_data,
):
    context = order_workflow_a.create()
    body = AdminOrderApi(authorized_admin).delivery_raw(
        context.order_id, "AUTO_EXPRESS", "INVALID-HISTORY"
    )
    assert_business_error(body)
    assert [
        history
        for history in order_repository.get_histories(context.order_id)
        if history["order_status"] == 2
    ] == []


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-2: 重复调用支付成功接口会再次扣减库存",
    strict=True,
)
@allure.feature("订单支付幂等性")
def test_duplicate_payment_is_rejected_without_second_stock_deduction(
    order_workflow_a,
    product_repository,
    portal_user_a,
    clean_test_data,
):
    context = order_workflow_a.create()
    order_api = OrderApi(portal_user_a)
    order_api.pay(context.order_id)
    after_first_payment = product_repository.stock_snapshot(context.sku_id)

    body = order_api.pay_raw(context.order_id)
    assert_business_error(body)
    assert product_repository.stock_snapshot(context.sku_id) == after_first_payment

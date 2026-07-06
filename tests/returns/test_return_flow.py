import allure
import pytest

from mall_api_test.api.admin.admin_return_api import AdminReturnApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.api.portal.return_api import ReturnApi
from mall_api_test.common.assertions import assert_business_error, assert_decimal_equal
from mall_api_test.workflows.return_workflow import ReturnWorkflow


@pytest.mark.e2e
@allure.feature("订单退货闭环")
def test_completed_order_return_is_approved_and_received(
    order_workflow_a,
    return_workflow_a,
    return_repository,
    authorized_admin,
    clean_test_data,
):
    order_context = order_workflow_a.complete()
    return_context = return_workflow_a.create(order_context)

    applications = AdminReturnApi(authorized_admin).list(status=0)
    assert return_context.apply_id in [item["id"] for item in applications]
    assert_decimal_equal(
        return_context.application["product_real_price"], return_context.return_amount
    )

    return_workflow_a.approve(return_context)
    approved = return_repository.get(return_context.apply_id)
    assert approved["status"] == 1
    assert_decimal_equal(approved["return_amount"], return_context.return_amount)

    return_workflow_a.complete(return_context)
    completed = return_repository.get(return_context.apply_id)
    assert completed["status"] == 2
    assert completed["receive_man"] == "autotest_warehouse"


@pytest.mark.regression
@allure.feature("订单退货闭环")
def test_rejected_return_can_be_deleted(
    order_workflow_a,
    return_workflow_a,
    return_repository,
    authorized_admin,
    clean_test_data,
):
    return_context = return_workflow_a.create(order_workflow_a.complete())
    return_workflow_a.reject(return_context)
    assert return_repository.get(return_context.apply_id)["status"] == 3

    AdminReturnApi(authorized_admin).delete([return_context.apply_id])
    assert return_repository.get(return_context.apply_id) is None


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-4: 退货申请接口缺少订单所有权校验",
    strict=True,
)
@allure.feature("退货申请用户隔离")
def test_user_cannot_submit_return_for_another_users_order(
    order_workflow_a,
    portal_user_a,
    portal_user_b,
    clean_test_data,
):
    context = order_workflow_a.complete()
    order = OrderApi(portal_user_a).detail(context.order_id)
    payload = ReturnWorkflow.build_payload(order)

    body = ReturnApi(portal_user_b).create_raw(payload)
    assert_business_error(body)


@pytest.mark.known_issue
@pytest.mark.xfail(
    reason="GH-4: 未完成订单也可以提交退货申请",
    strict=True,
)
@allure.feature("退货申请状态保护")
def test_uncompleted_order_cannot_submit_return(
    order_workflow_a,
    portal_user_a,
    clean_test_data,
):
    context = order_workflow_a.create()
    order = OrderApi(portal_user_a).detail(context.order_id)
    payload = ReturnWorkflow.build_payload(order)

    body = ReturnApi(portal_user_a).create_raw(payload)
    assert_business_error(body)

import allure
import pytest

from mall_api_test.common.polling import wait_until


@pytest.mark.slow
@pytest.mark.timeout(120)
@allure.feature("RabbitMQ订单超时取消")
def test_unpaid_order_is_cancelled_and_locked_stock_is_released(
    order_workflow_a,
    order_repository,
    product_repository,
    test_data_manager,
    settings,
    clean_test_data,
):
    original_timeout = test_data_manager.get_order_timeout_minutes()
    before = product_repository.stock_snapshot(settings.fixture.sku_id)
    try:
        test_data_manager.set_order_timeout_minutes(1)
        context = order_workflow_a.create()
        after_create = product_repository.stock_snapshot(context.sku_id)
        assert after_create.lock_stock == before.lock_stock + context.quantity

        cancelled = wait_until(
            lambda: order_repository.get(context.order_id),
            lambda order: order is not None and order["status"] == 4,
            timeout=90,
            interval=2,
            description="RabbitMQ to cancel the unpaid order",
        )
        assert cancelled["status"] == 4
        assert product_repository.stock_snapshot(context.sku_id) == before
    finally:
        test_data_manager.set_order_timeout_minutes(original_timeout)

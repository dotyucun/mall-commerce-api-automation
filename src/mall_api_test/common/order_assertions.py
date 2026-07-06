from mall_api_test.common.assertions import as_decimal, assert_decimal_equal


def assert_order_state(order: dict, expected_status: int) -> None:
    assert order["status"] == expected_status, order


def assert_order_created(order: dict, expected_username: str) -> None:
    assert order["id"] is not None
    assert order["orderSn"]
    assert order["memberUsername"] == expected_username
    assert_order_state(order, 0)
    assert as_decimal(order["payAmount"]) > 0


def assert_confirm_amounts(calc_amount: dict) -> None:
    expected_pay = (
        as_decimal(calc_amount["totalAmount"])
        + as_decimal(calc_amount["freightAmount"])
        - as_decimal(calc_amount["promotionAmount"])
    )
    assert_decimal_equal(calc_amount["payAmount"], expected_pay)


def assert_order_amounts_match_items(order: dict, items: list[dict]) -> None:
    item_total = sum(
        (as_decimal(item["product_price"]) * item["product_quantity"] for item in items),
        start=as_decimal(0),
    )
    item_real_total = sum(
        (as_decimal(item["real_amount"]) * item["product_quantity"] for item in items),
        start=as_decimal(0),
    )
    assert_decimal_equal(order["total_amount"], item_total)
    assert_decimal_equal(order["pay_amount"], item_real_total)

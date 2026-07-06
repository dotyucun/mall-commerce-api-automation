from __future__ import annotations

from mall_api_test.common.assertions import assert_api_success, get_data


class OrderApi:
    def __init__(self, client):
        self.client = client

    def generate_confirm_order(self, cart_ids: list[int]) -> dict:
        return get_data(self.client.post("/order/generateConfirmOrder", json=cart_ids))

    def generate_order_raw(
        self,
        cart_ids: list[int],
        address_id: int,
        *,
        coupon_id: int | None = None,
        use_integration: int = 0,
        pay_type: int = 0,
    ) -> dict:
        return self.client.post(
            "/order/generateOrder",
            json={
                "cartIds": cart_ids,
                "memberReceiveAddressId": address_id,
                "couponId": coupon_id,
                "useIntegration": use_integration,
                "payType": pay_type,
            },
        )

    def generate_order(self, cart_ids: list[int], address_id: int) -> dict:
        return get_data(self.generate_order_raw(cart_ids, address_id))

    def list(self, status: int = -1, page_num: int = 1, page_size: int = 5) -> list[dict]:
        data = get_data(
            self.client.get(
                "/order/list",
                params={"status": status, "pageNum": page_num, "pageSize": page_size},
            )
        )
        return data["list"]

    def detail_raw(self, order_id: int) -> dict:
        return self.client.get(f"/order/detail/{order_id}")

    def detail(self, order_id: int) -> dict:
        return get_data(self.detail_raw(order_id))

    def cancel_raw(self, order_id: int) -> dict:
        return self.client.post("/order/cancelUserOrder", params={"orderId": order_id})

    def cancel(self, order_id: int) -> None:
        assert_api_success(self.cancel_raw(order_id))

    def pay_raw(self, order_id: int, pay_type: int = 0) -> dict:
        return self.client.post(
            "/order/paySuccess",
            params={"orderId": order_id, "payType": pay_type},
        )

    def pay(self, order_id: int, pay_type: int = 0) -> int:
        body = self.pay_raw(order_id, pay_type)
        assert_api_success(body)
        return body["data"]

    def confirm_receive_raw(self, order_id: int) -> dict:
        return self.client.post("/order/confirmReceiveOrder", params={"orderId": order_id})

    def confirm_receive(self, order_id: int) -> None:
        assert_api_success(self.confirm_receive_raw(order_id))

    def delete_raw(self, order_id: int) -> dict:
        return self.client.post("/order/deleteOrder", params={"orderId": order_id})

    def delete(self, order_id: int) -> None:
        assert_api_success(self.delete_raw(order_id))

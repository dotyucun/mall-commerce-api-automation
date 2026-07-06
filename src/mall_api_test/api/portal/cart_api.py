from __future__ import annotations

from mall_api_test.common.assertions import assert_api_success, get_data


class CartApi:
    def __init__(self, client):
        self.client = client

    def list_raw(self) -> dict:
        return self.client.get("/cart/list")

    def list(self) -> list[dict]:
        return get_data(self.list_raw()) or []

    def list_promotion(self, cart_ids: list[int] | None = None) -> list[dict]:
        params = None
        if cart_ids:
            params = [("cartIds", cart_id) for cart_id in cart_ids]
        return get_data(self.client.get("/cart/list/promotion", params=params)) or []

    def add_raw(self, cart_item: dict) -> dict:
        return self.client.post("/cart/add", json=cart_item)

    def add(self, cart_item: dict) -> int:
        body = self.add_raw(cart_item)
        assert_api_success(body)
        return body["data"]

    def update_quantity_raw(self, cart_id: int, quantity: int) -> dict:
        return self.client.get(
            "/cart/update/quantity",
            params={"id": cart_id, "quantity": quantity},
        )

    def update_quantity(self, cart_id: int, quantity: int) -> int:
        body = self.update_quantity_raw(cart_id, quantity)
        assert_api_success(body)
        return body["data"]

    def delete_raw(self, cart_ids: list[int]) -> dict:
        return self.client.post(
            "/cart/delete",
            params=[("ids", cart_id) for cart_id in cart_ids],
        )

    def delete(self, cart_ids: list[int]) -> int:
        body = self.delete_raw(cart_ids)
        assert_api_success(body)
        return body["data"]

    def clear(self) -> int:
        body = self.client.post("/cart/clear")
        assert_api_success(body)
        return body["data"]

    def clean(self) -> None:
        cart_items = self.list()
        if cart_items:
            self.delete([item["id"] for item in cart_items])
        assert self.list() == [], "Cart cleanup failed"

from __future__ import annotations

from mall_api_test.common.assertions import assert_api_success, get_data


class AdminOrderApi:
    def __init__(self, client):
        self.client = client

    def list(
        self,
        *,
        order_sn: str | None = None,
        status: int | None = None,
        page_num: int = 1,
        page_size: int = 5,
    ) -> list[dict]:
        params = {"pageNum": page_num, "pageSize": page_size}
        if order_sn is not None:
            params["orderSn"] = order_sn
        if status is not None:
            params["status"] = status
        return get_data(self.client.get("/order/list", params=params))["list"]

    def detail(self, order_id: int) -> dict:
        return get_data(self.client.get(f"/order/{order_id}"))

    def delivery_raw(self, order_id: int, company: str, tracking_number: str) -> dict:
        return self.client.post(
            "/order/update/delivery",
            json=[
                {
                    "orderId": order_id,
                    "deliveryCompany": company,
                    "deliverySn": tracking_number,
                }
            ],
        )

    def delivery(self, order_id: int, company: str, tracking_number: str) -> int:
        body = self.delivery_raw(order_id, company, tracking_number)
        assert_api_success(body)
        return body["data"]

    def close_raw(self, order_ids: list[int], note: str) -> dict:
        params = [("ids", order_id) for order_id in order_ids]
        params.append(("note", note))
        return self.client.post("/order/update/close", params=params)

    def close(self, order_ids: list[int], note: str) -> int:
        body = self.close_raw(order_ids, note)
        assert_api_success(body)
        return body["data"]

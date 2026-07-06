from mall_api_test.common.assertions import assert_api_success


class AdminProductApi:
    def __init__(self, client):
        self.client = client

    def set_publish_status_raw(self, product_ids: list[int], publish_status: int) -> dict:
        params = [("ids", product_id) for product_id in product_ids]
        params.append(("publishStatus", publish_status))
        return self.client.post("/product/update/publishStatus", params=params)

    def set_publish_status(self, product_ids: list[int], publish_status: int) -> int:
        body = self.set_publish_status_raw(product_ids, publish_status)
        assert_api_success(body)
        return body["data"]

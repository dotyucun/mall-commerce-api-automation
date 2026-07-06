from mall_api_test.common.assertions import assert_api_success


class ReturnApi:
    def __init__(self, client):
        self.client = client

    def create_raw(self, payload: dict) -> dict:
        return self.client.post("/returnApply/create", json=payload)

    def create(self, payload: dict) -> int:
        body = self.create_raw(payload)
        assert_api_success(body)
        return body["data"]

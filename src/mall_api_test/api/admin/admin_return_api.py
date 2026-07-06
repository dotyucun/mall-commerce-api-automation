from __future__ import annotations

from mall_api_test.common.assertions import assert_api_success, get_data


class AdminReturnApi:
    def __init__(self, client):
        self.client = client

    def list(
        self,
        *,
        status: int | None = None,
        page_num: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        params = {"pageNum": page_num, "pageSize": page_size}
        if status is not None:
            params["status"] = status
        return get_data(self.client.get("/returnApply/list", params=params))["list"]

    def detail(self, apply_id: int) -> dict:
        return get_data(self.client.get(f"/returnApply/{apply_id}"))

    def update_status_raw(self, apply_id: int, payload: dict) -> dict:
        return self.client.post(f"/returnApply/update/status/{apply_id}", json=payload)

    def update_status(self, apply_id: int, payload: dict) -> int:
        body = self.update_status_raw(apply_id, payload)
        assert_api_success(body)
        return body["data"]

    def delete(self, apply_ids: list[int]) -> int:
        body = self.client.post(
            "/returnApply/delete",
            params=[("ids", apply_id) for apply_id in apply_ids],
        )
        assert_api_success(body)
        return body["data"]

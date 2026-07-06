from mall_api_test.common.assertions import get_data


class ProductApi:
    def __init__(self, client):
        self.client = client

    def search(
        self,
        *,
        keyword: str | None = None,
        product_category_id: int | None = None,
        page_num: int = 1,
        page_size: int = 5,
        sort: int = 0,
    ) -> list[dict]:
        params = {"pageNum": page_num, "pageSize": page_size, "sort": sort}
        if keyword is not None:
            params["keyword"] = keyword
        if product_category_id is not None:
            params["productCategoryId"] = product_category_id
        return get_data(self.client.get("/product/search", params=params))["list"]

    def detail(self, product_id: int) -> dict:
        return get_data(self.client.get(f"/product/detail/{product_id}"))

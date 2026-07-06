from mall_api_test.api.portal.cart_api import CartApi
from mall_api_test.api.portal.product_api import ProductApi
from mall_api_test.config.settings import FixtureSettings


class CartWorkflow:
    def __init__(self, client, fixture: FixtureSettings):
        self.cart_api = CartApi(client)
        self.product_api = ProductApi(client)
        self.fixture = fixture

    def build_item(self, quantity: int = 1) -> dict:
        detail = self.product_api.detail(self.fixture.product_id)
        product = detail["product"]
        sku = next(
            (item for item in detail["skuStockList"] if item["id"] == self.fixture.sku_id),
            None,
        )
        assert sku is not None, f"Fixture SKU {self.fixture.sku_id} not found"
        return {
            "productId": product["id"],
            "productSkuId": sku["id"],
            "quantity": quantity,
            "price": sku["price"],
            "productPic": product["pic"],
            "productName": product["name"],
            "productSubTitle": product["subTitle"],
            "productSkuCode": sku["skuCode"],
            "productCategoryId": product["productCategoryId"],
        }

    def add_fixture_item(self, quantity: int = 1, *, clean: bool = True) -> dict:
        if clean:
            self.cart_api.clean()
        item = self.build_item(quantity)
        self.cart_api.add(item)
        cart_items = self.cart_api.list()
        matching = [entry for entry in cart_items if entry["productSkuId"] == item["productSkuId"]]
        assert len(matching) == 1, cart_items
        return matching[0]

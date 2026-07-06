from mall_api_test.models import StockSnapshot


class ProductRepository:
    def __init__(self, db):
        self.db = db

    def get_product(self, product_id: int) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, name, publish_status, delete_status, promotion_type
            FROM pms_product
            WHERE id = %s
            """,
            (product_id,),
        )

    def get_sku(self, sku_id: int) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, product_id, sku_code, price, promotion_price, stock, lock_stock
            FROM pms_sku_stock
            WHERE id = %s
            """,
            (sku_id,),
        )

    def stock_snapshot(self, sku_id: int) -> StockSnapshot:
        sku = self.get_sku(sku_id)
        assert sku is not None, f"SKU not found: {sku_id}"
        return StockSnapshot(sku_id=sku_id, stock=sku["stock"], lock_stock=sku["lock_stock"])

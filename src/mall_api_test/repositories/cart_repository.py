class CartRepository:
    def __init__(self, db):
        self.db = db

    def list_active(self, member_id: int) -> list[dict]:
        return self.db.query_all(
            """
            SELECT id, member_id, product_id, product_sku_id, quantity, delete_status
            FROM oms_cart_item
            WHERE member_id = %s AND delete_status = 0
            ORDER BY id ASC
            """,
            (member_id,),
        )

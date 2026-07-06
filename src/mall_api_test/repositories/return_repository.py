class ReturnRepository:
    def __init__(self, db):
        self.db = db

    def get(self, apply_id: int) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, order_id, order_sn, member_username, product_id,
                   product_count, product_price, product_real_price,
                   return_amount, status, handle_man, receive_man
            FROM oms_order_return_apply
            WHERE id = %s
            """,
            (apply_id,),
        )

    def latest_for_order(self, order_id: int) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, order_id, order_sn, member_username, product_id,
                   product_count, product_price, product_real_price,
                   return_amount, status
            FROM oms_order_return_apply
            WHERE order_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (order_id,),
        )

class OrderRepository:
    def __init__(self, db):
        self.db = db

    def get(self, order_id: int) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, order_sn, member_id, member_username, status, delete_status,
                   pay_type, total_amount, freight_amount, promotion_amount,
                   coupon_amount, integration_amount, discount_amount, pay_amount,
                   delivery_company, delivery_sn, confirm_status,
                   payment_time, delivery_time, receive_time
            FROM oms_order
            WHERE id = %s
            """,
            (order_id,),
        )

    def get_items(self, order_id: int) -> list[dict]:
        return self.db.query_all(
            """
            SELECT id, order_id, product_id, product_sku_id, product_quantity,
                   product_price, promotion_amount, coupon_amount,
                   integration_amount, real_amount
            FROM oms_order_item
            WHERE order_id = %s
            ORDER BY id ASC
            """,
            (order_id,),
        )

    def get_histories(self, order_id: int) -> list[dict]:
        return self.db.query_all(
            """
            SELECT id, order_id, operate_man, create_time, order_status, note
            FROM oms_order_operate_history
            WHERE order_id = %s
            ORDER BY id ASC
            """,
            (order_id,),
        )

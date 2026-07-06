from urllib.parse import quote

import requests

from mall_api_test.config.settings import Settings
from mall_api_test.repositories.member_repository import MemberRepository


class TestDataManager:
    def __init__(self, db, settings: Settings):
        self.db = db
        self.settings = settings

    def reset(self) -> None:
        usernames = (self.settings.user_a.username, self.settings.user_b.username)
        members = [MemberRepository(self.db).get_by_username(username) for username in usernames]
        member_ids = [member["id"] for member in members if member is not None]

        if member_ids:
            placeholders = ",".join(["%s"] * len(member_ids))
            orders = self.db.query_all(
                f"SELECT id FROM oms_order WHERE member_id IN ({placeholders})",
                tuple(member_ids),
            )
            order_ids = [order["id"] for order in orders]
            if order_ids:
                order_placeholders = ",".join(["%s"] * len(order_ids))
                params = tuple(order_ids)
                self.db.execute(
                    f"DELETE FROM oms_order_return_apply WHERE order_id IN ({order_placeholders})",
                    params,
                )
                history_sql = (
                    "DELETE FROM oms_order_operate_history "
                    f"WHERE order_id IN ({order_placeholders})"
                )
                self.db.execute(history_sql, params)
                self.db.execute(
                    f"DELETE FROM oms_order_item WHERE order_id IN ({order_placeholders})",
                    params,
                )
                self.db.execute(
                    f"DELETE FROM oms_order WHERE id IN ({order_placeholders})",
                    params,
                )
            self.db.execute(
                f"DELETE FROM oms_cart_item WHERE member_id IN ({placeholders})",
                tuple(member_ids),
            )

        username_placeholders = ",".join(["%s"] * len(usernames))
        return_sql = (
            f"DELETE FROM oms_order_return_apply WHERE member_username IN ({username_placeholders})"
        )
        self.db.execute(return_sql, usernames)
        self.restore_product_fixture()
        self.purge_delayed_order_messages()

    def restore_product_fixture(self) -> None:
        fixture = self.settings.fixture
        self.db.execute(
            """
            UPDATE pms_product
            SET name = %s, publish_status = 1, delete_status = 0
            WHERE id = %s
            """,
            (fixture.product_keyword, fixture.product_id),
        )
        self.db.execute(
            """
            UPDATE pms_sku_stock
            SET stock = %s, lock_stock = 0
            WHERE id = %s
            """,
            (fixture.baseline_stock, fixture.sku_id),
        )

    def set_order_timeout_minutes(self, minutes: int) -> None:
        self.db.execute(
            "UPDATE oms_order_setting SET normal_order_overtime = %s WHERE id = 1",
            (minutes,),
        )

    def get_order_timeout_minutes(self) -> int:
        row = self.db.query_one("SELECT normal_order_overtime FROM oms_order_setting WHERE id = 1")
        assert row is not None
        return row["normal_order_overtime"]

    def purge_delayed_order_messages(self) -> None:
        rabbitmq = self.settings.rabbitmq
        vhost = quote("/mall", safe="")
        queue = quote("mall.order.cancel.ttl", safe="")
        response = requests.delete(
            f"{rabbitmq.management_url}/api/queues/{vhost}/{queue}/contents",
            auth=(rabbitmq.username, rabbitmq.password),
            timeout=self.settings.request_timeout,
        )
        assert response.status_code == 204, (
            f"Failed to purge RabbitMQ delayed queue: {response.status_code} {response.text}"
        )

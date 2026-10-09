from urllib.parse import quote

import bcrypt
import requests

from mall_api_test.config.settings import Settings
from mall_api_test.repositories.member_repository import MemberRepository


class TestDataManager:
    def __init__(self, db, settings: Settings):
        self.db = db
        self.settings = settings

    def validate_fixture(self) -> None:
        accounts = ((self.settings.user_a, 9001), (self.settings.user_b, 9002))
        if (
            self.settings.database.database != "mall"
            or self.settings.user_a.username != "autotest_a"
            or self.settings.user_b.username != "autotest_b"
            or self.settings.admin_account.username != "admin"
            or self.settings.fixture.product_id != 26
            or self.settings.fixture.sku_id != 110
            or not self.settings.fixture.product_keyword.startswith("AUTOTEST_")
        ):
            raise RuntimeError("Refusing database writes outside the dedicated mall test fixture")
        for account, expected_id in accounts:
            member = MemberRepository(self.db).get_by_username(account.username)
            if member is None or member["id"] != expected_id:
                raise RuntimeError(
                    f"Dedicated test member is missing or mismatched: {account.username}"
                )
        sku = self.db.query_one("SELECT product_id FROM pms_sku_stock WHERE id = %s", (110,))
        if sku is None or sku["product_id"] != 26:
            raise RuntimeError("Dedicated product/SKU fixture is missing or mismatched")

    def prepare_credentials(self) -> None:
        self.validate_fixture()
        accounts = (
            ("ums_admin", self.settings.admin_account),
            ("ums_member", self.settings.user_a),
            ("ums_member", self.settings.user_b),
        )
        for table, account in accounts:
            encoded = account.password.encode("utf-8")
            if not encoded or len(encoded) > 72:
                raise ValueError("Test account password must contain 1 to 72 UTF-8 bytes")
            row = self.db.query_one(
                f"SELECT password FROM {table} WHERE username = %s", (account.username,)
            )
            if row is None:
                raise RuntimeError(f"Seed account is missing: {account.username}")
            try:
                matches = bcrypt.checkpw(encoded, row["password"].encode("ascii"))
            except (ValueError, UnicodeEncodeError):
                matches = False
            if not matches:
                password_hash = bcrypt.hashpw(encoded, bcrypt.gensalt(prefix=b"2a")).decode("ascii")
                self.db.execute(
                    f"UPDATE {table} SET password = %s WHERE username = %s",
                    (password_hash, account.username),
                )

    def reset(self) -> None:
        self.validate_fixture()
        self.purge_delayed_order_messages()
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

    def verify_baseline(self) -> dict:
        self.validate_fixture()
        counts = {}
        for name, table, column, identifiers in (
            ("cart", "oms_cart_item", "member_id", (9001, 9002)),
            ("order", "oms_order", "member_id", (9001, 9002)),
            ("return", "oms_order_return_apply", "member_username", ("autotest_a", "autotest_b")),
        ):
            row = self.db.query_one(
                f"SELECT COUNT(*) AS count FROM {table} WHERE {column} IN (%s, %s)", identifiers
            )
            counts[name] = row["count"]
            assert row["count"] == 0, f"Dedicated {name} data was not cleaned: {row['count']}"
        product = self.db.query_one(
            "SELECT name, publish_status FROM pms_product WHERE id = %s", (26,)
        )
        stock = self.db.query_one(
            "SELECT stock, lock_stock FROM pms_sku_stock WHERE id = %s", (110,)
        )
        assert product["name"] == self.settings.fixture.product_keyword
        assert product["publish_status"] == 1
        assert stock == {"stock": self.settings.fixture.baseline_stock, "lock_stock": 0}
        rabbitmq = self.settings.rabbitmq
        queue_url = (
            f"{rabbitmq.management_url}/api/queues/"
            f"{quote('/mall', safe='')}/{quote('mall.order.cancel.ttl', safe='')}"
        )
        response = requests.get(
            queue_url,
            auth=(rabbitmq.username, rabbitmq.password),
            timeout=self.settings.request_timeout,
        )
        assert response.status_code == 200, "RabbitMQ queue verification failed"
        queue = response.json()
        assert queue["messages"] == 0, "Delayed test messages remain in RabbitMQ"
        return {
            "dedicated_rows": counts,
            "product": product,
            "sku": stock,
            "delayed_messages": queue["messages"],
            "order_timeout_minutes": self.get_order_timeout_minutes(),
        }

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

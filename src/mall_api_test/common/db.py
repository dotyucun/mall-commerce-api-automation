from collections.abc import Iterable
from typing import Any

import pymysql

from mall_api_test.config.settings import DatabaseSettings


class MallDb:
    def __init__(self, settings: DatabaseSettings):
        self.connection = pymysql.connect(
            host=settings.host,
            port=settings.port,
            user=settings.username,
            password=settings.password,
            database=settings.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    def query_one(self, sql: str, params: tuple | None = None) -> dict | None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql: str, params: tuple | None = None) -> list[dict]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def execute(self, sql: str, params: tuple | None = None) -> int:
        with self.connection.cursor() as cursor:
            return cursor.execute(sql, params)

    def execute_many(self, sql: str, params: Iterable[tuple[Any, ...]]) -> int:
        with self.connection.cursor() as cursor:
            return cursor.executemany(sql, params)

    def close(self) -> None:
        self.connection.close()

import os
from dataclasses import dataclass, field

from mall_api_test.config.config_loader import load_config


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class ServiceSettings:
    base_url: str


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    database: str


@dataclass(frozen=True)
class AccountSettings:
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class RabbitMqSettings:
    management_url: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class FixtureSettings:
    product_id: int
    sku_id: int
    product_keyword: str
    baseline_stock: int


@dataclass(frozen=True)
class Settings:
    portal: ServiceSettings
    admin: ServiceSettings
    database: DatabaseSettings
    admin_account: AccountSettings
    user_a: AccountSettings
    user_b: AccountSettings
    rabbitmq: RabbitMqSettings
    fixture: FixtureSettings
    request_timeout: int
    sut_repository: str
    sut_commit: str

    def require_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "MALL_ADMIN_PASSWORD": self.admin_account.password,
                "MALL_TEST_USER_A_PASSWORD": self.user_a.password,
                "MALL_TEST_USER_B_PASSWORD": self.user_b.password,
                "MALL_MYSQL_PASSWORD": self.database.password,
                "MALL_RABBITMQ_PASSWORD": self.rabbitmq.password,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def load_settings() -> Settings:
    config = load_config()
    return Settings(
        portal=ServiceSettings(
            base_url=_env("MALL_PORTAL_BASE_URL", config["portal"]["base_url"]),
        ),
        admin=ServiceSettings(
            base_url=_env("MALL_ADMIN_BASE_URL", config["admin"]["base_url"]),
        ),
        database=DatabaseSettings(
            host=_env("MALL_MYSQL_HOST", config["database"]["host"]),
            port=int(_env("MALL_MYSQL_PORT", str(config["database"]["port"]))),
            username=_env("MALL_MYSQL_USER", config["database"]["username"]),
            password=_env("MALL_MYSQL_PASSWORD"),
            database=_env("MALL_MYSQL_DATABASE", config["database"]["database"]),
        ),
        admin_account=AccountSettings(
            username=_env("MALL_ADMIN_USERNAME", config["admin"]["username"]),
            password=_env("MALL_ADMIN_PASSWORD"),
        ),
        user_a=AccountSettings(
            username=_env("MALL_TEST_USER_A", config["accounts"]["user_a"]),
            password=_env("MALL_TEST_USER_A_PASSWORD"),
        ),
        user_b=AccountSettings(
            username=_env("MALL_TEST_USER_B", config["accounts"]["user_b"]),
            password=_env("MALL_TEST_USER_B_PASSWORD"),
        ),
        rabbitmq=RabbitMqSettings(
            management_url=_env(
                "MALL_RABBITMQ_MANAGEMENT_URL", config["rabbitmq"]["management_url"]
            ),
            username=_env("MALL_RABBITMQ_USER", config["rabbitmq"]["username"]),
            password=_env("MALL_RABBITMQ_PASSWORD"),
        ),
        fixture=FixtureSettings(**config["fixture"]),
        request_timeout=int(_env("MALL_REQUEST_TIMEOUT", str(config["request_timeout"]))),
        sut_repository=config["sut"]["repository"],
        sut_commit=config["sut"]["commit"],
    )


SETTINGS = load_settings()

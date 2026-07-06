import platform
from collections.abc import Iterator
from pathlib import Path

import pytest

from mall_api_test.api.admin.admin_auth_api import AdminAuthApi
from mall_api_test.api.portal.member_api import MemberApi
from mall_api_test.common.db import MallDb
from mall_api_test.common.http_client import HttpClient
from mall_api_test.common.logging_config import configure_logging
from mall_api_test.config.settings import SETTINGS, Settings
from mall_api_test.repositories.cart_repository import CartRepository
from mall_api_test.repositories.member_repository import MemberRepository
from mall_api_test.repositories.order_repository import OrderRepository
from mall_api_test.repositories.product_repository import ProductRepository
from mall_api_test.repositories.return_repository import ReturnRepository
from mall_api_test.repositories.test_data_manager import TestDataManager
from mall_api_test.workflows.order_workflow import OrderWorkflow
from mall_api_test.workflows.return_workflow import ReturnWorkflow


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del session, exitstatus
    result_dir = Path("reports/allure-results")
    result_dir.mkdir(parents=True, exist_ok=True)
    properties = {
        "Environment": "Docker Compose local/CI",
        "Python": platform.python_version(),
        "Platform": platform.platform(),
        "SUT repository": SETTINGS.sut_repository,
        "SUT commit": SETTINGS.sut_commit,
        "mall-admin": SETTINGS.admin.base_url,
        "mall-portal": SETTINGS.portal.base_url,
    }
    content = "\n".join(f"{key}={value}" for key, value in properties.items()) + "\n"
    (result_dir / "environment.properties").write_text(content, encoding="utf-8")


@pytest.fixture(scope="session", autouse=True)
def test_logging() -> None:
    configure_logging()


@pytest.fixture(scope="session")
def settings() -> Settings:
    SETTINGS.require_credentials()
    return SETTINGS


@pytest.fixture(scope="session")
def db(settings: Settings) -> Iterator[MallDb]:
    database = MallDb(settings.database)
    yield database
    database.close()


@pytest.fixture(scope="session")
def portal_client(settings: Settings) -> Iterator[HttpClient]:
    client = HttpClient(settings.portal.base_url, "mall-portal")
    yield client
    client.close()


@pytest.fixture(scope="session")
def admin_client(settings: Settings) -> Iterator[HttpClient]:
    client = HttpClient(settings.admin.base_url, "mall-admin")
    yield client
    client.close()


def _authorized_portal_client(settings: Settings, username: str, password: str) -> HttpClient:
    client = HttpClient(settings.portal.base_url, f"mall-portal:{username}")
    client.set_authorization(MemberApi(client).login(username, password))
    return client


@pytest.fixture
def portal_user_a(settings: Settings) -> Iterator[HttpClient]:
    client = _authorized_portal_client(settings, settings.user_a.username, settings.user_a.password)
    yield client
    client.close()


@pytest.fixture
def portal_user_b(settings: Settings) -> Iterator[HttpClient]:
    client = _authorized_portal_client(settings, settings.user_b.username, settings.user_b.password)
    yield client
    client.close()


@pytest.fixture(scope="session")
def authorized_admin(settings: Settings) -> Iterator[HttpClient]:
    client = HttpClient(settings.admin.base_url, "mall-admin:admin")
    client.set_authorization(
        AdminAuthApi(client).login(
            settings.admin_account.username,
            settings.admin_account.password,
        )
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def test_data_manager(db: MallDb, settings: Settings) -> TestDataManager:
    return TestDataManager(db, settings)


@pytest.fixture
def clean_test_data(test_data_manager: TestDataManager) -> Iterator[None]:
    test_data_manager.reset()
    yield
    test_data_manager.reset()


@pytest.fixture
def member_repository(db: MallDb) -> MemberRepository:
    return MemberRepository(db)


@pytest.fixture
def product_repository(db: MallDb) -> ProductRepository:
    return ProductRepository(db)


@pytest.fixture
def cart_repository(db: MallDb) -> CartRepository:
    return CartRepository(db)


@pytest.fixture
def order_repository(db: MallDb) -> OrderRepository:
    return OrderRepository(db)


@pytest.fixture
def return_repository(db: MallDb) -> ReturnRepository:
    return ReturnRepository(db)


@pytest.fixture
def order_workflow_a(
    portal_user_a: HttpClient,
    authorized_admin: HttpClient,
    settings: Settings,
) -> OrderWorkflow:
    return OrderWorkflow(portal_user_a, settings.fixture, authorized_admin)


@pytest.fixture
def return_workflow_a(
    portal_user_a: HttpClient,
    authorized_admin: HttpClient,
    return_repository: ReturnRepository,
) -> ReturnWorkflow:
    return ReturnWorkflow(portal_user_a, authorized_admin, return_repository)

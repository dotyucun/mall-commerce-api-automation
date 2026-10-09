import os

from locust import HttpUser, between, events, task
from locust.exception import StopUser

from mall_api_test.common.performance_assertions import validate_read_payload
from mall_api_test.config.settings import SETTINGS

PRODUCT_ID = SETTINGS.fixture.product_id
MAX_FAILURE_RATIO = float(os.getenv("LOCUST_MAX_FAILURE_RATIO", "0.01"))
MAX_P95_MS = int(os.getenv("LOCUST_MAX_P95_MS", "1000"))


class MallPortalUser(HttpUser):
    host = SETTINGS.portal.base_url
    wait_time = between(0.5, 1.5)

    def on_start(self):
        with self.client.post(
            "/sso/login",
            data={"username": SETTINGS.user_a.username, "password": SETTINGS.user_a.password},
            name="POST /sso/login",
            catch_response=True,
            timeout=SETTINGS.request_timeout,
        ) as response:
            body = self._validate(response, "login")
        if body is None:
            raise StopUser()
        data = body["data"]
        self.client.headers.update({"Authorization": f"{data['tokenHead']}{data['token']}"})

    @staticmethod
    def _validate(response, operation):
        if response.status_code != 200:
            response.failure(f"HTTP status {response.status_code}")
            return None
        try:
            body = response.json()
            validate_read_payload(body, operation, PRODUCT_ID)
        except (ValueError, AssertionError) as error:
            response.failure(str(error))
            return None
        response.success()
        return body

    @task(3)
    def search_product(self):
        with self.client.get(
            "/product/search",
            params={"keyword": SETTINGS.fixture.product_keyword, "pageNum": 1, "pageSize": 5},
            name="GET /product/search",
            catch_response=True,
            timeout=SETTINGS.request_timeout,
        ) as response:
            self._validate(response, "search")

    @task(2)
    def product_detail(self):
        with self.client.get(
            f"/product/detail/{PRODUCT_ID}",
            name="GET /product/detail/:id",
            catch_response=True,
            timeout=SETTINGS.request_timeout,
        ) as response:
            self._validate(response, "detail")

    @task(1)
    def cart_list(self):
        with self.client.get(
            "/cart/list",
            name="GET /cart/list",
            catch_response=True,
            timeout=SETTINGS.request_timeout,
        ) as response:
            self._validate(response, "cart")


@events.quitting.add_listener
def enforce_baseline(environment, **_kwargs):
    stats = environment.stats.total
    if (
        stats.num_requests == 0
        or stats.fail_ratio >= MAX_FAILURE_RATIO
        or (stats.get_response_time_percentile(0.95) or 0) >= MAX_P95_MS
    ):
        environment.process_exit_code = 1

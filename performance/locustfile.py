import os

from locust import HttpUser, between, events, task

PRODUCT_ID = int(os.getenv("MALL_FIXTURE_PRODUCT_ID", "26"))
USERNAME = os.getenv("MALL_TEST_USER_A", "autotest_a")
PASSWORD = os.getenv("MALL_TEST_USER_A_PASSWORD", "")
MAX_FAILURE_RATIO = float(os.getenv("LOCUST_MAX_FAILURE_RATIO", "0.01"))
MAX_P95_MS = int(os.getenv("LOCUST_MAX_P95_MS", "1000"))


class MallPortalUser(HttpUser):
    host = os.getenv("MALL_PORTAL_BASE_URL", "http://localhost:8085")
    wait_time = between(0.5, 1.5)

    def on_start(self):
        response = self.client.post(
            "/sso/login",
            data={"username": USERNAME, "password": PASSWORD},
            name="POST /sso/login",
        )
        data = response.json()["data"]
        self.client.headers.update({"Authorization": f"{data['tokenHead']}{data['token']}"})

    @task(3)
    def search_product(self):
        self.client.get(
            "/product/search",
            params={"keyword": "AUTOTEST_PRODUCT_P20", "pageNum": 1, "pageSize": 5},
            name="GET /product/search",
        )

    @task(2)
    def product_detail(self):
        self.client.get(
            f"/product/detail/{PRODUCT_ID}",
            name="GET /product/detail/:id",
        )

    @task(1)
    def cart_list(self):
        self.client.get("/cart/list", name="GET /cart/list")


@events.quitting.add_listener
def enforce_baseline(environment, **_kwargs):
    stats = environment.stats.total
    if (
        stats.fail_ratio > MAX_FAILURE_RATIO
        or stats.get_response_time_percentile(0.95) > MAX_P95_MS
    ):
        environment.process_exit_code = 1

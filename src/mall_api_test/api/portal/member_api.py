from mall_api_test.common.assertions import get_data


class MemberApi:
    def __init__(self, client):
        self.client = client

    def login_raw(self, username: str, password: str) -> dict:
        return self.client.post(
            "/sso/login",
            data={"username": username, "password": password},
        )

    def login(self, username: str, password: str) -> str:
        data = get_data(self.login_raw(username, password))
        return f"{data['tokenHead']}{data['token']}"

    def info(self) -> dict:
        return get_data(self.client.get("/sso/info"))

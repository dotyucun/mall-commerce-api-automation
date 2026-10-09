from mall_api_test.common.assertions import assert_api_success


def validate_read_payload(body: dict, operation: str, product_id: int) -> None:
    assert_api_success(body)
    data = body.get("data")
    if operation == "login":
        assert isinstance(data, dict), "Login data is not an object"
        assert data.get("tokenHead") == "Bearer ", "Login token prefix is invalid"
        assert isinstance(data.get("token"), str) and data["token"], "Login token is missing"
    elif operation == "search":
        assert isinstance(data, dict), "Search data is not an object"
        assert isinstance(data.get("list"), list), "Search product list is missing"
        assert any(
            isinstance(item, dict) and item.get("id") == product_id for item in data["list"]
        ), "Dedicated product is missing from search"
    elif operation == "detail":
        assert isinstance(data, dict), "Product detail is not an object"
        assert isinstance(data.get("product"), dict), "Product is missing from detail"
        assert data["product"].get("id") == product_id, "Product detail ID is incorrect"
    elif operation == "cart":
        assert isinstance(data, list), "Cart data is not a list"
    else:
        raise ValueError(f"Unknown baseline operation: {operation}")

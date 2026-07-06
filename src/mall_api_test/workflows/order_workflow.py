import uuid

from mall_api_test.api.admin.admin_order_api import AdminOrderApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.common.assertions import as_decimal
from mall_api_test.common.order_assertions import assert_confirm_amounts
from mall_api_test.config.settings import FixtureSettings
from mall_api_test.models import OrderContext
from mall_api_test.workflows.cart_workflow import CartWorkflow


class OrderWorkflow:
    def __init__(self, portal_client, fixture: FixtureSettings, admin_client=None):
        self.portal_client = portal_client
        self.fixture = fixture
        self.cart_workflow = CartWorkflow(portal_client, fixture)
        self.order_api = OrderApi(portal_client)
        self.admin_order_api = AdminOrderApi(admin_client) if admin_client else None

    def create(self, quantity: int = 1) -> OrderContext:
        cart_entry = self.cart_workflow.add_fixture_item(quantity)
        cart_id = cart_entry["id"]
        confirm = self.order_api.generate_confirm_order([cart_id])
        assert len(confirm["cartPromotionItemList"]) == 1
        assert_confirm_amounts(confirm["calcAmount"])
        address = self._choose_address(confirm["memberReceiveAddressList"])
        result = self.order_api.generate_order([cart_id], address["id"])
        order = result["order"]
        return OrderContext(
            order_id=order["id"],
            order_sn=order["orderSn"],
            cart_id=cart_id,
            product_id=cart_entry["productId"],
            sku_id=cart_entry["productSkuId"],
            quantity=cart_entry["quantity"],
            address_id=address["id"],
            pay_amount=as_decimal(order["payAmount"]),
            cart_item=cart_entry,
            confirm=confirm,
            order=order,
        )

    def complete(self, quantity: int = 1) -> OrderContext:
        assert self.admin_order_api is not None, "Admin client is required"
        context = self.create(quantity)
        self.order_api.pay(context.order_id)
        self.admin_order_api.delivery(
            context.order_id,
            company="AUTO_EXPRESS",
            tracking_number=f"AUTO{uuid.uuid4().hex[:16]}",
        )
        self.order_api.confirm_receive(context.order_id)
        return context

    @staticmethod
    def _choose_address(addresses: list[dict]) -> dict:
        assert addresses, "No receive address found"
        return next((item for item in addresses if item.get("defaultStatus") == 1), addresses[0])

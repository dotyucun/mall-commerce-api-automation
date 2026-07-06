from mall_api_test.api.admin.admin_return_api import AdminReturnApi
from mall_api_test.api.portal.order_api import OrderApi
from mall_api_test.api.portal.return_api import ReturnApi
from mall_api_test.common.assertions import as_decimal
from mall_api_test.models import OrderContext, ReturnContext
from mall_api_test.repositories.return_repository import ReturnRepository


class ReturnWorkflow:
    def __init__(self, portal_client, admin_client, return_repository: ReturnRepository):
        self.order_api = OrderApi(portal_client)
        self.return_api = ReturnApi(portal_client)
        self.admin_return_api = AdminReturnApi(admin_client)
        self.return_repository = return_repository

    def create(self, order_context: OrderContext) -> ReturnContext:
        order = self.order_api.detail(order_context.order_id)
        payload = self.build_payload(order)
        self.return_api.create(payload)
        application = self.return_repository.latest_for_order(order_context.order_id)
        assert application is not None
        item = order["orderItemList"][0]
        return ReturnContext(
            apply_id=application["id"],
            order_id=order_context.order_id,
            order_sn=order_context.order_sn,
            return_amount=as_decimal(item["realAmount"]) * item["productQuantity"],
            application=application,
        )

    @staticmethod
    def build_payload(order: dict) -> dict:
        item = order["orderItemList"][0]
        return {
            "orderId": order["id"],
            "productId": item["productId"],
            "orderSn": order["orderSn"],
            "memberUsername": order["memberUsername"],
            "returnName": order["receiverName"],
            "returnPhone": order["receiverPhone"],
            "productPic": item["productPic"],
            "productName": item["productName"],
            "productBrand": item.get("productBrand"),
            "productAttr": item.get("productAttr"),
            "productCount": item["productQuantity"],
            "productPrice": item["productPrice"],
            "productRealPrice": item["realAmount"],
            "reason": "自动化测试退货",
            "description": "验证前后台退货状态闭环",
            "proofPics": "",
        }

    def approve(self, context: ReturnContext) -> None:
        self.admin_return_api.update_status(
            context.apply_id,
            {
                "status": 1,
                "returnAmount": float(context.return_amount),
                "companyAddressId": 1,
                "handleMan": "autotest_admin",
                "handleNote": "自动化审核通过",
            },
        )

    def complete(self, context: ReturnContext) -> None:
        self.admin_return_api.update_status(
            context.apply_id,
            {
                "status": 2,
                "receiveMan": "autotest_warehouse",
                "receiveNote": "自动化确认收货",
            },
        )

    def reject(self, context: ReturnContext) -> None:
        self.admin_return_api.update_status(
            context.apply_id,
            {
                "status": 3,
                "handleMan": "autotest_admin",
                "handleNote": "自动化拒绝退货",
            },
        )

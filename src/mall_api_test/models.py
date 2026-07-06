from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StockSnapshot:
    sku_id: int
    stock: int
    lock_stock: int


@dataclass(frozen=True)
class OrderContext:
    order_id: int
    order_sn: str
    cart_id: int
    product_id: int
    sku_id: int
    quantity: int
    address_id: int
    pay_amount: Decimal
    cart_item: dict
    confirm: dict
    order: dict


@dataclass(frozen=True)
class ReturnContext:
    apply_id: int
    order_id: int
    order_sn: str
    return_amount: Decimal
    application: dict

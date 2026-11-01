
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=20)
    selected_color: str | None = Field(default=None, max_length=40)
    selected_size: str | None = Field(default=None, max_length=30)


class OrderCreate(BaseModel):
    address_id: UUID
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)

    delivery_method: Literal["standard", "express"] = "standard"
    gift_wrap: bool = False
    delivery_notes: str = Field(default="", max_length=300)

    payment_method: str = Field(min_length=1, max_length=60)
    coupon_code: str | None = Field(default=None, max_length=60)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: str | None
    product_sku: str
    product_name: str
    image: str
    unit_price: Decimal
    quantity: int
    selected_color: str | None
    selected_size: str | None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    address_snapshot: dict
    delivery_snapshot: dict

    subtotal: Decimal
    discount: Decimal
    delivery_fee: Decimal
    gift_wrap_fee: Decimal
    cod_fee: Decimal
    gift_card_amount: Decimal
    total: Decimal

    order_status: str
    payment_status: str
    payment_method: str | None
    coupon_code: str | None

    tracking_number: str | None
    internal_note: str | None
    created_at: datetime

    items: list[OrderItemResponse]

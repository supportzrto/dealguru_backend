from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RefundReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: UUID
    order_id: UUID
    customer_name: str
    customer_email: str

    provider_payment_id: str
    amount: Decimal
    currency: str

    payment_status: str
    order_status: str
    refund_status: str
    refund_reference: str | None

    created_at: datetime


class RefundReferenceUpdate(BaseModel):
    refund_reference: str = Field(
        min_length=5,
        max_length=100,
        pattern=r"^rfnd_[A-Za-z0-9]+$",
    )


class RefundReviewResponse(BaseModel):
    payment_id: UUID
    refund_reference: str
    refund_status: Literal[
        "review_required",
        "refund_initiated",
        "refunded",
    ]
    razorpay_status: Literal[
        "pending",
        "processed",
        "failed",
    ]

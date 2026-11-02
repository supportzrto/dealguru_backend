
import uuid

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        default="razorpay",
        nullable=False,
    )

    provider_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    provider_payment_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="created",
        index=True,
        nullable=False,
    )

    method: Mapped[str | None] = mapped_column(String(40))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        back_populates="payments",
    )

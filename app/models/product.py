from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from sqlalchemy import Numeric
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    # Keep the existing frontend catalog IDs (for example "dg1") during migration.
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sku: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[list | None] = mapped_column(JSON)
    color_images: Mapped[dict | None] = mapped_column(JSON)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    colors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    badge: Mapped[str | None] = mapped_column(String(30))
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fabric: Mapped[str] = mapped_column(String(30), default="Other", nullable=False)
    occasion: Mapped[str] = mapped_column(String(30), default="Casual", nullable=False)
    set_includes: Mapped[str | None] = mapped_column(Text)
    features: Mapped[list | None] = mapped_column(JSON)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sizes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True, nullable=False
    )
    show_in_popular: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    show_in_best_sellers: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    featured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

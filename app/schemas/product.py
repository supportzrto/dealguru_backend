
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=60)

    description: str | None = None
    image: str

    images: list[str] | None = Field(default_factory=list)
    color_images: dict[str, str] | None = Field(default_factory=dict)

    price: Decimal = Field(ge=0)
    original_price: Decimal = Field(ge=0)

    rating: float = Field(default=0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)

    colors: list[str] = Field(default_factory=list)
    badge: str | None = None
    is_new: bool = False

    fabric: str = "Other"
    occasion: str = "Casual"

    set_includes: str | None = None
    features: list[str] | None = Field(default_factory=list)

    stock: int = Field(default=0, ge=0)
    sizes: list[str] = Field(default_factory=list)

    status: str = "active"

    show_in_popular: bool = False
    show_in_best_sellers: bool = False

    featured_at: datetime | None = None


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    category: str | None = None

    description: str | None = None
    image: str | None = None

    images: list[str] | None = None
    color_images: dict[str, str] | None = None

    price: Decimal | None = Field(default=None, ge=0)
    original_price: Decimal | None = Field(default=None, ge=0)

    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)

    colors: list[str] | None = None
    badge: str | None = None
    is_new: bool | None = None

    fabric: str | None = None
    occasion: str | None = None

    set_includes: str | None = None
    features: list[str] | None = None

    stock: int | None = Field(default=None, ge=0)
    sizes: list[str] | None = None

    status: str | None = None

    show_in_popular: bool | None = None
    show_in_best_sellers: bool | None = None

    featured_at: datetime | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    category: str

    description: str | None
    image: str

    images: list[str] | None
    color_images: dict[str, str] | None

    price: Decimal
    original_price: Decimal

    rating: float
    review_count: int

    colors: list[str]
    badge: str | None
    is_new: bool

    fabric: str
    occasion: str

    set_includes: str | None
    features: list[str] | None

    stock: int
    sizes: list[str]

    status: str

    show_in_popular: bool
    show_in_best_sellers: bool

    featured_at: datetime | None
    created_at: datetime

"""One-time, insert-only import of DealGuru's exported product JSON.

Run from the backend project root while the Railway SSH tunnel is active:
    python scripts/import_products.py path/to/dealguru-products-export.json

Existing product IDs are skipped. A duplicate SKU belonging to another ID aborts
without committing any rows. This script never deletes or overwrites products.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Product


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # Accept both ISO datetimes and date-only values from the frontend export.
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, datetime.min.time())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def money(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be a finite non-negative amount")
    return result.quantize(Decimal("0.01"))


def map_product(item: dict) -> dict:
    required = ("id", "sku", "name", "category", "image", "price", "originalPrice")
    missing = [key for key in required if item.get(key) in (None, "")]
    if missing:
        raise ValueError(f"Product {item.get('id', '<unknown>')} missing: {', '.join(missing)}")

    stock = int(item.get("stock", 0))
    if stock < 0:
        raise ValueError(f"Product {item['id']}: stock cannot be negative")

    return {
        "id": str(item["id"]),
        "sku": str(item["sku"]),
        "name": str(item["name"]),
        "category": str(item["category"]),
        "description": item.get("description"),
        "image": str(item["image"]),
        "images": item.get("images") or [],
        "color_images": item.get("colorImages") or {},
        "price": money(item["price"], "price"),
        "original_price": money(item["originalPrice"], "originalPrice"),
        "rating": float(item.get("rating") or 0),
        "review_count": int(item.get("reviewCount") or 0),
        "colors": item.get("colors") or [],
        "badge": item.get("badge"),
        "is_new": bool(item.get("isNew", False)),
        "fabric": item.get("fabric") or "Other",
        "occasion": item.get("occasion") or "Casual",
        "set_includes": item.get("setIncludes"),
        "features": item.get("features") or [],
        "stock": stock,
        "sizes": item.get("sizes") or [],
        "status": item.get("status") or "active",
        "show_in_popular": bool(item.get("showInPopular", False)),
        "show_in_best_sellers": bool(item.get("showInBestSellers", False)),
        "featured_at": parse_datetime(item.get("featuredAt")),
        "created_at": parse_datetime(item.get("createdAt")) or datetime.now(timezone.utc),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_products.py <export.json>")
        return 2

    source = Path(sys.argv[1])
    if not source.is_file():
        print(f"File not found: {source}")
        return 2
    
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and isinstance(payload.get("products"), list):
            items = payload["products"]
        else:
            raise ValueError("Expected a product list or an object containing a products list.")

        if not items:
            print("No products found in the export file.")
            return 1

        products = [map_product(item) for item in items]

        with SessionLocal() as db:
            existing_ids = set(
                db.scalars(
                    select(Product.id).where(
                        Product.id.in_([p["id"] for p in products])
                    )
                ).all()
            )

            new_products = [
                p for p in products if p["id"] not in existing_ids
            ]

            new_skus = [p["sku"] for p in new_products]

            if new_skus:
                conflicts = db.execute(
                    select(Product.id, Product.sku).where(
                        Product.sku.in_(new_skus)
                    )
                ).all()

                if conflicts:
                    raise ValueError(
                        f"SKU conflicts with existing products: {conflicts}"
                    )

            db.add_all([Product(**p) for p in new_products])
            db.commit()

        print(f"Import completed. Total products: {len(products)}")
        print(f"New products imported: {len(new_products)}")
        print(f"Existing product IDs skipped: {len(existing_ids)}")
        return 0

    except Exception as exc:
        print(f"Import failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

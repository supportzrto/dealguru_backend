from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product, User
from app.schemas.product import ProductCreate, ProductUpdate,ProductResponse
from app.core.dependencies import get_current_admin
from fastapi import UploadFile, File
from app.services.cloudinary_service import upload_product_image

router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[ProductResponse], include_in_schema=False)
@router.get("/", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    statement = (
        select(Product)
        .where(Product.status == "active")
        .order_by(Product.created_at.desc())
    )

    return db.scalars(statement).all()

@router.get("/admin/all", response_model=list[ProductResponse])
def get_all_products_admin(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    statement = select(Product).order_by(Product.created_at.desc())

    return db.scalars(statement).all()

@router.post("/admin/{product_id}/images")
def upload_product_image_endpoint(
    product_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Only image files are allowed",
        )

    try:
        url = upload_product_image(
            file.file,
            product_id,
            file.filename or "product-image.jpg",
        )

        return {"url": url}

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Image upload failed",
        ) from exc

    finally:
        file.file.close()

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    statement = select(Product).where(
        Product.id == product_id,
        Product.status == "active",
    )

@router.post("", response_model=ProductResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    # Check whether product ID already exists
    existing_id = db.scalar(
        select(Product).where(Product.id == product_data.id)
    )

    if existing_id:
        raise HTTPException(
            status_code=409,
            detail="Product ID already exists",
        )

    # Check whether SKU already exists
    existing_sku = db.scalar(
        select(Product).where(Product.sku == product_data.sku)
    )

    if existing_sku:
        raise HTTPException(
            status_code=409,
            detail="Product SKU already exists",
        )

    new_product = Product(**product_data.model_dump())

    try:
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        return new_product

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product ID or SKU already exists",
        )

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    product = db.scalar(
        select(Product).where(Product.id == product_id)
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    update_data = product_data.model_dump(exclude_unset=True)

    # Prevent null values for required database columns
    required_fields = {
        "sku", "name", "category", "image",
        "price", "original_price", "rating",
        "review_count", "colors", "is_new",
        "fabric", "occasion", "stock", "sizes",
        "status", "show_in_popular", "show_in_best_sellers",
    }

    for field, value in update_data.items():
        if field in required_fields and value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    # Check SKU uniqueness if SKU is being changed
    new_sku = update_data.get("sku")

    if new_sku and new_sku != product.sku:
        existing_sku = db.scalar(
            select(Product).where(Product.sku == new_sku)
        )

        if existing_sku:
            raise HTTPException(
                status_code=409,
                detail="Product SKU already exists",
            )

    try:
        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        return product

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product update conflicts with existing data",
        )

@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    product = db.scalar(
        select(Product).where(Product.id == product_id)
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }
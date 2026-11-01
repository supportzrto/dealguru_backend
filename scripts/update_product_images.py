
from pathlib import Path

from app.database import SessionLocal
from app.models import Product
from app.services.cloudinary_service import upload_product_image


IMAGE_DIR = Path(
    r"D:\dealguru project\product-images\lighter"
)

PRODUCT_ID = "dg1"

IMAGE_FILES = {
    "main": "lighter-all.jpg",
    "blue": "lighter-blue.jpg",
    "pink": "lighter-pink.jpg",
    "red": "lighter-red.jpg",
    "silver": "lighter-silver.jpg",
    "black": "lighter-black.jpg",
    "gold": "lighter-gold.jpg",
}


def main():
    # Check all local files before uploading.
    missing = [
        filename
        for filename in IMAGE_FILES.values()
        if not (IMAGE_DIR / filename).is_file()
    ]

    if missing:
        raise FileNotFoundError(
            f"Missing image files: {missing}"
        )

    # Confirm the product exists before uploading.
    with SessionLocal() as db:
        product = db.get(Product, PRODUCT_ID)

        if product is None:
            raise ValueError(
                f"Product {PRODUCT_ID} not found in database."
            )

    print("Starting Cloudinary uploads...")

    uploaded = {}

    for color, filename in IMAGE_FILES.items():
        image_path = IMAGE_DIR / filename

        print(f"Uploading: {filename}")

        url = upload_product_image(
            str(image_path),
            PRODUCT_ID,
            filename,
        )

        uploaded[color] = url
        print(f"Uploaded successfully: {url}")

    # Update the existing PostgreSQL product.
    with SessionLocal() as db:
        product = db.get(Product, PRODUCT_ID)

        if product is None:
            raise ValueError(
                f"Product {PRODUCT_ID} no longer exists."
            )

        product.image = uploaded["main"]

        product.images = list(uploaded.values())

        product.color_images = {
            color: uploaded[color]
            for color in (
                "blue",
                "pink",
                "red",
                "silver",
                "black",
                "gold",
            )
        }

        db.commit()

    print("\nImage migration completed!")
    print("Product ID:", PRODUCT_ID)
    print("Images uploaded:", len(uploaded))
    print("Database image fields updated successfully.")


if __name__ == "__main__":
    main()

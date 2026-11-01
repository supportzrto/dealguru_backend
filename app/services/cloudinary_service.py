
import cloudinary
import cloudinary.uploader

from app.config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def upload_product_image(file, product_id: str, filename: str):
    result = cloudinary.uploader.upload(
        file,
        folder=f"dealguru/products/{product_id}",
        public_id=filename.rsplit(".", 1)[0],
        overwrite=True,
        resource_type="image",
    )

    return result["secure_url"]


import cloudinary.api

from app.services.cloudinary_service import cloudinary

try:
    result = cloudinary.api.ping()
    print("Cloudinary connection successful!")
    print(result)
except Exception as error:
    print("Cloudinary connection failed:")
    print(error)

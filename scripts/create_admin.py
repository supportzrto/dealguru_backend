from getpass import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.core.security import hash_password


def main():
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()
    phone = input("Admin phone: ").strip()

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not full_name or not email or not phone:
        print("All fields are required.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    db = SessionLocal()

    try:
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            print("A user with this email already exists.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("\nAdmin account created successfully!")
        print("Email:", admin.email)
        print("Role:", admin.role)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_db,
    get_current_user,
    get_current_admin,
)
from app.core.security import verify_password, create_access_token
from app.models import User
from app.schemas.auth import LoginResponse, UserResponse
from app.config import settings
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.schemas.auth import ProfileUpdateRequest, ChangePasswordRequest
from app.core.security import hash_password
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(
    response: Response,
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == credentials.username.lower()))

    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id))

    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )

    return LoginResponse(
        access_token="",  # JWT is delivered only through the cookie
        token_type="cookie",
        user=UserResponse(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            role=user.role,
        ),
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = str(data.email).strip().lower()

    # Check whether the email already exists
    existing_user = db.scalar(select(User).where(User.email == email))

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Account already exists. Please login.",
        )

    # Create customer with Argon2 password hash
    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=data.phone.strip(),
        password_hash=hash_password(data.password),
        role="customer",
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    return RegisterResponse(
        message="Account created successfully",
        user={
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
        },
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )

    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
    }


@router.put("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = data.full_name.strip()
    current_user.phone = data.phone.strip()

    db.commit()
    db.refresh(current_user)

    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
    }


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(
        data.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(data.new_password)

    db.commit()

    return {"message": "Password changed successfully"}


@router.get("/customers", response_model=list[UserResponse])
def get_customers(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    customers = db.scalars(
        select(User).where(User.role == "customer").order_by(User.created_at.desc())
    ).all()

    return [
        {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "created_at": user.created_at,
        }
        for user in customers
    ]

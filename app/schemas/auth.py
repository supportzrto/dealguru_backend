
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: EmailStr
    phone: str
    role: str
    created_at: datetime | None = None


class LoginResponse(BaseModel):
    access_token: str = ""
    token_type: str = "cookie"
    user: UserResponse


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=10, max_length=20)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., max_length=128)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.USER


class UserRegister(BaseModel):
    email: EmailStr
    display_name: str = Field(..., max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

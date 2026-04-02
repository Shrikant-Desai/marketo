from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import bleach


# ── Auth ─────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Accepts email OR username."""

    login: str = Field(description="Email address or username")
    password: str

    model_config = {"extra": "forbid"}


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    model_config = {"extra": "forbid"}

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: str) -> str:
        cleaned = bleach.clean(v.strip(), tags=[], strip=True)
        return cleaned


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    msg: str
    id: int
    username: str
    email: str


# ── User CRUD ─────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

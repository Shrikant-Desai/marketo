# schemas/product.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal
import re, bleach

Category = Literal["electronics", "clothing", "food", "books", "home"]


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: float = Field(gt=0, le=999_999)
    stock: int = Field(ge=0)
    sku: str = Field(pattern=r"^[A-Z]{2}-\d{4}$")
    category: Category

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return bleach.clean(v.strip(), tags=[], strip=True)

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return bleach.clean(v.strip(), tags=[], strip=True)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    price: float | None = Field(default=None, gt=0, le=999_999)
    stock: int | None = Field(default=None, ge=0)
    category: Category | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    stock: int
    sku: str
    category: str
    is_active: bool
    vendor_id: int

    model_config = {"from_attributes": True}

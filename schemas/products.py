from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    price: float
    sku: str
    category: str
    description: Optional[str] = None
    stock: Optional[int] = 0

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    seller_id: int

    model_config = {"from_attributes": True}

# schemas/order.py
from pydantic import BaseModel, Field, model_validator


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def no_duplicate_products(self) -> "OrderCreate":
        ids = [item.product_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate products in order — combine quantities instead")
        return self


class OrderItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    status: str
    total: float
    items: list[OrderItemResponse]
    model_config = {"from_attributes": True}

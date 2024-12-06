from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductAddToCartRequest(BaseModel):
    product_id: int

class ProductResponse(ProductBase):
    id: int

    class Config:
        orm_mode = True

from pydantic import BaseModel

class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1
    user_email: str

class OrderResponse(BaseModel):
    id: int
    user_email: str

    class Config:
        orm_mode = True

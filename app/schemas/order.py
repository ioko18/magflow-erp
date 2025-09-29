from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Shared properties
class OrderBase(BaseModel):
    customer_id: Optional[int] = None
    order_date: Optional[datetime] = None
    status: Optional[str] = "pending"
    total_amount: Optional[float] = 0.0
    external_id: Optional[str] = None
    external_source: Optional[str] = None


# Properties to receive on order creation
class OrderCreate(OrderBase):
    customer_id: int
    order_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"
    total_amount: float = 0.0


# Properties to receive on order update
class OrderUpdate(OrderBase):
    status: Optional[str] = None


# Properties shared by models stored in DB
class OrderInDBBase(OrderBase):
    id: int
    customer_id: int
    order_date: datetime
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Properties to return to client
class Order(OrderInDBBase):
    pass


# Properties stored in DB
class OrderInDB(OrderInDBBase):
    pass


# OrderLine schemas
class OrderLineBase(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float


class OrderLineCreate(OrderLineBase):
    pass


class OrderLineUpdate(OrderLineBase):
    quantity: Optional[int] = 1
    unit_price: Optional[float] = None


class OrderLineInDBBase(OrderLineBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


class OrderLine(OrderLineInDBBase):
    pass


# Full order with order lines
class OrderWithLines(Order):
    order_lines: List[OrderLine] = []


# For creating an order with lines
class OrderCreateWithLines(OrderCreate):
    order_lines: List[OrderLineCreate] = []

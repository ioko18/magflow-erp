from datetime import datetime

from pydantic import BaseModel, Field


# Shared properties
class OrderBase(BaseModel):
    customer_id: int | None = None
    order_date: datetime | None = None
    status: str | None = "pending"
    total_amount: float | None = 0.0
    external_id: str | None = None
    external_source: str | None = None


# Properties to receive on order creation
class OrderCreate(OrderBase):
    customer_id: int
    order_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"
    total_amount: float = 0.0


# Properties to receive on order update
class OrderUpdate(OrderBase):
    status: str | None = None


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
    quantity: int | None = 1
    unit_price: float | None = None


class OrderLineInDBBase(OrderLineBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


class OrderLine(OrderLineInDBBase):
    pass


# Full order with order lines
class OrderWithLines(Order):
    order_lines: list[OrderLine] = []


# For creating an order with lines
class OrderCreateWithLines(OrderCreate):
    order_lines: list[OrderLineCreate] = []

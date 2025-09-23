"""Order model."""

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        index=True,
    )
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)

    customer: Mapped["User"] = relationship("User", back_populates="orders")
    order_lines: Mapped[List["OrderLine"]] = relationship(
        "OrderLine",
        back_populates="order",
    )


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)

    order: Mapped["Order"] = relationship("Order", back_populates="order_lines")
    product: Mapped["Product"] = relationship("Product")

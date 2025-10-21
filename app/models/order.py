"""Order model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "external_source",
            name="uq_orders_external_source",
        ),
        {"schema": "app", "extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.users.id"),
        index=True,
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    external_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    customer: Mapped["User"] = relationship("User", back_populates="orders")
    order_lines: Mapped[list["OrderLine"]] = relationship(
        "OrderLine",
        back_populates="order",
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.orders.id"),
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)

    order: Mapped["Order"] = relationship("Order", back_populates="order_lines")
    product: Mapped["Product"] = relationship("Product")

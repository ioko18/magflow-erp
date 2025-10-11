from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.order import Order, OrderLine
from app.schemas.order import OrderCreate, OrderLineCreate, OrderLineUpdate, OrderUpdate

ModelType = TypeVar("ModelType", Order, OrderLine)
CreateSchemaType = TypeVar("CreateSchemaType", OrderCreate, OrderLineCreate)
UpdateSchemaType = TypeVar("UpdateSchemaType", OrderUpdate, OrderLineUpdate)


class CRUDOrder(CRUDBase[Order, OrderCreate, OrderUpdate]):
    async def get_multi_by_customer(
        self, db: AsyncSession, *, customer_id: int, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_most_recent(self, db: AsyncSession) -> Order | None:
        result = await db.execute(
            select(self.model).order_by(self.model.order_date.desc()).limit(1)
        )
        return result.scalars().first()

    async def get_by_external_id(
        self, db: AsyncSession, *, external_id: str, external_source: str
    ) -> Order | None:
        result = await db.execute(
            select(self.model).filter(
                self.model.external_id == external_id,
                self.model.external_source == external_source,
            )
        )
        return result.scalars().first()

    async def create_with_lines(
        self, db: AsyncSession, *, obj_in: OrderCreate, lines_in: list[OrderLineCreate]
    ) -> Order:
        db_obj = self.model(
            customer_id=obj_in.customer_id,
            order_date=obj_in.order_date,
            status=obj_in.status,
            total_amount=obj_in.total_amount,
            external_id=obj_in.external_id,
            external_source=obj_in.external_source,
        )
        db.add(db_obj)
        await db.flush()

        for line_in in lines_in:
            line = OrderLine(
                order_id=db_obj.id,
                product_id=line_in.product_id,
                quantity=line_in.quantity,
                unit_price=line_in.unit_price,
            )
            db.add(line)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDOrderLine(CRUDBase[OrderLine, OrderLineCreate, OrderLineUpdate]):
    async def get_multi_by_order(
        self, db: AsyncSession, *, order_id: int, skip: int = 0, limit: int = 100
    ) -> list[OrderLine]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.order_id == order_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


order = CRUDOrder(Order)
order_line = CRUDOrderLine(OrderLine)

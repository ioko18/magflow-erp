"""Base repository class for database operations."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        self.model = model
        self.db = db_session

    async def get(self, id: Any) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        result = await self.db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
            .returning(self.model)
        )
        await self.db.commit()
        return result.scalars().first()

    async def delete(self, id: Any) -> bool:
        result = await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.commit()
        return result.rowcount > 0


async def get_repository(
    model: Type[ModelType], db_session: AsyncSession
) -> BaseRepository[ModelType]:
    return BaseRepository(model, db_session)

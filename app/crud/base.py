"""Base CRUD (Create, Read, Update, Delete) operations."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for CRUD operations.

    Args:
        model: SQLAlchemy model class

    """

    def __init__(self, model: Type[ModelType]):
        """Initialize CRUD base with model.

        Args:
            model: SQLAlchemy model class

        """
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Get a single record by ID.

        Args:
            db: Database session
            id: ID of the record to retrieve

        Returns:
            The record if found, None otherwise

        """
        result = await db.execute(select(self.model).filter(self.model.id == id))  # type: ignore
        return result.scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Get multiple records with optional pagination and filtering.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply

        Returns:
            List of records

        """
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                query = query.filter(getattr(self.model, field) == value)

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_with_relationships(
        self,
        db: AsyncSession,
        id: Any,
        relationships: List[str],
    ) -> Optional[ModelType]:
        """Get a single record with specified relationships loaded.

        Args:
            db: Database session
            id: ID of the record to retrieve
            relationships: List of relationship names to load

        Returns:
            The record with relationships if found, None otherwise

        """
        query = select(self.model).where(self.model.id == id)  # type: ignore

        # Add relationship loading
        for relationship in relationships:
            query = query.options(selectinload(getattr(self.model, relationship)))

        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi_with_relationships(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[str]] = None,
    ) -> List[ModelType]:
        """Get multiple records with optional relationships loaded.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            relationships: Optional list of relationship names to load

        Returns:
            List of records with relationships

        """
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                query = query.filter(getattr(self.model, field) == value)

        # Add relationship loading
        if relationships:
            for relationship in relationships:
                query = query.options(selectinload(getattr(self.model, relationship)))

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_multi_joined(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        join_relationships: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Get multiple records with joined relationships.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            join_relationships: Optional dict of relationship names to join conditions

        Returns:
            List of records with joined relationships

        """
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                query = query.filter(getattr(self.model, field) == value)

        # Add joins for relationships
        if join_relationships:
            for relationship, join_condition in join_relationships.items():
                relationship_attr = getattr(self.model, relationship)
                query = query.join(relationship_attr, join_condition)

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record.

        Args:
            db: Database session
            obj_in: Pydantic model with data to create

        Returns:
            The created record

        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """Update an existing record.

        Args:
            db: Database session
            db_obj: Database model instance to update
            obj_in: Pydantic model or dict with data to update

        Returns:
            The updated record

        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)  # type: ignore

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Delete a record by ID.

        Args:
            db: Database session
            id: ID of the record to delete

        Returns:
            The deleted record if found, None otherwise

        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def exists(self, db: AsyncSession, id: Any) -> bool:
        """Check if a record exists by ID.

        Args:
            db: Database session
            id: ID of the record to check

        Returns:
            True if record exists, False otherwise

        """
        obj = await self.get(db, id)
        return obj is not None

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records with optional filtering.

        Args:
            db: Database session
            filters: Optional filters to apply

        Returns:
            Number of matching records

        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                query = query.filter(getattr(self.model, field) == value)

        result = await db.execute(query)
        return result.scalar() or 0

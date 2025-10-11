from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import DeclarativeBase, declared_attr

ModelType = TypeVar("ModelType", bound="Base")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Provides common columns and helper methods while ensuring a single
    metadata registry backed by SQLAlchemy's DeclarativeBase.
    """

    @declared_attr
    def __tablename__(self) -> str:
        """Automatically generate snake_case table names."""

        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in self.__name__]
        ).lstrip("_")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to a dictionary."""

        columns = self.__table__.columns.keys()
        result: dict[str, Any] = {}
        for column in columns:
            if column.startswith("_"):
                continue
            value = getattr(self, column)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column] = value
        return result

    @classmethod
    def from_dict(cls: type[ModelType], data: dict[str, Any]) -> ModelType:
        """Create a model instance from a dictionary."""

        columns = cls.__table__.columns.keys()
        filtered_data = {k: v for k, v in data.items() if k in columns}
        return cls(**filtered_data)

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update fields on the model instance from a dictionary."""

        for key, value in data.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)

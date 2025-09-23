"""Base model definitions for SQLAlchemy."""

from datetime import datetime
from typing import Any, Dict, Type, TypeVar

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import as_declarative, declared_attr

# Create a generic type variable for type hints
ModelType = TypeVar("ModelType", bound="Base")


@as_declarative()
class Base:
    """Base class for all SQLAlchemy models.

    Provides common columns and methods for all models.
    """

    # Automatically generate __tablename__ from class name
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically.

        Converts CamelCase class name to snake_case table name.
        """
        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in cls.__name__],
        ).lstrip("_")

    # Common columns
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to a dictionary.

        Returns:
            Dict containing the model's data.

        """
        # Get all columns
        columns = self.__table__.columns.keys()

        # Convert to dictionary
        result = {}
        for column in columns:
            # Skip private attributes
            if column.startswith("_"):
                continue

            value = getattr(self, column)

            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()

            result[column] = value

        return result

    @classmethod
    def from_dict(cls: Type[ModelType], data: Dict[str, Any]) -> ModelType:
        """Create a model instance from a dictionary.

        Args:
            data: Dictionary containing model data.

        Returns:
            A new model instance.

        """
        # Filter out keys that don't correspond to model columns
        columns = cls.__table__.columns.keys()
        filtered_data = {k: v for k, v in data.items() if k in columns}

        return cls(**filtered_data)

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from a dictionary.

        Args:
            data: Dictionary containing fields to update.

        """
        for key, value in data.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)

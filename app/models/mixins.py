"""SQLAlchemy model mixins for common fields and functionality."""
from datetime import datetime

from sqlalchemy import Column, DateTime, func


class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality to models."""
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Mark the record as soft deleted."""
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None

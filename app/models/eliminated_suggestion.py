"""Eliminated Suggestion Model

This model tracks product suggestions that have been manually eliminated by users.
When a user removes a suggestion, it's recorded here to prevent it from reappearing
in future automatic matching suggestions.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base


class EliminatedSuggestion(Base):
    """
    Tracks manually eliminated product match suggestions.

    When a user determines that an automatic suggestion is incorrect,
    they can eliminate it. This record ensures the suggestion won't
    reappear in future matching operations.

    Attributes:
        id: Primary key
        supplier_product_id: ID of the supplier product
        local_product_id: ID of the local product that was suggested
        eliminated_at: Timestamp when the suggestion was eliminated
        eliminated_by: ID of the user who eliminated the suggestion
        reason: Optional reason for elimination
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    __tablename__ = "eliminated_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    supplier_product_id = Column(
        Integer,
        ForeignKey("supplier_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    local_product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    eliminated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    eliminated_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    # Note: Relationships removed to avoid circular dependency issues
    # Use foreign keys directly or query via session when needed

    # Unique constraint to prevent duplicate eliminations
    __table_args__ = (
        UniqueConstraint(
            'supplier_product_id',
            'local_product_id',
            name='uq_eliminated_suggestions_supplier_local'
        ),
    )

    def __repr__(self):
        return (
            f"<EliminatedSuggestion("
            f"id={self.id}, "
            f"supplier_product_id={self.supplier_product_id}, "
            f"local_product_id={self.local_product_id}, "
            f"eliminated_at={self.eliminated_at}"
            f")>"
        )

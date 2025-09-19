from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, Field, validator
from pydantic.generics import GenericModel
import base64
import json

T = TypeVar("T")


class CursorParams(BaseModel):
    """Cursor-based pagination parameters."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
    )
    after: Optional[str] = Field(
        default=None,
        description="Cursor for pagination (base64-encoded JSON with 'created_at' and 'id')",
    )

    @validator("after")
    def validate_cursor(cls, v):
        if v is None:
            return None
        try:
            cursor_data = json.loads(base64.b64decode(v.encode()).decode())
            if not all(k in cursor_data for k in ("created_at", "id")):
                raise ValueError("Invalid cursor format")
            return cursor_data
        except Exception as e:
            raise ValueError(f"Invalid cursor: {str(e)}")


class CursorPagination(GenericModel, Generic[T]):
    """Cursor-based pagination response model."""

    items: List[T]
    next_cursor: Optional[str] = Field(
        None,
        description="Base64-encoded cursor for the next page, or None if this is the last page",
    )
    has_more: bool = Field(..., description="Whether there are more items available")

    @classmethod
    def from_results(
        cls,
        items: List[T],
        limit: int,
        cursor_field: str = "created_at",
        cursor_id_field: str = "id",
    ) -> "CursorPagination[T]":
        """Create a pagination response from a list of results.

        Args:
            items: List of items for the current page
            limit: Requested page size
            cursor_field: Field to use for cursor (default: 'created_at')
            cursor_id_field: Field to use as tiebreaker (default: 'id')

        Returns:
            CursorPagination instance with next cursor if there are more items
        """
        has_more = len(items) > limit
        items = items[:limit]  # Remove the extra item we fetched to check for more

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_data = {
                cursor_field: (
                    last_item[cursor_field].isoformat()
                    if hasattr(last_item[cursor_field], "isoformat")
                    else last_item[cursor_field]
                ),
                cursor_id_field: last_item[cursor_id_field],
            }
            next_cursor = base64.b64encode(
                json.dumps(cursor_data, sort_keys=True).encode()
            ).decode()

        return cls(items=items, next_cursor=next_cursor, has_more=has_more)


def decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    """Decode a base64-encoded cursor to its original data.

    Args:
        cursor: Base64-encoded cursor string or None

    Returns:
        Decoded cursor data as dict, or None if cursor is None
    """
    if not cursor:
        return None
    try:
        return json.loads(base64.b64decode(cursor.encode()).decode())
    except Exception:
        raise ValueError("Invalid cursor format")

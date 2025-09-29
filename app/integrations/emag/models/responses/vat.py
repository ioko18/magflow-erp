"""Response models for VAT-related endpoints in the eMAG Marketplace API.

This module contains Pydantic models for handling VAT rate information
returned by the eMAG API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.utils.datetime_utils import get_utc_now
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    confloat,
    field_serializer,
    field_validator,
)


class VatRate(BaseModel):
    """Model representing a VAT rate in the eMAG Marketplace.

    Attributes:
        id: Unique identifier for the VAT rate in eMAG's system
        name: Display name of the VAT rate (e.g., "TVA 19%")
        value: VAT rate as a percentage (e.g., 19.0 for 19%)
        is_default: Indicates if this is the default VAT rate
        valid_from: Optional start date when this rate becomes effective
        valid_until: Optional end date when this rate expires
        country_code: ISO 3166-1 alpha-2 country code
        is_active: Whether this VAT rate is currently active

    """

    id: int = Field(
        ...,
        ge=1,
        description="Unique identifier for the VAT rate in eMAG's system",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name of the VAT rate (e.g., 'TVA 19%')",
    )
    value: confloat(ge=0, le=100) = Field(
        ...,
        description="VAT rate as a percentage (e.g., 19.0 for 19%)",
    )
    is_default: bool = Field(
        False,
        alias="isDefault",
        description="Indicates if this is the default VAT rate for the country",
    )
    valid_from: Optional[datetime] = Field(
        None,
        alias="validFrom",
        description="Date and time when this VAT rate becomes effective",
    )
    valid_until: Optional[datetime] = Field(
        None,
        alias="validUntil",
        description="Date and time when this VAT rate expires",
    )
    country_code: str = Field(
        "RO",
        min_length=2,
        max_length=2,
        alias="countryCode",
        description="ISO 3166-1 alpha-2 country code (e.g., 'RO' for Romania)",
    )
    is_active: bool = Field(
        True,
        alias="isActive",
        description="Whether this VAT rate is currently active",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("valid_from", "valid_until", when_used="json")
    def serialize_optional_datetime(
        self, value: Optional[datetime], _info
    ) -> Optional[str]:
        return value.isoformat() if value else None

    @field_validator("country_code")
    def validate_country_code(cls, v):
        """Validate country code is uppercase and valid."""
        if not v or len(v) != 2 or not v.isalpha():
            raise ValueError("Country code must be a 2-letter ISO code")
        return v.upper()

    @field_validator("name")
    def validate_name(cls, v):
        """Strip whitespace from name and ensure it's not empty."""
        v = v.strip()
        if not v:
            raise ValueError("VAT rate name cannot be empty")
        return v


class VatResponse(BaseModel):
    """Standard response model for VAT-related API endpoints with cursor-based pagination.

    Follows eMAG's standard response format with additional metadata and pagination support.
    """

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if the request resulted in an error",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages, warnings, or errors related to the request",
    )
    results: List[VatRate] = Field(
        default_factory=list,
        description="List of VAT rates returned by the API",
    )
    timestamp: datetime = Field(
        default_factory=get_utc_now,
        description="Server timestamp when the response was generated, in UTC timezone",
    )
    next_cursor: Optional[str] = Field(
        None,
        alias="nextCursor",
        description="Cursor for the next page of results, if available",
    )
    prev_cursor: Optional[str] = Field(
        None,
        alias="prevCursor",
        description="Cursor for the previous page of results, if available",
    )
    total_count: Optional[int] = Field(
        None,
        alias="totalCount",
        description="Total number of results available, if known",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("timestamp", when_used="json")
    def serialize_timestamp(self, value: datetime, _info) -> str:
        return value.isoformat()

    @classmethod
    def from_emag_response(
        cls,
        data: Dict[str, Any],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> "VatResponse":
        """Create a VatResponse from eMAG API response data with pagination support.

        Args:
            data: Raw response data from eMAG API
            cursor: Optional cursor for pagination
            limit: Optional limit for the number of results per page

        Returns:
            VatResponse: Parsed response object with pagination metadata

        """
        response = cls.model_validate(data)

        # If we have a cursor and results, generate next cursor for pagination
        if cursor and response.results:
            response.prev_cursor = cursor

            # Generate next cursor if there are more results
            if limit and len(response.results) >= limit:
                last_item = response.results[-1]
                response.next_cursor = f"vat_{last_item.id}"

        return response

    def get_default_rate(self) -> Optional[VatRate]:
        """Get the default VAT rate from the results.

        Returns:
            Optional[VatRate]: The default VAT rate if found, None otherwise

        """
        for rate in self.results:
            if rate.is_default:
                return rate
        return None

    def has_next_page(self) -> bool:
        """Check if there are more results available.

        Returns:
            bool: True if there are more results, False otherwise

        """
        return self.next_cursor is not None

    def get_pagination_links(self, base_url: str) -> Dict[str, Optional[str]]:
        """Generate pagination links for the response.

        Args:
            base_url: The base URL for the request (without query parameters)

        Returns:
            Dict[str, Optional[str]]: Dictionary with 'next' and 'prev' links

        """
        links = {"next": None, "prev": None}

        if self.next_cursor:
            links["next"] = f"{base_url}?cursor={self.next_cursor}"

        if self.prev_cursor:
            links["prev"] = f"{base_url}?cursor={self.prev_cursor}"

        return links

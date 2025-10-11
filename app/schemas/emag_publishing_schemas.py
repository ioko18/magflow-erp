"""
eMAG Product Publishing Schemas - API v4.4.9

Pydantic schemas for product publishing with support for:
- Size tags (breaking change in v4.4.9)
- GPSR compliance fields
- Enhanced characteristics
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CharacteristicValue(BaseModel):
    """
    Characteristic value with optional tag support (v4.4.9).

    Tags are used for size characteristics:
    - "original": Original size value (e.g., "36 EU")
    - "converted": Converted size value (e.g., "39 intl")
    """

    id: int = Field(..., description="Characteristic ID")
    value: str = Field(..., description="Characteristic value")
    tag: str | None = Field(
        None, description="Tag for size characteristics: 'original' or 'converted'"
    )

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, v):
        """Validate tag values."""
        if v is not None and v not in ["original", "converted"]:
            raise ValueError("Tag must be 'original' or 'converted'")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"id": 6506, "tag": "original", "value": "36 EU"},
                {"id": 6506, "tag": "converted", "value": "39 intl"},
                {"id": 100, "value": "Black"},
            ]
        }
    )


class ImageData(BaseModel):
    """Product image data."""

    display_type: int = Field(..., description="Display type (1=main, 2=additional)")
    url: str = Field(..., description="Image URL")
    overwrite: bool | None = Field(False, description="Overwrite existing image")
    force_download: bool | None = Field(False, description="Force download from URL")


class StockData(BaseModel):
    """Stock information per warehouse."""

    warehouse_id: int = Field(..., description="Warehouse ID")
    value: int = Field(..., ge=0, description="Stock quantity")


class HandlingTimeData(BaseModel):
    """Handling time per warehouse."""

    warehouse_id: int = Field(..., description="Warehouse ID")
    value: int = Field(..., ge=0, le=30, description="Handling time in days (0-30)")


class GPSRManufacturer(BaseModel):
    """
    GPSR Manufacturer information (EU compliance).

    Required for products sold in EU from 2024.
    """

    name: str = Field(..., description="Manufacturer name")
    address: str = Field(..., description="Manufacturer address")
    email: str | None = Field(None, description="Contact email")
    phone: str | None = Field(None, description="Contact phone")


class GPSREURepresentative(BaseModel):
    """
    GPSR EU Representative information (EU compliance).

    Required for non-EU manufacturers selling in EU.
    """

    name: str = Field(..., description="EU representative name")
    address: str = Field(..., description="EU representative address")
    email: str | None = Field(None, description="Contact email")
    phone: str | None = Field(None, description="Contact phone")


class DraftProductCreate(BaseModel):
    """
    Schema for creating a draft product (minimal fields).

    Draft products are not sent to eMAG validation until complete.
    """

    product_id: int = Field(..., description="Seller internal product ID")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    brand: str = Field(..., min_length=1, max_length=100, description="Brand name")
    part_number: str = Field(
        ..., min_length=1, max_length=100, description="Manufacturer part number"
    )
    category_id: int | None = Field(None, description="eMAG category ID")
    ean: list[str] | None = Field(None, description="List of EAN codes")
    source_language: str | None = Field(None, description="Source language code")


class CompleteProductCreate(BaseModel):
    """
    Schema for creating a complete product with full documentation.

    Includes GPSR compliance fields and size tag support.
    """

    product_id: int = Field(..., description="Seller internal product ID")
    category_id: int = Field(..., description="eMAG category ID")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    part_number: str = Field(
        ..., min_length=1, max_length=100, description="Manufacturer part number"
    )
    brand: str = Field(..., min_length=1, max_length=100, description="Brand name")
    description: str = Field(
        ..., min_length=10, description="Product description (HTML allowed)"
    )

    # Images
    images: list[ImageData] = Field(
        ..., min_items=1, description="Product images (at least 1 required)"
    )

    # Characteristics with tag support
    characteristics: list[CharacteristicValue] = Field(
        ..., description="Product characteristics"
    )

    # Offer data
    sale_price: float = Field(..., gt=0, description="Sale price")
    vat_id: int = Field(..., description="VAT rate ID")
    stock: list[StockData] = Field(..., min_items=1, description="Stock per warehouse")
    handling_time: list[HandlingTimeData] = Field(
        ..., min_items=1, description="Handling time per warehouse"
    )

    # Optional fields
    ean: list[str] | None = Field(None, description="List of EAN codes")
    warranty: int | None = Field(None, ge=0, description="Warranty in months")
    source_language: str | None = Field(None, description="Source language code")

    # GPSR Compliance (EU requirement from 2024)
    manufacturer: GPSRManufacturer | None = Field(
        None, description="Manufacturer information (GPSR)"
    )
    eu_representative: GPSREURepresentative | None = Field(
        None, description="EU representative (GPSR)"
    )
    safety_information: str | None = Field(
        None, description="Safety information (GPSR)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": 12345,
                "category_id": 506,
                "name": "Example Product",
                "part_number": "EX-12345",
                "brand": "Example Brand",
                "description": "<p>Product description</p>",
                "images": [{"display_type": 1, "url": "https://example.com/image.jpg"}],
                "characteristics": [
                    {"id": 6506, "tag": "original", "value": "36 EU"},
                    {"id": 6506, "tag": "converted", "value": "39 intl"},
                    {"id": 100, "value": "Black"},
                ],
                "sale_price": 199.99,
                "vat_id": 1,
                "stock": [{"warehouse_id": 1, "value": 50}],
                "handling_time": [{"warehouse_id": 1, "value": 1}],
                "ean": ["5941234567890"],
                "warranty": 24,
                "manufacturer": {
                    "name": "Example Manufacturer",
                    "address": "123 Main St, City, Country",
                    "email": "contact@manufacturer.com",
                },
            }
        }
    )


class AttachOfferCreate(BaseModel):
    """Schema for attaching an offer to an existing product."""

    product_id: int = Field(..., description="Seller internal product ID")
    part_number_key: str | None = Field(None, description="eMAG part number key")
    ean: list[str] | None = Field(None, description="List of EAN codes")
    sale_price: float = Field(..., gt=0, description="Sale price")
    vat_id: int = Field(..., description="VAT rate ID")
    stock: list[StockData] = Field(..., min_items=1, description="Stock per warehouse")
    handling_time: list[HandlingTimeData] = Field(
        ..., min_items=1, description="Handling time per warehouse"
    )
    warranty: int | None = Field(None, ge=0, description="Warranty in months")

    # GPSR Compliance
    manufacturer: GPSRManufacturer | None = Field(
        None, description="Manufacturer information (GPSR)"
    )
    eu_representative: GPSREURepresentative | None = Field(
        None, description="EU representative (GPSR)"
    )

    # Note: Cross-field validation moved to model_validator in Pydantic v2
    # For now, both fields are optional and validation happens at service level


class BatchProductUpdate(BaseModel):
    """
    Schema for batch product updates.

    Optimized for updating multiple products efficiently.
    """

    products: list[dict[str, Any]] = Field(
        ..., max_items=100, description="List of products to update (max 100)"
    )

    @field_validator("products")
    @classmethod
    def validate_batch_size(cls, v):
        """Validate batch size for optimal performance."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 products")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "products": [
                    {
                        "id": 12345,
                        "sale_price": 199.99,
                        "stock": [{"warehouse_id": 1, "value": 50}],
                    },
                    {
                        "id": 12346,
                        "sale_price": 299.99,
                        "stock": [{"warehouse_id": 1, "value": 30}],
                    },
                ]
            }
        }
    )


class PublishingResponse(BaseModel):
    """Standard response for publishing operations."""

    status: str = Field(..., description="Operation status")
    message: str | None = Field(None, description="Status message")
    data: dict[str, Any] | None = Field(None, description="Response data")
    errors: list[str] | None = Field(None, description="Error messages if any")

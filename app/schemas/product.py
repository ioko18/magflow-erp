from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class CategorySummary(BaseModel):
    id: int = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    """Base product schema with common fields."""

    # Basic Information
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    sku: str = Field(
        ..., min_length=1, max_length=100, description="Stock Keeping Unit (unique)"
    )
    description: str | None = Field(None, description="Product description")
    short_description: str | None = Field(
        None, max_length=500, description="Short product description"
    )
    brand: str | None = Field(None, max_length=100, description="Product brand")
    manufacturer: str | None = Field(
        None, max_length=100, description="Product manufacturer"
    )

    # Pricing
    base_price: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Recommended retail price",
    )
    currency: str | None = Field(
        default="RON",
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )

    # Physical Properties
    weight_kg: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product weight in kilograms",
    )
    length_cm: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product length in centimeters",
    )
    width_cm: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product width in centimeters",
    )
    height_cm: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product height in centimeters",
    )

    # Status
    is_active: bool | None = Field(True, description="Whether the product is active")
    is_discontinued: bool | None = Field(
        False, description="Whether the product is discontinued"
    )

    # eMAG Specific Fields
    ean: str | None = Field(
        None, max_length=18, description="European Article Number"
    )
    emag_category_id: int | None = Field(None, description="eMAG category ID")
    emag_brand_id: int | None = Field(None, description="eMAG brand ID")
    emag_warranty_months: int | None = Field(
        None,
        ge=0,
        le=240,
        description="Warranty period in months",
    )
    emag_part_number_key: str | None = Field(
        None,
        max_length=50,
        description="eMAG unique product identifier",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str:
        """Validate currency code."""
        if v is None:
            return "RON"
        return v.upper()

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        """Validate SKU format."""
        if not v or not v.strip():
            raise ValueError("SKU cannot be empty")
        # Allow alphanumeric, hyphens, and underscores
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(
                "SKU can only contain alphanumeric characters, hyphens, and underscores"
            )
        return v.strip().upper()


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    category_ids: list[int] = Field(
        default_factory=list,
        description="Categories to attach to the product",
    )
    characteristics: dict[str, Any] | None = Field(
        default=None,
        description="Structured product characteristics (key-value pairs)",
    )
    images: list[str] | None = Field(
        default_factory=list,
        description="Product image URLs",
    )
    attachments: list[str] | None = Field(
        default_factory=list,
        description="Product attachment URLs (manuals, certificates, etc.)",
    )

    # Auto-publish to eMAG option
    auto_publish_emag: bool | None = Field(
        default=False,
        description="Automatically publish to eMAG after creation",
    )

    @model_validator(mode="after")
    def validate_emag_fields(self) -> ProductCreate:
        """Validate eMAG-specific fields if auto-publish is enabled."""
        if self.auto_publish_emag:
            if not self.emag_category_id:
                raise ValueError("eMAG category ID is required for auto-publish")
            if not self.base_price or self.base_price <= 0:
                raise ValueError("Valid base price is required for auto-publish")
            if not self.description or len(self.description.strip()) < 10:
                raise ValueError(
                    "Description (min 10 chars) is required for auto-publish"
                )
        return self


class ProductUpdate(BaseModel):
    """Schema for updating an existing product."""

    # Basic Information
    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Product name",
    )
    sku: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Stock Keeping Unit",
    )
    description: str | None = Field(None, description="Product description")
    short_description: str | None = Field(
        None, max_length=500, description="Short product description"
    )
    brand: str | None = Field(None, max_length=100, description="Product brand")
    manufacturer: str | None = Field(
        None, max_length=100, description="Product manufacturer"
    )

    # Pricing
    base_price: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Decimal | None = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Recommended retail price",
    )
    currency: str | None = Field(
        None,
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )

    # Physical Properties
    weight_kg: Decimal | None = Field(
        None, ge=Decimal(0), description="Product weight in kilograms"
    )
    length_cm: Decimal | None = Field(
        None, ge=Decimal(0), description="Product length in centimeters"
    )
    width_cm: Decimal | None = Field(
        None, ge=Decimal(0), description="Product width in centimeters"
    )
    height_cm: Decimal | None = Field(
        None, ge=Decimal(0), description="Product height in centimeters"
    )

    # Status
    is_active: bool | None = Field(None, description="Whether the product is active")
    is_discontinued: bool | None = Field(
        None, description="Whether the product is discontinued"
    )

    # eMAG Specific
    ean: str | None = Field(
        None, max_length=18, description="European Article Number"
    )
    emag_category_id: int | None = Field(None, description="eMAG category ID")
    emag_brand_id: int | None = Field(None, description="eMAG brand ID")
    emag_warranty_months: int | None = Field(
        None, ge=0, le=240, description="Warranty period in months"
    )

    # Metadata
    category_ids: list[int] | None = Field(
        None, description="Categories to attach to the product"
    )
    characteristics: dict[str, Any] | None = Field(
        None, description="Product characteristics"
    )
    images: list[str] | None = Field(None, description="Product image URLs")
    attachments: list[str] | None = Field(
        None, description="Product attachment URLs"
    )

    # Sync to eMAG option
    sync_to_emag: bool | None = Field(
        default=False,
        description="Sync changes to eMAG after update",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Validate currency code."""
        if v is not None:
            return v.upper()
        return v

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str | None) -> str | None:
        """Validate SKU format."""
        if v is not None:
            if not v.strip():
                raise ValueError("SKU cannot be empty")
            if not all(c.isalnum() or c in "-_" for c in v):
                raise ValueError(
                    "SKU can only contain alphanumeric characters, hyphens, and underscores"
                )
            return v.strip().upper()
        return v


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: int
    name: str
    sku: str
    description: str | None = None
    short_description: str | None = None
    brand: str | None = None
    manufacturer: str | None = None

    # Pricing
    base_price: Decimal | None = Field(
        default=None,
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Decimal | None = None
    currency: str | None = Field(default="RON", description="ISO currency code")

    # Physical Properties
    weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None

    # Status
    is_active: bool = Field(..., description="Whether the product is active")
    is_discontinued: bool = Field(
        default=False, description="Whether the product is discontinued"
    )

    # eMAG Fields
    ean: str | None = None
    emag_category_id: int | None = None
    emag_brand_id: int | None = None
    emag_warranty_months: int | None = None
    emag_part_number_key: str | None = None

    # Metadata
    characteristics: dict[str, Any] | None = None
    images: list[str] | None = None
    attachments: list[str] | None = None

    # Relationships
    categories: list[CategorySummary] = Field(
        default_factory=list,
        description="Associated categories",
    )

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""

    products: list[ProductResponse]
    total: int
    limit: int
    offset: int


class ProductBulkCreate(BaseModel):
    """Schema for bulk product creation."""

    products: list[ProductCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of products to create (max 100)",
    )


class ProductBulkCreateResponse(BaseModel):
    """Schema for bulk product creation response."""

    created: list[ProductResponse] = Field(
        default_factory=list, description="Successfully created products"
    )
    failed: list[dict[str, Any]] = Field(
        default_factory=list, description="Failed products with error messages"
    )
    total_created: int = Field(
        default=0, description="Total number of products created"
    )
    total_failed: int = Field(
        default=0, description="Total number of products that failed"
    )


class ProductValidationResult(BaseModel):
    """Schema for product validation result."""

    is_valid: bool = Field(..., description="Whether the product is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    emag_ready: bool = Field(
        default=False, description="Whether the product is ready for eMAG"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Missing required fields for eMAG"
    )

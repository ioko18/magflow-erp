"""Response models for product offer operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer


class ProductOfferStatus(str, Enum):
    """Status of a product offer in eMAG's system."""

    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    REJECTED = "rejected"
    DELETED = "deleted"


class ProductOfferPrice(BaseModel):
    """Price information for a product offer."""

    current: float = Field(..., description="Current price")
    initial: float = Field(..., description="Initial/regular price")
    currency: str = Field(default="RON", description="Currency code (e.g., RON, EUR)")
    vat_rate: float = Field(..., description="VAT rate as a percentage (e.g., 19.0)")
    vat_amount: float = Field(..., description="VAT amount")
    model_config = ConfigDict()

    @field_serializer("current", "initial", "vat_rate", "vat_amount", when_used="json")
    def serialize_money(self, value: float, _info) -> float:
        return round(value, 2)


class ProductOfferStock(BaseModel):
    """Stock information for a product offer."""

    available_quantity: int = Field(
        ...,
        ge=0,
        description="Available quantity in stock",
    )
    initial_quantity: int = Field(..., ge=0, description="Initial quantity in stock")
    reserved_quantity: int = Field(..., ge=0, description="Reserved quantity")
    sold_quantity: int = Field(..., ge=0, description="Sold quantity")


class ProductOfferImage(BaseModel):
    """Image information for a product offer."""

    url: str = Field(..., description="Image URL")
    is_main: bool = Field(default=False, description="Whether this is the main image")
    position: int = Field(..., ge=0, description="Image position in the gallery")


class ProductOfferCharacteristic(BaseModel):
    """Characteristic information for a product offer."""

    id: int = Field(..., description="Characteristic ID")
    name: str = Field(..., description="Characteristic name")
    value: str = Field(..., description="Characteristic value")
    group_name: Optional[str] = Field(None, description="Characteristic group name")


class ProductOfferResponse(BaseModel):
    """Response model for a single product offer."""

    id: int = Field(..., description="eMAG offer ID")
    product_id: str = Field(..., description="Your product ID")
    emag_id: int = Field(..., description="eMAG product ID")
    part_number: Optional[str] = Field(None, description="Manufacturer part number")
    name: str = Field(..., description="Product name")
    category_id: int = Field(..., description="eMAG category ID")
    brand_id: int = Field(..., description="eMAG brand ID")
    brand_name: str = Field(..., description="Brand name")
    price: ProductOfferPrice = Field(..., description="Price information")
    stock: ProductOfferStock = Field(..., description="Stock information")
    status: ProductOfferStatus = Field(..., description="Offer status")
    images: List[ProductOfferImage] = Field(
        default_factory=list,
        description="Product images",
    )
    characteristics: List[ProductOfferCharacteristic] = Field(
        default_factory=list,
        description="Product characteristics",
    )
    url: Optional[HttpUrl] = Field(None, description="Product URL on eMAG marketplace")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.isoformat()


class ProductOfferListResponse(BaseModel):
    """Response model for listing product offers."""

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if there was an error",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages",
    )
    results: List[ProductOfferResponse] = Field(
        default_factory=list,
        description="List of product offers",
    )
    current_page: int = Field(1, alias="currentPage", description="Current page number")
    items_per_page: int = Field(
        50,
        alias="itemsPerPage",
        description="Number of items per page",
    )
    total_items: int = Field(0, alias="totalItems", description="Total number of items")
    total_pages: int = Field(1, alias="totalPages", description="Total number of pages")

    model_config = ConfigDict(allow_population_by_field_name=True)


class ProductOfferBulkResponseItem(BaseModel):
    """Response item for bulk operations."""

    product_id: str = Field(..., description="Your product ID")
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Operation message")
    emag_id: Optional[int] = Field(None, description="eMAG product ID if created")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors if any",
    )


class ProductOfferBulkResponse(BaseModel):
    """Response model for bulk operations on product offers."""

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if there was an error",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages",
    )
    results: List[ProductOfferBulkResponseItem] = Field(
        default_factory=list,
        description="Results of bulk operation",
    )

    model_config = ConfigDict(allow_population_by_field_name=True)


class ProductOfferSyncStatus(str, Enum):
    """Synchronization status of a product offer."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductOfferSyncResponse(BaseModel):
    """Response model for offer synchronization status."""

    sync_id: str = Field(..., description="Synchronization ID")
    status: ProductOfferSyncStatus = Field(..., description="Synchronization status")
    processed_items: int = Field(0, description="Number of processed items")
    total_items: int = Field(0, description="Total number of items to process")
    started_at: datetime = Field(..., description="Synchronization start time")
    completed_at: Optional[datetime] = Field(
        None,
        description="Synchronization completion time",
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors if any",
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_optional_datetime(
        self, value: Optional[datetime], _info
    ) -> Optional[str]:
        return value.isoformat() if value else None

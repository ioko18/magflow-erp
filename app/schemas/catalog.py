"""Data transfer objects for the Catalog service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"
    PRICE = "price"


class CategoryBase(BaseModel):
    """Base category DTO."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=150,
        pattern=r"^[a-z0-9-]+$",
    )
    parent_id: Optional[int] = Field(None, alias="parentId")
    is_active: bool = Field(default=True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class CategoryCreate(CategoryBase):
    """DTO for creating a category."""


class Category(CategoryBase):
    """Category DTO with identifiers."""

    id: int
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class Cursor(BaseModel):
    """Cursor for keyset pagination."""

    value: str
    has_more: bool = Field(..., alias="hasMore")

    model_config = ConfigDict(populate_by_name=True)


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total_items: int = Field(..., alias="totalItems", ge=0)
    total_pages: int = Field(..., alias="totalPages", ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., alias="perPage", ge=1, le=100)
    has_next: bool = Field(..., alias="hasNext")
    has_prev: bool = Field(..., alias="hasPrev")
    next_cursor: Optional[str] = Field(None, alias="nextCursor")
    prev_cursor: Optional[str] = Field(None, alias="prevCursor")

    model_config = ConfigDict(populate_by_name=True)


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ProductImage(BaseModel):
    """Product image DTO."""

    url: HttpUrl
    is_main: bool = Field(default=False, alias="isMain")
    position: int = 0
    alt: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ProductCharacteristicValue(BaseModel):
    """Product characteristic value DTO."""

    id: int
    name: str
    value: Union[str, int, float, bool]
    unit: Optional[str] = None


class ProductBase(BaseModel):
    """Base product DTO."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sku: str = Field(..., min_length=1, max_length=100)
    ean: Optional[str] = Field(None, min_length=8, max_length=13)
    price: float = Field(..., gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    currency: str = Field(default="RON", min_length=3, max_length=3)
    status: ProductStatus = ProductStatus.DRAFT
    is_active: bool = Field(default=True, alias="isActive")
    stock_quantity: int = Field(default=0, ge=0, alias="stockQuantity")
    weight: Optional[float] = Field(None, gt=0)  # in kg
    length: Optional[float] = Field(None, gt=0)  # in cm
    width: Optional[float] = Field(None, gt=0)  # in cm
    height: Optional[float] = Field(None, gt=0)  # in cm
    brand_id: Optional[int] = Field(None, alias="brandId")
    category_id: int = Field(..., alias="categoryId")
    images: List[ProductImage] = []
    characteristics: List[ProductCharacteristicValue] = []
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(populate_by_name=True)


class ProductCreate(ProductBase):
    """DTO for creating a new product."""


class ProductUpdate(BaseModel):
    """DTO for updating an existing product."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    ean: Optional[str] = Field(None, min_length=8, max_length=13)
    price: Optional[float] = Field(None, gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[ProductStatus] = None
    is_active: Optional[bool] = Field(None, alias="isActive")
    stock_quantity: Optional[int] = Field(None, ge=0, alias="stockQuantity")
    weight: Optional[float] = Field(None, gt=0)
    length: Optional[float] = Field(None, gt=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    brand_id: Optional[int] = Field(None, alias="brandId")
    category_id: Optional[int] = Field(None, alias="categoryId")
    images: Optional[List[ProductImage]] = None
    characteristics: Optional[List[ProductCharacteristicValue]] = None
    metadata: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(populate_by_name=True)


class Product(ProductBase):
    """Product DTO with read-only fields."""

    id: UUID
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    emag_id: Optional[int] = Field(None, alias="emagId")
    url: Optional[HttpUrl] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProductListResponse(BaseModel):
    """Response model for product listing with pagination."""

    data: List[Product]
    meta: PaginationMeta


class BrandBase(BaseModel):
    """Base brand DTO."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    website: Optional[HttpUrl] = None
    logo_url: Optional[HttpUrl] = Field(None, alias="logoUrl")
    is_active: bool = Field(default=True, alias="isActive")
    model_config = ConfigDict(populate_by_name=True)


class BrandCreate(BrandBase):
    """DTO for creating a new brand."""


class BrandUpdate(BaseModel):
    """DTO for updating an existing brand."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
    )
    description: Optional[str] = None
    website: Optional[HttpUrl] = None
    logo_url: Optional[HttpUrl] = Field(None, alias="logoUrl")
    is_active: Optional[bool] = Field(None, alias="isActive")
    model_config = ConfigDict(populate_by_name=True)


class Brand(BrandBase):
    """Brand DTO with read-only fields."""

    id: int
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    emag_id: Optional[int] = Field(None, alias="emagId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class BrandListResponse(BaseModel):
    """Response model for brand listing with pagination."""

    data: List[Brand]
    meta: PaginationMeta


class CharacteristicType(str, Enum):
    """Types of product characteristics."""

    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"


class CharacteristicValue(BaseModel):
    """Characteristic value DTO."""

    id: int
    value: str
    is_default: bool = Field(False, alias="isDefault")
    position: int = 0
    model_config = ConfigDict(populate_by_name=True)


class CharacteristicBase(BaseModel):
    """Base characteristic DTO."""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    type: CharacteristicType
    is_required: bool = Field(False, alias="isRequired")
    is_filterable: bool = Field(False, alias="isFilterable")
    is_variant: bool = Field(False, alias="isVariant")
    values: List[CharacteristicValue] = []
    category_id: int = Field(..., alias="categoryId")
    model_config = ConfigDict(populate_by_name=True)


class CharacteristicCreate(CharacteristicBase):
    """DTO for creating a new characteristic."""


class CharacteristicUpdate(BaseModel):
    """DTO for updating an existing characteristic."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )
    type: Optional[CharacteristicType] = None
    is_required: Optional[bool] = Field(None, alias="isRequired")
    is_filterable: Optional[bool] = Field(None, alias="isFilterable")
    is_variant: Optional[bool] = Field(None, alias="isVariant")
    values: Optional[List[CharacteristicValue]] = None
    category_id: Optional[int] = Field(None, alias="categoryId")
    model_config = ConfigDict(populate_by_name=True)


class Characteristic(CharacteristicBase):
    """Characteristic DTO with read-only fields."""

    id: int
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    emag_id: Optional[int] = Field(None, alias="emagId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CharacteristicListResponse(BaseModel):
    """Response model for characteristic listing with pagination."""

    data: List[Characteristic]
    meta: PaginationMeta


class ProductFilter(BaseModel):
    """Filter criteria for product listing."""

    q: Optional[str] = None
    category_id: Optional[int] = Field(None, alias="categoryId")
    brand_id: Optional[int] = Field(None, alias="brandId")
    status: Optional[ProductStatus] = None
    min_price: Optional[float] = Field(None, alias="minPrice", gt=0)
    max_price: Optional[float] = Field(None, alias="maxPrice", gt=0)
    in_stock: Optional[bool] = Field(None, alias="inStock")
    created_after: Optional[datetime] = Field(None, alias="createdAfter")
    updated_after: Optional[datetime] = Field(None, alias="updatedAfter")

    # Cursor-based pagination
    cursor: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    sort_by: SortField = Field(SortField.CREATED_AT, alias="sortBy")
    sort_direction: SortDirection = Field(SortDirection.DESC, alias="sortDirection")

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("created_after", "updated_after", when_used="json")
    def serialize_optional_datetime(
        self, value: Optional[datetime], _info
    ) -> Optional[str]:
        return value.isoformat() if value else None

    def to_query_params(self) -> Dict[str, str]:
        """Convert filter to query parameters."""
        params = {}
        if self.q:
            params["q"] = self.q
        if self.category_id is not None:
            params["category_id"] = str(self.category_id)
        if self.brand_id is not None:
            params["brand_id"] = str(self.brand_id)
        if self.status:
            params["status"] = self.status.value
        if self.min_price is not None:
            params["min_price"] = str(self.min_price)
        if self.max_price is not None:
            params["max_price"] = str(self.max_price)
        if self.in_stock is not None:
            params["in_stock"] = "true" if self.in_stock else "false"
        if self.created_after:
            params["created_after"] = self.created_after.isoformat()
        if self.updated_after:
            params["updated_after"] = self.updated_after.isoformat()
        if self.cursor:
            params["cursor"] = self.cursor
        if self.limit != 20:  # Only include if not default
            params["limit"] = str(self.limit)
        if self.sort_by != SortField.CREATED_AT:  # Only include if not default
            params["sort_by"] = self.sort_by.value
        if self.sort_direction != SortDirection.DESC:  # Only include if not default
            params["sort_direction"] = self.sort_direction.value
        return params

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CategorySummary(BaseModel):
    id: int = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    description: Optional[str] = Field(None, description="Product description")
    base_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    currency: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )
    is_active: Optional[bool] = Field(None, description="Whether the product is active")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProductCreate(ProductBase):
    category_ids: List[int] = Field(
        default_factory=list,
        description="Categories to attach to the product",
    )
    characteristics: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Structured product characteristics",
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="Product image URLs",
    )


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Product name",
    )
    sku: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Stock Keeping Unit",
    )
    description: Optional[str] = Field(None, description="Product description")
    base_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    currency: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )
    is_active: Optional[bool] = Field(None, description="Whether the product is active")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    currency: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )
    is_active: bool = Field(..., description="Whether the product is active")
    categories: List[CategorySummary] = Field(
        default_factory=list,
        description="Associated categories",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    limit: int
    offset: int

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    price: Optional[Decimal] = Field(
        None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product price",
    )


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Product name",
    )
    price: Optional[Decimal] = Field(
        None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product price",
    )


class ProductResponse(ProductBase):
    id: int
    categories: List[str] = Field(
        default_factory=list,
        description="Associated category names",
    )

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    limit: int
    offset: int

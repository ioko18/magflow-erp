"""Pydantic schemas for supplier product matching."""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class MatchingRequest(BaseModel):
    """Request for running matching algorithms."""
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Similarity threshold (0.0-1.0). Uses default if not provided."
    )


class ConfirmMatchRequest(BaseModel):
    """Request to confirm or reject a match."""
    notes: Optional[str] = Field(default=None, max_length=500)


class ImportColumnMapping(BaseModel):
    """Custom column mapping for Excel import."""
    chinese_name: str = Field(default="Nume produs")
    price_cny: str = Field(default="Pret CNY")
    product_url: str = Field(default="URL produs")
    image_url: str = Field(default="URL imagine")


# ==================== RESPONSE SCHEMAS ====================

class SupplierRawProductResponse(BaseModel):
    """Response schema for raw supplier product."""
    id: int
    supplier_id: int
    chinese_name: str
    english_name: Optional[str]
    price_cny: float
    product_url: str
    image_url: str
    matching_status: str
    product_group_id: Optional[int]
    import_batch_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductMatchingGroupResponse(BaseModel):
    """Response schema for matching group (list view)."""
    id: int
    group_name: str
    group_name_en: Optional[str]
    product_count: int
    min_price_cny: Optional[float]
    max_price_cny: Optional[float]
    avg_price_cny: Optional[float]
    confidence_score: float
    matching_method: str
    status: str
    representative_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductInGroup(BaseModel):
    """Product details within a matching group."""
    id: int
    supplier_id: int
    supplier_name: str
    chinese_name: str
    english_name: Optional[str]
    price_cny: float
    product_url: str
    image_url: str
    matching_status: str


class ProductMatchingGroupDetail(BaseModel):
    """Detailed response schema for matching group."""
    id: int
    group_name: str
    group_name_en: Optional[str]
    description: Optional[str]
    representative_image_url: Optional[str]
    product_count: int
    min_price_cny: Optional[float]
    max_price_cny: Optional[float]
    avg_price_cny: Optional[float]
    best_supplier_id: Optional[int]
    confidence_score: float
    matching_method: str
    status: str
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    created_at: datetime
    products: List[ProductInGroup]

    class Config:
        from_attributes = True


class PriceComparisonProduct(BaseModel):
    """Product in price comparison."""
    product_id: int
    supplier_id: int
    supplier_name: str
    price_cny: float
    product_url: str
    chinese_name: str
    english_name: Optional[str]
    image_url: str


class PriceComparisonResponse(BaseModel):
    """Price comparison for a matching group."""
    group_id: int
    group_name: str
    product_count: int
    best_price_cny: float
    worst_price_cny: float
    avg_price_cny: float
    savings_cny: float
    savings_percent: float
    products: List[Dict]


class ImportResponse(BaseModel):
    """Response for import operation."""
    success: bool
    batch_id: str
    supplier_id: int
    supplier_name: str
    total_rows: int
    imported: int
    skipped: int
    errors: int
    error_details: List[str] = []


class MatchingStatsResponse(BaseModel):
    """Overall matching statistics."""
    total_products: int
    matched_products: int
    pending_products: int
    total_groups: int
    verified_groups: int
    pending_groups: int
    active_suppliers: int
    matching_rate: float


class SupplierProductsSummary(BaseModel):
    """Summary of products per supplier."""
    supplier_id: int
    supplier_name: str
    total_products: int
    matched_products: int
    pending_products: int
    avg_price_cny: float
    min_price_cny: float
    max_price_cny: float

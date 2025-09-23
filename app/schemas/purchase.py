"""Pydantic schemas for purchase management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SupplierStatus(str, Enum):
    """Supplier status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PREFERRED = "preferred"


class SupplierBase(BaseModel):
    """Base supplier schema."""

    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    lead_time_days: int = 7
    minimum_order_value: Optional[float] = None
    is_active: bool = True
    rating: Optional[int] = Field(None, ge=1, le=5)


class SupplierCreate(SupplierBase):
    """Schema for creating a supplier."""


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier."""

    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    lead_time_days: Optional[int] = None
    minimum_order_value: Optional[float] = None
    is_active: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class SupplierInDBBase(SupplierBase):
    """Base schema for supplier data in database."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Supplier(SupplierInDBBase):
    """Schema for supplier data returned to clients."""


class SupplierProductBase(BaseModel):
    """Base supplier product schema."""

    supplier_id: int
    product_id: int
    supplier_product_code: Optional[str] = Field(None, max_length=50)
    supplier_product_name: Optional[str] = Field(None, max_length=100)
    unit_cost: float = Field(..., gt=0)
    minimum_order_quantity: int = 1
    lead_time_days: int = 7
    is_preferred: bool = False
    notes: Optional[str] = None


class SupplierProductCreate(SupplierProductBase):
    """Schema for creating a supplier product."""


class SupplierProductUpdate(BaseModel):
    """Schema for updating a supplier product."""

    supplier_product_code: Optional[str] = Field(None, max_length=50)
    supplier_product_name: Optional[str] = Field(None, max_length=100)
    unit_cost: Optional[float] = Field(None, gt=0)
    minimum_order_quantity: Optional[int] = Field(None, gt=0)
    lead_time_days: Optional[int] = Field(None, gt=0)
    is_preferred: Optional[bool] = None
    notes: Optional[str] = None


class SupplierProductInDBBase(SupplierProductBase):
    """Base schema for supplier product data in database."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierProduct(SupplierProductInDBBase):
    """Schema for supplier product data returned to clients."""

    supplier: Optional[Supplier] = None


class PurchaseOrderStatus(str, Enum):
    """Purchase order status enumeration."""

    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrderBase(BaseModel):
    """Base purchase order schema."""

    supplier_id: int
    order_date: datetime
    expected_delivery_date: Optional[datetime] = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    currency: str = "RON"
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating a purchase order."""

    order_lines: List["PurchaseOrderLineCreate"] = Field(..., min_length=1)


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating a purchase order."""

    expected_delivery_date: Optional[datetime] = None
    status: Optional[PurchaseOrderStatus] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PurchaseOrderLineBase(BaseModel):
    """Base purchase order line schema."""

    product_id: int
    supplier_product_id: Optional[int] = None
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    tax_percent: float = Field(19, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=255)


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    """Schema for creating a purchase order line."""


class PurchaseOrderLineInDBBase(PurchaseOrderLineBase):
    """Base schema for purchase order line data in database."""

    id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    line_total: Optional[float] = None
    received_quantity: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderLine(PurchaseOrderLineInDBBase):
    """Schema for purchase order line data returned to clients."""


class PurchaseOrderInDBBase(PurchaseOrderBase):
    """Base schema for purchase order data in database."""

    id: Optional[int] = None
    order_number: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    shipping_cost: Optional[float] = None
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrder(PurchaseOrderInDBBase):
    """Schema for purchase order data returned to clients."""

    supplier: Optional[Supplier] = None
    order_lines: List[PurchaseOrderLine] = []


class PurchaseReceiptStatus(str, Enum):
    """Purchase receipt status enumeration."""

    DRAFT = "draft"
    RECEIVED = "received"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"


class PurchaseReceiptBase(BaseModel):
    """Base purchase receipt schema."""

    purchase_order_id: int
    receipt_date: datetime
    supplier_invoice_number: Optional[str] = Field(None, max_length=50)
    supplier_invoice_date: Optional[datetime] = None
    currency: str = "RON"
    notes: Optional[str] = None


class PurchaseReceiptCreate(PurchaseReceiptBase):
    """Schema for creating a purchase receipt."""


class PurchaseReceiptUpdate(BaseModel):
    """Schema for updating a purchase receipt."""

    supplier_invoice_number: Optional[str] = Field(None, max_length=50)
    supplier_invoice_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[PurchaseReceiptStatus] = None
    quality_checked_by: Optional[int] = None


class PurchaseReceiptLineBase(BaseModel):
    """Base purchase receipt line schema."""

    purchase_order_line_id: int
    received_quantity: int = Field(..., gt=0)
    accepted_quantity: int = Field(..., gt=0)
    rejected_quantity: int = 0
    unit_cost: float = Field(..., gt=0)
    quality_status: str = "pending"  # pending, accepted, rejected, partial
    rejection_reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=255)


class PurchaseReceiptLineCreate(PurchaseReceiptLineBase):
    """Schema for creating a purchase receipt line."""


class PurchaseReceiptLineInDBBase(PurchaseReceiptLineBase):
    """Base schema for purchase receipt line data in database."""

    id: Optional[int] = None
    purchase_receipt_id: Optional[int] = None
    line_total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceiptLine(PurchaseReceiptLineInDBBase):
    """Schema for purchase receipt line data returned to clients."""

    purchase_order_line: Optional[PurchaseOrderLine] = None


class PurchaseReceiptInDBBase(PurchaseReceiptBase):
    """Base schema for purchase receipt data in database."""

    id: Optional[int] = None
    receipt_number: Optional[str] = None
    status: PurchaseReceiptStatus = PurchaseReceiptStatus.DRAFT
    total_received_quantity: Optional[int] = None
    total_amount: Optional[float] = None
    received_by: Optional[int] = None
    quality_checked_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceipt(PurchaseReceiptInDBBase):
    """Schema for purchase receipt data returned to clients."""

    purchase_order: Optional[PurchaseOrder] = None
    receipt_lines: List[PurchaseReceiptLine] = []


class SupplierPaymentMethod(str, Enum):
    """Supplier payment method enumeration."""

    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CASH = "cash"
    WIRE_TRANSFER = "wire_transfer"


class SupplierPaymentStatus(str, Enum):
    """Supplier payment status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SupplierPaymentBase(BaseModel):
    """Base supplier payment schema."""

    supplier_id: int
    purchase_receipt_id: Optional[int] = None
    payment_date: datetime
    amount: float = Field(..., gt=0)
    payment_method: SupplierPaymentMethod
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class SupplierPaymentCreate(SupplierPaymentBase):
    """Schema for creating a supplier payment."""


class SupplierPaymentUpdate(BaseModel):
    """Schema for updating a supplier payment."""

    payment_date: Optional[datetime] = None
    amount: Optional[float] = Field(None, gt=0)
    payment_method: Optional[SupplierPaymentMethod] = None
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[SupplierPaymentStatus] = None
    processed_by: Optional[int] = None


class SupplierPaymentInDBBase(SupplierPaymentBase):
    """Base schema for supplier payment data in database."""

    id: Optional[int] = None
    payment_number: Optional[str] = None
    status: SupplierPaymentStatus = SupplierPaymentStatus.PENDING
    processed_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierPayment(SupplierPaymentInDBBase):
    """Schema for supplier payment data returned to clients."""

    supplier: Optional[Supplier] = None
    purchase_receipt: Optional[PurchaseReceipt] = None


class PurchaseRequisitionPriority(str, Enum):
    """Purchase requisition priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PurchaseRequisitionStatus(str, Enum):
    """Purchase requisition status enumeration."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PurchaseRequisitionBase(BaseModel):
    """Base purchase requisition schema."""

    requested_by: int
    department: Optional[str] = Field(None, max_length=50)
    required_date: datetime
    status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT
    priority: PurchaseRequisitionPriority = PurchaseRequisitionPriority.NORMAL
    currency: str = "RON"
    justification: Optional[str] = None
    notes: Optional[str] = None


class PurchaseRequisitionCreate(PurchaseRequisitionBase):
    """Schema for creating a purchase requisition."""

    requisition_lines: List["PurchaseRequisitionLineCreate"] = Field(..., min_length=1)


class PurchaseRequisitionUpdate(BaseModel):
    """Schema for updating a purchase requisition."""

    department: Optional[str] = Field(None, max_length=50)
    required_date: Optional[datetime] = None
    priority: Optional[PurchaseRequisitionPriority] = None
    justification: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[PurchaseRequisitionStatus] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None


class PurchaseRequisitionLineBase(BaseModel):
    """Base purchase requisition line schema."""

    product_id: int
    description: str = Field(..., max_length=255)
    quantity: int = Field(..., gt=0)
    estimated_unit_cost: float = Field(..., gt=0)
    supplier_preference: Optional[str] = Field(None, max_length=100)
    justification: Optional[str] = None


class PurchaseRequisitionLineCreate(PurchaseRequisitionLineBase):
    """Schema for creating a purchase requisition line."""


class PurchaseRequisitionLineInDBBase(PurchaseRequisitionLineBase):
    """Base schema for purchase requisition line data in database."""

    id: Optional[int] = None
    purchase_requisition_id: Optional[int] = None
    estimated_total_cost: Optional[float] = None
    status: str = "pending"  # pending, ordered, received, cancelled
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequisitionLine(PurchaseRequisitionLineInDBBase):
    """Schema for purchase requisition line data returned to clients."""


class PurchaseRequisitionInDBBase(PurchaseRequisitionBase):
    """Base schema for purchase requisition data in database."""

    id: Optional[int] = None
    requisition_number: Optional[str] = None
    total_estimated_cost: Optional[float] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequisition(PurchaseRequisitionInDBBase):
    """Schema for purchase requisition data returned to clients."""

    requisition_lines: List[PurchaseRequisitionLine] = []


# Response schemas
class PurchaseSummary(BaseModel):
    """Summary of purchase metrics."""

    total_orders: int
    pending_orders: int
    received_orders: int
    total_spent: float
    pending_amount: float
    top_suppliers: List[Dict] = []
    monthly_spending: Dict[str, float] = {}


class SupplierPerformance(BaseModel):
    """Supplier performance metrics."""

    supplier_id: int
    supplier_name: str
    total_orders: int
    on_time_delivery: float  # percentage
    quality_rating: float
    average_lead_time: float
    total_spent: float

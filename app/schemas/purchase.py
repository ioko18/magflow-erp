"""Pydantic schemas for purchase management."""

from datetime import datetime
from enum import Enum

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
    email: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    address: str | None = None
    city: str | None = Field(None, max_length=50)
    country: str | None = Field(None, max_length=50)
    tax_id: str | None = Field(None, max_length=50)
    payment_terms: str | None = Field(None, max_length=100)
    lead_time_days: int = 7
    minimum_order_value: float | None = None
    is_active: bool = True
    rating: int | None = Field(None, ge=1, le=5)


class SupplierCreate(SupplierBase):
    """Schema for creating a supplier."""


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier."""

    code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    address: str | None = None
    city: str | None = Field(None, max_length=50)
    country: str | None = Field(None, max_length=50)
    tax_id: str | None = Field(None, max_length=50)
    payment_terms: str | None = Field(None, max_length=100)
    lead_time_days: int | None = None
    minimum_order_value: float | None = None
    is_active: bool | None = None
    rating: int | None = Field(None, ge=1, le=5)


class SupplierInDBBase(SupplierBase):
    """Base schema for supplier data in database."""

    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Supplier(SupplierInDBBase):
    """Schema for supplier data returned to clients."""


class SupplierProductBase(BaseModel):
    """Base supplier product schema."""

    supplier_id: int
    product_id: int
    supplier_product_code: str | None = Field(None, max_length=50)
    supplier_product_name: str | None = Field(None, max_length=100)
    unit_cost: float = Field(..., gt=0)
    minimum_order_quantity: int = 1
    lead_time_days: int = 7
    is_preferred: bool = False
    notes: str | None = None


class SupplierProductCreate(SupplierProductBase):
    """Schema for creating a supplier product."""


class SupplierProductUpdate(BaseModel):
    """Schema for updating a supplier product."""

    supplier_product_code: str | None = Field(None, max_length=50)
    supplier_product_name: str | None = Field(None, max_length=100)
    unit_cost: float | None = Field(None, gt=0)
    minimum_order_quantity: int | None = Field(None, gt=0)
    lead_time_days: int | None = Field(None, gt=0)
    is_preferred: bool | None = None
    notes: str | None = None


class SupplierProductInDBBase(SupplierProductBase):
    """Base schema for supplier product data in database."""

    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SupplierProduct(SupplierProductInDBBase):
    """Schema for supplier product data returned to clients."""

    supplier: Supplier | None = None


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
    expected_delivery_date: datetime | None = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    currency: str = "RON"
    payment_terms: str | None = Field(None, max_length=100)
    notes: str | None = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating a purchase order."""

    order_lines: list["PurchaseOrderLineCreate"] = Field(..., min_length=1)


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating a purchase order."""

    expected_delivery_date: datetime | None = None
    status: PurchaseOrderStatus | None = None
    payment_terms: str | None = Field(None, max_length=100)
    notes: str | None = None


class PurchaseOrderLineBase(BaseModel):
    """Base purchase order line schema - adapted to PurchaseOrderItem."""

    product_id: int  # Will map to local_product_id
    quantity: int = Field(..., gt=0)  # Will map to quantity_ordered
    unit_cost: float = Field(..., gt=0)  # Will map to unit_price
    discount_percent: float = Field(0, ge=0, le=100)  # Not in DB, calculated
    tax_percent: float = Field(19, ge=0, le=100)  # Not in DB, calculated
    line_total: float = Field(..., gt=0)  # Will map to total_price
    notes: str | None = Field(None, max_length=255)  # Not in purchase_order_items


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    """Schema for creating a purchase order line."""


class PurchaseOrderLineInDBBase(PurchaseOrderLineBase):
    """Base schema for purchase order line data in database."""

    id: int | None = None
    purchase_order_id: int | None = None
    received_quantity: int = 0  # Will map to quantity_received

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderLine(PurchaseOrderLineInDBBase):
    """Schema for purchase order line data returned to clients - uses PurchaseOrderItem model."""


class PurchaseOrderInDBBase(PurchaseOrderBase):
    """Base schema for purchase order data in database."""

    id: int | None = None
    order_number: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    discount_amount: float | None = None
    shipping_cost: float | None = None
    created_by: int | None = None
    approved_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrder(PurchaseOrderInDBBase):
    """Schema for purchase order data returned to clients."""

    supplier: Supplier | None = None
    order_lines: list[PurchaseOrderLine] = []


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
    supplier_invoice_number: str | None = Field(None, max_length=50)
    supplier_invoice_date: datetime | None = None
    currency: str = "RON"
    notes: str | None = None


class PurchaseReceiptCreate(PurchaseReceiptBase):
    """Schema for creating a purchase receipt."""


class PurchaseReceiptUpdate(BaseModel):
    """Schema for updating a purchase receipt."""

    supplier_invoice_number: str | None = Field(None, max_length=50)
    supplier_invoice_date: datetime | None = None
    notes: str | None = None
    status: PurchaseReceiptStatus | None = None
    quality_checked_by: int | None = None


class PurchaseReceiptLineBase(BaseModel):
    """Base purchase receipt line schema."""

    purchase_order_line_id: int
    received_quantity: int = Field(..., gt=0)
    accepted_quantity: int = Field(..., gt=0)
    rejected_quantity: int = 0
    unit_cost: float = Field(..., gt=0)
    quality_status: str = "pending"  # pending, accepted, rejected, partial
    rejection_reason: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=255)


class PurchaseReceiptLineCreate(PurchaseReceiptLineBase):
    """Schema for creating a purchase receipt line."""


class PurchaseReceiptLineInDBBase(PurchaseReceiptLineBase):
    """Base schema for purchase receipt line data in database."""

    id: int | None = None
    purchase_receipt_id: int | None = None
    line_total: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceiptLine(PurchaseReceiptLineInDBBase):
    """Schema for purchase receipt line data returned to clients."""

    purchase_order_line: PurchaseOrderLine | None = None


class PurchaseReceiptInDBBase(PurchaseReceiptBase):
    """Base schema for purchase receipt data in database."""

    id: int | None = None
    receipt_number: str | None = None
    status: PurchaseReceiptStatus = PurchaseReceiptStatus.DRAFT
    total_received_quantity: int | None = None
    total_amount: float | None = None
    received_by: int | None = None
    quality_checked_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceipt(PurchaseReceiptInDBBase):
    """Schema for purchase receipt data returned to clients."""

    purchase_order: PurchaseOrder | None = None
    receipt_lines: list[PurchaseReceiptLine] = []


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
    purchase_receipt_id: int | None = None
    payment_date: datetime
    amount: float = Field(..., gt=0)
    payment_method: SupplierPaymentMethod
    reference: str | None = Field(None, max_length=100)
    notes: str | None = None


class SupplierPaymentCreate(SupplierPaymentBase):
    """Schema for creating a supplier payment."""


class SupplierPaymentUpdate(BaseModel):
    """Schema for updating a supplier payment."""

    payment_date: datetime | None = None
    amount: float | None = Field(None, gt=0)
    payment_method: SupplierPaymentMethod | None = None
    reference: str | None = Field(None, max_length=100)
    notes: str | None = None
    status: SupplierPaymentStatus | None = None
    processed_by: int | None = None


class SupplierPaymentInDBBase(SupplierPaymentBase):
    """Base schema for supplier payment data in database."""

    id: int | None = None
    payment_number: str | None = None
    status: SupplierPaymentStatus = SupplierPaymentStatus.PENDING
    processed_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SupplierPayment(SupplierPaymentInDBBase):
    """Schema for supplier payment data returned to clients."""

    supplier: Supplier | None = None
    purchase_receipt: PurchaseReceipt | None = None


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
    department: str | None = Field(None, max_length=50)
    required_date: datetime
    status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT
    priority: PurchaseRequisitionPriority = PurchaseRequisitionPriority.NORMAL
    currency: str = "RON"
    justification: str | None = None
    notes: str | None = None


class PurchaseRequisitionCreate(PurchaseRequisitionBase):
    """Schema for creating a purchase requisition."""

    requisition_lines: list["PurchaseRequisitionLineCreate"] = Field(..., min_length=1)


class PurchaseRequisitionUpdate(BaseModel):
    """Schema for updating a purchase requisition."""

    department: str | None = Field(None, max_length=50)
    required_date: datetime | None = None
    priority: PurchaseRequisitionPriority | None = None
    justification: str | None = None
    notes: str | None = None
    status: PurchaseRequisitionStatus | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None


class PurchaseRequisitionLineBase(BaseModel):
    """Base purchase requisition line schema."""

    product_id: int
    description: str = Field(..., max_length=255)
    quantity: int = Field(..., gt=0)
    estimated_unit_cost: float = Field(..., gt=0)
    supplier_preference: str | None = Field(None, max_length=100)
    justification: str | None = None


class PurchaseRequisitionLineCreate(PurchaseRequisitionLineBase):
    """Schema for creating a purchase requisition line."""


class PurchaseRequisitionLineInDBBase(PurchaseRequisitionLineBase):
    """Base schema for purchase requisition line data in database."""

    id: int | None = None
    purchase_requisition_id: int | None = None
    estimated_total_cost: float | None = None
    status: str = "pending"  # pending, ordered, received, cancelled
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequisitionLine(PurchaseRequisitionLineInDBBase):
    """Schema for purchase requisition line data returned to clients."""


class PurchaseRequisitionInDBBase(PurchaseRequisitionBase):
    """Base schema for purchase requisition data in database."""

    id: int | None = None
    requisition_number: str | None = None
    total_estimated_cost: float | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequisition(PurchaseRequisitionInDBBase):
    """Schema for purchase requisition data returned to clients."""

    requisition_lines: list[PurchaseRequisitionLine] = []


# Response schemas
class PurchaseSummary(BaseModel):
    """Summary of purchase metrics."""

    total_orders: int
    pending_orders: int
    received_orders: int
    total_spent: float
    pending_amount: float
    top_suppliers: list[dict] = []
    monthly_spending: dict[str, float] = {}


class SupplierPerformance(BaseModel):
    """Supplier performance metrics."""

    supplier_id: int
    supplier_name: str
    total_orders: int
    on_time_delivery: float  # percentage
    quality_rating: float
    average_lead_time: float
    total_spent: float

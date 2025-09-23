"""Pydantic schemas for sales management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerStatus(str, Enum):
    """Customer status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class CustomerBase(BaseModel):
    """Base customer schema."""

    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[float] = None
    is_active: bool = True


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""

    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[float] = None
    is_active: Optional[bool] = None


class CustomerInDBBase(CustomerBase):
    """Base schema for customer data in database."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Customer(CustomerInDBBase):
    """Schema for customer data returned to clients."""


class SalesOrderStatus(str, Enum):
    """Sales order status enumeration."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SalesOrderBase(BaseModel):
    """Base sales order schema."""

    customer_id: int
    order_date: datetime
    delivery_date: Optional[datetime] = None
    status: SalesOrderStatus = SalesOrderStatus.DRAFT
    currency: str = "RON"
    notes: Optional[str] = None


class SalesOrderCreate(SalesOrderBase):
    """Schema for creating a sales order."""

    order_lines: List["SalesOrderLineCreate"] = Field(..., min_length=1)


class SalesOrderUpdate(BaseModel):
    """Schema for updating a sales order."""

    delivery_date: Optional[datetime] = None
    status: Optional[SalesOrderStatus] = None
    notes: Optional[str] = None


class SalesOrderLineBase(BaseModel):
    """Base sales order line schema."""

    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    tax_percent: float = Field(19, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=255)


class SalesOrderLineCreate(SalesOrderLineBase):
    """Schema for creating a sales order line."""


class SalesOrderLineInDBBase(SalesOrderLineBase):
    """Base schema for sales order line data in database."""

    id: Optional[int] = None
    sales_order_id: Optional[int] = None
    line_total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrderLine(SalesOrderLineInDBBase):
    """Schema for sales order line data returned to clients."""


class SalesOrderInDBBase(SalesOrderBase):
    """Base schema for sales order data in database."""

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


class SalesOrder(SalesOrderInDBBase):
    """Schema for sales order data returned to clients."""

    customer: Optional[Customer] = None
    order_lines: List[SalesOrderLine] = []


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceBase(BaseModel):
    """Base invoice schema."""

    customer_id: int
    sales_order_id: Optional[int] = None
    invoice_date: datetime
    due_date: datetime
    currency: str = "RON"
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""

    invoice_lines: List["InvoiceLineCreate"] = Field(..., min_length=1)


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice."""

    due_date: Optional[datetime] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoiceLineBase(BaseModel):
    """Base invoice line schema."""

    product_id: int
    description: str = Field(..., max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    tax_percent: float = Field(19, ge=0, le=100)


class InvoiceLineCreate(InvoiceLineBase):
    """Schema for creating an invoice line."""

    sales_order_line_id: Optional[int] = None


class InvoiceLineInDBBase(InvoiceLineBase):
    """Base schema for invoice line data in database."""

    id: Optional[int] = None
    invoice_id: Optional[int] = None
    line_total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceLine(InvoiceLineInDBBase):
    """Schema for invoice line data returned to clients."""


class InvoiceInDBBase(InvoiceBase):
    """Base schema for invoice data in database."""

    id: Optional[int] = None
    invoice_number: Optional[str] = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    subtotal_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Invoice(InvoiceInDBBase):
    """Schema for invoice data returned to clients."""

    customer: Optional[Customer] = None
    sales_order: Optional[SalesOrder] = None
    invoice_lines: List[InvoiceLine] = []
    payments: List["Payment"] = []


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CHECK = "check"
    PAYPAL = "paypal"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentBase(BaseModel):
    """Base payment schema."""

    invoice_id: int
    payment_date: datetime
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Schema for creating a payment."""


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""

    payment_date: Optional[datetime] = None
    amount: Optional[float] = Field(None, gt=0)
    payment_method: Optional[PaymentMethod] = None
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[PaymentStatus] = None
    processed_by: Optional[int] = None


class PaymentInDBBase(PaymentBase):
    """Base schema for payment data in database."""

    id: Optional[int] = None
    payment_number: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    processed_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Payment(PaymentInDBBase):
    """Schema for payment data returned to clients."""

    invoice: Optional[Invoice] = None


class SalesQuoteStatus(str, Enum):
    """Sales quote status enumeration."""

    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SalesQuoteBase(BaseModel):
    """Base sales quote schema."""

    customer_id: int
    valid_until: datetime
    currency: str = "RON"
    notes: Optional[str] = None


class SalesQuoteCreate(SalesQuoteBase):
    """Schema for creating a sales quote."""

    quote_lines: List["SalesQuoteLineCreate"] = Field(..., min_length=1)


class SalesQuoteUpdate(BaseModel):
    """Schema for updating a sales quote."""

    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[SalesQuoteStatus] = None


class SalesQuoteLineBase(BaseModel):
    """Base sales quote line schema."""

    product_id: int
    description: str = Field(..., max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    tax_percent: float = Field(19, ge=0, le=100)


class SalesQuoteLineCreate(SalesQuoteLineBase):
    """Schema for creating a sales quote line."""


class SalesQuoteLineInDBBase(SalesQuoteLineBase):
    """Base schema for sales quote line data in database."""

    id: Optional[int] = None
    sales_quote_id: Optional[int] = None
    line_total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesQuoteLine(SalesQuoteLineInDBBase):
    """Schema for sales quote line data returned to clients."""


class SalesQuoteInDBBase(SalesQuoteBase):
    """Base schema for sales quote data in database."""

    id: Optional[int] = None
    quote_number: Optional[str] = None
    status: SalesQuoteStatus = SalesQuoteStatus.DRAFT
    subtotal_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesQuote(SalesQuoteInDBBase):
    """Schema for sales quote data returned to clients."""

    customer: Optional[Customer] = None
    quote_lines: List[SalesQuoteLine] = []


# Response schemas
class SalesSummary(BaseModel):
    """Summary of sales metrics."""

    total_orders: int
    total_revenue: float
    pending_orders: int
    shipped_orders: int
    average_order_value: float
    top_customers: List[Dict] = []
    monthly_revenue: Dict[str, float] = {}


class InvoiceSummary(BaseModel):
    """Summary of invoice status."""

    total_invoices: int
    paid_invoices: int
    pending_invoices: int
    overdue_invoices: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    overdue_amount: float

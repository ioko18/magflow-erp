"""Invoice Management API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_async_session
from app.db.models import User
from app.models.invoice import (
    Invoice,
    InvoiceItem,
    InvoicePayment,
    InvoiceStatus,
    InvoiceType,
    PaymentMethod,
    TaxCategory,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=dict)
async def create_invoice(
    order_id: int | None = None,
    customer_id: int | None = None,
    customer_name: str = None,
    customer_email: str | None = None,
    customer_address: str | None = None,
    customer_tax_id: str | None = None,
    invoice_type: InvoiceType = InvoiceType.SALES_INVOICE,
    invoice_date: datetime = None,
    due_date: datetime = None,
    items: list[dict] = None,  # List of item dicts with sku, quantity, price, etc.
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new invoice."""
    if not invoice_date:
        invoice_date = datetime.now(UTC)

    # Calculate due date (30 days from invoice date)
    if not due_date:
        due_date = invoice_date.replace(day=min(invoice_date.day + 30, 31))

    # Generate invoice number
    invoice_number = (
        "INV-"
        f"{datetime.now().strftime('%Y%m%d')}"
        "-"
        f"{abs(hash(str(order_id or customer_id) + str(invoice_date.timestamp()))) % 10000:04d}"
    )

    # Calculate totals
    subtotal = 0.0
    tax_amount = 0.0
    total_amount = 0.0

    for item_data in items or []:
        item_total = item_data.get("quantity", 1) * item_data.get("unit_price", 0.0)
        subtotal += item_total

        # Calculate tax
        tax_rate = item_data.get("tax_rate", 19.0)  # Default 19% VAT
        item_tax = item_total * (tax_rate / 100)
        tax_amount += item_tax
        total_amount += item_total + item_tax

    # Create invoice
    invoice = Invoice(
        invoice_number=invoice_number,
        order_id=order_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_address=customer_address,
        customer_tax_id=customer_tax_id,
        invoice_type=invoice_type,
        status=InvoiceStatus.DRAFT,
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        currency="RON",  # Default currency
        account_type="main",  # Default to main, should be configurable
    )

    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    # Create invoice items
    for item_data in items or []:
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            sku=item_data.get("sku"),
            product_name=item_data.get("product_name", ""),
            description=item_data.get("description"),
            quantity=item_data.get("quantity", 1),
            unit_price=item_data.get("unit_price", 0.0),
            discount_amount=item_data.get("discount_amount", 0.0),
            line_total=item_data.get("quantity", 1) * item_data.get("unit_price", 0.0),
            tax_category=item_data.get("tax_category", TaxCategory.STANDARD),
            tax_rate=item_data.get("tax_rate", 19.0),
            tax_amount=(item_data.get("quantity", 1) * item_data.get("unit_price", 0.0))
            * (item_data.get("tax_rate", 19.0) / 100),
        )
        session.add(invoice_item)

    await session.commit()

    return {
        "message": "Invoice created successfully",
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "total_amount": invoice.total_amount,
        "status": invoice.status,
    }


@router.get("/", response_model=dict)
async def list_invoices(
    status: InvoiceStatus | None = Query(None, description="Filter by status"),
    invoice_type: InvoiceType | None = Query(None, description="Filter by type"),
    limit: int = Query(50, description="Number of results to return", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """List invoices with optional filtering."""
    query = select(Invoice).order_by(Invoice.created_at.desc())

    if status:
        query = query.where(Invoice.status == status)

    if invoice_type:
        query = query.where(Invoice.invoice_type == invoice_type)

    result = await session.execute(query.offset(offset).limit(limit))
    invoices = result.scalars().all()

    # Get total count
    count_query = select(Invoice)
    if status:
        count_query = count_query.where(Invoice.status == status)
    if invoice_type:
        count_query = count_query.where(Invoice.invoice_type == invoice_type)

    count_result = await session.execute(count_query)
    total_count = len(count_result.scalars().all())

    return {
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer_name,
                "status": inv.status,
                "invoice_type": inv.invoice_type,
                "total_amount": inv.total_amount,
                "invoice_date": inv.invoice_date,
                "due_date": inv.due_date,
                "paid_amount": inv.paid_amount,
            }
            for inv in invoices
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{invoice_id}", response_model=dict)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about an invoice."""
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get invoice items
    items_result = await session.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id),
    )
    invoice_items = items_result.scalars().all()

    # Get payments
    payments_result = await session.execute(
        select(InvoicePayment).where(InvoicePayment.invoice_id == invoice_id),
    )
    payments = payments_result.scalars().all()

    return {
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "customer_name": invoice.customer_name,
            "customer_email": invoice.customer_email,
            "customer_address": invoice.customer_address,
            "customer_tax_id": invoice.customer_tax_id,
            "status": invoice.status,
            "invoice_type": invoice.invoice_type,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "paid_at": invoice.paid_at,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "currency": invoice.currency,
            "paid_amount": invoice.paid_amount,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        },
        "items": [
            {
                "id": item.id,
                "sku": item.sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "tax_category": item.tax_category,
                "tax_rate": item.tax_rate,
                "tax_amount": item.tax_amount,
            }
            for item in invoice_items
        ],
        "payments": [
            {
                "id": payment.id,
                "payment_id": payment.payment_id,
                "amount": payment.amount,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "processed_at": payment.processed_at,
            }
            for payment in payments
        ],
    }


@router.put("/{invoice_id}/status", response_model=dict)
async def update_invoice_status(
    invoice_id: int,
    status: InvoiceStatus,
    notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Update the status of an invoice."""
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update status
    invoice.status = status

    if status == InvoiceStatus.ISSUED:
        invoice.issued_by = current_user.id
        invoice.issued_at = datetime.now(UTC)
    elif status == InvoiceStatus.SENT:
        invoice.sent_by = current_user.id
        invoice.sent_at = datetime.now(UTC)
    elif status == InvoiceStatus.PAID:
        invoice.paid_at = datetime.now(UTC)

    if notes:
        invoice.internal_notes = notes

    await session.commit()

    return {
        "message": "Invoice status updated successfully",
        "invoice_id": invoice.id,
        "new_status": invoice.status,
    }


@router.post("/{invoice_id}/payments", response_model=dict)
async def record_invoice_payment(
    invoice_id: int,
    amount: float,
    payment_method: PaymentMethod,
    payment_reference: str | None = None,
    notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Record a payment for an invoice."""
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Generate payment ID
    payment_id = (
        "PAY-"
        f"{datetime.now().strftime('%Y%m%d')}"
        "-"
        f"{abs(hash(str(invoice_id) + str(amount))) % 10000:04d}"
    )

    # Create payment record
    payment = InvoicePayment(
        payment_id=payment_id,
        invoice_id=invoice_id,
        order_id=invoice.order_id,
        amount=amount,
        currency=invoice.currency,
        payment_method=payment_method,
        status="completed",  # Simplified for now
        notes=notes,
    )

    session.add(payment)

    # Update invoice paid amount
    invoice.paid_amount = (invoice.paid_amount or 0) + amount

    # Check if fully paid
    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now(UTC)

    await session.commit()

    return {
        "message": "Payment recorded successfully",
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "total_paid": invoice.paid_amount,
        "invoice_status": invoice.status,
    }


@router.get("/statistics", response_model=dict)
async def get_invoice_statistics(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get invoice statistics and metrics."""
    # Get counts by status
    status_counts = {}
    for status in InvoiceStatus:
        result = await session.execute(select(Invoice).where(Invoice.status == status))
        status_counts[status.value] = len(result.scalars().all())

    # Get counts by type
    type_counts = {}
    for invoice_type in InvoiceType:
        result = await session.execute(
            select(Invoice).where(Invoice.invoice_type == invoice_type),
        )
        type_counts[invoice_type.value] = len(result.scalars().all())

    # Get financial totals
    financial_result = await session.execute(
        select(Invoice.total_amount, Invoice.paid_amount, Invoice.status),
    )
    financial_data = financial_result.all()

    total_revenue = sum(row[0] for row in financial_data if row[0])
    total_paid = sum(row[1] or 0 for row in financial_data if row[1])
    outstanding_amount = total_revenue - total_paid

    # Get overdue invoices
    overdue_result = await session.execute(
        select(Invoice).where(
            and_(
                Invoice.status != InvoiceStatus.PAID,
                Invoice.due_date < datetime.now(UTC),
            ),
        ),
    )
    overdue_invoices = overdue_result.scalars().all()

    return {
        "total_invoices": sum(status_counts.values()),
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "financial_summary": {
            "total_revenue": total_revenue,
            "total_paid": total_paid,
            "outstanding_amount": outstanding_amount,
            "overdue_invoices": len(overdue_invoices),
        },
    }

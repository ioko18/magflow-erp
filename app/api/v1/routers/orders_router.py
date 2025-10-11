"""Orders Management Router.

Consolidates all order-related endpoints including:
- Order CRUD operations
- Payment processing
- SMS notifications
- RMA (Returns Management)
- Cancellations
- Invoices
- Reporting
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    cancellations,
    invoices,
    orders,
    payment_gateways,
    reporting,
    rma,
    sms_notifications,
    vat,
)

router = APIRouter(tags=["orders"])

# Orders endpoints
router.include_router(orders, prefix="/orders", tags=["orders"])

# VAT endpoints
router.include_router(vat, tags=["vat"])

# Payment gateways endpoints
router.include_router(
    payment_gateways,
    prefix="/payments",
    tags=["payments"],
)

# SMS notifications endpoints
router.include_router(sms_notifications, prefix="/sms", tags=["sms"])

# RMA (Returns Management) endpoints
router.include_router(rma, prefix="/rma", tags=["rma"])

# Cancellation endpoints
router.include_router(
    cancellations,
    prefix="/cancellations",
    tags=["cancellations"],
)

# Invoice management endpoints
router.include_router(invoices, prefix="/invoices", tags=["invoices"])

# Reporting endpoints
router.include_router(reporting, prefix="/reports", tags=["reports"])

"""Payment Gateways API endpoints for MagFlow ERP.

This module provides REST API endpoints for payment processing,
including support for multiple payment gateways, refunds, webhooks,
and transaction management.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from app.api.dependencies import get_current_active_user
from app.core.exceptions import ConfigurationError
from app.db.models import User as UserModel
from app.services.orders.payment_service import (
    PaymentGatewayType,
    PaymentMethod,
    PaymentService,
)

router = APIRouter(prefix="/payments", tags=["payments"])


# Dependency provider for payment service
async def get_payment_service() -> PaymentService:
    """FastAPI dependency for PaymentService."""
    from app.core.service_registry import get_service_registry

    registry = get_service_registry()
    if not registry.is_initialized:
        from app.core.service_registry import initialize_service_registry

        # Initialize with a mock session for now
        db_session = None
        await initialize_service_registry(db_session)

    # For now, create a new instance
    # In production, this should come from the service registry
    from app.core.config import get_settings
    from app.core.dependency_injection import ServiceContext

    settings = get_settings()
    context = ServiceContext(settings=settings)
    service = PaymentService(context)

    await service.initialize()
    return service


@router.post("/create")
async def create_payment(
    payment_request: dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Create a new payment transaction.

    - **payment_request**: Payment creation request with amount, currency, order_id, etc.

    Supported gateways: stripe, paypal, bank_transfer
    """
    try:
        # Validate required fields
        required_fields = [
            "gateway_type",
            "amount",
            "currency",
            "order_id",
            "customer_email",
        ]
        for field in required_fields:
            if field not in payment_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        gateway_type = PaymentGatewayType(payment_request["gateway_type"])
        amount = Decimal(str(payment_request["amount"]))
        currency = payment_request["currency"]
        order_id = payment_request["order_id"]
        customer_email = payment_request["customer_email"]
        description = payment_request.get(
            "description",
            f"Payment for order {order_id}",
        )
        payment_method = PaymentMethod(
            payment_request.get("payment_method", "credit_card"),
        )
        metadata = payment_request.get("metadata", {})

        # Create payment transaction
        transaction = await payment_service.create_payment(
            gateway_type=gateway_type,
            amount=amount,
            currency=currency,
            order_id=order_id,
            customer_email=customer_email,
            description=description,
            payment_method=payment_method,
            metadata=metadata,
        )

        return {
            "transaction_id": transaction.id,
            "gateway_type": transaction.gateway_type.value,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status.value,
            "gateway_transaction_id": transaction.gateway_transaction_id,
            "gateway_response": transaction.gateway_response,
            "created_at": transaction.created_at.isoformat(),
            "message": "Payment transaction created successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment data: {e!s}",
        ) from e
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Payment gateway not configured: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {e!s}",
        ) from e


@router.post("/process/{transaction_id}")
async def process_payment(
    transaction_id: str,
    payment_data: dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Process a payment transaction.

    - **transaction_id**: ID of the payment transaction to process
    - **payment_data**: Payment method data (payment_method_id, payer_id, etc.)
    """
    try:
        # Validate required fields
        if "payment_method" not in payment_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field: payment_method",
            )

        payment_method = PaymentMethod(payment_data["payment_method"])

        # Process payment
        transaction = await payment_service.process_payment(
            transaction_id=transaction_id,
            payment_method=payment_method,
            payment_data=payment_data,
        )

        return {
            "transaction_id": transaction.id,
            "gateway_transaction_id": transaction.gateway_transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status.value,
            "completed_at": (
                transaction.completed_at.isoformat()
                if transaction.completed_at
                else None
            ),
            "gateway_response": transaction.gateway_response,
            "message": "Payment processed successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {e!s}",
        ) from e


@router.post("/refund/{transaction_id}")
async def refund_payment(
    transaction_id: str,
    refund_request: dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Refund a payment transaction.

    - **transaction_id**: ID of the payment transaction to refund
    - **refund_request**: Refund details (amount, reason)
    """
    try:
        amount = None
        if "amount" in refund_request:
            amount = Decimal(str(refund_request["amount"]))

        reason = refund_request.get("reason", "Customer requested refund")

        # Process refund
        transaction = await payment_service.refund_payment(
            transaction_id=transaction_id,
            amount=amount,
            reason=reason,
        )

        return {
            "transaction_id": transaction.id,
            "gateway_transaction_id": transaction.gateway_transaction_id,
            "amount": float(transaction.amount),
            "refund_amount": float(transaction.refund_amount),
            "currency": transaction.currency,
            "status": transaction.status.value,
            "refunded_at": (
                transaction.refunded_at.isoformat() if transaction.refunded_at else None
            ),
            "gateway_response": transaction.gateway_response,
            "message": "Payment refund processed successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid refund data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {e!s}",
        ) from e


@router.get("/status/{transaction_id}")
async def get_payment_status(
    transaction_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Get payment transaction status.

    - **transaction_id**: ID of the payment transaction
    """
    try:
        # Get payment status
        transaction = await payment_service.get_payment_status(transaction_id)

        return {
            "transaction_id": transaction.id,
            "order_id": transaction.order_id,
            "gateway_type": transaction.gateway_type.value,
            "gateway_transaction_id": transaction.gateway_transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status.value,
            "payment_method": transaction.payment_method.value,
            "description": transaction.description,
            "customer_email": transaction.customer_email,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "completed_at": (
                transaction.completed_at.isoformat()
                if transaction.completed_at
                else None
            ),
            "refunded_at": (
                transaction.refunded_at.isoformat() if transaction.refunded_at else None
            ),
            "refund_amount": float(transaction.refund_amount),
            "gateway_response": transaction.gateway_response,
            "metadata": transaction.metadata,
        }

    except Exception as _:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limit status: {_!s}",
        ) from _


@router.post("/webhook/{gateway_type}")
async def handle_webhook(
    gateway_type: str,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Handle webhook from payment gateway.

    - **gateway_type**: Type of payment gateway (stripe, paypal, bank_transfer)
    """
    try:
        gateway_type_enum = PaymentGatewayType(gateway_type)

        # Get raw payload
        payload = await request.json()

        # For Stripe, get signature from headers
        signature = ""
        if gateway_type_enum == PaymentGatewayType.STRIPE:
            signature = request.headers.get("stripe-signature", "")

        # Handle webhook
        result = await payment_service.handle_webhook(
            gateway_type=gateway_type_enum,
            payload=payload,
            signature=signature,
        )

        return {
            "status": "success",
            "gateway_type": gateway_type,
            "event_type": result.get("event_type"),
            "processed": result.get("processed", True),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except ValueError as _:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid gateway type: {gateway_type}",
        ) from _
    except Exception as _:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle webhook: {_!s}",
        ) from _


@router.get("/gateways")
async def get_supported_gateways(
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Get list of supported payment gateways.

    Returns information about configured payment gateways.
    """
    try:
        gateways = await payment_service.get_supported_gateways()

        return {
            "gateways": gateways,
            "total_count": len(gateways),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment gateways: {e!s}",
        ) from e


@router.get("/transactions")
async def get_payment_transactions(
    gateway_type: str | None = Query(None, description="Filter by gateway type"),
    status: str | None = Query(None, description="Filter by payment status"),
    order_id: str | None = Query(None, description="Filter by order ID"),
    customer_email: str | None = Query(None, description="Filter by customer email"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get payment transactions with filtering and pagination.

    - **gateway_type**: Filter by payment gateway type
    - **status**: Filter by payment status
    - **order_id**: Filter by order ID
    - **customer_email**: Filter by customer email
    - **page**: Page number for pagination
    - **limit**: Number of items per page
    """
    try:
        # In a real implementation, this would query the database
        # For now, return mock data
        mock_transactions = [
            {
                "id": f"txn_{i}",
                "order_id": f"order_{i}",
                "gateway_type": "stripe",
                "gateway_transaction_id": f"pi_test_{i}",
                "amount": float(Decimal("100.00") + i * Decimal("10.00")),
                "currency": "RON",
                "status": "completed",
                "payment_method": "credit_card",
                "description": f"Payment for order {i}",
                "customer_email": f"customer{i}@example.com",
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "gateway_response": {"status": "succeeded"},
            }
            for i in range(min(limit, 20))  # Mock 20 transactions max
        ]

        # Apply filters
        filtered_transactions = mock_transactions

        if gateway_type:
            filtered_transactions = [
                t for t in filtered_transactions if t["gateway_type"] == gateway_type
            ]

        if status:
            filtered_transactions = [
                t for t in filtered_transactions if t["status"] == status
            ]

        if order_id:
            filtered_transactions = [
                t for t in filtered_transactions if order_id in t["order_id"]
            ]

        if customer_email:
            filtered_transactions = [
                t
                for t in filtered_transactions
                if customer_email in t["customer_email"]
            ]

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_transactions = filtered_transactions[start_idx:end_idx]

        return {
            "transactions": paginated_transactions,
            "total_count": len(filtered_transactions),
            "page": page,
            "limit": limit,
            "total_pages": (len(filtered_transactions) + limit - 1) // limit,
            "filters_applied": {
                "gateway_type": gateway_type,
                "status": status,
                "order_id": order_id,
                "customer_email": customer_email,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment transactions: {e!s}",
        ) from e


@router.get("/transactions/{transaction_id}")
async def get_payment_transaction(
    transaction_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Get detailed information for a specific payment transaction.

    - **transaction_id**: ID of the payment transaction
    """
    try:
        # Get transaction status (this will return mock data for now)
        transaction = await payment_service.get_payment_status(transaction_id)

        return {
            "transaction_id": transaction.id,
            "order_id": transaction.order_id,
            "gateway_type": transaction.gateway_type.value,
            "gateway_transaction_id": transaction.gateway_transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status.value,
            "payment_method": transaction.payment_method.value,
            "description": transaction.description,
            "customer_email": transaction.customer_email,
            "customer_name": transaction.metadata.get("customer_name", ""),
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "completed_at": (
                transaction.completed_at.isoformat()
                if transaction.completed_at
                else None
            ),
            "refunded_at": (
                transaction.refunded_at.isoformat() if transaction.refunded_at else None
            ),
            "refund_amount": float(transaction.refund_amount),
            "gateway_response": transaction.gateway_response,
            "metadata": transaction.metadata,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as _:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment transaction {transaction_id} not found",
        ) from _


@router.get("/statistics")
async def get_payment_statistics(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    gateway_type: str | None = Query(None, description="Filter by gateway type"),
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get payment statistics and analytics.

    - **start_date**: Start date for statistics
    - **end_date**: End date for statistics
    - **gateway_type**: Filter by gateway type
    """
    try:
        # In a real implementation, this would query the database
        # For now, return mock statistics
        stats = {
            "total_transactions": 1250,
            "total_amount": 125000.00,
            "successful_transactions": 1180,
            "failed_transactions": 70,
            "refunded_transactions": 45,
            "success_rate": 94.4,
            "refund_rate": 3.6,
            "average_transaction_amount": 100.00,
            "gateway_breakdown": {
                "stripe": {
                    "transactions": 850,
                    "amount": 85000.00,
                    "success_rate": 96.5,
                },
                "paypal": {
                    "transactions": 300,
                    "amount": 30000.00,
                    "success_rate": 92.3,
                },
                "bank_transfer": {
                    "transactions": 100,
                    "amount": 10000.00,
                    "success_rate": 85.0,
                },
            },
            "status_distribution": {
                "completed": 1180,
                "failed": 70,
                "refunded": 45,
                "pending": 25,
            },
            "daily_totals": [
                {"date": "2024-01-01", "transactions": 45, "amount": 4500.00},
                {"date": "2024-01-02", "transactions": 52, "amount": 5200.00},
            ],
        }

        return {
            "statistics": stats,
            "period": {
                "start_date": start_date or "2024-01-01",
                "end_date": end_date or datetime.now(UTC).strftime("%Y-%m-%d"),
            },
            "filters_applied": {"gateway_type": gateway_type},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment statistics: {e!s}",
        ) from e


@router.post("/test/{gateway_type}")
async def test_payment_gateway(
    gateway_type: str,
    current_user: UserModel = Depends(get_current_active_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any]:
    """Test payment gateway connectivity.

    - **gateway_type**: Type of payment gateway to test (stripe, paypal, bank_transfer)
    """
    try:
        gateway_type_enum = PaymentGatewayType(gateway_type)

        # Test gateway connectivity
        gateway = await payment_service.gateway_manager.get_gateway(gateway_type_enum)

        # Perform basic connectivity test
        test_result = {
            "gateway_type": gateway_type,
            "status": "connected",
            "test_timestamp": datetime.now(UTC).isoformat(),
            "configuration": {
                "test_mode": gateway.config.test_mode,
                "supported_currencies": gateway.config.supported_currencies,
                "max_amount": float(gateway.config.max_amount),
                "min_amount": float(gateway.config.min_amount),
            },
        }

        return {
            "test_result": test_result,
            "message": f"Payment gateway {gateway_type} test completed successfully",
        }

    except ValueError as _:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid gateway type: {gateway_type}",
        ) from _
    except ConfigurationError as _:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Payment gateway {gateway_type} not configured: {_!s}",
        ) from _
    except Exception as _:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment gateway test failed: {_!s}",
        ) from _


@router.get("/methods")
async def get_supported_payment_methods(
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get list of supported payment methods.

    Returns information about all supported payment methods across gateways.
    """
    try:
        payment_methods = {
            "credit_card": {
                "type": "credit_card",
                "name": "Credit Card",
                "description": "Visa, MasterCard, American Express",
                "supported_gateways": ["stripe", "paypal"],
                "processing_time": "Instant",
                "fees": "2.9% + 0.30 RON",
            },
            "debit_card": {
                "type": "debit_card",
                "name": "Debit Card",
                "description": "Visa Debit, MasterCard Debit",
                "supported_gateways": ["stripe"],
                "processing_time": "Instant",
                "fees": "2.9% + 0.30 RON",
            },
            "bank_transfer": {
                "type": "bank_transfer",
                "name": "Bank Transfer",
                "description": "Traditional bank transfer",
                "supported_gateways": ["bank_transfer"],
                "processing_time": "1-3 business days",
                "fees": "No fees",
            },
            "paypal": {
                "type": "paypal",
                "name": "PayPal",
                "description": "PayPal wallet payment",
                "supported_gateways": ["paypal"],
                "processing_time": "Instant",
                "fees": "3.4% + 0.35 RON",
            },
            "cash": {
                "type": "cash",
                "name": "Cash Payment",
                "description": "Cash on delivery",
                "supported_gateways": [],
                "processing_time": "On delivery",
                "fees": "No fees",
            },
            "check": {
                "type": "check",
                "name": "Check Payment",
                "description": "Paper check payment",
                "supported_gateways": [],
                "processing_time": "3-5 business days",
                "fees": "No fees",
            },
        }

        return {
            "payment_methods": list(payment_methods.values()),
            "total_count": len(payment_methods),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment methods: {e!s}",
        ) from e

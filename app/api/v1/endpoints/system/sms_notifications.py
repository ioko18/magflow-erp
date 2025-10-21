"""SMS Notifications API endpoints for MagFlow ERP.

This module provides REST API endpoints for SMS notification management,
including sending messages, checking status, and managing templates.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user
from app.core.exceptions import ConfigurationError
from app.db.models import User as UserModel
from app.services.communication.sms_service import (
    NotificationType,
    SMSProvider,
    SMSService,
)

router = APIRouter(prefix="/sms", tags=["sms"])


# Dependency provider for SMS service
async def get_sms_service() -> SMSService:
    """FastAPI dependency for SMSService."""
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
    service = SMSService(context)

    await service.initialize()
    return service


@router.post("/send")
async def send_sms(
    sms_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send SMS message.

    - **sms_request**: SMS request with phone_number, message, provider, etc.

    Supported providers: twilio, messagebird
    """
    try:
        # Validate required fields
        required_fields = ["phone_number", "message"]
        for field in required_fields:
            if field not in sms_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = sms_request["phone_number"]
        message = sms_request["message"]
        provider = SMSProvider(sms_request.get("provider", "twilio"))
        notification_type = NotificationType(
            sms_request.get("notification_type", "custom"),
        )

        # Send SMS (background task)
        background_tasks.add_task(
            sms_service.send_sms,
            phone_number=phone_number,
            message=message,
            provider=provider,
            notification_type=notification_type,
        )

        return {
            "message_id": "queued",  # Would be actual ID in real implementation
            "phone_number": phone_number,
            "status": "queued",
            "provider": provider,
            "message": "SMS queued for sending",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SMS data: {e!s}",
        ) from e
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SMS service not configured: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SMS: {e!s}",
        ) from e


@router.post("/send/order-confirmation")
async def send_order_confirmation_sms(
    confirmation_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send order confirmation SMS.

    - **confirmation_request**: Order confirmation details
    """
    try:
        # Validate required fields
        required_fields = ["phone_number", "order_id", "amount"]
        for field in required_fields:
            if field not in confirmation_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = confirmation_request["phone_number"]
        order_id = confirmation_request["order_id"]
        amount = Decimal(str(confirmation_request["amount"]))
        currency = confirmation_request.get("currency", "RON")
        tracking_url = confirmation_request.get("tracking_url")
        language = confirmation_request.get("language", "en")

        # Send order confirmation SMS
        background_tasks.add_task(
            sms_service.send_order_confirmation,
            phone_number=phone_number,
            order_id=order_id,
            amount=amount,
            currency=currency,
            tracking_url=tracking_url,
            language=language,
        )

        return {
            "message_id": "queued",
            "phone_number": phone_number,
            "order_id": order_id,
            "status": "queued",
            "message": "Order confirmation SMS queued for sending",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order confirmation data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send order confirmation SMS: {e!s}",
        ) from e


@router.post("/send/order-shipped")
async def send_order_shipped_sms(
    shipped_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send order shipped SMS.

    - **shipped_request**: Order shipping details
    """
    try:
        # Validate required fields
        required_fields = ["phone_number", "order_id", "delivery_date", "tracking_url"]
        for field in required_fields:
            if field not in shipped_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = shipped_request["phone_number"]
        order_id = shipped_request["order_id"]
        delivery_date = shipped_request["delivery_date"]
        tracking_url = shipped_request["tracking_url"]
        language = shipped_request.get("language", "en")

        # Send order shipped SMS
        background_tasks.add_task(
            sms_service.send_order_shipped,
            phone_number=phone_number,
            order_id=order_id,
            delivery_date=delivery_date,
            tracking_url=tracking_url,
            language=language,
        )

        return {
            "message_id": "queued",
            "phone_number": phone_number,
            "order_id": order_id,
            "status": "queued",
            "message": "Order shipped SMS queued for sending",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid shipping data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send order shipped SMS: {e!s}",
        ) from e


@router.post("/send/payment-confirmation")
async def send_payment_confirmation_sms(
    payment_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send payment confirmation SMS.

    - **payment_request**: Payment confirmation details
    """
    try:
        # Validate required fields
        required_fields = ["phone_number", "order_id", "amount"]
        for field in required_fields:
            if field not in payment_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = payment_request["phone_number"]
        order_id = payment_request["order_id"]
        amount = Decimal(str(payment_request["amount"]))
        currency = payment_request.get("currency", "RON")
        language = payment_request.get("language", "en")

        # Send payment confirmation SMS
        background_tasks.add_task(
            sms_service.send_payment_confirmation,
            phone_number=phone_number,
            order_id=order_id,
            amount=amount,
            currency=currency,
            language=language,
        )

        return {
            "message_id": "queued",
            "phone_number": phone_number,
            "order_id": order_id,
            "status": "queued",
            "message": "Payment confirmation SMS queued for sending",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send payment confirmation SMS: {e!s}",
        ) from e


@router.post("/send/inventory-alert")
async def send_inventory_alert_sms(
    alert_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send low inventory alert SMS.

    - **alert_request**: Inventory alert details
    """
    try:
        # Validate required fields
        required_fields = ["phone_number", "product_name", "quantity"]
        for field in required_fields:
            if field not in alert_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = alert_request["phone_number"]
        product_name = alert_request["product_name"]
        quantity = alert_request["quantity"]
        language = alert_request.get("language", "en")

        # Send inventory alert SMS
        background_tasks.add_task(
            sms_service.send_inventory_alert,
            phone_number=phone_number,
            product_name=product_name,
            quantity=quantity,
            language=language,
        )

        return {
            "message_id": "queued",
            "phone_number": phone_number,
            "product_name": product_name,
            "status": "queued",
            "message": "Inventory alert SMS queued for sending",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid alert data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send inventory alert SMS: {e!s}",
        ) from e


@router.post("/send/bulk")
async def send_bulk_sms(
    bulk_request: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Send bulk SMS messages.

    - **bulk_request**: Bulk SMS request with recipients and message
    """
    try:
        # Validate required fields
        required_fields = ["phone_numbers", "message"]
        for field in required_fields:
            if field not in bulk_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_numbers = bulk_request["phone_numbers"]
        message = bulk_request["message"]
        provider = SMSProvider(bulk_request.get("provider", "twilio"))
        notification_type = NotificationType(
            bulk_request.get("notification_type", "custom"),
        )

        if not isinstance(phone_numbers, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="phone_numbers must be a list",
            )

        if len(phone_numbers) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 recipients allowed per bulk send",
            )

        # Send bulk SMS
        background_tasks.add_task(
            sms_service.send_bulk_sms,
            phone_numbers=phone_numbers,
            message=message,
            provider=provider,
            notification_type=notification_type,
        )

        return {
            "message_id": "bulk_queued",
            "recipient_count": len(phone_numbers),
            "status": "queued",
            "message": f"Bulk SMS queued for {len(phone_numbers)} recipients",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bulk SMS data: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send bulk SMS: {e!s}",
        ) from e


@router.get("/providers")
async def get_sms_providers(
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Get list of configured SMS providers.

    Returns information about available SMS providers.
    """
    try:
        providers_info = []
        for provider, _config in sms_service.providers.items():
            status = await sms_service.get_provider_status(provider)
            providers_info.append(status)

        return {
            "providers": providers_info,
            "total_count": len(providers_info),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SMS providers: {e!s}",
        ) from e


@router.get("/statistics")
async def get_sms_statistics(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    provider: str | None = Query(None, description="Filter by provider"),
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Get SMS statistics and analytics.

    - **start_date**: Start date for statistics
    - **end_date**: End date for statistics
    - **provider**: Filter by SMS provider
    """
    try:
        statistics = await sms_service.get_statistics()

        return {
            "statistics": statistics,
            "period": {
                "start_date": start_date or "2024-01-01",
                "end_date": end_date or datetime.now(UTC).strftime("%Y-%m-%d"),
            },
            "filters_applied": {"provider": provider},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SMS statistics: {e!s}",
        ) from e


@router.get("/templates")
async def get_sms_templates(
    notification_type: str | None = Query(
        None,
        description="Filter by notification type",
    ),
    language: str = Query("en", description="Template language"),
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get SMS message templates.

    - **notification_type**: Filter by notification type
    - **language**: Template language (en, ro)
    """
    try:
        from app.services.communication.sms_service import NotificationType, SMSTemplate

        templates = {}
        for n_type in NotificationType:
            if notification_type is None or n_type.value == notification_type:
                template = SMSTemplate.get_template(n_type, language)
                templates[n_type.value] = {
                    "type": n_type.value,
                    "template": template,
                    "language": language,
                    "max_length": 160,
                }

        return {
            "templates": templates,
            "language": language,
            "total_count": len(templates),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SMS templates: {e!s}",
        ) from e


@router.post("/templates/preview")
async def preview_sms_template(
    template_request: dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Preview SMS template with variables.

    - **template_request**: Template preview request with type and variables
    """
    try:
        from app.services.communication.sms_service import NotificationType, SMSTemplate

        # Validate required fields
        required_fields = ["notification_type", "variables"]
        for field in required_fields:
            if field not in template_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        notification_type = NotificationType(template_request["notification_type"])
        variables = template_request["variables"]
        language = template_request.get("language", "en")

        # Format message
        message = SMSTemplate.format_message(notification_type, variables, language)

        return {
            "notification_type": notification_type.value,
            "language": language,
            "variables": variables,
            "formatted_message": message,
            "message_length": len(message),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template request: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview SMS template: {e!s}",
        ) from e


@router.get("/countries")
async def get_supported_countries(
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get list of supported countries for SMS.

    Returns information about countries supported by SMS providers.
    """
    try:
        # Supported countries by various providers
        supported_countries = {
            "RO": {
                "name": "Romania",
                "code": "+40",
                "providers": ["twilio", "messagebird"],
            },
            "US": {
                "name": "United States",
                "code": "+1",
                "providers": ["twilio", "messagebird"],
            },
            "UK": {
                "name": "United Kingdom",
                "code": "+44",
                "providers": ["twilio", "messagebird"],
            },
            "DE": {
                "name": "Germany",
                "code": "+49",
                "providers": ["twilio", "messagebird"],
            },
            "FR": {
                "name": "France",
                "code": "+33",
                "providers": ["twilio", "messagebird"],
            },
            "IT": {
                "name": "Italy",
                "code": "+39",
                "providers": ["twilio", "messagebird"],
            },
            "ES": {
                "name": "Spain",
                "code": "+34",
                "providers": ["twilio", "messagebird"],
            },
            "NL": {
                "name": "Netherlands",
                "code": "+31",
                "providers": ["twilio", "messagebird"],
            },
            "BE": {
                "name": "Belgium",
                "code": "+32",
                "providers": ["twilio", "messagebird"],
            },
            "AT": {
                "name": "Austria",
                "code": "+43",
                "providers": ["twilio", "messagebird"],
            },
        }

        return {
            "countries": supported_countries,
            "total_count": len(supported_countries),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported countries: {e!s}",
        ) from e


@router.post("/test")
async def test_sms_service(
    test_request: dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    sms_service: SMSService = Depends(get_sms_service),
) -> dict[str, Any]:
    """Test SMS service connectivity.

    - **test_request**: Test request with phone number and provider
    """
    try:
        # Validate required fields
        required_fields = ["phone_number"]
        for field in required_fields:
            if field not in test_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        phone_number = test_request["phone_number"]
        provider = SMSProvider(test_request.get("provider", "twilio"))
        message = test_request.get("message", "Test SMS from MagFlow ERP")

        # Send test SMS
        await sms_service.send_sms(
            phone_number=phone_number,
            message=message,
            provider=provider,
            notification_type=NotificationType.CUSTOM,
        )

        return {
            "test_result": {
                "phone_number": phone_number,
                "provider": provider,
                "message": message,
                "status": "queued",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "message": "SMS test completed successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid test request: {e!s}",
        ) from e
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SMS service not configured: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SMS test failed: {e!s}",
        ) from e

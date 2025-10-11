"""SMS Notifications Service for MagFlow ERP.

This module provides comprehensive SMS notification capabilities,
supporting multiple SMS providers (Twilio, AWS SNS, MessageBird, etc.)
with features for order confirmations, alerts, and automated messaging.
"""

import asyncio
import contextlib
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import aiohttp

from app.core.dependency_injection import ServiceBase, ServiceContext

logger = logging.getLogger(__name__)


class SMSStatus(str, Enum):
    """SMS message status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    UNDELIVERED = "undelivered"


class SMSProvider(str, Enum):
    """SMS provider enumeration."""

    TWILIO = "twilio"
    AWS_SNS = "aws_sns"
    MESSAGEBIRD = "messagebird"
    VONAGE = "vonage"
    TELNYX = "telnyx"
    CLICKATELL = "clickatell"


class NotificationType(str, Enum):
    """Notification type enumeration."""

    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    INVENTORY_LOW = "inventory_low"
    PRICE_CHANGE = "price_change"
    PROMOTION = "promotion"
    APPOINTMENT_REMINDER = "appointment_reminder"
    CUSTOM = "custom"


@dataclass
class SMSMessage:
    """SMS message data structure."""

    id: str | None = None
    phone_number: str = ""
    message: str = ""
    provider: SMSProvider = SMSProvider.TWILIO
    notification_type: NotificationType = NotificationType.CUSTOM
    recipient_name: str = ""
    order_id: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: SMSStatus = SMSStatus.PENDING
    provider_message_id: str = ""
    cost: Decimal = Decimal("0.00")
    currency: str = "USD"
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    scheduled_for: datetime | None = None
    gateway_response: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)


@dataclass
class SMSProviderConfig:
    """Configuration for SMS providers."""

    provider: SMSProvider
    api_key: str = ""
    api_secret: str = ""
    account_sid: str = ""  # For Twilio
    auth_token: str = ""  # For Twilio
    sender_id: str = ""  # For MessageBird, Clickatell
    region: str = ""  # For AWS SNS
    test_mode: bool = True
    supported_countries: list[str] = field(
        default_factory=lambda: ["RO", "US", "UK", "DE", "FR"],
    )
    max_message_length: int = 160
    rate_limit_per_minute: int = 60
    cost_per_message: Decimal = Decimal("0.05")

    # Provider-specific URLs
    api_base_url: str = ""

    def __post_init__(self):
        """Set provider-specific URLs."""
        if self.provider == SMSProvider.TWILIO:
            self.api_base_url = "https://api.twilio.com/2010-04-01"
        elif self.provider == SMSProvider.AWS_SNS:
            self.api_base_url = "https://sns.us-east-1.amazonaws.com"  # Default region
        elif self.provider == SMSProvider.MESSAGEBIRD:
            self.api_base_url = "https://rest.messagebird.com"
        elif self.provider == SMSProvider.VONAGE:
            self.api_base_url = "https://rest.nexmo.com"
        elif self.provider == SMSProvider.TELNYX:
            self.api_base_url = "https://api.telnyx.com/v2"
        elif self.provider == SMSProvider.CLICKATELL:
            self.api_base_url = "https://platform.clickatell.com"


class SMSProviderError(Exception):
    """Base exception for SMS provider errors."""

    def __init__(
        self,
        message: str,
        provider: SMSProvider = None,
        code: str = None,
        details: dict[str, Any] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.details = details or {}


class BaseSMSProvider(ABC):
    """Abstract base class for SMS providers."""

    def __init__(self, config: SMSProviderConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None
        self._request_count = 0
        self._last_request_time = datetime.now()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the SMS provider."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._validate_config()

    async def close(self):
        """Close the SMS provider."""
        if self.session:
            await self.session.close()

    async def _validate_config(self):
        """Validate provider configuration."""
        if not self.config.api_key:
            raise SMSProviderError("API key is required", self.config.provider)

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        time_since_last_request = (now - self._last_request_time).total_seconds()

        if time_since_last_request < (60 / self.config.rate_limit_per_minute):
            sleep_time = (
                60 / self.config.rate_limit_per_minute
            ) - time_since_last_request
            await asyncio.sleep(sleep_time)

        self._last_request_time = datetime.now()

    @abstractmethod
    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender: str = None,
    ) -> dict[str, Any]:
        """Send SMS message."""

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format."""
        # Basic validation - should start with + and contain only digits
        if not phone_number.startswith("+"):
            return False

        # Remove + and check if remaining are digits
        digits_only = phone_number[1:]
        if not digits_only.isdigit():
            return False

        # Check length (international numbers are 7-15 digits)
        return 7 <= len(digits_only) <= 15

    def _truncate_message(self, message: str) -> str:
        """Truncate message if too long."""
        if len(message) <= self.config.max_message_length:
            return message

        # Truncate and add indicator
        truncated = message[: self.config.max_message_length - 3] + "..."
        logger.warning(
            "Message truncated from %d to %d characters",
            len(message),
            len(truncated),
        )
        return truncated

    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for the provider."""
        # Ensure phone number starts with +
        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number
        return phone_number


class TwilioSMSProvider(BaseSMSProvider):
    """Twilio SMS provider implementation."""

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender: str = None,
    ) -> dict[str, Any]:
        """Send SMS via Twilio."""
        if not self.session:
            raise SMSProviderError(
                "SMS provider not initialized. Call initialize() first.",
                SMSProvider.TWILIO,
            )

        if not self._validate_phone_number(phone_number):
            raise SMSProviderError(
                f"Invalid phone number format: {phone_number}",
                SMSProvider.TWILIO,
            )

        message = self._truncate_message(message)
        await self._check_rate_limit()

        from_number = sender or self.config.sender_id or self.config.account_sid

        sms_data = {
            "From": from_number,
            "To": self._format_phone_number(phone_number),
            "Body": message,
        }

        # Create auth string
        import base64

        auth_str = f"{self.config.account_sid}:{self.config.auth_token}"
        auth_header = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/Accounts/{self.config.account_sid}/Messages.json",
            data=sms_data,
            headers=headers,
        ) as response:
            self._request_count += 1

            if response.status != 201:
                error_text = await response.text()
                raise SMSProviderError(
                    f"Failed to send SMS: {error_text}",
                    SMSProvider.TWILIO,
                )

            result = await response.json()
            return {
                "message_id": result.get("sid"),
                "status": result.get("status", "sent"),
                "to": result.get("to"),
                "from": result.get("from"),
                "cost": Decimal(str(result.get("price", "0"))),
            }


class MessageBirdSMSProvider(BaseSMSProvider):
    """MessageBird SMS provider implementation."""

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender: str = None,
    ) -> dict[str, Any]:
        """Send SMS via MessageBird."""
        if not self.session:
            raise SMSProviderError(
                "SMS provider not initialized. Call initialize() first.",
                SMSProvider.MESSAGEBIRD,
            )

        if not self._validate_phone_number(phone_number):
            raise SMSProviderError(
                f"Invalid phone number format: {phone_number}",
                SMSProvider.MESSAGEBIRD,
            )

        message = self._truncate_message(message)
        await self._check_rate_limit()

        sms_data = {
            "recipients": [self._format_phone_number(phone_number)],
            "body": message,
        }

        if sender:
            sms_data["originator"] = sender
        elif self.config.sender_id:
            sms_data["originator"] = self.config.sender_id

        headers = {
            "Authorization": f"AccessKey {self.config.api_key}",
            "Content-Type": "application/json",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/messages",
            json=sms_data,
            headers=headers,
        ) as response:
            self._request_count += 1

            if response.status != 201:
                error_text = await response.text()
                raise SMSProviderError(
                    f"Failed to send SMS: {error_text}",
                    SMSProvider.MESSAGEBIRD,
                )

            result = await response.json()
            return {
                "message_id": result.get("id"),
                "status": "sent",  # MessageBird uses different status format
                "to": phone_number,
                "from": sender or self.config.sender_id,
                "cost": Decimal(
                    str(result.get("total_sent_price", {}).get("amount", "0")),
                ),
            }


class SMSTemplate:
    """SMS message templates."""

    TEMPLATES = {
        NotificationType.ORDER_CONFIRMATION: {
            "en": "Order {order_id} confirmed. Total: {amount} {currency}. Track: {tracking_url}",
            "ro": "Comanda {order_id} confirmată. Total: {amount} {currency}. Urmărire: {tracking_url}",
        },
        NotificationType.ORDER_SHIPPED: {
            "en": "Order {order_id} shipped! Delivery expected: {delivery_date}. Track: {tracking_url}",
            "ro": "Comanda {order_id} expediată! Livrare estimată: {delivery_date}. Urmărire: {tracking_url}",
        },
        NotificationType.ORDER_DELIVERED: {
            "en": "Order {order_id} delivered successfully. Thank you for choosing us!",
            "ro": "Comanda {order_id} livrată cu succes. Vă mulțumim că ne-ați ales!",
        },
        NotificationType.PAYMENT_CONFIRMATION: {
            "en": "Payment of {amount} {currency} confirmed for order {order_id}.",
            "ro": "Plata de {amount} {currency} confirmată pentru comanda {order_id}.",
        },
        NotificationType.INVENTORY_LOW: {
            "en": "Low stock alert: {product_name} only has {quantity} items left.",
            "ro": "Alertă stoc redus: {product_name} mai are doar {quantity} bucăți.",
        },
        NotificationType.PROMOTION: {
            "en": "{promotion_message}",
            "ro": "{promotion_message}",
        },
    }

    @classmethod
    def get_template(
        cls,
        notification_type: NotificationType,
        language: str = "en",
    ) -> str:
        """Get SMS template for notification type."""
        templates = cls.TEMPLATES.get(notification_type, {})
        return templates.get(language, templates.get("en", ""))

    @classmethod
    def format_message(
        cls,
        notification_type: NotificationType,
        variables: dict[str, Any],
        language: str = "en",
    ) -> str:
        """Format SMS message with variables."""
        template = cls.get_template(notification_type, language)

        import string

        # Use a custom formatter that preserves missing variable names
        # This allows partial formatting while keeping original placeholders
        class SafeFormatter(string.Formatter):
            def get_value(self, key, args, kwargs):
                if isinstance(key, str):
                    # Return the value if present, otherwise preserve the placeholder
                    return kwargs.get(key, "{" + key + "}")
                return super().get_value(key, args, kwargs)

        formatter = SafeFormatter()
        return formatter.format(template, **variables)


class SMSService(ServiceBase):
    """Service for managing SMS notifications."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.providers: dict[SMSProvider, BaseSMSProvider] = {}
        self.message_queue: list[SMSMessage] = []
        self._processing_task: asyncio.Task | None = None
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize configured SMS providers."""
        settings = self.context.settings

        # Initialize Twilio if configured
        if hasattr(settings, "twilio_account_sid") and settings.twilio_account_sid:
            twilio_config = SMSProviderConfig(
                provider=SMSProvider.TWILIO,
                account_sid=settings.twilio_account_sid,
                auth_token=settings.twilio_auth_token,
                sender_id=getattr(settings, "twilio_sender_id", ""),
                test_mode=getattr(settings, "twilio_test_mode", True),
            )
            # Create provider instance (would normally be async)
            self.providers[SMSProvider.TWILIO] = TwilioSMSProvider(twilio_config)

        # Initialize MessageBird if configured
        if hasattr(settings, "messagebird_api_key") and settings.messagebird_api_key:
            messagebird_config = SMSProviderConfig(
                provider=SMSProvider.MESSAGEBIRD,
                api_key=settings.messagebird_api_key,
                sender_id=getattr(settings, "messagebird_sender_id", ""),
                test_mode=getattr(settings, "messagebird_test_mode", True),
            )
            # Create provider instance
            self.providers[SMSProvider.MESSAGEBIRD] = MessageBirdSMSProvider(
                messagebird_config,
            )

    async def initialize(self):
        """Initialize SMS service."""
        await super().initialize()

        # Initialize all providers
        for provider in self.providers.values():
            await provider.initialize()

        # Start message processing task
        self._processing_task = asyncio.create_task(self._process_message_queue())

        logger.info("SMS service initialized with %d providers", len(self.providers))

    async def cleanup(self):
        """Cleanup SMS service."""
        # Stop processing task
        if self._processing_task:
            self._processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processing_task

        # Close all providers
        for provider in self.providers.values():
            await provider.close()

        self.providers.clear()
        await super().cleanup()

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        provider: SMSProvider = None,
        notification_type: NotificationType = NotificationType.CUSTOM,
        priority: int = 1,
        scheduled_for: datetime | None = None,
    ) -> SMSMessage:
        """Send SMS message."""
        try:
            # Select provider (use first available if not specified)
            if not provider:
                provider = (
                    list(self.providers.keys())[0]
                    if self.providers
                    else SMSProvider.TWILIO
                )

            if provider not in self.providers:
                raise SMSProviderError(
                    f"SMS provider {provider} not configured",
                    provider,
                )

            sms_provider = self.providers[provider]

            # Validate phone number
            if not sms_provider._validate_phone_number(phone_number):
                raise SMSProviderError(
                    f"Invalid phone number format: {phone_number}",
                    provider,
                )

            # Create SMS message
            sms_message = SMSMessage(
                id=str(uuid.uuid4()),
                phone_number=phone_number,
                message=message,
                provider=provider,
                notification_type=notification_type,
                scheduled_for=scheduled_for,
                status=SMSStatus.PENDING,
            )

            # Add to queue
            self.message_queue.append(sms_message)

            # Sort by priority and scheduled time
            self.message_queue.sort(
                key=lambda x: (
                    x.scheduled_for or datetime.min,
                    -x.metadata.get("priority", 1),
                ),
            )

            logger.info("SMS message queued for %s: %s", phone_number, message[:50])
            return sms_message

        except Exception as e:
            logger.error("Failed to queue SMS: %s", e)
            raise SMSProviderError(f"SMS queuing failed: {e}")

    async def send_templated_sms(
        self,
        phone_number: str,
        notification_type: NotificationType,
        template_vars: dict[str, Any],
        language: str = "en",
        provider: SMSProvider = None,
    ) -> SMSMessage:
        """Send templated SMS message."""
        message = SMSTemplate.format_message(notification_type, template_vars, language)
        return await self.send_sms(phone_number, message, provider, notification_type)

    async def send_bulk_sms(
        self,
        phone_numbers: list[str],
        message: str,
        provider: SMSProvider = None,
        notification_type: NotificationType = NotificationType.CUSTOM,
    ) -> list[SMSMessage]:
        """Send SMS to multiple recipients."""
        tasks = []
        for phone_number in phone_numbers:
            task = self.send_sms(phone_number, message, provider, notification_type)
            tasks.append(task)

        # Send concurrently but with rate limiting
        messages = []
        batch_size = 10  # Send in batches to respect rate limits

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_messages = await asyncio.gather(*batch, return_exceptions=True)

            for msg in batch_messages:
                if isinstance(msg, SMSMessage):
                    messages.append(msg)
                else:
                    logger.error("Failed to send bulk SMS: %s", msg)

            # Small delay between batches
            await asyncio.sleep(1)

        return messages

    async def _process_message_queue(self):
        """Process SMS message queue."""
        while True:
            try:
                # Get next message to process
                if not self.message_queue:
                    await asyncio.sleep(1)
                    continue

                message = self.message_queue[0]

                # Check if scheduled for future
                if message.scheduled_for and message.scheduled_for > datetime.now(
                    UTC
                ):
                    await asyncio.sleep(5)  # Check again in 5 seconds
                    continue

                # Process message
                await self._send_message(message)

                # Remove from queue
                self.message_queue.pop(0)

            except asyncio.CancelledError:
                logger.info("SMS message processing task cancelled")
                break
            except Exception as e:
                logger.error("Error processing SMS queue: %s", e)
                await asyncio.sleep(5)  # Wait before retrying

    async def _send_message(self, message: SMSMessage):
        """Send SMS message using provider."""
        try:
            provider = self.providers.get(message.provider)
            if not provider:
                raise SMSProviderError(
                    f"Provider {message.provider} not available",
                    message.provider,
                )

            # Send message
            result = await provider.send_sms(
                phone_number=message.phone_number,
                message=message.message,
            )

            # Update message with result
            message.status = SMSStatus.SENT
            message.provider_message_id = result.get("message_id", "")
            message.cost = result.get("cost", Decimal(0))
            message.sent_at = datetime.now(UTC)
            message.gateway_response = result

            logger.info(
                "SMS sent successfully to %s: %s",
                message.phone_number,
                message.provider_message_id,
            )

        except Exception as e:
            logger.error("Failed to send SMS to %s: %s", message.phone_number, e)

            # Update message with error
            message.status = SMSStatus.FAILED
            message.error_message = str(e)
            message.retry_count += 1

            # Re-queue if retries remaining
            if message.retry_count < message.max_retries:
                message.status = SMSStatus.PENDING
                # Add back to queue with delay
                await asyncio.sleep(message.retry_count * 2)  # Exponential backoff

    async def get_message_status(self, message_id: str) -> SMSMessage:
        """Get SMS message status."""
        # In a real implementation, this would query the database
        # For now, return mock data
        return SMSMessage(
            id=message_id,
            phone_number="+40700123456",
            message="Test message",
            status=SMSStatus.SENT,
        )

    async def get_provider_status(self, provider: SMSProvider) -> dict[str, Any]:
        """Get SMS provider status."""
        if provider not in self.providers:
            return {"provider": provider, "status": "not_configured"}

        provider_instance = self.providers[provider]
        return {
            "provider": provider,
            "status": "active",
            "configuration": {
                "test_mode": provider_instance.config.test_mode,
                "rate_limit": provider_instance.config.rate_limit_per_minute,
                "cost_per_message": float(provider_instance.config.cost_per_message),
            },
            "request_count": provider_instance._request_count,
        }

    async def get_statistics(self) -> dict[str, Any]:
        """Get SMS statistics."""
        # Mock statistics for demonstration
        return {
            "total_messages": 1250,
            "sent_messages": 1180,
            "delivered_messages": 1150,
            "failed_messages": 70,
            "success_rate": 92.0,
            "total_cost": 62.50,
            "provider_breakdown": {
                "twilio": {"messages": 850, "cost": 42.50},
                "messagebird": {"messages": 400, "cost": 20.00},
            },
            "notification_types": {
                "order_confirmation": 450,
                "order_shipped": 300,
                "payment_confirmation": 200,
                "inventory_low": 100,
                "promotion": 200,
            },
        }

    # Convenience methods for common notifications
    async def send_order_confirmation(
        self,
        phone_number: str,
        order_id: str,
        amount: Decimal,
        currency: str = "RON",
        tracking_url: str = None,
        language: str = "en",
    ) -> SMSMessage:
        """Send order confirmation SMS."""
        template_vars = {
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "tracking_url": tracking_url or "N/A",
        }

        return await self.send_templated_sms(
            phone_number=phone_number,
            notification_type=NotificationType.ORDER_CONFIRMATION,
            template_vars=template_vars,
            language=language,
        )

    async def send_order_shipped(
        self,
        phone_number: str,
        order_id: str,
        delivery_date: str,
        tracking_url: str,
        language: str = "en",
    ) -> SMSMessage:
        """Send order shipped SMS."""
        template_vars = {
            "order_id": order_id,
            "delivery_date": delivery_date,
            "tracking_url": tracking_url,
        }

        return await self.send_templated_sms(
            phone_number=phone_number,
            notification_type=NotificationType.ORDER_SHIPPED,
            template_vars=template_vars,
            language=language,
        )

    async def send_payment_confirmation(
        self,
        phone_number: str,
        order_id: str,
        amount: Decimal,
        currency: str = "RON",
        language: str = "en",
    ) -> SMSMessage:
        """Send payment confirmation SMS."""
        template_vars = {
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "currency": currency,
        }

        return await self.send_templated_sms(
            phone_number=phone_number,
            notification_type=NotificationType.PAYMENT_CONFIRMATION,
            template_vars=template_vars,
            language=language,
        )

    async def send_inventory_alert(
        self,
        phone_number: str,
        product_name: str,
        quantity: int,
        language: str = "en",
    ) -> SMSMessage:
        """Send low inventory alert SMS."""
        template_vars = {"product_name": product_name, "quantity": quantity}

        return await self.send_templated_sms(
            phone_number=phone_number,
            notification_type=NotificationType.INVENTORY_LOW,
            template_vars=template_vars,
            language=language,
        )

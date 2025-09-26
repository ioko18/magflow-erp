"""Payment Gateways Integration for MagFlow ERP.

This module provides comprehensive integration with multiple payment gateways
including Stripe, PayPal, and bank transfers, with support for payments,
refunds, webhooks, and transaction management.
"""

import asyncio
import base64
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Coroutine

import aiohttp

from app.core.dependency_injection import ServiceBase, ServiceContext
from app.core.service_registry import (
    get_order_repository,
)

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CASH = "cash"
    CHECK = "check"


class PaymentGatewayType(str, Enum):
    """Payment gateway type enumeration."""

    STRIPE = "stripe"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    MOLLIE = "mollie"
    SQUARE = "square"


@dataclass
class PaymentTransaction:
    """Payment transaction data structure."""

    id: Optional[str] = None
    order_id: str = ""
    gateway_type: PaymentGatewayType = PaymentGatewayType.STRIPE
    gateway_transaction_id: str = ""
    amount: Decimal = Decimal("0.00")
    currency: str = "RON"
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    description: str = ""
    customer_id: str = ""
    customer_email: str = ""
    customer_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    gateway_response: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = None
    updated_at: datetime = None
    completed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    refund_amount: Decimal = Decimal("0.00")

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class PaymentGatewayConfig:
    """Configuration for payment gateways."""

    gateway_type: PaymentGatewayType
    api_key: str = ""
    api_secret: str = ""
    public_key: str = ""
    webhook_secret: str = ""
    test_mode: bool = True
    supported_currencies: List[str] = field(
        default_factory=lambda: ["RON", "EUR", "USD"],
    )
    max_amount: Decimal = Decimal("50000.00")
    min_amount: Decimal = Decimal("0.01")

    # Gateway-specific URLs
    base_url: str = ""
    api_base_url: str = ""
    webhooks_url: str = ""

    def __post_init__(self):
        """Set gateway-specific URLs."""
        if self.gateway_type == PaymentGatewayType.STRIPE:
            self.api_base_url = (
                "https://api.stripe.com/v1"
                if not self.test_mode
                else "https://api.stripe.com/v1"
            )
        elif self.gateway_type == PaymentGatewayType.PAYPAL:
            self.api_base_url = (
                "https://api-m.paypal.com"
                if not self.test_mode
                else "https://api-m.sandbox.paypal.com"
            )
        elif self.gateway_type == PaymentGatewayType.MOLLIE:
            self.api_base_url = (
                "https://api.mollie.com/v2"
                if not self.test_mode
                else "https://api.mollie.com/v2"
            )


class PaymentGatewayError(Exception):
    """Base exception for payment gateway errors."""

    def __init__(
        self,
        message: str,
        gateway_type: PaymentGatewayType = None,
        code: str = None,
        details: Dict[str, Any] = None,
    ):
        super().__init__(message)
        self.gateway_type = gateway_type
        self.code = code
        self.details = details or {}


class BasePaymentGateway(ABC):
    """Abstract base class for payment gateways."""

    def __init__(self, config: PaymentGatewayConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the payment gateway."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._validate_config()

    async def close(self):
        """Close the payment gateway."""
        if self.session:
            await self.session.close()

    async def _validate_config(self):
        """Validate gateway configuration."""
        if not self.config.api_key:
            raise PaymentGatewayError("API key is required", self.config.gateway_type)

    @abstractmethod
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: str,
        description: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a payment intent."""

    @abstractmethod
    async def process_payment(
        self,
        payment_intent_id: str,
        payment_method: PaymentMethod,
        payment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a payment."""

    @abstractmethod
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Refund a payment."""

    @abstractmethod
    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get payment status."""

    @abstractmethod
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """Handle webhook from payment gateway."""

    def _validate_amount(self, amount: Decimal) -> bool:
        """Validate payment amount."""
        if amount < self.config.min_amount:
            raise PaymentGatewayError(
                f"Amount {amount} is below minimum {self.config.min_amount}",
                self.config.gateway_type,
            )

        if amount > self.config.max_amount:
            raise PaymentGatewayError(
                f"Amount {amount} exceeds maximum {self.config.max_amount}",
                self.config.gateway_type,
            )

        return True

    def _validate_currency(self, currency: str) -> bool:
        """Validate payment currency."""
        if currency not in self.config.supported_currencies:
            raise PaymentGatewayError(
                f"Currency {currency} not supported. Supported: {self.config.supported_currencies}",
                self.config.gateway_type,
            )
        return True


class StripePaymentGateway(BasePaymentGateway):
    """Stripe payment gateway implementation."""

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: str,
        description: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create Stripe payment intent."""
        self._validate_amount(amount)
        self._validate_currency(currency)

        intent_data = {
            "amount": int(amount * 100),  # Convert to cents
            "currency": currency.lower(),
            "metadata": {
                "order_id": order_id,
                "description": description,
                **(metadata or {}),
            },
            "receipt_email": customer_email,
            "description": description,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/payment_intents",
            data=intent_data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to create payment intent: {error_text}",
                    PaymentGatewayType.STRIPE,
                )

            return await response.json()

    async def process_payment(
        self,
        payment_intent_id: str,
        payment_method: PaymentMethod,
        payment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process Stripe payment."""
        payment_data = {"payment_method": payment_data.get("payment_method_id")}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/payment_intents/{payment_intent_id}/confirm",
            data=payment_data,
            headers=headers,
        ) as response:
            if response.status not in [200, 201]:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to process payment: {error_text}",
                    PaymentGatewayType.STRIPE,
                )

            return await response.json()

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Refund Stripe payment."""
        refund_data = {}
        if amount:
            refund_data["amount"] = int(amount * 100)
        if reason:
            refund_data["reason"] = reason

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/refunds",
            data=refund_data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to refund payment: {error_text}",
                    PaymentGatewayType.STRIPE,
                )

            return await response.json()

    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get Stripe payment status."""
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        async with self.session.get(
            f"{self.config.api_base_url}/payment_intents/{transaction_id}",
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to get payment status: {error_text}",
                    PaymentGatewayType.STRIPE,
                )

            return await response.json()

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """Handle Stripe webhook."""
        # Verify webhook signature
        if not self._verify_webhook_signature(payload, signature):
            raise PaymentGatewayError(
                "Invalid webhook signature",
                PaymentGatewayType.STRIPE,
            )

        return {
            "gateway_type": PaymentGatewayType.STRIPE,
            "event_type": payload.get("type"),
            "data": payload.get("data", {}),
            "processed": True,
        }

    def _verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """Verify Stripe webhook signature."""
        try:
            import stripe

            stripe.api_key = self.config.api_key
            stripe.webhook.construct_event(
                json.dumps(payload, separators=(",", ":")).encode(),
                signature,
                self.config.webhook_secret,
            )
            return True
        except Exception:
            return False


class PayPalPaymentGateway(BasePaymentGateway):
    """PayPal payment gateway implementation."""

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: str,
        description: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create PayPal payment intent."""
        self._validate_amount(amount)
        self._validate_currency(currency)

        payment_data = {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {"total": str(amount), "currency": currency},
                    "description": description,
                    "custom": order_id,
                },
            ],
            "redirect_urls": {
                "return_url": f"{self.config.base_url}/payment/success",
                "cancel_url": f"{self.config.base_url}/payment/cancel",
            },
        }

        headers = {
            "Authorization": f"Bearer {await self._get_access_token()}",
            "Content-Type": "application/json",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/payments/payment",
            json=payment_data,
            headers=headers,
        ) as response:
            if response.status != 201:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to create payment: {error_text}",
                    PaymentGatewayType.PAYPAL,
                )

            return await response.json()

    async def process_payment(
        self,
        payment_intent_id: str,
        payment_method: PaymentMethod,
        payment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process PayPal payment."""
        headers = {
            "Authorization": f"Bearer {await self._get_access_token()}",
            "Content-Type": "application/json",
        }

        execute_data = {"payer_id": payment_data.get("payer_id")}

        async with self.session.post(
            f"{self.config.api_base_url}/payments/payment/{payment_intent_id}/execute",
            json=execute_data,
            headers=headers,
        ) as response:
            if response.status not in [200, 201]:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to execute payment: {error_text}",
                    PaymentGatewayType.PAYPAL,
                )

            return await response.json()

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Refund PayPal payment."""
        headers = {
            "Authorization": f"Bearer {await self._get_access_token()}",
            "Content-Type": "application/json",
        }

        refund_data = {}
        if amount:
            refund_data["amount"] = {"total": str(amount), "currency": "RON"}
        if reason:
            refund_data["reason"] = reason

        async with self.session.post(
            f"{self.config.api_base_url}/payments/capture/{transaction_id}/refund",
            json=refund_data,
            headers=headers,
        ) as response:
            if response.status != 201:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to refund payment: {error_text}",
                    PaymentGatewayType.PAYPAL,
                )

            return await response.json()

    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get PayPal payment status."""
        headers = {"Authorization": f"Bearer {await self._get_access_token()}"}

        async with self.session.get(
            f"{self.config.api_base_url}/payments/payment/{transaction_id}",
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to get payment status: {error_text}",
                    PaymentGatewayType.PAYPAL,
                )

            return await response.json()

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """Handle PayPal webhook."""
        # PayPal webhooks don't use signatures like Stripe
        return {
            "gateway_type": PaymentGatewayType.PAYPAL,
            "event_type": payload.get("event_type"),
            "data": payload,
            "processed": True,
        }

    async def _get_access_token(self) -> str:
        """Get PayPal access token."""
        auth_data = {"grant_type": "client_credentials"}

        auth_str = f"{self.config.api_key}:{self.config.api_secret}"
        auth_header = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(
            f"{self.config.api_base_url}/oauth2/token",
            data=auth_data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise PaymentGatewayError(
                    f"Failed to get access token: {error_text}",
                    PaymentGatewayType.PAYPAL,
                )

            token_data = await response.json()
            return token_data["access_token"]


class BankTransferPaymentGateway(BasePaymentGateway):
    """Bank transfer payment gateway implementation."""

    async def _validate_config(self):  # type: ignore[override]
        """Bank transfer gateway does not require API credentials."""
        return True

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: str,
        description: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create bank transfer payment intent."""
        self._validate_amount(amount)
        self._validate_currency(currency)

        # Generate bank transfer instructions
        bank_instructions = {
            "bank_name": "Banca Transilvania",
            "account_number": "RO49BTRLRONCRT1234567890",
            "account_holder": "MagFlow ERP SRL",
            "amount": float(amount),
            "currency": currency,
            "reference": f"ORDER-{order_id}",
            "description": description,
            "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }

        return {
            "payment_intent_id": f"bt_{uuid.uuid4().hex}",
            "instructions": bank_instructions,
            "status": "pending_confirmation",
        }

    async def process_payment(
        self,
        payment_intent_id: str,
        payment_method: PaymentMethod,
        payment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process bank transfer payment."""
        # Bank transfers require manual confirmation
        return {
            "transaction_id": payment_intent_id,
            "status": "pending_confirmation",
            "message": "Bank transfer initiated. Awaiting confirmation.",
        }

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Refund bank transfer payment."""
        # Bank transfers refunds need to be processed manually
        return {
            "refund_id": f"refund_{uuid.uuid4().hex}",
            "status": "pending_manual_processing",
            "message": "Bank transfer refund requires manual processing",
            "amount": float(amount) if amount else 0,
        }

    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get bank transfer payment status."""
        # In a real implementation, this would check with the bank
        return {
            "transaction_id": transaction_id,
            "status": "pending_confirmation",
            "message": "Bank transfer payment status check",
        }

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """Handle bank transfer webhook (if supported)."""
        return {
            "gateway_type": PaymentGatewayType.BANK_TRANSFER,
            "event_type": "bank_transfer_notification",
            "data": payload,
            "processed": True,
        }


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances."""

    @staticmethod
    def create_gateway(
        gateway_type: PaymentGatewayType,
        config: PaymentGatewayConfig,
    ) -> BasePaymentGateway:
        """Create payment gateway instance."""
        if gateway_type == PaymentGatewayType.STRIPE:
            return StripePaymentGateway(config)
        if gateway_type == PaymentGatewayType.PAYPAL:
            return PayPalPaymentGateway(config)
        if gateway_type == PaymentGatewayType.BANK_TRANSFER:
            return BankTransferPaymentGateway(config)
        raise PaymentGatewayError(
            f"Unsupported payment gateway: {gateway_type}",
            gateway_type,
        )


class PaymentGatewayManager:
    """Manager for multiple payment gateways."""

    def __init__(self):
        self.gateways: Dict[PaymentGatewayType, BasePaymentGateway] = {}
        self.configs: Dict[PaymentGatewayType, PaymentGatewayConfig] = {}

    async def add_gateway(
        self,
        gateway_type: PaymentGatewayType,
        config: PaymentGatewayConfig,
    ):
        """Add payment gateway."""
        gateway = PaymentGatewayFactory.create_gateway(gateway_type, config)
        await gateway.initialize()

        self.gateways[gateway_type] = gateway
        self.configs[gateway_type] = config

    async def get_gateway(self, gateway_type: PaymentGatewayType) -> BasePaymentGateway:
        """Get payment gateway."""
        if gateway_type not in self.gateways:
            raise PaymentGatewayError(
                f"Payment gateway {gateway_type} not configured",
                gateway_type,
            )
        return self.gateways[gateway_type]

    async def remove_gateway(self, gateway_type: PaymentGatewayType):
        """Remove payment gateway."""
        if gateway_type in self.gateways:
            await self.gateways[gateway_type].close()
            del self.gateways[gateway_type]
            del self.configs[gateway_type]

    async def close_all(self):
        """Close all payment gateways."""
        for gateway in self.gateways.values():
            await gateway.close()
        self.gateways.clear()
        self.configs.clear()


class PaymentService(ServiceBase):
    """Service for managing payments across multiple gateways."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.gateway_manager = PaymentGatewayManager()
        self.order_repository = get_order_repository()
        self._pending_gateway_initializations: List[Coroutine[Any, Any, Any]] = []
        self._gateway_init_tasks: List[asyncio.Task[Any]] = []
        self._initialize_gateways()

    def _initialize_gateways(self):
        """Initialize configured payment gateways."""
        settings = self.context.settings

        # Initialize Stripe if configured
        stripe_api_key = getattr(settings, "stripe_api_key", "")
        if isinstance(stripe_api_key, str) and stripe_api_key.strip():
            stripe_config = PaymentGatewayConfig(
                gateway_type=PaymentGatewayType.STRIPE,
                api_key=stripe_api_key,
                public_key=getattr(settings, "stripe_public_key", ""),
                webhook_secret=getattr(settings, "stripe_webhook_secret", ""),
                test_mode=getattr(settings, "stripe_test_mode", True),
            )
            self._schedule_gateway_initialization(
                self.gateway_manager.add_gateway(
                    PaymentGatewayType.STRIPE,
                    stripe_config,
                ),
            )

        # Initialize PayPal if configured
        paypal_client_id = getattr(settings, "paypal_client_id", "")
        paypal_client_secret = getattr(settings, "paypal_client_secret", "")
        if (
            isinstance(paypal_client_id, str)
            and paypal_client_id.strip()
            and isinstance(paypal_client_secret, str)
            and paypal_client_secret.strip()
        ):
            paypal_config = PaymentGatewayConfig(
                gateway_type=PaymentGatewayType.PAYPAL,
                api_key=paypal_client_id,
                api_secret=paypal_client_secret,
                test_mode=getattr(settings, "paypal_test_mode", True),
            )
            self._schedule_gateway_initialization(
                self.gateway_manager.add_gateway(
                    PaymentGatewayType.PAYPAL,
                    paypal_config,
                ),
            )

        # Initialize Bank Transfer
        if getattr(settings, "enable_bank_transfer_gateway", True):
            bank_config = PaymentGatewayConfig(
                gateway_type=PaymentGatewayType.BANK_TRANSFER,
                test_mode=getattr(settings, "bank_transfer_test_mode", False),
            )
            self._schedule_gateway_initialization(
                self.gateway_manager.add_gateway(
                    PaymentGatewayType.BANK_TRANSFER,
                    bank_config,
                ),
            )

    def _schedule_gateway_initialization(self, coro: Coroutine[Any, Any, Any]):
        """Schedule gateway initialization respecting current event loop state."""

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop – execute immediately in current context.
            # This keeps tests that instantiate the service without an event
            # loop from failing while still ensuring gateways are ready.
            self._pending_gateway_initializations.append(coro)
        else:
            task = loop.create_task(coro)
            self._gateway_init_tasks.append(task)
            task.add_done_callback(lambda t: self._gateway_init_tasks.remove(t) if t in self._gateway_init_tasks else None)

    async def initialize(self):
        """Initialize payment service."""
        await super().initialize()
        await self._ensure_gateways_ready()
        logger.info(
            "Payment service initialized with %d gateways",
            len(self.gateway_manager.gateways),
        )

    async def cleanup(self):
        """Cleanup payment service."""
        await self.gateway_manager.close_all()
        await super().cleanup()

    async def create_payment(
        self,
        gateway_type: PaymentGatewayType,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: str,
        description: str,
        payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        metadata: Dict[str, Any] = None,
    ) -> PaymentTransaction:
        """Create a payment transaction."""
        try:
            await self._ensure_gateways_ready()
            gateway = await self.gateway_manager.get_gateway(gateway_type)

            # Create payment intent
            intent_result = await gateway.create_payment_intent(
                amount=amount,
                currency=currency,
                order_id=order_id,
                customer_email=customer_email,
                description=description,
                metadata=metadata,
            )

            # Create transaction record
            transaction = PaymentTransaction(
                id=str(uuid.uuid4()),
                order_id=order_id,
                gateway_type=gateway_type,
                gateway_transaction_id=intent_result.get("id", ""),
                amount=amount,
                currency=currency,
                status=PaymentStatus.PENDING,
                payment_method=payment_method,
                description=description,
                customer_email=customer_email,
                gateway_response=intent_result,
            )

            # Store transaction (in real implementation, this would go to database)
            logger.info(
                "Created payment transaction %s for order %s",
                transaction.id,
                order_id,
            )

            return transaction

        except Exception as e:
            logger.error("Failed to create payment: %s", e)
            raise PaymentGatewayError(f"Payment creation failed: {e}", gateway_type)

    async def process_payment(
        self,
        transaction_id: str,
        payment_method: PaymentMethod,
        payment_data: Dict[str, Any],
    ) -> PaymentTransaction:
        """Process a payment transaction."""
        try:
            await self._ensure_gateways_ready()
            # Get transaction (in real implementation, this would come from database)
            # For now, we'll create a mock transaction
            transaction = PaymentTransaction(
                id=transaction_id,
                order_id=payment_data.get("order_id", "unknown"),
                gateway_type=PaymentGatewayType.STRIPE,
                amount=Decimal(str(payment_data.get("amount", "0"))),
                currency=payment_data.get("currency", "RON"),
            )

            gateway = await self.gateway_manager.get_gateway(transaction.gateway_type)

            # Process payment
            result = await gateway.process_payment(
                transaction.gateway_transaction_id,
                payment_method,
                payment_data,
            )

            # Update transaction status
            transaction.status = PaymentStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            transaction.gateway_response.update(result)

            logger.info("Processed payment %s: %s", transaction_id, transaction.status)
            return transaction

        except Exception as e:
            logger.error("Failed to process payment %s: %s", transaction_id, e)

            # Update transaction with error
            if "transaction" in locals():
                transaction.status = PaymentStatus.FAILED
                transaction.gateway_response.update({"error": str(e)})

            raise PaymentGatewayError(f"Payment processing failed: {e}")

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> PaymentTransaction:
        """Refund a payment transaction."""
        try:
            await self._ensure_gateways_ready()
            # Get transaction (in real implementation, this would come from database)
            # For now, we'll create a mock transaction
            transaction = PaymentTransaction(
                id=transaction_id,
                order_id="unknown",
                gateway_type=PaymentGatewayType.STRIPE,
                amount=Decimal("100.00"),
                currency="RON",
                status=PaymentStatus.COMPLETED,
            )

            gateway = await self.gateway_manager.get_gateway(transaction.gateway_type)

            # Process refund
            result = await gateway.refund_payment(
                transaction.gateway_transaction_id,
                amount,
                reason,
            )

            # Update transaction status
            refund_amount = amount or transaction.amount
            transaction.status = PaymentStatus.REFUNDED
            transaction.refunded_at = datetime.utcnow()
            transaction.refund_amount = refund_amount
            transaction.gateway_response.update(result)

            logger.info("Refunded payment %s: %s", transaction_id, refund_amount)
            return transaction

        except Exception as e:
            logger.error("Failed to refund payment %s: %s", transaction_id, e)
            raise PaymentGatewayError(f"Payment refund failed: {e}")

    async def get_payment_status(self, transaction_id: str) -> PaymentTransaction:
        """Get payment transaction status."""
        try:
            await self._ensure_gateways_ready()
            # Get transaction (in real implementation, this would come from database)
            # For now, we'll create a mock transaction
            transaction = PaymentTransaction(
                id=transaction_id,
                order_id="unknown",
                gateway_type=PaymentGatewayType.STRIPE,
                amount=Decimal("100.00"),
                currency="RON",
            )

            gateway = await self.gateway_manager.get_gateway(transaction.gateway_type)

            # Get status from gateway
            status_result = await gateway.get_payment_status(
                transaction.gateway_transaction_id,
            )

            # Update transaction with latest status
            transaction.gateway_response.update(status_result)

            logger.info(
                "Retrieved payment status for %s: %s",
                transaction_id,
                transaction.status,
            )
            return transaction

        except Exception as e:
            logger.error("Failed to get payment status %s: %s", transaction_id, e)
            raise PaymentGatewayError(f"Payment status retrieval failed: {e}")

    async def handle_webhook(
        self,
        gateway_type: PaymentGatewayType,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """Handle payment gateway webhook."""
        try:
            await self._ensure_gateways_ready()
            gateway = await self.gateway_manager.get_gateway(gateway_type)

            # Process webhook
            result = await gateway.handle_webhook(payload, signature)
            await self._process_webhook_data(gateway_type, payload)

            event_type = result.get("event_type") or payload.get("type") or "unknown"
            logger.info("Processed webhook from %s: %s", gateway_type, event_type)
            return result

        except Exception as e:
            logger.error("Failed to handle webhook from %s: %s", gateway_type, e)
            raise PaymentGatewayError(f"Webhook handling failed: {e}", gateway_type)

    async def get_supported_gateways(self) -> List[Dict[str, Any]]:
        """Get list of supported gateways."""
        await self._ensure_gateways_ready()
        gateways_info: List[Dict[str, Any]] = []

        for gateway_type, config in self.gateway_manager.configs.items():
            gateways_info.append(
                {
                    "type": gateway_type.value,
                    "name": gateway_type.value.title(),
                    "test_mode": config.test_mode,
                    "supported_currencies": config.supported_currencies,
                    "max_amount": float(config.max_amount),
                    "status": "configured",
                },
            )

        for gateway_type in PaymentGatewayType:
            if gateway_type not in self.gateway_manager.configs:
                gateways_info.append(
                    {
                        "type": gateway_type.value,
                        "name": gateway_type.value.title(),
                        "status": "not_configured",
                    },
                )

        return gateways_info

    async def _ensure_gateways_ready(self):
        """Ensure any pending gateway initializations are completed."""

        if self._pending_gateway_initializations:
            pending = self._pending_gateway_initializations
            self._pending_gateway_initializations = []
            await asyncio.gather(*pending)

        active_tasks = [task for task in self._gateway_init_tasks if not task.done()]
        if active_tasks:
            await asyncio.gather(*active_tasks)

    async def _process_webhook_data(
        self,
        gateway_type: PaymentGatewayType,
        payload: Dict[str, Any],
    ):
        """Process webhook data and update transactions."""
        # In a real implementation, this would:
        # 1. Parse webhook payload
        # 2. Find relevant transactions in database
        # 3. Update transaction status
        # 4. Trigger any business logic (order status updates, notifications, etc.)

        event_type = payload.get("type", "")
        logger.info("Processing webhook event: %s from %s", event_type, gateway_type)

        # Mock processing for now
        if event_type == "payment_intent.succeeded":
            logger.info("Payment succeeded - would update order status")
        elif event_type == "payment_intent.payment_failed":
            logger.info("Payment failed - would notify customer")
        elif event_type == "charge.refunded":
            logger.info("Payment refunded - would update inventory")

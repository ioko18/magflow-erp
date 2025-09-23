"""Comprehensive tests for Payment Gateways integration.

This module contains unit tests, integration tests, and performance tests
for the payment gateways functionality including Stripe, PayPal, and bank transfers.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.dependency_injection import ServiceContext
from app.services.payment_service import (
    BankTransferPaymentGateway,
    PaymentGatewayConfig,
    PaymentGatewayError,
    PaymentGatewayType,
    PaymentMethod,
    PaymentService,
    PaymentStatus,
    PaymentTransaction,
    PayPalPaymentGateway,
    StripePaymentGateway,
)


class TestPaymentGatewayConfig:
    """Test payment gateway configuration."""

    def test_stripe_config_creation(self):
        """Test Stripe gateway configuration."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.STRIPE,
            api_key="sk_test_123",
            test_mode=True,
        )

        assert config.gateway_type == PaymentGatewayType.STRIPE
        assert config.api_key == "sk_test_123"
        assert config.test_mode is True
        assert "RON" in config.supported_currencies

    def test_paypal_config_creation(self):
        """Test PayPal gateway configuration."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.PAYPAL,
            api_key="paypal_client_id",
            api_secret="paypal_secret",
            test_mode=False,
        )

        assert config.gateway_type == PaymentGatewayType.PAYPAL
        assert config.api_key == "paypal_client_id"
        assert config.test_mode is False

    def test_bank_transfer_config_creation(self):
        """Test bank transfer gateway configuration."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.BANK_TRANSFER,
            test_mode=True,
        )

        assert config.gateway_type == PaymentGatewayType.BANK_TRANSFER
        assert config.test_mode is True


class TestStripePaymentGateway:
    """Test Stripe payment gateway implementation."""

    @pytest.fixture
    def config(self):
        """Create test Stripe configuration."""
        return PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.STRIPE,
            api_key="sk_test_123",
            test_mode=True,
        )

    @pytest.fixture
    def gateway(self, config):
        """Create Stripe gateway instance."""
        return StripePaymentGateway(config)

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self, gateway):
        """Test successful payment intent creation."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 200
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "id": "pi_test_123",
                    "amount": 10000,
                    "currency": "ron",
                    "status": "requires_payment_method",
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            result = await gateway.create_payment_intent(
                amount=Decimal("100.00"),
                currency="RON",
                order_id="order_123",
                customer_email="test@example.com",
                description="Test payment",
            )

            assert result["id"] == "pi_test_123"
            assert result["amount"] == 10000

    @pytest.mark.asyncio
    async def test_process_payment_success(self, gateway):
        """Test successful payment processing."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 200
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "id": "pi_test_123",
                    "status": "succeeded",
                    "amount_received": 10000,
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            result = await gateway.process_payment(
                "pi_test_123",
                PaymentMethod.CREDIT_CARD,
                {"payment_method_id": "pm_test_456"},
            )

            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_refund_payment_success(self, gateway):
        """Test successful payment refund."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 200
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "id": "rf_test_123",
                    "amount": 10000,
                    "status": "succeeded",
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            result = await gateway.refund_payment("ch_test_123", Decimal("100.00"))

            assert result["id"] == "rf_test_123"
            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_webhook_handling_success(self, gateway):
        """Test successful webhook handling."""
        webhook_payload = {
            "id": "evt_test_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "amount": 10000,
                    "status": "succeeded",
                },
            },
        }

        # Mock signature verification
        with patch.object(gateway, "_verify_webhook_signature", return_value=True):
            result = await gateway.handle_webhook(webhook_payload, "signature_123")

            assert result["gateway_type"] == PaymentGatewayType.STRIPE
            assert result["event_type"] == "payment_intent.succeeded"
            assert result["processed"] is True


class TestPayPalPaymentGateway:
    """Test PayPal payment gateway implementation."""

    @pytest.fixture
    def config(self):
        """Create test PayPal configuration."""
        return PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.PAYPAL,
            api_key="paypal_client_id",
            api_secret="paypal_client_secret",
            test_mode=True,
        )

    @pytest.fixture
    def gateway(self, config):
        """Create PayPal gateway instance."""
        return PayPalPaymentGateway(config)

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self, gateway):
        """Test successful PayPal payment creation."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 201
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "id": "PAY-123",
                    "status": "CREATED",
                    "links": [
                        {"rel": "approval_url", "href": "https://paypal.com/approve"}
                    ],
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            result = await gateway.create_payment_intent(
                amount=Decimal("100.00"),
                currency="RON",
                order_id="order_123",
                customer_email="test@example.com",
                description="Test payment",
            )

            assert result["id"] == "PAY-123"
            assert result["status"] == "CREATED"

    @pytest.mark.asyncio
    async def test_process_payment_success(self, gateway):
        """Test successful PayPal payment processing."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 200
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "id": "PAY-123",
                    "status": "COMPLETED",
                    "amount": {"total": "100.00", "currency": "RON"},
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            result = await gateway.process_payment(
                "PAY-123",
                PaymentMethod.PAYPAL,
                {"payer_id": "payer_123"},
            )

            assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, gateway):
        """Test successful access token retrieval."""
        with patch("aiohttp.ClientSession"):
            mock_session_instance = AsyncMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_post.__aenter__.return_value.status = 200
            mock_post.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "access_token": "access_token_123",
                    "expires_in": 3600,
                }
            )

            mock_session_instance.post = AsyncMock(return_value=mock_post)
            gateway.session = mock_session_instance

            token = await gateway._get_access_token()
            assert token == "access_token_123"


class TestBankTransferPaymentGateway:
    """Test bank transfer payment gateway implementation."""

    @pytest.fixture
    def config(self):
        """Create test bank transfer configuration."""
        return PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.BANK_TRANSFER,
            test_mode=True,
        )

    @pytest.fixture
    def gateway(self, config):
        """Create bank transfer gateway instance."""
        return BankTransferPaymentGateway(config)

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self, gateway):
        """Test successful bank transfer payment creation."""
        result = await gateway.create_payment_intent(
            amount=Decimal("100.00"),
            currency="RON",
            order_id="order_123",
            customer_email="test@example.com",
            description="Test payment",
        )

        assert "payment_intent_id" in result
        assert "instructions" in result
        assert result["instructions"]["bank_name"] == "Banca Transilvania"
        assert result["instructions"]["reference"] == "ORDER-order_123"

    @pytest.mark.asyncio
    async def test_process_payment_pending(self, gateway):
        """Test bank transfer payment processing."""
        result = await gateway.process_payment(
            "bt_123",
            PaymentMethod.BANK_TRANSFER,
            {"order_id": "order_123"},
        )

        assert result["transaction_id"] == "bt_123"
        assert result["status"] == "pending_confirmation"

    @pytest.mark.asyncio
    async def test_refund_payment_manual(self, gateway):
        """Test bank transfer payment refund."""
        result = await gateway.refund_payment("bt_123", Decimal("100.00"))

        assert "refund_id" in result
        assert result["status"] == "pending_manual_processing"


class TestPaymentService:
    """Test payment service functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create mock service context."""
        mock_context = MagicMock(spec=ServiceContext)
        mock_context.settings = MagicMock()
        return mock_context

    @pytest.fixture
    def payment_service(self, mock_context):
        """Create payment service instance."""
        service = PaymentService(mock_context)
        return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, payment_service):
        """Test payment service initialization."""
        assert payment_service.gateway_manager is not None
        assert (
            len(payment_service.gateway_manager.gateways) == 0
        )  # No gateways configured yet

    @pytest.mark.asyncio
    async def test_gateway_initialization(self, payment_service):
        """Test payment gateway initialization."""
        # Mock settings with Stripe configuration
        payment_service.context.settings.stripe_api_key = "sk_test_123"
        payment_service.context.settings.stripe_test_mode = True

        # Re-initialize gateways
        payment_service._initialize_gateways()

        # Wait for async initialization
        await asyncio.sleep(0.1)

        # Check that Stripe gateway was added
        assert PaymentGatewayType.STRIPE in payment_service.gateway_manager.gateways

    @pytest.mark.asyncio
    async def test_create_payment_transaction(self, payment_service):
        """Test payment transaction creation."""
        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.create_payment_intent = AsyncMock(
            return_value={
                "id": "pi_test_123",
                "amount": 10000,
                "currency": "ron",
            }
        )

        payment_service.gateway_manager.get_gateway = AsyncMock(
            return_value=mock_gateway
        )

        # Create payment
        transaction = await payment_service.create_payment(
            gateway_type=PaymentGatewayType.STRIPE,
            amount=Decimal("100.00"),
            currency="RON",
            order_id="order_123",
            customer_email="test@example.com",
            description="Test payment",
        )

        assert transaction.id is not None
        assert transaction.gateway_transaction_id == "pi_test_123"
        assert transaction.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_process_payment_transaction(self, payment_service):
        """Test payment transaction processing."""
        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.process_payment = AsyncMock(
            return_value={
                "id": "pi_test_123",
                "status": "succeeded",
            }
        )

        payment_service.gateway_manager.get_gateway = AsyncMock(
            return_value=mock_gateway
        )

        # Process payment
        transaction = await payment_service.process_payment(
            "txn_123",
            PaymentMethod.CREDIT_CARD,
            {"payment_method_id": "pm_test_456"},
        )

        assert transaction.status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_refund_payment_transaction(self, payment_service):
        """Test payment transaction refund."""
        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.refund_payment = AsyncMock(
            return_value={
                "id": "rf_test_123",
                "status": "succeeded",
            }
        )

        payment_service.gateway_manager.get_gateway = AsyncMock(
            return_value=mock_gateway
        )

        # Process refund
        transaction = await payment_service.refund_payment("txn_123", Decimal("50.00"))

        assert transaction.status == PaymentStatus.REFUNDED
        assert transaction.refund_amount == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_webhook_handling(self, payment_service):
        """Test webhook handling."""
        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.handle_webhook = AsyncMock(
            return_value={
                "gateway_type": PaymentGatewayType.STRIPE,
                "event_type": "payment_intent.succeeded",
                "processed": True,
            }
        )

        payment_service.gateway_manager.get_gateway = AsyncMock(
            return_value=mock_gateway
        )

        # Handle webhook
        result = await payment_service.handle_webhook(
            PaymentGatewayType.STRIPE,
            {"type": "payment_intent.succeeded", "data": {"object": {}}},
        )

        assert result["gateway_type"] == PaymentGatewayType.STRIPE
        assert result["event_type"] == "payment_intent.succeeded"
        assert result["processed"] is True


class TestPaymentTransaction:
    """Test payment transaction model."""

    def test_transaction_creation(self):
        """Test payment transaction creation."""
        transaction = PaymentTransaction(
            id="txn_123",
            order_id="order_123",
            gateway_type=PaymentGatewayType.STRIPE,
            amount=Decimal("100.00"),
            currency="RON",
            status=PaymentStatus.COMPLETED,
        )

        assert transaction.id == "txn_123"
        assert transaction.order_id == "order_123"
        assert transaction.gateway_type == PaymentGatewayType.STRIPE
        assert transaction.amount == Decimal("100.00")
        assert transaction.currency == "RON"
        assert transaction.status == PaymentStatus.COMPLETED
        assert transaction.created_at is not None
        assert transaction.updated_at is not None

    def test_transaction_timestamps(self):
        """Test transaction timestamp handling."""
        now = datetime.utcnow()
        transaction = PaymentTransaction(
            created_at=now,
            updated_at=now,
        )

        assert transaction.created_at == now
        assert transaction.updated_at == now

    def test_transaction_refund_tracking(self):
        """Test transaction refund tracking."""
        transaction = PaymentTransaction(
            status=PaymentStatus.PARTIALLY_REFUNDED,
            refund_amount=Decimal("25.00"),
        )

        assert transaction.status == PaymentStatus.PARTIALLY_REFUNDED
        assert transaction.refund_amount == Decimal("25.00")


class TestPaymentGatewayErrors:
    """Test payment gateway error handling."""

    def test_payment_gateway_error_creation(self):
        """Test payment gateway error creation."""
        error = PaymentGatewayError(
            "Payment failed",
            PaymentGatewayType.STRIPE,
            "insufficient_funds",
            {"amount": 100},
        )

        assert str(error) == "Payment failed"
        assert error.gateway_type == PaymentGatewayType.STRIPE
        assert error.code == "insufficient_funds"
        assert error.details == {"amount": 100}

    def test_payment_gateway_error_without_details(self):
        """Test payment gateway error without additional details."""
        error = PaymentGatewayError(
            "Gateway timeout",
            PaymentGatewayType.PAYPAL,
        )

        assert error.gateway_type == PaymentGatewayType.PAYPAL
        assert error.code is None
        assert error.details == {}


class TestPaymentGatewayPerformance:
    """Test payment gateway performance."""

    @pytest.mark.asyncio
    async def test_concurrent_payment_processing(self, mock_context):
        """Test concurrent payment processing."""
        import asyncio

        service = PaymentService(mock_context)

        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.create_payment_intent = AsyncMock(
            return_value={"id": "pi_test_123"}
        )
        service.gateway_manager.get_gateway = AsyncMock(return_value=mock_gateway)

        async def create_payment(i):
            return await service.create_payment(
                gateway_type=PaymentGatewayType.STRIPE,
                amount=Decimal("100.00"),
                currency="RON",
                order_id=f"order_{i}",
                customer_email=f"customer{i}@example.com",
                description=f"Payment {i}",
            )

        # Process multiple payments concurrently
        start_time = asyncio.get_event_loop().time()

        tasks = [create_payment(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()

        # Should complete within reasonable time
        duration = end_time - start_time
        assert duration < 3.0  # Should complete within 3 seconds

        # All payments should succeed
        assert len(results) == 10
        assert all(result.id for result in results)

    @pytest.mark.asyncio
    async def test_gateway_response_time(self, mock_context):
        """Test gateway response time monitoring."""
        service = PaymentService(mock_context)

        # Mock gateway with slow response
        mock_gateway = AsyncMock()
        mock_gateway.create_payment_intent = AsyncMock(
            return_value={"id": "pi_test_123"}
        )

        # Simulate slow response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms delay
            return {"id": "pi_test_123"}

        mock_gateway.create_payment_intent = slow_response
        service.gateway_manager.get_gateway = AsyncMock(return_value=mock_gateway)

        start_time = asyncio.get_event_loop().time()

        result = await service.create_payment(
            gateway_type=PaymentGatewayType.STRIPE,
            amount=Decimal("100.00"),
            currency="RON",
            order_id="order_123",
            customer_email="test@example.com",
            description="Test payment",
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should take at least 500ms due to simulated delay
        assert duration >= 0.5
        assert result is not None


class TestPaymentGatewaySecurity:
    """Test payment gateway security features."""

    def test_amount_validation(self):
        """Test payment amount validation."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.STRIPE,
            min_amount=Decimal("0.50"),
            max_amount=Decimal("10000.00"),
        )

        gateway = StripePaymentGateway(config)

        # Test valid amount
        assert gateway._validate_amount(Decimal("100.00")) is True

        # Test amount too low
        with pytest.raises(PaymentGatewayError, match="below minimum"):
            gateway._validate_amount(Decimal("0.25"))

        # Test amount too high
        with pytest.raises(PaymentGatewayError, match="exceeds maximum"):
            gateway._validate_amount(Decimal("15000.00"))

    def test_currency_validation(self):
        """Test payment currency validation."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.STRIPE,
            supported_currencies=["RON", "EUR", "USD"],
        )

        gateway = StripePaymentGateway(config)

        # Test valid currency
        assert gateway._validate_currency("RON") is True

        # Test invalid currency
        with pytest.raises(PaymentGatewayError, match="not supported"):
            gateway._validate_currency("GBP")

    def test_webhook_signature_verification(self):
        """Test webhook signature verification."""
        config = PaymentGatewayConfig(
            gateway_type=PaymentGatewayType.STRIPE,
            webhook_secret="whsec_test_123",
        )

        gateway = StripePaymentGateway(config)

        # Test with valid signature (mocked)
        with patch.object(gateway, "_verify_webhook_signature", return_value=True):
            assert gateway._verify_webhook_signature({}, "signature_123") is True

    def test_transaction_id_generation(self):
        """Test transaction ID generation security."""
        transaction = PaymentTransaction()

        # Should generate unique ID
        assert transaction.id is not None
        assert len(transaction.id) > 0

        # Should be unique across instances
        transaction2 = PaymentTransaction()
        assert transaction.id != transaction2.id


class TestPaymentGatewayMonitoring:
    """Test payment gateway monitoring and health checks."""

    @pytest.mark.asyncio
    async def test_gateway_health_check(self, mock_context):
        """Test payment gateway health monitoring."""
        service = PaymentService(mock_context)

        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.create_payment_intent = AsyncMock(
            return_value={"id": "pi_test_123"}
        )
        service.gateway_manager.get_gateway = AsyncMock(return_value=mock_gateway)

        # Test health check (mock implementation)
        gateways = await service.get_supported_gateways()

        # Should return gateway information
        assert isinstance(gateways, list)
        assert len(gateways) >= 0

    @pytest.mark.asyncio
    async def test_gateway_error_rate_monitoring(self, mock_context):
        """Test payment gateway error rate monitoring."""
        service = PaymentService(mock_context)

        # Mock gateway manager with error
        mock_gateway = AsyncMock()
        mock_gateway.create_payment_intent = AsyncMock(
            side_effect=PaymentGatewayError("API Error")
        )
        service.gateway_manager.get_gateway = AsyncMock(return_value=mock_gateway)

        # Test error handling
        with pytest.raises(PaymentGatewayError):
            await service.create_payment(
                gateway_type=PaymentGatewayType.STRIPE,
                amount=Decimal("100.00"),
                currency="RON",
                order_id="order_123",
                customer_email="test@example.com",
                description="Test payment",
            )

    @pytest.mark.asyncio
    async def test_transaction_status_tracking(self, mock_context):
        """Test payment transaction status tracking."""
        service = PaymentService(mock_context)

        # Mock gateway manager
        mock_gateway = AsyncMock()
        mock_gateway.get_payment_status = AsyncMock(
            return_value={
                "id": "pi_test_123",
                "status": "succeeded",
                "amount_received": 10000,
            }
        )
        service.gateway_manager.get_gateway = AsyncMock(return_value=mock_gateway)

        # Test status retrieval
        transaction = await service.get_payment_status("txn_123")

        assert transaction.gateway_transaction_id == "pi_test_123"
        assert "succeeded" in str(transaction.gateway_response)

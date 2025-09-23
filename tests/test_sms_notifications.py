"""Comprehensive tests for SMS Notifications integration.

This module contains unit tests, integration tests, and performance tests
for the SMS notification functionality including Twilio, MessageBird, and templates.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.dependency_injection import ServiceContext
from app.services.sms_service import (
    MessageBirdSMSProvider,
    NotificationType,
    SMSMessage,
    SMSProvider,
    SMSProviderError,
    SMSService,
    SMSStatus,
    SMSTemplate,
    TwilioSMSProvider,
)


@pytest.fixture
def mock_context():
    """Create mock service context."""
    mock_context = MagicMock(spec=ServiceContext)
    mock_context.settings = MagicMock()
    return mock_context


class TestSMSProviderConfig:
    """Test SMS provider configuration."""

    def test_twilio_config_creation(self):
        """Test Twilio provider configuration."""
        from app.services.sms_service import SMSProvider, SMSProviderConfig

        config = SMSProviderConfig(
            provider=SMSProvider.TWILIO,
            api_key="test_api_key",
            account_sid="test_account_sid",
            auth_token="test_auth_token",
            test_mode=True,
        )

        assert config.provider == SMSProvider.TWILIO
        assert config.api_key == "test_api_key"
        assert config.account_sid == "test_account_sid"
        assert config.test_mode is True

    def test_messagebird_config_creation(self):
        """Test MessageBird provider configuration."""
        from app.services.sms_service import SMSProvider, SMSProviderConfig

        config = SMSProviderConfig(
            provider=SMSProvider.MESSAGEBIRD,
            api_key="test_api_key",
            sender_id="TestSender",
            test_mode=False,
        )

        assert config.provider == SMSProvider.MESSAGEBIRD
        assert config.api_key == "test_api_key"
        assert config.sender_id == "TestSender"
        assert config.test_mode is False


class TestTwilioSMSProvider:
    """Test Twilio SMS provider implementation."""

    @pytest.fixture
    def config(self):
        """Create test Twilio configuration."""
        from app.services.sms_service import SMSProvider, SMSProviderConfig

        return SMSProviderConfig(
            provider=SMSProvider.TWILIO,
            account_sid="test_account_sid",
            auth_token="test_auth_token",
            test_mode=True,
        )

    @pytest.fixture
    def provider(self, config):
        """Create Twilio provider instance."""
        return TwilioSMSProvider(config)

    @pytest.mark.asyncio
    async def test_send_sms_success(self, provider):
        """Test successful SMS sending via Twilio."""

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "sid": "SM123",
            "status": "sent",
            "to": "+40700123456",
            "from": "+40700987654",
            "price": "0.05",
        }

        # Correctly mock the async context manager
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        provider.session = mock_session

        result = await provider.send_sms(
            phone_number="+40700123456",
            message="Test message",
            sender="+40700987654",
        )

        assert result["message_id"] == "SM123"
        assert result["status"] == "sent"
        assert result["to"] == "+40700123456"

    @pytest.mark.asyncio
    async def test_phone_number_validation(self, provider):
        """Test phone number validation."""
        # Valid phone numbers
        assert provider._validate_phone_number("+40700123456") is True
        assert provider._validate_phone_number("+123456789012") is True

        # Invalid phone numbers
        assert provider._validate_phone_number("40700123456") is False  # Missing +
        assert (
            provider._validate_phone_number("+4070012345678901234567890") is False
        )  # Too long
        assert provider._validate_phone_number("+40700") is False  # Too short
        assert (
            provider._validate_phone_number("+40700abc123") is False
        )  # Contains letters

    @pytest.mark.asyncio
    async def test_message_truncation(self, provider):
        """Test message truncation."""
        long_message = "A" * 200
        truncated = provider._truncate_message(long_message)

        assert len(truncated) == 160  # max_length (160) characters total
        assert truncated.endswith("...")
        assert truncated.startswith("A" * 157)  # 160 - 3 for "..."

        # Short message should not be truncated
        short_message = "Short message"
        assert provider._truncate_message(short_message) == short_message


class TestMessageBirdSMSProvider:
    """Test MessageBird SMS provider implementation."""

    @pytest.fixture
    def config(self):
        """Create test MessageBird configuration."""
        from app.services.sms_service import SMSProvider, SMSProviderConfig

        return SMSProviderConfig(
            provider=SMSProvider.MESSAGEBIRD,
            api_key="test_api_key",
            sender_id="TestSender",
            test_mode=True,
        )

    @pytest.fixture
    def provider(self, config):
        """Create MessageBird provider instance."""
        return MessageBirdSMSProvider(config)

    @pytest.mark.asyncio
    async def test_send_sms_success(self, provider):
        """Test successful SMS sending via MessageBird."""

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "id": "msg_123",
            "total_sent_price": {"amount": "0.05"},
        }

        # Correctly mock the async context manager
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        provider.session = mock_session

        result = await provider.send_sms(
            phone_number="+40700123456",
            message="Test message",
        )

        assert result["message_id"] == "msg_123"
        assert result["status"] == "sent"
        assert result["cost"] == "0.05"


class TestSMSTemplate:
    """Test SMS template functionality."""

    def test_get_template_order_confirmation(self):
        """Test getting order confirmation template."""
        template = SMSTemplate.get_template(NotificationType.ORDER_CONFIRMATION, "en")

        assert "order_id" in template
        assert "amount" in template
        assert "currency" in template

    def test_get_template_different_languages(self):
        """Test template localization."""
        en_template = SMSTemplate.get_template(
            NotificationType.ORDER_CONFIRMATION, "en"
        )
        ro_template = SMSTemplate.get_template(
            NotificationType.ORDER_CONFIRMATION, "ro"
        )

        assert en_template != ro_template
        assert "order_id" in en_template
        assert "order_id" in ro_template

    def test_format_message_with_variables(self):
        """Test message formatting with variables."""
        variables = {
            "order_id": "ORD-123",
            "amount": "100.50",
            "currency": "RON",
            "tracking_url": "https://track.example.com",
        }

        message = SMSTemplate.format_message(
            NotificationType.ORDER_CONFIRMATION,
            variables,
            "en",
        )

        assert "ORD-123" in message
        assert "100.50" in message
        assert "RON" in message

    def test_format_message_missing_variables(self):
        """Test message formatting with missing variables."""
        variables = {}  # Empty variables

        message = SMSTemplate.format_message(
            NotificationType.ORDER_CONFIRMATION,
            variables,
            "en",
        )

        # Should return template without formatting if variables are missing
        assert "order_id" in message
        assert "amount" in message


class TestSMSService:
    """Test SMS service functionality."""

    @pytest.fixture
    def sms_service(self, mock_context):
        """Create SMS service instance."""
        service = SMSService(mock_context)
        return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, sms_service):
        """Test SMS service initialization."""
        assert sms_service.providers is not None
        assert len(sms_service.providers) == 0  # No providers configured yet

    @pytest.mark.asyncio
    async def test_provider_initialization(self, sms_service):
        """Test SMS provider initialization."""
        # Mock settings with Twilio configuration
        sms_service.context.settings.twilio_account_sid = "test_account_sid"
        sms_service.context.settings.twilio_auth_token = "test_auth_token"

        # Re-initialize providers
        sms_service._initialize_providers()

        # Wait for async initialization
        await asyncio.sleep(0.1)

        # Check that Twilio provider was added
        assert SMSProvider.TWILIO in sms_service.providers

    @pytest.mark.asyncio
    async def test_send_sms_message(self, sms_service):
        """Test SMS message sending."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
                "cost": "0.05",
            }
        )
        mock_provider._validate_phone_number = AsyncMock(return_value=True)

        sms_service.providers[SMSProvider.TWILIO] = mock_provider

        # Send SMS
        message = await sms_service.send_sms(
            phone_number="+40700123456",
            message="Test message",
            provider=SMSProvider.TWILIO,
            notification_type=NotificationType.CUSTOM,
        )

        assert message.id is not None
        assert message.phone_number == "+40700123456"
        assert message.message == "Test message"
        assert message.status == SMSStatus.PENDING

    @pytest.mark.asyncio
    async def test_send_templated_sms(self, sms_service):
        """Test templated SMS sending."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        sms_service.providers[SMSProvider.TWILIO] = mock_provider

        # Send templated SMS
        message = await sms_service.send_templated_sms(
            phone_number="+40700123456",
            notification_type=NotificationType.ORDER_CONFIRMATION,
            template_vars={
                "order_id": "ORD-123",
                "amount": "100.50",
                "currency": "RON",
            },
            language="en",
        )

        assert message.id is not None
        assert message.notification_type == NotificationType.ORDER_CONFIRMATION
        assert "ORD-123" in message.message

    @pytest.mark.asyncio
    async def test_send_bulk_sms(self, sms_service):
        """Test bulk SMS sending."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        sms_service.providers[SMSProvider.TWILIO] = mock_provider

        phone_numbers = ["+40700123456", "+40700123457", "+40700123458"]

        # Send bulk SMS
        messages = await sms_service.send_bulk_sms(
            phone_numbers=phone_numbers,
            message="Bulk test message",
            provider=SMSProvider.TWILIO,
            notification_type=NotificationType.CUSTOM,
        )

        assert len(messages) == 3
        assert all(msg.phone_number in phone_numbers for msg in messages)

    @pytest.mark.asyncio
    async def test_send_order_confirmation(self, sms_service):
        """Test order confirmation SMS sending."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        sms_service.providers[SMSProvider.TWILIO] = mock_provider

        # Send order confirmation
        message = await sms_service.send_order_confirmation(
            phone_number="+40700123456",
            order_id="ORD-123",
            amount=100.50,
            currency="RON",
            tracking_url="https://track.example.com",
        )

        assert message.id is not None
        assert message.notification_type == NotificationType.ORDER_CONFIRMATION
        assert "ORD-123" in message.message
        assert "100.50" in message.message

    @pytest.mark.asyncio
    async def test_send_inventory_alert(self, sms_service):
        """Test inventory alert SMS sending."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        sms_service.providers[SMSProvider.TWILIO] = mock_provider

        # Send inventory alert
        message = await sms_service.send_inventory_alert(
            phone_number="+40700123456",
            product_name="iPhone 15",
            quantity=5,
        )

        assert message.id is not None
        assert message.notification_type == NotificationType.INVENTORY_LOW
        assert "iPhone 15" in message.message
        assert "5" in message.message


class TestSMSMessage:
    """Test SMS message model."""

    def test_message_creation(self):
        """Test SMS message creation."""
        message = SMSMessage(
            id="msg_123",
            phone_number="+40700123456",
            message="Test message",
            provider=SMSProvider.TWILIO,
            notification_type=NotificationType.CUSTOM,
        )

        assert message.id == "msg_123"
        assert message.phone_number == "+40700123456"
        assert message.message == "Test message"
        assert message.provider == SMSProvider.TWILIO
        assert message.notification_type == NotificationType.CUSTOM
        assert message.status == SMSStatus.PENDING
        assert message.created_at is not None
        assert message.updated_at is not None

    def test_message_timestamps(self):
        """Test message timestamp handling."""
        now = datetime.utcnow()
        message = SMSMessage(
            created_at=now,
            updated_at=now,
        )

        assert message.created_at == now
        assert message.updated_at == now

    def test_message_retry_tracking(self):
        """Test message retry tracking."""
        message = SMSMessage(
            status=SMSStatus.FAILED,
            retry_count=2,
            max_retries=3,
        )

        assert message.status == SMSStatus.FAILED
        assert message.retry_count == 2
        assert message.max_retries == 3


class TestSMSProviderErrors:
    """Test SMS provider error handling."""

    def test_sms_provider_error_creation(self):
        """Test SMS provider error creation."""
        error = SMSProviderError(
            "SMS sending failed",
            SMSProvider.TWILIO,
            "invalid_phone_number",
            {"phone_number": "+40700123456"},
        )

        assert str(error) == "SMS sending failed"
        assert error.provider == SMSProvider.TWILIO
        assert error.code == "invalid_phone_number"
        assert error.details == {"phone_number": "+40700123456"}

    def test_sms_provider_error_without_details(self):
        """Test SMS provider error without additional details."""
        error = SMSProviderError(
            "Provider timeout",
            SMSProvider.MESSAGEBIRD,
        )

        assert error.provider == SMSProvider.MESSAGEBIRD
        assert error.code is None
        assert error.details == {}


class TestSMSPerformance:
    """Test SMS service performance."""

    @pytest.mark.asyncio
    async def test_concurrent_sms_sending(self, mock_context):
        """Test concurrent SMS sending."""
        import asyncio

        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        service.providers[SMSProvider.TWILIO] = mock_provider

        async def send_sms(i):
            return await service.send_sms(
                phone_number=f"+4070012345{i}",
                message=f"Test message {i}",
                provider=SMSProvider.TWILIO,
                notification_type=NotificationType.CUSTOM,
            )

        # Send multiple SMS concurrently
        start_time = asyncio.get_event_loop().time()

        tasks = [send_sms(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()

        # Should complete within reasonable time
        duration = end_time - start_time
        assert duration < 3.0  # Should complete within 3 seconds

        # All SMS should succeed
        assert len(results) == 10
        assert all(msg.id for msg in results)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_context):
        """Test SMS rate limiting."""
        service = SMSService(mock_context)

        # Mock provider with rate limiting
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        mock_provider.config.rate_limit_per_minute = 2  # Very low for testing
        service.providers[SMSProvider.TWILIO] = mock_provider

        start_time = asyncio.get_event_loop().time()

        # Send SMS rapidly
        for i in range(3):
            await service.send_sms(
                phone_number=f"+4070012345{i}",
                message=f"Test message {i}",
                provider=SMSProvider.TWILIO,
            )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should take some time due to rate limiting
        assert duration > 0.5  # Should take at least 500ms due to rate limiting

    @pytest.mark.asyncio
    async def test_bulk_sms_performance(self, mock_context):
        """Test bulk SMS performance."""
        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        service.providers[SMSProvider.TWILIO] = mock_provider

        phone_numbers = [f"+4070012345{i}" for i in range(5)]

        start_time = asyncio.get_event_loop().time()

        messages = await service.send_bulk_sms(
            phone_numbers=phone_numbers,
            message="Bulk test message",
            provider=SMSProvider.TWILIO,
        )

        end_time = asyncio.get_event_loop().time()

        # Should complete within reasonable time
        duration = end_time - start_time
        assert duration < 2.0  # Should complete within 2 seconds

        # All messages should be processed
        assert len(messages) == 5


class TestSMSMonitoring:
    """Test SMS monitoring and analytics."""

    @pytest.mark.asyncio
    async def test_provider_status_check(self, mock_context):
        """Test SMS provider status monitoring."""
        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.config.test_mode = True
        mock_provider.config.rate_limit_per_minute = 60
        mock_provider.config.cost_per_message = Decimal("0.05")
        service.providers[SMSProvider.TWILIO] = mock_provider

        # Check provider status
        status = await service.get_provider_status(SMSProvider.TWILIO)

        assert status["provider"] == SMSProvider.TWILIO
        assert status["status"] == "active"
        assert status["configuration"]["test_mode"] is True

    @pytest.mark.asyncio
    async def test_statistics_generation(self, mock_context):
        """Test SMS statistics generation."""
        service = SMSService(mock_context)

        # Get statistics
        stats = await service.get_statistics()

        # Should return statistics structure
        assert isinstance(stats, dict)
        assert "total_messages" in stats
        assert "success_rate" in stats
        assert "total_cost" in stats

    @pytest.mark.asyncio
    async def test_message_queue_processing(self, mock_context):
        """Test SMS message queue processing."""
        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        service.providers[SMSProvider.TWILIO] = mock_provider

        # Add messages to queue
        await service.send_sms("+40700123456", "Test 1", SMSProvider.TWILIO)
        await service.send_sms("+40700123457", "Test 2", SMSProvider.TWILIO)

        # Wait for processing
        await asyncio.sleep(1)

        # Queue should be empty after processing
        assert len(service.message_queue) == 0

    def test_template_localization(self):
        """Test SMS template localization."""
        # Test English template
        en_message = SMSTemplate.format_message(
            NotificationType.ORDER_CONFIRMATION,
            {"order_id": "ORD-123", "amount": "100.50", "currency": "RON"},
            "en",
        )

        # Test Romanian template
        ro_message = SMSTemplate.format_message(
            NotificationType.ORDER_CONFIRMATION,
            {"order_id": "ORD-123", "amount": "100.50", "currency": "RON"},
            "ro",
        )

        # Should be different languages
        assert en_message != ro_message
        assert "ORD-123" in en_message
        assert "ORD-123" in ro_message


class TestSMSIntegration:
    """Test SMS integration with eMAG marketplace."""

    @pytest.mark.asyncio
    async def test_emag_order_confirmation_sms(self, mock_context):
        """Test eMAG order confirmation SMS."""
        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        service.providers[SMSProvider.TWILIO] = mock_provider

        # Send eMAG order confirmation
        message = await service.send_order_confirmation(
            phone_number="+40700123456",
            order_id="EMAG-123",
            amount=250.75,
            currency="RON",
            tracking_url="https://emag.ro/track/123",
        )

        assert message.notification_type == NotificationType.ORDER_CONFIRMATION
        assert "EMAG-123" in message.message
        assert "250.75" in message.message
        assert "https://emag.ro/track/123" in message.message

    @pytest.mark.asyncio
    async def test_emag_low_stock_alert(self, mock_context):
        """Test eMAG low stock alert SMS."""
        service = SMSService(mock_context)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send_sms = AsyncMock(
            return_value={
                "message_id": "msg_123",
                "status": "sent",
            }
        )
        service.providers[SMSProvider.TWILIO] = mock_provider

        # Send low stock alert
        message = await service.send_inventory_alert(
            phone_number="+40700123456",
            product_name="Samsung Galaxy S24",
            quantity=3,
        )

        assert message.notification_type == NotificationType.INVENTORY_LOW
        assert "Samsung Galaxy S24" in message.message
        assert "3" in message.message

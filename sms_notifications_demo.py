"""
SMS Notifications Demo - MagFlow ERP Integration

This script demonstrates the comprehensive SMS notification system
for eMAG marketplace integration, including order confirmations,
alerts, and automated messaging.
"""

import asyncio

from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext
from app.services.sms_service import NotificationType, SMSProvider, SMSService


async def demonstrate_sms_notifications():
    """Demonstrate SMS notification functionality."""

    print("📱 SMS Notifications Demo - MagFlow ERP")
    print("=" * 45)

    # Initialize the SMS service
    settings = get_settings()
    context = ServiceContext(settings=settings)
    sms_service = SMSService(context)

    await sms_service.initialize()

    try:
        print("\n📊 Getting SMS Providers...")

        # Get supported providers
        providers_info = []
        for provider, config in sms_service.providers.items():
            status = await sms_service.get_provider_status(provider)
            providers_info.append(status)

        print('✅ Found ' + str(len(providers_info)) + ' configured SMS providers:')
        for provider_info in providers_info:
            print('  • ' + provider_info['provider'].title() + ' - ' + provider_info['status'])
            if provider_info['status'] == 'active':
                config = provider_info['configuration']
                print('    - Rate Limit: ' + str(config['rate_limit']) + ' messages/minute')
                print('    - Cost: ' + str(config['cost_per_message']) + ' per message')

        print("\n📱 SMS Templates Available...")

        # Get available templates
        templates = {
            "order_confirmation": {
                "en": (
                    "Order {order_id} confirmed. Total: {amount} {currency}. "
                    "Track: {tracking_url}"
                ),
                "ro": (
                    "Comanda {order_id} confirmată. Total: {amount} {currency}. "
                    "Urmărire: {tracking_url}"
                ),
            },
            "order_shipped": {
                "en": (
                    "Order {order_id} shipped! Delivery: {delivery_date}. "
                    "Track: {tracking_url}"
                ),
                "ro": (
                    "Comanda {order_id} expediată! Livrare: {delivery_date}. "
                    "Urmărire: {tracking_url}"
                ),
            },
            "payment_confirmation": {
                "en": "Payment of {amount} {currency} confirmed for order {order_id}.",
                "ro": "Plata de {amount} {currency} confirmată pentru comanda {order_id}."
            },
            "inventory_low": {
                "en": "Low stock alert: {product_name} only has {quantity} items left.",
                "ro": "Alertă stoc redus: {product_name} mai are doar {quantity} bucăți."
            }
        }

        print("✅ Available SMS templates:")
        for template_type, languages in templates.items():
            print('  • ' + template_type.replace('_', ' ').title() + ':')
            for lang, template in languages.items():
                preview = template[:50]
                suffix = '...' if len(template) > 50 else ''
                print('    - ' + lang.upper() + ': ' + preview + suffix)

        print("\n📤 Sending Test SMS Messages...")

        # Send test messages
        test_messages = [
            {
                "phone": "+40700123456",
                "type": "Order Confirmation",
                "message": "Order EMAG-123 confirmed. Total: 250.75 RON. Track: https://emag.ro/track/123"
            },
            {
                "phone": "+40700123457",
                "type": "Payment Confirmation",
                "message": "Payment of 150.00 RON confirmed for order EMAG-124."
            },
            {
                "phone": "+40700123458",
                "type": "Inventory Alert",
                "message": "Low stock alert: iPhone 15 only has 3 items left."
            }
        ]

        for i, test_msg in enumerate(test_messages, 1):
            try:
                print('  Sending SMS ' + str(i) + '/3: ' + test_msg['type'])

                # Send SMS message
                message = await sms_service.send_sms(
                    phone_number=test_msg["phone"],
                    message=test_msg["message"],
                    provider=SMSProvider.TWILIO,
                    notification_type=NotificationType.CUSTOM
                )

                print('    ✅ SMS queued successfully')
                print('       Message ID: ' + str(message.id))
                print('       Status: ' + str(message.status.value))
                print('       Provider: ' + str(message.provider.value))

            except Exception as e:
                print('    ❌ Failed to send SMS: ' + str(e))

        print("\n📤 Sending Templated SMS Messages...")

        # Send templated messages
        template_tests = [
            {
                "phone": "+40700123456",
                "type": "Order Confirmation",
                "template": NotificationType.ORDER_CONFIRMATION,
                "vars": {
                    "order_id": "EMAG-125",
                    "amount": "300.50",
                    "currency": "RON",
                    "tracking_url": "https://emag.ro/track/125"
                }
            },
            {
                "phone": "+40700123457",
                "type": "Order Shipped",
                "template": NotificationType.ORDER_SHIPPED,
                "vars": {
                    "order_id": "EMAG-126",
                    "delivery_date": "2024-01-15",
                    "tracking_url": "https://emag.ro/track/126"
                }
            },
            {
                "phone": "+40700123458",
                "type": "Payment Confirmation",
                "template": NotificationType.PAYMENT_CONFIRMATION,
                "vars": {
                    "order_id": "EMAG-127",
                    "amount": "75.25",
                    "currency": "RON"
                }
            }
        ]

        for i, test in enumerate(template_tests, 1):
            try:
                print('  Sending Templated SMS ' + str(i) + '/3: ' + test['type'])

                # Send templated SMS
                message = await sms_service.send_templated_sms(
                    phone_number=test["phone"],
                    notification_type=test["template"],
                    template_vars=test["vars"],
                    language="en"
                )

                print('    ✅ Templated SMS sent successfully')
                print('       Template: ' + str(test['template'].value))
                msg_preview = message.message[:60]
                msg_suffix = '...' if len(message.message) > 60 else ''
                print('       Message: ' + str(msg_preview) + msg_suffix)

            except Exception as e:
                print('    ❌ Failed to send templated SMS: ' + str(e))

        print("\n📊 SMS Statistics (Demo Data)...")

        # Mock statistics
        stats = {
            "total_messages": 1250,
            "sent_messages": 1180,
            "delivered_messages": 1150,
            "failed_messages": 70,
            "success_rate": 92.0,
            "total_cost": 62.50,
            "average_delivery_time": "45 seconds",
            "notification_breakdown": {
                "order_confirmation": 450,
                "order_shipped": 300,
                "payment_confirmation": 200,
                "inventory_low": 100,
                "promotion": 200
            }
        }

        print('  • Total Messages: ' + str(stats['total_messages']))
        print('  • Success Rate: ' + str(stats['success_rate']) + '%')
        print('  • Total Cost: ' + str(stats['total_cost']) + ' EUR')
        print('  • Average Delivery Time: ' + str(stats['average_delivery_time']))
        print('  Messages by Type:')
        for msg_type, count in stats['notification_breakdown'].items():
            percentage = (count / stats['total_messages']) * 100
            label = msg_type.replace('_', ' ').title()
            percentage_str = str(round(percentage, 1)) + '%'
            print('    - ' + label + ': ' + str(count) + ' (' + percentage_str + ')')

        print("\n🌍 Supported Countries...")

        # Supported countries
        countries = {
            "RO": "Romania (+40)",
            "US": "United States (+1)",
            "UK": "United Kingdom (+44)",
            "DE": "Germany (+49)",
            "FR": "France (+33)",
            "IT": "Italy (+39)",
            "ES": "Spain (+34)",
            "NL": "Netherlands (+31)"
        }

        print('✅ Supported in ' + str(len(countries)) + ' countries:')
        for _code, name in countries.items():
            print('  • ' + name)

        print("\n🎯 Available API Endpoints:")
        print("  POST /api/v1/sms/send                - Send SMS message")
        print("  POST /api/v1/sms/send/order-confirmation - Send order confirmation")
        print("  POST /api/v1/sms/send/order-shipped    - Send shipping notification")
        print("  POST /api/v1/sms/send/payment-confirmation - Send payment confirmation")
        print("  POST /api/v1/sms/send/inventory-alert - Send inventory alert")
        print("  POST /api/v1/sms/send/bulk            - Send bulk SMS")
        print("  GET  /api/v1/sms/providers            - List SMS providers")
        print("  GET  /api/v1/sms/statistics           - Get SMS statistics")
        print("  GET  /api/v1/sms/templates            - List SMS templates")
        print("  POST /api/v1/sms/templates/preview    - Preview template")
        print("  GET  /api/v1/sms/countries            - List supported countries")
        print("  POST /api/v1/sms/test                 - Test SMS service")

        print("\n📝 API Usage Examples:")
        print("  Send Order Confirmation:")
        print(
            "  curl -X POST 'http://localhost:8000/api/v1/sms/send/"
            "order-confirmation' \\"
        )
        print("       -H 'Content-Type: application/json' \\")
        print(
            "       -d '{\"phone_number\": \"+40700123456\", \"order_id\": "
            "\"EMAG-123\", \"amount\": 250.75}'"
        )

        print("\n  Send Bulk SMS:")
        print(
            "  curl -X POST 'http://localhost:8000/api/v1/sms/send/"
            "bulk' \\"
        )
        print("       -H 'Content-Type: application/json' \\")
        print(
            "       -d '{\"phone_numbers\": [\"+40700123456\", \"+40700123457\"], "
            "\"message\": \"Sale! 20% off\"}'"
        )

        print("\n  Preview Template:")
        print(
            "  curl -X POST 'http://localhost:8000/api/v1/sms/templates/"
            "preview' \\"
        )
        print("       -H 'Content-Type: application/json' \\")
        print(
            "       -d '{\"notification_type\": \"order_confirmation\", "
            "\"variables\": {\"order_id\": \"123\", \"amount\": \"100.50\"}}'"
        )

        print("\n✅ SMS Notifications Demo completed successfully!")

    except Exception as e:
        print('❌ Error during demonstration: ' + str(e))
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        await sms_service.cleanup()


def demonstrate_configuration():
    """Show SMS configuration examples."""

    print("\n⚙️  SMS Provider Configuration:")
    print("=" * 35)

    print("\n1️⃣ Twilio Configuration:")
    print("  TWILIO_ACCOUNT_SID=AC123...")
    print("  TWILIO_AUTH_TOKEN=sk_456...")
    print("  TWILIO_SENDER_ID=MagFlow")
    print("  TWILIO_TEST_MODE=true")

    print("\n2️⃣ MessageBird Configuration:")
    print("  MESSAGEBIRD_API_KEY=123abc...")
    print("  MESSAGEBIRD_SENDER_ID=MagFlow")
    print("  MESSAGEBIRD_TEST_MODE=true")

    print("\n3️⃣ SMS Settings:")
    print("  SMS_DEFAULT_PROVIDER=twilio")
    print("  SMS_RATE_LIMIT_PER_MINUTE=60")
    print("  SMS_MAX_MESSAGE_LENGTH=160")
    print("  SMS_SUPPORTED_COUNTRIES=RO,US,UK,DE,FR")

    print("\n📋 Configuration Files:")
    print("  • Environment variables (.env)")
    print("  • Settings in app/core/config.py")
    print("  • Provider-specific configuration")


def demonstrate_emag_integration():
    """Show eMAG marketplace SMS integration examples."""

    print("\n🔗 eMAG Marketplace Integration:")
    print("=" * 35)

    print("\n📱 eMAG Order Notifications:")
    print("  • Order Confirmation SMS")
    print("  • Payment Confirmation SMS")
    print("  • Shipping Notification SMS")
    print("  • Delivery Confirmation SMS")

    print("\n🚨 eMAG Alerts:")
    print("  • Low Stock Alerts")
    print("  • Price Change Notifications")
    print("  • Promotion Announcements")
    print("  • Order Status Updates")

    print("\n⚡ Automated Workflows:")
    print("  • Automatic order confirmation on eMAG order")
    print("  • Inventory alerts when stock is low")
    print("  • Payment confirmation after successful payment")
    print("  • Shipping notifications when order is dispatched")

    print("\n🌐 Multi-language Support:")
    print("  • Romanian (RO) - Native language")
    print("  • English (EN) - International")
    print("  • Templates for all notification types")
    print("  • Automatic language detection")


async def main():
    """Main demonstration function."""

    print("🎯 SMS Notifications - MagFlow ERP")
    print("=" * 40)
    print("\nThis demonstration shows comprehensive SMS notifications with:")
    print("• Twilio & MessageBird integration")
    print("• Template-based messaging")
    print("• Multi-language support (EN/RO)")
    print("• eMAG marketplace integration")
    print("• Bulk messaging capabilities")
    print("• Real-time delivery tracking")

    # Show configuration first
    demonstrate_configuration()

    # Show eMAG integration
    demonstrate_emag_integration()

    # Run the SMS demonstration
    await demonstrate_sms_notifications()

    print("\n" + "=" * 40)
    print("🎉 SMS Notifications demonstration completed!")
    print("💡 Next Steps:")
    print("  1. Configure your SMS provider credentials")
    print("  2. Set up phone number verification")
    print("  3. Test with real SMS messages")
    print("  4. Integrate with eMAG order workflow")
    print("  5. Monitor delivery statistics")
    print("\n📚 API Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())

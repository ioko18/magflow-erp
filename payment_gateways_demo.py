"""
Payment Gateways Demo - MagFlow ERP Integration

This script demonstrates the comprehensive payment gateways integration
including Stripe, PayPal, and bank transfers for processing payments,
handling refunds, and managing transactions.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal

from app.services.payment_service import (
    PaymentService, PaymentGatewayType, PaymentMethod, PaymentStatus
)
from app.core.dependency_injection import ServiceContext
from app.core.config import get_settings


async def demonstrate_payment_gateways():
    """Demonstrate payment gateways functionality."""

    print("💳 Payment Gateways Integration - MagFlow ERP")
    print("=" * 50)

    # Initialize the payment service
    settings = get_settings()
    context = ServiceContext(settings=settings)
    payment_service = PaymentService(context)

    await payment_service.initialize()

    try:
        print("\n📊 Getting Supported Payment Gateways...")

        # Get supported gateways
        gateways = await payment_service.get_supported_gateways()

        print(f"✅ Found {len(gateways)} configured payment gateways:")
        for gateway in gateways:
            print(f"  • {gateway['name']} ({gateway['type']})")
            print(f"    - Test Mode: {gateway['test_mode']}")
            print(f"    - Currencies: {', '.join(gateway['supported_currencies'])}")
            print(f"    - Amount Range: {gateway['min_amount']} - {gateway['max_amount']}")

        print("\n💰 Creating Payment Transactions...")

        # Create test payment transactions
        test_payments = [
            {
                "gateway": PaymentGatewayType.STRIPE,
                "amount": Decimal('100.00'),
                "currency": "RON",
                "order_id": "order_001",
                "customer_email": "customer1@example.com",
                "description": "Payment for electronics"
            },
            {
                "gateway": PaymentGatewayType.PAYPAL,
                "amount": Decimal('250.50'),
                "currency": "EUR",
                "order_id": "order_002",
                "customer_email": "customer2@example.com",
                "description": "Payment for furniture"
            },
            {
                "gateway": PaymentGatewayType.BANK_TRANSFER,
                "amount": Decimal('75.25'),
                "currency": "RON",
                "order_id": "order_003",
                "customer_email": "customer3@example.com",
                "description": "Payment for books"
            }
        ]

        transactions = []
        for i, payment in enumerate(test_payments, 1):
            try:
                print(f"  Creating payment {i}/3: {payment['description']} ({payment['amount']} {payment['currency']})")

                transaction = await payment_service.create_payment(
                    gateway_type=payment["gateway"],
                    amount=payment["amount"],
                    currency=payment["currency"],
                    order_id=payment["order_id"],
                    customer_email=payment["customer_email"],
                    description=payment["description"],
                    payment_method=PaymentMethod.CREDIT_CARD,
                    metadata={"test": True, "demo": True}
                )

                transactions.append(transaction)
                print(f"    ✅ Created transaction {transaction.id}")
                print(f"       Gateway Transaction ID: {transaction.gateway_transaction_id}")
                print(f"       Status: {transaction.status.value}")

            except Exception as e:
                print(f"    ❌ Failed to create payment: {e}")

        print("
🔄 Processing Payments..."
        # Process the payments
        for i, transaction in enumerate(transactions, 1):
            try:
                print(f"  Processing payment {i}/{len(transactions)}: {transaction.description}")

                processed_transaction = await payment_service.process_payment(
                    transaction_id=transaction.id,
                    payment_method=PaymentMethod.CREDIT_CARD,
                    payment_data={
                        "order_id": transaction.order_id,
                        "payment_method_id": f"pm_test_{i}",
                        "amount": float(transaction.amount)
                    }
                )

                print(f"    ✅ Payment processed successfully")
                print(f"       Status: {processed_transaction.status.value}")
                print(f"       Completed at: {processed_transaction.completed_at}")

            except Exception as e:
                print(f"    ❌ Failed to process payment: {e}")

        print("
🔍 Getting Payment Status..."
        # Check payment status
        for i, transaction in enumerate(transactions, 1):
            try:
                print(f"  Checking status {i}/{len(transactions)}: Transaction {transaction.id}")

                status_transaction = await payment_service.get_payment_status(transaction.id)

                print(f"    ✅ Status: {status_transaction.status.value}")
                print(f"       Amount: {status_transaction.amount} {status_transaction.currency}")
                print(f"       Gateway Status: {status_transaction.gateway_response.get('status', 'unknown')}")

            except Exception as e:
                print(f"    ❌ Failed to get payment status: {e}")

        print("
💸 Testing Refund Functionality..."
        # Test refund for the first successful transaction
        if transactions:
            try:
                print(f"  Processing refund for transaction {transactions[0].id}")

                refund_transaction = await payment_service.refund_payment(
                    transaction_id=transactions[0].id,
                    amount=Decimal('25.00'),
                    reason="Customer requested partial refund"
                )

                print(f"    ✅ Refund processed successfully")
                print(f"       Refund Amount: {refund_transaction.refund_amount}")
                print(f"       Status: {refund_transaction.status.value}")

            except Exception as e:
                print(f"    ❌ Failed to process refund: {e}")

        print("
📊 Payment Methods Available..."
        # Get supported payment methods
        methods = {
            "credit_card": {
                "name": "Credit Card",
                "gateways": ["Stripe", "PayPal"],
                "processing_time": "Instant",
                "fees": "2.9% + 0.30 RON"
            },
            "paypal": {
                "name": "PayPal",
                "gateways": ["PayPal"],
                "processing_time": "Instant",
                "fees": "3.4% + 0.35 RON"
            },
            "bank_transfer": {
                "name": "Bank Transfer",
                "gateways": ["Bank Transfer"],
                "processing_time": "1-3 days",
                "fees": "No fees"
            }
        }

        print(f"✅ Available payment methods: {len(methods)}")
        for method_id, method_info in methods.items():
            print(f"  • {method_info['name']}")
            print(f"    - Supported by: {', '.join(method_info['gateways'])}")
            print(f"    - Processing: {method_info['processing_time']}")
            print(f"    - Fees: {method_info['fees']}")

        print("
📈 Payment Statistics (Demo Data)...")

        # Mock statistics
        stats = {
            "total_transactions": 1250,
            "successful_transactions": 1180,
            "failed_transactions": 70,
            "refunded_transactions": 45,
            "total_volume": 125000.00,
            "success_rate": 94.4,
            "average_transaction": 100.00,
            "gateway_performance": {
                "stripe": {"success_rate": 96.5, "transactions": 850},
                "paypal": {"success_rate": 92.3, "transactions": 300},
                "bank_transfer": {"success_rate": 85.0, "transactions": 100}
            }
        }

        print(f"  • Total Transactions: {stats['total_transactions']}")
        print(f"  • Success Rate: {stats['success_rate']}%")
        print(f"  • Total Volume: {stats['total_volume']} RON")
        print(f"  • Average Transaction: {stats['average_transaction']} RON")
        print("
  Gateway Performance:"        for gateway, perf in stats['gateway_performance'].items():
            print(f"    - {gateway.title()}: {perf['success_rate']}% success rate ({perf['transactions']} transactions)")

        print("
🎯 Available API Endpoints:"        print("  POST /api/v1/payments/create     - Create payment transaction")
        print("  POST /api/v1/payments/process/{id} - Process payment")
        print("  POST /api/v1/payments/refund/{id}  - Refund payment")
        print("  GET  /api/v1/payments/status/{id}  - Get payment status")
        print("  POST /api/v1/payments/webhook/{type} - Handle webhook")
        print("  GET  /api/v1/payments/gateways     - List payment gateways")
        print("  GET  /api/v1/payments/transactions - List transactions")
        print("  GET  /api/v1/payments/methods      - List payment methods")
        print("  GET  /api/v1/payments/statistics   - Get statistics")

        print("
📝 API Usage Examples:"
        print("  Create Payment:")
        print("  curl -X POST 'http://localhost:8000/api/v1/payments/create' \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"gateway_type\": \"stripe\", \"amount\": 100.00, \"currency\": \"RON\", ...}'")

        print("
  Process Payment:"        print("  curl -X POST 'http://localhost:8000/api/v1/payments/process/txn_123' \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"payment_method\": \"credit_card\", \"payment_method_id\": \"pm_456\"}'")

        print("
  Get Payment Status:"        print("  curl 'http://localhost:8000/api/v1/payments/status/txn_123'")

        print("
✅ Payment Gateways Demo completed successfully!"
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        await payment_service.cleanup()


def demonstrate_configuration():
    """Show payment gateway configuration examples."""

    print("
⚙️  Payment Gateway Configuration:"    print("=" * 35)

    print("\n1️⃣ Stripe Configuration:")
    print("  STRIPE_API_KEY=sk_test_...")
    print("  STRIPE_PUBLIC_KEY=pk_test_...")
    print("  STRIPE_WEBHOOK_SECRET=whsec_...")
    print("  STRIPE_TEST_MODE=true")

    print("\n2️⃣ PayPal Configuration:")
    print("  PAYPAL_CLIENT_ID=your_client_id")
    print("  PAYPAL_CLIENT_SECRET=your_client_secret")
    print("  PAYPAL_TEST_MODE=true")

    print("\n3️⃣ Bank Transfer Configuration:")
    print("  BANK_NAME=Banca Transilvania")
    print("  BANK_ACCOUNT=RO49BTRLRONCRT1234567890")
    print("  BANK_HOLDER=MagFlow ERP SRL")

    print("\n📋 Configuration Files:")
    print("  • Environment variables (.env)")
    print("  • Settings in app/core/config.py")
    print("  • Gateway-specific configuration files")


async def main():
    """Main demonstration function."""

    print("🎯 Payment Gateways Integration - MagFlow ERP")
    print("=" * 55)
    print("\nThis demonstration shows comprehensive payment processing with:")
    print("• Stripe - Credit card processing")
    print("• PayPal - Digital wallet payments")
    print("• Bank Transfer - Traditional banking")
    print("\nKey Features:")
    print("• Multi-gateway support")
    print("• Payment processing")
    print("• Refund management")
    print("• Status tracking")
    print("• Webhook handling")
    print("• Statistics and analytics")

    # Show configuration first
    demonstrate_configuration()

    # Run the payment demonstration
    await demonstrate_payment_gateways()

    print("\n" + "=" * 55)
    print("🎉 Payment Gateways demonstration completed!")
    print("💡 Next Steps:")
    print("  1. Configure your payment gateway credentials")
    print("  2. Test with real payment data")
    print("  3. Set up webhook endpoints")
    print("  4. Monitor payment analytics")
    print("  5. Integrate with order management")
    print("\n📚 API Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())

# eMAG Integration - Quick Reference Guide

## 🚀 Quick Start

### Run Tests
```bash
python3 test_emag_improvements.py
```

### Start Backend
```bash
./start_dev.sh backend
```

### Start Frontend
```bash
cd admin-frontend && npm run dev
```

---

## 📦 New Modules

### 1. Constants (`app/core/emag_constants.py`)
```python
from app.core.emag_constants import (
    OrderStatus,
    CANCELLATION_REASONS,
    get_cancellation_reason_text,
    get_order_status_text,
    get_payment_mode_text,
)

# Usage
reason = get_cancellation_reason_text(31)
status = get_order_status_text(OrderStatus.FINALIZED.value)
```

### 2. Monitoring (`app/core/emag_monitoring.py`)
```python
from app.core.emag_monitoring import get_monitor

monitor = get_monitor()
monitor.start_sync("orders")

# Record requests
monitor.record_request(
    endpoint="/order/read",
    method="GET",
    status_code=200,
    response_time_ms=245.5,
    account_type="main",
    success=True
)

# Get health
health = monitor.get_health_status()
print(health['status'])  # 'healthy', 'warning', or 'error'

monitor.end_sync()
```

---

## 🔧 API Usage

### Sync Orders
```python
from app.services.enhanced_emag_service import EnhancedEmagIntegrationService

async with EnhancedEmagIntegrationService("main") as service:
    # Sync all orders from both accounts
    results = await service.sync_all_orders_from_both_accounts(
        max_pages_per_account=50,
        delay_between_requests=1.2,
        status_filter="1"  # 1=new, 2=in_progress, 3=prepared, 4=finalized
    )
    
    print(f"MAIN: {results['main_account']['orders_count']} orders")
    print(f"FBE: {results['fbe_account']['orders_count']} orders")
    print(f"Total: {results['combined']['total_orders']} orders")
```

### Error Handling
```python
from app.services.emag_api_client import EmagApiClient, EmagApiError

try:
    async with EmagApiClient(username, password) as client:
        orders = await client.get_orders()
except EmagApiError as e:
    if e.is_rate_limit_error:
        # Automatic retry will occur
        pass
    elif e.is_auth_error:
        # Check credentials
        logger.error("Auth failed")
    elif e.is_validation_error:
        # Check request parameters
        logger.error("Validation failed")
```

---

## 📊 Order Status Codes

| Code | Status | Romanian |
|------|--------|----------|
| 0 | CANCELED | Anulată |
| 1 | NEW | Nouă |
| 2 | IN_PROGRESS | În procesare |
| 3 | PREPARED | Pregătită |
| 4 | FINALIZED | Finalizată |
| 5 | RETURNED | Returnată |

---

## 🚫 Cancellation Reasons (Top 10)

| Code | Reason (Romanian) |
|------|-------------------|
| 1 | Lipsă stoc |
| 2 | Anulat de client |
| 3 | Clientul nu poate fi contactat |
| 23 | Clientul s-a răzgândit |
| 24 | La solicitarea clientului |
| 31 | Partener Marketplace eMAG a cerut anularea |
| 33 | Produsul nu mai este disponibil în stocul partenerului |
| 38 | Clientul s-a răzgândit, nu mai dorește produsul |

[See all 28 reasons in `app/core/emag_constants.py`]

---

## 💳 Payment Modes

| Code | Method | Romanian |
|------|--------|----------|
| 1 | COD | Numerar la livrare |
| 2 | Bank Transfer | Transfer bancar |
| 3 | Card Online | Plată cu cardul online |

---

## 🚚 Delivery Methods

- **courier**: Livrare la domiciliu
- **pickup**: Ridicare din locker/punct de colectare

---

## 📈 Monitoring Thresholds

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Error Rate | >5% | Error |
| Response Time | >2000ms | Warning |
| Rate Limit Usage | >80% | Warning |
| Success Rate | <95% | Error |

---

## 🔐 Rate Limits

| Resource | RPS | RPM |
|----------|-----|-----|
| Orders | 12 | 720 |
| Products | 3 | 180 |
| Offers | 3 | 180 |
| Other | 3 | 180 |

---

## 🎯 Frontend Pages

### Orders Page Enhancements
- ✅ eMAG Order ID display
- ✅ Sync status badges (synced, pending, failed)
- ✅ Payment method and status
- ✅ Delivery method and tracking
- ✅ Fulfillment type (FBE/FBS)
- ✅ Expandable rows with eMAG details
- ✅ Sync error alerts

### Access
- **URL**: http://localhost:5173
- **Login**: admin@example.com / secret
- **Pages**: eMAG Integration, Products, Orders, Customers

---

## 🧪 Testing

### Run All Tests
```bash
python3 test_emag_improvements.py
```

### Expected Output
```
✅ PASSED: Constants & Enumerations
✅ PASSED: Monitoring & Metrics
✅ PASSED: API Client Enhancements
✅ PASSED: Service Methods
✅ PASSED: Module Imports
✅ PASSED: Documentation

Total: 6/6 tests passed (100.0%)
```

---

## 📝 Logging Format

All requests are logged in JSON format:
```json
{
  "timestamp": "2025-09-29T21:00:00Z",
  "level": "INFO",
  "service": "emag_integration",
  "request": {
    "method": "POST",
    "endpoint": "/order/read",
    "account_type": "main"
  },
  "response": {
    "status_code": 200,
    "response_time_ms": 245.5,
    "success": true
  }
}
```

---

## 🔍 Troubleshooting

### Rate Limit Errors (429)
- Automatic retry with exponential backoff
- Max wait time: 64 seconds
- Jitter: 0-100ms

### Authentication Errors (401/403)
- Check credentials in `.env`
- Verify IP whitelisting in eMAG dashboard
- Ensure Basic Auth header is correct

### Validation Errors (400)
- Check request parameters
- Verify data types
- Review eMAG API v4.4.8 documentation

---

## 📚 Documentation

- **Full Guide**: `docs/EMAG_FULL_SYNC_GUIDE.md`
- **Implementation Summary**: `EMAG_IMPROVEMENTS_SUMMARY.md`
- **This Guide**: `QUICK_REFERENCE_EMAG.md`

---

## 🆘 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review test output: `python3 test_emag_improvements.py`
3. Check monitoring: `monitor.get_health_status()`
4. Review API documentation: http://localhost:8000/docs

---

**Last Updated:** 2025-09-29  
**Version:** 2.0  
**Status:** Production Ready ✅

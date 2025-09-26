---
title: eMAG Integration Overview
last_reviewed: 2025-09-25
owner: integrations-team
---

# eMAG Integration Overview

## Summary

MagFlow ERP integrates with the eMAG marketplace to handle returns (RMA), order
cancellations, invoice management, and synchronized product offers. This document
consolidates the previous `EMAG_INTEGRATION_READY.md`, `EMAG_INTEGRATION_COMPLETE.md`,
and `EMAG_INTEGRATION_CONFIG.md` files.

## Supported Flows

| Flow | Purpose | Key Endpoints |
| --- | --- | --- |
| RMA Management | Create, update, and track returns | `/rma/create`, `/rma/update_status`, `/rma/{id}` |
| Order Cancellations | Process cancellations and refunds | `/order/cancel`, `/order/process_refund` |
| Invoice Management | Create invoices and track payment status | `/invoice/create`, `/invoice/update_payment`, `/invoice/{id}` |
| Product Offers | Sync catalog offers | `/product_offer/read`, `/product_offer/save`, `/product_offer/count` |

## Architecture

- **Client**: `app/emag/emag_client_complete.py`
- **Services**: `app/integrations/emag/services.py`
- **API Endpoints**: `app/api/v1/endpoints/emag/integration.py`

## Configuration

```bash
EMAG_USERNAME=your_emag_username
EMAG_PASSWORD=your_emag_api_key
EMAG_BASE_URL=https://marketplace-api.emag.ro/api-3
EMAG_ACCOUNT_TYPE=main  # or fbe
```

Required tables: `app.emag_return_integrations`,
`app.emag_cancellation_integrations`, `app.emag_invoice_integrations`.
Implement `get_auth_token()` in `emag_client_complete.py` with the production
OAuth logic.

## Testing

```bash
curl -X POST "http://localhost:8000/api/v1/emag/integration/test-connection" \
  -H "Content-Type: application/json" \
  -d '{"account_type": "main"}'

curl http://localhost:8000/api/v1/emag/integration/configuration
curl http://localhost:8000/api/v1/emag/integration/flows
```

## Usage Example

```python
from app.integrations.emag.services import (
    EmagRMAIntegration,
    EmagCancellationIntegration,
    EmagInvoiceIntegration,
)

async def create_return(return_request):
    rma_service = EmagRMAIntegration()
    return await rma_service.create_return_request(return_request)
```

## Rate Limits & Timeouts

- Orders: 12 req/s
- Returns: 5 req/s
- Offers: 3 req/s
- Invoices: 3 req/s
- Request timeout: 30 s
- Connect timeout: 10 s

## Business Impact

- Automates eMAG workflows, reduces manual data entry, and improves data accuracy.

## Related Documents

- `docs/EMAG_FULL_SYNC_GUIDE.md`
- `docs/EMAG_CREDENTIALS_TESTING_GUIDE.md`
- `docs/emag_api_documentation.md`
- `docs/integrations/emag/catalog.md`
- `docs/integrations/emag/vat_service.md`

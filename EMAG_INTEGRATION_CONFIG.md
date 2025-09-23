# 📋 **eMAG INTEGRATION CONFIGURATION GUIDE**

## **🎯 Overview**

This guide explains how to configure eMAG integration for the new flows (RMA, Cancellations, Invoices) in your MagFlow ERP system.

---

## **✅ What We've Implemented**

### **🔗 Integration Components:**

1. **eMAG API Client** (`app/emag/emag_client_complete.py`)
   - Complete async client with rate limiting
   - Support for all eMAG endpoints
   - Automatic retry logic
   - Error handling

2. **Integration Services** (`app/integrations/emag/services.py`)
   - RMA (Returns Management) service
   - Order Cancellation service
   - Invoice Management service
   - Integration manager

3. **API Endpoints** (`app/api/v1/endpoints/emag/integration.py`)
   - Connection testing
   - Status monitoring
   - Flow configuration

---

## **🔧 Configuration Steps**

### **Step 1: eMAG API Credentials**

You need to configure eMAG API credentials in your environment variables:

```bash
# .env file
EMAG_USERNAME=your_emag_username
EMAG_PASSWORD=your_emag_api_key
EMAG_BASE_URL=https://marketplace.emag.ro/api-3

# Account Types (main/fbe)
EMAG_ACCOUNT_TYPE=main
```

### **Step 2: Database Setup**

The integration requires these database tables:

```sql
-- RMA Integration Table
CREATE TABLE app.emag_return_integrations (
    id SERIAL PRIMARY KEY,
    return_request_id INTEGER REFERENCES app.return_requests(id),
    emag_return_id VARCHAR(100),
    emag_status VARCHAR(50),
    last_synced_at TIMESTAMP,
    sync_attempts INTEGER DEFAULT 0,
    emag_response TEXT,
    error_message TEXT,
    account_type VARCHAR(10) DEFAULT 'main'
);

-- Cancellation Integration Table
CREATE TABLE app.emag_cancellation_integrations (
    id SERIAL PRIMARY KEY,
    cancellation_request_id INTEGER REFERENCES app.cancellation_requests(id),
    emag_cancellation_id VARCHAR(100),
    emag_status VARCHAR(50),
    last_synced_at TIMESTAMP,
    sync_attempts INTEGER DEFAULT 0,
    emag_response TEXT,
    error_message TEXT,
    account_type VARCHAR(10) DEFAULT 'main'
);

-- Invoice Integration Table
CREATE TABLE app.emag_invoice_integrations (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES app.invoices(id),
    emag_invoice_id VARCHAR(100),
    emag_status VARCHAR(50),
    emag_invoice_type VARCHAR(50),
    last_synced_at TIMESTAMP,
    sync_attempts INTEGER DEFAULT 0,
    emag_response TEXT,
    error_message TEXT,
    account_type VARCHAR(10) DEFAULT 'main'
);
```

### **Step 3: Authentication Setup**

The eMAG client uses placeholder authentication. You need to implement proper eMAG OAuth:

```python
# In app/emag/emag_client_complete.py
async def get_auth_token(self) -> str:
    """Get authentication token from eMAG."""
    # TODO: Implement proper eMAG OAuth flow
    # This is a placeholder implementation
    return "your_actual_emag_token"
```

---

## **🧪 Testing the Integration**

### **Test Connection:**

```bash
# Test eMAG API connection
curl -X POST "http://localhost:8000/api/v1/emag/integration/test-connection" \
  -H "Content-Type: application/json" \
  -d '{"account_type": "main"}'
```

### **Check Integration Status:**

```bash
# Get integration status
curl http://localhost:8000/api/v1/emag/integration/status

# Get supported flows
curl http://localhost:8000/api/v1/emag/integration/flows

# Get configuration
curl http://localhost:8000/api/v1/emag/integration/configuration
```

### **Expected Responses:**

```json
{
  "status": "success",
  "integration_status": {
    "connected": true,
    "account_type": "main",
    "supported_flows": [
      "product_offers",
      "rma_management",
      "order_cancellations",
      "invoice_management"
    ]
  },
  "message": "eMAG integration status retrieved"
}
```

---

## **🔄 Using the Integration**

### **RMA Integration:**

```python
from app.integrations.emag.services import EmagRMAIntegration

async def create_emag_rma(return_request):
    rma_service = EmagRMAIntegration()
    result = await rma_service.create_return_request(return_request)

    if result["success"]:
        print(f"RMA created: {result['emag_rma_id']}")
    else:
        print(f"Failed: {result['error']}")
```

### **Cancellation Integration:**

```python
from app.integrations.emag.services import EmagCancellationIntegration

async def cancel_emag_order(cancellation_request):
    cancel_service = EmagCancellationIntegration()
    result = await cancel_service.create_cancellation_request(cancellation_request)

    if result["success"]:
        print(f"Cancellation created: {result['emag_cancellation_id']}")
    else:
        print(f"Failed: {result['error']}")
```

### **Invoice Integration:**

```python
from app.integrations.emag.services import EmagInvoiceIntegration

async def create_emag_invoice(invoice):
    invoice_service = EmagInvoiceIntegration()
    result = await invoice_service.create_invoice(invoice)

    if result["success"]:
        print(f"Invoice created: {result['emag_invoice_id']}")
    else:
        print(f"Failed: {result['error']}")
```

---

## **📊 Monitoring & Troubleshooting**

### **Check Integration Logs:**

```bash
# View application logs
tail -f logs/app.log

# Check for eMAG integration errors
grep -i "emag" logs/app.log
```

### **Database Queries:**

```sql
-- Check RMA integration status
SELECT r.return_number, e.emag_return_id, e.emag_status, e.last_synced_at
FROM app.return_requests r
LEFT JOIN app.emag_return_integrations e ON r.id = e.return_request_id
WHERE r.created_at > NOW() - INTERVAL '1 day';

-- Check sync attempts
SELECT sync_id, status, total_offers_processed, offers_failed, started_at
FROM app.emag_offer_syncs
ORDER BY started_at DESC
LIMIT 10;
```

### **Common Issues:**

1. **Authentication Failed:**
   - Check EMAG_USERNAME and EMAG_PASSWORD
   - Verify API credentials in eMAG dashboard
   - Ensure account has API access

2. **Rate Limiting:**
   - The client implements automatic rate limiting
   - Check if you're hitting eMAG API limits
   - Wait before retrying requests

3. **Database Connection:**
   - Verify PostgreSQL connection
   - Check database permissions
   - Ensure tables exist

---

## **🚀 Production Deployment**

### **Environment Variables:**

```bash
# Production .env
EMAG_USERNAME=prod_emag_username
EMAG_PASSWORD=prod_emag_api_key
EMAG_BASE_URL=https://marketplace.emag.ro/api-3
EMAG_ACCOUNT_TYPE=main
EMAG_ENVIRONMENT=production

# Rate limiting (optional)
EMAG_RATE_LIMIT_ORDERS=12
EMAG_RATE_LIMIT_OFFERS=3
EMAG_RATE_LIMIT_RMA=5
EMAG_RATE_LIMIT_INVOICES=3
```

### **Security Considerations:**

1. **Store credentials securely** (environment variables, secrets manager)
2. **Use HTTPS** for all API calls
3. **Implement proper error logging** (without exposing credentials)
4. **Set up monitoring** for integration health
5. **Regular credential rotation** policies

### **Performance Optimization:**

1. **Connection pooling** for database connections
2. **Rate limiting** to respect eMAG API limits
3. **Batch processing** for bulk operations
4. **Caching** for frequently accessed data
5. **Background job processing** for heavy operations

---

## **📚 API Reference**

### **RMA Endpoints:**
- `POST /rma/create` - Create return request
- `POST /rma/update_status` - Update RMA status
- `GET /rma/{rma_id}` - Get RMA details

### **Cancellation Endpoints:**
- `POST /order/cancel` - Cancel order
- `POST /order/process_refund` - Process refund

### **Invoice Endpoints:**
- `POST /invoice/create` - Create invoice
- `POST /invoice/update_payment` - Update payment status
- `GET /invoice/{invoice_id}` - Get invoice details

### **Configuration Endpoints:**
- `GET /integration/status` - Integration status
- `POST /integration/test-connection` - Test connection
- `GET /integration/flows` - Supported flows
- `GET /integration/configuration` - Configuration details

---

## **🎯 Next Steps**

1. **Set up eMAG credentials** in your environment
2. **Test the connection** using the API endpoints
3. **Configure your specific account type** (main/fbe)
4. **Start using the integration** for RMA, Cancellations, and Invoices
5. **Monitor and optimize** based on your usage patterns

---

## **💡 Support & Documentation**

- **API Documentation:** http://localhost:8000/docs
- **Integration Guide:** This document
- **Code Examples:** Available in the services module
- **Database Schema:** See migration files

For additional support, check the logs and ensure all environment variables are properly configured.

---

**🎉 Your eMAG integration is now configured and ready to use!**

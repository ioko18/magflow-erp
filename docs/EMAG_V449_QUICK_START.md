# eMAG API v4.4.9 Quick Start Guide
**MagFlow ERP System**

---

## 🚀 New Features in v4.4.9

### 1. Light Offer API - Fast Stock/Price Updates

**Use Case**: Update stock or price without sending full product data

**Python Example**:
```python
from app.services.emag_api_client import EmagApiClient

async with EmagApiClient(username, password) as client:
    # Update only stock
    await client.update_offer_light(
        product_id=12345,
        stock=[{"warehouse_id": 1, "value": 50}]
    )
    
    # Update only price
    await client.update_offer_light(
        product_id=12345,
        sale_price=99.99
    )
    
    # Update both
    await client.update_offer_light(
        product_id=12345,
        sale_price=89.99,
        stock=[{"warehouse_id": 1, "value": 25}]
    )
```

**API Endpoint**: `POST /api/v1/emag/enhanced/offers/update-light`

---

### 2. EAN Search API - Find Products Before Creating

**Use Case**: Check if product exists on eMAG before creating new offer

**Python Example**:
```python
# Search by EAN
result = await client.find_products_by_eans(
    ["5941234567890", "7086812930967"]
)

for product in result['results']:
    print(f"Product: {product['product_name']}")
    print(f"Brand: {product['brand_name']}")
    print(f"Part Number Key: {product['part_number_key']}")
    print(f"Vendor has offer: {product['vendor_has_offer']}")
    print(f"Can add offer: {product['allow_to_add_offer']}")
    
    if product['vendor_has_offer']:
        print("→ Update existing offer")
    elif product['allow_to_add_offer']:
        print("→ Attach to existing product")
    else:
        print("→ Request category access")
```

**Rate Limits**: 5 req/sec, 200 req/min, 5000 req/day

---

### 3. Addresses API - Manage Pickup/Return Locations

**Use Case**: Save and reuse addresses for AWB creation

**Python Example**:
```python
# Get all addresses
addresses = await client.get_addresses()

for addr in addresses['results']:
    if addr['address_type_id'] == 2:  # Pickup address
        print(f"Pickup: {addr['city']}, {addr['address']}")
        print(f"Address ID: {addr['address_id']}")
```

**Frontend**: Navigate to **eMAG Addresses** page

**Address Types**:
- `1` = Return address
- `2` = Pickup address
- `3` = Invoice (HQ) address
- `4` = Delivery estimates address

---

### 4. AWB Creation with Saved Addresses

**Use Case**: Create AWB using saved address ID

**Python Example**:
```python
# Create AWB for order using saved pickup address
await client.create_awb(
    order_id=123456,
    sender={
        "address_id": "12345",  # Use saved address
        "name": "My Company SRL",
        "contact": "John Doe",
        "phone1": "0721234567"
    },
    receiver={
        "name": "Customer Name",
        "contact": "Customer Name",
        "phone1": "0729876543",
        "locality_id": 8801,
        "street": "Str. Customer, Nr. 5",
        "legal_entity": 0
    },
    parcel_number=1,
    cod=199.99
)
```

**Benefits**:
- Faster AWB creation
- Consistent address data
- Reduced errors

---

### 5. Stock-Only Update (PATCH)

**Use Case**: Fastest method for inventory synchronization

**Python Example**:
```python
# Update only stock using PATCH
await client.update_stock_only(
    product_id=12345,
    warehouse_id=1,
    stock_value=100
)
```

**Benefits**:
- Fastest method
- Minimal bandwidth
- No need for full offer data

---

## 📊 Workflow Examples

### Workflow 1: Create New Product with EAN Check

```python
async def create_product_with_ean_check(ean: str, product_data: dict):
    """Smart product creation with EAN check."""
    
    # Step 1: Search by EAN
    search_result = await client.find_products_by_eans([ean])
    
    if search_result['results']:
        product = search_result['results'][0]
        
        # Step 2: Check if we already have offer
        if product['vendor_has_offer']:
            print("✅ Product exists, updating offer...")
            await client.update_offer_light(
                product_id=product_data['id'],
                sale_price=product_data['price'],
                stock=product_data['stock']
            )
        
        # Step 3: Attach to existing product
        elif product['allow_to_add_offer']:
            print("✅ Attaching to existing product...")
            await client.save_product_offer({
                'id': product_data['id'],
                'part_number_key': product['part_number_key'],
                'sale_price': product_data['price'],
                'stock': product_data['stock'],
                'vat_id': 1,
                'handling_time': [{'warehouse_id': 1, 'value': 1}]
            })
        
        else:
            print("❌ Cannot add offer - request category access")
    
    else:
        # Step 4: Create new product
        print("✅ Creating new product...")
        await client.save_product_offer(product_data)
```

---

### Workflow 2: Bulk Stock Update

```python
async def bulk_stock_update(updates: list):
    """Update stock for multiple products efficiently."""
    
    for update in updates:
        # Use Light Offer API for speed
        await client.update_offer_light(
            product_id=update['id'],
            stock=[{
                'warehouse_id': 1,
                'value': update['stock']
            }]
        )
        
        # Rate limiting
        await asyncio.sleep(0.4)  # ~3 requests per second
```

---

### Workflow 3: Order Processing with AWB

```python
async def process_order_with_awb(order_id: int, pickup_address_id: str):
    """Complete order processing workflow."""
    
    # Step 1: Read order
    order = await client.get_order_by_id(order_id)
    
    # Step 2: Acknowledge order (status 1 → 2)
    await client.acknowledge_order(order_id)
    
    # Step 3: Process order (your business logic)
    # ... pick, pack, prepare ...
    
    # Step 4: Mark as prepared (status 2 → 3)
    await client.save_order({
        'id': order_id,
        'status': 3
    })
    
    # Step 5: Create AWB (automatically sets status to 4)
    awb = await client.create_awb(
        order_id=order_id,
        sender={
            'address_id': pickup_address_id,  # Use saved address
            'name': 'My Company',
            'contact': 'John Doe',
            'phone1': '0721234567'
        },
        receiver=order['customer'],
        parcel_number=1,
        cod=order['total']
    )
    
    # Step 6: Attach invoice
    await client.attach_invoice(
        order_id=order_id,
        invoice_url='https://example.com/invoices/123.pdf'
    )
    
    print(f"✅ Order processed, AWB: {awb['results']['awb_number']}")
```

---

## 🎯 Best Practices

### 1. Use Light Offer API for Updates
✅ **DO**: Use `update_offer_light()` for stock/price changes  
❌ **DON'T**: Use `save_product_offer()` with full data for simple updates

### 2. Check EAN Before Creating Products
✅ **DO**: Search by EAN first to avoid duplicates  
❌ **DON'T**: Create products without checking if they exist

### 3. Cache Addresses Locally
✅ **DO**: Fetch addresses once and cache for 1 hour  
❌ **DON'T**: Fetch addresses on every AWB creation

### 4. Use Saved Addresses for AWB
✅ **DO**: Use `address_id` for consistent addresses  
❌ **DON'T**: Manually enter address details every time

### 5. Respect Rate Limits
✅ **DO**: Implement proper rate limiting (3 req/sec for most operations)  
❌ **DON'T**: Send requests without delays

---

## 🔧 Configuration

### Environment Variables

```bash
# MAIN Account
EMAG_MAIN_USERNAME=your_username
EMAG_MAIN_PASSWORD=your_password
EMAG_MAIN_BASE_URL=https://marketplace-api.emag.ro/api-3

# FBE Account
EMAG_FBE_USERNAME=your_fbe_username
EMAG_FBE_PASSWORD=your_fbe_password
EMAG_FBE_BASE_URL=https://marketplace-api.emag.ro/api-3
```

---

## 📱 Frontend Usage

### Access eMAG Addresses Page

1. Login to MagFlow ERP
2. Navigate to **eMAG** → **Addresses**
3. View pickup and return addresses
4. Use address IDs when creating AWBs

### View Address Details

- **Address ID**: Unique identifier for API calls
- **Type**: Pickup, Return, Invoice, or Delivery Estimates
- **Default**: Marked with badge
- **Location**: Full address details

---

## 🧪 Testing

### Run Test Script

```bash
# Test all v4.4.9 features
python scripts/test_emag_v449_features.py
```

### Manual Testing

```python
# Test in Python console
import asyncio
from app.services.emag_api_client import EmagApiClient
from app.config.emag_config import get_emag_config

async def test():
    config = get_emag_config("main")
    async with EmagApiClient(
        username=config.api_username,
        password=config.api_password,
        base_url=config.base_url
    ) as client:
        # Test Light Offer API
        result = await client.update_offer_light(
            product_id=12345,
            stock=[{"warehouse_id": 1, "value": 50}]
        )
        print(result)

asyncio.run(test())
```

---

## 📚 Additional Resources

- **Full API Reference**: `/docs/EMAG_API_REFERENCE.md`
- **Implementation Status**: `/EMAG_V4.4.9_IMPLEMENTATION_STATUS.md`
- **Test Script**: `/scripts/test_emag_v449_features.py`

---

## 🆘 Troubleshooting

### Issue: Rate Limit Exceeded (429)
**Solution**: Implement delays between requests (0.4s for 3 req/sec)

### Issue: Address ID Not Found
**Solution**: Fetch addresses first using `get_addresses()` to get valid IDs

### Issue: EAN Search Returns Empty
**Solution**: Verify EAN format (6-14 numeric characters)

### Issue: Commission Estimate Fails
**Solution**: Endpoint might require different authentication - verify with eMAG support

---

**Last Updated**: September 30, 2025  
**API Version**: 4.4.9  
**System**: MagFlow ERP

# 🧪 Testing Guide - Sold Quantity Feature

## Quick Testing Checklist

### Backend Testing

#### 1. Test the API Endpoint
```bash
# Test with curl
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected response should include:
# - sold_last_6_months: number
# - avg_monthly_sales: number
# - sales_sources: object
```

#### 2. Verify Database Queries
```python
# Run in Python console or create test file
import asyncio
from app.db import get_db
from app.api.v1.endpoints.inventory.low_stock_suppliers import calculate_sold_quantity_last_6_months

async def test_sold_quantity():
    async for db in get_db():
        # Test with sample product IDs
        product_ids = [1, 2, 3, 4, 5]
        result = await calculate_sold_quantity_last_6_months(db, product_ids)
        
        print("Results:")
        for pid, data in result.items():
            print(f"Product {pid}:")
            print(f"  Total Sold: {data['total_sold']}")
            print(f"  Avg Monthly: {data['avg_monthly']}")
            print(f"  Sources: {data['sources']}")
        
        break

asyncio.run(test_sold_quantity())
```

#### 3. Test Edge Cases
- Products with no sales (should return 0)
- Products with sales only from eMAG
- Products with sales from multiple sources
- New products (added less than 6 months ago)
- Products with very high sales (>100/month)

### Frontend Testing

#### 1. Visual Verification
```bash
# Start the frontend
cd admin-frontend
npm run dev
```

Navigate to: `http://localhost:3000/products/low-stock-suppliers`

**Check:**
- [ ] "Sold (6m):" label appears in Stock Status column
- [ ] Quantity displays with correct color
- [ ] Icon appears based on sales velocity
- [ ] Tag shows average monthly sales (~X/mo)
- [ ] Tooltip appears on hover
- [ ] Tooltip shows all sources
- [ ] Colors match velocity (Red/Orange/Blue/Gray)

#### 2. Test Different Scenarios

**High Demand Product (≥10/month)**
- Should show: 🔥 Fire icon
- Color: Red (#ff4d4f)
- Label: "High Demand"

**Medium Demand Product (5-9/month)**
- Should show: 📈 Rise icon
- Color: Orange (#faad14)
- Label: "Medium Demand"

**Low Demand Product (1-4/month)**
- Should show: 📊 Chart icon
- Color: Blue (#1890ff)
- Label: "Low Demand"

**Very Low Demand (<1/month)**
- Should show: 📉 Fall icon
- Color: Gray (#8c8c8c)
- Label: "Very Low"

**No Sales (0)**
- Should show: No icon
- Color: Gray
- Label: "Very Low"

#### 3. Responsive Testing
- [ ] Test on desktop (1920x1080)
- [ ] Test on tablet (768x1024)
- [ ] Test on mobile (375x667)
- [ ] Check tooltip positioning
- [ ] Verify text wrapping

### Integration Testing

#### 1. Test with Real Data
```sql
-- Check if there's order data in the database
SELECT COUNT(*) FROM app.emag_orders WHERE order_date >= NOW() - INTERVAL '6 months';
SELECT COUNT(*) FROM app.sales_order_lines;
SELECT COUNT(*) FROM app.order_lines;
```

#### 2. Test Performance
```bash
# Use Apache Bench or similar tool
ab -n 100 -c 10 http://localhost:8000/api/v1/inventory/low-stock-with-suppliers

# Check response times:
# - Should be < 2 seconds for 50 products
# - Should be < 5 seconds for 200 products
```

#### 3. Test Filters
- [ ] Filter by account type (MAIN/FBE)
- [ ] Filter by stock status
- [ ] Pagination works correctly
- [ ] Sold quantity updates when filters change

### Manual Test Scenarios

#### Scenario 1: High Demand Product with Low Stock
**Setup:**
- Product with avg_monthly_sales = 15
- Available quantity = 5
- Reorder point = 20

**Expected:**
- 🔥 Fire icon (red)
- Sold (6m): 90 (red text)
- Tag: ~15/mo (red)
- Tooltip shows "High Demand"
- Visual urgency is clear

#### Scenario 2: Product with No Sales
**Setup:**
- Product with sold_last_6_months = 0
- Available quantity = 100

**Expected:**
- No icon
- Sold (6m): 0 (gray text)
- Tag: ~0/mo (gray)
- Tooltip shows "Very Low"
- Consider discontinuing product

#### Scenario 3: Multiple Sales Sources
**Setup:**
- eMAG sales: 40 units
- Sales orders: 10 units
- Generic orders: 5 units
- Total: 55 units

**Expected:**
- Tooltip breakdown shows all three sources
- Total adds up correctly
- Average calculated properly (~9.17/mo)

### Automated Test Examples

#### Backend Unit Test
```python
# tests/api/test_low_stock_suppliers.py
import pytest
from datetime import datetime, timedelta
from app.api.v1.endpoints.inventory.low_stock_suppliers import calculate_sold_quantity_last_6_months

@pytest.mark.asyncio
async def test_calculate_sold_quantity_empty_list(db_session):
    """Test with empty product list"""
    result = await calculate_sold_quantity_last_6_months(db_session, [])
    assert result == {}

@pytest.mark.asyncio
async def test_calculate_sold_quantity_no_sales(db_session, sample_product):
    """Test product with no sales"""
    result = await calculate_sold_quantity_last_6_months(db_session, [sample_product.id])
    
    assert result[sample_product.id]['total_sold'] == 0
    assert result[sample_product.id]['avg_monthly'] == 0.0
    assert result[sample_product.id]['sources'] == {}

@pytest.mark.asyncio
async def test_calculate_sold_quantity_with_emag_orders(db_session, sample_product, sample_emag_order):
    """Test with eMAG orders"""
    result = await calculate_sold_quantity_last_6_months(db_session, [sample_product.id])
    
    assert result[sample_product.id]['total_sold'] > 0
    assert 'emag' in result[sample_product.id]['sources']
    assert result[sample_product.id]['avg_monthly'] == round(result[sample_product.id]['total_sold'] / 6.0, 2)
```

#### Frontend Component Test
```typescript
// tests/pages/LowStockSuppliers.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LowStockSuppliersPage from '@/pages/products/LowStockSuppliers';

describe('LowStockSuppliers - Sold Quantity', () => {
  it('displays sold quantity with correct formatting', async () => {
    const mockProduct = {
      sold_last_6_months: 45,
      avg_monthly_sales: 7.5,
      sales_sources: { emag: 40, sales_orders: 5 }
    };
    
    render(<LowStockSuppliersPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Sold (6m):')).toBeInTheDocument();
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('~7.5/mo')).toBeInTheDocument();
    });
  });
  
  it('shows correct icon for high demand', () => {
    // Test high demand icon (≥10/month)
    // Should render FireOutlined icon
  });
  
  it('displays tooltip with sales breakdown on hover', async () => {
    const user = userEvent.setup();
    render(<LowStockSuppliersPage />);
    
    const soldQtyElement = screen.getByText('Sold (6m):');
    await user.hover(soldQtyElement);
    
    await waitFor(() => {
      expect(screen.getByText('Sales in Last 6 Months')).toBeInTheDocument();
      expect(screen.getByText(/Total Sold:/)).toBeInTheDocument();
      expect(screen.getByText(/Sources:/)).toBeInTheDocument();
    });
  });
});
```

### Performance Benchmarks

#### Expected Performance
- **API Response Time**: < 2 seconds for 50 products
- **Database Query Time**: < 500ms for sold quantity calculation
- **Frontend Render Time**: < 100ms for table update
- **Memory Usage**: < 100MB additional for calculations

#### Load Testing
```bash
# Test with 100 concurrent requests
ab -n 1000 -c 100 http://localhost:8000/api/v1/inventory/low-stock-with-suppliers

# Monitor:
# - Response times (p50, p95, p99)
# - Error rate (should be 0%)
# - Database connection pool usage
# - Memory consumption
```

### Browser Compatibility

Test in:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

### Accessibility Testing

- [ ] Keyboard navigation works
- [ ] Screen reader announces sold quantity
- [ ] Color contrast meets WCAG AA standards
- [ ] Tooltip is accessible
- [ ] Focus indicators are visible

### Data Validation

#### Check Data Accuracy
```sql
-- Manually verify sold quantity for a product
SELECT 
    p.sku,
    p.name,
    -- eMAG orders
    (SELECT COUNT(*) FROM app.emag_orders eo
     WHERE eo.products::text LIKE '%' || p.sku || '%'
     AND eo.order_date >= NOW() - INTERVAL '6 months'
     AND eo.status IN (3, 4)) as emag_orders,
    -- Sales orders
    (SELECT COALESCE(SUM(sol.quantity), 0) FROM app.sales_order_lines sol
     JOIN app.sales_orders so ON sol.sales_order_id = so.id
     WHERE sol.product_id = p.id
     AND so.order_date >= NOW() - INTERVAL '6 months'
     AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered')) as sales_qty,
    -- Generic orders
    (SELECT COALESCE(SUM(ol.quantity), 0) FROM app.order_lines ol
     JOIN app.orders o ON ol.order_id = o.id
     WHERE ol.product_id = p.id
     AND o.order_date >= NOW() - INTERVAL '6 months'
     AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed')) as order_qty
FROM app.products p
WHERE p.id = 1; -- Replace with actual product ID

-- Compare with API response
```

### Common Issues and Solutions

#### Issue 1: Sold quantity shows 0 for all products
**Possible causes:**
- No order data in database
- Date filtering too restrictive
- Status filtering excluding valid orders

**Solution:**
```sql
-- Check if there's any order data
SELECT COUNT(*), MIN(order_date), MAX(order_date) FROM app.emag_orders;
```

#### Issue 2: Tooltip not showing
**Possible causes:**
- CSS z-index conflict
- Ant Design Tooltip not configured
- Missing contextHolder

**Solution:**
Check that notification contextHolder is rendered in component

#### Issue 3: Performance issues with large datasets
**Possible causes:**
- No database indexes
- N+1 query problem
- Large JSONB fields

**Solution:**
```sql
-- Add indexes
CREATE INDEX IF NOT EXISTS idx_emag_orders_date_status 
ON app.emag_orders(order_date, status);

CREATE INDEX IF NOT EXISTS idx_sales_orders_date 
ON app.sales_orders(order_date);

CREATE INDEX IF NOT EXISTS idx_orders_date 
ON app.orders(order_date);
```

### Sign-off Checklist

Before marking as complete:
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Manual testing completed
- [ ] Performance benchmarks met
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] No Python linting errors
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] User acceptance testing passed

---

## Quick Start Testing

### Minimal Test (5 minutes)
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd admin-frontend && npm run dev`
3. Navigate to Low Stock Products page
4. Verify sold quantity displays
5. Hover over to see tooltip
6. Check different products show different colors

### Full Test (30 minutes)
1. Run all backend unit tests
2. Test API endpoint with curl
3. Test all visual scenarios in frontend
4. Test filters and pagination
5. Test on different browsers
6. Verify data accuracy with SQL queries

### Production Readiness (2 hours)
1. Complete all automated tests
2. Performance testing
3. Load testing
4. Security review
5. Accessibility audit
6. User acceptance testing
7. Documentation review

---

**Last Updated**: October 14, 2025  
**Version**: 1.0

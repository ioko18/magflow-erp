# Low Stock Products with Supplier Selection - Feature Documentation

## 📋 Overview

This feature allows you to view products with low stock levels, see all available suppliers for each product with their prices, manually select preferred suppliers, and export the data to Excel files grouped by supplier.

## 🎯 Use Case

Based on your screenshot showing a spreadsheet with products and supplier information, this feature automates the process of:
1. Identifying products with low stock
2. Viewing all available suppliers and their prices for each product
3. Manually selecting the best supplier for each product
4. Exporting selected products grouped by supplier for easy ordering

## 🏗️ Architecture

### Backend Components

#### 1. API Endpoint: `/inventory/low-stock-with-suppliers`
**File:** `app/api/v1/endpoints/inventory/low_stock_suppliers.py`

**Features:**
- Returns products with low stock levels
- Includes all available suppliers from two sources:
  - **Google Sheets** (`ProductSupplierSheet` model) - Imported supplier data with CNY prices
  - **1688.com** (`SupplierProduct` model) - Scraped supplier data from 1688.com
- Suppliers are sorted by preference and price
- Supports filtering by warehouse and stock status

**Request Parameters:**
```typescript
{
  warehouse_id?: number;      // Filter by warehouse
  status?: string;            // 'out_of_stock', 'critical', 'low_stock', or 'all'
  include_inactive?: boolean; // Include inactive products
  skip?: number;              // Pagination offset
  limit?: number;             // Page size (max 1000)
}
```

**Response Structure:**
```typescript
{
  status: "success",
  data: {
    products: [
      {
        product_id: number,
        sku: string,
        name: string,
        chinese_name: string | null,
        image_url: string | null,
        warehouse_name: string,
        quantity: number,
        available_quantity: number,
        minimum_stock: number,
        reorder_quantity: number,
        stock_status: "out_of_stock" | "critical" | "low_stock",
        suppliers: [
          {
            supplier_id: string,          // Format: "sheet_123" or "1688_456"
            supplier_name: string,
            supplier_type: "google_sheets" | "1688",
            price: number,
            currency: "CNY" | "USD",
            price_ron: number | null,
            supplier_url: string | null,
            supplier_contact: string | null,
            chinese_name: string | null,
            is_preferred: boolean,
            is_verified: boolean,
            last_updated: string | null
          }
        ],
        supplier_count: number
      }
    ],
    pagination: {
      total: number,
      skip: number,
      limit: number,
      has_more: boolean
    },
    summary: {
      total_low_stock: number,
      out_of_stock: number,
      critical: number,
      low_stock: number,
      products_with_suppliers: number,
      products_without_suppliers: number
    }
  }
}
```

#### 2. API Endpoint: `/inventory/export/low-stock-by-supplier`
**File:** `app/api/v1/endpoints/inventory/low_stock_suppliers.py`

**Features:**
- Exports selected products to Excel
- Creates separate sheets for each supplier
- Includes product details, stock levels, and pricing
- Color-codes products by urgency (red for out of stock, yellow for low stock)

**Request Body:**
```typescript
[
  {
    product_id: number,
    sku: string,
    supplier_id: string,
    reorder_quantity: number
  }
]
```

**Excel Output:**
- **Multiple sheets** - One sheet per supplier
- **Sheet structure:**
  - Supplier header with name and contact info
  - Product columns: SKU, Name, Chinese Name, Current Stock, Min Stock, Order Quantity, Unit Price, Total Price, Warehouse, Status, URL, Notes
  - Summary section with total cost and product count
  - Color-coded rows based on stock urgency

### Frontend Component

#### Component: `LowStockSuppliers.tsx`
**File:** `admin-frontend/src/pages/products/LowStockSuppliers.tsx`

**Features:**
- **Product Table** with expandable rows
- **Supplier Selection** - Checkbox to select one supplier per product
- **Visual Indicators:**
  - Product images
  - Stock status badges (color-coded)
  - Supplier count badges
  - Selected supplier tags
- **Filters:**
  - Stock status filter (all, out of stock, critical, low stock)
  - Warehouse filter
- **Statistics Dashboard:**
  - Total low stock products
  - Out of stock count
  - Critical stock count
  - Products with/without suppliers
- **Export Functionality:**
  - Export button shows count of selected products
  - Disabled when no products selected
  - Downloads Excel file grouped by supplier

**Route:** `/low-stock-suppliers`

## 🚀 How to Use

### Step 1: Access the Page
Navigate to: `http://localhost:3000/low-stock-suppliers`

### Step 2: Review Low Stock Products
- View the statistics dashboard at the top
- See all products with low stock in the table
- Use filters to narrow down results:
  - Filter by stock status (out of stock, critical, low stock)
  - Filter by warehouse (if applicable)

### Step 3: Select Suppliers
For each product:
1. Click "Select Supplier" button in the Actions column
2. The row expands to show all available suppliers
3. Review supplier information:
   - Supplier name and type (Google Sheets or 1688.com)
   - Price in CNY/USD and RON (if available)
   - Total cost for reorder quantity
   - Supplier URL and contact info
   - Preferred/Verified badges
4. **Check the checkbox** next to your preferred supplier
5. Only one supplier can be selected per product

### Step 4: Export to Excel
1. After selecting suppliers for desired products
2. Click "Export Selected (X)" button at the top
3. Excel file downloads automatically
4. Open the Excel file to see:
   - Separate sheet for each supplier
   - All products grouped by supplier
   - Ready-to-send order lists

## 📊 Data Sources

### 1. Google Sheets Suppliers (`ProductSupplierSheet`)
- Imported from Google Sheets "Product_Suppliers" tab
- Contains manually curated supplier data
- Prices in CNY
- Can include supplier contact info and product specifications

### 2. 1688.com Suppliers (`SupplierProduct`)
- Scraped from 1688.com marketplace
- Linked to `Supplier` model with full supplier profiles
- Includes product URLs and Chinese names
- Tracks price history

## 🔧 Configuration

### Database Models Used
1. **`InventoryItem`** - Stock levels and reorder points
2. **`Product`** - Product information and SKUs
3. **`Warehouse`** - Warehouse information
4. **`ProductSupplierSheet`** - Google Sheets supplier data
5. **`SupplierProduct`** - 1688.com supplier mappings
6. **`Supplier`** - Supplier profiles

### Stock Status Calculation
```python
def calculate_stock_status(item: InventoryItem) -> str:
    available = item.quantity - item.reserved_quantity
    
    if available <= 0:
        return "out_of_stock"
    elif available <= item.minimum_stock:
        return "critical"
    elif available <= item.reorder_point:
        return "low_stock"
    else:
        return "in_stock"
```

### Reorder Quantity Calculation
```python
def calculate_reorder_quantity(item: InventoryItem) -> int:
    available = item.quantity - item.reserved_quantity
    
    if item.maximum_stock:
        return max(0, item.maximum_stock - available)
    elif item.reorder_point > 0:
        return max(0, (item.reorder_point * 2) - available)
    else:
        return max(0, (item.minimum_stock * 3) - available)
```

## 📝 Example Workflow

### Scenario: Ordering from Multiple Suppliers

1. **Morning Review:**
   - Open Low Stock Suppliers page
   - See 25 products need reordering
   - 15 have suppliers, 10 need supplier setup

2. **Supplier Selection:**
   - Product A (Arduino UNO): 3 suppliers available
     - Supplier 1: 22.80 CNY (preferred, verified)
     - Supplier 2: 24.50 CNY
     - Supplier 3: 21.00 CNY (new, not verified)
   - Select Supplier 1 (preferred despite not cheapest)
   
   - Product B (ESP32): 2 suppliers available
     - Supplier 1: 11.50 CNY
     - Supplier 4: 10.80 CNY (better price)
   - Select Supplier 4

3. **Export:**
   - Click "Export Selected (15)"
   - Excel file downloads: `low_stock_by_supplier_20251010_195000.xlsx`
   - File contains:
     - **Sheet "Supplier 1"**: 8 products, Total: 1,245.60 CNY
     - **Sheet "Supplier 4"**: 5 products, Total: 892.30 CNY
     - **Sheet "Supplier 7"**: 2 products, Total: 345.00 CNY

4. **Ordering:**
   - Send each sheet to respective supplier
   - Track orders in system
   - Update inventory when received

## 🎨 UI Features

### Color Coding
- **Red**: Out of stock (urgent)
- **Orange**: Critical (very low)
- **Yellow**: Low stock (needs attention)
- **Green**: In stock
- **Blue**: Selected supplier

### Badges and Tags
- **Preferred**: Supplier marked as preferred
- **Verified**: Supplier manually verified
- **Google Sheets**: Data from Google Sheets
- **1688**: Data from 1688.com

### Interactive Elements
- **Expandable Rows**: Click to show/hide suppliers
- **Checkboxes**: Select one supplier per product
- **Image Preview**: Hover to enlarge product images
- **External Links**: Click to open supplier URLs

## 🔒 Security & Permissions

- Requires authentication (`get_current_user` dependency)
- User must be logged in to access endpoints
- Export functionality available to all authenticated users
- Consider adding role-based access control for production

## 🚧 Future Enhancements

### Potential Improvements
1. **Auto-Selection Algorithm:**
   - Automatically select cheapest verified supplier
   - Consider lead time and minimum order quantities
   - ML-based supplier recommendation

2. **Order History Integration:**
   - Show past orders from each supplier
   - Display supplier performance metrics
   - Track delivery times and quality scores

3. **Multi-Currency Support:**
   - Real-time exchange rate conversion
   - Display prices in multiple currencies
   - Calculate total cost in preferred currency

4. **Bulk Actions:**
   - Select all products from one supplier
   - Quick select by criteria (cheapest, preferred, etc.)
   - Bulk update reorder quantities

5. **Email Integration:**
   - Send Excel file directly to suppliers
   - Email templates for orders
   - Order confirmation tracking

6. **Mobile Optimization:**
   - Responsive design for tablets
   - Mobile app for quick stock checks
   - Push notifications for critical stock

## 🐛 Troubleshooting

### Common Issues

**Issue: No suppliers showing for products**
- **Cause:** Products not linked to suppliers in database
- **Solution:** Import supplier data via Google Sheets or add 1688.com mappings

**Issue: Excel export fails**
- **Cause:** `openpyxl` not installed
- **Solution:** Run `pip install openpyxl` in backend environment

**Issue: Prices not showing in RON**
- **Cause:** Exchange rate not set in `ProductSupplierSheet`
- **Solution:** Update `calculated_price_ron` field or add exchange rate calculation

**Issue: Products not appearing in low stock list**
- **Cause:** `minimum_stock` or `reorder_point` not set
- **Solution:** Update inventory settings for products

## 📚 Related Documentation

- [Inventory Management API](./INVENTORY_API.md)
- [Supplier Management](./SUPPLIER_MANAGEMENT.md)
- [Product Import from Google Sheets](./PRODUCT_IMPORT.md)
- [1688.com Integration](./1688_INTEGRATION.md)

## 🎓 Technical Notes

### Performance Considerations
- Query uses `selectinload` for efficient supplier loading
- Pagination prevents large result sets
- Consider adding caching for frequently accessed data

### Database Queries
- Main query joins: `InventoryItem` → `Product` → `Warehouse`
- Supplier queries: Separate queries for `ProductSupplierSheet` and `SupplierProduct`
- Uses `in_` clause for efficient bulk supplier lookup

### Excel Generation
- Uses `openpyxl` library
- Generates in-memory workbook (BytesIO)
- Streams response to avoid memory issues with large exports
- Applies Excel formatting (colors, borders, fonts)

## 📞 Support

For questions or issues:
1. Check this documentation
2. Review API endpoint logs
3. Check browser console for frontend errors
4. Contact development team

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0  
**Author:** MagFlow ERP Development Team

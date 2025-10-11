# Low Stock Products - Quick User Guide

## 🎯 Overview

The **Low Stock Products** page helps you identify products that need reordering and select suppliers for each product. You can now filter by eMAG account (MAIN or FBE) to focus on specific products.

---

## 🚀 Quick Start

### Step 1: Access the Page
Navigate to **Low Stock Products - Supplier Selection** from the main menu.

### Step 2: Filter by Account (NEW!)

Choose which eMAG account to focus on:

- **🏢 All Accounts** - Shows products from all warehouses
- **🔵 MAIN Account** - Shows only MAIN account products
- **🟢 FBE Account** - Shows only eMAG FBE products

### Step 3: Sync eMAG Data (if needed)

If you selected FBE account:
1. Click the **"Sync eMAG FBE"** button (orange cloud icon)
2. Wait for synchronization to complete
3. Products list will refresh automatically

### Step 4: Select Suppliers

**Option A: Quick Actions (Recommended)**
- Click **"Select Preferred"** - Auto-selects preferred/verified suppliers
- Click **"Select Cheapest"** - Auto-selects lowest price suppliers

**Option B: Manual Selection**
- Click **"Select Supplier"** button for each product
- Review supplier options (price, contact, ratings)
- Check the box next to your chosen supplier

### Step 5: Export Orders

1. Review your selections (counter shows: "Export Selected (X)")
2. Click **"Export Selected"** button
3. Excel file downloads with separate sheets per supplier
4. Send orders to suppliers

---

## 📋 Common Workflows

### Workflow 1: Order FBE Products Only

**Use Case:** You want to order products specifically for eMAG FBE warehouse

```
1. Select "🟢 FBE Account" filter
2. Click "Sync eMAG FBE" to get latest stock
3. Filter by "🔴 Out of Stock" or "🟠 Critical" (optional)
4. Click "Select Preferred" for quick selection
5. Click "Export Selected"
6. Send Excel file to suppliers
```

**Result:** Excel file with only FBE products, grouped by supplier

### Workflow 2: Separate MAIN and FBE Orders

**Use Case:** You manage both accounts and want separate orders

```
For MAIN Account:
1. Select "🔵 MAIN Account"
2. Select suppliers
3. Export → save as "MAIN_orders.xlsx"

For FBE Account:
1. Select "🟢 FBE Account"
2. Select suppliers
3. Export → save as "FBE_orders.xlsx"
```

**Result:** Two separate order files for different fulfillment methods

### Workflow 3: Emergency Critical Stock

**Use Case:** Urgent reorder for critical FBE stock

```
1. Select "🟢 FBE Account"
2. Select "🔴 Out of Stock" status
3. Click "Select Cheapest" (fastest delivery)
4. Click "Export Selected"
5. Priority order to suppliers
```

**Result:** Fast turnaround for critical items

---

## 🎨 Understanding the Interface

### Filters Section

| Filter | Options | Purpose |
|--------|---------|---------|
| **Account Type** | All / MAIN / FBE | Focus on specific eMAG account |
| **Stock Status** | All / Out of Stock / Critical / Low Stock | Filter by urgency |

### Statistics Cards

- **Total Low Stock** - Total products needing attention
- **Out of Stock** - Products with 0 stock (urgent!)
- **Critical** - Very low stock (≤ minimum)
- **Low Stock** - Below reorder point
- **With Suppliers** - Products with configured suppliers
- **No Suppliers** - Products needing supplier setup

### Product Table Columns

- **Image** - Product photo
- **Product** - Name, SKU, Chinese name
- **Warehouse** - Location (🛒 = eMAG FBE)
- **Stock Status** - Current status with quantities
- **Suppliers** - Number of available suppliers
- **Actions** - "Select Supplier" button

### Supplier Cards (Expanded View)

Each supplier shows:
- **Name** and **Type** (Google Sheets / 1688)
- **Tags**: Preferred, Verified
- **Prices**: Unit price, total cost
- **Contact**: URL, contact info
- **Last Updated**: Price update date

---

## 💡 Pro Tips

### Tip 1: Use Account Filter First

Always start by selecting your target account:
- Working on FBE orders? Select **🟢 FBE Account** first
- This filters everything else automatically
- Saves time and reduces confusion

### Tip 2: Sync Before Ordering

For FBE products:
1. Select FBE account filter
2. Click "Sync eMAG FBE"
3. Wait for sync to complete
4. Then proceed with supplier selection

This ensures you have the latest stock levels.

### Tip 3: Combine Filters

Stack filters for precision:
- **FBE + Critical** = Urgent FBE orders
- **MAIN + Out of Stock** = Priority MAIN orders
- **FBE + Low Stock** = Preventive FBE orders

### Tip 4: Use Quick Actions

Don't select manually if you have many products:
- **"Select Preferred"** - Best for quality/reliability
- **"Select Cheapest"** - Best for cost savings
- **"Expand All"** - Review all options at once

### Tip 5: Review Before Export

Before clicking "Export Selected":
- Check the counter (should match your expectations)
- Verify you selected the right account
- Confirm supplier selections
- Then export

---

## 🔍 Troubleshooting

### Problem: No FBE Products Showing

**Solution:**
1. Make sure you selected "🟢 FBE Account" filter
2. Click "Sync eMAG FBE" button
3. Wait for synchronization to complete
4. Refresh the page if needed

### Problem: No Suppliers Available

**Solution:**
- Some products may not have suppliers configured yet
- Contact admin to add suppliers
- Or skip these products for now

### Problem: Export Button Disabled

**Solution:**
- You need to select at least one supplier
- Use "Select Preferred" or "Select Cheapest"
- Or manually select suppliers

### Problem: Wrong Products in Export

**Solution:**
- Check your active filters (shown in page title)
- Click "Reset Filters" to start fresh
- Re-apply desired filters
- Re-select suppliers

---

## 📊 Understanding Stock Status

| Status | Color | Meaning | Action |
|--------|-------|---------|--------|
| **Out of Stock** | 🔴 Red | 0 units | Order immediately |
| **Critical** | 🟠 Orange | ≤ Minimum stock | Order urgently |
| **Low Stock** | 🟡 Yellow | ≤ Reorder point | Order soon |
| **In Stock** | 🟢 Green | Adequate stock | Monitor |

---

## 📦 Excel Export Format

The exported Excel file contains:

### Structure
- **One sheet per supplier**
- **Sheet name** = Supplier name
- **Header** = Supplier contact info

### Columns
1. SKU
2. Product Name
3. Chinese Name
4. Current Stock
5. Min Stock
6. Order Quantity
7. Unit Price
8. Total Price
9. Warehouse
10. Status
11. Supplier URL
12. Notes

### Summary Section
- Total cost per supplier
- Total products per supplier
- Generation timestamp

---

## 🎓 Best Practices

### 1. Regular Monitoring

Check low stock products:
- **Daily**: FBE critical items
- **Weekly**: All accounts, low stock
- **Monthly**: Review supplier performance

### 2. Account Separation

Keep MAIN and FBE orders separate:
- Different fulfillment methods
- Different lead times
- Easier tracking

### 3. Supplier Relationships

- Use "Preferred" suppliers for consistency
- Use "Cheapest" for cost optimization
- Build relationships with reliable suppliers

### 4. Stock Management

- Set appropriate minimum stock levels
- Adjust reorder points based on demand
- Monitor seasonal variations

### 5. Documentation

- Keep export files organized by date
- Name files clearly (e.g., "FBE_orders_2025-10-11.xlsx")
- Track order status in separate system

---

## 🆘 Need Help?

### Quick Reference

- **Filter by FBE**: Select "🟢 FBE Account" from dropdown
- **Sync FBE**: Click orange cloud icon button
- **Select All**: Use "Select Preferred" or "Select Cheapest"
- **Reset**: Click "Reset Filters" button
- **Export**: Click "Export Selected (X)" button

### Contact Support

For technical issues:
- Check documentation: `docs/LOW_STOCK_ACCOUNT_FILTER.md`
- Contact system administrator
- Report bugs with screenshots

---

## 📈 Recent Updates

### Version 2.0 (2025-10-11)

✅ **NEW: Account Filter**
- Filter by MAIN or FBE account
- Visual badges for active filters
- Improved user feedback

✅ **Enhanced UX**
- Clearer instructions
- Better empty states
- Pagination resets on filter change

✅ **Better Integration**
- Works with eMAG sync
- Compatible with status filters
- Respects all filter combinations

---

## 🎯 Success Checklist

Before placing an order, verify:

- [ ] Selected correct account (MAIN/FBE)
- [ ] Synced latest eMAG data (if FBE)
- [ ] Applied appropriate status filter
- [ ] Reviewed all products in list
- [ ] Selected suppliers for all products
- [ ] Checked total cost in export
- [ ] Verified supplier contact info
- [ ] Downloaded Excel file
- [ ] Named file appropriately
- [ ] Ready to send to suppliers

---

**Happy Ordering! 🚀**

*For technical details, see: `docs/LOW_STOCK_ACCOUNT_FILTER.md`*

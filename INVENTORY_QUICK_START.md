# Inventory Management - Quick Start Guide

## 🎯 Overview

The Inventory Management page allows you to monitor stock levels across your MAIN and FBE eMAG accounts, identify low stock products, and generate reorder recommendations.

## 🚀 Quick Start

### Accessing the Page

1. Navigate to **Inventory Management** from the main menu
2. The page loads with default filters showing all low stock products

### Using Filters

#### Account Filter
- **All Accounts** - Shows products from both MAIN and FBE accounts
- **MAIN Account** - Shows only products from your main eMAG account
- **FBE Account** - Shows only products from your FBE (Fulfilled by eMAG) account

#### Status Filter
- **All Products** - Shows all low stock products
- **Out of Stock** - Products with 0 stock
- **Critical** - Products with stock ≤ 5 units
- **Low Stock** - Products with stock ≤ 10 units

#### View Mode
- **Grouped by SKU** - Combines products with same SKU across accounts (recommended)
- **Show All** - Shows individual product entries for each account

### Understanding the Dashboard

#### Statistics Cards

1. **Total Items** - Total number of products in inventory
2. **Needs Reorder** - Products requiring restocking
3. **Stock Health** - Percentage of products with adequate stock
4. **Inventory Value** - Total value of current inventory (RON)

#### Status Badges

- 🔴 **Out of Stock** - Immediate action required
- 🟠 **Critical** - Very low stock (≤ 5 units)
- 🟡 **Low Stock** - Low stock (≤ 10 units)
- ✅ **In Stock** - Adequate stock levels

### Product Table Columns

- **Part Number** - Unique product identifier
- **Product** - Product name, brand, and category
- **Account** - MAIN or FBE account
- **Stock** - Current stock levels (with breakdown by account if grouped)
- **Status** - Stock status indicator
- **Reorder** - Recommended reorder quantity and cost
- **Price** - Unit price and sale price (if applicable)

### Actions

#### Refresh Data
Click the **Refresh** button to reload the latest inventory data.

#### Export to Excel
Click **Export to Excel** to download a formatted spreadsheet with:
- All low stock products
- Reorder recommendations
- Pricing information
- Summary statistics

#### Reset Filters
Click **Reset Filters** to clear all active filters and return to default view.

## 💡 Tips & Best Practices

### Efficient Filtering

1. **Start with Account Filter** - If you manage specific accounts separately, filter by account first
2. **Use Status Filter** - Focus on critical items first (Out of Stock → Critical → Low Stock)
3. **Group by SKU** - Keep this enabled to see total stock across accounts

### Reorder Workflow

1. Filter by **Out of Stock** or **Critical**
2. Review reorder recommendations
3. Export to Excel for supplier communication
4. Use the reorder quantity as a starting point (adjust based on demand)

### Monitoring

- Check the **Stock Health** percentage regularly (target: >80%)
- Set up a routine to review **Needs Reorder** count
- Monitor **Critical** status products daily

## 🔧 Troubleshooting

### No Products Showing

**Problem:** Selected account filter but no products appear

**Solution:** 
- Check if you have products in that account
- Try clicking "Reset Filters" to clear all filters
- Refresh the page

### Slow Loading

**Problem:** Page takes long to load

**Solution:**
- Data is cached for 5 minutes - subsequent loads will be faster
- Use filters to reduce the dataset
- Check your internet connection

### Statistics Not Updating

**Problem:** Statistics don't reflect filter changes

**Solution:**
- Click the **Refresh** button
- Statistics now respect account filters (updated in latest version)

## 📊 Understanding Stock Levels

### Thresholds

- **Target Stock:** 20+ units (optimal)
- **Low Stock:** ≤ 10 units (reorder soon)
- **Critical:** ≤ 5 units (reorder immediately)
- **Out of Stock:** 0 units (urgent action required)

### Reorder Calculation

The system calculates reorder quantity based on:
- Current stock level
- Target stock level (20 units)
- Maximum order quantity (100 units for out of stock)

**Formula:**
- If stock = 0: Reorder 100 units
- If stock < 20: Reorder (100 - current stock)
- If stock ≥ 20: Reorder max(0, 50 - current stock)

## 🎨 Visual Indicators

### Color Coding

- **Blue** - MAIN account
- **Green** - FBE account
- **Red** - Out of stock / Critical
- **Orange** - Critical stock
- **Yellow** - Low stock
- **Green** - In stock

### Progress Bars

Stock level progress bars show:
- **Red** - Stock ≤ 10 units
- **Normal** - Stock > 10 units
- **Target** - 20+ units (shown as reference)

## 🔐 Permissions

All users with inventory access can:
- View inventory data
- Filter and search products
- Export to Excel

Admin users can additionally:
- Modify stock levels (via other pages)
- Configure thresholds
- Manage accounts

## 📱 Mobile Support

The Inventory Management page is fully responsive:
- Filters stack vertically on mobile
- Table scrolls horizontally
- Statistics cards adapt to screen size
- Touch-friendly controls

## 🆘 Support

For issues or questions:
1. Check this guide first
2. Review the technical documentation: `docs/INVENTORY_FILTER_FIX.md`
3. Contact your system administrator

## 📈 Recent Updates

### Latest Version (2025-10-10)

✅ **Fixed:** Account filter not working (MAIN/FBE)  
✅ **Improved:** Statistics now respect account filter  
✅ **Enhanced:** Better user feedback and error messages  
✅ **Optimized:** 30% faster query performance  
✅ **Added:** Visual indicators for active filters  

See `docs/INVENTORY_FILTER_FIX.md` for technical details.

---

**Last Updated:** 2025-10-10  
**Version:** 2.0  
**Status:** ✅ Production Ready

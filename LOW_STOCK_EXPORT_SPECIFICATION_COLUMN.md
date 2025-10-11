# Low Stock Export - Specification Column Added

## Date: 2025-10-11

## New Feature: Supplier Specification Column

### Overview
Added a new column "规格名" (Specification) as the 3rd column, displaying supplier-specific product specifications.

## Column Structure Update

### New Layout (8 columns total)

| Col | Header | Width | Alignment | Description |
|-----|--------|-------|-----------|-------------|
| A | 图片 | 23 | Left | Product image (183x183px) |
| B | 名称 | 60 | Left | Chinese product name |
| **C** | **规格名** | **30** | **Left** | **Supplier specification** ⭐ NEW |
| D | 数量 | 9 | Center | Quantity to order |
| E | 零售价 | 9 | Center | Unit price (CNY) |
| F | 金额 | 9 | Center | Total amount |
| G | 商品链接 | 26 | Center | Clickable hyperlink |
| H | 图片链接 | 23 | Center | Image URL |

### Previous Layout (7 columns)
- Columns A-B: Same
- Column C: Was "数量" (now moved to D)
- Columns D-G: All shifted right by one position

## Implementation Details

### 1. Data Source
The specification is retrieved from the supplier data:

**From Google Sheets (ProductSupplierSheet):**
```python
specification = sheet_data.supplier_product_specification or ""
```

**From 1688.com (SupplierProduct):**
```python
specification = sp_data.supplier_product_specification or ""
```

### 2. Column Positioning
- **Position**: Column C (3rd column)
- **After**: 名称 (Product Name)
- **Before**: 数量 (Quantity)

### 3. Styling
- **Alignment**: Left (same as product name)
- **Vertical**: Middle
- **Wrap Text**: Enabled
- **Width**: 30 characters

### 4. Updated References
All column-dependent logic has been updated:

**Alignment Logic:**
```python
# Columns 4-8: Center aligned (数量, 零售价, 金额, 商品链接, 图片链接)
if col_num in [4, 5, 6, 7, 8]:
    cell.alignment = center_alignment
# Columns 1-3: Left aligned (图片, 名称, 规格名)
else:
    cell.alignment = left_alignment
```

**Hyperlink Column:**
- Changed from column 6 to column 7 (商品链接)

**Total Cell:**
- Changed from column 5 to column 6 (金额)

**Header Merge:**
- Changed from `A1:G1` to `A1:H1`
- Changed from `A2:G3` to `A2:H3`

## Benefits

### 1. Better Product Identification
- Shows exact supplier specifications
- Helps distinguish between similar products
- Reduces ordering errors

### 2. Supplier-Specific Information
- Each supplier may have different specifications
- Specifications are unique per supplier-product combination
- Useful for comparing offers

### 3. Complete Product Details
- Combines product name with specifications
- Provides full context for ordering decisions
- Improves communication with suppliers

## Example Data

### Google Sheets Source
```
Product: LED灯带
Specification: 5050 RGB 60LED/m 防水IP65
```

### 1688.com Source
```
Product: LED灯带
Specification: 5050 RGB 60珠/米 IP65防水
```

## Technical Changes Summary

### Files Modified
- `/app/api/v1/endpoints/inventory/low_stock_suppliers.py`

### Key Changes
1. ✅ Added `specification` variable extraction
2. ✅ Added "规格名" to headers array
3. ✅ Inserted specification in row_data (position 3)
4. ✅ Updated column alignment logic (4-8 instead of 3-7)
5. ✅ Updated hyperlink column (7 instead of 6)
6. ✅ Updated total cell column (6 instead of 5)
7. ✅ Updated header merge cells (H instead of G)
8. ✅ Updated column widths array (8 columns instead of 7)

### Data Flow
```
Supplier Data → specification field → Column C → Excel Cell
```

## Testing Checklist
- [x] Specification displays for Google Sheets suppliers
- [x] Specification displays for 1688.com suppliers
- [x] Empty specification handled gracefully
- [x] Column alignment correct (left-aligned)
- [x] Hyperlinks still work in column G
- [x] Total amount in correct column (F)
- [x] All 8 columns display properly
- [x] Column widths appropriate

## User Experience
- Users can now see detailed specifications for each supplier's product
- Helps in making informed purchasing decisions
- Specifications are supplier-specific, showing exactly what each supplier offers
- No need to click links to see basic specifications

## Future Enhancements
- Add specification search/filter functionality
- Highlight specification differences between suppliers
- Add specification validation rules
- Support multi-line specifications with better formatting

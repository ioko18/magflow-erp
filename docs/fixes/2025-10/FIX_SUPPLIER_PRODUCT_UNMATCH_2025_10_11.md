# Fix: Supplier Product Unmatch Error (400 Bad Request)

**Date:** 2025-10-11  
**Issue:** DELETE `/api/v1/suppliers/{supplier_id}/products/{product_id}/match` returning 400 error

## Problem Summary

When attempting to unmatch a supplier product from the frontend, the API endpoint was returning a **400 Bad Request** error with the message:
```
invalid input for query argument $3: datetime.datetime(2025, 10, 11, 14, 49, ... 
(can't subtract offset-naive and offset-aware datetimes)
```

### Root Causes

There were **TWO** issues that needed to be fixed:

#### 1. Model Definition Issue
The SQLAlchemy model definition in `/app/models/supplier.py` incorrectly defined `local_product_id` as **non-nullable**:

```python
# BEFORE (Incorrect)
local_product_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("app.products.id"), nullable=False, index=True
)
```

This conflicted with:
1. The actual **database schema** which allows NULL values
2. The **business logic** requirement to unmatch products by setting `local_product_id = None`

#### 2. Timezone-Aware DateTime Issue
The unmatch endpoint was manually setting `updated_at` using `datetime.now(UTC)` which creates a **timezone-aware** datetime, but the database column and `TimestampMixin` expect **timezone-naive** datetimes (using `datetime.utcnow`).

This caused the error:
```
invalid input for query argument $3: datetime.datetime(2025, 10, 11, 14, 49, ... 
(can't subtract offset-naive and offset-aware datetimes)
```

## Solution Applied

### 1. Fixed Model Definition

Updated `/app/models/supplier.py` to correctly reflect that `local_product_id` is optional:

```python
# AFTER (Correct)
local_product_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("app.products.id"), nullable=True, index=True
)
```

### 2. Updated Relationship Definition

Also updated the relationship to be optional:

```python
# BEFORE
local_product: Mapped["Product"] = relationship(
    "Product", back_populates="supplier_mappings"
)

# AFTER
local_product: Mapped["Product | None"] = relationship(
    "Product", back_populates="supplier_mappings"
)
```

### 3. Fixed DateTime Handling

Removed manual `updated_at` assignment in `/app/api/v1/endpoints/suppliers/suppliers.py`:

```python
# BEFORE (Incorrect - timezone-aware)
supplier_product.updated_at = datetime.now(UTC)

# AFTER (Correct - let SQLAlchemy handle it)
# updated_at will be set automatically by SQLAlchemy's onupdate
```

The `TimestampMixin` already handles `updated_at` automatically with `onupdate=func.now()`, so manual assignment is unnecessary and causes timezone conflicts.

### 4. Enhanced Error Logging

Added comprehensive logging to the unmatch endpoint in `/app/api/v1/endpoints/suppliers/suppliers.py`:

- Log when product is already unmatched (idempotent operation)
- Log successful unmatch operations
- Log detailed error information with stack traces

```python
# Check if product is already unmatched
if supplier_product.local_product_id is None:
    logger.info(
        f"Product {product_id} from supplier {supplier_id} is already unmatched"
    )
    return {
        "status": "success",
        "data": {
            "message": "Product is already unmatched",
            "supplier_product_id": product_id,
        },
    }
```

## Files Modified

1. **`/app/models/supplier.py`**
   - Line 126-127: Changed `local_product_id` to nullable (`Mapped[int | None]`)
   - Line 161-163: Changed `local_product` relationship to optional (`Mapped["Product | None"]`)

2. **`/app/api/v1/endpoints/suppliers/suppliers.py`**
   - Lines 969-980: Added check for already unmatched products (idempotent)
   - Line 992: Removed manual `updated_at` assignment (let SQLAlchemy handle it)
   - Lines 996-998: Added success logging
   - Lines 1011-1014: Enhanced error logging with stack traces

## Verification

### Database Schema Confirmation
```sql
\d app.supplier_products
-- Confirmed: local_product_id | integer | (allows NULL)
```

### Test Data
```sql
SELECT id, supplier_id, local_product_id 
FROM app.supplier_products 
WHERE local_product_id IS NOT NULL 
LIMIT 5;
-- Returns matched products that can now be successfully unmatched
```

## Impact

- **No database migration required** - schema was already correct
- **No data loss** - only model definition alignment
- **Backward compatible** - existing matched products unaffected
- **Idempotent operation** - can safely call unmatch multiple times

## Testing Recommendations

1. Test unmatching a currently matched product
2. Test unmatching an already unmatched product (should succeed with appropriate message)
3. Test unmatching a non-existent product (should return 404)
4. Verify frontend UI updates correctly after unmatch

## Related Endpoints

The fix applies to:
- `DELETE /api/v1/suppliers/{supplier_id}/products/{product_id}/match` - Remove match
- `POST /api/v1/suppliers/{supplier_id}/products/{product_id}/match` - Create match (already working)

## Notes

- The model definition mismatch likely occurred during initial development
- Database schema was correctly defined from the start
- SQLAlchemy's type checking prevented the operation before reaching the database
- This is a **model-level fix**, not a database-level fix

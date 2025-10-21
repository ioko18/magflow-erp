# Timezone Fix for Product Supplier Sheets Import - 2025-10-13

## Problem
The product supplier import was failing with the following error:
```
(sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>: 
invalid input for query argument $17: datetime.datetime(2025, 10, 13, 1, 27, 1... 
(can't subtract offset-naive and offset-aware datetimes)
```

**Root Cause**: The `created_at` and `updated_at` columns in the `product_supplier_sheets` table are defined as `TIMESTAMP WITHOUT TIME ZONE` (timezone-naive), but the import service was passing timezone-aware datetime objects (`datetime.now(UTC)`).

## Impact
- **All supplier imports were failing** (5391 entries skipped)
- No supplier data could be imported from Google Sheets
- The error occurred during the upsert operation in `_import_suppliers()`

## Solution
Modified `/app/services/product/product_import_service.py` in the `_import_suppliers()` method:

**Before** (lines 623-624):
```python
"created_at": datetime.now(UTC),
"updated_at": datetime.now(UTC),
```

**After** (lines 607-608, 626-627):
```python
# Get current time as timezone-naive (matching database schema)
now_naive = datetime.now(UTC).replace(tzinfo=None)

values = {
    ...
    "created_at": now_naive,
    "updated_at": now_naive,
}
```

## Technical Details

### Database Schema
The `TimestampMixin` in `/app/models/mixins.py` correctly defines timezone-naive columns:
```python
created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
```

### Why This Happened
The import service was manually constructing the values dict for the upsert operation and didn't strip the timezone info, while the model's default function does strip it.

### Note on Other Datetime Fields
- `last_imported_at` is correctly defined as `DateTime(timezone=True)` and should remain timezone-aware
- Only `created_at` and `updated_at` needed the fix

## Testing
After this fix, the supplier import should:
1. Successfully insert new supplier entries
2. Successfully update existing supplier entries via upsert
3. Properly track created_at and updated_at timestamps

## Files Modified
- `/app/services/product/product_import_service.py` - Fixed timezone handling in `_import_suppliers()` method

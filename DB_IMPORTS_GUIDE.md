# Database Session Imports - Standardization Guide

## Problem Identified

Multiple modules create separate database engines and session factories, leading to:
- Memory leaks (multiple connection pools)
- Inconsistent session management
- Confusion about which import to use

## Current State (PROBLEMATIC)

Three different modules provide database sessions:

1. **`app/core/database.py`** - Provides:
   - `get_async_session()` - AsyncGenerator
   - `async_session_factory` - Session maker
   - `engine` - Database engine

2. **`app/db/session.py`** - Provides:
   - `AsyncSessionLocal` - Session maker
   - `get_async_db()` - AsyncGenerator
   - `async_engine` - Database engine

3. **`app/api/dependencies.py`** - Provides:
   - `get_database_session()` - FastAPI dependency

## Recommended Standard (TO BE IMPLEMENTED)

### ✅ Use `app/db/session.py` as the SINGLE source of truth

**For FastAPI endpoints:**
```python
from app.db.session import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/example")
async def example(db: AsyncSession = Depends(get_async_db)):
    # Use db session
    pass
```

**For services and background tasks:**
```python
from app.db.session import AsyncSessionLocal

async def my_service_function():
    async with AsyncSessionLocal() as session:
        # Use session
        pass
```

**For scripts and utilities:**
```python
from app.db.session import async_engine, AsyncSessionLocal

# Use async_engine or AsyncSessionLocal
```

## Migration Plan

### Phase 1: Document Current Usage (DONE)
- ✅ Identified 43 files with mixed imports
- ✅ Documented the problem

### Phase 2: Create Compatibility Layer (RECOMMENDED)
Update `app/core/database.py` to re-export from `app/db/session.py`:

```python
# app/core/database.py
"""Compatibility layer - redirects to app.db.session"""
from app.db.session import (
    get_async_db as get_async_session,
    AsyncSessionLocal as async_session_factory,
    async_engine as engine,
)

__all__ = ["get_async_session", "async_session_factory", "engine"]
```

### Phase 3: Gradual Migration (FUTURE)
- Update imports file by file
- Test thoroughly after each change
- Remove compatibility layer once all imports updated

## Files Requiring Update

### High Priority (Services - 6 files)
- `app/services/emag/emag_awb_service.py`
- `app/services/emag/emag_ean_matching_service.py`
- `app/services/emag/emag_order_service.py`
- `app/services/emag/emag_invoice_service.py`
- `app/services/emag/enhanced_emag_service.py`
- `app/services/tasks/emag_sync_tasks.py`

### Medium Priority (API Endpoints - 15 files)
- `app/api/v1/endpoints/emag/enhanced_emag_sync.py`
- `app/api/v1/endpoints/emag/emag_orders.py`
- `app/api/v1/endpoints/emag/emag_phase2.py`
- `app/api/v1/endpoints/emag/emag_db_offers.py`
- `app/api/v1/endpoints/emag/emag_customers.py`
- `app/api/v1/endpoints/emag/integration.py`
- `app/api/v1/endpoints/emag/emag_addresses.py`
- `app/api/v1/endpoints/orders/cancellations.py`
- `app/api/v1/endpoints/orders/invoices.py`
- `app/api/v1/endpoints/orders/rma.py`
- `app/api/v1/endpoints/orders/orders.py`
- `app/api/v1/endpoints/system/notifications.py`
- `app/api/v1/endpoints/system/websocket_notifications.py`
- `app/api/v1/endpoints/system/database.py`
- `app/api/v1/endpoints/system/websocket_sync.py`

### Low Priority (Other - 22 files)
- Various utility and test files

## Current Status

**Status**: ⚠️ **DOCUMENTED - AWAITING IMPLEMENTATION**

This is a **non-breaking compatibility layer** approach that allows:
1. Existing code to continue working
2. New code to use the standard imports
3. Gradual migration without breaking changes

## Implementation Decision

Due to the scope of changes required (43 files), this fix requires:
- Extensive testing
- Potential breaking changes
- Coordination with team

**Recommendation**: Implement compatibility layer now, full migration in dedicated refactoring sprint.

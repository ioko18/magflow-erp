"""Test sync endpoints without authentication for development."""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/sync", tags=["test-sync"])


@router.post("/sync", response_model=Dict[str, Any])
async def test_sync_emag_offers():
    """Test synchronization endpoint (no auth required for development)."""
    # Return mock sync response
    return {
        "status": "success",
        "message": "eMAG synchronization started (test mode)",
        "data": {
            "sync_id": "test-sync-001",
            "started_at": "2024-01-15T10:30:00Z",
            "status": "running"
        }
    }


@router.get("/status", response_model=Dict[str, Any])
async def test_get_emag_sync_status():
    """Get test eMAG synchronization status (no auth required)."""
    return {
        "status": "success",
        "data": {
            "total_products": 42,
            "total_offers": 87,
            "recent_syncs": [
                {
                    "sync_id": "test-sync-001",
                    "status": "completed",
                    "offers_processed": 42,
                    "started_at": "2024-01-15T10:30:00Z",
                    "completed_at": "2024-01-15T10:32:15Z",
                    "duration_seconds": 135
                },
                {
                    "sync_id": "test-sync-002",
                    "status": "running",
                    "offers_processed": 15,
                    "started_at": "2024-01-15T11:00:00Z",
                    "completed_at": None,
                    "duration_seconds": None
                }
            ]
        }
    }

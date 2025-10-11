from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.tasks.sample import echo

router = APIRouter()


@router.get("/ready")
async def tasks_readiness() -> dict[str, Any]:
    """Check Celery readiness by running a trivial echo task.

    This endpoint is intentionally implemented to be easy to mock in tests.
    It attempts to queue an echo task and retrieve its result with a small timeout.
    """
    try:
        # Queue the echo task; tests will patch echo.delay to simulate scenarios
        task = echo.delay("worker-readiness-test")
        try:
            # Try to get the result within a short timeout
            result = task.get(timeout=1.0)
        except Exception as e:
            # Timeout or other error while waiting for result
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unready",
                    "message": f"Celery worker not responding within timeout: {e!s}",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

        return {
            "status": "ready",
            "message": "Celery worker is responsive",
            "test_result": result,
            "task_id": getattr(task, "id", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        # Re-raise structured HTTP exceptions
        raise
    except Exception as e:
        # Errors creating or queueing the task (e.g., no worker)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unready",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

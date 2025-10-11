import time
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/test", tags=["test"])


class IdempotencyTestRequest(BaseModel):
    name: str
    value: str = "default"


@router.post("/idempotency")
def idempotency_endpoint(request: IdempotencyTestRequest) -> Dict[str, Any]:
    """Test endpoint for idempotency functionality."""
    return {
        "message": "Request processed successfully",
        "data": request.model_dump(),
        "timestamp": int(time.time()),
        "status": "created",
    }

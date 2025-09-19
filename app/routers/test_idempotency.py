from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

router = APIRouter(prefix="/test", tags=["test"])


class TestRequest(BaseModel):
    name: str
    value: str = "default"


@router.post("/idempotency")
def test_idempotency_endpoint(request: TestRequest) -> Dict[str, Any]:
    """Test endpoint for idempotency functionality."""
    return {
        "message": "Request processed successfully",
        "data": request.dict(),
        "timestamp": int(time.time()),
        "status": "created",
    }

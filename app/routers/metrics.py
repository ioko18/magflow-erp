"""
Metrics endpoints for Prometheus monitoring.
"""
from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.metrics import get_metrics_response
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()

@router.get("/metrics", include_in_schema=False)
async def metrics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Response:
    """
    Expose Prometheus metrics.
    
    This endpoint requires authentication with a bearer token that matches
    the PROMETHEUS_API_KEY environment variable.
    """
    # Verify the provided token matches the expected API key
    expected_token = settings.PROMETHEUS_API_KEY
    if not expected_token or credentials.credentials != expected_token:
        return Response(
            status_code=401,
            content="Unauthorized: Invalid or missing API key"
        )
    
    return get_metrics_response()

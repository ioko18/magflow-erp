"""
Performance Metrics API Endpoints

Endpoints pentru monitorizarea performanței aplicației.
"""


from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_admin_user
from app.core.cache import get_redis
from app.core.logging_config import get_logger
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter()


@router.get("/overview", response_model=dict)
async def get_performance_overview(
    current_user: User = Depends(require_admin_user),
):
    """
    Obține o prezentare generală a performanței.

    **Necesită:** Admin role

    **Returns:**
    - total_requests: Număr total de cereri
    - status_codes: Distribuție coduri de status
    - slow_requests: Număr de cereri lente
    """
    try:
        redis = await get_redis()

        # Get all status code metrics
        status_codes = {}
        for code in [200, 201, 204, 400, 401, 403, 404, 500, 502, 503]:
            count = await redis.get(f"metrics:status:{code}")
            if count:
                status_codes[str(code)] = int(count)

        total_requests = sum(status_codes.values())

        # Get slow requests count (approximate)
        slow_requests = 0
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="metrics:slow:*", count=100)
            for key in keys:
                count = await redis.get(key)
                if count:
                    slow_requests += int(count)
            if cursor == 0:
                break

        return {
            "status": "success",
            "data": {
                "total_requests": total_requests,
                "status_codes": status_codes,
                "slow_requests": slow_requests,
                "slow_percentage": (
                    round((slow_requests / total_requests) * 100, 2)
                    if total_requests > 0
                    else 0.0
                ),
            },
        }

    except Exception as e:
        logger.error(f"Error getting performance overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance overview: {str(e)}",
        )


@router.get("/endpoints", response_model=dict)
async def get_endpoint_metrics(
    limit: int = 20,
    current_user: User = Depends(require_admin_user),
):
    """
    Obține metrici pentru endpoint-uri.

    **Necesită:** Admin role

    **Args:**
    - limit: Număr maxim de endpoint-uri de returnat

    **Returns:**
    Lista de endpoint-uri cu metrici
    """
    try:
        redis = await get_redis()

        # Get all endpoint metrics
        endpoints = []
        cursor = 0

        while True:
            cursor, keys = await redis.scan(
                cursor, match="metrics:requests:*", count=100
            )

            for key in keys:
                # Extract endpoint from key
                endpoint_key = key.decode("utf-8").replace("metrics:requests:", "")

                # Get metrics
                request_count = await redis.get(key)
                duration_key = f"metrics:duration:{endpoint_key}"
                total_duration = await redis.get(duration_key)
                slow_key = f"metrics:slow:{endpoint_key}"
                slow_count = await redis.get(slow_key)

                request_count = int(request_count) if request_count else 0
                total_duration = float(total_duration) if total_duration else 0.0
                slow_count = int(slow_count) if slow_count else 0

                avg_duration = (
                    total_duration / request_count if request_count > 0 else 0.0
                )

                endpoints.append(
                    {
                        "endpoint": endpoint_key,
                        "request_count": request_count,
                        "avg_duration": round(avg_duration, 3),
                        "slow_requests": slow_count,
                        "slow_percentage": (
                            round((slow_count / request_count) * 100, 2)
                            if request_count > 0
                            else 0.0
                        ),
                    }
                )

            if cursor == 0:
                break

        # Sort by request count and limit
        endpoints.sort(key=lambda x: x["request_count"], reverse=True)
        endpoints = endpoints[:limit]

        return {
            "status": "success",
            "data": {
                "endpoints": endpoints,
                "total": len(endpoints),
            },
        }

    except Exception as e:
        logger.error(f"Error getting endpoint metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint metrics: {str(e)}",
        )


@router.get("/slowest", response_model=dict)
async def get_slowest_endpoints(
    limit: int = 10,
    current_user: User = Depends(require_admin_user),
):
    """
    Obține cele mai lente endpoint-uri.

    **Necesită:** Admin role

    **Args:**
    - limit: Număr maxim de endpoint-uri de returnat

    **Returns:**
    Lista celor mai lente endpoint-uri
    """
    try:
        redis = await get_redis()

        # Get all endpoint metrics
        endpoints = []
        cursor = 0

        while True:
            cursor, keys = await redis.scan(
                cursor, match="metrics:requests:*", count=100
            )

            for key in keys:
                endpoint_key = key.decode("utf-8").replace("metrics:requests:", "")

                request_count = await redis.get(key)
                duration_key = f"metrics:duration:{endpoint_key}"
                total_duration = await redis.get(duration_key)

                request_count = int(request_count) if request_count else 0
                total_duration = float(total_duration) if total_duration else 0.0

                if request_count > 0:
                    avg_duration = total_duration / request_count
                    endpoints.append(
                        {
                            "endpoint": endpoint_key,
                            "avg_duration": round(avg_duration, 3),
                            "request_count": request_count,
                        }
                    )

            if cursor == 0:
                break

        # Sort by average duration
        endpoints.sort(key=lambda x: x["avg_duration"], reverse=True)
        endpoints = endpoints[:limit]

        return {
            "status": "success",
            "data": {
                "slowest_endpoints": endpoints,
                "total": len(endpoints),
            },
        }

    except Exception as e:
        logger.error(f"Error getting slowest endpoints: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get slowest endpoints: {str(e)}",
        )


@router.delete("/reset", response_model=dict)
async def reset_metrics(
    current_user: User = Depends(require_admin_user),
):
    """
    Resetează toate metricile de performanță.

    **Necesită:** Admin role

    **Returns:**
    - success: True dacă resetarea a avut succes
    """
    try:
        redis = await get_redis()

        # Delete all metrics keys
        deleted_count = 0
        for pattern in [
            "metrics:requests:*",
            "metrics:duration:*",
            "metrics:slow:*",
            "metrics:status:*",
        ]:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break

        return {
            "status": "success",
            "message": f"Deleted {deleted_count} metric keys",
            "data": {"deleted_keys": deleted_count},
        }

    except Exception as e:
        logger.error(f"Error resetting metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset metrics: {str(e)}",
        )

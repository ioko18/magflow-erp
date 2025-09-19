"""Prometheus metrics endpoint for the application."""
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, REGISTRY
from prometheus_client.exposition import generate_latest as prom_generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
import os

router = APIRouter(prefix="/metrics", tags=["monitoring"])

@router.get(
    "/",
    summary="Prometheus metrics",
    description="Exposes Prometheus metrics for the application",
    response_description="Prometheus metrics in text format",
    tags=["monitoring"],
)
async def get_metrics():
    """Return Prometheus metrics."""
    # Check if we're running in a multiprocess environment
    if 'prometheus_multiproc_dir' in os.environ:
        registry = REGISTRY
        collector = MultiProcessCollector(registry)
        return Response(
            content=prom_generate_latest(collector.registry),
            media_type=CONTENT_TYPE_LATEST,
        )
    else:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

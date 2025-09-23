from __future__ import annotations

import os

from celery import Celery

# Broker and backend default to Redis and fall back to REDIS_URL if specific vars are not provided
BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

# Create Celery application
celery_app = Celery(
    "magflow",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.services.tasks.sample",
        "app.services.tasks.maintenance",
    ],
)

# Basic, safe Celery configuration
celery_app.conf.update(
    # Core behavior
    task_default_queue="default",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=os.getenv("TZ", "UTC"),
    enable_utc=True,

    # Robustness and reliability
    broker_connection_retry_on_startup=True,
    broker_heartbeat=int(os.getenv("CELERY_BROKER_HEARTBEAT", "30")),
    broker_pool_limit=int(os.getenv("CELERY_BROKER_POOL_LIMIT", "10")),
    broker_transport_options={
        # Make sure unacked tasks are re-queued if worker dies
        "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
        # Keep the connection alive at TCP layer
        "socket_keepalive": True,
        # Retry in case of timeouts
        "retry_on_timeout": True,
    },

    # Task acknowledgement and worker resiliency
    task_acks_late=os.getenv("CELERY_TASK_ACKS_LATE", "true").lower() == "true",
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),

    # Results expiration to avoid unbounded growth
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", str(60 * 60 * 24))),  # 24h
)

# Beat (scheduler) configuration - lightweight heartbeat task
celery_app.conf.beat_schedule = {
    "maintenance.heartbeat": {
        "task": "maintenance.heartbeat",
        # Interval in seconds, overridable via env
        "schedule": int(os.getenv("CELERY_HEARTBEAT_INTERVAL", "60")),
    }
}

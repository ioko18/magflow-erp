from __future__ import annotations

import os
import socket
from datetime import UTC, datetime

from celery import shared_task


@shared_task(name="maintenance.heartbeat")
def heartbeat() -> dict:
    """Lightweight heartbeat task used by Celery Beat.

    Returns a small payload that can be inspected in Flower/Logs.
    """
    return {
        "status": "ok",
        "service": "celery-beat",
        "host": socket.gethostname(),
        "timestamp": datetime.now(UTC).isoformat(),
        "env": {
            "TZ": os.getenv("TZ", "UTC"),
        },
    }

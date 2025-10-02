"""
Celery Beat Schedule Configuration for eMAG Synchronization.

This module defines the periodic task schedule for automated eMAG synchronization:
- Product synchronization every hour
- Order synchronization every 5 minutes
- Auto-acknowledgment of new orders
- Cleanup of old sync logs
- Health checks
"""

from celery.schedules import crontab
import os

# Get configuration from environment
EMAG_SYNC_INTERVAL_MINUTES = int(os.getenv("EMAG_SYNC_INTERVAL_MINUTES", "60"))
EMAG_ENABLE_SCHEDULED_SYNC = os.getenv("EMAG_ENABLE_SCHEDULED_SYNC", "false").lower() == "true"
EMAG_LOG_RETENTION = int(os.getenv("EMAG_MAIN_LOG_RETENTION", "30"))

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    # Product synchronization - runs every hour (or configured interval)
    "sync-emag-products-hourly": {
        "task": "emag.sync_products",
        "schedule": EMAG_SYNC_INTERVAL_MINUTES * 60.0,  # Convert to seconds
        "args": ("both", 10),  # Sync both accounts, max 10 pages each
        "options": {
            "expires": 3600,  # Task expires after 1 hour
        },
        "enabled": EMAG_ENABLE_SCHEDULED_SYNC,
    },
    
    # Order synchronization - runs every 5 minutes
    "sync-emag-orders-5min": {
        "task": "emag.sync_orders",
        "schedule": 300.0,  # 5 minutes
        "options": {
            "expires": 300,  # Task expires after 5 minutes
        },
        "enabled": True,  # Always enabled for orders
    },
    
    # Auto-acknowledge new orders - runs every 10 minutes
    "auto-acknowledge-orders-10min": {
        "task": "emag.auto_acknowledge_orders",
        "schedule": 600.0,  # 10 minutes
        "options": {
            "expires": 600,
        },
        "enabled": True,
    },
    
    # Cleanup old sync logs - runs daily at 3 AM
    "cleanup-sync-logs-daily": {
        "task": "emag.cleanup_old_sync_logs",
        "schedule": crontab(hour=3, minute=0),
        "args": (EMAG_LOG_RETENTION,),
        "options": {
            "expires": 3600,
        },
        "enabled": True,
    },
    
    # Health check - runs every 15 minutes
    "emag-health-check-15min": {
        "task": "emag.health_check",
        "schedule": 900.0,  # 15 minutes
        "options": {
            "expires": 900,
        },
        "enabled": True,
    },
    
    # Full product sync - runs daily at 2 AM (for comprehensive sync)
    "full-product-sync-daily": {
        "task": "emag.sync_products",
        "schedule": crontab(hour=2, minute=0),
        "args": ("both", None),  # Sync all pages
        "options": {
            "expires": 7200,  # 2 hours
        },
        "enabled": EMAG_ENABLE_SCHEDULED_SYNC,
    },
}


def get_beat_schedule():
    """Get the Celery Beat schedule with only enabled tasks."""
    return {
        name: config
        for name, config in CELERY_BEAT_SCHEDULE.items()
        if config.get("enabled", True)
    }

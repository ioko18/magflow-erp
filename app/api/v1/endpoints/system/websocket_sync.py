"""
WebSocket endpoints for real-time eMAG sync progress.

This module provides WebSocket connections for live sync progress updates,
eliminating the need for polling and providing instant feedback to users.
"""

import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from app.core.database import get_async_session
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Active WebSocket connections
active_connections: set[WebSocket] = set()
# Sync progress cache
sync_progress_cache: dict[str, dict] = {}


class ConnectionManager:
    """Manages WebSocket connections for sync progress updates."""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to websocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected WebSockets."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def get_sync_progress_from_db():
    """Fetch current sync progress from database."""
    try:
        async for async_db in get_async_session():
            query = """
                SELECT
                    sync_type,
                    account_type,
                    status,
                    sync_params,
                    started_at,
                    processed_items,
                    total_items,
                    EXTRACT(EPOCH FROM (NOW() - started_at)) as duration_seconds,
                    COALESCE(
                        ARRAY_TO_STRING(
                            ARRAY(SELECT jsonb_array_elements_text(errors)), ', '
                        ),
                        NULL
                    ) as error_message
                FROM app.emag_sync_logs
                WHERE status = 'running'
                  AND sync_type IN ('products', 'offers', 'orders')
                ORDER BY started_at DESC
                LIMIT 10
            """
            result = await async_db.execute(text(query))
            active_syncs = result.fetchall()

            progress_data = []
            for sync in active_syncs:
                sync_params = sync.sync_params or {}
                items_processed = sync.processed_items or 0
                items_total = sync.total_items or 0
                duration = sync.duration_seconds or 0

                # Calculate metrics
                throughput = items_processed / duration if duration > 0 else 0
                remaining_items = max(0, items_total - items_processed)
                eta_seconds = remaining_items / throughput if throughput > 0 else 0
                progress_pct = int(
                    (items_processed / items_total * 100) if items_total > 0 else 0
                )

                progress_data.append(
                    {
                        "sync_type": sync.sync_type,
                        "account_type": sync.account_type,
                        "status": sync.status,
                        "current_page": sync_params.get("current_page", 0),
                        "total_pages": sync_params.get("max_pages_per_account", 0),
                        "processed_items": items_processed,
                        "total_items": items_total,
                        "progress_percentage": progress_pct,
                        "started_at": sync.started_at.isoformat()
                        if sync.started_at
                        else None,
                        "duration_seconds": int(duration),
                        "throughput_per_second": round(throughput, 2),
                        "estimated_time_remaining_seconds": int(eta_seconds),
                        "error_message": sync.error_message,
                    }
                )

            return {
                "is_running": len(progress_data) > 0,
                "active_syncs": progress_data,
                "total_active": len(progress_data),
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "syncing" if progress_data else "idle",
            }

    except Exception as e:
        logger.error(f"Error fetching sync progress: {e}", exc_info=True)
        return {
            "is_running": False,
            "active_syncs": [],
            "total_active": 0,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.websocket("/ws/sync-progress")
async def websocket_sync_progress(websocket: WebSocket):
    """
    WebSocket endpoint for real-time sync progress updates.

    Provides live updates every second with:
    - Current sync status
    - Progress percentage
    - Throughput metrics
    - ETA calculation
    - Error messages

    Usage:
        const ws = new WebSocket('ws://localhost:8000/api/v1/emag/enhanced/ws/sync-progress');
        ws.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            console.log('Sync progress:', progress);
        };
    """
    await manager.connect(websocket)

    try:
        # Send initial status
        initial_progress = await get_sync_progress_from_db()
        await manager.send_personal_message(initial_progress, websocket)

        # Keep connection alive and send updates
        while True:
            try:
                # Check for client messages (ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)

                # Handle client messages
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json(
                            {"type": "pong", "timestamp": datetime.now(UTC).isoformat()}
                        )
                except json.JSONDecodeError:
                    pass

            except TimeoutError:
                # No message from client, send progress update
                progress = await get_sync_progress_from_db()
                await manager.send_personal_message(progress, websocket)

            # Small delay to prevent overwhelming
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from sync progress WebSocket")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/ws/sync-events")
async def websocket_sync_events(websocket: WebSocket):
    """
    WebSocket endpoint for sync event notifications.

    Sends notifications when:
    - Sync starts
    - Sync completes
    - Sync fails
    - Milestones reached (25%, 50%, 75%, 100%)

    Usage:
        const ws = new WebSocket('ws://localhost:8000/api/v1/emag/enhanced/ws/sync-events');
        ws.onmessage = (event) => {
            const notification = JSON.parse(event.data);
            showNotification(notification.message);
        };
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to sync events stream",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            websocket,
        )

        last_progress = 0

        while True:
            try:
                # Wait for messages with timeout
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except TimeoutError:
                # Check for sync events
                progress = await get_sync_progress_from_db()

                if progress["is_running"] and progress["active_syncs"]:
                    current_sync = progress["active_syncs"][0]
                    current_progress = current_sync["progress_percentage"]

                    # Check for milestones
                    milestones = [25, 50, 75, 100]
                    for milestone in milestones:
                        if last_progress < milestone <= current_progress:
                            await manager.send_personal_message(
                                {
                                    "type": "milestone",
                                    "milestone": milestone,
                                    "message": f"Sync progress: {milestone}% complete",
                                    "sync_type": current_sync["sync_type"],
                                    "account_type": current_sync["account_type"],
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                                websocket,
                            )

                    last_progress = current_progress
                elif not progress["is_running"] and last_progress > 0:
                    # Sync completed
                    await manager.send_personal_message(
                        {
                            "type": "completed",
                            "message": "Sync completed successfully",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                        websocket,
                    )
                    last_progress = 0

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from sync events WebSocket")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


async def broadcast_sync_update(sync_data: dict):
    """
    Broadcast sync update to all connected clients.

    This function can be called from sync services to push updates.
    """
    await manager.broadcast(
        {
            "type": "sync_update",
            "data": sync_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


async def broadcast_sync_event(event_type: str, message: str, **kwargs):
    """
    Broadcast sync event to all connected clients.

    Args:
        event_type: Type of event (started, completed, failed, milestone)
        message: Human-readable message
        **kwargs: Additional event data
    """
    await manager.broadcast(
        {
            "type": event_type,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }
    )

"""
WebSocket endpoint for real-time notifications.

Provides real-time updates for:
- New eMAG orders
- Order status changes
- AWB generation
- Invoice generation
- Sync progress
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.emag_models import EmagOrder

logger = get_logger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {
            "orders": set(),
            "sync": set(),
            "all": set(),
        }

    async def connect(self, websocket: WebSocket, channel: str = "all"):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[channel].add(websocket)
        self.active_connections["all"].add(websocket)
        logger.info(f"New WebSocket connection on channel: {channel}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from all channels."""
        for channel in self.active_connections.values():
            channel.discard(websocket)
        logger.info("WebSocket connection closed")

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocket
    ):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any], channel: str = "all"):
        """Broadcast a message to all connections on a channel."""
        disconnected = set()

        for websocket in self.active_connections.get(channel, set()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to connection: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    def get_connection_count(self, channel: str = "all") -> int:
        """Get the number of active connections on a channel."""
        return len(self.active_connections.get(channel, set()))


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket, channel: str = "all", db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    Channels:
    - 'all': All notifications
    - 'orders': Order-related notifications
    - 'sync': Sync progress notifications

    Message format:
    {
        "type": "order_new" | "order_update" | "sync_progress" | "awb_generated" | "invoice_generated",
        "data": {...},
        "timestamp": "ISO8601"
    }
    """
    await manager.connect(websocket, channel)

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            {
                "type": "connection_established",
                "channel": channel,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            websocket,
        )

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Receive message from client (ping/pong or commands)
                data = await websocket.receive_text()

                # Handle client commands
                if data == "ping":
                    await manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now(UTC).isoformat()},
                        websocket,
                    )

                elif data.startswith("subscribe:"):
                    # Allow dynamic channel subscription
                    new_channel = data.split(":", 1)[1]
                    if new_channel in manager.active_connections:
                        manager.active_connections[new_channel].add(websocket)
                        await manager.send_personal_message(
                            {
                                "type": "subscribed",
                                "channel": new_channel,
                                "timestamp": datetime.now(UTC).isoformat(),
                            },
                            websocket,
                        )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break

    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint specifically for order notifications.

    Sends real-time updates when:
    - New orders arrive
    - Order status changes
    - AWB is generated
    - Invoice is attached
    """
    await manager.connect(websocket, "orders")

    try:
        # Send initial order statistics
        from sqlalchemy import func

        result = await db.execute(
            select(func.count(EmagOrder.id)).where(EmagOrder.status == 1)
        )
        new_orders_count = result.scalar()

        await manager.send_personal_message(
            {
                "type": "initial_stats",
                "data": {"new_orders": new_orders_count},
                "timestamp": datetime.now(UTC).isoformat(),
            },
            websocket,
        )

        # Monitor for new orders (polling every 10 seconds)
        last_check = datetime.now(UTC)

        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                # Check for new orders since last check
                result = await db.execute(
                    select(EmagOrder).where(
                        and_(EmagOrder.status == 1, EmagOrder.created_at > last_check)
                    )
                )
                new_orders = result.scalars().all()

                if new_orders:
                    for order in new_orders:
                        await manager.broadcast(
                            {
                                "type": "order_new",
                                "data": {
                                    "order_id": order.emag_order_id,
                                    "customer_name": order.customer_name,
                                    "total_amount": float(order.total_amount)
                                    if order.total_amount
                                    else 0,
                                    "currency": order.currency,
                                    "account_type": order.account_type,
                                },
                                "timestamp": datetime.now(UTC).isoformat(),
                            },
                            channel="orders",
                        )

                last_check = datetime.now(UTC)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error monitoring orders: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    finally:
        manager.disconnect(websocket)


# Helper functions to send notifications from other parts of the application


async def notify_new_order(order_data: dict[str, Any]):
    """
    Send notification about a new order.

    Args:
        order_data: Dictionary with order information
    """
    await manager.broadcast(
        {
            "type": "order_new",
            "data": order_data,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        channel="orders",
    )


async def notify_order_status_change(order_id: int, old_status: int, new_status: int):
    """
    Send notification about order status change.

    Args:
        order_id: eMAG order ID
        old_status: Previous status code
        new_status: New status code
    """
    status_names = {
        0: "canceled",
        1: "new",
        2: "in_progress",
        3: "prepared",
        4: "finalized",
        5: "returned",
    }

    await manager.broadcast(
        {
            "type": "order_status_change",
            "data": {
                "order_id": order_id,
                "old_status": old_status,
                "old_status_name": status_names.get(old_status, "unknown"),
                "new_status": new_status,
                "new_status_name": status_names.get(new_status, "unknown"),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
        channel="orders",
    )


async def notify_awb_generated(order_id: int, awb_number: str):
    """
    Send notification about AWB generation.

    Args:
        order_id: eMAG order ID
        awb_number: Generated AWB number
    """
    await manager.broadcast(
        {
            "type": "awb_generated",
            "data": {
                "order_id": order_id,
                "awb_number": awb_number,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
        channel="orders",
    )


async def notify_invoice_generated(order_id: int, invoice_number: str):
    """
    Send notification about invoice generation.

    Args:
        order_id: eMAG order ID
        invoice_number: Generated invoice number
    """
    await manager.broadcast(
        {
            "type": "invoice_generated",
            "data": {
                "order_id": order_id,
                "invoice_number": invoice_number,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
        channel="orders",
    )


async def notify_sync_progress(
    account_type: str, progress: int, total: int, message: str
):
    """
    Send notification about sync progress.

    Args:
        account_type: Account being synced
        progress: Current progress count
        total: Total items to sync
        message: Progress message
    """
    await manager.broadcast(
        {
            "type": "sync_progress",
            "data": {
                "account_type": account_type,
                "progress": progress,
                "total": total,
                "percentage": (progress / total * 100) if total > 0 else 0,
                "message": message,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
        channel="sync",
    )


# Endpoint to get connection statistics
@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": manager.get_connection_count("all"),
        "orders_channel": manager.get_connection_count("orders"),
        "sync_channel": manager.get_connection_count("sync"),
        "timestamp": datetime.now(UTC).isoformat(),
    }

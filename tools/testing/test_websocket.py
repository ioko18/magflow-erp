#!/usr/bin/env python3
"""
Test WebSocket connection for real-time sync progress.
"""

import asyncio
import json

import websockets


async def test_websocket():
    """Test WebSocket connection."""
    uri = "ws://localhost:8000/api/v1/emag/enhanced/ws/sync-progress"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")

            # Receive initial message
            message = await websocket.recv()
            data = json.loads(message)
            print("\n📊 Initial sync status:")
            print("  Status: {}".format(data.get('status')))
            print("  Is Running: {}".format(data.get('is_running')))
            print("  Active Syncs: {}".format(data.get('total_active')))

            # Listen for updates for 10 seconds
            print("\n🔄 Listening for updates (10 seconds)...")
            for i in range(10):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.5)
                    data = json.loads(message)

                    if data.get('is_running'):
                        syncs = data.get('active_syncs', [])
                        if syncs:
                            sync = syncs[0]
                            print(f"  [{i+1}] Progress: {sync.get('progress_percentage')}% "
                                  f"({sync.get('processed_items')}/{sync.get('total_items')} items)")
                    else:
                        print(f"  [{i+1}] No active syncs")

                except TimeoutError:
                    print(f"  [{i+1}] No update (timeout)")

            print("\n✅ WebSocket test completed successfully!")

    except Exception as e:
        print(f"\n❌ WebSocket test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)

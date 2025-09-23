#!/usr/bin/env python3
"""Test script to verify monitoring setup.
This script simulates traffic and verifies that metrics are being collected correctly.
"""

import random
import time

import requests

# Configuration
BASE_URL = "http://localhost:8000"
METRICS_URL = f"{BASE_URL}/metrics"
HEALTH_URL = f"{BASE_URL}/health"

# Sample endpoints to test
ENDPOINTS = [
    "/api/v1/auth/login",
    "/api/v1/users/me",
    "/api/v1/items",
    "/api/v1/items/1",
]


def check_metrics() -> bool:
    """Check if metrics endpoint is working."""
    try:
        response = requests.get(METRICS_URL, timeout=5)
        if (
            response.status_code == 200
            and "http_server_requests_total" in response.text
        ):
            print("✅ Metrics endpoint is working")
            return True
        print(
            f"❌ Metrics endpoint returned unexpected response: {response.status_code}",
        )
        return False
    except Exception as e:
        print(f"❌ Failed to fetch metrics: {e}")
        return False


def simulate_traffic(duration_seconds: int = 60) -> None:
    """Simulate HTTP traffic to generate metrics."""
    print(f"🚀 Simulating traffic for {duration_seconds} seconds...")

    end_time = time.time() + duration_seconds
    request_count = 0

    while time.time() < end_time:
        try:
            # Randomly select an endpoint
            endpoint = random.choice(ENDPOINTS)
            url = f"{BASE_URL}{endpoint}"

            # Make the request
            requests.get(url, timeout=5)
            request_count += 1

            # Print status every 10 requests
            if request_count % 10 == 0:
                print(f"  Sent {request_count} requests...")

            # Random delay between requests
            time.sleep(0.1)

        except Exception as e:
            print(f"  Error making request: {e}")
            time.sleep(1)

    print(f"✅ Traffic simulation complete. Sent {request_count} requests.")


def check_alert_conditions() -> None:
    """Check if alert conditions are properly configured."""
    print("\n🔍 Checking alert conditions...")

    # Check if metrics for alert conditions exist
    metrics_to_check = [
        "http_server_duration_milliseconds_bucket",
        "http_server_requests_total",
        "health_status",
    ]

    try:
        response = requests.get(METRICS_URL, timeout=5)
        metrics_text = response.text

        for metric in metrics_to_check:
            if metric in metrics_text:
                print(f"✅ Found metric: {metric}")
            else:
                print(f"❌ Missing metric: {metric}")

    except Exception as e:
        print(f"❌ Failed to check alert conditions: {e}")


def main():
    print("🔍 Starting monitoring test...")

    # Check if metrics endpoint is working
    if not check_metrics():
        print("❌ Initial metrics check failed. Exiting.")
        return

    # Simulate traffic to generate metrics
    simulate_traffic(duration_seconds=30)

    # Check alert conditions
    check_alert_conditions()

    print("\n✅ Monitoring test complete.")
    print(
        "Check your Grafana dashboard at http://localhost:3000 to verify the metrics.",
    )


if __name__ == "__main__":
    main()

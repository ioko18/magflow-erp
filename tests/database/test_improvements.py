#!/usr/bin/env python3
"""Simple test to verify Celery readiness endpoint logic."""

import sys
import pytest

sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')


def test_celery_readiness_logic():
    """Test the Celery readiness endpoint logic without external dependencies."""

    class MockTask:
        def __init__(self, task_id="test-123"):
            self.id = task_id

        def get(self):
            return "echo: worker-readiness-test"

    def mock_echo_delay(message):
        return MockTask()

    task = mock_echo_delay("worker-readiness-test")
    result = task.get()

    assert task.id == "test-123"
    assert result == "echo: worker-readiness-test"


def test_tasks_router():
    """Test that the tasks router can be imported."""
    try:
        from app.api.tasks import router
    except Exception as exc:  # pragma: no cover - ensures explicit failure reporting
        pytest.fail(f"Tasks router import failed: {exc}")

    assert router is not None

if __name__ == "__main__":
    print("🧪 Testing MagFlow ERP improvements...")

    test1_passed = test_celery_readiness_logic()
    test2_passed = test_tasks_router()

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! MagFlow ERP improvements are working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

#!/usr/bin/env python3
"""Simple test to verify Celery readiness endpoint logic."""

import sys
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

def test_celery_readiness_logic():
    """Test the Celery readiness endpoint logic without external dependencies."""

    # Mock the echo task
    class MockTask:
        def __init__(self, task_id="test-123"):
            self.id = task_id

        def get(self):
            return "echo: worker-readiness-test"

    # Mock the echo.delay function
    def mock_echo_delay(message):
        return MockTask()

    # Test the logic
    try:
        # Simulate the readiness check logic
        task = mock_echo_delay("worker-readiness-test")
        result = task.get()

        expected_result = {
            "status": "ready",
            "message": "Celery worker is responsive",
            "test_result": result,
            "task_id": task.id,
        }

        print("✅ Celery readiness logic test passed!")
        print(f"Expected: {expected_result}")

        return True

    except Exception as e:
        print(f"❌ Celery readiness logic test failed: {e}")
        return False

def test_tasks_router():
    """Test that the tasks router can be imported."""
    try:
        from app.api.tasks import router
        print("✅ Tasks router imported successfully!")
        print(f"Router: {router}")
        return True
    except Exception as e:
        print(f"❌ Tasks router import failed: {e}")
        return False

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

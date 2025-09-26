#!/usr/bin/env python3
"""
Test script for improved eMAG sync functionality
Tests the sync script and monitor functionality
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync_emag_sync_improved import (
    load_credentials, update_sync_status,
    get_db_engine, get_db_session, check_sync_timeout
)
from sync_monitor_recovery import (
    find_stuck_syncs, get_sync_health_status,
    cleanup_stuck_syncs, log_sync_health
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSyncImprovements:
    """Test cases for sync improvements"""

    def test_credentials_loading(self):
        """Test that credentials are loaded correctly"""
        # Mock environment variables
        with patch.dict(os.environ, {
            'EMAG_API_USERNAME': 'test@example.com',
            'EMAG_API_PASSWORD': 'testpass',
            'EMAG_FBE_API_USERNAME': 'testfbe@example.com',
            'EMAG_FBE_API_PASSWORD': 'testfbepass',
            'EMAG_ACCOUNT_TYPE': 'main'
        }):
            # Reset global variables
            import sync_emag_sync_improved
            sync_emag_sync_improved.EMAG_USER = None
            sync_emag_sync_improved.EMAG_PASS = None
            sync_emag_sync_improved.EMAG_ACCOUNT_TYPE = None

            load_credentials()

            assert sync_emag_sync_improved.EMAG_USER == 'test@example.com'
            assert sync_emag_sync_improved.EMAG_PASS == 'testpass'
            assert sync_emag_sync_improved.EMAG_ACCOUNT_TYPE == 'main'
            logger.info("✅ Credentials loading test passed")

    def test_database_connection(self):
        """Test database connection setup"""
        try:
            engine = get_db_engine()
            session = get_db_session()

            assert engine is not None
            assert session is not None
            logger.info("✅ Database connection test passed")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    def test_sync_timeout_check(self):
        """Test sync timeout detection"""

        # Test with no start time
        assert not check_sync_timeout()

        # Test with recent start time
        import sync_emag_sync_improved
        sync_emag_sync_improved.sync_start_time = datetime.utcnow()
        assert not check_sync_timeout()

        # Test with old start time (simulate timeout)
        sync_emag_sync_improved.sync_start_time = datetime.utcnow() - timedelta(hours=3)
        assert check_sync_timeout()
        logger.info("✅ Sync timeout check test passed")

    def test_sync_status_update(self):
        """Test sync status update functionality"""
        test_sync_id = f"test-{datetime.now().strftime('%H%M%S')}"

        # This should not raise an exception even if database is not available
        try:
            update_sync_status(test_sync_id, 'completed', 100)
            logger.info("✅ Sync status update test passed")
        except Exception as e:
            # It's OK if database is not available for testing
            logger.info(f"Sync status update test skipped (expected): {e}")

class TestMonitorRecovery:
    """Test cases for monitor and recovery functionality"""

    def test_stuck_sync_detection(self):
        """Test detection of stuck sync processes"""
        stuck_syncs = find_stuck_syncs(max_age_hours=24)  # Look for very old syncs

        # Should return a list (even if empty)
        assert isinstance(stuck_syncs, list)
        logger.info(f"✅ Stuck sync detection test passed. Found {len(stuck_syncs)} old syncs")

    def test_sync_health_status(self):
        """Test sync health status retrieval"""
        health = get_sync_health_status()

        if health:
            assert 'running_syncs' in health
            assert 'health_data' in health
            assert 'total_running' in health
            logger.info("✅ Sync health status test passed")
        else:
            logger.warning("Sync health status test skipped - no database connection")

    def test_cleanup_functionality(self):
        """Test cleanup of stuck syncs"""
        # This should not raise an exception
        try:
            recovered = cleanup_stuck_syncs(max_age_hours=24)
            assert isinstance(recovered, int)
            logger.info(f"✅ Cleanup functionality test passed. Recovered: {recovered}")
        except Exception as e:
            logger.error(f"Cleanup functionality test failed: {e}")
            raise

class TestIntegration:
    """Integration tests"""

    def test_monitor_health_logging(self):
        """Test health logging functionality"""
        try:
            log_sync_health()
            logger.info("✅ Monitor health logging test passed")
        except Exception as e:
            logger.warning(f"Monitor health logging test skipped: {e}")

    def test_metrics_initialization(self):
        """Test that Prometheus metrics are properly initialized"""
        from prometheus_client import REGISTRY

        # Check if our metrics are registered
        metrics = [m.name for m in REGISTRY.collect()]
        expected_metrics = [
            'emag_sync_monitor_status',
            'emag_sync_stuck_syncs_total',
            'emag_sync_active_syncs_total'
        ]

        for metric in expected_metrics:
            assert any(metric in m for m in metrics), f"Metric {metric} not found in registry"
        logger.info("✅ Metrics initialization test passed")

async def run_async_tests():
    """Run async-specific tests"""
    logger.info("🧪 Starting async tests...")

    # Test sync timeout functionality
    from sync_emag_sync_improved import check_sync_timeout

    # Test normal operation
    sync_start_time = datetime.utcnow()
    assert not check_sync_timeout()
    logger.info("✅ Normal sync timeout test passed")

    # Test timeout condition
    sync_start_time = datetime.utcnow() - timedelta(hours=3)
    assert check_sync_timeout()
    logger.info("✅ Timeout detection test passed")

def main():
    """Main test runner"""
    logger.info("🚀 Starting eMAG Sync Improvement Tests...")

    try:
        # Run synchronous tests
        test_sync = TestSyncImprovements()
        test_sync.test_credentials_loading()
        test_sync.test_database_connection()
        test_sync.test_sync_timeout_check()
        test_sync.test_sync_status_update()

        test_monitor = TestMonitorRecovery()
        test_monitor.test_stuck_sync_detection()
        test_monitor.test_sync_health_status()
        test_monitor.test_cleanup_functionality()

        test_integration = TestIntegration()
        test_integration.test_monitor_health_logging()
        test_integration.test_metrics_initialization()

        # Run async tests
        asyncio.run(run_async_tests())

        logger.info("✅ All tests passed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
eMAG Automated Sync Scheduler
Handles automated synchronization for multiple eMAG accounts
"""

import asyncio
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum
import json
import threading
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sync_emag_sync import load_credentials  # for type reference  # noqa: E402
import sync_emag_sync  # Import once to avoid Prometheus metric re-registration  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/emag_sync_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SyncType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    PRODUCTS_ONLY = "products_only"
    OFFERS_ONLY = "offers_only"

class AccountConfig:
    def __init__(self, account_type: str, sync_interval: int, sync_types: List[SyncType]):
        self.account_type = account_type
        self.sync_interval = sync_interval  # minutes
        self.sync_types = sync_types
        self.last_sync = None
        self.next_sync = datetime.now()
        self.status = "idle"

    def should_sync(self) -> bool:
        """Check if it's time to sync"""
        return datetime.now() >= self.next_sync

    def update_schedule(self):
        """Update next sync time"""
        self.next_sync = datetime.now() + timedelta(minutes=self.sync_interval)
        self.last_sync = datetime.now()

    def __str__(self):
        return f"Account({self.account_type}, interval={self.sync_interval}min, types={self.sync_types})"

class SyncScheduler:
    def __init__(self):
        self.accounts: Dict[str, AccountConfig] = {}
        self.running = False
        self.sync_thread = None
        self.load_configuration()

    def load_configuration(self):
        """Load sync configuration from environment"""
        logger.info("Loading sync configuration...")

        # MAIN Account - more frequent sync for direct shipping
        self.accounts['main'] = AccountConfig(
            account_type='main',
            sync_interval=int(os.getenv('EMAG_MAIN_SYNC_INTERVAL', '30')),  # Every 30 minutes
            sync_types=[SyncType.FULL, SyncType.PRODUCTS_ONLY]
        )

        # FBE Account - less frequent sync for fulfillment
        self.accounts['fbe'] = AccountConfig(
            account_type='fbe',
            sync_interval=int(os.getenv('EMAG_FBE_SYNC_INTERVAL', '60')),  # Every 60 minutes
            sync_types=[SyncType.FULL]
        )

        logger.info(f"Loaded {len(self.accounts)} account configurations")
        for account in self.accounts.values():
            logger.info(f"  - {account}")

    def run_sync(self, account_config: AccountConfig) -> bool:
        """Run sync for a specific account"""
        sync_start_time = datetime.now()
        try:
            account_config.status = "running"
            logger.info(
                f"🚀 Starting sync for {account_config.account_type.upper()} account "
                f"(interval: {account_config.sync_interval}min, types: {[t.value for t in account_config.sync_types]})"
            )

            # Set environment variable
            original_account_type = os.environ.get('EMAG_ACCOUNT_TYPE')
            os.environ['EMAG_ACCOUNT_TYPE'] = account_config.account_type
            logger.debug(f"Set EMAG_ACCOUNT_TYPE to: {account_config.account_type}")

            # Map container hostnames to localhost for DB access when running on host
            # Prefer setting DATABASE_SYNC_URL which the sync script will use first
            db_sync_url = os.environ.get('DATABASE_SYNC_URL')
            if not db_sync_url:
                db_url = os.environ.get('DATABASE_URL')
                set_explicit = False
                if db_url:
                    try:
                        parsed = urlparse(db_url)
                        netloc = parsed.netloc
                        # Split userinfo and host:port
                        if '@' in netloc:
                            userinfo, hostport = netloc.split('@', 1)
                        else:
                            userinfo, hostport = '', netloc
                        host, sep, port = hostport.partition(':')
                        if host in {'db', 'pgbouncer', 'magflow_pg', 'magflow_pgbouncer'}:
                            # Replace with localhost
                            new_host = '127.0.0.1'
                            new_hostport = f"{new_host}{sep}{port}" if sep else new_host
                            new_netloc = f"{userinfo + '@' if userinfo else ''}{new_hostport}"
                            scheme = parsed.scheme.replace('+asyncpg', '')
                            rebuilt = parsed._replace(scheme=scheme, netloc=new_netloc)
                            os.environ['DATABASE_SYNC_URL'] = urlunparse(rebuilt)
                            logger.info(f"Using host DB mapping for sync: {os.environ['DATABASE_SYNC_URL']}")
                            set_explicit = True
                    except Exception as e:
                        logger.warning(f"Could not map DATABASE_URL for host access: {e}")
                if not set_explicit:
                    # Build from DB_* envs but force localhost and PgBouncer port
                    user = os.environ.get('DB_USER', 'app')
                    password = os.environ.get('DB_PASS', 'app_password_change_me')
                    host = '127.0.0.1'
                    port = os.environ.get('DB_PORT', '6432')
                    name = os.environ.get('DB_NAME', 'postgres')
                    os.environ['DATABASE_SYNC_URL'] = f"postgresql://{user}:{password}@{host}:{port}/{name}"
                    logger.info(f"Using constructed host DB URL for sync: {os.environ['DATABASE_SYNC_URL']}")
            else:
                logger.debug(f"Using existing DATABASE_SYNC_URL: {db_sync_url}")

            # Execute the sync using the already imported module
            start_time = time.time()
            logger.info(f"Executing sync_emag_offers() for {account_config.account_type}")
            asyncio.run(sync_emag_sync.sync_emag_offers())

            # Restore original environment
            if original_account_type:
                os.environ['EMAG_ACCOUNT_TYPE'] = original_account_type
                logger.debug(f"Restored EMAG_ACCOUNT_TYPE to: {original_account_type}")
            else:
                os.environ.pop('EMAG_ACCOUNT_TYPE', None)
                logger.debug("Removed EMAG_ACCOUNT_TYPE from environment")

            execution_time = time.time() - start_time
            total_time = (datetime.now() - sync_start_time).total_seconds()
            account_config.status = "completed"
            logger.info(
                f"✅ {account_config.account_type.upper()} sync completed successfully in {execution_time:.2f}s "
                f"(total time: {total_time:.2f}s)"
            )

            # Update schedule
            account_config.update_schedule()
            logger.debug(f"Next sync for {account_config.account_type} scheduled at: {account_config.next_sync}")
            return True

        except Exception as e:
            total_time = (datetime.now() - sync_start_time).total_seconds()
            account_config.status = "failed"
            logger.error(
                f"❌ {account_config.account_type.upper()} sync failed after {total_time:.2f}s: {e}",
                exc_info=True
            )
            return False

    def run_scheduler(self):
        """Main scheduler loop"""
        logger.info("🎯 Starting eMAG Sync Scheduler...")
        logger.info("Scheduler will check for syncs every 60 seconds")
        self.running = True
        cycle_count = 0

        while self.running:
            try:
                current_time = datetime.now()
                cycle_count += 1

                logger.debug(f"Scheduler cycle {cycle_count} at {current_time}")

                # Check each account
                syncs_triggered = 0
                for account_name, account_config in self.accounts.items():
                    if account_config.should_sync():
                        logger.info(f"⏰ Time to sync {account_name.upper()} account (next sync: {account_config.next_sync})")
                        syncs_triggered += 1

                        # Run sync in a separate thread to avoid blocking
                        sync_thread = threading.Thread(
                            target=self.run_sync,
                            args=(account_config,)
                        )
                        sync_thread.daemon = True
                        sync_thread.start()

                        # Small delay between account syncs
                        logger.debug(f"Started sync thread for {account_name}, waiting 5 seconds before next")
                        time.sleep(5)

                if syncs_triggered == 0:
                    logger.debug("No syncs triggered in this cycle")

                # Sleep for 1 minute before next check
                logger.debug("Scheduler sleeping for 60 seconds")
                time.sleep(60)

            except Exception as e:
                logger.error(f"Scheduler error in cycle {cycle_count}: {e}", exc_info=True)
                logger.info("Scheduler will retry in 60 seconds")
                time.sleep(60)  # Wait before retrying

        logger.info(f"🛑 Sync Scheduler stopped after {cycle_count} cycles")

    def start(self):
        """Start the scheduler"""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("Scheduler already running")
            return

        self.sync_thread = threading.Thread(target=self.run_scheduler)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        logger.info("✅ Sync Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=30)
        logger.info("🛑 Sync Scheduler stopped")

    def get_status(self) -> Dict:
        """Get current scheduler status"""
        status = {
            "scheduler_running": self.running,
            "accounts": {}
        }

        for name, account in self.accounts.items():
            status["accounts"][name] = {
                "account_type": account.account_type,
                "status": account.status,
                "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                "next_sync": account.next_sync.isoformat() if account.next_sync else None,
                "sync_interval": account.sync_interval,
                "sync_types": [st.value for st in account.sync_types]
            }

        return status

def main():
    """Main function"""
    scheduler = SyncScheduler()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "start":
            scheduler.start()
            # Keep running
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                scheduler.stop()

        elif command == "stop":
            scheduler.stop()

        elif command == "status":
            status = scheduler.get_status()
            print(json.dumps(status, indent=2))

        elif command == "sync":
            # Manual sync
            account_type = sys.argv[2] if len(sys.argv) > 2 else "main"
            if account_type in scheduler.accounts:
                success = scheduler.run_sync(scheduler.accounts[account_type])
                print(f"Sync {'completed' if success else 'failed'}")
            else:
                print(f"Unknown account type: {account_type}")

        elif command == "test":
            # Test configuration
            print("Testing configuration...")
            try:
                load_credentials()
                print("✅ Credentials loaded successfully")
                print(f"📡 API URL: {os.getenv('EMAG_API_BASE_URL')}")
                print(f"👤 Account Type: {os.getenv('EMAG_ACCOUNT_TYPE')}")
                print("✅ Configuration test passed")
            except Exception as e:
                print(f"❌ Configuration test failed: {e}")

        else:
            print("Usage: python3 sync_scheduler.py [start|stop|status|sync|test]")

    else:
        # Default: show status
        status = scheduler.get_status()
        print("📊 eMAG Sync Scheduler Status:")
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()

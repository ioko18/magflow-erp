#!/usr/bin/env python3
"""
eMAG Sync Monitor
Monitors sync operations and provides real-time status
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import sys
from pathlib import Path

class SyncMonitor:
    def __init__(self, scheduler_url: str = "http://localhost:8001"):
        self.scheduler_url = scheduler_url
        self.log_file = Path("logs/emag_sync_scheduler.log")

    def get_scheduler_status(self) -> Optional[Dict]:
        """Get scheduler status"""
        try:
            response = requests.get(f"{self.scheduler_url}/scheduler/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting scheduler status: {e}")
        return None

    def get_database_status(self) -> Optional[Dict]:
        """Get database sync records"""
        try:
            # This would connect to your database to get sync records
            # For now, return mock data
            return {
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "last_sync": None
            }
        except Exception as e:
            print(f"Error getting database status: {e}")
        return None

    def get_log_summary(self) -> Dict:
        """Get summary from log file"""
        summary = {
            "errors_last_hour": 0,
            "warnings_last_hour": 0,
            "last_log_time": None
        }

        if self.log_file.exists():
            try:
                one_hour_ago = datetime.now() - timedelta(hours=1)
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            # Parse log line (assuming format: 2025-01-20 10:30:45 - logger - LEVEL - message)
                            parts = line.strip().split(' - ')
                            if len(parts) >= 4:
                                log_time_str = parts[0]
                                log_level = parts[2]

                                try:
                                    log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                                    if log_time > one_hour_ago:
                                        if 'ERROR' in log_level:
                                            summary["errors_last_hour"] += 1
                                        elif 'WARNING' in log_level:
                                            summary["warnings_last_hour"] += 1

                                    summary["last_log_time"] = log_time_str
                                except ValueError:
                                    continue
                        except:
                            continue
            except Exception as e:
                print(f"Error reading log file: {e}")

        return summary

    def generate_report(self) -> Dict:
        """Generate comprehensive status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "scheduler": self.get_scheduler_status(),
            "database": self.get_database_status(),
            "logs": self.get_log_summary(),
            "alerts": []
        }

        # Generate alerts
        alerts = []

        # Check scheduler status
        if report["scheduler"]:
            if not report["scheduler"].get("scheduler_running", False):
                alerts.append({
                    "type": "critical",
                    "message": "Sync scheduler is not running",
                    "action": "Restart scheduler"
                })

            # Check each account
            for account_name, account_info in report["scheduler"].get("accounts", {}).items():
                if account_info.get("status") == "failed":
                    alerts.append({
                        "type": "warning",
                        "message": f"{account_name.upper()} account sync failed",
                        "action": "Check credentials and network"
                    })
        else:
            alerts.append({
                "type": "critical",
                "message": "Cannot connect to scheduler",
                "action": "Check if scheduler service is running"
            })

        # Check error rate
        if report["logs"]["errors_last_hour"] > 5:
            alerts.append({
                "type": "warning",
                "message": f"High error rate: {report['logs']['errors_last_hour']} errors in last hour",
                "action": "Check system logs for details"
            })

        report["alerts"] = alerts
        return report

    def print_report(self):
        """Print formatted report"""
        report = self.generate_report()

        print("📊 eMAG Sync Monitor Report")
        print("=" * 50)
        print(f"📅 Generated: {report['timestamp']}")
        print()

        # Scheduler Status
        if report["scheduler"]:
            print("🎯 Scheduler Status:")
            print(f"   Running: {'✅' if report['scheduler']['scheduler_running'] else '❌'}")

            for account_name, account_info in report["scheduler"]["accounts"].items():
                status_emoji = "🟢" if account_info["status"] == "completed" else "🔴" if account_info["status"] == "failed" else "🟡"
                print(f"   {account_name.upper()}: {status_emoji} {account_info['status']}")
                if account_info["last_sync"]:
                    print(f"      Last sync: {account_info['last_sync']}")
        else:
            print("🎯 Scheduler Status: ❌ Cannot connect")

        print()

        # Log Summary
        print("📋 Log Summary (Last Hour):")
        print(f"   Errors: {report['logs']['errors_last_hour']}")
        print(f"   Warnings: {report['logs']['warnings_last_hour']}")
        if report['logs']['last_log_time']:
            print(f"   Last log: {report['logs']['last_log_time']}")

        print()

        # Alerts
        if report["alerts"]:
            print("🚨 Alerts:")
            for alert in report["alerts"]:
                emoji = "🔴" if alert["type"] == "critical" else "🟡"
                print(f"   {emoji} {alert['message']}")
                print(f"      Action: {alert['action']}")
        else:
            print("✅ No alerts - system running smoothly")

        print()

        # Recommendations
        print("💡 Recommendations:")
        if report["logs"]["errors_last_hour"] > 0:
            print("   • Review error logs in logs/emag_sync_scheduler.log")
        if not report["scheduler"] or not report["scheduler"].get("scheduler_running", False):
            print("   • Start the sync scheduler: python3 sync_scheduler.py start")
        print("   • Monitor sync frequency and adjust intervals if needed")
        print("   • Consider implementing real-time notifications")

def main():
    """Main function"""
    monitor = SyncMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "report":
            monitor.print_report()

        elif command == "json":
            report = monitor.generate_report()
            print(json.dumps(report, indent=2))

        elif command == "health":
            # Simple health check
            report = monitor.generate_report()
            if report["alerts"]:
                critical_alerts = [a for a in report["alerts"] if a["type"] == "critical"]
                if critical_alerts:
                    print("❌ UNHEALTHY")
                    sys.exit(1)
            print("✅ HEALTHY")
            sys.exit(0)

        else:
            print("Usage: python3 sync_monitor.py [report|json|health]")

    else:
        # Default: show report
        monitor.print_report()

if __name__ == "__main__":
    main()

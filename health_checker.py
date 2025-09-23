#!/usr/bin/env python3
"""
Comprehensive Health Check System for MagFlow ERP
Provides detailed health status for all system components
"""

import asyncio
import os
import json
import psutil
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0
    last_check: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SystemHealthReport:
    """Complete system health report"""
    timestamp: datetime
    overall_status: HealthStatus
    uptime_seconds: float
    components: Dict[str, HealthCheckResult] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

class HealthChecker:
    """Comprehensive health check system"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self._database_pool = None

    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # Determine status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "High resource usage detected"
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = "Elevated resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Resource usage normal"

            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            )

        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}"
            )

    def check_database_connection(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        try:
            import psycopg2
            from sqlalchemy import create_engine, text

            start_time = datetime.utcnow()

            # Try multiple connection methods
            db_configs = []

            # Direct database URL
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                db_configs.append(('DATABASE_URL', db_url))

            # Individual parameters
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_pass = os.getenv('DB_PASS')

            if all([db_host, db_port, db_name, db_user, db_pass]):
                db_configs.append(('Individual params', f"postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}"))

            success_count = 0
            total_time = 0

            for config_name, connection_string in db_configs:
                try:
                    # Test connection
                    if db_url:
                        engine = create_engine(db_url)
                        with engine.connect() as conn:
                            result = conn.execute(text("SELECT 1"))
                            result.fetchone()
                    else:
                        conn = psycopg2.connect(
                            host=db_host,
                            port=int(db_port),
                            database=db_name,
                            user=db_user,
                            password=db_pass,
                            connect_timeout=5
                        )
                        conn.close()

                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds() * 1000

                    success_count += 1
                    total_time += response_time

                except Exception as e:
                    logger.warning(f"Database connection {config_name} failed: {str(e)}")

            avg_response_time = total_time / max(success_count, 1)

            if success_count == 0:
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.UNHEALTHY,
                    message="All database connections failed",
                    details={"available_configs": len(db_configs)}
                )
            elif success_count < len(db_configs):
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.DEGRADED,
                    message=f"Some database connections failed ({success_count}/{len(db_configs)} working)",
                    details={"working_connections": success_count, "avg_response_time_ms": avg_response_time}
                )
            else:
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.HEALTHY,
                    message=f"Database connections healthy ({success_count} working)",
                    details={"avg_response_time_ms": avg_response_time},
                    response_time_ms=avg_response_time
                )

        except ImportError:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message="Database drivers not available"
            )
        except Exception as e:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}"
            )

    def check_redis_connection(self) -> HealthCheckResult:
        """Check Redis connectivity"""
        try:
            import redis

            start_time = datetime.utcnow()

            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD')

            # Test connection
            if redis_password:
                r = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                r = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )

            # Test basic operations
            r.ping()
            r.set('health_check_test', 'ok', ex=10)
            test_value = r.get('health_check_test')
            r.delete('health_check_test')

            assert test_value == b'ok'

            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000

            # Get Redis info
            info = r.info()

            return HealthCheckResult(
                component="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection and operations healthy",
                details={
                    "response_time_ms": response_time,
                    "connected_clients": info.get('connected_clients', 0),
                    "used_memory_mb": round(info.get('used_memory', 0) / (1024*1024), 2),
                    "uptime_days": info.get('uptime_in_days', 0)
                },
                response_time_ms=response_time
            )

        except ImportError:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                message="Redis driver not available"
            )
        except Exception as e:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}"
            )

    def check_emag_api_connectivity(self) -> HealthCheckResult:
        """Check eMAG API connectivity"""
        try:
            import aiohttp

            async def test_api():
                emag_base_url = os.getenv('EMAG_API_BASE_URL', 'https://marketplace-api.emag.ro/api-3')
                timeout = int(os.getenv('EMAG_REQUEST_TIMEOUT', '30'))

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                    # Simple connectivity test (not a full API call)
                    try:
                        async with session.get(emag_base_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            # Just check if we get a response (even if it's an error)
                            status = response.status
                            return status >= 200 and status < 500  # Any HTTP response is considered "reachable"
                    except Exception:
                        # If we can't even reach the endpoint
                        return False

            start_time = datetime.utcnow()
            api_reachable = asyncio.run(test_api())
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000

            if api_reachable:
                return HealthCheckResult(
                    component="emag_api",
                    status=HealthStatus.HEALTHY,
                    message="eMAG API is reachable",
                    details={"response_time_ms": response_time},
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="emag_api",
                    status=HealthStatus.UNHEALTHY,
                    message="eMAG API is not reachable",
                    details={"response_time_ms": response_time},
                    response_time_ms=response_time
                )

        except ImportError:
            return HealthCheckResult(
                component="emag_api",
                status=HealthStatus.UNHEALTHY,
                message="HTTP client not available"
            )
        except Exception as e:
            return HealthCheckResult(
                component="emag_api",
                status=HealthStatus.UNHEALTHY,
                message=f"eMAG API health check failed: {str(e)}"
            )

    def check_sync_processes(self) -> HealthCheckResult:
        """Check eMAG sync process health"""
        try:
            # Check if sync processes are running
            sync_processes = []

            # Look for sync-related processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    if any(keyword in ' '.join(proc.info['cmdline'] or []) for keyword in
                           ['sync_emag', 'sync_monitor', 'emag_sync']):
                        sync_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'status': proc.info['status'],
                            'cmdline': ' '.join(proc.info['cmdline'] or [])
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not sync_processes:
                return HealthCheckResult(
                    component="sync_processes",
                    status=HealthStatus.DEGRADED,
                    message="No eMAG sync processes running"
                )

            # Analyze process health
            healthy_processes = 0
            for proc_info in sync_processes:
                if proc_info['status'] == 'running':
                    healthy_processes += 1

            if healthy_processes == len(sync_processes):
                return HealthCheckResult(
                    component="sync_processes",
                    status=HealthStatus.HEALTHY,
                    message=f"All {len(sync_processes)} sync processes running",
                    details={"processes": len(sync_processes), "healthy": healthy_processes}
                )
            elif healthy_processes > 0:
                return HealthCheckResult(
                    component="sync_processes",
                    status=HealthStatus.DEGRADED,
                    message=f"{healthy_processes}/{len(sync_processes)} sync processes healthy",
                    details={"processes": len(sync_processes), "healthy": healthy_processes}
                )
            else:
                return HealthCheckResult(
                    component="sync_processes",
                    status=HealthStatus.UNHEALTHY,
                    message="All sync processes unhealthy",
                    details={"processes": len(sync_processes), "healthy": healthy_processes}
                )

        except Exception as e:
            return HealthCheckResult(
                component="sync_processes",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot check sync processes: {str(e)}"
            )

    def check_disk_space(self) -> HealthCheckResult:
        """Check disk space availability"""
        try:
            # Check main disk
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)

            # Check log directories
            log_dirs = ['/var/log/magflow', '/opt/magflow/logs', 'logs']
            log_space_ok = True

            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    try:
                        log_disk = psutil.disk_usage(log_dir)
                        if log_disk.percent > 95:
                            log_space_ok = False
                            break
                    except Exception:
                        continue

            if disk_percent > 95:
                return HealthCheckResult(
                    component="disk_space",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Critical disk space: {disk_percent:.1f}% used",
                    details={"disk_percent": disk_percent, "free_gb": round(disk_free_gb, 2)}
                )
            elif disk_percent > 80:
                return HealthCheckResult(
                    component="disk_space",
                    status=HealthStatus.DEGRADED,
                    message=f"Low disk space: {disk_percent:.1f}% used",
                    details={"disk_percent": disk_percent, "free_gb": round(disk_free_gb, 2)}
                )
            elif not log_space_ok:
                return HealthCheckResult(
                    component="disk_space",
                    status=HealthStatus.DEGRADED,
                    message="Low disk space in log directories",
                    details={"disk_percent": disk_percent, "free_gb": round(disk_free_gb, 2)}
                )
            else:
                return HealthCheckResult(
                    component="disk_space",
                    status=HealthStatus.HEALTHY,
                    message=f"Disk space OK: {disk_percent:.1f}% used",
                    details={"disk_percent": disk_percent, "free_gb": round(disk_free_gb, 2)}
                )

        except Exception as e:
            return HealthCheckResult(
                component="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot check disk space: {str(e)}"
            )

    def check_environment_variables(self) -> HealthCheckResult:
        """Check critical environment variables"""
        required_vars = [
            'APP_ENV', 'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASS',
            'REDIS_HOST', 'REDIS_PORT', 'EMAG_API_USERNAME', 'EMAG_API_PASSWORD'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            return HealthCheckResult(
                component="environment",
                status=HealthStatus.UNHEALTHY,
                message=f"Missing required environment variables: {', '.join(missing_vars)}",
                details={"missing": missing_vars, "total_required": len(required_vars)}
            )
        else:
            return HealthCheckResult(
                component="environment",
                status=HealthStatus.HEALTHY,
                message="All required environment variables present",
                details={"total_required": len(required_vars)}
            )

    def generate_health_report(self) -> SystemHealthReport:
        """Generate comprehensive health report"""
        logger.info("🏥 Generating comprehensive health report...")

        components = {}

        # Run all health checks
        checks = [
            self.check_system_resources,
            self.check_database_connection,
            self.check_redis_connection,
            self.check_emag_api_connectivity,
            self.check_sync_processes,
            self.check_disk_space,
            self.check_environment_variables
        ]

        for check_func in checks:
            try:
                result = check_func()
                components[result.component] = result
                logger.debug(f"Health check {result.component}: {result.status.value}")
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                components[check_func.__name__.replace('check_', '')] = HealthCheckResult(
                    component=check_func.__name__.replace('check_', ''),
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}"
                )

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        unhealthy_count = sum(1 for r in components.values() if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in components.values() if r.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED

        # Collect metrics
        metrics = {
            "uptime_seconds": self.get_uptime(),
            "total_components": len(components),
            "healthy_components": sum(1 for r in components.values() if r.status == HealthStatus.HEALTHY),
            "degraded_components": degraded_count,
            "unhealthy_components": unhealthy_count
        }

        return SystemHealthReport(
            timestamp=datetime.utcnow(),
            overall_status=overall_status,
            uptime_seconds=self.get_uptime(),
            components=components,
            metrics=metrics
        )

def format_health_report_html(report: SystemHealthReport) -> str:
    """Format health report as HTML"""
    status_colors = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "orange",
        HealthStatus.UNHEALTHY: "red",
        HealthStatus.UNKNOWN: "gray"
    }

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MagFlow ERP - Health Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .component {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
            .healthy {{ border-left: 5px solid green; }}
            .degraded {{ border-left: 5px solid orange; }}
            .unhealthy {{ border-left: 5px solid red; }}
            .metrics {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; }}
            .status-badge {{ padding: 4px 8px; border-radius: 3px; color: white; font-weight: bold; }}
            .overall-healthy {{ background-color: green; }}
            .overall-degraded {{ background-color: orange; }}
            .overall-unhealthy {{ background-color: red; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 MagFlow ERP - System Health Report</h1>
            <p><strong>Generated:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Uptime:</strong> {report.uptime_seconds/3600:.1f} hours</p>
            <p><strong>Overall Status:</strong>
                <span class="status-badge overall-{report.overall_status.value}">
                    {report.overall_status.value.upper()}
                </span>
            </p>
        </div>

        <div class="metrics">
            <h3>📊 System Metrics</h3>
            <p><strong>Total Components:</strong> {report.metrics['total_components']}</p>
            <p><strong>Healthy Components:</strong> {report.metrics['healthy_components']}</p>
            <p><strong>Degraded Components:</strong> {report.metrics['degraded_components']}</p>
            <p><strong>Unhealthy Components:</strong> {report.metrics['unhealthy_components']}</p>
        </div>

        <h3>🔍 Component Details</h3>
    """

    for component_name, result in report.components.items():
        status_class = result.status.value
        html += f"""
        <div class="component {status_class}">
            <h4>{component_name.replace('_', ' ').title()}</h4>
            <p><strong>Status:</strong>
                <span class="status-badge overall-{result.status.value}">
                    {result.status.value.upper()}
                </span>
            </p>
            <p><strong>Message:</strong> {result.message}</p>
            <p><strong>Response Time:</strong> {result.response_time_ms:.1f}ms</p>
            <p><strong>Last Check:</strong> {result.last_check.strftime('%H:%M:%S')}</p>
        """

        if result.details:
            html += "<details><summary>📋 Details</summary><ul>"
            for key, value in result.details.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul></details>"

        html += "</div>"

    html += """
    </body>
    </html>
    """

    return html

def format_health_report_json(report: SystemHealthReport) -> str:
    """Format health report as JSON"""
    return json.dumps({
        "timestamp": report.timestamp.isoformat(),
        "overall_status": report.overall_status.value,
        "uptime_seconds": report.uptime_seconds,
        "metrics": report.metrics,
        "components": {
            name: {
                "status": result.status.value,
                "message": result.message,
                "details": result.details,
                "response_time_ms": result.response_time_ms,
                "last_check": result.last_check.isoformat()
            }
            for name, result in report.components.items()
        }
    }, indent=2)

# Global health checker instance
_health_checker = None

def get_health_checker() -> HealthChecker:
    """Get or create health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

# Export functions for easy usage
__all__ = [
    'HealthChecker',
    'SystemHealthReport',
    'HealthCheckResult',
    'HealthStatus',
    'get_health_checker',
    'format_health_report_html',
    'format_health_report_json'
]

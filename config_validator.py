#!/usr/bin/env python3
"""
MagFlow ERP Configuration Validation System
Comprehensive validation of environment variables, database connections,
API credentials, and system requirements
"""

import logging
import os
import socket
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"      # System cannot function
    WARNING = "warning"  # Not optimal but functional
    INFO = "info"        # Informational

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    level: ValidationLevel
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    passed: bool = True

@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: str
    environment: str
    results: list[ValidationResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

class ConfigurationValidator:
    """Comprehensive configuration validator for MagFlow ERP"""

    def __init__(self):
        self.report = ValidationReport(
            timestamp=datetime.utcnow().isoformat(),
            environment=os.getenv('APP_ENV', 'unknown')
        )
        self._required_env_vars = {
            'APP_ENV': str,
            'APP_NAME': str,
            'DB_HOST': str,
            'DB_PORT': str,
            'DB_NAME': str,
            'DB_USER': str,
            'DB_PASS': str,
            'REDIS_HOST': str,
            'REDIS_PORT': str,
            'EMAG_API_USERNAME': str,
            'EMAG_API_PASSWORD': str,
            'EMAG_FBE_API_USERNAME': str,
            'EMAG_FBE_API_PASSWORD': str,
            'JWT_ALGORITHM': str,
            'SECRET_KEY': str
        }
        self._optional_env_vars = {
            'APP_PORT': int,
            'APP_DEBUG': bool,
            'DB_SYNC_URL': str,
            'DATABASE_URL': str,
            'REDIS_DB': int,
            'REDIS_PASSWORD': str,
            'EMAG_API_BASE_URL': str,
            'EMAG_ACCOUNT_TYPE': str,
            'EMAG_RATE_LIMIT_ORDERS': int,
            'EMAG_RATE_LIMIT_OFFERS': int,
            'EMAG_REQUEST_TIMEOUT': int,
            'EMAG_SYNC_METRICS_PORT': int,
            'EMAG_SYNC_MAX_PAGES': int,
            'EMAG_SYNC_TIMEOUT_HOURS': int,
            'GRAFANA_ADMIN_PASSWORD': str
        }

    def add_result(self, check_name: str, level: ValidationLevel, message: str,
                   details: dict[str, Any] = None, passed: bool = True):
        """Add a validation result"""
        result = ValidationResult(
            check_name=check_name,
            level=level,
            message=message,
            details=details or {},
            passed=passed
        )
        self.report.results.append(result)

        # Update summary
        level_key = level.value
        if level_key not in self.report.summary:
            self.report.summary[level_key] = 0
        self.report.summary[level_key] += 1

        # Log the result
        log_method = getattr(logger, level.value)
        log_method(f"[{check_name}] {message}")

        return result

    def validate_environment_variables(self):
        """Validate environment variables"""
        logger.info("🔍 Validating environment variables...")

        # Check required variables
        for var_name, expected_type in self._required_env_vars.items():
            value = os.getenv(var_name)

            if value is None or value.strip() == '':
                self.add_result(
                    f"env_var_{var_name}",
                    ValidationLevel.ERROR,
                    f"Required environment variable '{var_name}' is not set",
                    passed=False
                )
                continue

            # Validate type
            try:
                if expected_type == int:
                    int(value)
                elif expected_type == bool:
                    if value.lower() not in ['true', 'false', '1', '0']:
                        raise ValueError
                elif expected_type == str:
                    if not value.strip():
                        raise ValueError("Empty string")
            except (ValueError, TypeError):
                self.add_result(
                    f"env_var_{var_name}",
                    ValidationLevel.ERROR,
                    f"Environment variable '{var_name}' has invalid format: expected {expected_type.__name__}",
                    details={'value': value},
                    passed=False
                )
                continue

            self.add_result(
                f"env_var_{var_name}",
                ValidationLevel.INFO,
                f"Environment variable '{var_name}' is properly configured",
                details={'type': expected_type.__name__}
            )

        # Check optional variables
        for var_name, expected_type in self._optional_env_vars.items():
            value = os.getenv(var_name)

            if value is None or value.strip() == '':
                self.add_result(
                    f"env_var_{var_name}",
                    ValidationLevel.WARNING,
                    f"Optional environment variable '{var_name}' is not set (using defaults)",
                    details={'default': self._get_default_value(var_name)}
                )
                continue

            # Validate type
            try:
                if expected_type == int:
                    int(value)
                elif expected_type == bool:
                    if value.lower() not in ['true', 'false', '1', '0']:
                        raise ValueError
                elif expected_type == str:
                    if not value.strip():
                        raise ValueError("Empty string")
            except (ValueError, TypeError):
                self.add_result(
                    f"env_var_{var_name}",
                    ValidationLevel.WARNING,
                    f"Optional environment variable '{var_name}' has invalid format: expected {expected_type.__name__}",
                    details={'value': value, 'default': self._get_default_value(var_name)},
                    passed=False
                )
                continue

            self.add_result(
                f"env_var_{var_name}",
                ValidationLevel.INFO,
                f"Optional environment variable '{var_name}' is properly configured",
                details={'type': expected_type.__name__}
            )

    def _get_default_value(self, var_name: str) -> Any:
        """Get default value for optional environment variable"""
        defaults = {
            'APP_PORT': 8000,
            'APP_DEBUG': False,
            'EMAG_API_BASE_URL': 'https://marketplace-api.emag.ro/api-3',
            'EMAG_ACCOUNT_TYPE': 'main',
            'EMAG_RATE_LIMIT_ORDERS': 12,
            'EMAG_RATE_LIMIT_OFFERS': 3,
            'EMAG_REQUEST_TIMEOUT': 30,
            'EMAG_SYNC_METRICS_PORT': 9108,
            'EMAG_SYNC_MAX_PAGES': 100,
            'EMAG_SYNC_TIMEOUT_HOURS': 2
        }
        return defaults.get(var_name)

    def validate_database_connection(self):
        """Validate database connectivity"""
        logger.info("🔍 Validating database connection...")

        try:
            import psycopg2
            from sqlalchemy import create_engine

            # Try multiple connection methods
            connection_successful = False

            # Method 1: Direct database connection
            db_url = os.getenv('DATABASE_URL') or os.getenv('DB_SYNC_URL')
            if db_url:
                try:
                    engine = create_engine(db_url)
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT 1"))
                        result.fetchone()

                    self.add_result(
                        "database_direct",
                        ValidationLevel.INFO,
                        "Direct database connection successful",
                        details={'url': db_url.replace(os.getenv('DB_PASS', ''), '***') if 'DB_PASS' in os.environ else 'No password'}
                    )
                    connection_successful = True
                except Exception as e:
                    self.add_result(
                        "database_direct",
                        ValidationLevel.ERROR,
                        f"Direct database connection failed: {str(e)}",
                        passed=False
                    )

            # Method 2: Individual connection parameters
            if not connection_successful:
                db_host = os.getenv('DB_HOST')
                db_port = os.getenv('DB_PORT', '5432')
                db_name = os.getenv('DB_NAME')
                db_user = os.getenv('DB_USER')
                db_pass = os.getenv('DB_PASS')

                if all([db_host, db_port, db_name, db_user, db_pass]):
                    try:
                        conn = psycopg2.connect(
                            host=db_host,
                            port=int(db_port),
                            database=db_name,
                            user=db_user,
                            password=db_pass,
                            connect_timeout=10
                        )
                        conn.close()

                        self.add_result(
                            "database_params",
                            ValidationLevel.INFO,
                            "Database connection via parameters successful",
                            details={'host': db_host, 'port': db_port, 'database': db_name}
                        )
                        connection_successful = True
                    except Exception as e:
                        self.add_result(
                            "database_params",
                            ValidationLevel.ERROR,
                            f"Database connection via parameters failed: {str(e)}",
                            passed=False
                        )

            # Check if we can connect at all
            if not connection_successful:
                # Try to check if PostgreSQL service is available
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    db_port = int(os.getenv('DB_PORT', '5432'))
                    result = sock.connect_ex((os.getenv('DB_HOST', 'localhost'), db_port))
                    sock.close()

                    if result == 0:
                        self.add_result(
                            "database_service",
                            ValidationLevel.WARNING,
                            "Database service is reachable but authentication failed",
                            details={'host': os.getenv('DB_HOST', 'localhost'), 'port': db_port}
                        )
                    else:
                        self.add_result(
                            "database_service",
                            ValidationLevel.ERROR,
                            "Database service is not reachable",
                            details={'host': os.getenv('DB_HOST', 'localhost'), 'port': db_port},
                            passed=False
                        )
                except Exception as e:
                    self.add_result(
                        "database_service",
                        ValidationLevel.ERROR,
                        f"Cannot check database service: {str(e)}",
                        passed=False
                    )

            if connection_successful:
                self.add_result(
                    "database_overall",
                    ValidationLevel.INFO,
                    "Database connectivity validated successfully"
                )

        except ImportError:
            self.add_result(
                "database_dependencies",
                ValidationLevel.WARNING,
                "Database validation skipped - psycopg2 or sqlalchemy not available"
            )

    def validate_redis_connection(self):
        """Validate Redis connectivity"""
        logger.info("🔍 Validating Redis connection...")

        try:
            import redis

            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD')

            try:
                # Try connection with password if available
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

                # Test connection
                r.ping()

                self.add_result(
                    "redis_connection",
                    ValidationLevel.INFO,
                    "Redis connection successful",
                    details={'host': redis_host, 'port': redis_port, 'db': redis_db}
                )

            except Exception as e:
                self.add_result(
                    "redis_connection",
                    ValidationLevel.ERROR,
                    f"Redis connection failed: {str(e)}",
                    passed=False
                )

        except ImportError:
            self.add_result(
                "redis_dependencies",
                ValidationLevel.WARNING,
                "Redis validation skipped - redis-py not available"
            )

    def validate_emag_credentials(self):
        """Validate eMAG API credentials"""
        logger.info("🔍 Validating eMAG credentials...")

        try:
            import aiohttp

            # Test MAIN account credentials
            main_username = os.getenv('EMAG_API_USERNAME')
            main_password = os.getenv('EMAG_API_PASSWORD')

            if main_username and main_password:
                self.add_result(
                    "emag_main_creds",
                    ValidationLevel.INFO,
                    "eMAG MAIN account credentials configured"
                )
            else:
                self.add_result(
                    "emag_main_creds",
                    ValidationLevel.ERROR,
                    "eMAG MAIN account credentials missing",
                    passed=False
                )

            # Test FBE account credentials
            fbe_username = os.getenv('EMAG_FBE_API_USERNAME')
            fbe_password = os.getenv('EMAG_FBE_API_PASSWORD')

            if fbe_username and fbe_password:
                self.add_result(
                    "emag_fbe_creds",
                    ValidationLevel.INFO,
                    "eMAG FBE account credentials configured"
                )
            else:
                self.add_result(
                    "emag_fbe_creds",
                    ValidationLevel.WARNING,
                    "eMAG FBE account credentials missing (some features may not work)"
                )

        except ImportError:
            self.add_result(
                "emag_dependencies",
                ValidationLevel.WARNING,
                "eMAG validation skipped - aiohttp not available"
            )

    def validate_file_permissions(self):
        """Validate file system permissions"""
        logger.info("🔍 Validating file permissions...")

        # Check log directory
        log_paths = ['logs', '/var/log/magflow', '/opt/magflow/logs']
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    # Test write permissions
                    test_file = os.path.join(log_path, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)

                    self.add_result(
                        f"file_permissions_{log_path.replace('/', '_')}",
                        ValidationLevel.INFO,
                        f"Write permissions OK for {log_path}"
                    )
                    break
                except Exception as e:
                    self.add_result(
                        f"file_permissions_{log_path.replace('/', '_')}",
                        ValidationLevel.WARNING,
                        f"Cannot write to {log_path}: {str(e)}"
                    )

    def validate_network_connectivity(self):
        """Validate network connectivity to external services"""
        logger.info("🔍 Validating network connectivity...")

        # Test eMAG API connectivity
        emag_base_url = os.getenv('EMAG_API_BASE_URL', 'https://marketplace-api.emag.ro/api-3')

        try:
            parsed = urlparse(emag_base_url)
            hostname = parsed.hostname

            if hostname:
                # Simple connectivity test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Try HTTPS port (443)
                    result = sock.connect_ex((hostname, 443))
                    sock.close()

                    if result == 0:
                        self.add_result(
                            "network_emag_api",
                            ValidationLevel.INFO,
                            f"eMAG API endpoint reachable: {hostname}"
                        )
                    else:
                        self.add_result(
                            "network_emag_api",
                            ValidationLevel.WARNING,
                            f"eMAG API endpoint not reachable: {hostname}"
                        )
                except Exception as e:
                    self.add_result(
                        "network_emag_api",
                        ValidationLevel.WARNING,
                        f"Cannot test eMAG API connectivity: {str(e)}"
                    )

        except Exception as e:
            self.add_result(
                "network_emag_api",
                ValidationLevel.ERROR,
                f"Invalid eMAG API URL format: {str(e)}",
                passed=False
            )

    def validate_docker_environment(self):
        """Validate Docker environment setup"""
        logger.info("🔍 Validating Docker environment...")

        try:
            # Check if we're running in Docker
            with open('/proc/1/cgroup') as f:
                if 'docker' in f.read().lower():
                    self.add_result(
                        "docker_environment",
                        ValidationLevel.INFO,
                        "Running in Docker environment"
                    )
                else:
                    self.add_result(
                        "docker_environment",
                        ValidationLevel.WARNING,
                        "Not running in Docker environment (may be running locally)"
                    )
        except Exception:
            self.add_result(
                "docker_environment",
                ValidationLevel.WARNING,
                "Cannot determine Docker environment status"
            )

    def validate_ssl_certificates(self):
        """Validate SSL/TLS configuration"""
        logger.info("🔍 Validating SSL certificates...")

        # Check for SSL certificates
        cert_paths = [
            '/etc/ssl/certs',
            '/opt/magflow/certs',
            '/opt/magflow/ssl'
        ]

        cert_found = False
        for cert_path in cert_paths:
            if os.path.exists(cert_path):
                cert_files = [f for f in os.listdir(cert_path) if f.endswith(('.pem', '.crt', '.key'))]
                if cert_files:
                    self.add_result(
                        f"ssl_certificates_{cert_path}",
                        ValidationLevel.INFO,
                        f"SSL certificates found in {cert_path}: {', '.join(cert_files[:3])}"
                    )
                    cert_found = True
                    break

        if not cert_found:
            self.add_result(
                "ssl_certificates",
                ValidationLevel.WARNING,
                "No SSL certificates found (HTTPS may not work properly)"
            )

    def generate_report(self) -> ValidationReport:
        """Generate complete validation report"""
        logger.info("🚀 Starting comprehensive configuration validation...")

        # Run all validation checks
        self.validate_environment_variables()
        self.validate_database_connection()
        self.validate_redis_connection()
        self.validate_emag_credentials()
        self.validate_file_permissions()
        self.validate_network_connectivity()
        self.validate_docker_environment()
        self.validate_ssl_certificates()

        logger.info("✅ Configuration validation completed")
        return self.report

def print_validation_report(report: ValidationReport):
    """Print formatted validation report"""
    print("\n" + "="*80)
    print("🔍 MAGFLOW ERP - CONFIGURATION VALIDATION REPORT")
    print("="*80)
    print(f"Environment: {report.environment}")
    print(f"Timestamp: {report.timestamp}")
    print()

    # Summary
    print("📊 SUMMARY:")
    for level, count in report.summary.items():
        if level == 'error':
            print(f"  ❌ Errors: {count}")
        elif level == 'warning':
            print(f"  ⚠️  Warnings: {count}")
        elif level == 'info':
            print(f"  ℹ️  Info: {count}")

    print()

    # Detailed results
    for result in report.results:
        if result.level == ValidationLevel.ERROR:
            print(f"❌ [{result.check_name}] {result.message}")
        elif result.level == ValidationLevel.WARNING:
            print(f"⚠️  [{result.check_name}] {result.message}")
        else:
            print(f"ℹ️  [{result.check_name}] {result.message}")

        if result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")

        print()

def main():
    """Main validation function"""
    try:
        validator = ConfigurationValidator()
        report = validator.generate_report()
        print_validation_report(report)

        # Exit with error code if there are errors
        error_count = report.summary.get('error', 0)
        if error_count > 0:
            logger.error(f"Configuration validation failed with {error_count} errors")
            sys.exit(1)
        else:
            logger.info("Configuration validation passed successfully")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

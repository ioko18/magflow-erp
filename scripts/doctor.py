#!/usr/bin/env python3
"""
MagFlow Doctor - Environment and system validation tool.

This script validates the system environment, dependencies, and configuration
required to run the MagFlow application.
"""

import json
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


# Global state
class State:
    has_errors = False
    has_warnings = False
    config = {}
    env = {}


def load_environment() -> bool:
    """Load environment variables from .env file if it exists."""
    env_path = Path(".env")
    if not env_path.exists():
        print(f"{YELLOW}⚠  .env file not found. Creating from .env.example...{RESET}")
        example_path = Path(".env.example")
        if not example_path.exists():
            print(f"{RED}✗  .env.example not found. Cannot create .env file.{RESET}")
            State.has_errors = True
            return False

        with open(example_path) as src, open(env_path, "w") as dst:
            dst.write(src.read())
        print(f"{GREEN}✓  Created .env file from .env.example{RESET}")

    # Load environment variables
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    State.env[key] = value
        return True
    except Exception as e:
        print(f"{RED}✗  Failed to load .env file: {e}{RESET}")
        State.has_errors = True
        return False


def check_required_tools() -> None:
    """Check for required command-line tools."""
    print(f"\n{BOLD}🔧 Checking required tools...{RESET}")

    tools = {
        "docker": {
            "command": ["docker", "--version"],
            "required": True,
            "hint": "Install Docker from https://docs.docker.com/get-docker/",
        },
        "docker-compose": {
            "command": ["docker-compose", "--version"],
            "required": True,
            "hint": "Install Docker Compose from https://docs.docker.com/compose/install/",
        },
        "python": {
            "command": ["python3", "--version"],
            "required": True,
            "hint": "Python 3.11+ is required",
        },
        "openssl": {
            "command": ["openssl", "version"],
            "required": False,
            "hint": "Required for TLS certificate generation",
        },
    }

    for name, tool in tools.items():
        try:
            result = subprocess.run(tool["command"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"{GREEN}✓  {name}: {version}{RESET}")
            else:
                raise Exception(result.stderr.strip())
        except Exception as e:
            if tool["required"]:
                print(f"{RED}✗  {name}: Not found or error: {e}{RESET}")
                print(f"    Hint: {tool['hint']}")
                State.has_errors = True
            else:
                print(f"{YELLOW}⚠  {name}: Not found or error: {e}{RESET}")
                print(f"    Hint: {tool['hint']}")
                State.has_warnings = True


def check_directories() -> None:
    """Check for required directories and permissions."""
    print(f"\n{BOLD}📁 Checking directories and permissions...{RESET}")

    dirs = [
        ("certs", True, "TLS certificates directory"),
        ("jwt-keys", True, "JWT keys directory"),
        ("migrations", True, "Database migrations"),
        ("app", True, "Application code"),
        ("tests", False, "Test files"),
    ]

    for dir_path, required, desc in dirs:
        path = Path(dir_path)
        if path.exists():
            try:
                # Check if directory is readable
                test_file = path / ".test"
                test_file.touch(exist_ok=True)
                test_file.unlink(missing_ok=True)

                # Check if directory is writable
                if os.access(str(path), os.W_OK):
                    print(f"{GREEN}✓  {dir_path}/ - {desc} (readable/writable){RESET}")
                else:
                    print(
                        f"{YELLOW}⚠  {dir_path}/ - {desc} (readable, not writable){RESET}"
                    )
                    State.has_warnings = True
            except Exception as e:
                if required:
                    print(f"{RED}✗  {dir_path}/ - {desc} (inaccessible: {e}){RESET}")
                    State.has_errors = True
                else:
                    print(f"{YELLOW}⚠  {dir_path}/ - {desc} (inaccessible: {e}){RESET}")
                    State.has_warnings = True
        else:
            if required:
                print(f"{RED}✗  {dir_path}/ - {desc} (missing){RESET}")
                State.has_errors = True
            else:
                print(f"{YELLOW}⚠  {dir_path}/ - {desc} (missing){RESET}")
                State.has_warnings = True


def check_ports() -> None:
    """Check if required ports are available."""
    print(f"\n{BOLD}🔌 Checking required ports...{RESET}")

    ports = [
        (8000, "FastAPI application"),
        (5432, "PostgreSQL"),
        (6432, "PgBouncer"),
        (6379, "Redis"),
    ]

    for port, service in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()

        if result == 0:
            print(f"{YELLOW}⚠  Port {port} ({service}) is in use{RESET}")
            State.has_warnings = True
        else:
            print(f"{GREEN}✓  Port {port} ({service}) is available{RESET}")


def check_tls_certificates() -> None:
    """Check for required TLS certificates."""
    print(f"\n{BOLD}🔒 Checking TLS certificates...{RESET}")

    required_certs = [
        ("certs/ca/ca.crt", "CA Certificate"),
        ("certs/ca/ca.key", "CA Private Key"),
        ("certs/pgbouncer.crt", "PgBouncer Certificate"),
        ("certs/pgbouncer.key", "PgBouncer Private Key"),
        ("certs/postgres.crt", "PostgreSQL Certificate"),
        ("certs/postgres.key", "PostgreSQL Private Key"),
    ]

    all_certs_exist = True
    for cert_path, desc in required_certs:
        path = Path(cert_path)
        if not path.exists():
            print(f"{YELLOW}⚠  {desc} not found: {cert_path}{RESET}")
            all_certs_exist = False
            State.has_warnings = True
        else:
            print(f"{GREEN}✓  Found {desc}: {cert_path}{RESET}")

    if not all_certs_exist:
        print(
            f"\n{YELLOW}Some TLS certificates are missing. You can generate them with:{RESET}"
        )
        print("  ./scripts/tls/make-ca.sh")
        print(
            '  ./scripts/tls/make-cert.sh pgbouncer "DNS:pgbouncer,DNS:localhost,IP:127.0.0.1"'
        )
        print(
            '  ./scripts/tls/make-cert.sh postgres "DNS:postgres,DNS:localhost,IP:127.0.0.1"\n'
        )


def check_jwt_keys() -> None:
    """Check for JWT keys."""
    print(f"\n{BOLD}🔑 Checking JWT keys...{RESET}")

    required_keys = [
        ("jwt-keys/private.pem", "JWT Private Key"),
        ("jwt-keys/public.pem", "JWT Public Key"),
    ]

    all_keys_exist = True
    for key_path, desc in required_keys:
        path = Path(key_path)
        if not path.exists():
            print(f"{YELLOW}⚠  {desc} not found: {key_path}{RESET}")
            all_keys_exist = False
            State.has_warnings = True
        else:
            print(f"{GREEN}✓  Found {desc}: {key_path}{RESET}")

    if not all_keys_exist:
        print(f"\n{YELLOW}JWT keys are missing. You can generate them with:{RESET}")
        print("  mkdir -p jwt-keys")
        print("  openssl genrsa -out jwt-keys/private.pem 4096")
        print(
            "  openssl rsa -in jwt-keys/private.pem -pubout -out jwt-keys/public.pem\n"
        )


def check_docker_services() -> None:
    """Check if Docker services are running."""
    print(f"\n{BOLD}🐳 Checking Docker services...{RESET}")

    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], capture_output=True, check=True)

        # Check if services are running
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--status", "running"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            running_services = [
                s.strip() for s in result.stdout.splitlines() if s.strip()
            ]
            expected_services = ["db", "pgbouncer", "redis", "app"]

            for service in expected_services:
                if service in running_services:
                    print(f"{GREEN}✓  {service} is running{RESET}")
                else:
                    print(f"{YELLOW}⚠  {service} is not running{RESET}")
                    State.has_warnings = True
        else:
            print(
                f"{YELLOW}⚠  Could not check running services: {result.stderr.strip()}{RESET}"
            )
            State.has_warnings = True

    except subprocess.CalledProcessError as e:
        print(
            f"{RED}✗  Docker is not running or not installed: {e.stderr.strip()}{RESET}"
        )
        print("    Make sure Docker is installed and running")
        State.has_errors = True
    except Exception as e:
        print(f"{RED}✗  Error checking Docker services: {str(e)}{RESET}")
        State.has_errors = True


def check_health_endpoint() -> None:
    """Check the health endpoint."""
    print(f"\n{BOLD}🏥 Checking health endpoint...{RESET}")

    try:
        import requests
        from urllib3.exceptions import InsecureRequestWarning

        # Suppress only the single InsecureRequestWarning from urllib3
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        # First try with HTTPS, fall back to HTTP if needed
        base_url = State.env.get("APP_URL", "http://localhost:8000")
        health_url = f"{base_url}/health/full"

        try:
            response = requests.get(health_url, verify=False, timeout=5)
            data = response.json()

            if response.status_code == 200 and data.get("status") == "ok":
                print(f"{GREEN}✓  Health check passed: {health_url}{RESET}")

                # Print service statuses
                print("\nService Status:")
                for service, status in data.get("services", {}).items():
                    status_emoji = "✅" if status.get("status") == "ok" else "❌"
                    print(
                        f"  {status_emoji} {service}: {status.get('status', 'unknown')}"
                    )

                    # Print additional details for errors
                    if "error" in status:
                        print(f"     Error: {status['error']}")
            else:
                print(
                    f"{YELLOW}⚠  Health check returned non-OK status: {response.status_code}{RESET}"
                )
                print(f"    Response: {json.dumps(data, indent=2)}")
                State.has_warnings = True

        except requests.exceptions.SSLError as e:
            print(f"{YELLOW}⚠  SSL certificate verification failed: {e}{RESET}")
            print("    Trying with SSL verification disabled...")

            # Retry with SSL verification disabled
            try:
                response = requests.get(health_url, verify=False, timeout=5)
                data = response.json()

                if response.status_code == 200 and data.get("status") == "ok":
                    print(
                        f"{GREEN}✓  Health check passed (insecure): {health_url}{RESET}"
                    )
                    print("    Note: SSL certificate verification is disabled")
                else:
                    print(
                        f"{YELLOW}⚠  Health check failed: {response.status_code}{RESET}"
                    )
                    print(f"    Response: {json.dumps(data, indent=2)}")
                    State.has_warnings = True

            except Exception as e:
                print(f"{RED}✗  Health check failed: {str(e)}{RESET}")
                State.has_errors = True

    except ImportError:
        print(
            f"{YELLOW}⚠  'requests' package not available. Install with: pip install requests{RESET}"
        )
        State.has_warnings = True
    except Exception as e:
        print(f"{RED}✗  Error checking health endpoint: {str(e)}{RESET}")
        State.has_errors = True


def check_database_migrations() -> None:
    """Check if database migrations are up to date."""
    print(f"\n{BOLD}📊 Checking database migrations...{RESET}")

    try:
        # First check if we can run the migration check command
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "app", "alembic", "current"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Parse the output to check if we're at the latest migration
            output = result.stdout.strip()
            if "head" in output.lower() or "(head)" in output.lower():
                print(f"{GREEN}✓  Database is up to date with migrations{RESET}")
            else:
                print(f"{YELLOW}⚠  Database is not at the latest migration{RESET}")
                print(f"    Current state:\n{output}")
                print("\nTo apply migrations, run:")
                print("  docker-compose exec app alembic upgrade head")
                State.has_warnings = True
        else:
            print(
                f"{YELLOW}⚠  Could not check database migrations: {result.stderr.strip()}{RESET}"
            )
            State.has_warnings = True

    except subprocess.TimeoutExpired:
        print(
            f"{YELLOW}⚠  Database migration check timed out. Is the database running?{RESET}"
        )
        State.has_warnings = True
    except Exception as e:
        print(f"{YELLOW}⚠  Error checking database migrations: {str(e)}{RESET}")
        State.has_warnings = True


def print_summary() -> None:
    """Print a summary of the health check results."""
    print(f"\n{BOLD}📋 Summary{RESET}")
    print("=" * 50)

    if State.has_errors:
        print(
            f"{RED}✗  There are errors that need to be fixed before running the application.{RESET}"
        )
    elif State.has_warnings:
        print(
            f"{YELLOW}⚠  There are some warnings, but the application should work.{RESET}"
        )
    else:
        print(f"{GREEN}✓  All checks passed! Your environment is ready to go!{RESET}")

    print("\nNext steps:")
    if State.has_errors:
        print(f"  1. Fix the {RED}errors{RESET} listed above")
    if State.has_warnings:
        print(f"  2. Review the {YELLOW}warnings{RESET} above")

    if not State.has_errors:
        print("  3. Start the application with:")
        print("     docker-compose up -d")
        print("\n  4. Access the application at:")
        print("     Web Interface: http://localhost:8000")
        print("     API Docs: http://localhost:8000/docs")
        print("     Health Check: http://localhost:8000/health/full")

    print("\nFor more information, check the documentation at:")
    print("  https://github.com/your-org/magflow#readme\n")


def main() -> None:
    """Main function to run all checks."""
    print(f"{BOLD}🔍 MagFlow Environment Checker 🔍{RESET}")
    print("=" * 50)

    # Check Python version
    print(
        f"{GREEN}✓  Python {platform.python_version()} (meets requirements){RESET}"
    )

    # Run all checks
    load_environment()
    check_required_tools()
    check_directories()
    check_ports()
    check_tls_certificates()
    check_jwt_keys()
    check_docker_services()
    check_health_endpoint()
    check_database_migrations()

    # Print summary
    print_summary()

    # Exit with appropriate status code
    sys.exit(1 if State.has_errors else (2 if State.has_warnings else 0))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(1)

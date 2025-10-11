"""
eMAG Request Logger - v4.4.9

Logs all eMAG API requests and responses for 30 days retention.
Per eMAG API documentation: Always log all requests and responses for at least 30 days.
"""

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs/emag")
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class EmagRequestLogger:
    """
    Logs all eMAG API requests and responses for 30 days.

    Per eMAG API v4.4.9 documentation:
    - Always log all requests and responses
    - Minimum retention: 30 days
    - Include full request and response data
    - Track timing and errors
    """

    def __init__(self, log_file: str = "logs/emag/api_requests.log"):
        """
        Initialize the request logger.

        Args:
            log_file: Path to log file
        """
        self.logger = logging.getLogger("emag_api_requests")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers = []

        # Create rotating file handler
        # 100MB per file, 30 files = ~3GB total for 30 days
        handler = RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=30,  # 30 files for ~30 days
            encoding="utf-8",
        )

        # JSON formatter for structured logging
        formatter = logging.Formatter(
            "%(message)s"  # We'll format as JSON ourselves
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

        # Also log to console for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - eMAG API - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(console_handler)

    def log_request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        account_type: str = "unknown",
    ) -> str:
        """
        Log API request.

        Args:
            method: HTTP method
            url: Request URL
            payload: Request payload
            headers: Request headers (sensitive data will be masked)
            account_type: Account type (main/fbe)

        Returns:
            Request ID for correlation
        """
        request_id = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

        # Mask sensitive data in headers
        safe_headers = self._mask_sensitive_data(headers) if headers else {}

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "type": "request",
            "method": method,
            "url": url,
            "account_type": account_type,
            "payload": payload,
            "headers": safe_headers,
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
        return request_id

    def log_response(
        self,
        request_id: str,
        status_code: int,
        response: dict[str, Any],
        duration_ms: float,
        url: str,
        account_type: str = "unknown",
    ):
        """
        Log API response.

        Args:
            request_id: Request ID for correlation
            status_code: HTTP status code
            response: Response data
            duration_ms: Request duration in milliseconds
            url: Request URL
            account_type: Account type (main/fbe)
        """
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "type": "response",
            "status_code": status_code,
            "duration_ms": duration_ms,
            "url": url,
            "account_type": account_type,
            "has_isError": "isError" in response,
            "isError": response.get("isError"),
            "response": response,
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_error(
        self, request_id: str, error: Exception, url: str, account_type: str = "unknown"
    ):
        """
        Log API error.

        Args:
            request_id: Request ID for correlation
            error: Exception that occurred
            url: Request URL
            account_type: Account type (main/fbe)
        """
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "type": "error",
            "url": url,
            "account_type": account_type,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        self.logger.error(json.dumps(log_entry, ensure_ascii=False))

    def _mask_sensitive_data(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Mask sensitive data in headers.

        Args:
            headers: Original headers

        Returns:
            Headers with masked sensitive data
        """
        masked = headers.copy()

        sensitive_keys = ["authorization", "auth", "password", "token", "api-key"]

        for key in masked:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                # Keep first 10 chars, mask the rest
                value = masked[key]
                if len(value) > 10:
                    masked[key] = value[:10] + "***MASKED***"
                else:
                    masked[key] = "***MASKED***"

        return masked


# Global logger instance
_request_logger = EmagRequestLogger()


def get_request_logger() -> EmagRequestLogger:
    """Get global request logger instance."""
    return _request_logger


def log_emag_request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    account_type: str = "unknown",
) -> str:
    """
    Convenience function to log eMAG request.

    Args:
        method: HTTP method
        url: Request URL
        payload: Request payload
        headers: Request headers
        account_type: Account type

    Returns:
        Request ID
    """
    return _request_logger.log_request(method, url, payload, headers, account_type)


def log_emag_response(
    request_id: str,
    status_code: int,
    response: dict[str, Any],
    duration_ms: float,
    url: str,
    account_type: str = "unknown",
):
    """
    Convenience function to log eMAG response.

    Args:
        request_id: Request ID
        status_code: HTTP status code
        response: Response data
        duration_ms: Duration in milliseconds
        url: Request URL
        account_type: Account type
    """
    _request_logger.log_response(
        request_id, status_code, response, duration_ms, url, account_type
    )


def log_emag_error(
    request_id: str, error: Exception, url: str, account_type: str = "unknown"
):
    """
    Convenience function to log eMAG error.

    Args:
        request_id: Request ID
        error: Exception
        url: Request URL
        account_type: Account type
    """
    _request_logger.log_error(request_id, error, url, account_type)

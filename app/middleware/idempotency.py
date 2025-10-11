import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle idempotency keys for API requests.

    Supports the Idempotency-Key header to prevent duplicate requests.
    Returns 409 Conflict if the same key is used with different request payload.
    """

    def __init__(self, app, ttl_hours: int = 24, redis_client=None):
        super().__init__(app)
        self.ttl_hours = ttl_hours
        self.redis_client = redis_client
        # In tests, use an in-memory store to avoid DB requirements
        self._memory_store: dict[str, dict[str, Any]] = {}

    async def _get_db_connection(self):
        """Get async database connection."""
        return await asyncpg.connect(
            host=os.getenv("DB_HOST", "pgbouncer"),
            port=int(os.getenv("DB_PORT", "6432")),
            user=os.getenv("DB_USER", "app"),
            password=os.getenv("DB_PASS", "app_password_change_me"),
            database=os.getenv("DB_NAME", "magflow"),
            timeout=10,
            command_timeout=10,
        )

    def _compute_request_hash(self, method: str, path: str, body: bytes) -> str:
        """Compute SHA-256 hash of request method, path, and body."""
        content = f"{method}:{path}:{body.decode('utf-8', errors='ignore')}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _validate_key(self, key: str) -> tuple[bool, str]:
        """Validate idempotency key format.

        Args:
            key: The idempotency key to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not key:
            return False, "Idempotency key cannot be empty"

        if not (1 <= len(key) <= 80):
            return False, "Idempotency key must be between 1 and 80 characters"

        if any(ord(c) < 0x20 or ord(c) > 0x7E for c in key):
            return (
                False,
                "Idempotency key contains invalid characters. Only printable ASCII characters are allowed",
            )

        return True, ""

    def _should_process_request(self, request: Request) -> bool:
        """Check if request should be processed for idempotency."""
        # Only process POST, PUT, PATCH requests
        if request.method not in ["POST", "PUT", "PATCH"]:
            return False

        # Only process if Idempotency-Key header is present
        return "idempotency-key" in request.headers

    async def _get_existing_record(
        self,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        """Check if idempotency key exists in database."""
        # In testing environment, check memory store first
        if settings.TESTING and idempotency_key in self._memory_store:
            record = self._memory_store[idempotency_key]
            # TTL check
            if record.get("ttl_at") and record["ttl_at"] > datetime.now(UTC):
                return record
            return None
        conn = None
        try:
            conn = await self._get_db_connection()
            row = await conn.fetchrow(
                """
                SELECT key, method, path, req_hash, status_code, response_body, created_at, ttl_at
                FROM app.idempotency_keys
                WHERE key = $1 AND ttl_at > now()
                """,
                idempotency_key,
            )
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching idempotency record: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    async def _store_idempotency_record(
        self,
        idempotency_key: str,
        method: str,
        path: str,
        req_hash: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> bool:
        """Store or update idempotency record in database."""
        # In testing environment, write to memory store and return
        if settings.TESTING:
            record = self._memory_store.get(
                idempotency_key,
                {
                    "key": idempotency_key,
                    "method": method,
                    "path": path,
                    "req_hash": req_hash,
                    "created_at": datetime.now(UTC),
                    "ttl_at": datetime.now(UTC) + timedelta(hours=self.ttl_hours),
                    "status_code": None,
                    "response_body": None,
                },
            )
            # Update with response data if provided
            if status_code is not None:
                record["status_code"] = status_code
                record["response_body"] = response_body
            self._memory_store[idempotency_key] = record
            return True
        try:
            conn = await self._get_db_connection()
            if status_code is None:
                # Initial insert without response data
                await conn.execute(
                    """
                    INSERT INTO app.idempotency_keys
                    (key, method, path, req_hash, ttl_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (key) DO NOTHING
                    """,
                    idempotency_key,
                    method,
                    path,
                    req_hash,
                    datetime.now(UTC) + timedelta(hours=self.ttl_hours),
                )
            else:
                # Update with response data
                await conn.execute(
                    """
                    UPDATE app.idempotency_keys
                    SET status_code = $1, response_body = $2
                    WHERE key = $3
                    """,
                    status_code,
                    response_body,
                    idempotency_key,
                )
            return True
        except Exception as e:
            logger.error(f"Error storing idempotency record: {e}")
            return False

    async def dispatch(self, request: Request, call_next):
        """Main middleware logic."""
        if not self._should_process_request(request):
            return await call_next(request)

        idempotency_key = request.headers.get("idempotency-key")
        if not idempotency_key:
            return await call_next(request)

        # Validate idempotency key format
        is_valid, error_msg = self._validate_key(idempotency_key)
        if not is_valid:
            logger.warning(f"Invalid idempotency key format: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_idempotency_key", "message": error_msg},
            )

        # Read request body
        body = await request.body()
        req_hash = self._compute_request_hash(
            request.method,
            str(request.url.path),
            body,
        )

        # Create new receive method with cached body

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive

        # Check for existing record
        try:
            existing = await self._get_existing_record(idempotency_key)
        except Exception as e:
            if "relation " in str(e) and " does not exist" in str(e):
                logger.warning(
                    "Idempotency keys table does not exist. Continuing without idempotency check.",
                )
                return await call_next(request)
            raise

        if existing:
            # Check if request hash matches
            if existing["req_hash"] != req_hash:
                logger.warning(f"Idempotency key conflict: {idempotency_key}")
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": "Conflict",
                        "message": "Idempotency key already used with different request payload",
                    },
                )

            # If we have a completed response, return it
            if existing["status_code"] is not None:
                logger.info(
                    f"Returning cached response for idempotency key: {idempotency_key}",
                )
                try:
                    response_data = (
                        json.loads(existing["response_body"])
                        if existing["response_body"]
                        else {}
                    )
                    return JSONResponse(
                        status_code=existing["status_code"],
                        content=response_data,
                    )
                except json.JSONDecodeError:
                    # If response body is not JSON, return as text
                    return Response(
                        content=existing["response_body"] or "",
                        status_code=existing["status_code"],
                        media_type="text/plain",
                    )

        # Store initial record (without response data)
        try:
            await self._store_idempotency_record(
                idempotency_key,
                request.method,
                str(request.url.path),
                req_hash,
            )
        except Exception as e:
            if "relation " in str(e) and " does not exist" in str(e):
                logger.warning(
                    "Idempotency keys table does not exist. Continuing without idempotency tracking.",
                )
                return await call_next(request)
            raise

        # Process the request
        response = await call_next(request)

        # Store response data
        if hasattr(response, "body"):
            response_body = response.body.decode("utf-8", errors="ignore")
        else:
            response_body = ""

        await self._store_idempotency_record(
            idempotency_key,
            request.method,
            str(request.url.path),
            req_hash,
            response.status_code,
            response_body,
        )

        logger.info(f"Processed request with idempotency key: {idempotency_key}")
        return response

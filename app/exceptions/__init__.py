"""Exception handling for the application.

This package provides custom exceptions and exception handlers that convert various types of
exceptions into RFC 9457 Problem Details responses.
"""
from typing import Any, Dict, Optional, Type, TypeVar, Union

from fastapi import status
from fastapi.exceptions import HTTPException

from .handlers import (
    create_problem_response,
    create_problem,
    http_exception_handler,
    validation_exception_handler,
    python_exception_handler,
    register_exception_handlers,
)

from app.schemas.errors import (
    Problem,
    ValidationProblem,
    UnauthorizedProblem,
    ForbiddenProblem,
    NotFoundProblem,
    ConflictProblem,
    TooManyRequestsProblem,
    InternalServerErrorProblem,
    ServiceUnavailableProblem,
)

__all__ = [
    # Core exception classes
    "HTTPException",
    "HTTPExceptionWithProblem",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "TooManyRequestsError",
    "InternalServerError",
    "ServiceUnavailableError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseTimeoutError",
    "DatabaseIntegrityError",
    "DatabaseQueryError",
    "ExternalServiceError",
    "RateLimitExceededError",
    "IdempotencyError",
    "InvalidTokenError",
    "ExpiredTokenError",
    "InsufficientPermissionsError",
    "ResourceLockedError",
    "VersionConflictError",
    "InvalidStateError",
    "NotImplementedError",
    "ConfigurationError",
    "MaintenanceError",
    
    # Handler functions
    "create_problem_response",
    "create_problem",
    "http_exception_handler",
    "validation_exception_handler",
    "python_exception_handler",
    "register_exception_handlers",
]


class HTTPExceptionWithProblem(HTTPException):
    """Base exception class for HTTP exceptions with problem details.
    
    This extends FastAPI's HTTPException to support RFC 9457 Problem Details.
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    problem_type: Type[Problem] = Problem


class TooManyRequestsError(HTTPExceptionWithProblem):
    """Raised when a client has sent too many requests in a given amount of time."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    problem_type = TooManyRequestsProblem
    
    def __init__(
        self, 
        detail: str = "Too many requests",
        retry_after: Optional[int] = None,
        **extra: Any
    ) -> None:
        """Initialize the too many requests error.
        
        Args:
            detail: A human-readable explanation of the error
            retry_after: Number of seconds to wait before retrying
            **extra: Additional fields to include in the problem details
        """
        if retry_after is not None:
            extra['retry_after'] = retry_after
            if 'headers' not in extra:
                extra['headers'] = {'Retry-After': str(retry_after)}
        super().__init__(detail=detail, **extra)


class ValidationError(HTTPExceptionWithProblem):
    """Raised when request validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    problem_type = ValidationProblem
    
    class RateLimitExceededError(TooManyRequestsError):
        """Raised when a rate limit is exceeded.
        
        This exception indicates that the client has made too many requests
        in a given time period and should wait before making new requests.
        
        Attributes:
            detail: Human-readable error message
            limit: The maximum number of requests allowed
            period: The time period in seconds for the limit
            remaining: Number of requests remaining in the current period
            reset_time: When the rate limit will reset (ISO 8601 format)
            scope: The scope of the rate limit (e.g., 'ip', 'user', 'global')
        
        Example:
            ```python
            async def check_rate_limit(user_id: str, scope: str = "user"):
                # Use a sliding window counter in Redis
                key = f"rate_limit:{scope}:{user_id}"
                current = await redis.incr(key)
                
                if current == 1:
                    # Set expiration on first request
                    await redis.expire(key, RATE_LIMIT_WINDOW)
                
                # Check if limit exceeded
                if current > RATE_LIMIT_MAX_REQUESTS:
                    ttl = await redis.ttl(key)
                    raise RateLimitExceededError(
                        f"Rate limit exceeded: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds",
                        limit=RATE_LIMIT_MAX_REQUESTS,
                        period=RATE_LIMIT_WINDOW,
                        remaining=0,
                        reset_time=(datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
                        scope=scope
                    )
                    
                return RATE_LIMIT_MAX_REQUESTS - current
            ```
        """
        def __init__(
            self, 
            detail: str = "Rate limit exceeded",
            limit: Optional[int] = None,
            period: Optional[int] = None,
            remaining: Optional[int] = None,
            reset_time: Optional[str] = None,
            scope: Optional[str] = None,
            **extra: Any
        ) -> None:
            """Initialize the rate limit exceeded error.
            
            Args:
                detail: A human-readable explanation of the error
                limit: The maximum number of requests allowed
                period: The time period in seconds for the limit
                remaining: Number of requests remaining in the current period
                reset_time: When the rate limit will reset (ISO 8601 format)
                scope: The scope of the rate limit (e.g., 'ip', 'user', 'global')
                **extra: Additional fields to include in the problem details
            """
            rate_limit = {}
            
            if limit is not None and period is not None:
                rate_limit['limit'] = f"{limit} requests per {period} seconds"
            if remaining is not None:
                rate_limit['remaining'] = remaining
            if reset_time is not None:
                rate_limit['reset'] = reset_time
            if scope is not None:
                rate_limit['scope'] = scope
                
            if rate_limit:
                extra['rate_limit'] = rate_limit
                
            # Add Retry-After header if we have a reset time
            if reset_time and 'headers' not in extra:
                try:
                    from datetime import datetime, timezone
                    reset_dt = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    retry_after = int((reset_dt - now).total_seconds())
                    if retry_after > 0:
                        extra['headers'] = {'Retry-After': str(retry_after)}
                except (ValueError, TypeError):
                    pass
                    
            extra['hint'] = "Please wait before making additional requests"
            super().__init__(detail=detail, **extra)

    def __init__(
        self, 
        detail: str = "Invalid request data", 
        errors: Optional[list] = None,
        **extra: Any
    ) -> None:
        """Initialize the validation error.
        
        Args:
            detail: A human-readable explanation of the validation error
            errors: A list of validation errors
            **extra: Additional fields to include in the problem details
        """
        if errors is not None:
            extra['errors'] = errors
        super().__init__(detail=detail, **extra)


class UnauthorizedError(HTTPExceptionWithProblem):
    """Raised when authentication is required but not provided or invalid."""
    status_code = status.HTTP_401_UNAUTHORIZED
    problem_type = UnauthorizedProblem
    
    def __init__(
        self, 
        detail: str = "Authentication required",
        **extra: Any
    ) -> None:
        """Initialize the unauthorized error.
        
        Args:
            detail: A human-readable explanation of the error
            **extra: Additional fields to include in the problem details
        """
        super().__init__(detail=detail, **extra)
        self.headers["WWW-Authenticate"] = 'Bearer realm="MagFlow API"'


class ForbiddenError(HTTPExceptionWithProblem):
    """Raised when the user doesn't have permission to access a resource."""
    status_code = status.HTTP_403_FORBIDDEN
    problem_type = ForbiddenProblem
    
    def __init__(
        self, 
        detail: str = "You don't have permission to access this resource",
        **extra: Any
    ) -> None:
        """Initialize the forbidden error.
        
        Args:
            detail: A human-readable explanation of the error
            **extra: Additional fields to include in the problem details
        """
        super().__init__(detail=detail, **extra)


class NotFoundError(HTTPExceptionWithProblem):
    """Raised when a requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    problem_type = NotFoundProblem
    
    def __init__(
        self, 
        resource: Optional[str] = None,
        resource_id: Any = None,
        **extra: Any
    ) -> None:
        """Initialize the not found error.
        
        Args:
            resource: The type of resource that was not found
            resource_id: The ID of the resource that was not found
            **extra: Additional fields to include in the problem details
        """
        detail = "The requested resource was not found"
        if resource is not None:
            detail = f"{resource} not found"
            if resource_id is not None:
                detail = f"{resource} with ID {resource_id} not found"
                extra['resource_id'] = resource_id
            extra['resource'] = resource
            
        super().__init__(detail=detail, **extra)


class ConflictError(HTTPExceptionWithProblem):
    """Raised when a resource conflict occurs (e.g., duplicate entry)."""
    status_code = status.HTTP_409_CONFLICT
    problem_type = ConflictProblem
    
    def __init__(
        self, 
        detail: str = "A resource with this identifier already exists",
        **extra: Any
    ) -> None:
        """Initialize the conflict error.
        
        Args:
            detail: A human-readable explanation of the conflict
            **extra: Additional fields to include in the problem details
        """
        super().__init__(detail=detail, **extra)


class TooManyRequestsError(HTTPExceptionWithProblem):
    """Raised when a rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    problem_type = TooManyRequestsProblem
    
    def __init__(
        self, 
        retry_after: Optional[int] = None,
        **extra: Any
    ) -> None:
        """Initialize the too many requests error.
        
        Args:
            retry_after: Number of seconds after which to retry
            **extra: Additional fields to include in the problem details
        """
        detail = "Too many requests"
        if retry_after is not None:
            self.headers["Retry-After"] = str(retry_after)
            detail = f"Too many requests. Please try again in {retry_after} seconds."
            extra['retry_after'] = retry_after
            
        super().__init__(detail=detail, **extra)


class InternalServerError(HTTPExceptionWithProblem):
    """Raised when an unexpected error occurs on the server."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    problem_type = InternalServerErrorProblem
    
    def __init__(
        self, 
        detail: str = "An unexpected error occurred",
        **extra: Any
    ) -> None:
        """Initialize the internal server error.
        
        Args:
            detail: A human-readable explanation of the error
            **extra: Additional fields to include in the problem details
        """
        super().__init__(detail=detail, **extra)


class ServiceUnavailableError(HTTPExceptionWithProblem):
    """Raised when a required service is temporarily unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    problem_type = ServiceUnavailableProblem
    
    def __init__(
        self, 
        detail: str = "Service is temporarily unavailable. Please try again later.",
        retry_after: Optional[int] = None,
        **extra: Any
    ) -> None:
        """Initialize the service unavailable error.
        
        Args:
            detail: A human-readable explanation of the error
            retry_after: Number of seconds after which to retry
            **extra: Additional fields to include in the problem details
        """
        if retry_after is not None:
            self.headers["Retry-After"] = str(retry_after)
            extra['retry_after'] = retry_after
            
        super().__init__(detail=detail, **extra)


# Database exceptions
class DatabaseError(InternalServerError):
    """Base class for database-related errors.
    
    Example:
        ```python
        try:
            # Database operation
            await db.execute(query)
        except DatabaseError as e:
            logger.error(f"Database error: {e}")
            raise  # Re-raise with original traceback
        ```
    """
    def __init__(self, detail: str = "A database error occurred", **extra: Any) -> None:
        super().__init__(detail=detail, **extra)


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be established.
    
    Attributes:
        detail: Human-readable error message
        connection_string: The connection string used (without password)
        max_retries: Number of connection attempts made
        timeout: Connection timeout in seconds
    
    Example:
        ```python
        try:
            pool = await create_async_pool(DATABASE_URL)
        except DatabaseConnectionError as e:
            logger.error(f"Failed to connect to database: {e.detail}")
            raise ServiceUnavailableError("Database is currently unavailable")
        ```
    """
    def __init__(
        self, 
        detail: str = "Failed to connect to the database",
        connection_string: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
        **extra: Any
    ) -> None:
        if connection_string:
            # Sanitize connection string by removing password
            import re
            safe_conn_str = re.sub(r':[^@/]+@', ':***@', connection_string)
            extra['connection_string'] = safe_conn_str
        if max_retries is not None:
            extra['max_retries'] = max_retries
        if timeout is not None:
            extra['timeout_seconds'] = timeout
        super().__init__(detail=detail, **extra)


class DatabaseTimeoutError(DatabaseError):
    """Raised when a database operation times out.
    
    Attributes:
        detail: Human-readable error message
        operation: The type of operation that timed out (e.g., 'query', 'transaction')
        timeout: The timeout value in seconds
        query_id: Optional identifier for the query that timed out
    
    Example:
        ```python
        try:
            await db.execute("SELECT pg_sleep(10)", timeout=1.0)
        except DatabaseTimeoutError as e:
            logger.warning(f"Query {e.extra.get('query_id')} timed out after {e.extra.get('timeout_seconds')}s")
            raise HTTPException(504, "Database operation timed out")
        ```
    """
    def __init__(
        self, 
        detail: str = "Database operation timed out",
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
        query_id: Optional[str] = None,
        **extra: Any
    ) -> None:
        if operation:
            extra['operation'] = operation
        if timeout is not None:
            extra['timeout_seconds'] = timeout
        if query_id:
            extra['query_id'] = query_id
        super().__init__(detail=detail, **extra)


class DatabaseIntegrityError(DatabaseError):
    """Raised when a database integrity constraint is violated.
    
    This typically occurs for:
    - Unique constraint violations
    - Foreign key constraint violations
    - Check constraint violations
    - Not null constraint violations
    
    Attributes:
        detail: Human-readable error message
        constraint: Name of the violated constraint
        table: Name of the table where the violation occurred
        column: Column that caused the violation (if applicable)
        value: The value that caused the violation (if available)
    
    Example:
        ```python
        try:
            # Attempt to insert a duplicate user
            await db.execute(
                "INSERT INTO users (email) VALUES ($1)",
                "user@example.com"
            )
        except DatabaseIntegrityError as e:
            if e.extra.get('constraint') == 'users_email_key':
                raise ConflictError("Email already registered")
            raise
        ```
    """
    status_code = status.HTTP_409_CONFLICT
    
    def __init__(
        self, 
        detail: str = "Database integrity constraint violated",
        constraint: Optional[str] = None,
        table: Optional[str] = None,
        column: Optional[str] = None,
        value: Any = None,
        **extra: Any
    ) -> None:
        """Initialize the database integrity error.
        
        Args:
            detail: A human-readable explanation of the error
            constraint: The name of the constraint that was violated
            table: The table where the violation occurred
            column: The column that caused the violation
            value: The value that caused the violation
            **extra: Additional fields to include in the problem details
        """
        if constraint is not None:
            extra['constraint'] = constraint
        if table is not None:
            extra['table'] = table
        if column is not None:
            extra['column'] = column
        if value is not None:
            extra['value'] = value
            
        super().__init__(detail=detail, **extra)


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails.
    
    This exception captures detailed information about failed queries
    for debugging purposes while being careful not to expose sensitive
    information in production.
    
    Attributes:
        detail: Human-readable error message
        query: The query that failed (sanitized if necessary)
        params: Query parameters (sanitized)
        query_id: Optional identifier for the query
        error_code: Database-specific error code
    
    Example:
        ```python
        try:
            await db.execute(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
        except DatabaseQueryError as e:
            logger.error(f"Query failed: {e.detail}")
            if e.extra.get('error_code') == '42P01':  # Undefined table
                raise InternalServerError("Database configuration error")
            raise
        ```
    """
    def __init__(
        self, 
        detail: str = "Database query failed",
        query: Optional[str] = None,
        params: Any = None,
        query_id: Optional[str] = None,
        error_code: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Initialize the database query error.
        
        Args:
            detail: A human-readable explanation of the error
            query: The query that failed (sanitized if necessary)
            params: Query parameters (will be sanitized)
            query_id: Optional identifier for the query
            error_code: Database-specific error code
            **extra: Additional fields to include in the problem details
        """
        if query is not None:
            # Sanitize the query if it contains sensitive information
            safe_query = self._sanitize_query(query)
            extra['query'] = safe_query
            
            # Add query fingerprint for error tracking
            extra['query_fingerprint'] = self._get_query_fingerprint(query)
            
        if params is not None:
            # Sanitize parameters to avoid logging sensitive data
            safe_params = self._sanitize_parameters(params)
            if safe_params:
                extra['params'] = safe_params
                
        if query_id is not None:
            extra['query_id'] = query_id
            
        if error_code is not None:
            extra['error_code'] = error_code
            
        super().__init__(detail=detail, **extra)
    
    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Sanitize SQL query for logging purposes.
        
        Removes or masks sensitive information like passwords.
        """
        # This is a basic implementation - should be enhanced based on your needs
        import re
        
        # Mask password in connection strings
        query = re.sub(
            r"(password|pwd|passwd)=['\"][^'\"]*['\"]",
            r"\1=***",
            query,
            flags=re.IGNORECASE
        )
        
        # Mask sensitive values in queries
        sensitive_terms = ['password', 'token', 'secret', 'api_key']
        for term in sensitive_terms:
            query = re.sub(
                fr"({term}\s*=\s*['\"])([^'\"]*)(['\"])"  # noqa: F541,
                fr"\1***\3",
                query,
                flags=re.IGNORECASE
            )
            
        return query.strip()
    
    @staticmethod
    def _sanitize_parameters(params: Any) -> Any:
        """Sanitize query parameters to remove sensitive data.
        
        Returns a version of the parameters safe for logging.
        """
        if params is None:
            return None
            
        if isinstance(params, (str, int, float, bool)):
            return "***" if any(s in str(params).lower() for s in ['pass', 'token', 'secret', 'key']) else params
            
        if isinstance(params, (list, tuple)):
            return [DatabaseQueryError._sanitize_parameters(p) for p in params]
            
        if isinstance(params, dict):
            return {
                k: "***" if any(s in k.lower() for s in ['pass', 'token', 'secret', 'key']) 
                     else DatabaseQueryError._sanitize_parameters(v)
                for k, v in params.items()
            }
            
        return "[complex-parameter]"
    
    @staticmethod
    def _get_query_fingerprint(query: str) -> str:
        """Create a fingerprint of the query for grouping similar errors."""
        import hashlib
        import re
        
        # Remove comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Remove string literals
        query = re.sub(r"'[^']*'", '?', query)
        query = re.sub(r'"[^"]*"', '?', query)
        
        # Remove numeric values
        query = re.sub(r'\b\d+\b', '?', query)
        
        # Create a hash of the normalized query
        return hashlib.md5(query.encode('utf-8')).hexdigest()


# Authentication and authorization exceptions
class InvalidTokenError(UnauthorizedError):
    """Raised when an invalid or malformed token is provided.
    
    This exception indicates that the provided authentication token is either:
    - Malformed
    - Has an invalid signature
    - Is not in the expected format
    - Has been tampered with
    
    Attributes:
        detail: Human-readable error message
        token_type: Type of token (e.g., 'access', 'refresh')
        algorithm: The algorithm used for the token
        
    Example:
        ```python
        try:
            payload = jwt.decode(token, key, algorithms=["RS256"])
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid authentication token")
        ```
    """
    def __init__(
        self, 
        detail: str = "Invalid or malformed token", 
        token_type: Optional[str] = None,
        algorithm: Optional[str] = None,
        **extra: Any
    ) -> None:
        if token_type:
            extra['token_type'] = token_type
        if algorithm:
            extra['algorithm'] = algorithm
        extra['hint'] = "Check that your token is correctly formatted and not corrupted"
        super().__init__(detail=detail, **extra)


class ExpiredTokenError(UnauthorizedError):
    """Raised when a token has expired.
    
    This exception indicates that the authentication token was valid but has
    exceeded its expiration time.
    
    Attributes:
        detail: Human-readable error message
        expires_at: When the token expired (ISO 8601 format)
        token_type: Type of token (e.g., 'access', 'refresh')
    
    Example:
        ```python
        try:
            payload = jwt.decode(token, key, algorithms=["RS256"])
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenError(
                "Token has expired",
                expires_at=datetime.utcnow().isoformat()
            )
        ```
    """
    def __init__(
        self, 
        detail: str = "Token has expired", 
        expires_at: Optional[str] = None,
        token_type: Optional[str] = None,
        **extra: Any
    ) -> None:
        extra['reason'] = 'token_expired'
        if expires_at:
            extra['expires_at'] = expires_at
        if token_type:
            extra['token_type'] = token_type
        extra['hint'] = "Request a new token using the refresh token endpoint"
        super().__init__(detail=detail, **extra)


class InsufficientPermissionsError(ForbiddenError):
    """Raised when the user doesn't have sufficient permissions.
    
    This exception indicates that while the user is authenticated, they don't
    have the required permissions to access the requested resource.
    
    Attributes:
        detail: Human-readable error message
        required_permissions: List of required permissions
        user_permissions: List of permissions the user has
        resource: The resource being accessed
        action: The action being attempted
    
    Example:
        ```python
        required_perms = ["documents:read"]
        user_perms = get_user_permissions(user_id)
        
        if not all(perm in user_perms for perm in required_perms):
            raise InsufficientPermissionsError(
                "You don't have permission to view this document",
                required_permissions=required_perms,
                user_permissions=user_perms,
                resource=f"documents/{document_id}",
                action="read"
            )
        ```
    """
    def __init__(
        self, 
        detail: str = "Insufficient permissions to perform this action",
        required_permissions: Optional[list] = None,
        user_permissions: Optional[list] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Initialize the insufficient permissions error.
        
        Args:
            detail: A human-readable explanation of the error
            required_permissions: List of required permissions
            user_permissions: List of permissions the user has
            resource: The resource being accessed
            action: The action being attempted
            **extra: Additional fields to include in the problem details
        """
        if required_permissions is not None:
            extra['required_permissions'] = required_permissions
        if user_permissions is not None:
            extra['user_permissions'] = user_permissions
        if resource is not None:
            extra['resource'] = resource
        if action is not None:
            extra['action'] = action
            
        extra['hint'] = "Contact your administrator to request additional permissions"
        super().__init__(detail=detail, **extra)


class RateLimitExceededError(TooManyRequestsError):
    """Raised when a rate limit is exceeded.
    
    This exception indicates that the client has made too many requests
    in a given time period and should wait before making new requests.
    
    Attributes:
        detail: Human-readable error message
        limit: The rate limit that was exceeded (e.g., "100 requests per hour")
        reset_time: When the rate limit will reset (ISO 8601 format)
        scope: The scope of the rate limit (e.g., 'ip', 'user', 'global')
    
    Example:
        ```python
        def check_rate_limit(user_id):
            key = f"rate_limit:{user_id}"
            current = cache.incr(key)
            if current == 1:
                cache.expire(key, 3600)  # Set 1-hour expiration
            
            limit = 100  # requests per hour
            if current > limit:
                reset_time = datetime.utcnow() + cache.ttl(key)
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {limit} requests per hour",
                    limit=f"{limit} requests per hour",
                    reset_time=reset_time.isoformat(),
                    scope="user"
                )
        ```
    """
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        limit: Optional[str] = None,
        reset_time: Optional[str] = None,
        scope: Optional[str] = None,
        **extra: Any
    ) -> None:
        if limit is not None:
            extra['limit'] = limit
        if reset_time is not None:
            extra['reset_time'] = reset_time
        if scope is not None:
            extra['scope'] = scope
            
        extra['hint'] = "Please wait before making additional requests"
        super().__init__(detail=detail, **extra)


class SecurityError(ForbiddenError):
    """Base class for security-related errors.
    
    This should be used as a base class for more specific security exceptions.
    """
    def __init__(self, detail: str = "Security violation", **extra: Any) -> None:
        super().__init__(detail=detail, **extra)


class CSRFError(SecurityError):
    """Raised when CSRF validation fails.
    
    This exception indicates a potential CSRF attack or misconfiguration.
    """
    def __init__(
        self, 
        detail: str = "CSRF token validation failed",
        reason: Optional[str] = None,
        **extra: Any
    ) -> None:
        if reason:
            extra['reason'] = reason
        extra['hint'] = "Ensure your request includes a valid CSRF token"
        super().__init__(detail=detail, **extra)


class InputValidationError(ValidationError):
    """Raised when input data fails validation checks.
    
    This is a more specific version of ValidationError for security-related
    input validation failures.
    """
    def __init__(
        self, 
        detail: str = "Input validation failed",
        field: Optional[str] = None,
        value: Any = None,
        **extra: Any
    ) -> None:
        if field is not None:
            extra['field'] = field
        if value is not None:
            extra['value'] = str(value)[:100]  # Truncate long values
            
        extra['hint'] = "Check the input data for potentially malicious content"
        super().__init__(detail=detail, **extra)


# Business logic exceptions
class ResourceLockedError(ConflictError):
    """Raised when a resource is locked and cannot be modified.
    
    This exception indicates that the requested resource is currently locked
    by another process or user and cannot be modified at this time.
    
    Attributes:
        detail: Human-readable error message
        locked_by: ID or name of the process/user holding the lock
        locked_at: When the lock was acquired (ISO 8601 format)
        locked_until: When the lock will be released (ISO 8601 format)
        lock_ttl: Time-to-live for the lock in seconds
        resource: The resource that is locked
        
    Example:
        ```python
        # Try to acquire a lock
        lock_acquired = cache.add(
            f"lock:resource:{resource_id}", 
            current_user.id, 
            timeout=300  # 5 minutes
        )
        
        if not lock_acquired:
            # Check who has the lock
            locked_by = cache.get(f"lock:resource:{resource_id}")
            raise ResourceLockedError(
                "This resource is currently being modified by another user",
                locked_by=locked_by,
                locked_until=cache.ttl(f"lock:resource:{resource_id}"),
                resource=f"resources/{resource_id}"
            )
        ```
    """
    def __init__(
        self, 
        detail: str = "The resource is currently locked",
        locked_by: Optional[str] = None,
        locked_at: Optional[str] = None,
        locked_until: Optional[str] = None,
        lock_ttl: Optional[int] = None,
        resource: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Initialize the resource locked error.
        
        Args:
            detail: A human-readable explanation of the error
            locked_by: Identifier of who locked the resource
            locked_until: When the lock will expire (ISO 8601 format)
            **extra: Additional fields to include in the problem details
        """
        if locked_by is not None:
            extra['locked_by'] = str(locked_by)
        if locked_at is not None:
            extra['locked_at'] = locked_at
        if locked_until is not None:
            extra['locked_until'] = locked_until
        if lock_ttl is not None:
            extra['lock_ttl_seconds'] = lock_ttl
        if resource is not None:
            extra['resource'] = resource
            
        extra['hint'] = "Try again later or contact the lock owner if you need immediate access"
        super().__init__(detail=detail, **extra)


class VersionConflictError(ConflictError):
    """Raised when there's a version conflict (optimistic concurrency control).
    
    This exception is used to implement optimistic concurrency control, where
    a version number or timestamp is used to detect concurrent modifications.
    
    Attributes:
        detail: Human-readable error message
        current_version: The current version of the resource
        provided_version: The version that was provided in the request
        resource: The resource that has the version conflict
        diff: Optional dictionary showing the differences between versions
    
    Example:
        ```python
        async def update_resource(resource_id: str, data: dict, version: int):
            # Get current version from database
            current = await db.fetch_one(
                "SELECT version FROM resources WHERE id = $1",
                resource_id
            )
            
            if current['version'] != version:
                raise VersionConflictError(
                    "Resource has been modified by another user",
                    current_version=current['version'],
                    provided_version=version,
                    resource=f"resources/{resource_id}",
                    diff={
                        'current': current['data'],
                        'provided': data
                    }
                )
        ```
    """
    def __init__(
        self, 
        detail: str = "Version conflict",
        current_version: Optional[Any] = None,
        provided_version: Optional[Any] = None,
        resource: Optional[str] = None,
        diff: Optional[Dict[str, Any]] = None,
        **extra: Any
    ) -> None:
        """Initialize the version conflict error.
        
        Args:
            detail: A human-readable explanation of the error
            current_version: The current version of the resource
            provided_version: The version that was provided in the request
            resource: The resource that has the version conflict
            diff: Optional dictionary showing the differences between versions
            **extra: Additional fields to include in the problem details
        """
        if current_version is not None:
            extra['current_version'] = str(current_version)
        if provided_version is not None:
            extra['provided_version'] = str(provided_version)
        if resource is not None:
            extra['resource'] = resource
        if diff is not None:
            extra['diff'] = diff
            
        extra['hint'] = "Refresh the resource and try again with the latest version"
        super().__init__(detail=detail, **extra)


class InvalidStateError(ConflictError):
    """Raised when an operation is invalid for the current state.
    
    This exception indicates that the requested operation cannot be performed
    because the resource is in an incompatible state.
    
    Attributes:
        detail: Human-readable error message
        current_state: The current state of the resource
        allowed_actions: List of actions that are allowed in the current state
        resource: The resource that is in an invalid state
        valid_states: List of states in which the operation would be valid
    
    Example:
        ```python
        def cancel_order(order_id: str):
            order = get_order(order_id)
            
            if order['status'] not in ['pending', 'processing']:
                raise InvalidStateError(
                    f"Cannot cancel order in {order['status']} state",
                    current_state=order['status'],
                    allowed_actions=['refund', 'return'],
                    resource=f"orders/{order_id}",
                    valid_states=['pending', 'processing']
                )
        ```
    """
    def __init__(
        self, 
        service_name: str,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        **extra: Any
    ) -> None:
        """Initialize the external service error.
        
        Args:
            service_name: The name of the external service
            detail: A human-readable explanation of the error
            status_code: The HTTP status code returned by the service (if any)
            **extra: Additional fields to include in the problem details
        """
        if detail is None:
            detail = f"Error communicating with {service_name} service"
            
        extra['service'] = service_name
        if status_code is not None:
            extra['service_status_code'] = status_code
            
        super().__init__(detail=detail, **extra)


# Configuration and maintenance
class ConfigurationError(InternalServerError):
    """Raised when there is a configuration error.
    
    This exception indicates that there's a problem with the application's
    configuration that prevents it from functioning correctly. This is typically
    a deployment or environment issue rather than a runtime error.
    
    Attributes:
        detail: Human-readable error message
        setting: The name of the problematic setting
        expected: The expected value or format
        actual: The actual value that caused the error
        environment: The environment where the error occurred (e.g., 'production')
    
    Example:
        ```python
        def get_required_setting(name: str) -> str:
            value = os.getenv(name)
            if not value:
                raise ConfigurationError(
                    f"Required setting {name} is not configured",
                    setting=name,
                    expected="non-empty string",
                    environment=os.getenv("ENVIRONMENT", "development")
                )
            return value
        ```
    """
    def __init__(
        self, 
        detail: str = "Configuration error",
        setting: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        environment: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Initialize the configuration error.
        
        Args:
            detail: A human-readable explanation of the error
            setting: The name of the problematic setting
            expected: The expected value or format
            actual: The actual value that caused the error
            environment: The environment where the error occurred
            **extra: Additional fields to include in the problem details
        """
        if setting is not None:
            extra['setting'] = setting
        if expected is not None:
            extra['expected'] = str(expected)
        if actual is not None:
            extra['actual'] = str(actual)
        if environment is not None:
            extra['environment'] = environment
            
        extra['hint'] = "Check your environment variables and configuration files"
        super().__init__(detail=detail, **extra)


class ExternalServiceError(ServiceUnavailableError):
    """Raised when an external service fails.
    
    This exception indicates that an error occurred while communicating with
    an external service or dependency. It should be used for temporary
    failures where retrying the operation might succeed.
    
    Attributes:
        detail: Human-readable error message
        service: The name of the external service that failed
        status_code: The HTTP status code returned by the service (if any)
        error_code: Service-specific error code (if available)
        request_id: Request ID for tracing (if available)
        retry_after: Suggested time to wait before retrying (in seconds)
        
    Example:
        ```python
        try:
            response = await http_client.post(
                "https://api.payments.com/charges",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                service_name="payment-gateway",
                detail=f"Payment service error: {e.response.text}",
                status_code=e.response.status_code,
                request_id=e.response.headers.get("X-Request-ID"),
                retry_after=e.response.headers.get("Retry-After")
            )
        ```
    """
    def __init__(
        self, 
        service_name: str,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[Union[int, str]] = None,
        **extra: Any
    ) -> None:
        """Initialize the external service error.
        
        Args:
            service_name: The name of the external service
            detail: A human-readable explanation of the error
            status_code: The HTTP status code returned by the service
            error_code: Service-specific error code
            request_id: Request ID for tracing
            retry_after: Suggested time to wait before retrying (in seconds or HTTP date)
            **extra: Additional fields to include in the problem details
        """
        detail = detail or f"Error communicating with {service_name}"
        extra['service'] = service_name
        if status_code is not None:
            extra['status_code'] = status_code
        if error_code is not None:
            extra['error_code'] = error_code
        if request_id is not None:
            extra['request_id'] = request_id
        if retry_after is not None:
            extra['retry_after_seconds'] = retry_after
            
        extra['hint'] = "The issue may be temporary. Please try again later."
        
        # Set Retry-After header if provided
        if retry_after is not None and 'headers' not in extra:
            if isinstance(retry_after, (int, float)):
                # Already in seconds
                retry_seconds = int(retry_after)
            else:
                # Try to parse as ISO 8601 datetime
                try:
                    from datetime import datetime, timezone
                    restore_dt = datetime.fromisoformat(str(retry_after).replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    retry_seconds = int((restore_dt - now).total_seconds())
                except (ValueError, TypeError):
                    # If we can't parse it, use a default value
                    retry_seconds = 60  # 1 minute
            
            if retry_seconds > 0:
                extra['headers'] = {'Retry-After': str(retry_seconds)}
                
        super().__init__(detail=detail, **extra)


class MaintenanceError(ServiceUnavailableError):
    """Raised when the service is down for maintenance.
    
    This exception indicates that the service is temporarily unavailable
    due to planned or emergency maintenance.
    
    Attributes:
        detail: Human-readable error message
        scheduled: Whether the maintenance was scheduled in advance
        estimated_restore_time: When the service is expected to be back (ISO 8601 format)
        maintenance_id: Identifier for the maintenance event
        impact: Description of the impact (e.g., 'full-outage', 'degraded-performance')
        updates_url: URL for maintenance updates
    
    Example:
        ```python
        if maintenance_in_progress():
            raise MaintenanceError(
                "Database maintenance in progress",
                scheduled=True,
                estimated_restore_time="2023-06-15T14:00:00Z",
                maintenance_id="db-upgrade-2023-06",
                impact="read-only-mode",
                updates_url="https://status.example.com/incidents/123"
            )
        ```
    """
    def __init__(
        self, 
        detail: str = "Service is currently under maintenance",
        scheduled: bool = False,
        estimated_restore_time: Optional[str] = None,
        maintenance_id: Optional[str] = None,
        impact: Optional[str] = None,
        updates_url: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Initialize the maintenance error.
        
        Args:
            detail: A human-readable explanation of the maintenance
            scheduled: Whether the maintenance was scheduled in advance
            estimated_restore_time: When the service is expected to be back (ISO 8601 format)
            maintenance_id: Identifier for the maintenance event
            impact: Description of the impact (e.g., 'full-outage', 'degraded-performance')
            updates_url: URL for maintenance updates
            **extra: Additional fields to include in the problem details
        """
        maintenance_info = {'scheduled': scheduled}
        
        if estimated_restore_time is not None:
            maintenance_info['estimated_restore_time'] = estimated_restore_time
        if maintenance_id is not None:
            maintenance_info['id'] = maintenance_id
        if impact is not None:
            maintenance_info['impact'] = impact
        if updates_url is not None:
            maintenance_info['updates_url'] = updates_url
            
        extra['maintenance'] = maintenance_info
        
        # Set Retry-After header if we have an estimated restore time
        if estimated_restore_time and 'headers' not in extra:
            try:
                from datetime import datetime, timezone
                restore_dt = datetime.fromisoformat(estimated_restore_time.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                retry_after = int((restore_dt - now).total_seconds())
                if retry_after > 0:
                    extra['headers'] = {'Retry-After': str(retry_after)}
            except (ValueError, TypeError):
                pass
                
        extra['hint'] = "Please try again after the maintenance window"
        super().__init__(detail=detail, **extra)


# Idempotency
class IdempotencyError(ConflictError):
    """Raised when an idempotency key is reused with different parameters.
    
    This exception indicates that the same idempotency key was used for
    different request parameters, which is not allowed to prevent
    accidental duplicate operations.
    
    Attributes:
        detail: Human-readable error message
        idempotency_key: The idempotency key that was reused
        original_request_id: The ID of the original request
        request_diff: Dictionary showing differences between requests
    
    Example:
        ```python
        def process_with_idempotency(key: str, params: dict):
            # Check if we've seen this key before
            cached = cache.get(f"idempotency:{key}")
            
            if cached:
                # Compare the new params with the cached ones
                if cached['params'] != params:
                    raise IdempotencyError(
                        idempotency_key=key,
                        original_request_id=cached['request_id'],
                        request_diff={
                            'original': cached['params'],
                            'new': params
                        }
                    )
                return cached['result']
                
            # Process the request and cache the result
            result = process_request(params)
            cache.set(
                f"idempotency:{key}",
                {
                    'request_id': str(uuid.uuid4()),
                    'params': params,
                    'result': result
                },
                timeout=24 * 60 * 60  # 24 hours
            )
            return result
        ```
    """
    def __init__(
        self, 
        detail: str = "Idempotency key has already been used with different parameters",
        idempotency_key: Optional[str] = None,
        original_request_id: Optional[str] = None,
        request_diff: Optional[Dict[str, Any]] = None,
        **extra: Any
    ) -> None:
        """Initialize the idempotency error.
        
        Args:
            detail: A human-readable explanation of the error
            idempotency_key: The idempotency key that was reused
            original_request_id: The ID of the original request
            request_diff: Dictionary showing differences between requests
            **extra: Additional fields to include in the problem details
        """
        if idempotency_key is not None:
            extra['idempotency_key'] = idempotency_key
        if original_request_id is not None:
            extra['original_request_id'] = original_request_id
        if request_diff is not None:
            extra['request_diff'] = request_diff
            
        extra['hint'] = "Use a new idempotency key for different requests"
        super().__init__(detail=detail, **extra)

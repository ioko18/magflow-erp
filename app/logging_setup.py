"""Simple logging setup for request context management."""

import contextvars

# Context variables for request tracking
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def set_request_context(request_id: str) -> None:
    """Set the current request ID in the context."""
    request_id_var.set(request_id)


def clear_request_context() -> None:
    """Clear the current request context."""
    request_id_var.set(None)


def get_current_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_var.get()

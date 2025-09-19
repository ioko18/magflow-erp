"""Sentry initialization shim for tests.

In testing environments, Sentry can be a no-op. This module provides an
`init_sentry()` function referenced by `app.main`.
"""
from __future__ import annotations

def init_sentry() -> None:
    # No-op for tests; production can wire real Sentry SDK here.
    return None

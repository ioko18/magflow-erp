"""Utility functions for the MagFlow project.

This module currently provides a simple UUID generator used throughout the
codebase. Additional helpers can be added here as the project grows.
"""

import uuid


def generate_uuid() -> str:
    """Return a new random UUID4 string.

    The function is deliberately tiny – it simply wraps ``uuid.uuid4`` and
    returns the string representation.  Keeping it in a central ``utils``
    module makes it easy to mock in tests and provides a single place for
    future enhancements (e.g., prefixing, custom version, etc.).
    """
    return str(uuid.uuid4())

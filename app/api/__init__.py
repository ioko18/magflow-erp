"""Top‑level API package.

This file exists so that imports such as ``from app.api import dependencies`` work.
It re‑exports the ``dependencies`` module from the versioned ``v1`` package for
back‑compatibility with older code.
"""

# Re‑export ``dependencies`` for legacy imports used in some endpoint modules.
from . import dependencies  # noqa: F401

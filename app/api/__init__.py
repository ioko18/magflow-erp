"""Top‑level API package.

This file exists so that imports such as ``from app.api import deps`` work.
It re‑exports the ``deps`` module from the versioned ``v1`` package for
back‑compatibility with older code.
"""

# Re‑export ``deps`` for legacy imports used in some endpoint modules.
from . import deps  # noqa: F401

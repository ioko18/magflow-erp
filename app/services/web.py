# Minimal aiohttp.web shim for tests.
# Provides a Response object with attributes used by tests and an async json() method.
from __future__ import annotations

import json as _json
from typing import Any


class Response:
    def __init__(
        self,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        text: str = "",
        content_type: str = "application/json",
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self._text = text
        self.content_type = content_type

    async def json(self) -> Any:
        if self._text:
            return _json.loads(self._text)
        return {}

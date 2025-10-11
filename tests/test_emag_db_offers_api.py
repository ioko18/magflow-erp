from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from app.main import app


class FakeResult:
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = rows

    def fetchall(self):
        class _M:
            def __init__(self, d):
                self._mapping = d

        return [_M(r) for r in self._rows]

    def scalar(self):
        return len(self._rows)


class FakeAsyncSession:
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = rows

    async def execute(self, _sql, _params=None):
        # crude branching: if COUNT(*) requested, detect by 'COUNT(' in SQL string
        sql_text = getattr(_sql, "text", str(_sql))
        if "COUNT(" in sql_text.upper():
            return FakeResult(self._rows)
        return FakeResult(self._rows)


@pytest.fixture(autouse=True)
def override_dependencies():
    # Bypass auth
    from app.api import dependencies as deps

    async def fake_user():
        return {"id": 1, "email": "test@example.com"}

    app.dependency_overrides[deps.get_current_active_user] = fake_user

    # Override DB session with static data
    from app.core import database as db_module

    sample_rows = [
        {
            "emag_offer_id": 1001,
            "emag_product_id": 2001,
            "product_name": "Amplificator Pro",
            "currency": "RON",
            "sale_price": 123.45,
            "stock": 5,
            "is_available": True,
            "account_type": "fbe",
            "updated_at": "2025-09-22T20:00:00Z",
        },
        {
            "emag_offer_id": 1002,
            "emag_product_id": 2002,
            "product_name": "Amplificator Basic",
            "currency": "RON",
            "sale_price": 99.99,
            "stock": 0,
            "is_available": False,
            "account_type": "main",
            "updated_at": "2025-09-22T19:00:00Z",
        },
    ]

    async def fake_session_gen():
        yield FakeAsyncSession(sample_rows)

    app.dependency_overrides[db_module.get_async_session] = fake_session_gen
    yield
    app.dependency_overrides.clear()


@pytest.mark.api
def test_list_offers_basic():
    client = TestClient(app)
    r = client.get("/api/v1/emag/db/offers", params={"limit": 10, "page": 1})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert {i["emag_offer_id"] for i in data["items"]} == {1001, 1002}


@pytest.mark.api
def test_list_offers_filters_and_sort():
    client = TestClient(app)
    r = client.get(
        "/api/v1/emag/db/offers",
        params={
            "account_type": "fbe",
            "search": "Amplificator",
            "only_available": True,
            "sort_by": "sale_price",
            "order": "asc",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Fake session returns both rows; API-layer filtering happens in SQL, but here we just
    # validate response structure and that override worked
    assert "items" in data and "total" in data
    assert isinstance(data["items"], list)

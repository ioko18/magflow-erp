import pytest
from types import SimpleNamespace

from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext
from app.services.emag_integration_service import EmagIntegrationService


class FakeProductRepository:
    async def get_all(self, *args, **kwargs):  # pragma: no cover - unused helper
        return []


class FakeOrderRepository:
    def __init__(self):
        self.created_calls = []
        self.updated_calls = []
        self.existing = {}

    async def get_by_id(self, order_id):
        return self.existing.get(order_id)

    async def create(self, data):
        self.created_calls.append(data)
        order_id = data.get("id", f"local-{len(self.created_calls)}")
        entity = SimpleNamespace(id=order_id, **data)
        return entity

    async def update(self, order_id, data):
        self.updated_calls.append((order_id, data))
        entity = self.existing.setdefault(order_id, SimpleNamespace(id=order_id))
        for key, value in data.items():
            setattr(entity, key, value)
        return entity


class FakeApiClient:
    def __init__(self, orders):
        self.orders = orders

    async def get_orders(self, *args, **kwargs):
        return {"orders": self.orders}


def build_order_payload(order_id: str, status: str) -> list[dict]:
    return [
        {
            "id": order_id,
            "status": status,
            "customer_name": "Tester",
            "customer_email": "tester@example.com",
            "total_amount": 199.5,
            "currency": "RON",
            "order_date": "2024-01-01T00:00:00Z",
            "items": [{"sku": "SKU-1", "quantity": 1}],
            "shipping_address": {"city": "Bucharest"},
            "billing_address": {"city": "Bucharest"},
            "payment_method": "card",
            "shipping_cost": 9.99,
        }
    ]


@pytest.mark.asyncio
async def test_sync_orders_creates_and_updates_orders(monkeypatch):
    fake_order_repo = FakeOrderRepository()
    fake_product_repo = FakeProductRepository()

    monkeypatch.setattr(
        "app.services.emag_integration_service.get_order_repository",
        lambda: fake_order_repo,
    )
    monkeypatch.setattr(
        "app.services.emag_integration_service.get_product_repository",
        lambda: fake_product_repo,
    )

    settings = get_settings()
    context = ServiceContext(settings=settings)
    service = EmagIntegrationService(context)

    orders_payload = build_order_payload("order-123", "new")
    service.api_client = FakeApiClient(orders_payload)

    create_result = await service.sync_orders()

    assert create_result["created"] == ["order-123"]
    assert create_result["updated"] == []
    assert fake_order_repo.created_calls, "Order creation should be triggered"
    assert fake_order_repo.created_calls[0]["status"] == "pending"

    fake_order_repo.existing["order-123"] = SimpleNamespace(
        id="order-123", status="pending"
    )

    orders_payload[0]["status"] = "confirmed"

    update_result = await service.sync_orders()

    assert update_result["updated"] == ["order-123"]
    assert fake_order_repo.updated_calls, "Order update should be triggered"
    assert fake_order_repo.updated_calls[0][1]["status"] == "confirmed"

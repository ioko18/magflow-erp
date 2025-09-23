import pytest
from fastapi import status

pytestmark = pytest.mark.asyncio

# Sample test data
TEST_ITEMS = [
    {"id": i, "name": f"Item {i}", "created_at": f"2023-01-{i:02d}T00:00:00Z"}
    for i in range(1, 21)  # 20 test items
]


async def test_keyset_pagination_forward(async_client, auth_headers):
    # First page
    response = await async_client.get(
        "/api/items",
        params={"limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 5
    assert data["pagination"]["has_more"] is True
    assert "next_cursor" in data["pagination"]

    # Next page using cursor
    next_cursor = data["pagination"]["next_cursor"]
    response = await async_client.get(
        "/api/items",
        params={"limit": 5, "after": next_cursor},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 5


async def test_keyset_pagination_backward(async_client, auth_headers):
    # Get a cursor from the middle
    response = await async_client.get(
        "/api/items",
        params={"limit": 10},
        headers=auth_headers,
    )
    middle_cursor = response.json()["pagination"]["next_cursor"]

    # Go back 5 items
    response = await async_client.get(
        "/api/items",
        params={"limit": 5, "before": middle_cursor},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 5


async def test_invalid_cursor(async_client, auth_headers):
    # Test with invalid cursor format
    response = await async_client.get(
        "/api/items",
        params={"after": "invalid_cursor"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_max_page_size(async_client, auth_headers):
    # Test maximum page size limit
    response = await async_client.get(
        "/api/items",
        params={"limit": 1000},  # Exceeds max limit
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) <= 100  # Assuming 100 is max page size


async def test_empty_result_set(async_client, auth_headers):
    # Test with cursor that points beyond last item
    response = await async_client.get(
        "/api/items",
        params={
            "after": "eyJpZCI6MTAwMDAwMDAwMCwiY3JlYXRlZF9hdCI6IjIwMjMtMTItMzFUMjM6NTk6NTkuOTk5OTk5WiJ9",
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 0
    assert data["pagination"]["has_more"] is False

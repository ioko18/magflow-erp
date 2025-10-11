"""Thin wrapper around the async eMAG client for use in the ERP.

The project already ships a fairly complete async client in
`app/emag_client_complete.py`.  That client is designed for direct use
by developers and prints request/response details to stdout.  For the
ERP we want a clean, reusable interface that:

* Exposes only the methods needed by the sync service (GET/POST).
* Returns parsed JSON (or Pydantic models) without printing.
* Uses the same rate‑limiting and retry logic already implemented.
"""

from __future__ import annotations

from typing import Any, TypeVar

from .emag_client_complete import EmagAccountType, EmagClient

T = TypeVar("T")


class EmagAPIWrapper:
    """High‑level wrapper used by the ERP services.

    The wrapper is a thin async context manager that forwards calls to the
    underlying :class:`EmagClient`.  It hides the low‑level details such as
    authentication headers and logging, providing a clean ``await``‑able API.
    """

    def __init__(self, account_type: EmagAccountType = EmagAccountType.MAIN) -> None:
        self.account_type = account_type
        self._client: EmagClient | None = None

    async def __aenter__(self) -> EmagAPIWrapper:
        self._client = EmagClient(account_type=self.account_type)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T:
        if not self._client:
            raise RuntimeError(
                "EmagAPIWrapper must be used as an async context manager",
            )
        return await self._client.get(
            endpoint=endpoint,
            params=params,
            response_model=response_model,
        )

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T:
        if not self._client:
            raise RuntimeError(
                "EmagAPIWrapper must be used as an async context manager",
            )
        return await self._client.post(
            endpoint=endpoint,
            data=data,
            response_model=response_model,
        )

    # Additional HTTP verbs can be added if needed (put, delete, …)

    async def fetch_all_offers(self, per_page: int = 100) -> list[dict[str, Any]]:
        """Iterate over all pages of ``/product_offer/read``.

        The eMAG API uses POST for reads, so we delegate to ``post``.
        """
        offers: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = await self.post(
                endpoint="product_offer/read",
                data={"page": page, "per_page": per_page},
            )
            batch = resp.get("results", [])
            if not batch:
                break
            offers.extend(batch)
            page += 1
        return offers

    # RMA (Returns Management) endpoints
    async def create_rma(self, rma_data: dict[str, Any]) -> dict[str, Any]:
        """Create a return request in eMAG."""
        return await self.post("rma/create", data=rma_data, response_model=dict)

    async def update_rma_status(
        self,
        rma_id: str,
        status: str,
        notes: str = None,
    ) -> dict[str, Any]:
        """Update RMA status in eMAG."""
        data = {"rma_id": rma_id, "status": status}
        if notes:
            data["notes"] = notes
        return await self.post("rma/update_status", data=data, response_model=dict)

    async def get_rma_details(self, rma_id: str) -> dict[str, Any]:
        """Get RMA details from eMAG."""
        return await self.get(f"rma/{rma_id}", response_model=dict)

    # Order Cancellation endpoints
    async def cancel_order(
        self,
        order_id: str,
        reason: str,
        description: str = None,
    ) -> dict[str, Any]:
        """Cancel an order in eMAG."""
        data = {
            "order_id": order_id,
            "reason": reason,
            "description": description or reason,
        }
        return await self.post("order/cancel", data=data, response_model=dict)

    async def process_cancellation_refund(
        self,
        cancellation_id: str,
        refund_amount: float,
        currency: str = "RON",
    ) -> dict[str, Any]:
        """Process refund for order cancellation in eMAG."""
        data = {
            "cancellation_id": cancellation_id,
            "refund_amount": refund_amount,
            "currency": currency,
        }
        return await self.post("order/process_refund", data=data, response_model=dict)

    # Invoice endpoints
    async def create_invoice(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        """Create an invoice in eMAG."""
        return await self.post("invoice/create", data=invoice_data, response_model=dict)

    async def update_invoice_payment_status(
        self,
        invoice_id: str,
        payment_status: str,
        paid_amount: float = None,
    ) -> dict[str, Any]:
        """Update invoice payment status in eMAG."""
        data = {"invoice_id": invoice_id, "payment_status": payment_status}
        if paid_amount:
            data["paid_amount"] = paid_amount
        return await self.post("invoice/update_payment", data=data, response_model=dict)

    async def get_invoice_details(self, invoice_id: str) -> dict[str, Any]:
        """Get invoice details from eMAG."""
        return await self.get(f"invoice/{invoice_id}", response_model=dict)

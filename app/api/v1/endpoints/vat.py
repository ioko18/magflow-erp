"""VAT rate endpoints for the MagFlow API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.integrations.emag.client import EmagAPIClient
from app.integrations.emag.models.responses.vat import VatRate, VatResponse

router = APIRouter(prefix="/vat", tags=["vat"])


@router.get("", response_model=VatResponse)
async def get_vat_rates(
    *,
    cursor: str | None = Query(
        None,
        description="Pagination cursor provided by the previous response.",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Number of VAT rates to retrieve (1-1000).",
    ),
    include_inactive: bool = Query(
        False,
        description="Include inactive VAT rates when set to true.",
    ),
    details: str = Query(
        "full",
        description="Detail level requested from the eMAG API.",
    ),
    country_code: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        description="Optional ISO 3166-1 alpha-2 country code filter.",
    ),
    current_user=Depends(deps.get_current_user),
) -> VatResponse:
    """Fetch VAT rates from the eMAG API with optional pagination."""
    params: dict[str, str] = {"details": details}

    if include_inactive:
        params["includeInactive"] = str(include_inactive).lower()

    if country_code:
        params["countryCode"] = country_code.upper()

    try:
        async with EmagAPIClient() as emag_client:
            return await emag_client.get_paginated(
                endpoint="/api/vat",
                response_model=VatResponse,
                cursor=cursor,
                limit=limit,
                params=params,
            )
    except Exception as exc:  # pragma: no cover - defensive safety net
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching VAT rates: {exc}",
        ) from exc


@router.get("/default", response_model=VatRate)
async def get_default_vat_rate(
    *,
    country_code: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        description="Optional ISO 3166-1 alpha-2 country code filter.",
    ),
    current_user=Depends(deps.get_current_user),
) -> VatRate:
    """Fetch the default VAT rate from the eMAG API."""
    params: dict[str, str] = {"isDefault": "true"}

    if country_code:
        params["countryCode"] = country_code.upper()

    try:
        async with EmagAPIClient() as emag_client:
            response = await emag_client.get(
                endpoint="/api/vat",
                response_model=VatResponse,
                params=params,
            )
    except Exception as exc:  # pragma: no cover - defensive safety net
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching default VAT rate: {exc}",
        ) from exc

    if not response.results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default VAT rate found",
        )

    return response.results[0]

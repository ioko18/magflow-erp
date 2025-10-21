"""
eMAG Addresses Management API Endpoints (NEW in v4.4.9).

This module provides endpoints for managing saved addresses for pickup and return locations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.emag_config import get_emag_config
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.emag.emag_api_client import EmagApiClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emag/addresses", tags=["eMAG Addresses"])


# ========== Pydantic Models ==========


class AddressResponse(BaseModel):
    """eMAG Address model."""

    address_id: str = Field(..., description="Unique address identifier")
    country_id: int = Field(..., description="Country ID")
    country_code: str = Field(..., description="Country Alpha-2 code (e.g., RO, BG)")
    address_type_id: int = Field(
        ..., description="1=Return, 2=Pickup, 3=Invoice HQ, 4=Delivery estimates"
    )
    locality_id: int = Field(..., description="Locality ID")
    suburb: str = Field(..., description="County")
    city: str = Field(..., description="City name")
    address: str = Field(..., description="Street, number, etc.")
    zipcode: str = Field(..., description="Postal code")
    quarter: str | None = Field(None, description="Quarter/district")
    floor: str | None = Field(None, description="Floor number")
    is_default: bool = Field(..., description="Whether this is the default address")


class AddressesListResponse(BaseModel):
    """Response model for addresses list."""

    success: bool
    addresses: list[AddressResponse]
    total: int
    page: int
    items_per_page: int
    message: str | None = None


class AWBRequest(BaseModel):
    """Request model for creating AWB with address_id support."""

    order_id: int | None = Field(None, description="eMAG order ID (for orders)")
    rma_id: int | None = Field(None, description="RMA ID (for returns)")
    sender_address_id: str | None = Field(
        None, description="Saved sender address ID (NEW v4.4.9)"
    )
    sender_name: str | None = Field(None, description="Sender name")
    sender_contact: str | None = Field(None, description="Sender contact person")
    sender_phone1: str | None = Field(None, description="Sender primary phone")
    sender_locality_id: int | None = Field(None, description="Sender locality ID")
    sender_street: str | None = Field(None, description="Sender street address")
    receiver_address_id: str | None = Field(
        None, description="Saved receiver address ID (NEW v4.4.9)"
    )
    receiver_name: str | None = Field(None, description="Receiver name")
    receiver_contact: str | None = Field(None, description="Receiver contact person")
    receiver_phone1: str | None = Field(None, description="Receiver primary phone")
    receiver_locality_id: int | None = Field(
        None, description="Receiver locality ID"
    )
    receiver_street: str | None = Field(None, description="Receiver street address")
    receiver_legal_entity: int = Field(
        0, description="Whether receiver is legal entity"
    )
    envelope_number: int = Field(0, description="Number of envelopes")
    parcel_number: int = Field(1, description="Number of parcels")
    cod: float = Field(0.0, description="Cash on delivery amount")
    is_oversize: int = Field(0, description="Whether package is oversize")
    date: str | None = Field(
        None, description="Pickup date for returns (YYYY-MM-DD)"
    )


# ========== Helper Functions ==========


async def get_emag_client(account_type: str = "main") -> EmagApiClient:
    """Get eMAG API client for specified account."""
    config = get_emag_config()

    if account_type.lower() == "main":
        return EmagApiClient(
            username=config.main_username,
            password=config.main_password,
            base_url=config.main_base_url,
        )
    elif account_type.lower() == "fbe":
        return EmagApiClient(
            username=config.fbe_username,
            password=config.fbe_password,
            base_url=config.fbe_base_url,
        )
    else:
        raise ValueError(f"Invalid account type: {account_type}")


# ========== API Endpoints ==========


@router.get("/list", response_model=AddressesListResponse)
async def get_addresses(
    account_type: str = Query("main", description="Account type: main or fbe"),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get saved addresses for pickup and return locations (NEW in v4.4.9).

    This endpoint retrieves your saved addresses that can be used when issuing AWBs.

    **Address Types:**
    - 1 = Return address
    - 2 = Pickup address
    - 3 = Invoice (HQ) address
    - 4 = Delivery estimates address

    **Example Response:**
    ```json
    {
      "success": true,
      "addresses": [
        {
          "address_id": "12345",
          "country_id": 1,
          "country_code": "RO",
          "address_type_id": 2,
          "locality_id": 8801,
          "suburb": "Bucuresti",
          "city": "Sector 1",
          "address": "Str. Exemplu, Nr. 10",
          "zipcode": "010101",
          "quarter": "",
          "floor": "2",
          "is_default": true
        }
      ],
      "total": 1,
      "page": 1,
      "items_per_page": 100
    }
    ```
    """
    try:
        async with await get_emag_client(account_type) as client:
            # Get addresses from eMAG API
            response = await client.get_addresses(
                page=page, items_per_page=items_per_page
            )

            if response.get("isError"):
                error_messages = response.get("messages", [])
                error_text = error_messages[0] if error_messages else "Unknown error"
                raise HTTPException(
                    status_code=400, detail=f"eMAG API error: {error_text}"
                )

            results = response.get("results", [])

            # Parse addresses
            addresses = []
            for addr in results:
                addresses.append(
                    AddressResponse(
                        address_id=str(addr.get("address_id", "")),
                        country_id=addr.get("country_id", 0),
                        country_code=addr.get("country_code", ""),
                        address_type_id=addr.get("address_type_id", 0),
                        locality_id=addr.get("locality_id", 0),
                        suburb=addr.get("suburb", ""),
                        city=addr.get("city", ""),
                        address=addr.get("address", ""),
                        zipcode=addr.get("zipcode", ""),
                        quarter=addr.get("quarter"),
                        floor=addr.get("floor"),
                        is_default=addr.get("is_default", False),
                    )
                )

            return AddressesListResponse(
                success=True,
                addresses=addresses,
                total=len(addresses),
                page=page,
                items_per_page=items_per_page,
                message=(
                    f"Retrieved {len(addresses)} addresses from eMAG "
                    f"{account_type.upper()} account"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching addresses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch addresses: {str(e)}"
        ) from e


@router.get("/pickup", response_model=AddressesListResponse)
async def get_pickup_addresses(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get only pickup addresses (address_type_id = 2).

    Convenience endpoint to retrieve only pickup addresses for AWB creation.
    """
    try:
        async with await get_emag_client(account_type) as client:
            response = await client.get_addresses(page=1, items_per_page=100)

            if response.get("isError"):
                error_messages = response.get("messages", [])
                error_text = error_messages[0] if error_messages else "Unknown error"
                raise HTTPException(
                    status_code=400, detail=f"eMAG API error: {error_text}"
                )

            results = response.get("results", [])

            # Filter only pickup addresses
            pickup_addresses = []
            for addr in results:
                if addr.get("address_type_id") == 2:  # Pickup address
                    pickup_addresses.append(
                        AddressResponse(
                            address_id=str(addr.get("address_id", "")),
                            country_id=addr.get("country_id", 0),
                            country_code=addr.get("country_code", ""),
                            address_type_id=addr.get("address_type_id", 0),
                            locality_id=addr.get("locality_id", 0),
                            suburb=addr.get("suburb", ""),
                            city=addr.get("city", ""),
                            address=addr.get("address", ""),
                            zipcode=addr.get("zipcode", ""),
                            quarter=addr.get("quarter"),
                            floor=addr.get("floor"),
                            is_default=addr.get("is_default", False),
                        )
                    )

            return AddressesListResponse(
                success=True,
                addresses=pickup_addresses,
                total=len(pickup_addresses),
                page=1,
                items_per_page=100,
                message=f"Retrieved {len(pickup_addresses)} pickup addresses",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pickup addresses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch pickup addresses: {str(e)}"
        ) from e


@router.get("/return", response_model=AddressesListResponse)
async def get_return_addresses(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get only return addresses (address_type_id = 1).

    Convenience endpoint to retrieve only return addresses for RMA AWB creation.
    """
    try:
        async with await get_emag_client(account_type) as client:
            response = await client.get_addresses(page=1, items_per_page=100)

            if response.get("isError"):
                error_messages = response.get("messages", [])
                error_text = error_messages[0] if error_messages else "Unknown error"
                raise HTTPException(
                    status_code=400, detail=f"eMAG API error: {error_text}"
                )

            results = response.get("results", [])

            # Filter only return addresses
            return_addresses = []
            for addr in results:
                if addr.get("address_type_id") == 1:  # Return address
                    return_addresses.append(
                        AddressResponse(
                            address_id=str(addr.get("address_id", "")),
                            country_id=addr.get("country_id", 0),
                            country_code=addr.get("country_code", ""),
                            address_type_id=addr.get("address_type_id", 0),
                            locality_id=addr.get("locality_id", 0),
                            suburb=addr.get("suburb", ""),
                            city=addr.get("city", ""),
                            address=addr.get("address", ""),
                            zipcode=addr.get("zipcode", ""),
                            quarter=addr.get("quarter"),
                            floor=addr.get("floor"),
                            is_default=addr.get("is_default", False),
                        )
                    )

            return AddressesListResponse(
                success=True,
                addresses=return_addresses,
                total=len(return_addresses),
                page=1,
                items_per_page=100,
                message=f"Retrieved {len(return_addresses)} return addresses",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching return addresses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch return addresses: {str(e)}"
        ) from e


@router.post("/awb/create")
async def create_awb_with_address(
    awb_request: AWBRequest,
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create AWB with support for saved addresses (UPDATED in v4.4.9).

    **NEW in v4.4.9:** You can now use `sender_address_id` or `receiver_address_id`
    to reference saved addresses instead of providing all address details.

    When `address_id` is provided, the saved address is used regardless of other address fields.

    **Example Request (Order with saved sender address):**
    ```json
    {
      "order_id": 123456,
      "sender_address_id": "12345",
      "sender_name": "My Company SRL",
      "sender_contact": "John Doe",
      "sender_phone1": "0721234567",
      "receiver_name": "Customer Name",
      "receiver_contact": "Customer Name",
      "receiver_phone1": "0729876543",
      "receiver_locality_id": 8801,
      "receiver_street": "Str. Customer, Nr. 5",
      "receiver_legal_entity": 0,
      "parcel_number": 1,
      "cod": 199.99
    }
    ```

    **Example Request (Return with saved receiver address):**
    ```json
    {
      "rma_id": 789012,
      "sender_name": "Customer Name",
      "sender_contact": "Customer Name",
      "sender_phone1": "0729876543",
      "sender_locality_id": 8801,
      "sender_street": "Str. Customer, Nr. 5",
      "receiver_address_id": "12345",
      "receiver_name": "My Company SRL",
      "receiver_contact": "John Doe",
      "receiver_phone1": "0721234567",
      "parcel_number": 1,
      "date": "2025-10-02"
    }
    ```
    """
    try:
        async with await get_emag_client(account_type) as client:
            # Build sender object
            sender = {}
            if awb_request.sender_address_id:
                sender["address_id"] = awb_request.sender_address_id
            if awb_request.sender_name:
                sender["name"] = awb_request.sender_name
            if awb_request.sender_contact:
                sender["contact"] = awb_request.sender_contact
            if awb_request.sender_phone1:
                sender["phone1"] = awb_request.sender_phone1
            if awb_request.sender_locality_id:
                sender["locality_id"] = awb_request.sender_locality_id
            if awb_request.sender_street:
                sender["street"] = awb_request.sender_street

            # Build receiver object
            receiver = {}
            if awb_request.receiver_address_id:
                receiver["address_id"] = awb_request.receiver_address_id
            if awb_request.receiver_name:
                receiver["name"] = awb_request.receiver_name
            if awb_request.receiver_contact:
                receiver["contact"] = awb_request.receiver_contact
            if awb_request.receiver_phone1:
                receiver["phone1"] = awb_request.receiver_phone1
            if awb_request.receiver_locality_id:
                receiver["locality_id"] = awb_request.receiver_locality_id
            if awb_request.receiver_street:
                receiver["street"] = awb_request.receiver_street
            receiver["legal_entity"] = awb_request.receiver_legal_entity

            # Create AWB
            response = await client.create_awb(
                order_id=awb_request.order_id,
                rma_id=awb_request.rma_id,
                sender=sender if sender else None,
                receiver=receiver if receiver else None,
                envelope_number=awb_request.envelope_number,
                parcel_number=awb_request.parcel_number,
                cod=awb_request.cod,
                is_oversize=awb_request.is_oversize,
                date=awb_request.date,
            )

            if response.get("isError"):
                error_messages = response.get("messages", [])
                error_text = error_messages[0] if error_messages else "Unknown error"
                raise HTTPException(
                    status_code=400, detail=f"eMAG API error: {error_text}"
                )

            return {
                "success": True,
                "data": response.get("results", {}),
                "message": "AWB created successfully",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating AWB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create AWB: {str(e)}") from e

"""
eMAG Measurements Service - v4.4.9

Provides product volumetry (dimensions and weight) management using the
measurements/save endpoint from eMAG API Section 8.9.
"""

import asyncio
from typing import Dict, Any, List
from decimal import Decimal

from app.core.logging import get_logger
from app.core.exceptions import ServiceError, ValidationError
from app.services.emag_api_client import EmagApiClient, EmagApiError
from app.config.emag_config import get_emag_config
from app.core.emag_validator import validate_emag_response

logger = get_logger(__name__)


class EmagMeasurementsService:
    """
    Service for managing product measurements (volumetry) on eMAG.
    
    Handles dimensions (mm) and weight (g) for products according to
    eMAG API v4.4.9 Section 8.9 specifications.
    
    Measurement Units:
    - Dimensions: millimeters (mm)
    - Weight: grams (g)
    
    Constraints:
    - All values: 0..999,999 with up to 2 decimals
    """

    # Validation constants
    MIN_VALUE = 0.0
    MAX_VALUE = 999999.0
    MAX_DECIMALS = 2

    def __init__(self, account_type: str = "main"):
        """
        Initialize Measurements Service.
        
        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        self.account_type = account_type
        self.config = get_emag_config(account_type)
        self.client = EmagApiClient(self.config)

        logger.info(
            "Initialized EmagMeasurementsService for %s account",
            account_type
        )

    async def initialize(self):
        """Initialize the service."""
        await self.client.initialize()

    async def close(self):
        """Close the service and cleanup resources."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def save_measurements(
        self,
        product_id: int,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        weight_g: float
    ) -> Dict[str, Any]:
        """
        Save product measurements (volumetry) to eMAG.
        
        Args:
            product_id: Seller internal product ID
            length_mm: Product length in millimeters (0-999,999, 2 decimals)
            width_mm: Product width in millimeters (0-999,999, 2 decimals)
            height_mm: Product height in millimeters (0-999,999, 2 decimals)
            weight_g: Product weight in grams (0-999,999, 2 decimals)
            
        Returns:
            API response dictionary
            
        Raises:
            ValidationError: If measurements are invalid
            ServiceError: If API call fails
        """
        # Validate all measurements
        self._validate_measurement(length_mm, "length")
        self._validate_measurement(width_mm, "width")
        self._validate_measurement(height_mm, "height")
        self._validate_measurement(weight_g, "weight")

        # Round to 2 decimals
        payload = {
            "id": product_id,
            "length": round(length_mm, 2),
            "width": round(width_mm, 2),
            "height": round(height_mm, 2),
            "weight": round(weight_g, 2)
        }

        logger.info(
            "Saving measurements for product %d: L=%.2fmm W=%.2fmm H=%.2fmm Wt=%.2fg",
            product_id,
            length_mm,
            width_mm,
            height_mm,
            weight_g
        )

        try:
            response = await self.client.post("/measurements/save", payload)
            return self._validate_response(response, "measurements save")
        except EmagApiError as e:
            logger.error(
                "Failed to save measurements for product %d: %s",
                product_id,
                str(e)
            )
            raise ServiceError(f"Failed to save measurements: {str(e)}")

    async def save_measurements_from_dict(
        self,
        product_id: int,
        measurements: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Save measurements from a dictionary.
        
        Args:
            product_id: Seller internal product ID
            measurements: Dict with keys: length, width, height, weight
            
        Returns:
            API response dictionary
            
        Raises:
            ValidationError: If measurements are invalid or missing
            ServiceError: If API call fails
        """
        required_keys = ["length", "width", "height", "weight"]
        missing_keys = [key for key in required_keys if key not in measurements]

        if missing_keys:
            raise ValidationError(
                f"Missing required measurement keys: {', '.join(missing_keys)}"
            )

        return await self.save_measurements(
            product_id=product_id,
            length_mm=measurements["length"],
            width_mm=measurements["width"],
            height_mm=measurements["height"],
            weight_g=measurements["weight"]
        )

    async def bulk_save_measurements(
        self,
        measurements_list: List[Dict[str, Any]],
        batch_size: int = 25
    ) -> Dict[str, Any]:
        """
        Bulk save measurements for multiple products.
        
        Args:
            measurements_list: List of dicts with 'id' and measurement fields
            batch_size: Number of updates per batch (default: 25)
            
        Returns:
            Summary of results
            
        Example:
            measurements_list = [
                {
                    "id": 12345,
                    "length": 200.0,
                    "width": 150.5,
                    "height": 80.0,
                    "weight": 450.75
                },
                ...
            ]
        """
        results = {
            "total": len(measurements_list),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        for i in range(0, len(measurements_list), batch_size):
            batch = measurements_list[i:i + batch_size]

            for item in batch:
                try:
                    product_id = item["id"]
                    await self.save_measurements(
                        product_id=product_id,
                        length_mm=item["length"],
                        width_mm=item["width"],
                        height_mm=item["height"],
                        weight_g=item["weight"]
                    )
                    results["successful"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "product_id": item.get("id", "unknown"),
                        "error": str(e)
                    })

                # Rate limiting: ~3 RPS
                await asyncio.sleep(0.4)

        logger.info(
            "Bulk measurements save completed: %d successful, %d failed",
            results["successful"],
            results["failed"]
        )

        return results

    def _validate_measurement(self, value: float, field_name: str) -> None:
        """
        Validate a single measurement value.
        
        Args:
            value: Measurement value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError(
                f"{field_name} must be a number, got {type(value).__name__}"
            )

        if value < self.MIN_VALUE or value > self.MAX_VALUE:
            raise ValidationError(
                f"{field_name} must be between {self.MIN_VALUE} and {self.MAX_VALUE}, "
                f"got {value}"
            )

        # Check decimal places
        decimal_str = str(value)
        if '.' in decimal_str:
            decimal_places = len(decimal_str.split('.')[1])
            if decimal_places > self.MAX_DECIMALS:
                raise ValidationError(
                    f"{field_name} can have maximum {self.MAX_DECIMALS} decimal places, "
                    f"got {decimal_places}"
                )

    def calculate_volume_cm3(
        self,
        length_mm: float,
        width_mm: float,
        height_mm: float
    ) -> float:
        """
        Calculate volume in cubic centimeters from millimeter dimensions.
        
        Args:
            length_mm: Length in millimeters
            width_mm: Width in millimeters
            height_mm: Height in millimeters
            
        Returns:
            Volume in cubic centimeters (cm³)
        """
        # Convert mm to cm and calculate volume
        length_cm = length_mm / 10
        width_cm = width_mm / 10
        height_cm = height_mm / 10

        volume_cm3 = length_cm * width_cm * height_cm
        return round(volume_cm3, 2)

    def calculate_volumetric_weight_kg(
        self,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        divisor: int = 5000
    ) -> float:
        """
        Calculate volumetric weight in kilograms.
        
        Args:
            length_mm: Length in millimeters
            width_mm: Width in millimeters
            height_mm: Height in millimeters
            divisor: Volumetric divisor (default: 5000 for standard shipping)
            
        Returns:
            Volumetric weight in kilograms
            
        Note:
            Common divisors:
            - 5000: Standard shipping
            - 6000: Express shipping
            - 4000: Air freight
        """
        volume_cm3 = self.calculate_volume_cm3(length_mm, width_mm, height_mm)
        volumetric_weight = volume_cm3 / divisor
        return round(volumetric_weight, 2)

    def get_shipping_weight_kg(
        self,
        actual_weight_g: float,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        divisor: int = 5000
    ) -> float:
        """
        Get the chargeable shipping weight (higher of actual or volumetric).
        
        Args:
            actual_weight_g: Actual weight in grams
            length_mm: Length in millimeters
            width_mm: Width in millimeters
            height_mm: Height in millimeters
            divisor: Volumetric divisor
            
        Returns:
            Chargeable weight in kilograms
        """
        actual_weight_kg = actual_weight_g / 1000
        volumetric_weight_kg = self.calculate_volumetric_weight_kg(
            length_mm, width_mm, height_mm, divisor
        )

        return max(actual_weight_kg, volumetric_weight_kg)

    def _validate_response(
        self,
        response: Dict[str, Any],
        operation: str
    ) -> Dict[str, Any]:
        """
        Validate eMAG API response.
        
        Args:
            response: API response dictionary
            operation: Operation description for logging
            
        Returns:
            Validated response
            
        Raises:
            ServiceError: If response is invalid or contains errors
        """
        return validate_emag_response(response, "/measurements/save", operation)

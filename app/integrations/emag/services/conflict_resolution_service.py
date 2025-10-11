"""Conflict resolution service for handling data conflicts during import operations."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.models.emag_offers import EmagImportConflict, EmagProductOffer

logger = logging.getLogger(__name__)


class ConflictResolutionService:
    """Service for detecting and resolving data conflicts during import operations."""

    # Conflict types
    PRICE_MISMATCH = "price_mismatch"
    STOCK_DISCREPANCY = "stock_discrepancy"
    STATUS_CHANGE = "status_change"
    AVAILABILITY_CHANGE = "availability_change"
    VAT_RATE_MISMATCH = "vat_rate_mismatch"

    # Resolution strategies
    STRATEGY_SKIP = "skip"
    STRATEGY_UPDATE = "update"
    STRATEGY_MERGE = "merge"
    STRATEGY_MANUAL = "manual"
    STRATEGY_NEWEST = "newest"
    STRATEGY_HIGHEST_PRICE = "highest_price"
    STRATEGY_LOWEST_STOCK = "lowest_stock"

    def __init__(self):
        """Initialize the conflict resolution service."""
        self.conflict_thresholds = {
            "price_difference_percent": 10.0,  # 10% price difference
            "stock_difference_units": 5,  # 5 units stock difference
            "price_difference_absolute": 50.0,  # 50 RON absolute difference
        }

    def detect_offer_conflicts(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Detect conflicts between existing offer and new offer data.

        Args:
            existing_offer: Existing offer in database
            new_offer_data: New offer data from eMAG

        Returns:
            List of detected conflicts

        """
        conflicts = []

        # Price conflict detection
        price_conflict = self._detect_price_conflict(existing_offer, new_offer_data)
        if price_conflict:
            conflicts.append(price_conflict)

        # Stock conflict detection
        stock_conflict = self._detect_stock_conflict(existing_offer, new_offer_data)
        if stock_conflict:
            conflicts.append(stock_conflict)

        # Status conflict detection
        status_conflict = self._detect_status_conflict(existing_offer, new_offer_data)
        if status_conflict:
            conflicts.append(status_conflict)

        # Availability conflict detection
        availability_conflict = self._detect_availability_conflict(
            existing_offer,
            new_offer_data,
        )
        if availability_conflict:
            conflicts.append(availability_conflict)

        # VAT rate conflict detection
        vat_conflict = self._detect_vat_conflict(existing_offer, new_offer_data)
        if vat_conflict:
            conflicts.append(vat_conflict)

        return conflicts

    def _detect_price_conflict(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect price conflicts."""
        existing_price = existing_offer.price
        new_price = new_offer_data.get("price")

        if existing_price is None or new_price is None:
            return None

        if existing_price == new_price:
            return None

        price_diff = abs(existing_price - new_price)
        price_diff_percent = (
            (price_diff / existing_price) * 100 if existing_price != 0 else 0
        )

        # Check if difference exceeds thresholds
        if (
            price_diff_percent >= self.conflict_thresholds["price_difference_percent"]
            or price_diff >= self.conflict_thresholds["price_difference_absolute"]
        ):
            return {
                "type": self.PRICE_MISMATCH,
                "severity": "high" if price_diff_percent >= 25 else "medium",
                "field": "price",
                "existing_value": existing_price,
                "new_value": new_price,
                "difference": price_diff,
                "difference_percent": price_diff_percent,
                "description": ".2f",
            }

        return None

    def _detect_stock_conflict(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect stock conflicts."""
        existing_stock = existing_offer.stock
        new_stock = new_offer_data.get("stock")

        if existing_stock is None or new_stock is None:
            return None

        if existing_stock == new_stock:
            return None

        stock_diff = abs(existing_stock - new_stock)

        # Check if difference exceeds threshold
        if stock_diff >= self.conflict_thresholds["stock_difference_units"]:
            return {
                "type": self.STOCK_DISCREPANCY,
                "severity": "medium",
                "field": "stock",
                "existing_value": existing_stock,
                "new_value": new_stock,
                "difference": stock_diff,
                "description": f"Stock difference of {stock_diff} units",
            }

        return None

    def _detect_status_conflict(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect status conflicts."""
        existing_status = existing_offer.status
        new_status = new_offer_data.get("status")

        if not existing_status or not new_status:
            return None

        if existing_status == new_status:
            return None

        # Define status priority (higher number = more important)
        status_priority = {
            "active": 3,
            "inactive": 2,
            "pending": 1,
            "blocked": 0,
        }

        existing_priority = status_priority.get(existing_status, 1)
        new_priority = status_priority.get(new_status, 1)

        severity = "low"
        if existing_priority >= 2 and new_priority < 2:
            severity = "high"  # Active to inactive/blocked
        elif existing_priority < 2 and new_priority >= 2:
            severity = "medium"  # Inactive to active

        return {
            "type": self.STATUS_CHANGE,
            "severity": severity,
            "field": "status",
            "existing_value": existing_status,
            "new_value": new_status,
            "description": f"Status changed from {existing_status} to {new_status}",
        }

    def _detect_availability_conflict(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect availability conflicts."""
        existing_available = existing_offer.is_available
        new_available = new_offer_data.get("is_available")

        if existing_available is None or new_available is None:
            return None

        if existing_available == new_available:
            return None

        severity = "high" if not new_available else "medium"

        return {
            "type": self.AVAILABILITY_CHANGE,
            "severity": severity,
            "field": "is_available",
            "existing_value": existing_available,
            "new_value": new_available,
            "description": f"Availability changed from {existing_available} to {new_available}",
        }

    def _detect_vat_conflict(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect VAT rate conflicts."""
        existing_vat = existing_offer.vat_rate
        new_vat = new_offer_data.get("vat_rate")

        if existing_vat is None or new_vat is None:
            return None

        if existing_vat == new_vat:
            return None

        vat_diff = abs(existing_vat - new_vat)

        # VAT rate changes are usually significant
        return {
            "type": self.VAT_RATE_MISMATCH,
            "severity": "high",
            "field": "vat_rate",
            "existing_value": existing_vat,
            "new_value": new_vat,
            "difference": vat_diff,
            "description": ".2f",
        }

    def resolve_conflicts(
        self,
        conflicts: list[dict[str, Any]],
        strategy: str = STRATEGY_MANUAL,
    ) -> tuple[str, dict[str, Any]]:
        """Resolve a list of conflicts using the specified strategy.

        Args:
            conflicts: List of conflicts to resolve
            strategy: Resolution strategy

        Returns:
            Tuple of (resolution_action, resolution_details)

        """
        if not conflicts:
            return "no_conflicts", {}

        # Analyze conflict severity
        high_severity = any(c.get("severity") == "high" for c in conflicts)
        has_price_conflicts = any(c["type"] == self.PRICE_MISMATCH for c in conflicts)

        # Apply resolution strategy
        if strategy == self.STRATEGY_SKIP:
            return "skip", {"reason": "User chose to skip conflicting records"}

        if strategy == self.STRATEGY_UPDATE:
            return "update", {"reason": "User chose to update with new data"}

        if strategy == self.STRATEGY_MERGE:
            merge_details = self._resolve_merge_strategy(conflicts)
            return "merge", merge_details

        if strategy == self.STRATEGY_NEWEST:
            return "update", {"reason": "Using newest data available"}

        if strategy == self.STRATEGY_HIGHEST_PRICE:
            return "update", {"reason": "Using highest price"}

        if strategy == self.STRATEGY_LOWEST_STOCK:
            return "update", {"reason": "Using lowest stock value"}

        # Default to manual review
        return "manual_review", {
            "reason": "Conflicts require manual review",
            "high_severity": high_severity,
            "price_conflicts": has_price_conflicts,
            "conflict_count": len(conflicts),
        }

    def _resolve_merge_strategy(
        self,
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Resolve conflicts using merge strategy."""
        merge_details = {
            "reason": "Merged data from both sources",
            "field_resolutions": {},
        }

        for conflict in conflicts:
            field = conflict["field"]
            conflict_type = conflict["type"]

            if conflict_type == self.PRICE_MISMATCH:
                # For price conflicts, use the higher price
                existing = conflict["existing_value"]
                new = conflict["new_value"]
                resolved_value = max(existing, new)
                merge_details["field_resolutions"][field] = {
                    "strategy": "highest_price",
                    "original_values": [existing, new],
                    "resolved_value": resolved_value,
                }

            elif conflict_type == self.STOCK_DISCREPANCY:
                # For stock conflicts, use the lower stock (more conservative)
                existing = conflict["existing_value"]
                new = conflict["new_value"]
                resolved_value = min(existing, new)
                merge_details["field_resolutions"][field] = {
                    "strategy": "lowest_stock",
                    "original_values": [existing, new],
                    "resolved_value": resolved_value,
                }

            elif conflict_type == self.STATUS_CHANGE:
                # For status conflicts, prefer active status
                existing = conflict["existing_value"]
                new = conflict["new_value"]
                resolved_value = new if new == "active" else existing
                merge_details["field_resolutions"][field] = {
                    "strategy": "prefer_active",
                    "original_values": [existing, new],
                    "resolved_value": resolved_value,
                }

            else:
                # For other conflicts, use new value
                merge_details["field_resolutions"][field] = {
                    "strategy": "use_new",
                    "original_values": [
                        conflict["existing_value"],
                        conflict["new_value"],
                    ],
                    "resolved_value": conflict["new_value"],
                }

        return merge_details

    def create_conflict_record(
        self,
        existing_offer: EmagProductOffer,
        new_offer_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
        sync_id: str,
    ) -> EmagImportConflict:
        """Create a conflict record for manual review.

        Args:
            existing_offer: Existing offer in database
            new_offer_data: New offer data from eMAG
            conflicts: List of detected conflicts
            sync_id: Sync operation ID

        Returns:
            EmagImportConflict record

        """
        # Determine overall severity
        severity_levels = [c.get("severity", "low") for c in conflicts]
        overall_severity = (
            "high"
            if "high" in severity_levels
            else "medium"
            if "medium" in severity_levels
            else "low"
        )

        # Create conflict summary
        conflict_summary = {
            "total_conflicts": len(conflicts),
            "severity": overall_severity,
            "conflict_types": list({c["type"] for c in conflicts}),
            "fields_affected": [c["field"] for c in conflicts],
            "descriptions": [c["description"] for c in conflicts],
        }

        return EmagImportConflict(
            sync_id=sync_id,
            emag_offer_id=new_offer_data.get("emag_offer_id"),
            emag_product_id=new_offer_data.get("emag_product_id"),
            conflict_type=(
                "multiple_conflicts" if len(conflicts) > 1 else conflicts[0]["type"]
            ),
            emag_data=new_offer_data,
            internal_data={
                "price": existing_offer.price,
                "stock": existing_offer.stock,
                "status": existing_offer.status,
                "is_available": existing_offer.is_available,
                "vat_rate": existing_offer.vat_rate,
            },
            status="pending",
            notes=f"Detected {len(conflicts)} conflicts with severity: {overall_severity}",
            metadata_=conflict_summary,
        )

    def get_resolution_recommendation(
        self,
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Get resolution recommendation based on conflict analysis.

        Args:
            conflicts: List of detected conflicts

        Returns:
            Dictionary with recommended resolution strategy and reasoning

        """
        if not conflicts:
            return {"strategy": "update", "reason": "No conflicts detected"}

        # Analyze conflicts
        high_severity_count = sum(1 for c in conflicts if c.get("severity") == "high")
        price_conflicts = [c for c in conflicts if c["type"] == self.PRICE_MISMATCH]
        stock_conflicts = [c for c in conflicts if c["type"] == self.STOCK_DISCREPANCY]

        # Decision logic
        if high_severity_count > 0:
            return {
                "strategy": self.STRATEGY_MANUAL,
                "reason": f"Found {high_severity_count} high-severity conflicts requiring manual review",
                "confidence": "high",
            }

        if price_conflicts:
            # For price conflicts, recommend manual review if difference is significant
            max_price_diff = max(
                (c.get("difference_percent", 0) for c in price_conflicts),
                default=0,
            )
            if max_price_diff >= 25:
                return {
                    "strategy": self.STRATEGY_MANUAL,
                    "reason": ".1f",
                    "confidence": "high",
                }
            return {
                "strategy": self.STRATEGY_UPDATE,
                "reason": "Minor price differences, safe to update automatically",
                "confidence": "medium",
            }

        if stock_conflicts:
            return {
                "strategy": self.STRATEGY_MERGE,
                "reason": "Stock discrepancies can be resolved using conservative approach",
                "confidence": "medium",
            }

        return {
            "strategy": self.STRATEGY_UPDATE,
            "reason": "Minor conflicts that can be safely updated",
            "confidence": "low",
        }

    def apply_resolution_to_offer(
        self,
        offer_record: EmagProductOffer,
        new_offer_data: dict[str, Any],
        resolution: str,
        merge_details: dict[str, Any] | None = None,
    ) -> None:
        """Apply resolution strategy to update offer data.

        Args:
            offer_record: Offer record to update
            new_offer_data: New offer data
            resolution: Resolution strategy
            merge_details: Details for merge resolution

        """
        if resolution == self.STRATEGY_UPDATE:
            # Update all fields with new data
            for field, value in new_offer_data.items():
                if hasattr(offer_record, field):
                    setattr(offer_record, field, value)

        elif resolution == self.STRATEGY_MERGE and merge_details:
            # Apply merge resolution
            field_resolutions = merge_details.get("field_resolutions", {})
            for field, resolution_info in field_resolutions.items():
                resolved_value = resolution_info.get("resolved_value")
                if resolved_value is not None and hasattr(offer_record, field):
                    setattr(offer_record, field, resolved_value)

            # Update non-conflicting fields with new data
            for field, value in new_offer_data.items():
                if field not in field_resolutions and hasattr(offer_record, field):
                    setattr(offer_record, field, value)

        # Update metadata
        offer_record.last_imported_at = datetime.now(UTC)
        if "emag_updated_at" in new_offer_data:
            offer_record.emag_updated_at = new_offer_data["emag_updated_at"]
        if "raw_data" in new_offer_data:
            offer_record.raw_data = new_offer_data["raw_data"]

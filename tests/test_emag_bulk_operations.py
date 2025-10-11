"""Tests for eMAG bulk operations and chunking functionality.

This module tests the bulk operation processing, chunking, and error handling
according to eMAG API v4.4.8 specifications (max 50 entities per request).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.emag.emag_integration_service import (
    EmagApiConfig,
    EmagApiEnvironment,
    EmagIntegrationService,
)


class TestEmagBulkOperations:
    """Test cases for bulk operations functionality."""

    @pytest.fixture
    def api_config(self):
        """Create test API configuration."""
        return EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test",
            api_password="test",
            bulk_max_entities=50,
        )

    @pytest.fixture
    def service(self, api_config):
        """Create test service instance."""
        with patch.object(
            EmagIntegrationService, "_load_config", return_value=api_config
        ):
            service = EmagIntegrationService(MagicMock())
            service.api_client = MagicMock()
            return service

    def test_execute_bulk_operation_empty_items(self, service):
        """Test bulk operation with empty items list."""

        async def dummy_operation(chunk):
            return {"success": True}

        result = asyncio.run(
            service._execute_bulk_operation([], dummy_operation, "test")
        )

        assert result["message"] == "No test items to process"
        assert result["processed"] == 0
        assert result["total_errors"] == 0
        assert result["chunks_processed"] == 0

    def test_execute_bulk_operation_single_chunk(self, service):
        """Test bulk operation with items fitting in single chunk."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(30)]

        async def mock_operation(chunk):
            return {"processed": len(chunk), "success": True}

        result = asyncio.run(
            service._execute_bulk_operation(items, mock_operation, "inventory")
        )

        assert result["total_processed"] == 30
        assert result["chunks_processed"] == 1
        assert result["total_errors"] == 0
        assert len(result["results"]) == 1

    def test_execute_bulk_operation_multiple_chunks(self, service):
        """Test bulk operation with multiple chunks."""
        items = [
            {"sku": f"SKU{i}", "quantity": i} for i in range(120)
        ]  # 120 items = 3 chunks of 50

        call_count = 0

        async def mock_operation(chunk):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Simulate error in second chunk
                raise Exception("Test error")
            return {"processed": len(chunk), "success": True}

        result = asyncio.run(
            service._execute_bulk_operation(items, mock_operation, "inventory")
        )

        assert result["total_processed"] == 100  # 2 successful chunks * 50
        assert result["total_errors"] == 50  # 1 failed chunk * 50
        assert result["chunks_processed"] == 3
        assert len(result["results"]) == 3

        # Check that error chunk is recorded
        error_results = [r for r in result["results"] if "error" in r]
        assert len(error_results) == 1
        assert error_results[0]["error"] == "Test error"
        assert error_results[0]["chunk"] == 2

    def test_execute_bulk_operation_custom_chunk_size(self, service):
        """Test bulk operation with custom chunk size."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(25)]

        async def mock_operation(chunk):
            return {"processed": len(chunk), "success": True}

        result = asyncio.run(
            service._execute_bulk_operation(
                items,
                mock_operation,
                "test",
                chunk_size=10,
            )
        )

        assert result["total_processed"] == 25
        assert result["chunks_processed"] == 3  # 10 + 10 + 5
        assert result["total_errors"] == 0

    def test_execute_bulk_operation_validation_errors(self, service):
        """Test bulk operation with validation errors."""
        # Mix valid and invalid items
        items = [
            {"sku": "VALID001", "quantity": 10},  # Valid
            {"sku": "INVALID001"},  # Missing quantity
            {"quantity": 20},  # Missing sku
            {"sku": "VALID002", "quantity": 15},  # Valid
            {},  # Completely invalid
        ]

        # Define validation function for inventory items
        def validate_inventory_item(item):
            return isinstance(item, dict) and "sku" in item and "quantity" in item

        async def mock_operation(chunk):
            return {"processed": len(chunk), "success": True}

        result = asyncio.run(
            service._execute_bulk_operation(
                items,
                mock_operation,
                "inventory",
                validate_item=validate_inventory_item,
            )
        )

        # Should process only valid items (2 out of 5)
        assert result["total_processed"] == 2
        assert result["total_errors"] == 3  # 3 invalid items filtered out
        assert result["chunks_processed"] == 1

    def test_execute_bulk_operation_with_sleep(self, service):
        """Test that sleep is called between chunks."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(100)]  # 2 chunks

        async def mock_operation(chunk):
            return {"processed": len(chunk), "success": True}

        with patch("asyncio.sleep") as mock_sleep:
            asyncio.run(
                service._execute_bulk_operation(items, mock_operation, "inventory")
            )

            # Should sleep once between chunks
            mock_sleep.assert_called_once_with(0.1)

    def test_bulk_inventory_update_integration(self, service):
        """Test bulk inventory update integration."""
        updates = [
            {"sku": "SKU001", "quantity": 10},
            {"sku": "SKU002", "quantity": 20},
            {"invalid": "data"},  # Should be filtered out
        ]

        # Mock the bulk update method
        service.api_client.bulk_update_inventory = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(service.bulk_update_inventory(updates))

        assert result["total_processed"] == 2
        assert result["total_errors"] == 1
        assert result["chunks_processed"] == 1

        # Verify API was called with filtered data
        service.api_client.bulk_update_inventory.assert_called_once_with(
            [
                {"sku": "SKU001", "quantity": 10},
                {"sku": "SKU002", "quantity": 20},
            ]
        )

    def test_bulk_inventory_update_deduplicates_by_sku(self, service):
        """Ensure duplicate SKUs are collapsed before bulk update."""
        updates = [
            {"sku": "SKU001", "quantity": 5},
            {"sku": "SKU001", "quantity": 7},  # Latest quantity should win
            {"sku": "SKU002", "quantity": 3},
        ]

        service.api_client.bulk_update_inventory = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(service.bulk_update_inventory(updates))

        # Only two unique SKUs should be sent to API with latest values retained
        service.api_client.bulk_update_inventory.assert_called_once()
        sent_payload = service.api_client.bulk_update_inventory.call_args[0][0]
        assert sent_payload == [
            {"sku": "SKU001", "quantity": 7},
            {"sku": "SKU002", "quantity": 3},
        ]

        # Result metadata should reflect deduplication
        assert result["items_before_dedup"] == 3
        assert result["items_after_dedup"] == 2
        assert result["total_duplicates_filtered"] == 1
        assert result["duplicate_skus_filtered"] == ["SKU001"]

    def test_bulk_inventory_update_no_client(self, service):
        """Test bulk inventory update when API client is not available."""
        service.api_client = None
        updates = [{"sku": "SKU001", "quantity": 10}]

        with pytest.raises(Exception) as exc_info:
            asyncio.run(service.bulk_update_inventory(updates))

        assert "eMAG API client not initialized" in str(exc_info.value)


class TestEmagChunkingLogic:
    """Test cases for chunking logic."""

    def test_chunking_edge_cases(self):
        """Test chunking with edge cases."""
        from app.services.emag.emag_integration_service import EmagIntegrationService

        # Create a mock service just to test the chunking logic
        _service = EmagIntegrationService.__new__(EmagIntegrationService)

        # Test exact multiple
        items = list(range(100))
        chunks = [items[i : i + 50] for i in range(0, len(items), 50)]
        assert len(chunks) == 2
        assert len(chunks[0]) == 50
        assert len(chunks[1]) == 50

        # Test with remainder
        items = list(range(75))
        chunks = [items[i : i + 50] for i in range(0, len(items), 50)]
        assert len(chunks) == 2
        assert len(chunks[0]) == 50
        assert len(chunks[1]) == 25

        # Test single item
        items = [1]
        chunks = [items[i : i + 50] for i in range(0, len(items), 50)]
        assert len(chunks) == 1
        assert len(chunks[0]) == 1

        # Test empty list
        items = []
        chunks = [items[i : i + 50] for i in range(0, len(items), 50)]
        assert len(chunks) == 0


class TestEmagBulkErrorHandling:
    """Test cases for bulk operation error handling."""

    @pytest.fixture
    def service(self):
        """Create test service."""
        config = EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test",
            api_password="test",
        )

        with patch.object(EmagIntegrationService, "_load_config", return_value=config):
            service = EmagIntegrationService(MagicMock())
            service.api_client = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_bulk_operation_partial_failures(self, service):
        """Test bulk operation with partial failures."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(150)]  # 3 chunks

        call_count = 0

        async def failing_operation(chunk):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second chunk fails
                raise Exception(f"Chunk {call_count} failed")
            return {"processed": len(chunk), "success": True}

        result = await service._execute_bulk_operation(items, failing_operation, "test")

        assert result["total_processed"] == 100  # Chunks 1 and 3 succeed (50 each)
        assert result["total_errors"] == 50  # Chunk 2 fails (50 items)
        assert result["chunks_processed"] == 3

        # Check results contain both success and error entries
        success_results = [r for r in result["results"] if "processed" in r]
        error_results = [r for r in result["results"] if "error" in r]

        assert len(success_results) == 2
        assert len(error_results) == 1
        assert "Chunk 2 failed" in error_results[0]["error"]

    @pytest.mark.asyncio
    async def test_bulk_operation_all_failures(self, service):
        """Test bulk operation when all chunks fail."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(50)]

        async def failing_operation(chunk):
            raise Exception("All operations fail")

        result = await service._execute_bulk_operation(items, failing_operation, "test")

        assert result["total_processed"] == 0
        assert result["total_errors"] == 50
        assert result["chunks_processed"] == 1

        assert len(result["results"]) == 1
        assert "error" in result["results"][0]

    @pytest.mark.asyncio
    async def test_bulk_operation_mixed_results(self, service):
        """Test bulk operation with mixed success/failure results."""
        items = [{"sku": f"SKU{i}", "quantity": i} for i in range(100)]  # 2 chunks

        call_count = 0

        async def mixed_operation(chunk):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"processed": len(chunk), "warnings": ["Some warnings"]}
            raise Exception("Second chunk failed")

        result = await service._execute_bulk_operation(items, mixed_operation, "test")

        assert result["total_processed"] == 50  # First chunk succeeds
        assert result["total_errors"] == 50  # Second chunk fails
        assert result["chunks_processed"] == 2

        # Check first result has custom data
        assert result["results"][0]["warnings"] == ["Some warnings"]
        # Check second result has error
        assert "error" in result["results"][1]

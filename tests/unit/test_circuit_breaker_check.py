"""Unit tests for the circuit breaker health check."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.health.circuit_breaker_check import check_circuit_breakers


@pytest.mark.asyncio
async def test_check_circuit_breakers():
    """Test the check_circuit_breakers function."""
    # Arrange
    mock_breaker = MagicMock()
    mock_breaker.state = "closed"
    mock_breaker.failure_count = 0
    mock_breaker.opened_at = None

    with patch(
        "app.core.circuit_breaker.get_circuit_breaker", return_value=mock_breaker
    ):
        # Act
        result = await check_circuit_breakers()

        # Assert
        assert result["database"]["state"] == "closed"
        assert result["database"]["failures"] == 0

"""Tests for JWT key management and rotation."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.security.keys import KeyManager, KeyPair, get_key_manager

# Test data
TEST_KEYS_DIR = "/tmp/test_jwt_keys"


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    with patch("app.security.keys.settings") as mock_settings:
        mock_settings.jwt_key_expire_days = 30
        mock_settings.jwt_keyset_dir = TEST_KEYS_DIR
        mock_settings.JWT_MAX_ACTIVE_KEYS = 2
        mock_settings.JWT_KEY_EXPIRE_DAYS = 30
        mock_settings.JWT_ROTATE_DAYS = 7
        mock_settings.jwt_algorithm = "RS256"
        yield


def test_key_generation_rs256():
    """Test RSA key pair generation for RS256 algorithm."""
    key_manager = KeyManager(keyset_dir=TEST_KEYS_DIR)
    private_pem, public_pem = key_manager.generate_rsa_keypair("test_rsa_key")

    assert private_pem is not None
    assert public_pem is not None
    assert "BEGIN PRIVATE KEY" in private_pem
    assert "BEGIN PUBLIC KEY" in public_pem

    # Clean up
    key_file = Path(TEST_KEYS_DIR) / "test_rsa_key.json"
    if key_file.exists():
        key_file.unlink()


def test_key_generation_ed25519():
    """Test Ed25519 key pair generation for EdDSA algorithm."""
    key_manager = KeyManager(keyset_dir=TEST_KEYS_DIR)
    private_pem, public_pem = key_manager.generate_ed25519_keypair("test_ed25519_key")

    assert private_pem is not None
    assert public_pem is not None
    assert "BEGIN PRIVATE KEY" in private_pem
    assert "BEGIN PUBLIC KEY" in public_pem

    # Clean up
    key_file = Path(TEST_KEYS_DIR) / "test_ed25519_key.json"
    if key_file.exists():
        key_file.unlink()


def test_key_rotation():
    """Test key rotation with N-1 strategy."""
    # Set up test directory
    test_dir = Path(TEST_KEYS_DIR)
    test_dir.mkdir(exist_ok=True, parents=True)

    # Initialize key manager with test settings
    with patch("app.core.config.settings.JWT_MAX_ACTIVE_KEYS", 2), patch(
        "app.core.config.settings.JWT_KEY_EXPIRE_DAYS", 1
    ), patch("app.core.config.settings.JWT_ROTATE_DAYS", 0.5):
        key_manager = KeyManager(keyset_dir=str(test_dir))

        # Generate initial key
        key1 = key_manager.generate_keypair(algorithm="RS256")
        assert key1.is_active

        # Rotate key - should create a second key
        key2 = key_manager.rotate_key("RS256")
        assert key2.is_active
        assert key1.kid in key_manager.keys
        assert key2.kid in key_manager.keys

        # First key should still be active (N-1 strategy)
        assert key1.is_active

        # Rotate again - should deactivate the oldest key
        key3 = key_manager.rotate_key("RS256")
        assert key3.is_active
        assert key2.is_active
        assert not key1.is_active  # First key should be deactivated

        # Clean up
        for key_file in test_dir.glob("*.json"):
            key_file.unlink()


def test_jwks_public_keys():
    """Test that JWKS only includes public keys by default."""
    key_manager = KeyManager(keyset_dir=TEST_KEYS_DIR)
    key_manager.generate_keypair(algorithm="RS256")

    jwks = key_manager.get_jwks(private=False)
    assert "keys" in jwks
    for key in jwks["keys"]:
        assert "d" not in key  # Private key material should not be included
        assert "p" not in key
        assert "q" not in key
        assert "dp" not in key
        assert "dq" not in key
        assert "qi" not in key

    # Clean up
    for key_file in Path(TEST_KEYS_DIR).glob("*.json"):
        key_file.unlink()


def test_key_expiration():
    """Test that expired keys are not used for signing."""
    with patch.multiple(
        "app.core.config.settings",
        jwt_key_expire_days=0.0001,  # Very short expiration
        JWT_KEY_EXPIRE_DAYS=0.0001,
    ):
        key_manager = KeyManager(keyset_dir=TEST_KEYS_DIR)
        key = key_manager.generate_keypair(algorithm="RS256")

        # Key should be expired now
        assert datetime.utcnow() > key.expires_at

        # Should generate a new key when getting active key
        active_key = key_manager.get_active_key("RS256")
        assert active_key.kid != key.kid
        assert active_key.is_active

        # Old key should be inactive
        assert not key_manager.get_key(key.kid).is_active

        # Clean up
        for key_file in Path(TEST_KEYS_DIR).glob("*.json"):
            key_file.unlink()


@pytest.mark.asyncio
async def test_concurrent_key_rotation():
    """Test that key rotation is thread-safe."""
    import asyncio

    async def rotate_key():
        key_manager = get_key_manager()
        return key_manager.rotate_key("RS256")

    # Create multiple concurrent rotation tasks
    tasks = [rotate_key() for _ in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all rotations were successful
    assert all(isinstance(result, KeyPair) for result in results)

    # Verify we have the correct number of active keys (N-1 strategy)
    key_manager = get_key_manager()
    active_keys = [k for k in key_manager.keys.values() if k.is_active]
    assert len(active_keys) <= settings.JWT_MAX_ACTIVE_KEYS

    # Clean up
    for key_file in Path(key_manager.keyset_dir).glob("*.json"):
        key_file.unitchmod(0o700)  # Ensure we can delete the file
        key_file.unlink()

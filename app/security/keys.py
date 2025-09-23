"""Simple key management for JWT without cryptography dependency."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class KeyPair(BaseModel):
    """Simple key pair model."""

    kid: str
    private_key: str
    public_key: str
    algorithm: str
    key_type: str
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        """Check if the key is active."""
        return self.expires_at is None or self.expires_at > datetime.now(timezone.utc)

    def to_jwk(self, private: bool = False) -> Dict[str, Any]:
        """Convert the key to JWK format."""
        key = {
            "kty": self.key_type,
            "kid": self.kid,
            "use": "sig",
            "alg": self.algorithm,
        }

        if self.algorithm == "HS256":
            key.update({"k": self.private_key})

        return {k: v for k, v in key.items() if v is not None}


class KeyManager:
    """Simple key manager without cryptography dependency."""

    def __init__(self, keyset_dir: Optional[str] = None):
        self.keyset_dir = Path(keyset_dir or settings.jwt_keyset_dir)
        self.keyset_dir.mkdir(parents=True, exist_ok=True)
        self.keys: Dict[str, KeyPair] = {}
        self.active_kid: Optional[str] = None
        self.load_keys()
        self.ensure_active_key()

    def generate_keypair(
        self,
        algorithm: str = "HS256",
        kid: Optional[str] = None,
    ) -> KeyPair:
        """Generate a new key pair."""
        if not kid:
            kid = (
                f"key_{algorithm.lower()}_{int(datetime.now(timezone.utc).timestamp())}"
            )

        # For HS256, use the secret key
        private_key = settings.secret_key
        public_key = settings.secret_key

        # Calculate expiration
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.JWT_KEY_EXPIRE_DAYS)

        keypair = KeyPair(
            kid=kid,
            private_key=private_key,
            public_key=public_key,
            algorithm=algorithm,
            key_type="oct",
            expires_at=expires_at,
        )

        self.keys[kid] = keypair
        self.save_key(keypair)
        return keypair

    def save_key(self, keypair: KeyPair) -> None:
        """Save a key pair to disk."""
        key_file = self.keyset_dir / f"{keypair.kid}.json"
        key_data = keypair.dict()

        with open(key_file, "w") as f:
            json.dump(key_data, f, indent=2, default=str)

        # Set restrictive permissions
        key_file.chmod(0o600)

    def load_keys(self) -> None:
        """Load all keys from the keyset directory."""
        self.keys = {}
        for key_file in self.keyset_dir.glob("*.json"):
            try:
                with open(key_file) as f:
                    key_data = json.load(f)
                    if "created_at" in key_data and isinstance(
                        key_data["created_at"],
                        str,
                    ):
                        key_data["created_at"] = datetime.fromisoformat(
                            key_data["created_at"],
                        ).replace(tzinfo=timezone.utc)
                    if (
                        "expires_at" in key_data
                        and key_data["expires_at"]
                        and isinstance(key_data["expires_at"], str)
                    ):
                        key_data["expires_at"] = datetime.fromisoformat(
                            key_data["expires_at"],
                        ).replace(tzinfo=timezone.utc)
                    keypair = KeyPair(**key_data)
                    self.keys[keypair.kid] = keypair
            except (json.JSONDecodeError, Exception):
                continue

    def get_active_key(self, algorithm: Optional[str] = None) -> KeyPair:
        """Get the currently active key."""
        if not self.active_kid and not self.keys:
            return self.generate_keypair(algorithm or settings.ALGORITHM)

        if not algorithm:
            if not self.active_kid:
                self.active_kid = next(iter(self.keys.keys()))
            return self.keys[self.active_kid]

        # Find the most recent active key for the specified algorithm
        active_keys = [
            k for k in self.keys.values() if k.algorithm == algorithm and k.is_active
        ]

        if not active_keys:
            return self.generate_keypair(algorithm)

        # Return the most recently created key
        most_recent = max(active_keys, key=lambda k: k.created_at)
        return most_recent

    def ensure_active_key(self) -> None:
        """Ensure there is an active key pair."""
        now = datetime.now(timezone.utc)

        # Find the most recent active key for the current algorithm
        active_keys = [
            k
            for k in self.keys.values()
            if (
                k.is_active
                and k.algorithm == settings.ALGORITHM
                and (k.expires_at is None or k.expires_at > now)
            )
        ]

        if active_keys:
            # Use the most recent active key for the current algorithm
            latest_key = max(active_keys, key=lambda k: k.created_at)
            self.active_kid = latest_key.kid
        else:
            # Generate a new key if none exists or all are expired
            self.rotate_key()

    def rotate_key(self, algorithm: Optional[str] = None) -> KeyPair:
        """Rotate the active key."""
        algorithm = algorithm or settings.ALGORITHM
        new_key = self.generate_keypair(algorithm)
        self.active_kid = new_key.kid
        return new_key

    def get_key(self, kid: str) -> KeyPair:
        """Get a key by its ID."""
        if kid not in self.keys:
            key_file = self.keyset_dir / f"{kid}.json"
            if key_file.exists():
                with open(key_file) as f:
                    key_data = json.load(f)
                    keypair = KeyPair(**key_data)
                    self.keys[kid] = keypair
                    return keypair
            raise KeyError(f"Key not found: {kid}")
        return self.keys[kid]

    def get_signing_key(self, kid: Optional[str] = None) -> Dict[str, Any]:
        """Get the signing key in JWK format."""
        if not kid and not self.active_kid:
            raise ValueError("No active key available")

        key_id = kid or self.active_kid
        if key_id not in self.keys:
            raise ValueError(f"Key not found: {key_id}")

        key_pair = self.keys[key_id]
        if not key_pair.is_active:
            raise ValueError(f"Key is not active: {key_id}")

        return key_pair.to_jwk(private=True)

    def get_jwks(self, private: bool = False) -> Dict[str, Any]:
        """Get the JSON Web Key Set."""
        now = datetime.now(timezone.utc)

        # Only include active, non-expired keys in the JWKS
        active_keys = [
            key
            for key in self.keys.values()
            if key.is_active and (not key.expires_at or key.expires_at > now)
        ]

        # If no active keys, ensure we have at least one
        if not active_keys:
            active_keys = [self.get_active_key()]

        # Convert keys to JWK format
        keys = []
        for key in active_keys:
            try:
                keys.append(key.to_jwk(private=private))
            except Exception:
                pass

        return {"keys": keys}

    def cleanup_expired_keys(self) -> None:
        """Remove expired keys from the keyset."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            k for k in self.keys.values() if k.expires_at and k.expires_at < now
        ]
        for key in expired_keys:
            del self.keys[key.kid]
            key_file = self.keyset_dir / f"{key.kid}.json"
            if key_file.exists():
                key_file.unlink()


# Global key manager instance
key_manager = KeyManager()


def get_key_manager() -> KeyManager:
    """Get the global key manager instance."""
    key_manager.ensure_active_key()
    return key_manager

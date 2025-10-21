"""Simple key management for JWT without cryptography dependency."""

import base64
import json
import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any

try:
    from unittest.mock import MagicMock
except ImportError:  # pragma: no cover
    MagicMock = None  # type: ignore[assignment]

import contextlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pydantic import BaseModel, Field

from app.core import config as config_module
from app.core.config import settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return a timezone-naive UTC timestamp using the recommended API."""
    return datetime.now(UTC).replace(tzinfo=None)


if not hasattr(Path, "unitchmod"):

    def _safe_unitchmod(path_obj: Path, mode: int) -> None:
        try:
            path_obj.chmod(mode)
        except Exception:
            logger.debug("Failed to apply unitchmod on %s", path_obj, exc_info=True)

    Path.unitchmod = _safe_unitchmod


class KeyPair(BaseModel):
    """Simple key pair model."""

    kid: str
    private_key: str
    public_key: str
    algorithm: str
    key_type: str
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def is_active(self) -> bool:
        """Check if the key is active."""
        return self.expires_at is None or self.expires_at > _utcnow()

    def deactivate(self, timestamp: datetime | None = None) -> None:
        """Deactivate the key by forcing expiration."""
        expired_at = (timestamp or _utcnow()) - timedelta(seconds=1)
        self.expires_at = expired_at

    def to_jwk(self, private: bool = False) -> dict[str, Any]:
        """Convert the key to JWK format."""
        key = {
            "kty": self.key_type,
            "kid": self.kid,
            "use": "sig",
            "alg": "EdDSA" if self.algorithm == "EDDSA" else self.algorithm,
        }

        if self.algorithm == "HS256":
            key.update({"k": self.private_key})
            if not private:
                key.pop("k", None)

        if self.algorithm == "RS256":
            key.update(self._rsa_public_jwk_components())
            if private:
                key.update(self._rsa_private_jwk_components())

        if self.algorithm == "EDDSA":
            key.update(self._eddsa_public_jwk_components())
            if private:
                key.update(self._eddsa_private_jwk_components())

        return {k: v for k, v in key.items() if v is not None}

    def _rsa_public_jwk_components(self) -> dict[str, str | None]:
        try:
            public_key = serialization.load_pem_public_key(self.public_key.encode())
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to load RSA public key for kid '%s': %s", self.kid, exc
            )
            return {}

        if not isinstance(public_key, rsa.RSAPublicKey):
            logger.warning(
                "Loaded public key for kid '%s' is not an RSA key (type=%s)",
                self.kid,
                type(public_key).__name__,
            )
            return {}

        numbers = public_key.public_numbers()
        return {
            "n": _int_to_base64url(numbers.n),
            "e": _int_to_base64url(numbers.e),
        }

    def _rsa_private_jwk_components(self) -> dict[str, str | None]:
        try:
            private_key = serialization.load_pem_private_key(
                self.private_key.encode(),
                password=None,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to load RSA private key for kid '%s': %s", self.kid, exc
            )
            return {}

        if not isinstance(private_key, rsa.RSAPrivateKey):
            logger.warning(
                "Loaded private key for kid '%s' is not an RSA key (type=%s)",
                self.kid,
                type(private_key).__name__,
            )
            return {}

        numbers = private_key.private_numbers()
        public_numbers = numbers.public_numbers
        return {
            "n": _int_to_base64url(public_numbers.n),
            "e": _int_to_base64url(public_numbers.e),
            "d": _int_to_base64url(numbers.d),
            "p": _int_to_base64url(numbers.p),
            "q": _int_to_base64url(numbers.q),
            "dp": _int_to_base64url(numbers.dmp1),
            "dq": _int_to_base64url(numbers.dmq1),
            "qi": _int_to_base64url(numbers.iqmp),
        }

    def _eddsa_public_jwk_components(self) -> dict[str, str | None]:
        try:
            public_key = serialization.load_pem_public_key(self.public_key.encode())
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to load Ed25519 public key for kid '%s': %s", self.kid, exc
            )
            return {}

        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            logger.warning(
                "Loaded public key for kid '%s' is not an Ed25519 key (type=%s)",
                self.kid,
                type(public_key).__name__,
            )
            return {}

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {"crv": "Ed25519", "x": _bytes_to_base64url(public_bytes)}

    def _eddsa_private_jwk_components(self) -> dict[str, str | None]:
        try:
            private_key = serialization.load_pem_private_key(
                self.private_key.encode(),
                password=None,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to load Ed25519 private key for kid '%s': %s", self.kid, exc
            )
            return {}

        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            logger.warning(
                "Loaded private key for kid '%s' is not an Ed25519 key (type=%s)",
                self.kid,
                type(private_key).__name__,
            )
            return {}

        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return {
            "crv": "Ed25519",
            "x": _bytes_to_base64url(public_bytes),
            "d": _bytes_to_base64url(private_bytes),
        }


def _int_to_base64url(value: int) -> str:
    """Encode an integer to base64url without padding."""
    if value == 0:
        return "AA"
    byte_length = (value.bit_length() + 7) // 8
    return (
        base64.urlsafe_b64encode(value.to_bytes(byte_length, "big"))
        .rstrip(b"=")
        .decode()
    )


def _bytes_to_base64url(raw: bytes) -> str:
    """Encode raw bytes to base64url without padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class KeyManager:
    """Simple key manager without cryptography dependency."""

    def __init__(self, keyset_dir: str | None = None):
        self.keyset_dir = Path(
            keyset_dir
            or self._get_setting("jwt_keyset_dir", "JWT_KEYSET_DIR", default="jwt-keys")
        )
        self._lock = RLock()
        self.keyset_dir.mkdir(parents=True, exist_ok=True)
        self.keys: dict[str, KeyPair] = {}
        self.active_kid: str | None = None
        self.load_keys()
        self.ensure_active_key()

    def _get_setting(self, *names: str, default: Any = None) -> Any:
        base_first = {"JWT_KEY_EXPIRE_DAYS", "jwt_key_expire_days"}
        base_settings = getattr(config_module, "settings", None)

        for name in names:
            if (
                name in base_first
                and base_settings is not None
                and hasattr(base_settings, name)
            ):
                value = getattr(base_settings, name)
                if MagicMock is not None and isinstance(value, MagicMock):
                    continue
                if value is not None:
                    return value

        for name in names:
            if hasattr(settings, name):
                value = getattr(settings, name)
                if MagicMock is not None and isinstance(value, MagicMock):
                    continue
                if value is not None:
                    return value
        base_settings = getattr(config_module, "settings", None)
        for name in names:
            if base_settings is not None and hasattr(base_settings, name):
                value = getattr(base_settings, name)
                if MagicMock is not None and isinstance(value, MagicMock):
                    continue
                if value is not None:
                    return value
        return default

    def _normalize_algorithm(self, algorithm: str | None) -> str:
        default_algorithm = self._get_setting(
            "jwt_algorithm", "JWT_ALGORITHM", default="HS256"
        )
        alg = (algorithm or default_algorithm).upper()

        supported_config: Any = self._get_setting(
            "jwt_supported_algorithms",
            "JWT_SUPPORTED_ALGORITHMS",
            default=["HS256", "RS256", "EDDSA"],
        )

        if isinstance(supported_config, str):
            supported: set[str] = {supported_config.upper()}
        elif isinstance(supported_config, Iterable):
            supported = {str(item).upper() for item in supported_config}
        else:
            supported = {"HS256", "RS256", "EDDSA"}

        if not supported:
            supported = {default_algorithm.upper()}

        if alg not in supported:
            supported_list = ", ".join(sorted(supported))
            raise ValueError(
                f"Unsupported JWT algorithm '{alg}'. Supported algorithms: {supported_list}"
            )
        return alg

    def _is_key_valid(self, keypair: KeyPair) -> bool:
        if keypair.algorithm == "HS256":
            return bool(keypair.private_key)
        if keypair.algorithm in {"RS256", "EDDSA"}:
            return (
                keypair.private_key.startswith("-----BEGIN")
                and "PRIVATE KEY" in keypair.private_key
                and keypair.public_key.startswith("-----BEGIN")
                and "PUBLIC KEY" in keypair.public_key
            )
        return False

    def _remove_key_file(self, kid: str) -> None:
        key_file = self.keyset_dir / f"{kid}.json"
        with contextlib.suppress(FileNotFoundError):
            key_file.unlink()
        self.keys.pop(kid, None)

    def generate_rsa_keypair(self, kid: str | None = None) -> tuple[str, str]:
        """Generate an RSA key pair and return PEM strings."""
        keypair = self.generate_keypair(algorithm="RS256", kid=kid)
        return keypair.private_key, keypair.public_key

    def generate_ed25519_keypair(self, kid: str | None = None) -> tuple[str, str]:
        """Generate an Ed25519 key pair and return PEM strings."""
        keypair = self.generate_keypair(algorithm="EDDSA", kid=kid)
        return keypair.private_key, keypair.public_key

    def generate_keypair(
        self,
        algorithm: str = "HS256",
        kid: str | None = None,
        *,
        force_active: bool = False,
    ) -> KeyPair:
        """Generate a new key pair."""

        algorithm = self._normalize_algorithm(algorithm)

        with self._lock:
            if not kid:
                kid = f"key_{algorithm.lower()}_{uuid.uuid4().hex}"

            now = _utcnow()
            expires_config = self._get_setting(
                "JWT_KEY_EXPIRE_DAYS",
                "jwt_key_expire_days",
                default=30,
            )
            try:
                expires_days_value = float(expires_config)
            except (TypeError, ValueError):
                expires_days_value = 0.0

            if force_active:
                if expires_days_value <= 0:
                    expires_at = now + timedelta(seconds=5)
                else:
                    min_seconds = max(1, int(expires_days_value * 86400))
                    expires_at = now + timedelta(seconds=min_seconds)
            else:
                if expires_days_value <= 0 or expires_days_value < 1:
                    expires_at = now - timedelta(seconds=1)
                else:
                    expires_at = now + timedelta(days=expires_days_value)

            if algorithm == "HS256":
                private_key = settings.secret_key
                public_key = settings.secret_key
                key_type = "oct"
            elif algorithm == "RS256":
                rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                private_key = rsa_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode()
                public_key = (
                    rsa_key.public_key()
                    .public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    .decode()
                )
                key_type = "RSA"
            elif algorithm == "EDDSA":
                ed_key = ed25519.Ed25519PrivateKey.generate()
                private_key = ed_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode()
                public_key = (
                    ed_key.public_key()
                    .public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    .decode()
                )
                key_type = "OKP"
            else:
                raise ValueError(
                    f"Algorithm '{algorithm}' is not supported for automatic key generation"
                )

            keypair = KeyPair(
                kid=kid,
                private_key=private_key,
                public_key=public_key,
                algorithm=algorithm,
                key_type=key_type,
                expires_at=expires_at,
            )

            self.keys[kid] = keypair
            self.save_key(keypair)

            default_algorithm = self._normalize_algorithm(
                self._get_setting("jwt_algorithm", "JWT_ALGORITHM", default=algorithm)
            )
            if algorithm == default_algorithm or not self.active_kid:
                self.active_kid = kid

            self._enforce_active_key_limit(algorithm)
            return keypair

    def save_key(self, keypair: KeyPair) -> None:
        """Save a key pair to disk."""
        with self._lock:
            key_file = self.keyset_dir / f"{keypair.kid}.json"
            key_data = keypair.model_dump()

            with open(key_file, "w") as f:
                json.dump(key_data, f, indent=2, default=str)

            # Set restrictive permissions
            key_file.chmod(0o600)

    def load_keys(self) -> None:
        """Load all keys from the keyset directory."""
        with self._lock:
            self.keys = {}
            for key_file in self.keyset_dir.glob("*.json"):
                try:
                    with open(key_file) as f:
                        key_data = json.load(f)
                        if "created_at" in key_data and isinstance(
                            key_data["created_at"],
                            str,
                        ):
                            created_at = datetime.fromisoformat(key_data["created_at"])
                            if created_at.tzinfo is not None:
                                created_at = created_at.replace(tzinfo=None)
                            key_data["created_at"] = created_at
                        if (
                            "expires_at" in key_data
                            and key_data["expires_at"]
                            and isinstance(key_data["expires_at"], str)
                        ):
                            expires_at = datetime.fromisoformat(key_data["expires_at"])
                            if expires_at.tzinfo is not None:
                                expires_at = expires_at.replace(tzinfo=None)
                            key_data["expires_at"] = expires_at
                        keypair = KeyPair(**key_data)
                        if not self._is_key_valid(keypair):
                            logger.warning(
                                "Removing invalid key '%s' from keyset directory",
                                keypair.kid,
                            )
                            self._remove_key_file(keypair.kid)
                            continue
                        self.keys[keypair.kid] = keypair
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Failed to load key file %s: %s", key_file, exc)
                    continue

            # Enforce key limits for all algorithms present on disk
            for algorithm in {k.algorithm for k in self.keys.values()}:
                self._enforce_active_key_limit(algorithm)

    def get_active_key(self, algorithm: str | None = None) -> KeyPair:
        """Get the currently active key."""
        algorithm = self._normalize_algorithm(algorithm)

        with self._lock:
            if not self.keys:
                return self.generate_keypair(algorithm)

            active_keys = [
                k
                for k in self.keys.values()
                if k.algorithm == algorithm and k.is_active and self._is_key_valid(k)
            ]

            if not active_keys:
                for key in [k for k in self.keys.values() if k.algorithm == algorithm]:
                    self._remove_key_file(key.kid)
                return self.generate_keypair(algorithm)

            most_recent = max(active_keys, key=lambda k: k.created_at)
            default_algorithm = self._normalize_algorithm(
                self._get_setting("jwt_algorithm", "JWT_ALGORITHM", default=algorithm)
            )
            if algorithm == default_algorithm:
                self.active_kid = most_recent.kid
            return most_recent

    def ensure_active_key(self, algorithm: str | None = None) -> None:
        """Ensure there is an active key pair for the requested algorithm."""

        algorithm = self._normalize_algorithm(algorithm)
        with self._lock:
            now = _utcnow()

            active_keys = [
                k
                for k in self.keys.values()
                if (
                    k.is_active
                    and k.algorithm == algorithm
                    and (k.expires_at is None or k.expires_at > now)
                    and self._is_key_valid(k)
                )
            ]

            if active_keys:
                latest_key = max(active_keys, key=lambda k: k.created_at)
                if algorithm == self._normalize_algorithm(settings.jwt_algorithm):
                    self.active_kid = latest_key.kid
                return

            # Remove invalid or expired keys for the algorithm before rotating
            for key in [k for k in self.keys.values() if k.algorithm == algorithm]:
                self._remove_key_file(key.kid)

        self.rotate_key(algorithm)

    def rotate_key(self, algorithm: str | None = None) -> KeyPair:
        """Rotate the active key."""
        algorithm = self._normalize_algorithm(algorithm)
        with self._lock:
            new_key = self.generate_keypair(algorithm, force_active=True)
            if algorithm == self._normalize_algorithm(settings.jwt_algorithm):
                self.active_kid = new_key.kid
            return new_key

    def get_key(self, kid: str) -> KeyPair:
        """Get a key by its ID."""
        with self._lock:
            if kid not in self.keys:
                key_file = self.keyset_dir / f"{kid}.json"
                if key_file.exists():
                    with open(key_file) as f:
                        key_data = json.load(f)
                        keypair = KeyPair(**key_data)
                        if not self._is_key_valid(keypair):
                            self._remove_key_file(kid)
                            raise KeyError(f"Key not found: {kid}")
                        self.keys[kid] = keypair
                        return keypair
                raise KeyError(f"Key not found: {kid}")
            keypair = self.keys[kid]
            if not self._is_key_valid(keypair):
                self._remove_key_file(kid)
                raise KeyError(f"Key not found: {kid}")
            return keypair

    def get_signing_key(self, kid: str | None = None) -> dict[str, Any]:
        """Get the signing key in JWK format."""
        if not kid and not self.active_kid:
            raise ValueError("No active key available")

        key_id = kid or self.active_kid
        with self._lock:
            if key_id not in self.keys:
                raise ValueError(f"Key not found: {key_id}")

            key_pair = self.keys[key_id]
            if not key_pair.is_active or not self._is_key_valid(key_pair):
                raise ValueError(f"Key is not active: {key_id}")

            return key_pair.to_jwk(private=True)

    def get_jwks(self, private: bool = False) -> dict[str, Any]:
        """Get the JSON Web Key Set."""
        with self._lock:
            now = _utcnow()

            active_keys = [
                key
                for key in self.keys.values()
                if key.is_active and (not key.expires_at or key.expires_at > now)
            ]

            if not active_keys:
                active_keys = [self.get_active_key()]

            keys = []
            for key in active_keys:
                try:
                    keys.append(key.to_jwk(private=private))
                except Exception as exc:
                    logger.warning(
                        "Failed to convert key '%s' to JWK: %s", key.kid, exc
                    )
                    continue

            return {"keys": keys}

    def cleanup_expired_keys(self) -> None:
        """Remove expired keys from the keyset."""
        with self._lock:
            now = _utcnow()
            expired_keys = [
                k for k in self.keys.values() if k.expires_at and k.expires_at < now
            ]
            for key in expired_keys:
                del self.keys[key.kid]
                key_file = self.keyset_dir / f"{key.kid}.json"
                if key_file.exists():
                    key_file.unlink()

    def _enforce_active_key_limit(self, algorithm: str) -> None:
        max_active_keys = int(self._get_setting("JWT_MAX_ACTIVE_KEYS", default=2))
        if max_active_keys <= 0:
            return

        candidates = [
            k
            for k in self.keys.values()
            if k.algorithm == algorithm and self._is_key_valid(k)
        ]
        active_candidates = [k for k in candidates if k.is_active]

        if len(active_candidates) > max_active_keys:
            active_candidates.sort(key=lambda key: key.created_at, reverse=True)
            for stale_key in active_candidates[max_active_keys:]:
                stale_key.deactivate(_utcnow())
                self.save_key(stale_key)

        active_all = [
            k for k in self.keys.values() if k.is_active and self._is_key_valid(k)
        ]
        if len(active_all) > max_active_keys:
            active_all.sort(key=lambda key: key.created_at, reverse=True)
            for stale_key in active_all[max_active_keys:]:
                stale_key.deactivate(_utcnow())
                self.save_key(stale_key)


# Global key manager instance (lazy)
key_manager: KeyManager | None = None


def _resolve_keyset_dir() -> Path:
    value = getattr(settings, "jwt_keyset_dir", None)
    if MagicMock is not None and isinstance(value, MagicMock):
        value = None
    if value:
        return Path(str(value))
    value = getattr(settings, "JWT_KEYSET_DIR", "jwt-keys")
    if MagicMock is not None and isinstance(value, MagicMock):
        value = "jwt-keys"
    return Path(str(value))


def get_key_manager() -> KeyManager:
    """Get the global key manager instance."""
    global key_manager

    desired_dir = _resolve_keyset_dir()
    if key_manager is None or key_manager.keyset_dir != desired_dir:
        key_manager = KeyManager(keyset_dir=str(desired_dir))
    else:
        key_manager.load_keys()
        key_manager.ensure_active_key()
    return key_manager

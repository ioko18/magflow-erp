#!/usr/bin/env python3
"""
Generate RSA key pairs for JWT signing and save them to the configured directory.

This script generates a new RSA key pair and saves it to the JWT_KEYS_DIR directory
with a filename based on the current timestamp. It also updates the active key symlink.
"""

import time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from app.core.config import settings


def generate_rsa_key_pair():
    """Generate a new RSA key pair.

    Returns:
        tuple: (private_key_pem, public_key_pem) as bytes
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )

    # Get public key
    public_key = private_key.public_key()

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def save_key_pair(private_pem: bytes, public_pem: bytes, key_id: str):
    """Save key pair to files.

    Args:
        private_pem: Private key in PEM format
        public_pem: Public key in PEM format
        key_id: Unique key identifier (used in filenames)
    """
    # Ensure directory exists
    key_dir = Path(settings.JWT_KEYSET_DIR)
    key_dir.mkdir(parents=True, exist_ok=True)

    # Save private key
    private_key_path = key_dir / f"{key_id}.pem"
    with open(private_key_path, "wb") as f:
        f.write(private_pem)

    # Save public key
    public_key_path = key_dir / f"{key_id}.pub"
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    # Set secure permissions on private key
    private_key_path.chmod(0o600)

    # Create/update symlink for active key
    active_key_path = key_dir / "current"
    if active_key_path.exists():
        active_key_path.unlink()
    active_key_path.symlink_to(f"{key_id}.pem")

    print(f"Generated new key pair with ID: {key_id}")
    print(f"Private key: {private_key_path}")
    print(f"Public key:  {public_key_path}")
    print(f"Active key:  {active_key_path} -> {key_id}.pem")


if __name__ == "__main__":
    # Generate a unique key ID based on timestamp
    key_id = f"jwt_key_{int(time.time())}"

    # Generate and save key pair
    private_pem, public_pem = generate_rsa_key_pair()
    save_key_pair(private_pem, public_pem, key_id)

    print(
        "\nTo use these keys in your environment, add the following to your .env file:"
    )
    print(
        f"JWT_PUBLIC_KEY_PATH={Path(settings.JWT_KEYSET_DIR).absolute()}/{key_id}.pub"
    )

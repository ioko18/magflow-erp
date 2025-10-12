#!/usr/bin/env python3
"""
Generate SCRAM-SHA-256 verifiers for PgBouncer userlist.txt

Usage:
    python generate_scram_verifiers.py username password [iterations=4096]
"""

import base64
import hashlib
import hmac
import os
import sys


def generate_salt(length: int = 16) -> bytes:
    """Generate a random salt."""
    return os.urandom(length)


def generate_scram_verifier(
    username: str, password: str, iterations: int = 4096
) -> str:
    """
    Generate a SCRAM-SHA-256 verifier string for PgBouncer.

    Args:
        username: Database username
        password: Plain text password
        iterations: Number of iterations for the hash (default: 4096)

    Returns:
        String in format: "username" "SCRAM-SHA-256$iterations:salt$storedkey:serverkey"
    """
    # Generate a random salt
    salt = generate_salt(16)

    # Normalize password (SASLprep would be better, but this is simpler)
    normalized = password.encode("utf-8")

    # Generate SaltedPassword
    salted_password = hashlib.pbkdf2_hmac(
        "sha256", normalized, salt, iterations, dklen=32
    )

    # Generate client and server keys
    client_key = hmac.new(salted_password, b"Client Key", "sha256").digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted_password, b"Server Key", "sha256").digest()

    # Base64 encode the binary values
    salt_b64 = base64.b64encode(salt).decode("ascii")
    stored_key_b64 = base64.b64encode(stored_key).decode("ascii")
    server_key_b64 = base64.b64encode(server_key).decode("ascii")

    # Return the verifier string
    return f'"{username}" "SCRAM-SHA-256${iterations}:{salt_b64}${stored_key_b64}:{server_key_b64}"'


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python generate_scram_verifiers.py username password [iterations]"
        )
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 4096

    verifier = generate_scram_verifier(username, password, iterations)
    print("Add this line to your PgBouncer userlist.txt:")
    print(verifier)


if __name__ == "__main__":
    main()

"""Security utilities for authentication and authorization."""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.auth import TokenPayload

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.
    
    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    
    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token.
    
    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    
    return jwt.encode(
        to_encode, 
        settings.REFRESH_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )


def verify_token(token: str, *, is_refresh: bool = False) -> TokenPayload:
    """Verify a JWT token and return its payload.
    
    Args:
        token: The JWT token to verify
        is_refresh: Whether this is a refresh token
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    if is_refresh:
        secret_key = settings.REFRESH_SECRET_KEY
    else:
        secret_key = settings.SECRET_KEY
    
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        token_data = TokenPayload(**payload)
        
        # Additional validation for token type
        if is_refresh and token_data.type != "refresh":
            raise JWTError("Invalid token type")
        elif not is_refresh and token_data.type != "access":
            raise JWTError("Invalid token type")
            
    except (JWTError, ValidationError) as e:
        raise ValueError("Could not validate credentials") from e
    
    return token_data


def generate_password_reset_token(email: str) -> str:
    """Generate a password reset token.
    
    Args:
        email: User's email address
        
    Returns:
        JWT token for password reset
    """
    expires = datetime.utcnow() + timedelta(
        hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS
    )
    to_encode = {
        "exp": expires,
        "sub": email,
        "type": "password_reset",
    }
    
    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )


def get_public_key() -> str:
    """Get the current public key for JWT verification.
    
    Returns:
        The public key as a string
        
    Raises:
        RuntimeError: If the public key file is not found
    """
    # Look for the public key in the configured directory
    keys_dir = Path(settings.JWT_KEYSET_DIR)
    if not keys_dir.exists() or not keys_dir.is_dir():
        raise RuntimeError(f"JWT keys directory not found: {keys_dir}")
    
    # Find the most recent public key
    public_keys = list(keys_dir.glob("*.pub"))
    if not public_keys:
        raise RuntimeError(f"No public key files found in {keys_dir}")
    
    # Get the most recent key (by modification time)
    latest_key = max(public_keys, key=os.path.getmtime)
    return latest_key.read_text()


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        The email address if the token is valid, None otherwise
    """
    try:
        # Get the public key for verification
        public_key = get_public_key()
        
        # Decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"verify_exp": True},
        )
        
        # Verify this is a password reset token
        if payload.get("type") != "password_reset":
            return None
            
        return payload.get("sub")
        
    except JWTError:
        return None


def decode_token(token: str) -> dict:
    """Decode a JWT token and return its payload.
    
    This is a lower-level function that just decodes the token without
    performing all the validations done in verify_token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If the token is invalid or expired
    """
    # Get the public key for verification
    public_key = get_public_key()
    
    # Decode and verify the token
    return jwt.decode(
        token,
        public_key,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options={"verify_exp": True},
    )

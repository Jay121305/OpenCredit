"""
Security Utilities
==================

Cryptographic functions for authentication and authorization:

Password Hashing:
    - Uses PBKDF2-SHA256 with 210,000 iterations
    - Random 16-byte salt per password
    - Format: "pbkdf2_sha256${iterations}${salt}${hash}"

JWT Tokens:
    - HS256 algorithm with configurable secret
    - Configurable expiration (default 60 minutes)
    - Payload: {"sub": email, "exp": expiration}

API Keys:
    - Format: "oc_live_{32_random_chars}"
    - Stored as SHA-256 hash (never plain text)
"""

from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import secrets
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-SHA256.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password in format: "pbkdf2_sha256${iterations}${salt}${hash}"
    """
    salt = secrets.token_hex(16)
    iterations = 210000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        password: Plain text password to verify
        hashed_password: Previously hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        _, iterations_str, salt, expected_hex = hashed_password.split("$", maxsplit=3)
        iterations = int(iterations_str)
    except ValueError:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return hmac.compare_digest(actual, expected_hex)


def create_access_token(subject: str) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (typically user email)
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary
        
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def generate_merchant_api_key() -> str:
    """
    Generate a new merchant API key.
    
    Format: "oc_live_{32_random_urlsafe_chars}"
    
    Returns:
        Plain text API key (store only the hash!)
    """
    return f"oc_live_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.
    
    Uses SHA-256 for fast verification during API calls.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        SHA-256 hex digest of the key
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

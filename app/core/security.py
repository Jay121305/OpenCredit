from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import secrets
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 210000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        _, iterations_str, salt, expected_hex = hashed_password.split("$", maxsplit=3)
        iterations = int(iterations_str)
    except ValueError:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return hmac.compare_digest(actual, expected_hex)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def generate_merchant_api_key() -> str:
    return f"oc_live_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

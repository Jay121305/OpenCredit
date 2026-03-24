"""
Dependency injection for API authentication and authorization.

Provides:
- get_current_user: JWT-based user authentication
- get_current_active_user: Active user validation
- get_current_admin_user: Admin role validation
- get_merchant_by_api_key: API key-based merchant authentication (supports key rotation)
"""

from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_api_key
from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Grace period for secondary key validity
KEY_ROTATION_GRACE_PERIOD_DAYS = 7


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.email == user_email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """
    Get the current user and verify they are active.
    
    Raises:
        HTTPException 403: If user account is deactivated
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


def get_current_admin_user(user: User = Depends(get_current_active_user)) -> User:
    """
    Get the current user and verify they have admin role.
    
    Raises:
        HTTPException 403: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def get_merchant_by_api_key(
    x_api_key: str = Header(default="", alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Merchant:
    """
    Get merchant by API key header.
    
    Supports key rotation: both primary and secondary keys are accepted during
    the grace period (7 days after rotation).
    
    Raises:
        HTTPException 401: If API key is missing or invalid
        HTTPException 403: If merchant is inactive or secondary key expired
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing merchant API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    if not x_api_key.startswith("oc_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    key_hash = hash_api_key(x_api_key)
    
    # Check primary key first
    merchant = db.scalar(
        select(Merchant).where(Merchant.api_key_hash == key_hash)
    )
    
    if merchant:
        if not merchant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant account is inactive",
            )
        return merchant
    
    # Check secondary key (during rotation grace period)
    merchant = db.scalar(
        select(Merchant).where(Merchant.api_key_hash_secondary == key_hash)
    )
    
    if merchant:
        if not merchant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant account is inactive",
            )
        
        # Check if secondary key is still within grace period
        if merchant.key_rotated_at:
            grace_period_end = merchant.key_rotated_at + timedelta(days=KEY_ROTATION_GRACE_PERIOD_DAYS)
            if datetime.utcnow() > grace_period_end:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired (rotation grace period ended)",
                    headers={"WWW-Authenticate": "X-API-Key"},
                )
        
        return merchant
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid merchant API key",
        headers={"WWW-Authenticate": "X-API-Key"},
    )

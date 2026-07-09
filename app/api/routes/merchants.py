"""
Merchant management endpoints.

Note: Merchant creation and key rotation require admin privileges for security.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin_user
from app.core.config import settings
from app.core.security import generate_merchant_api_key, hash_api_key
from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.user import User
from app.schemas.merchant import (
    MerchantCreateRequest,
    MerchantCreateResponse,
    MerchantKeyRotateResponse,
    MerchantKeyRevokeResponse,
    MerchantResponse,
)


router = APIRouter(prefix="/merchants", tags=["merchants"])


# Grace period for old API key validity (7 days)
KEY_ROTATION_GRACE_PERIOD_DAYS = 7


@router.post(
    "",
    response_model=MerchantCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new merchant",
    description="Create a new merchant account and generate an API key. **Available to all authenticated users.**",
)
def create_merchant(
    payload: MerchantCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> MerchantCreateResponse:
    """
    Create a new merchant account.
    
    - Requires user authentication
    - Generates a unique API key for the merchant
    - API key is only shown once - store it securely!
    
    Returns:
        MerchantCreateResponse with merchant_id, name, and API key
    """
    api_key = generate_merchant_api_key()
    merchant = Merchant(name=payload.name, api_key_hash=hash_api_key(api_key))
    db.add(merchant)
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create merchant",
        ) from exc
    
    db.refresh(merchant)
    
    return MerchantCreateResponse(
        merchant_id=merchant.id,
        name=merchant.name,
        api_key=api_key,
    )


@router.get(
    "",
    response_model=list[MerchantResponse],
    summary="List all merchants",
    description="Retrieve all active merchants. **Available to all authenticated users.**",
)
def list_merchants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MerchantResponse]:
    """List all active merchants."""
    merchants = db.query(Merchant).filter(Merchant.is_active == True).all()
    return [MerchantResponse.model_validate(m) for m in merchants]


@router.get(
    "/{merchant_id}",
    response_model=MerchantResponse,
    summary="Get merchant details",
    description="Retrieve merchant information. **Available to all authenticated users.**",
)
def get_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MerchantResponse:
    """Get merchant details by ID."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant {merchant_id} not found",
        )
    return MerchantResponse.model_validate(merchant)


@router.post(
    "/{merchant_id}/rotate-key",
    response_model=MerchantKeyRotateResponse,
    summary="Rotate merchant API key",
    description="""
    Rotate a merchant's API key. The old key remains valid for a grace period (7 days).
    
    **Security best practice:** Rotate API keys regularly and immediately if compromised.
    
    **Requires admin privileges.**
    """,
)
def rotate_merchant_key(
    merchant_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> MerchantKeyRotateResponse:
    """
    Rotate a merchant's API key.
    
    Process:
    1. Move current key to secondary slot
    2. Generate new primary key
    3. Old key remains valid for grace period
    
    Returns:
        New API key and expiry time for old key
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant {merchant_id} not found",
        )
    
    if not merchant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rotate key for inactive merchant",
        )
    
    # Generate new API key
    new_api_key = generate_merchant_api_key()
    new_key_hash = hash_api_key(new_api_key)
    
    # Move current key to secondary slot (grace period)
    merchant.api_key_hash_secondary = merchant.api_key_hash
    merchant.api_key_hash = new_key_hash
    merchant.key_rotated_at = datetime.utcnow()
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key",
        ) from exc
    
    old_key_valid_until = merchant.key_rotated_at + timedelta(days=KEY_ROTATION_GRACE_PERIOD_DAYS)
    
    return MerchantKeyRotateResponse(
        merchant_id=merchant.id,
        new_api_key=new_api_key,
        old_key_valid_until=old_key_valid_until,
        message=f"API key rotated. Old key valid until {old_key_valid_until.isoformat()}",
    )


@router.post(
    "/{merchant_id}/revoke-secondary-key",
    response_model=MerchantKeyRevokeResponse,
    summary="Revoke secondary API key",
    description="""
    Immediately revoke the secondary (old) API key before grace period expires.
    
    Use this if the old key was compromised or you want to force immediate rotation.
    
    **Requires admin privileges.**
    """,
)
def revoke_secondary_key(
    merchant_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> MerchantKeyRevokeResponse:
    """Immediately revoke the secondary API key."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant {merchant_id} not found",
        )
    
    if not merchant.api_key_hash_secondary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No secondary key to revoke",
        )
    
    merchant.api_key_hash_secondary = None
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke secondary key",
        ) from exc
    
    return MerchantKeyRevokeResponse(
        merchant_id=merchant.id,
        message="Secondary API key revoked immediately",
    )


@router.post(
    "/{merchant_id}/deactivate",
    response_model=MerchantResponse,
    summary="Deactivate a merchant",
    description="Deactivate a merchant account. All API keys become invalid. **Requires admin privileges.**",
)
def deactivate_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> MerchantResponse:
    """Deactivate a merchant account."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant {merchant_id} not found",
        )
    
    merchant.is_active = False
    merchant.api_key_hash_secondary = None  # Clear secondary key on deactivation
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate merchant",
        ) from exc
    
    db.refresh(merchant)
    return MerchantResponse.model_validate(merchant)

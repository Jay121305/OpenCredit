"""
Authentication API Routes
=========================

Endpoints for user registration, login, and profile access.

Endpoints:
    POST /auth/register - Create new user account
    POST /auth/login - Authenticate and get JWT token
    GET /auth/me - Get current user profile with role info

Security:
    - Passwords hashed with bcrypt (cost factor 12)
    - JWT tokens for session management
    - Tokens expire after configured duration (default 30 min)

Roles:
    - viewer: Read-only dashboard access
    - user: Standard user (default)
    - analyst: Create/edit records + analytics
    - admin: Full administrative access
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.credit import CreditAccount
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class UserProfileResponse(BaseModel):
    """
    User profile response with role and credit information.
    
    Attributes:
        id: User's unique identifier
        email: User's email address
        full_name: User's display name
        role: Role string (viewer/user/analyst/admin)
        is_active: Whether account is active
        is_admin: True if user has admin role
        is_analyst: True if user has analyst role or higher
        access_level: Numeric access level (1-4)
        credit_limit: Total credit limit
        available_credit: Remaining available credit
    """
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_admin: bool
    is_analyst: bool
    access_level: int
    credit_limit: float = 0.0
    available_credit: float = 0.0


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Register a new user account.
    
    Creates user with default credit limit and returns JWT token.
    Email must be unique across all accounts.
    
    Args:
        payload: Registration data (email, full_name, password, optional role)
        
    Returns:
        TokenResponse with access_token for immediate authentication
        
    Raises:
        400: Email already exists
    """
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role
    )
    db.add(user)
    db.flush()
    db.add(CreditAccount(
        user_id=user.id,
        credit_limit=settings.default_credit_limit,
        available_credit=settings.default_credit_limit
    ))
    db.commit()

    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Args:
        payload: Login credentials (email, password)
        
    Returns:
        TokenResponse with access_token for API authentication
        
    Raises:
        401: Invalid email or password
    """
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserProfileResponse:
    """
    Get current authenticated user's profile.
    
    Returns complete profile including role permissions and credit info.
    Used by dashboard to determine which features to show.
    
    Returns:
        UserProfileResponse with role, permissions, and credit data
        
    Requires:
        Valid JWT token in Authorization header
    """
    account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user.id))
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_analyst=user.is_analyst,
        access_level=user.access_level,
        credit_limit=account.credit_limit if account else 0.0,
        available_credit=account.available_credit if account else 0.0,
    )

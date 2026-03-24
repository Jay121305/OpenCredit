"""
Authentication schemas with strong input validation.

Password Requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
"""

import re
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


# Disposable email domains to reject
DISPOSABLE_EMAIL_DOMAINS = {
    "tempmail.com", "throwaway.email", "mailinator.com", "guerrillamail.com",
    "10minutemail.com", "temp-mail.org", "fakeinbox.com", "trashmail.com",
    "sharklasers.com", "yopmail.com", "getnada.com", "maildrop.cc",
}


class RegisterRequest(BaseModel):
    """User registration request with strong validation."""
    
    email: EmailStr = Field(
        ...,
        description="Valid email address (disposable emails not allowed)",
        json_schema_extra={"example": "user@example.com"}
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name",
        json_schema_extra={"example": "John Doe"}
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password with uppercase, lowercase, digit, and special character",
        json_schema_extra={"example": "SecurePass123!"}
    )

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Reject disposable email domains."""
        domain = v.split("@")[1].lower()
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise ValueError("Disposable email addresses are not allowed")
        return v.lower()  # Normalize to lowercase

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce password complexity requirements.
        
        Requirements:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (@$!%*?&_#)
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&_#\-\.]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&_#-.)")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Sanitize and validate full name."""
        # Remove excess whitespace
        v = " ".join(v.split())
        # Check for reasonable characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[\w\s\-'\.]+$", v, re.UNICODE):
            raise ValueError("Full name contains invalid characters")
        return v


class LoginRequest(BaseModel):
    """Login request."""
    
    email: EmailStr = Field(
        ...,
        description="Registered email address",
        json_schema_extra={"example": "user@example.com"}
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Account password"
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()


class TokenResponse(BaseModel):
    """JWT token response."""
    
    access_token: str = Field(
        ...,
        description="JWT access token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        default=3600,
        description="Token lifetime in seconds"
    )

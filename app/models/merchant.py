"""
Merchant model with API key management.

Supports:
- Primary API key (api_key_hash)
- Secondary API key for rotation (api_key_hash_secondary)
- Key metadata (created_at, rotated_at)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Merchant(Base):
    """
    Merchant account model.
    
    API Key Rotation:
    - api_key_hash: Current primary API key
    - api_key_hash_secondary: Previous key (valid during rotation grace period)
    - key_rotated_at: When the key was last rotated
    
    During rotation, both keys are valid for a grace period (default 7 days).
    """
    
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    api_key_hash_secondary: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    key_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

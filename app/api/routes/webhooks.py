"""
Webhook API routes.

Endpoints for:
- Registering webhook endpoints
- Managing subscriptions
- Viewing delivery history
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin_user
from app.db.session import get_db
from app.models.webhook import WebhookEndpoint, WebhookDelivery, WebhookEventType, WebhookDeliveryStatus
from app.models.merchant import Merchant
from app.models.user import User
from app.services.webhooks import webhook_service


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ============================================================================
# Schemas
# ============================================================================

class WebhookEndpointCreate(BaseModel):
    """Request to create a webhook endpoint."""
    
    url: str = Field(..., description="URL to receive webhook events")
    description: Optional[str] = Field(None, description="Description of this endpoint")
    events: List[str] = Field(default=[], description="Event types to subscribe to (empty = all)")


class WebhookEndpointResponse(BaseModel):
    """Webhook endpoint details."""
    
    id: int
    merchant_id: int
    url: str
    description: Optional[str] = None
    events: List[str]
    is_active: bool
    secret_key: str  # Only shown once on creation, masked otherwise
    created_at: str


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery record."""
    
    id: int
    endpoint_id: int
    event_type: str
    event_id: str
    status: str
    attempts: int
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    last_attempt_at: Optional[str] = None
    delivered_at: Optional[str] = None


class WebhookEndpointUpdate(BaseModel):
    """Request to update a webhook endpoint."""
    
    url: Optional[str] = None
    description: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_merchant_for_user(db: Session, user: User) -> Merchant:
    """Get merchant associated with user."""
    merchant = db.scalar(select(Merchant).where(Merchant.owner_id == user.id))
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No merchant found for this user. Create a merchant first.",
        )
    return merchant


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/events", summary="List available webhook events")
def list_webhook_events() -> dict:
    """List all available webhook event types."""
    return {
        "events": [
            {
                "type": event.value,
                "description": event.value.replace(".", " ").replace("_", " ").title(),
            }
            for event in WebhookEventType
        ]
    }


@router.post("", response_model=WebhookEndpointResponse, summary="Create webhook endpoint")
def create_webhook_endpoint(
    request: WebhookEndpointCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookEndpointResponse:
    """
    Create a new webhook endpoint for your merchant.
    
    The secret key is only shown once - save it securely!
    """
    merchant = get_merchant_for_user(db, user)
    
    # Validate events
    valid_events = [e.value for e in WebhookEventType]
    for event in request.events:
        if event not in valid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event}. Valid types: {valid_events}",
            )
    
    # Generate secret key
    secret_key = webhook_service.generate_secret_key()
    
    # Create endpoint
    endpoint = WebhookEndpoint(
        merchant_id=merchant.id,
        url=request.url,
        description=request.description,
        secret_key=secret_key,
        events=json.dumps(request.events),
        is_active=True,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    
    return WebhookEndpointResponse(
        id=endpoint.id,
        merchant_id=endpoint.merchant_id,
        url=endpoint.url,
        description=endpoint.description,
        events=request.events,
        is_active=endpoint.is_active,
        secret_key=secret_key,  # Only shown on creation!
        created_at=endpoint.created_at.isoformat(),
    )


@router.get("", summary="List webhook endpoints")
def list_webhook_endpoints(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict]:
    """List all webhook endpoints for your merchant."""
    merchant = get_merchant_for_user(db, user)
    
    endpoints = db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.merchant_id == merchant.id)
    ).scalars().all()
    
    return [
        {
            "id": e.id,
            "merchant_id": e.merchant_id,
            "url": e.url,
            "description": e.description,
            "events": json.loads(e.events) if e.events else [],
            "is_active": e.is_active,
            "secret_key": f"{e.secret_key[:8]}...{e.secret_key[-4:]}",  # Masked
            "created_at": e.created_at.isoformat(),
        }
        for e in endpoints
    ]


@router.get("/{endpoint_id}", summary="Get webhook endpoint")
def get_webhook_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get details of a specific webhook endpoint."""
    merchant = get_merchant_for_user(db, user)
    
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    return {
        "id": endpoint.id,
        "merchant_id": endpoint.merchant_id,
        "url": endpoint.url,
        "description": endpoint.description,
        "events": json.loads(endpoint.events) if endpoint.events else [],
        "is_active": endpoint.is_active,
        "secret_key": f"{endpoint.secret_key[:8]}...{endpoint.secret_key[-4:]}",
        "created_at": endpoint.created_at.isoformat(),
        "updated_at": endpoint.updated_at.isoformat(),
    }


@router.patch("/{endpoint_id}", summary="Update webhook endpoint")
def update_webhook_endpoint(
    endpoint_id: int,
    request: WebhookEndpointUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update a webhook endpoint."""
    merchant = get_merchant_for_user(db, user)
    
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    if request.url is not None:
        endpoint.url = request.url
    if request.description is not None:
        endpoint.description = request.description
    if request.events is not None:
        endpoint.events = json.dumps(request.events)
    if request.is_active is not None:
        endpoint.is_active = request.is_active
    
    db.commit()
    db.refresh(endpoint)
    
    return {
        "id": endpoint.id,
        "url": endpoint.url,
        "description": endpoint.description,
        "events": json.loads(endpoint.events) if endpoint.events else [],
        "is_active": endpoint.is_active,
        "message": "Webhook endpoint updated successfully.",
    }


@router.post("/{endpoint_id}/rotate-secret", summary="Rotate webhook secret")
def rotate_webhook_secret(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Rotate the webhook secret key.
    
    The new secret is only shown once - save it securely!
    """
    merchant = get_merchant_for_user(db, user)
    
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    new_secret = webhook_service.generate_secret_key()
    endpoint.secret_key = new_secret
    db.commit()
    
    return {
        "message": "Secret key rotated successfully.",
        "secret_key": new_secret,  # Only shown once!
    }


@router.delete("/{endpoint_id}", summary="Delete webhook endpoint")
def delete_webhook_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a webhook endpoint."""
    merchant = get_merchant_for_user(db, user)
    
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    db.delete(endpoint)
    db.commit()
    
    return {"message": "Webhook endpoint deleted successfully."}


@router.get("/{endpoint_id}/deliveries", summary="List webhook deliveries")
def list_webhook_deliveries(
    endpoint_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List delivery attempts for a webhook endpoint."""
    merchant = get_merchant_for_user(db, user)
    
    # Verify ownership
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    # Build query
    query = select(WebhookDelivery).where(WebhookDelivery.endpoint_id == endpoint_id)
    count_query = select(func.count(WebhookDelivery.id)).where(WebhookDelivery.endpoint_id == endpoint_id)
    
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)
        count_query = count_query.where(WebhookDelivery.status == status_filter)
    
    total = db.scalar(count_query)
    
    deliveries = db.execute(
        query.order_by(WebhookDelivery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return {
        "items": [
            {
                "id": d.id,
                "event_type": d.event_type,
                "event_id": d.event_id,
                "status": d.status,
                "attempts": d.attempts,
                "response_status": d.response_status,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat(),
                "last_attempt_at": d.last_attempt_at.isoformat() if d.last_attempt_at else None,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            }
            for d in deliveries
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{endpoint_id}/test", summary="Test webhook endpoint")
async def test_webhook_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Send a test event to verify the webhook endpoint is working."""
    merchant = get_merchant_for_user(db, user)
    
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.merchant_id == merchant.id,
        )
    )
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found.",
        )
    
    # Dispatch test event
    delivery_ids = await webhook_service.dispatch_event(
        db=db,
        merchant_id=merchant.id,
        event_type="test.ping",
        data={"message": "This is a test webhook event."},
    )
    
    return {
        "message": "Test event dispatched.",
        "delivery_ids": delivery_ids,
    }

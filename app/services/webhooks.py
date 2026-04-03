"""
Webhook delivery service.

Handles:
- Event dispatching to merchant endpoints
- HMAC signature generation
- Retry logic with exponential backoff
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.webhook import WebhookEndpoint, WebhookDelivery, WebhookEventType, WebhookDeliveryStatus


logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook delivery service.
    
    Features:
    - HMAC-SHA256 signature for payload verification
    - Automatic retries with exponential backoff
    - Event filtering based on subscription
    """
    
    RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # 1min, 5min, 15min, 1hr, 4hr
    
    def __init__(self):
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.max_retries = settings.WEBHOOK_MAX_RETRIES
    
    def generate_secret_key(self) -> str:
        """Generate a new webhook secret key."""
        return secrets.token_hex(32)
    
    def sign_payload(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: JSON payload string
            secret: Webhook secret key
            
        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Received payload
            signature: Received signature header
            secret: Webhook secret key
            
        Returns:
            True if signature is valid
        """
        expected = self.sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)
    
    def build_event_payload(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a webhook event payload.
        
        Args:
            event_type: Type of event
            data: Event data
            event_id: Optional event ID (generated if not provided)
            
        Returns:
            Complete event payload
        """
        return {
            "id": event_id or str(uuid.uuid4()),
            "type": event_type,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }
    
    async def dispatch_event(
        self,
        db: Session,
        merchant_id: int,
        event_type: str,
        data: Dict[str, Any],
    ) -> List[int]:
        """
        Dispatch an event to all subscribed endpoints for a merchant.
        
        Args:
            db: Database session
            merchant_id: Merchant ID
            event_type: Event type
            data: Event data
            
        Returns:
            List of delivery IDs created
        """
        # Find subscribed endpoints
        endpoints = db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.merchant_id == merchant_id,
                WebhookEndpoint.is_active == True,
            )
        ).scalars().all()
        
        delivery_ids = []
        
        for endpoint in endpoints:
            # Check if endpoint is subscribed to this event
            try:
                subscribed_events = json.loads(endpoint.events)
            except json.JSONDecodeError:
                subscribed_events = []
            
            # Support wildcard subscription (empty list = all events)
            if subscribed_events and event_type not in subscribed_events:
                continue
            
            # Build payload
            event_id = str(uuid.uuid4())
            payload = self.build_event_payload(event_type, data, event_id)
            payload_str = json.dumps(payload, default=str)
            
            # Create delivery record
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                event_id=event_id,
                payload=payload_str,
                status=WebhookDeliveryStatus.PENDING.value,
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)
            
            delivery_ids.append(delivery.id)
            
            # Attempt delivery
            await self._deliver(db, delivery, endpoint)
        
        return delivery_ids
    
    async def _deliver(
        self,
        db: Session,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint,
    ) -> bool:
        """
        Attempt to deliver a webhook.
        
        Args:
            db: Database session
            delivery: Delivery record
            endpoint: Endpoint configuration
            
        Returns:
            True if delivery succeeded
        """
        delivery.attempts += 1
        delivery.last_attempt_at = datetime.utcnow()
        
        try:
            # Sign payload
            signature = self.sign_payload(delivery.payload, endpoint.secret_key)
            
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": delivery.event_type,
                "X-Webhook-Event-Id": delivery.event_id,
                "X-Webhook-Timestamp": str(int(time.time())),
                "User-Agent": "OpenCredit-Webhooks/1.0",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint.url,
                    content=delivery.payload,
                    headers=headers,
                )
            
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000] if response.text else None
            
            if 200 <= response.status_code < 300:
                delivery.status = WebhookDeliveryStatus.SUCCESS.value
                delivery.delivered_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Webhook delivered: {delivery.event_id} to {endpoint.url}")
                return True
            else:
                raise Exception(f"HTTP {response.status_code}")
            
        except Exception as e:
            delivery.error_message = str(e)
            
            if delivery.attempts >= delivery.max_attempts:
                delivery.status = WebhookDeliveryStatus.FAILED.value
                logger.error(
                    f"Webhook failed permanently: {delivery.event_id} to {endpoint.url} "
                    f"after {delivery.attempts} attempts: {e}"
                )
            else:
                delivery.status = WebhookDeliveryStatus.RETRYING.value
                # Calculate next retry time with exponential backoff
                delay_index = min(delivery.attempts - 1, len(self.RETRY_DELAYS) - 1)
                delay = self.RETRY_DELAYS[delay_index]
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                
                logger.warning(
                    f"Webhook delivery failed: {delivery.event_id} to {endpoint.url}, "
                    f"attempt {delivery.attempts}/{delivery.max_attempts}, "
                    f"retry at {delivery.next_retry_at}: {e}"
                )
            
            db.commit()
            return False
    
    async def retry_pending_deliveries(self, db: Session) -> int:
        """
        Retry all pending webhook deliveries that are due.
        
        This should be called periodically by a background worker.
        
        Returns:
            Number of deliveries retried
        """
        now = datetime.utcnow()
        
        # Find deliveries due for retry
        deliveries = db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status == WebhookDeliveryStatus.RETRYING.value,
                WebhookDelivery.next_retry_at <= now,
            )
        ).scalars().all()
        
        retried = 0
        
        for delivery in deliveries:
            endpoint = db.scalar(
                select(WebhookEndpoint).where(WebhookEndpoint.id == delivery.endpoint_id)
            )
            
            if endpoint and endpoint.is_active:
                await self._deliver(db, delivery, endpoint)
                retried += 1
        
        return retried


# Singleton instance
webhook_service = WebhookService()

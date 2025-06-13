from fastapi import HTTPException, Request
from typing import Optional
import hmac
import hashlib
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WebhookAuth:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret.encode()
        
    def _compute_signature(self, payload: bytes) -> str:
        """Compute HMAC signature for webhook payload"""
        return hmac.new(
            self.webhook_secret,
            payload,
            hashlib.sha256
        ).hexdigest()
        
    def _verify_timestamp(self, timestamp: str) -> bool:
        """Verify webhook timestamp is within acceptable range"""
        try:
            webhook_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.utcnow()
            
            # Allow 5-minute window for clock skew
            time_diff = abs((now - webhook_time).total_seconds())
            return time_diff <= 300
            
        except Exception as e:
            logger.error(f"Error verifying timestamp: {str(e)}")
            return False
            
    async def verify_signature(self, request: Request) -> bool:
        """Verify webhook signature and timestamp"""
        try:
            # Get signature from header
            signature = request.headers.get("X-Webhook-Signature")
            if not signature:
                raise HTTPException(
                    status_code=401,
                    detail="Missing webhook signature"
                )
                
            # Get timestamp from header
            timestamp = request.headers.get("X-Webhook-Timestamp")
            if not timestamp:
                raise HTTPException(
                    status_code=401,
                    detail="Missing webhook timestamp"
                )
                
            # Verify timestamp
            if not self._verify_timestamp(timestamp):
                raise HTTPException(
                    status_code=401,
                    detail="Webhook timestamp is too old"
                )
                
            # Get request body
            body = await request.body()
            
            # Compute expected signature
            expected_signature = self._compute_signature(body)
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid webhook signature"
                )
                
            return True
            
        except HTTPException:
            raise
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error verifying webhook signature"
            )
            
    async def verify_webhook(self, request: Request) -> bool:
        """Verify webhook request"""
        # Skip verification for non-webhook endpoints
        if not request.url.path.startswith("/webhooks/"):
            return True
            
        return await self.verify_signature(request) 
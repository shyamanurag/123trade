"""
Secure Webhook Handler with Authentication and Signature Verification
Production-ready webhook processing with security measures
"""
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional, Any
import logging
import hmac
import hashlib
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()
security = HTTPBearer()

# Webhook security configuration
WEBHOOK_SECRET = "your_webhook_secret_here"  # Should be from environment
WEBHOOK_TIMEOUT = 300  # 5 minutes

async def verify_webhook_signature(
    request: Request,
    signature: str = Header(None, alias="X-Webhook-Signature"),
    timestamp: str = Header(None, alias="X-Webhook-Timestamp")
) -> bool:
    """Verify webhook signature and timestamp"""
    
    if not signature or not timestamp:
        logger.warning("Missing webhook signature or timestamp")
        raise HTTPException(status_code=401, detail="Missing webhook authentication")
    
    # Check timestamp to prevent replay attacks
    try:
        webhook_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - webhook_time) > WEBHOOK_TIMEOUT:
            logger.warning(f"Webhook timestamp too old: {webhook_time}")
            raise HTTPException(status_code=401, detail="Webhook timestamp expired")
    except ValueError:
        logger.warning(f"Invalid webhook timestamp: {timestamp}")
        raise HTTPException(status_code=401, detail="Invalid webhook timestamp")
    
    # Verify signature
    body = await request.body()
    payload = f"{timestamp}.{body.decode()}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    received_signature = signature.replace("sha256=", "")
    
    if not hmac.compare_digest(expected_signature, received_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    return True

async def authenticate_webhook(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Authenticate webhook using bearer token"""
    
    expected_token = "your_webhook_bearer_token"  # Should be from environment
    
    if not credentials or credentials.credentials != expected_token:
        logger.warning("Invalid webhook bearer token")
        raise HTTPException(status_code=401, detail="Invalid webhook authentication")
    
    return True

# Secure webhook endpoints with authentication

@router.post("/market-data")
async def receive_market_data(
    data: Dict[str, Any], 
    request: Request,
    authenticated: bool = Depends(verify_webhook_signature)
):
    """Receive real-time market data with authentication"""
    try:
        logger.info(f"Authenticated market data received from {request.client.host if request.client else 'unknown'}")
        
        # Validate required fields
        required_fields = ["symbol", "price", "timestamp"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Process market data
        symbol = data.get("symbol")
        price = data.get("price")
        
        # Here you would typically:
        # 1. Store in database
        # 2. Update cache
        # 3. Trigger trading signals
        # 4. Notify subscribers
        
        logger.info(f"Market data processed for {symbol}: {price}")
        
        return {
            "status": "processed",
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing market data: {str(e)}")
        raise HTTPException(status_code=500, detail="Market data processing failed")

@router.post("/order-update")
async def receive_order_update(
    data: Dict[str, Any], 
    request: Request,
    authenticated: bool = Depends(verify_webhook_signature)
):
    """Receive order status updates with authentication"""
    try:
        logger.info(f"Authenticated order update received from {request.client.host if request.client else 'unknown'}")
        
        # Validate required fields
        required_fields = ["order_id", "status", "user_id"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        order_id = data.get("order_id")
        status = data.get("status")
        user_id = data.get("user_id")
        
        # Process order update
        # Here you would typically:
        # 1. Update order status in database
        # 2. Notify user
        # 3. Update portfolio
        # 4. Log transaction
        
        logger.info(f"Order {order_id} updated to {status} for user {user_id}")
        
        return {
            "status": "processed",
            "order_id": order_id,
            "order_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing order update: {str(e)}")
        raise HTTPException(status_code=500, detail="Order update processing failed")

@router.post("/position-update")
async def receive_position_update(
    data: Dict[str, Any], 
    request: Request,
    authenticated: bool = Depends(verify_webhook_signature)
):
    """Receive position updates with authentication"""
    try:
        logger.info(f"Authenticated position update received from {request.client.host if request.client else 'unknown'}")
        
        # Validate required fields
        required_fields = ["user_id", "symbol", "quantity"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        quantity = data.get("quantity")
        
        # Process position update
        # Here you would typically:
        # 1. Update position in database
        # 2. Recalculate P&L
        # 3. Update risk metrics
        # 4. Check risk limits
        
        logger.info(f"Position updated for user {user_id}: {symbol} quantity {quantity}")
        
        return {
            "status": "processed",
            "user_id": user_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing position update: {str(e)}")
        raise HTTPException(status_code=500, detail="Position update processing failed")

@router.post("/risk-alert")
async def receive_risk_alert(
    data: Dict[str, Any], 
    request: Request,
    authenticated: bool = Depends(verify_webhook_signature)
):
    """Receive risk management alerts with authentication"""
    try:
        logger.info(f"Authenticated risk alert received from {request.client.host if request.client else 'unknown'}")
        
        # Validate required fields
        required_fields = ["alert_type", "severity", "user_id"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        alert_type = data.get("alert_type")
        severity = data.get("severity")
        user_id = data.get("user_id")
        
        # Process risk alert
        # Here you would typically:
        # 1. Log alert
        # 2. Notify risk team
        # 3. Take automated action if needed
        # 4. Update risk dashboard
        
        logger.warning(f"Risk alert processed: {alert_type} (severity: {severity}) for user {user_id}")
        
        return {
            "status": "processed",
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing risk alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Risk alert processing failed")

# System webhooks
@router.post("/system-event")
async def receive_system_event(
    data: Dict[str, Any], 
    request: Request,
    authenticated: bool = Depends(authenticate_webhook)
):
    """Receive system events with bearer token authentication"""
    try:
        logger.info(f"Authenticated system event received from {request.client.host if request.client else 'unknown'}")
        
        event_type = data.get("event_type")
        event_data = data.get("event_data", {})
        
        # Process system event
        logger.info(f"System event processed: {event_type}")
        
        return {
            "status": "processed",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing system event: {str(e)}")
        raise HTTPException(status_code=500, detail="System event processing failed")

# Health check for webhooks
@router.get("/health")
async def webhook_health():
    """Webhook system health check"""
    return {
        "status": "healthy",
        "service": "webhook_handler",
        "timestamp": datetime.utcnow().isoformat(),
        "security": "enabled"
    } 
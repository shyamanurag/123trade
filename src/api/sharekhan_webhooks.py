"""
ShareKhan Webhook Endpoints
Handles notifications and callbacks from ShareKhan API
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/sharekhan")
async def sharekhan_webhook(request: Request):
    """
    Handle ShareKhan webhook notifications
    This endpoint receives order updates, trade confirmations, and other notifications
    """
    try:
        # Get the raw request body
        body = await request.body()
        
        # Parse JSON payload
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            logger.warning("Received non-JSON webhook payload from ShareKhan")
            payload = {"raw_body": body.decode() if body else ""}
        
        # Get headers for verification
        headers = dict(request.headers)
        
        logger.info(f"📨 ShareKhan webhook received: {payload}")
        
        # Handle different types of notifications
        notification_type = payload.get('type', 'unknown')
        
        if notification_type == 'order_update':
            await handle_order_update(payload)
        elif notification_type == 'trade_confirmation':
            await handle_trade_confirmation(payload)
        elif notification_type == 'position_update':
            await handle_position_update(payload)
        else:
            logger.info(f"📋 Unhandled ShareKhan notification type: {notification_type}")
        
        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "type": notification_type
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing ShareKhan webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_order_update(payload: Dict[str, Any]):
    """Handle order status updates from ShareKhan"""
    try:
        order_id = payload.get('order_id')
        status = payload.get('status')
        
        logger.info(f"📊 Order Update: {order_id} -> {status}")
        
        # Update order status in your system
        # You can integrate this with your order manager
        
    except Exception as e:
        logger.error(f"Error handling order update: {e}")

async def handle_trade_confirmation(payload: Dict[str, Any]):
    """Handle trade confirmations from ShareKhan"""
    try:
        trade_id = payload.get('trade_id')
        symbol = payload.get('symbol')
        quantity = payload.get('quantity')
        price = payload.get('price')
        
        logger.info(f"💰 Trade Confirmation: {symbol} {quantity} @ {price}")
        
        # Process trade confirmation
        # Update positions, calculate P&L, etc.
        
    except Exception as e:
        logger.error(f"Error handling trade confirmation: {e}")

async def handle_position_update(payload: Dict[str, Any]):
    """Handle position updates from ShareKhan"""
    try:
        symbol = payload.get('symbol')
        position = payload.get('position')
        
        logger.info(f"📈 Position Update: {symbol} -> {position}")
        
        # Update position tracking
        
    except Exception as e:
        logger.error(f"Error handling position update: {e}")

@router.get("/webhooks/sharekhan/test")
async def test_webhook():
    """Test endpoint to verify webhook functionality"""
    return {
        "status": "active",
        "message": "ShareKhan webhook endpoint is working",
        "timestamp": "2025-01-03T10:30:00Z"
    } 
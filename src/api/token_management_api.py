"""
Token Management API for Daily Authentication Tokens
Handles daily token submission and status tracking for all users
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import random

from .auth_api import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["token-management"])

# Pydantic Models
class DailyTokenSubmission(BaseModel):
    token: str
    broker_type: str = "sharekhan"
    user_id: Optional[str] = None
    expires_at: Optional[str] = None

class TokenStatusResponse(BaseModel):
    zerodha_status: str
    zerodha_expires_at: Optional[str]
    last_updated: str

# Mock token storage with ShareKhan tokens that match frontend expectations
MOCK_TOKENS = {
    "user_001": {
        "user_id": "user_001",
        "username": "demo_user",
        "token": "sk_token_demo_123",
        "token_type": "sharekhan_daily",
        "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
        "status": "active",
        "last_used": datetime.now().isoformat(),
        "auth_url": None
    },
    "admin_001": {
        "user_id": "admin_001",
        "username": "admin_user", 
        "token": "sk_token_admin_456",
        "token_type": "sharekhan_daily",
        "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
        "status": "expiring",
        "last_used": (datetime.now() - timedelta(hours=1)).isoformat(),
        "auth_url": None
    },
    "trader_001": {
        "user_id": "trader_001",
        "username": "pro_trader",
        "token": "sk_token_trader_789",
        "token_type": "sharekhan_daily", 
        "expires_at": (datetime.now() + timedelta(hours=6)).isoformat(),
        "status": "active",
        "last_used": datetime.now().isoformat(),
        "auth_url": None
    }
}

@router.post("/daily")
async def submit_daily_token(
    token_data: DailyTokenSubmission,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit daily authentication token"""
    try:
        user_id = token_data.user_id or current_user["user_id"]
        
        # Calculate expiry (default 24 hours)
        expires_at = token_data.expires_at or (datetime.now() + timedelta(days=1)).isoformat()
        
        # Store token (in production, use database)
        MOCK_TOKENS[user_id] = {
            "user_id": user_id,
            "username": current_user.get("name", "Unknown"),
            "token": token_data.token,
            "token_type": "sharekhan_daily",
            "expires_at": expires_at,
            "status": "active", 
            "last_used": datetime.now().isoformat(),
            "auth_url": None
        }
        
        logger.info(f"Daily token submitted for user {user_id} by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Daily token submitted successfully",
            "user_id": user_id,
            "broker_type": token_data.broker_type,
            "expires_at": expires_at
        }
        
    except Exception as e:
        logger.error(f"Token submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit daily token"
        )

@router.get("/tokens")
async def get_auth_tokens():
    """Get authentication tokens status for all users - matches frontend expectations"""
    try:
        tokens_list = []
        for user_id, token_data in MOCK_TOKENS.items():
            # Update status based on expiry
            expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
            time_until_expiry = expires_at - datetime.now(expires_at.tzinfo)
            
            if time_until_expiry.total_seconds() < 0:
                status = "expired"
            elif time_until_expiry.total_seconds() < 4 * 3600:  # 4 hours
                status = "expiring" 
            else:
                status = "active"
            
            # Update the stored status
            MOCK_TOKENS[user_id]["status"] = status
            
            tokens_list.append({
                "user_id": user_id,
                "username": token_data["username"],
                "token": token_data["token"][:8] + "...",  # Truncated for security
                "token_type": token_data["token_type"],
                "expires_at": token_data["expires_at"],
                "status": status,
                "last_used": token_data["last_used"],
                "auth_url": token_data.get("auth_url")
            })
        
        return {
            "success": True,
            "data": tokens_list,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting auth tokens: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/status", response_model=TokenStatusResponse)
async def get_token_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's token status"""
    try:
        user_id = current_user["user_id"]
        user_token = MOCK_TOKENS.get(user_id)
        
        if not user_token:
            return TokenStatusResponse(
                zerodha_status="not_set",
                zerodha_expires_at=None,
                last_updated=datetime.now().isoformat()
            )
        
        # Check if token is expiring (within 4 hours)
        expires_at = datetime.fromisoformat(user_token["expires_at"].replace("Z", "+00:00"))
        time_until_expiry = expires_at - datetime.now(expires_at.tzinfo)
        
        if time_until_expiry.total_seconds() < 0:
            status = "expired"
        elif time_until_expiry.total_seconds() < 4 * 3600:  # 4 hours
            status = "expiring"
        else:
            status = "active"
        
        return TokenStatusResponse(
            zerodha_status=status,
            zerodha_expires_at=user_token["expires_at"],
            last_updated=user_token["last_used"]
        )
        
    except Exception as e:
        logger.error(f"Token status error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch token status"
        )

@router.get("/all-users")
async def get_all_user_tokens(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get token status for all users (admin only)"""
    try:
        # Check if user is admin
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        all_tokens = []
        
        for user_id, token_data in MOCK_TOKENS.items():
            # Check token status
            expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
            time_until_expiry = expires_at - datetime.now(expires_at.tzinfo)
            
            if time_until_expiry.total_seconds() < 0:
                status = "expired"
            elif time_until_expiry.total_seconds() < 4 * 3600:
                status = "expiring" 
            else:
                status = "active"
            
            all_tokens.append({
                "user_id": user_id,
                "username": token_data.get("username", "Unknown"),
                "token_type": token_data.get("token_type", "sharekhan_daily"),
                "status": status,
                "expires_at": token_data["expires_at"],
                "last_used": token_data["last_used"]
            })
        
        logger.info(f"All user tokens requested by admin: {current_user['email']}")
        
        return {
            "success": True,
            "tokens": all_tokens,
            "total_users": len(all_tokens),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"All user tokens error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch all user tokens"
        ) 
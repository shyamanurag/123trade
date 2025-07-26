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
router = APIRouter(prefix="/v1/auth-tokens", tags=["token-management"])

# Pydantic Models
class DailyTokenSubmission(BaseModel):
    token: str
    broker_type: str = "zerodha"
    user_id: Optional[str] = None
    expires_at: Optional[str] = None

class TokenStatusResponse(BaseModel):
    zerodha_status: str
    zerodha_expires_at: Optional[str]
    last_updated: str

# Mock token storage (replace with database in production)
MOCK_TOKENS = {
    "user_001": {
        "zerodha_token": "mock_token_123",
        "broker_type": "zerodha", 
        "status": "active",
        "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
        "updated_at": datetime.now().isoformat(),
        "username": "Demo User",
        "email": "demo@trade123.com"
    },
    "admin_001": {
        "zerodha_token": "mock_admin_token_456",
        "broker_type": "zerodha",
        "status": "expiring", 
        "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
        "updated_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "username": "Admin User",
        "email": "admin@trade123.com"
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
            "zerodha_token": token_data.token,
            "broker_type": token_data.broker_type,
            "status": "active",
            "expires_at": expires_at,
            "updated_at": datetime.now().isoformat(),
            "username": current_user.get("name", "Unknown"),
            "email": current_user.get("email", "unknown@example.com")
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
            last_updated=user_token["updated_at"]
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
                "email": token_data.get("email", "unknown@example.com"),
                "broker_type": token_data["broker_type"],
                "status": status,
                "expires_at": token_data["expires_at"],
                "updated_at": token_data["updated_at"]
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
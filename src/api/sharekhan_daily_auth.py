"""
ShareKhan Daily Authentication System
Handles daily request token submission and session management
100% REAL PRODUCTION AUTHENTICATION - NO SIMULATION
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import logging
import os
import json
import asyncio
from dataclasses import dataclass

from src.core.dependencies import get_orchestrator
from src.config.database import get_redis
import urllib.parse
from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
from brokers.sharekhan import ShareKhanIntegration

logger = logging.getLogger(__name__)

router = APIRouter()

# Data Models
class DailyAuthRequest(BaseModel):
    user_id: int
    sharekhan_client_id: str
    request_token: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

class TokenValidationRequest(BaseModel):
    user_id: int
    sharekhan_client_id: str

class AuthUrlRequest(BaseModel):
    user_id: int
    redirect_uri: Optional[str] = None

@dataclass
class DailyAuthSession:
    """Daily authentication session data"""
    user_id: int
    sharekhan_client_id: str
    request_token: str
    access_token: Optional[str] = None
    session_token: Optional[str] = None
    authenticated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_valid: bool = False
    last_error: Optional[str] = None

# In-memory session storage (production uses Redis with TTL; this is fallback)
daily_auth_sessions: Dict[str, DailyAuthSession] = {}

def get_session_key(user_id: int, client_id: str) -> str:
    """Generate session key for user+client combination"""
    return f"{user_id}_{client_id}"

# Redis-backed persistence helpers
async def _save_session(session: DailyAuthSession):
    """Persist session to Redis with TTL; fallback to in-memory map."""
    try:
        redis = await get_redis()
        session_key = get_session_key(session.user_id, session.sharekhan_client_id)
        # Always update in-memory fallback
        daily_auth_sessions[session_key] = session
        if not redis:
            return
        payload = {
            "user_id": session.user_id,
            "sharekhan_client_id": session.sharekhan_client_id,
            "request_token": session.request_token,
            "access_token": session.access_token,
            "session_token": session.session_token,
            "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "is_valid": session.is_valid,
            "last_error": session.last_error,
        }
        ttl_seconds = 0
        if session.expires_at:
            ttl_seconds = max(1, int((session.expires_at - datetime.now()).total_seconds()))
        key = f"sharekhan:session:{session_key}"
        await redis.set(key, json.dumps(payload))
        if ttl_seconds > 0:
            await redis.expire(key, ttl_seconds)
    except Exception as e:
        logger.warning(f"Session save fallback to memory only: {e}")

async def _load_session(user_id: int, client_id: str) -> Optional[DailyAuthSession]:
    """Load session from Redis; fallback to in-memory map."""
    try:
        session_key = get_session_key(user_id, client_id)
        redis = await get_redis()
        if redis:
            key = f"sharekhan:session:{session_key}"
            raw = await redis.get(key)
            if raw:
                data = json.loads(raw)
                authed = datetime.fromisoformat(data["authenticated_at"]) if data.get("authenticated_at") else None
                exp = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
                return DailyAuthSession(
                    user_id=data["user_id"],
                    sharekhan_client_id=data["sharekhan_client_id"],
                    request_token=data.get("request_token", ""),
                    access_token=data.get("access_token"),
                    session_token=data.get("session_token"),
                    authenticated_at=authed,
                    expires_at=exp,
                    is_valid=bool(data.get("is_valid", False)),
                    last_error=data.get("last_error")
                )
        return daily_auth_sessions.get(session_key)
    except Exception as e:
        logger.warning(f"Session load failed, using memory: {e}")
        session_key = get_session_key(user_id, client_id)
        return daily_auth_sessions.get(session_key)

@router.get("/auth/daily-url")
async def generate_daily_auth_url(request: AuthUrlRequest):
    """
    Generate ShareKhan authentication URL for daily login
    User must visit this URL daily to get request token
    """
    try:
        # Get production ShareKhan API key
        api_key = os.getenv('SHAREKHAN_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="ShareKhan API key not configured")
        
        # Use provided redirect URI or default from PUBLIC_BASE_URL
        public_base = os.getenv('PUBLIC_BASE_URL', 'https://trade123-edtd2.ondigitalocean.app').rstrip('/')
        redirect_uri = request.redirect_uri or f"{public_base}/auth/sharekhan/callback"
        
        # Generate state parameter for security
        import uuid
        state = str(uuid.uuid4())
        
        # ShareKhan authorization URL (CORRECTED: using newtrade.sharekhan.com)
        auth_url = (
            "https://newtrade.sharekhan.com/api/login"
            f"?api_key={api_key}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
            f"&state={state}"
            f"&response_type=code"
        )
        
        logger.info(f"🔗 Generated daily auth URL for user {request.user_id}")
        
        return {
            "success": True,
            "auth_url": auth_url,
            "state": state,
            "instructions": {
                "step_1": "Click the authorization URL above",
                "step_2": "Login with your ShareKhan credentials",
                "step_3": "After successful login, you'll be redirected",
                "step_4": "Copy the 'request_token' from the redirected URL",
                "step_5": "Submit the request_token using the /submit-daily-token endpoint"
            },
            "example_callback": f"{redirect_uri}?request_token=YOUR_TOKEN_HERE&action=login&status=success",
            "note": "⚠️ This token is valid only for TODAY and must be renewed daily",
            "validity": "24 hours from login",
            "api_key_preview": f"{api_key[:8]}..." if api_key else "Not configured"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate daily auth URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.post("/auth/submit-daily-token")
async def submit_daily_token(
    request: DailyAuthRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Submit daily request token and authenticate with ShareKhan
    This establishes the authenticated session for live trading
    """
    try:
        logger.info(f"🔐 Processing daily token submission for user {request.user_id}")
        
        # Get ShareKhan credentials
        api_key = request.api_key or os.getenv('SHAREKHAN_API_KEY')
        api_secret = request.api_secret or os.getenv('SHAREKHAN_SECRET_KEY')
        
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=400, 
                detail="ShareKhan API credentials required (api_key and api_secret)"
            )
        
        # Create ShareKhan integration instance
        sharekhan_client = ShareKhanIntegration(
            api_key=api_key,
            secret_key=api_secret,
            customer_id=request.sharekhan_client_id
        )
        
        # Authenticate with request token
        auth_result = await sharekhan_client.authenticate(request_token=request.request_token)
        
        if auth_result:
            # Create session record
            session = DailyAuthSession(
                user_id=request.user_id,
                sharekhan_client_id=request.sharekhan_client_id,
                request_token=request.request_token,
                access_token=sharekhan_client.access_token,
                session_token=sharekhan_client.session_token,
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),  # ShareKhan tokens typically expire in 24 hours
                is_valid=True
            )
            
            # Store session (Redis + in-memory)
            await _save_session(session)
            
            # Update orchestrator with authenticated client
            if orchestrator.sharekhan_integration:
                orchestrator.sharekhan_integration.access_token = sharekhan_client.access_token
                orchestrator.sharekhan_integration.session_token = sharekhan_client.session_token
                orchestrator.sharekhan_integration.is_authenticated = True
            
            logger.info(f"✅ Daily authentication successful for user {request.user_id}")
            
            # Test data fetching to verify authentication
            try:
                test_symbols = ["RELIANCE", "TCS", "INFY"]
                quotes = await sharekhan_client.get_market_quote(test_symbols)
                test_success = len(quotes) > 0
            except Exception as e:
                logger.warning(f"⚠️ Authentication successful but data test failed: {e}")
                test_success = False
            
            return {
                "success": True,
                "message": "Daily authentication completed successfully",
                "session_details": {
                    "user_id": request.user_id,
                    "sharekhan_client_id": request.sharekhan_client_id,
                    "authenticated_at": session.authenticated_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "access_token_preview": f"{session.access_token[:8]}..." if session.access_token else None,
                    "data_test_success": test_success
                },
                "status": "AUTHENTICATED",
                "next_steps": [
                    "System is now ready for live trading",
                    "All market data endpoints will work",
                    "Position sync and strategy recommendations are active",
                    "Token will expire in 24 hours - resubmit tomorrow"
                ]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="ShareKhan authentication failed. Please check your request token and try again."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Daily token submission failed: {e}")
        
        # Store failed session for debugging
        session = DailyAuthSession(
            user_id=request.user_id,
            sharekhan_client_id=request.sharekhan_client_id,
            request_token=request.request_token,
            is_valid=False,
            last_error=str(e)
        )
        session_key = get_session_key(request.user_id, request.sharekhan_client_id)
        daily_auth_sessions[session_key] = session
        
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/auth/session-status/{user_id}")
async def get_session_status(
    user_id: int,
    sharekhan_client_id: str
):
    """
    Check the status of daily authentication session
    Shows whether user needs to resubmit token
    """
    try:
        session = await _load_session(user_id, sharekhan_client_id)
        
        if not session:
            return {
                "success": True,
                "status": "NO_SESSION",
                "message": "No authentication session found",
                "authenticated": False,
                "action_required": "Submit daily authentication token",
                "auth_url_endpoint": "/api/sharekhan-auth/auth/daily-url"
            }
        
        # Check if session is still valid
        now = datetime.now()
        is_expired = session.expires_at and now > session.expires_at
        
        if is_expired:
            session.is_valid = False
            session.last_error = "Session expired"
        
        status_info = {
            "success": True,
            "status": "AUTHENTICATED" if session.is_valid else "EXPIRED" if is_expired else "FAILED",
            "authenticated": session.is_valid,
            "user_id": session.user_id,
            "sharekhan_client_id": session.sharekhan_client_id,
            "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "last_error": session.last_error,
            "time_until_expiry": str(session.expires_at - now) if session.expires_at and not is_expired else None
        }
        
        if not session.is_valid:
            status_info["action_required"] = "Submit new daily authentication token"
            status_info["auth_url_endpoint"] = "/api/sharekhan-auth/auth/daily-url"
        
        return status_info
        
    except Exception as e:
        logger.error(f"❌ Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

@router.post("/auth/refresh-session")
async def refresh_session(
    request: TokenValidationRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Refresh authentication session if still valid
    Useful for extending session or reconnecting after temporary disconnection
    """
    try:
        session_key = get_session_key(request.user_id, request.sharekhan_client_id)
        session = daily_auth_sessions.get(session_key)
        
        if not session or not session.is_valid:
            raise HTTPException(
                status_code=400,
                detail="No valid session found. Please submit daily authentication token."
            )
        
        # Check if session is expired
        if session.expires_at and datetime.now() > session.expires_at:
            session.is_valid = False
            raise HTTPException(
                status_code=400,
                detail="Session expired. Please submit new daily authentication token."
            )
        
        # Refresh orchestrator connection
        if orchestrator.sharekhan_integration:
            orchestrator.sharekhan_integration.access_token = session.access_token
            orchestrator.sharekhan_integration.session_token = session.session_token
            orchestrator.sharekhan_integration.is_authenticated = True
        
        logger.info(f"✅ Session refreshed for user {request.user_id}")
        
        return {
            "success": True,
            "message": "Session refreshed successfully",
            "status": "AUTHENTICATED",
            "expires_at": session.expires_at.isoformat() if session.expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session refresh failed: {str(e)}")

@router.get("/auth/all-sessions")
async def get_all_sessions():
    """
    Get status of all authentication sessions
    Useful for admin monitoring and debugging
    """
    try:
        sessions_status = []
        
        for session_key, session in daily_auth_sessions.items():
            now = datetime.now()
            is_expired = session.expires_at and now > session.expires_at
            
            sessions_status.append({
                "session_key": session_key,
                "user_id": session.user_id,
                "sharekhan_client_id": session.sharekhan_client_id,
                "status": "AUTHENTICATED" if session.is_valid and not is_expired else "EXPIRED" if is_expired else "FAILED",
                "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "time_until_expiry": str(session.expires_at - now) if session.expires_at and not is_expired else None,
                "last_error": session.last_error
            })
        
        return {
            "success": True,
            "total_sessions": len(sessions_status),
            "active_sessions": len([s for s in sessions_status if s["status"] == "AUTHENTICATED"]),
            "expired_sessions": len([s for s in sessions_status if s["status"] == "EXPIRED"]),
            "failed_sessions": len([s for s in sessions_status if s["status"] == "FAILED"]),
            "sessions": sessions_status
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get all sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@router.delete("/auth/clear-session/{user_id}")
async def clear_session(
    user_id: int,
    sharekhan_client_id: str
):
    """
    Clear authentication session for user
    Useful for logout or forcing re-authentication
    """
    try:
        session_key = get_session_key(user_id, sharekhan_client_id)
        # Remove from Redis
        try:
            redis = await get_redis()
            if redis:
                await redis.delete(f"sharekhan:session:{session_key}")
        except Exception:
            pass
        # Remove from fallback memory
        if session_key in daily_auth_sessions:
            del daily_auth_sessions[session_key]
            logger.info(f"✅ Session cleared for user {user_id}")
            
            return {
                "success": True,
                "message": f"Session cleared for user {user_id}",
                "status": "CLEARED"
            }
        else:
            return {
                "success": True,
                "message": f"No session found for user {user_id}",
                "status": "NO_SESSION"
            }
        
    except Exception as e:
        logger.error(f"❌ Failed to clear session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")

# Utility function to get authenticated client for other services
async def get_authenticated_sharekhan_client(user_id: int, client_id: str) -> Optional[ShareKhanIntegration]:
    """
    Get authenticated ShareKhan client for user
    Used by other services to access live data
    """
    try:
        session = await _load_session(user_id, client_id)
        
        if not session or not session.is_valid:
            return None
        
        # Check if session is expired
        if session.expires_at and datetime.now() > session.expires_at:
            session.is_valid = False
            return None
        
        # Create authenticated client
        sharekhan_client = ShareKhanIntegration(
            api_key=os.getenv('SHAREKHAN_API_KEY'),
            secret_key=os.getenv('SHAREKHAN_SECRET_KEY'),
            customer_id=client_id
        )
        
        # Set authentication tokens
        sharekhan_client.access_token = session.access_token
        sharekhan_client.session_token = session.session_token
        sharekhan_client.is_authenticated = True
        
        return sharekhan_client
        
    except Exception as e:
        logger.error(f"❌ Failed to get authenticated client: {e}")
        return None
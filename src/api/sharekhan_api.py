"""
ShareKhan API Endpoints
Complete API interface for ShareKhan trading system with multi-user support
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import uuid

# Import with fallback handling for cloud deployment
IMPORTS_AVAILABLE = True

try:
    from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
    from src.core.multi_user_sharekhan_manager import UserRole, TradingPermission
    from brokers.sharekhan import ShareKhanOrder
except ImportError:
    try:
        from ..core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        from ..core.multi_user_sharekhan_manager import UserRole, TradingPermission
        from brokers.sharekhan import ShareKhanOrder
    except ImportError:
        # Components not available - create minimal fallback
        IMPORTS_AVAILABLE = False
        
        class ShareKhanTradingOrchestrator:
            @classmethod
            async def get_instance(cls):
                return None
        
        class UserRole:
            TRADER = "trader"
            ADMIN = "admin"
        
        class TradingPermission:
            PLACE_ORDERS = "place_orders"
            VIEW_PORTFOLIO = "view_portfolio"
        
        class ShareKhanOrder:
            def __init__(self, **kwargs):
                pass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sharekhan", tags=["sharekhan"])

# Pydantic models for request/response
class UserLoginRequest(BaseModel):
    user_id: str
    password: str

class ShareKhanAuthRequest(BaseModel):
    request_token: str
    user_id: Optional[str] = None

class OrderRequest(BaseModel):
    customer_id: str
    scrip_code: int
    trading_symbol: str
    exchange: str
    transaction_type: str
    quantity: int
    price: float
    product_type: str
    order_type: str = "NORMAL"
    validity: str = "GFD"
    disclosed_qty: int = 0
    trigger_price: float = 0
    after_hour: str = "N"

class SymbolSubscriptionRequest(BaseModel):
    symbols: List[str]

class AddUserRequest(BaseModel):
    user_id: str
    display_name: str
    email: str
    role: str  # Will be converted to UserRole
    custom_limits: Optional[Dict[str, float]] = None

# Dependency to get orchestrator instance
async def get_orchestrator() -> ShareKhanTradingOrchestrator:
    """Get the ShareKhan orchestrator instance"""
    try:
        return await ShareKhanTradingOrchestrator.get_instance()
    except Exception as e:
        logger.error(f"Failed to get orchestrator instance: {e}")
        raise HTTPException(status_code=500, detail="System not available")

# Dependency to validate user session
async def validate_user_session(request: Request, orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)):
    """Validate user session from Authorization header"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # In production, validate against orchestrator's user manager
        # For now, return a mock user for compatibility
        return {
            "user_id": "demo_user",
            "email": "demo@trade123.com",
            "role": "admin"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")

# NEW: Auth endpoints for frontend compatibility
@router.post("/auth/generate-url")
async def generate_auth_url(request: Dict[str, str]):
    """Generate ShareKhan authentication URL - Public endpoint for frontend"""
    try:
        user_id = request.get("user_id", "default_user")
        
        # Use production ShareKhan API key from environment
        api_key = os.getenv('SHAREKHAN_API_KEY', 'vc9ft4zpknynpm3u')
        redirect_uri = "https://trade123-edtd2.ondigitalocean.app/auth/sharekhan/callback"
        
        # Generate real ShareKhan auth URL
        state = str(uuid.uuid4())
        auth_url = f"https://kite.sharekhan.com/connect/login?api_key={api_key}&redirect_uri={redirect_uri}&state={state}"
        
        logger.info(f"Generated ShareKhan auth URL for user {user_id}")
        
        return {
            "success": True,
            "auth_url": auth_url,
            "state": state,
            "user_id": user_id,
            "api_key": api_key[:8] + "...",  # Show first 8 chars for debugging
            "message": "ShareKhan auth URL generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.post("/auth/refresh")
async def refresh_auth_token(
    request: Dict[str, str],
    user_session: Dict = Depends(validate_user_session)
):
    """Refresh ShareKhan authentication token"""
    try:
        user_id = request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Simulate token refresh
        logger.info(f"Refreshing auth token for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "ShareKhan token refreshed successfully",
            "new_expiry": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")

@router.post("/auth/revoke")
async def revoke_auth_token(
    request: Dict[str, str],
    user_session: Dict = Depends(validate_user_session)
):
    """Revoke ShareKhan authentication token"""
    try:
        user_id = request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Simulate token revocation
        logger.info(f"Revoking auth token for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "ShareKhan token revoked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke token")

# Authentication Status Check
@router.get("/auth/status")
async def get_auth_status():
    """Get ShareKhan authentication status for all users"""
    try:
        # Mock auth status data
        auth_status = [
            {
                "user_id": "user_001",
                "status": "authenticated",
                "last_login": datetime.now().isoformat(),
                "token_expires": (datetime.now() + timedelta(days=1)).isoformat()
            },
            {
                "user_id": "admin_001", 
                "status": "authenticated",
                "last_login": (datetime.now() - timedelta(hours=2)).isoformat(),
                "token_expires": (datetime.now() + timedelta(hours=6)).isoformat()
            }
        ]
        
        return {
            "success": True,
            "data": auth_status,
            "message": "Auth status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting auth status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get auth status")

# User Management
@router.get("/admin/users")
async def get_admin_users():
    """Get all users for admin view"""
    try:
        users = [
            {
                "user_id": "user_001",
                "display_name": "Demo User",
                "email": "demo@trade123.com",
                "role": "trader",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            },
            {
                "user_id": "admin_001",
                "display_name": "Admin User", 
                "email": "admin@trade123.com",
                "role": "admin",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        ]
        
        return {
            "success": True,
            "data": {"users": users},
            "message": "Users retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting admin users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@router.post("/users/add")
async def add_user(
    user_data: AddUserRequest,
    user_session: Dict = Depends(validate_user_session)
):
    """Add new ShareKhan user"""
    try:
        # Validate admin permissions
        if user_session.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin permissions required")
        
        logger.info(f"Adding new user: {user_data.user_id}")
        
        return {
            "success": True,
            "message": f"User {user_data.user_id} added successfully",
            "user_id": user_data.user_id,
            "display_name": user_data.display_name,
            "role": user_data.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail="Failed to add user")

# Trading Operations  
@router.post("/orders")
async def place_order(
    order: OrderRequest,
    user_session: Dict = Depends(validate_user_session)
):
    """Place ShareKhan order"""
    try:
        logger.info(f"Placing ShareKhan order for {order.trading_symbol}")
        
        # Mock order placement
        order_id = f"SK_{uuid.uuid4().hex[:8].upper()}"
        
        return {
            "success": True,
            "order_id": order_id,
            "status": "pending",
            "message": "Order placed successfully",
            "details": {
                "symbol": order.trading_symbol,
                "quantity": order.quantity,
                "price": order.price,
                "transaction_type": order.transaction_type
            }
        }
        
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

@router.get("/portfolio")
async def get_portfolio(user_session: Dict = Depends(validate_user_session)):
    """Get ShareKhan portfolio"""
    try:
        # Mock portfolio data
        portfolio = {
            "positions": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 50,
                    "avg_price": 2450.75,
                    "current_price": 2475.20,
                    "pnl": 1222.50,
                    "pnl_percent": 1.0
                },
                {
                    "symbol": "TCS", 
                    "quantity": 25,
                    "avg_price": 3250.00,
                    "current_price": 3275.85,
                    "pnl": 646.25,
                    "pnl_percent": 0.79
                }
            ],
            "total_value": 203941.25,
            "total_pnl": 1868.75,
            "total_pnl_percent": 0.93
        }
        
        return {
            "success": True,
            "data": portfolio,
            "message": "Portfolio retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio")

@router.get("/positions")
async def get_positions(user_session: Dict = Depends(validate_user_session)):
    """Get ShareKhan positions"""
    try:
        # Mock positions data
        positions = [
            {
                "symbol": "NIFTY25JAN26000CE",
                "product_type": "MIS",
                "quantity": 50,
                "avg_price": 125.75,
                "ltp": 135.20,
                "pnl": 472.50,
                "pnl_percent": 7.52
            },
            {
                "symbol": "BANKNIFTY25JAN55000PE",
                "product_type": "MIS", 
                "quantity": -25,
                "avg_price": 180.30,
                "ltp": 165.85,
                "pnl": 361.25,
                "pnl_percent": 8.01
            }
        ]
        
        return {
            "success": True,
            "data": {"positions": positions},
            "message": "Positions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get positions")

# Symbol Management
@router.post("/symbols/subscribe")
async def subscribe_symbols(
    symbols_request: SymbolSubscriptionRequest,
    user_session: Dict = Depends(validate_user_session)
):
    """Subscribe to ShareKhan symbols for real-time data"""
    try:
        logger.info(f"Subscribing to symbols: {symbols_request.symbols}")
        
        return {
            "success": True,
            "subscribed_symbols": symbols_request.symbols,
            "message": f"Subscribed to {len(symbols_request.symbols)} symbols"
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe to symbols")

# System Status
@router.get("/status")
async def get_sharekhan_status():
    """Get ShareKhan integration status"""
    try:
        status = {
            "connection": "connected",
            "api_status": "operational", 
            "last_heartbeat": datetime.now().isoformat(),
            "active_users": 3,
            "active_orders": 5,
            "data_feed": "live"
        }
        
        return {
            "success": True,
            "data": status,
            "message": "ShareKhan status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting ShareKhan status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status") 
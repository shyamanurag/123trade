"""
ShareKhan API Endpoints
Complete API interface for ShareKhan trading system with multi-user support
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import asyncio

# Fixed import paths
try:
    from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
    from src.core.multi_user_sharekhan_manager import UserRole, TradingPermission
    from brokers.sharekhan import ShareKhanOrder
except ImportError:
    # Fallback imports
    from ..core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
    from ..core.multi_user_sharekhan_manager import UserRole, TradingPermission
    from ...brokers.sharekhan import ShareKhanOrder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sharekhan", tags=["sharekhan"])

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
        
        access_token = auth_header.split(" ")[1]
        session = await orchestrator.validate_user_session(access_token)
        
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(status_code=500, detail="Session validation failed")

# AUTHENTICATION ENDPOINTS

@router.post("/auth/login")
async def login_user(
    request: UserLoginRequest,
    req: Request,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Authenticate user and create session"""
    try:
        ip_address = req.client.host if req.client else None
        
        result = await orchestrator.authenticate_user(
            user_id=request.user_id,
            password=request.password,
            ip_address=ip_address
        )
        
        if result.get("success"):
            logger.info(f"✅ User login successful: {request.user_id}")
            return JSONResponse(content=result)
        else:
            logger.warning(f"❌ User login failed: {request.user_id}")
            raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/logout")
async def logout_user(
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Logout user and terminate session"""
    try:
        if orchestrator.multi_user_manager:
            success = await orchestrator.multi_user_manager.terminate_session(session.session_id)
            
            if success:
                return {"success": True, "message": "Logged out successfully"}
            else:
                return {"success": False, "error": "Session termination failed"}
        else:
            return {"success": False, "error": "Multi-user system not available"}
            
    except Exception as e:
        logger.error(f"Logout endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/sharekhan")
async def authenticate_sharekhan(
    request: ShareKhanAuthRequest,
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Authenticate ShareKhan integration with request token"""
    try:
        result = await orchestrator.authenticate_sharekhan(
            request_token=request.request_token,
            user_id=request.user_id or session.user_id
        )
        
        if result.get("success"):
            logger.info("✅ ShareKhan authentication successful")
            return JSONResponse(content=result)
        else:
            logger.error(f"❌ ShareKhan authentication failed: {result.get('error')}")
            raise HTTPException(status_code=401, detail=result.get("error", "ShareKhan authentication failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ShareKhan auth endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TRADING ENDPOINTS

@router.post("/orders/place")
async def place_order(
    request: OrderRequest,
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Place order for authenticated user"""
    try:
        # Check if user has order placement permission
        if TradingPermission.PLACE_ORDER not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to place orders")
        
        # Convert request to order data
        order_data = request.dict()
        
        result = await orchestrator.place_order(
            user_id=session.user_id,
            order_data=order_data
        )
        
        if result.get("success"):
            logger.info(f"✅ Order placed for user {session.user_id}: {result.get('order_id')}")
            return JSONResponse(content=result)
        else:
            logger.error(f"❌ Order placement failed for user {session.user_id}: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Order placement failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Place order endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
async def get_portfolio(
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Get portfolio for authenticated user"""
    try:
        # Check if user has portfolio view permission
        if TradingPermission.VIEW_PORTFOLIO not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view portfolio")
        
        result = await orchestrator.get_portfolio(user_id=session.user_id)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Portfolio retrieval failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MARKET DATA ENDPOINTS

@router.post("/market-data/subscribe")
async def subscribe_symbols(
    request: SymbolSubscriptionRequest,
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Subscribe to market data for symbols"""
    try:
        # Check if user has market data permission
        if TradingPermission.VIEW_MARKET_DATA not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to access market data")
        
        result = await orchestrator.subscribe_to_symbols(
            symbols=request.symbols,
            user_id=session.user_id
        )
        
        if result.get("success"):
            logger.info(f"✅ Symbols subscribed for user {session.user_id}: {request.symbols}")
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Subscription failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscribe symbols endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-data/live/{symbol}")
async def get_live_data(
    symbol: str,
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Get live market data for symbol"""
    try:
        # Check if user has market data permission
        if TradingPermission.VIEW_MARKET_DATA not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to access market data")
        
        result = await orchestrator.get_live_data(symbol=symbol)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=404, detail=result.get("error", f"No data available for {symbol}"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live data endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ADMIN ENDPOINTS

@router.post("/admin/users/add")
async def add_user(
    request: AddUserRequest,
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Add new user (Admin only)"""
    try:
        # Check if user has admin permissions
        if TradingPermission.MANAGE_USERS not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to manage users")
        
        # Validate role
        try:
            role = UserRole(request.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
        
        if orchestrator.multi_user_manager:
            success = await orchestrator.multi_user_manager.add_user(
                user_id=request.user_id,
                display_name=request.display_name,
                email=request.email,
                role=role,
                custom_limits=request.custom_limits
            )
            
            if success:
                logger.info(f"✅ User added by admin {session.user_id}: {request.user_id}")
                return {"success": True, "message": f"User {request.user_id} added successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to add user")
        else:
            raise HTTPException(status_code=503, detail="Multi-user system not available")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add user endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/users")
async def list_users(
    session = Depends(validate_user_session),
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """List all users (Admin only)"""
    try:
        # Check if user has admin permissions
        if TradingPermission.MANAGE_USERS not in session.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions to manage users")
        
        if orchestrator.multi_user_manager:
            active_users = orchestrator.multi_user_manager.get_active_users()
            
            users_info = []
            for user_id in active_users:
                user_config = orchestrator.multi_user_manager.get_user_config(user_id)
                user_stats = orchestrator.multi_user_manager.get_user_stats(user_id)
                
                if user_config:
                    users_info.append({
                        "user_id": user_config.user_id,
                        "display_name": user_config.display_name,
                        "email": user_config.email,
                        "role": user_config.role.value,
                        "active": user_config.active,
                        "last_login": user_config.last_login.isoformat() if user_config.last_login else None,
                        "stats": {
                            "total_trades": user_stats.total_trades if user_stats else 0,
                            "daily_pnl": user_stats.daily_pnl if user_stats else 0.0,
                            "risk_violations": user_stats.risk_violations if user_stats else 0
                        }
                    })
            
            return {"success": True, "users": users_info}
        else:
            raise HTTPException(status_code=503, detail="Multi-user system not available")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List users endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# SYSTEM STATUS ENDPOINTS

@router.get("/status")
async def get_system_status(
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Get system status (Public endpoint)"""
    try:
        status = await orchestrator.get_system_status()
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"System status endpoint error: {e}")
        return JSONResponse(
            content={"error": str(e), "timestamp": datetime.now().isoformat()},
            status_code=500
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        orchestrator = await ShareKhanTradingOrchestrator.get_instance()
        
        return {
            "status": "healthy",
            "service": "ShareKhan Trading System",
            "timestamp": datetime.now().isoformat(),
            "initialized": orchestrator.is_initialized,
            "running": orchestrator.is_running
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "ShareKhan Trading System",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

# WEBSOCKET ENDPOINT (for real-time data)

@router.get("/ws")
async def websocket_info():
    """WebSocket connection information"""
    return {
        "message": "WebSocket endpoint for real-time data",
        "endpoint": "/ws/sharekhan",
        "authentication": "Required - pass access_token as query parameter",
        "supported_channels": ["market_data", "order_updates", "portfolio_updates"]
    }

# HTML DASHBOARD (for development/testing)

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Simple HTML dashboard for ShareKhan system"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShareKhan Trading System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .status-box { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .endpoint-list { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .endpoint { margin: 10px 0; padding: 10px; background: white; border-left: 4px solid #007bff; }
            .method { font-weight: bold; color: #007bff; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #0056b3; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 ShareKhan Trading System</h1>
            
            <div class="status-box">
                <h3>System Overview</h3>
                <p><strong>Architecture:</strong> Unified ShareKhan API integration</p>
                <p><strong>Features:</strong> Multi-user management, Real-time data, Risk management</p>
                <p><strong>Status:</strong> <span id="system-status">Loading...</span></p>
            </div>
            
            <div class="grid">
                <div class="endpoint-list">
                    <h3>Authentication</h3>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/auth/login
                        <br><small>User authentication</small>
                    </div>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/auth/sharekhan
                        <br><small>ShareKhan API authentication</small>
                    </div>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/auth/logout
                        <br><small>Session termination</small>
                    </div>
                </div>
                
                <div class="endpoint-list">
                    <h3>Trading</h3>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/orders/place
                        <br><small>Place trading orders</small>
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /sharekhan/portfolio
                        <br><small>Get portfolio information</small>
                    </div>
                </div>
                
                <div class="endpoint-list">
                    <h3>Market Data</h3>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/market-data/subscribe
                        <br><small>Subscribe to symbols</small>
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /sharekhan/market-data/live/{symbol}
                        <br><small>Get live data</small>
                    </div>
                </div>
                
                <div class="endpoint-list">
                    <h3>Administration</h3>
                    <div class="endpoint">
                        <span class="method">POST</span> /sharekhan/admin/users/add
                        <br><small>Add new users</small>
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /sharekhan/admin/users
                        <br><small>List all users</small>
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <button onclick="checkStatus()">Check System Status</button>
                <button onclick="window.open('/docs', '_blank')">API Documentation</button>
            </div>
            
            <div id="status-details" style="margin-top: 20px; display: none;">
                <h3>System Status Details</h3>
                <pre id="status-json" style="background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;"></pre>
            </div>
        </div>
        
        <script>
            async function checkStatus() {
                try {
                    const response = await fetch('/sharekhan/status');
                    const status = await response.json();
                    
                    document.getElementById('system-status').textContent = status.orchestrator?.health_status || 'Unknown';
                    document.getElementById('status-json').textContent = JSON.stringify(status, null, 2);
                    document.getElementById('status-details').style.display = 'block';
                    
                } catch (error) {
                    document.getElementById('system-status').textContent = 'Error';
                    document.getElementById('status-json').textContent = 'Failed to fetch status: ' + error.message;
                    document.getElementById('status-details').style.display = 'block';
                }
            }
            
            // Check status on page load
            checkStatus();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content) 
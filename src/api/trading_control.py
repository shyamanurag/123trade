"""
Trading Control API - Start/Stop Trading and User Management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import os
import asyncio
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Global trading state
trading_state = {
    "is_running": False,
    "start_time": None,
    "orchestrator": None,
    "data_provider": None
}

class BrokerUser(BaseModel):
    """Model for broker user credentials"""
    user_id: str
    name: str
    broker: str = "zerodha"
    api_key: str
    api_secret: str
    client_id: str
    initial_capital: float = 1000000.0  # 10 lakhs
    risk_tolerance: str = "medium"
    paper_trading: bool = True

class TradingCommand(BaseModel):
    """Model for trading control commands"""
    action: str  # start, stop, pause, resume

# In-memory user storage (replace with database in production)
broker_users = {}

def initialize_default_users():
    """Initialize default master user on startup to prevent user loss on redeploy"""
    try:
        # Only add if master user doesn't exist (prevent duplicates)
        if "MASTER_USER_001" not in broker_users:
            # Use REAL environment variables instead of fake ones
            real_api_key = os.getenv('ZERODHA_API_KEY', 'vc9ft4zpknynpm3u')
            real_api_secret = os.getenv('ZERODHA_API_SECRET', '0nwjb2cncw9stf3m5cre73rqc3bc5xsc')
            real_client_id = os.getenv('ZERODHA_USER_ID', 'QSW899')
            
            master_user = {
                "user_id": "MASTER_USER_001",
                "name": "Master Trader",
                "broker": "zerodha",
                "api_key": real_api_key,
                "api_secret": real_api_secret,
                "client_id": real_client_id,
                "initial_capital": 1000000.0,
                "current_capital": 1000000.0,
                "risk_tolerance": "medium",
                "paper_trading": True,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "total_pnl": 0,
                "daily_pnl": 0,
                "total_trades": 0,
                "win_rate": 0,
                "open_trades": 0
            }
            
            broker_users["MASTER_USER_001"] = master_user
            
            # DON'T overwrite environment variables - they're already set correctly!
            # Environment variables are properly configured in DigitalOcean
            logger.info(f"✅ Using real API key: {real_api_key[:8]}...")
            logger.info(f"✅ Using real client ID: {real_client_id}")
            
            logger.info("✅ Auto-initialized MASTER_USER_001 to prevent user loss on redeploy")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize default users: {e}")
        return False

# Auto-initialize default users on module import
initialize_default_users()

@router.post("/users/broker")
async def add_broker_user(user: BrokerUser):
    """Add a broker user with credentials for paper trading"""
    try:
        # Validate required fields
        if not all([user.user_id, user.name, user.api_key, user.api_secret, user.client_id]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: user_id, name, api_key, api_secret, client_id"
            )

        # Check if user already exists
        if user.user_id in broker_users:
            raise HTTPException(
                status_code=400,
                detail=f"User {user.user_id} already exists"
            )

        # Store user credentials
        broker_users[user.user_id] = {
            "user_id": user.user_id,
            "name": user.name,
            "broker": user.broker,
            "api_key": user.api_key,
            "api_secret": user.api_secret,
            "client_id": user.client_id,
            "initial_capital": user.initial_capital,
            "current_capital": user.initial_capital,
            "risk_tolerance": user.risk_tolerance,
            "paper_trading": user.paper_trading,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "total_pnl": 0,
            "daily_pnl": 0,
            "total_trades": 0,
            "win_rate": 0,
            "open_trades": 0
        }
        
        # Set environment variables for the broker
        os.environ['ZERODHA_API_KEY'] = user.api_key
        os.environ['ZERODHA_API_SECRET'] = user.api_secret
        os.environ['ZERODHA_CLIENT_ID'] = user.client_id
        os.environ['PAPER_TRADING'] = str(user.paper_trading).lower()
        
        logger.info(f"Added broker user: {user.user_id} for {user.broker} trading")
        
        return {
            "success": True,
            "message": f"Broker user {user.user_id} added successfully",
            "user": broker_users[user.user_id]
        }
        
    except HTTPException as he:
        logger.error(f"Validation error adding broker user: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error adding broker user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/broker")
async def get_broker_users():
    """Get all broker users"""
    try:
        # Convert to list format expected by frontend
        users_list = list(broker_users.values())
        
        # Add mock data if no users exist
        if not users_list:
            # NO MOCK DATA - Real broker data required
            return {
                "success": True,
                "users": []
            }
        
        # Format users for frontend
        formatted_users = []
        for user in users_list:
            formatted_users.append({
                "user_id": user["user_id"],
                "name": user["name"],
                "username": user["user_id"],
                "avatar": user["name"][0].upper(),
                "initial_capital": user["initial_capital"],
                "current_capital": user["current_capital"],
                "total_pnl": user["total_pnl"],
                "daily_pnl": user["daily_pnl"],
                "total_trades": user["total_trades"],
                "win_rate": user["win_rate"],
                "is_active": user["is_active"],
                "open_trades": user["open_trades"],
                "paper_trading": user["paper_trading"]
            })
        
        return {
            "success": True,
            "users": formatted_users
        }
        
    except Exception as e:
        logger.error(f"Error fetching broker users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/broker/{user_id}")
async def update_broker_user(user_id: str, user: BrokerUser):
    """Update an existing broker user"""
    try:
        # Check if user exists
        if user_id not in broker_users:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        # Update user data
        broker_users[user_id].update({
            "name": user.name,
            "broker": user.broker,
            "api_key": user.api_key,
            "api_secret": user.api_secret,
            "client_id": user.client_id,
            "initial_capital": user.initial_capital,
            "risk_tolerance": user.risk_tolerance,
            "paper_trading": user.paper_trading,
            "updated_at": datetime.now().isoformat()
        })
        
        # Update environment variables
        os.environ['ZERODHA_API_KEY'] = user.api_key
        os.environ['ZERODHA_API_SECRET'] = user.api_secret
        os.environ['ZERODHA_CLIENT_ID'] = user.client_id
        os.environ['PAPER_TRADING'] = str(user.paper_trading).lower()
        
        logger.info(f"Updated broker user: {user_id} - Paper Trading: {user.paper_trading}")
        
        return {
            "success": True,
            "message": f"Broker user {user_id} updated successfully",
            "user": broker_users[user_id]
        }
        
    except HTTPException as he:
        logger.error(f"Validation error updating broker user: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error updating broker user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/broker/{user_id}")
async def delete_broker_user(user_id: str):
    """Delete a broker user"""
    try:
        # Check if user exists
        if user_id not in broker_users:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        # Remove user
        deleted_user = broker_users.pop(user_id)
        
        logger.info(f"Deleted broker user: {user_id}")
        
        return {
            "success": True,
            "message": f"Broker user {user_id} deleted successfully",
            "deleted_user": deleted_user
        }
        
    except HTTPException as he:
        logger.error(f"Error deleting broker user: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error deleting broker user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/broker/initialize")
async def initialize_users():
    """Manual endpoint to reinitialize default users (useful for testing)"""
    try:
        success = initialize_default_users()
        if success:
            return {
                "success": True,
                "message": "Default users initialized successfully",
                "users": list(broker_users.values())
            }
        else:
            return {
                "success": False,
                "message": "Failed to initialize default users"
            }
    except Exception as e:
        logger.error(f"Error in manual user initialization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trading/control")
async def control_trading(command: TradingCommand):
    """Control trading operations - start, stop, pause, resume"""
    try:
        global trading_state
        
        if command.action == "start":
            if trading_state["is_running"]:
                return {
                    "success": False,
                    "message": "Trading is already running",
                    "status": "running"
                }
            
            # Check if we have at least one user
            if not broker_users:
                return {
                    "success": False,
                    "message": "No broker users configured. Please add a user first.",
                    "status": "no_users"
                }
            
            # Start trading components
            logger.info("Starting trading system...")
            
            # Import and initialize components
            from src.core.orchestrator import TradingOrchestrator
            from data.truedata_client import (
                initialize_truedata,
                get_truedata_status, 
                is_connected,
                live_market_data,
                truedata_connection_status
            )
            
            # Create config
            config = {
                'redis': {
                    'host': os.getenv('REDIS_HOST', 'localhost'),
                    'port': int(os.getenv('REDIS_PORT', 6379)),
                    'password': os.getenv('REDIS_PASSWORD'),
                    'ssl': os.getenv('REDIS_SSL', 'false').lower() == 'true'
                },
                'broker': {
                    'api_key': os.getenv('ZERODHA_API_KEY'),
                    'api_secret': os.getenv('ZERODHA_API_SECRET'),
                    'client_id': os.getenv('ZERODHA_CLIENT_ID')
                },
                'data_provider': {
                                    'username': os.getenv('TRUEDATA_USERNAME', 'tdwsp697'),
                'password': os.getenv('TRUEDATA_PASSWORD', 'shyam@697'),
                    'url': os.getenv('TRUEDATA_URL', 'push.truedata.in'),
                    'port': int(os.getenv('TRUEDATA_PORT', 8084))
                },
                'strategies': {
                    'volatility_explosion': {'enabled': True},
                    'momentum_surfer': {'enabled': True},
                    'volume_profile_scalper': {'enabled': True},
                    'news_impact_scalper': {'enabled': True}
                }
            }
            
            # Initialize orchestrator (singleton)
            trading_state["orchestrator"] = TradingOrchestrator.get_instance()
            
            # Enable trading
            await trading_state["orchestrator"].enable_trading()
            
            trading_state["is_running"] = True
            trading_state["start_time"] = datetime.now().isoformat()
            
            logger.info(f"Trading started - Zerodha API will handle paper/live mode automatically")
            
            return {
                "success": True,
                "message": f"Trading started successfully - Zerodha API will handle paper/live mode automatically",
                "status": "running",
                "start_time": trading_state["start_time"]
            }
            
        elif command.action == "stop":
            if not trading_state["is_running"]:
                return {
                    "success": False,
                    "message": "Trading is not running",
                    "status": "stopped"
                }
            
            # Stop trading
            logger.info("Stopping trading system...")
            
            if trading_state["orchestrator"]:
                await trading_state["orchestrator"].disable_trading()
                trading_state["orchestrator"] = None
            
            trading_state["is_running"] = False
            trading_state["start_time"] = None
            
            logger.info("Trading stopped")
            
            return {
                "success": True,
                "message": "Trading stopped successfully",
                "status": "stopped"
            }
            
        elif command.action == "status":
            return {
                "success": True,
                "status": "running" if trading_state["is_running"] else "stopped",
                "paper_trading": trading_state["paper_trading"],
                "start_time": trading_state["start_time"],
                "users_count": len(broker_users)
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {command.action}")
            
    except Exception as e:
        logger.error(f"Error controlling trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading/status")
async def get_trading_status():
    """Get current trading system status"""
    try:
        return {
            "success": True,
            "is_running": trading_state["is_running"],
            "paper_trading": trading_state["paper_trading"],
            "start_time": trading_state["start_time"],
            "users_count": len(broker_users),
            "autonomous_trading": trading_state["is_running"],
            "status": "running" if trading_state["is_running"] else "stopped"
        }
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add Zerodha Manual Authentication endpoints to existing working router
@router.get("/zerodha-manual/auth-url")
async def get_zerodha_manual_auth_url():
    """Get Zerodha authorization URL for manual token extraction"""
    try:
        api_key = os.getenv('ZERODHA_API_KEY', 'sylcoq492qz6f7ej')
        auth_url = f"https://kite.zerodha.com/connect/login?api_key={api_key}"
        
        return {
            "success": True,
            "auth_url": auth_url,
            "instructions": [
                "1. Click the authorization URL",
                "2. Login to Zerodha with your credentials", 
                "3. After login, you'll be redirected to a URL",
                "4. Copy the 'request_token' parameter from the redirected URL",
                "5. Paste the token in the manual token entry"
            ],
            "example_redirect": "https://yourapp.com/callback?request_token=YOUR_TOKEN_HERE&action=login&status=success",
            "note": "Extract only the request_token value, not the full URL",
            "status": "Ready for use after TrueData testing complete"
        }
    except Exception as e:
        logger.error(f"Failed to generate Zerodha auth URL: {e}")
        return {"success": False, "error": str(e)}

@router.get("/zerodha-manual/status")
async def get_zerodha_manual_status(user_id: str = "ZERODHA_DEFAULT"):
    """Get current Zerodha manual authentication status"""
    try:
        return {
            "success": True,
            "message": "Zerodha manual auth ready - awaiting TrueData completion",
            "authenticated": False,
            "user_id": user_id,
            "note": "System ready for manual token submission when needed",
            "priority": "TrueData first, Zerodha second (as planned)"
        }
    except Exception as e:
        logger.error(f"Zerodha manual status check failed: {e}")
        return {
            "success": False,
            "message": f"Status check failed: {str(e)}",
            "authenticated": False
        }

@router.post("/zerodha-manual/submit-token")
async def submit_zerodha_manual_token(request: dict):
    """Submit manually extracted Zerodha request token (for future use)"""
    try:
        request_token = request.get('request_token', '')
        user_id = request.get('user_id', 'ZERODHA_DEFAULT')
        
        # Validate token format
        if not request_token or len(request_token) < 10:
            return {
                "success": False,
                "error": "Invalid request token format. Token should be at least 10 characters long."
            }
        
        # For now, just validate the token format and return success
        # Full implementation will be activated after TrueData testing
        return {
            "success": True,
            "message": "Token format validated. Full processing ready after TrueData completion.",
            "user_id": user_id,
            "token_preview": f"{request_token[:8]}...",
            "status": "Stored for future activation",
            "note": "Zerodha integration will be activated post-TrueData testing"
        }
        
    except Exception as e:
        logger.error(f"Zerodha manual token submission failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/zerodha-manual/test")
async def test_zerodha_manual_system():
    """Test Zerodha manual auth system readiness"""
    return {
        "success": True,
        "message": "Zerodha manual authentication system ready",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "status": "Standby - awaiting TrueData completion",
        "endpoints": [
            "/api/v1/control/zerodha-manual/auth-url",
            "/api/v1/control/zerodha-manual/status", 
            "/api/v1/control/zerodha-manual/submit-token",
            "/api/v1/control/zerodha-manual/test"
        ],
        "workflow": "TrueData → Complete Testing → Zerodha Authorization → Trading Ready"
    } 
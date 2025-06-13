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
    "data_provider": None,
    "paper_trading": True
}

class BrokerUser(BaseModel):
    """Model for broker user credentials"""
    user_id: str
    name: str
    broker: str = "zerodha"
    api_key: str
    api_secret: str
    client_id: str
    initial_capital: float = 100000.0
    risk_tolerance: str = "medium"
    paper_trading: bool = True

class TradingCommand(BaseModel):
    """Model for trading control commands"""
    action: str  # start, stop, pause, resume
    paper_trading: Optional[bool] = True

# In-memory user storage (replace with database in production)
broker_users = {}

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
            # Return empty list instead of mock data
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
                "open_trades": user["open_trades"]
            })
        
        return {
            "success": True,
            "users": formatted_users
        }
        
    except Exception as e:
        logger.error(f"Error fetching broker users: {e}")
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
            from core.orchestrator import TradingOrchestrator
            from data.truedata_provider import TrueDataProvider
            
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
                    'username': os.getenv('TRUEDATA_USERNAME', 'Trial106'),
                    'password': os.getenv('TRUEDATA_PASSWORD', 'shyam106'),
                    'url': os.getenv('TRUEDATA_URL', 'push.truedata.in'),
                    'port': int(os.getenv('TRUEDATA_PORT', 8086))
                },
                'strategies': {
                    'volatility_explosion': {'enabled': True},
                    'momentum_surfer': {'enabled': True},
                    'volume_profile_scalper': {'enabled': True},
                    'news_impact_scalper': {'enabled': True}
                },
                'paper_trading': command.paper_trading
            }
            
            # Initialize orchestrator
            trading_state["orchestrator"] = TradingOrchestrator(config)
            
            # Start orchestrator in background
            asyncio.create_task(trading_state["orchestrator"].start())
            
            trading_state["is_running"] = True
            trading_state["start_time"] = datetime.now().isoformat()
            trading_state["paper_trading"] = command.paper_trading
            
            logger.info(f"Trading started in {'PAPER' if command.paper_trading else 'LIVE'} mode")
            
            return {
                "success": True,
                "message": f"Trading started successfully in {'paper' if command.paper_trading else 'live'} mode",
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
                await trading_state["orchestrator"].stop()
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
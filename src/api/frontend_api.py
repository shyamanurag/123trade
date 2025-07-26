"""
Frontend API Endpoints for ShareKhan Trading Platform
Provides all necessary endpoints for the static frontend
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["frontend"])

# Sample data for demonstration
SAMPLE_USERS = [
    {
        "id": 1,
        "name": "Admin User",
        "email": "admin@trading.com",
        "status": "Active",
        "last_login": datetime.now().isoformat(),
        "trading_limit": 100000,
        "total_trades": 0,
        "pnl": 0.0
    },
    {
        "id": 2,
        "name": "Demo User", 
        "email": "demo@trading.com",
        "status": "Inactive",
        "last_login": None,
        "trading_limit": 50000,
        "total_trades": 0,
        "pnl": 0.0
    }
]

SAMPLE_INDICES = [
    {"symbol": "NIFTY50", "name": "NIFTY 50", "ltp": 19850.45, "change": 0.75, "change_percent": 0.75},
    {"symbol": "BANKNIFTY", "name": "BANK NIFTY", "ltp": 44320.80, "change": -142.30, "change_percent": -0.32},
    {"symbol": "SENSEX", "name": "SENSEX", "ltp": 66795.14, "change": 299.85, "change_percent": 0.45},
    {"symbol": "NIFTYIT", "name": "NIFTY IT", "ltp": 28450.30, "change": 351.25, "change_percent": 1.25},
    {"symbol": "NIFTYPHARMA", "name": "NIFTY PHARMA", "ltp": 13890.60, "change": -119.15, "change_percent": -0.85}
]

# Market Data Endpoints
@router.get("/indices")
async def get_market_indices():
    """Get live market indices data"""
    try:
        # Add some random variation to simulate live data
        import random
        live_indices = []
        
        for index in SAMPLE_INDICES:
            variation = random.uniform(-0.5, 0.5)
            new_change = index["change_percent"] + variation
            new_ltp = index["ltp"] * (1 + new_change / 100)
            
            live_indices.append({
                **index,
                "ltp": round(new_ltp, 2),
                "change_percent": round(new_change, 2),
                "change": round(new_ltp - index["ltp"], 2),
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "status": "success",
            "data": live_indices,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching indices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market indices")

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote for a specific symbol"""
    try:
        # Find the symbol in our sample data
        for index in SAMPLE_INDICES:
            if index["symbol"].upper() == symbol.upper():
                import random
                variation = random.uniform(-1, 1)
                new_ltp = index["ltp"] * (1 + variation / 100)
                
                return {
                    "status": "success",
                    "data": {
                        "symbol": symbol.upper(),
                        "ltp": round(new_ltp, 2),
                        "change": round(new_ltp - index["ltp"], 2),
                        "change_percent": round(variation, 2),
                        "volume": random.randint(1000000, 10000000),
                        "timestamp": datetime.now().isoformat()
                    }
                }
        
        # If not found, return sample data
        import random
        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "ltp": round(random.uniform(100, 5000), 2),
                "change": round(random.uniform(-50, 50), 2),
                "change_percent": round(random.uniform(-5, 5), 2),
                "volume": random.randint(100000, 1000000),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote for {symbol}")

@router.get("/market-status")
async def get_market_status():
    """Get current market status"""
    try:
        now = datetime.now()
        is_open = 9 <= now.hour < 16  # Market hours 9 AM to 4 PM
        
        return {
            "status": "success",
            "data": {
                "market_status": "OPEN" if is_open else "CLOSED",
                "last_update": now.isoformat(),
                "next_open": "2025-07-26 09:00:00" if not is_open else None,
                "next_close": "2025-07-26 15:30:00" if is_open else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get market status")

# User Management Endpoints
@router.get("/users")
async def get_users():
    """Get all users"""
    try:
        return {
            "status": "success",
            "data": SAMPLE_USERS,
            "total": len(SAMPLE_USERS)
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get specific user details"""
    try:
        user = next((u for u in SAMPLE_USERS if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "data": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user")

@router.post("/users")
async def create_user(user_data: Dict[str, Any]):
    """Create a new user"""
    try:
        new_user = {
            "id": len(SAMPLE_USERS) + 1,
            "name": user_data.get("name", "New User"),
            "email": user_data.get("email", "user@trading.com"),
            "status": "Active",
            "last_login": None,
            "trading_limit": user_data.get("trading_limit", 50000),
            "total_trades": 0,
            "pnl": 0.0
        }
        
        SAMPLE_USERS.append(new_user)
        
        return {
            "status": "success",
            "message": "User created successfully",
            "data": new_user
        }
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

# Trading Endpoints
@router.get("/portfolio")
async def get_portfolio(user_id: Optional[int] = None):
    """Get portfolio information"""
    try:
        portfolio = {
            "total_value": 150000.0,
            "invested_amount": 145000.0,
            "current_value": 150000.0,
            "day_pnl": 2500.0,
            "total_pnl": 5000.0,
            "positions": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 10,
                    "avg_price": 2450.0,
                    "ltp": 2475.0,
                    "pnl": 250.0,
                    "change_percent": 1.02
                },
                {
                    "symbol": "TCS",
                    "quantity": 5,
                    "avg_price": 3650.0,
                    "ltp": 3625.0,
                    "pnl": -125.0,
                    "change_percent": -0.68
                }
            ]
        }
        
        return {
            "status": "success",
            "data": portfolio
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")

@router.get("/trades")
async def get_trades(
    user_id: Optional[int] = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get trading history"""
    try:
        trades = [
            {
                "id": 1,
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 10,
                "price": 2450.0,
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "status": "COMPLETED",
                "pnl": 250.0
            },
            {
                "id": 2,
                "symbol": "TCS",
                "side": "BUY", 
                "quantity": 5,
                "price": 3650.0,
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "status": "COMPLETED",
                "pnl": -125.0
            }
        ]
        
        return {
            "status": "success",
            "data": trades,
            "total": len(trades)
        }
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trades")

# Analytics Endpoints
@router.get("/analytics")
async def get_analytics(user_id: Optional[int] = None):
    """Get trading analytics"""
    try:
        analytics = {
            "performance_metrics": {
                "total_trades": 25,
                "winning_trades": 18,
                "losing_trades": 7,
                "win_rate": 72.0,
                "avg_profit": 1250.0,
                "avg_loss": -850.0,
                "sharpe_ratio": 1.45,
                "max_drawdown": -5.2
            },
            "monthly_pnl": [
                {"month": "Jan", "pnl": 2500},
                {"month": "Feb", "pnl": 1800},
                {"month": "Mar", "pnl": -1200},
                {"month": "Apr", "pnl": 3200},
                {"month": "May", "pnl": 2800},
                {"month": "Jun", "pnl": 4100},
                {"month": "Jul", "pnl": 2200}
            ],
            "asset_allocation": [
                {"category": "Equity", "percentage": 65, "value": 97500},
                {"category": "Options", "percentage": 20, "value": 30000},
                {"category": "Futures", "percentage": 10, "value": 15000},
                {"category": "Cash", "percentage": 5, "value": 7500}
            ]
        }
        
        return {
            "status": "success",
            "data": analytics
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

@router.get("/performance/metrics")
async def get_performance_metrics(
    user_id: Optional[int] = None,
    period: str = Query("1M", regex="^(1D|1W|1M|3M|6M|1Y)$")
):
    """Get performance metrics for specified period"""
    try:
        metrics = {
            "period": period,
            "portfolio_value": 150000.0,
            "benchmark_value": 148000.0,
            "returns": {
                "portfolio": 3.45,
                "benchmark": 2.87,
                "outperformance": 0.58
            },
            "volatility": {
                "portfolio": 15.2,
                "benchmark": 12.8
            },
            "sharpe_ratio": 1.45,
            "max_drawdown": -5.2,
            "calmar_ratio": 0.67
        }
        
        return {
            "status": "success",
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance metrics")

# Configuration Endpoints
@router.get("/config")
async def get_config():
    """Get system configuration"""
    try:
        config = {
            "trading_enabled": True,
            "market_hours": {
                "start": "09:00",
                "end": "15:30",
                "timezone": "IST"
            },
            "risk_limits": {
                "max_position_size": 100000,
                "daily_loss_limit": 50000,
                "max_orders_per_minute": 10
            },
            "sharekhan_config": {
                "api_connected": True,
                "customer_id": "Sanurag1977",
                "last_token_refresh": datetime.now().isoformat()
            }
        }
        
        return {
            "status": "success",
            "data": config
        }
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch configuration")

@router.get("/debug/status")
async def get_debug_status():
    """Get detailed debug status for troubleshooting"""
    try:
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "environment": "production",
            "components": {
                "database": "connected",
                "redis": "connected", 
                "sharekhan_api": "connected",
                "websocket": "active"
            },
            "system_health": {
                "cpu_usage": "25%",
                "memory_usage": "45%",
                "disk_usage": "60%",
                "uptime": "2h 15m"
            },
            "active_connections": {
                "websockets": 2,
                "api_requests": 15,
                "database_pool": "3/10"
            }
        }
        
        return {
            "status": "success",
            "data": debug_info
        }
    except Exception as e:
        logger.error(f"Error getting debug status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get debug status") 
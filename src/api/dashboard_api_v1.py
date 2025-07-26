"""
Dashboard API v1 Endpoints for React Frontend
Provides dashboard data, analytics, and system metrics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import logging

from .auth_api import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["dashboard"])

def generate_mock_dashboard_data() -> Dict[str, Any]:
    """Generate mock dashboard data for demonstration"""
    
    # Generate realistic mock data
    base_portfolio_value = 500000
    todays_change = random.uniform(-2, 3)
    todays_pnl = base_portfolio_value * (todays_change / 100)
    
    return {
        "metrics": {
            "portfolio_value": base_portfolio_value + random.uniform(-10000, 20000),
            "portfolio_change": round(todays_change, 2),
            "todays_pnl": round(todays_pnl, 2),
            "pnl_percentage": round(todays_change, 2),
            "active_positions": random.randint(5, 15),
            "positions_change": random.randint(-2, 5),
            "connected_users": random.randint(3, 8)
        },
        "recent_trades": [
            {
                "id": f"trade_{i}",
                "symbol": random.choice(["NIFTY50", "BANKNIFTY", "RELIANCE", "INFY", "TCS"]),
                "side": random.choice(["BUY", "SELL"]),
                "quantity": random.randint(1, 100),
                "price": random.uniform(100, 3000),
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 120))).isoformat(),
                "status": random.choice(["COMPLETED", "PENDING", "CANCELLED"])
            }
            for i in range(5)
        ],
        "alerts": [
            {
                "id": f"alert_{i}",
                "title": random.choice([
                    "Market Volatility Alert",
                    "Position Limit Warning", 
                    "System Update Available",
                    "Risk Threshold Exceeded"
                ]),
                "message": random.choice([
                    "High volatility detected in NIFTY50",
                    "Position size approaching daily limit",
                    "System maintenance scheduled",
                    "Risk parameters need review"
                ]),
                "priority": random.choice(["high", "medium", "low"]),
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat()
            }
            for i in range(3)
        ],
        "performance_data": {
            "daily_pnl": [
                {
                    "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "pnl": random.uniform(-5000, 8000)
                }
                for i in range(30, 0, -1)
            ],
            "portfolio_growth": [
                {
                    "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "value": base_portfolio_value + random.uniform(-20000, 30000)
                }
                for i in range(30, 0, -1)
            ]
        }
    }

@router.get("/dashboard")
async def get_dashboard_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get comprehensive dashboard data"""
    try:
        logger.info(f"Dashboard data requested by user: {current_user['email']}")
        
        dashboard_data = generate_mock_dashboard_data()
        
        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat(),
            "user": current_user["email"]
        }
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch dashboard data"
        )

@router.get("/market-data")
async def get_market_data(symbol: Optional[str] = None):
    """Get market data for symbols"""
    try:
        if symbol:
            # Return data for specific symbol
            return {
                "symbol": symbol,
                "price": random.uniform(100, 3000),
                "change": random.uniform(-5, 5),
                "change_percent": random.uniform(-2, 2),
                "volume": random.randint(10000, 100000),
                "high": random.uniform(100, 3000),
                "low": random.uniform(100, 3000),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Return multiple symbols
            symbols = ["NIFTY50", "BANKNIFTY", "SENSEX", "RELIANCE", "INFY", "TCS"]
            return {
                "symbols": [
                    {
                        "symbol": sym,
                        "price": random.uniform(100, 3000),
                        "change": random.uniform(-5, 5),
                        "change_percent": random.uniform(-2, 2),
                        "volume": random.randint(10000, 100000),
                        "timestamp": datetime.now().isoformat()
                    }
                    for sym in symbols
                ],
                "symbol_count": len(symbols),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Market data error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch market data"
        )

@router.get("/market-data/indices")
async def get_live_indices():
    """Get live market indices data"""
    try:
        indices = [
            {
                "symbol": "NIFTY50",
                "name": "NIFTY 50",
                "price": 19850.45 + random.uniform(-100, 100),
                "change": random.uniform(-50, 50),
                "change_percent": random.uniform(-1, 1),
                "volume": random.randint(100000, 1000000),
                "high": 19950.75,
                "low": 19780.20,
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "BANKNIFTY", 
                "name": "BANK NIFTY",
                "price": 44320.80 + random.uniform(-200, 200),
                "change": random.uniform(-150, 150),
                "change_percent": random.uniform(-0.5, 0.5),
                "volume": random.randint(50000, 500000),
                "high": 44580.90,
                "low": 44120.50,
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "SENSEX",
                "name": "SENSEX",
                "price": 66795.14 + random.uniform(-300, 300),
                "change": random.uniform(-200, 200),
                "change_percent": random.uniform(-0.8, 0.8),
                "volume": random.randint(80000, 800000),
                "high": 67120.25,
                "low": 66540.80,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return {
            "indices": indices,
            "count": len(indices),
            "timestamp": datetime.now().isoformat(),
            "market_status": "OPEN" if 9 <= datetime.now().hour < 16 else "CLOSED"
        }
        
    except Exception as e:
        logger.error(f"Indices data error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch indices data"
        )

@router.get("/trades")
async def get_trades(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get trade history"""
    try:
        trades = [
            {
                "id": f"trade_{i}",
                "symbol": random.choice(["NIFTY50", "BANKNIFTY", "RELIANCE", "INFY", "TCS"]),
                "side": random.choice(["BUY", "SELL"]),
                "quantity": random.randint(1, 100),
                "price": round(random.uniform(100, 3000), 2),
                "amount": round(random.uniform(1000, 50000), 2),
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
                "status": random.choice(["COMPLETED", "PENDING", "CANCELLED"]),
                "user_id": current_user["user_id"]
            }
            for i in range(limit)
        ]
        
        return {
            "trades": trades,
            "total": len(trades),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Trades data error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch trades data"
        )

@router.get("/analytics")
async def get_analytics(
    timeframe: str = "1d",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get analytics data"""
    try:
        # Generate analytics based on timeframe
        days = 1 if timeframe == "1d" else 7 if timeframe == "1w" else 30
        
        analytics = {
            "performance": {
                "total_pnl": random.uniform(-10000, 20000),
                "win_rate": random.uniform(0.45, 0.75),
                "avg_profit": random.uniform(500, 2000),
                "avg_loss": random.uniform(-1000, -200),
                "total_trades": random.randint(10, 100),
                "profitable_trades": random.randint(5, 60)
            },
            "risk_metrics": {
                "max_drawdown": random.uniform(-5000, -1000),
                "sharpe_ratio": random.uniform(0.5, 2.0),
                "volatility": random.uniform(0.1, 0.4),
                "var_95": random.uniform(-2000, -500)
            },
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "analytics": analytics,
            "user_id": current_user["user_id"]
        }
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch analytics data"
        ) 
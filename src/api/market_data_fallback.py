"""
Market Data Fallback API
Provides mock market data when real feeds are unavailable
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging
from datetime import datetime
import random

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market-data-fallback"])

# Mock market data with realistic values
MOCK_MARKET_DATA = {
    "NIFTY": {"symbol": "NIFTY", "ltp": 19800.50, "change": 150.25, "change_percent": 0.76, "volume": 1250000},
    "BANKNIFTY": {"symbol": "BANKNIFTY", "ltp": 44250.75, "change": -120.50, "change_percent": -0.27, "volume": 850000},
    "SENSEX": {"symbol": "SENSEX", "ltp": 66500.30, "change": 200.15, "change_percent": 0.30, "volume": 950000},
    "RELIANCE": {"symbol": "RELIANCE", "ltp": 2450.30, "change": 25.80, "change_percent": 1.06, "volume": 2100000},
    "TCS": {"symbol": "TCS", "ltp": 3850.60, "change": -15.40, "change_percent": -0.40, "volume": 980000},
    "HDFCBANK": {"symbol": "HDFCBANK", "ltp": 1680.25, "change": 12.75, "change_percent": 0.76, "volume": 1850000},
    "INFY": {"symbol": "INFY", "ltp": 1520.45, "change": 8.90, "change_percent": 0.59, "volume": 1320000},
    "ICICIBANK": {"symbol": "ICICIBANK", "ltp": 950.80, "change": 7.20, "change_percent": 0.76, "volume": 1650000},
    "SBIN": {"symbol": "SBIN", "ltp": 590.15, "change": -3.85, "change_percent": -0.65, "volume": 2850000},
    "ADANIPORTS": {"symbol": "ADANIPORTS", "ltp": 1180.40, "change": 18.60, "change_percent": 1.60, "volume": 890000}
}

MARKET_STATUS = {
    "is_open": True,
    "market_type": "NORMAL",
    "session": "REGULAR",
    "open_time": "09:15:00",
    "close_time": "15:30:00",
    "last_updated": datetime.now().isoformat()
}

def add_realistic_variation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add small realistic variations to mock data"""
    # Add small random variations (0.1%)
    variation = random.uniform(-0.001, 0.001)
    new_ltp = data["ltp"] * (1 + variation)
    price_change = new_ltp - data["ltp"]
    
    return {
        **data,
        "ltp": round(new_ltp, 2),
        "change": round(data["change"] + price_change, 2),
        "change_percent": round(((new_ltp - (data["ltp"] - data["change"])) / (data["ltp"] - data["change"])) * 100, 2),
        "timestamp": datetime.now().isoformat(),
        "data_source": "fallback_mock"
    }

@router.get("/indices")
async def get_market_indices():
    """Get major market indices data"""
    try:
        indices_data = []
        for symbol in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            if symbol in MOCK_MARKET_DATA:
                index_data = add_realistic_variation(MOCK_MARKET_DATA[symbol])
                indices_data.append(index_data)
        
        return {
            "success": True,
            "data": indices_data,
            "message": "Market indices retrieved successfully (fallback data)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market indices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market indices: {str(e)}")

@router.get("/market-status")
async def get_market_status():
    """Get current market status"""
    try:
        current_time = datetime.now()
        
        # Update market status based on time
        if 9 <= current_time.hour < 15 or (current_time.hour == 15 and current_time.minute <= 30):
            MARKET_STATUS["is_open"] = True
            MARKET_STATUS["session"] = "REGULAR"
        else:
            MARKET_STATUS["is_open"] = False
            MARKET_STATUS["session"] = "CLOSED"
        
        MARKET_STATUS["last_updated"] = current_time.isoformat()
        
        return {
            "success": True,
            "data": MARKET_STATUS,
            "message": "Market status retrieved successfully",
            "timestamp": current_time.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market status: {str(e)}")

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a symbol"""
    try:
        symbol = symbol.upper()
        
        if symbol in MOCK_MARKET_DATA:
            quote_data = add_realistic_variation(MOCK_MARKET_DATA[symbol])
        else:
            # Generate mock data for unknown symbols
            quote_data = {
                "symbol": symbol,
                "ltp": round(random.uniform(100, 5000), 2),
                "change": round(random.uniform(-50, 50), 2),
                "change_percent": round(random.uniform(-2, 2), 2),
                "volume": random.randint(10000, 1000000),
                "timestamp": datetime.now().isoformat(),
                "data_source": "fallback_generated"
            }
        
        return {
            "success": True,
            "data": quote_data,
            "message": f"Quote for {symbol} retrieved successfully (fallback data)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")

@router.get("/top-gainers")
async def get_top_gainers():
    """Get top gaining stocks"""
    try:
        gainers = []
        for symbol, data in MOCK_MARKET_DATA.items():
            if data["change_percent"] > 0:
                gainer_data = add_realistic_variation(data)
                gainers.append(gainer_data)
        
        # Sort by change_percent descending
        gainers.sort(key=lambda x: x["change_percent"], reverse=True)
        
        return {
            "success": True,
            "data": gainers[:10],
            "message": "Top gainers retrieved successfully (fallback data)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting top gainers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get top gainers: {str(e)}")

@router.get("/top-losers")
async def get_top_losers():
    """Get top losing stocks"""
    try:
        losers = []
        for symbol, data in MOCK_MARKET_DATA.items():
            if data["change_percent"] < 0:
                loser_data = add_realistic_variation(data)
                losers.append(loser_data)
        
        # Sort by change_percent ascending (most negative first)
        losers.sort(key=lambda x: x["change_percent"])
        
        return {
            "success": True,
            "data": losers[:10],
            "message": "Top losers retrieved successfully (fallback data)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting top losers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get top losers: {str(e)}")

@router.post("/subscribe")
async def subscribe_to_symbols(symbols: List[str]):
    """Subscribe to real-time updates for symbols"""
    try:
        # For fallback, just acknowledge subscription
        logger.info(f"Fallback subscription request for symbols: {symbols}")
        
        return {
            "success": True,
            "data": {
                "subscribed_symbols": symbols,
                "subscription_id": f"fallback_{datetime.now().timestamp()}"
            },
            "message": f"Subscribed to {len(symbols)} symbols (fallback mode)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")

@router.get("/connection-status")
async def get_connection_status():
    """Get market data connection status"""
    try:
        return {
            "success": True,
            "data": {
                "sharekhan_status": "fallback_mode",
                "sharekhan_status": "fallback_mode",
                "primary_feed": "mock_data",
                "fallback_active": True,
                "last_updated": datetime.now().isoformat()
            },
            "message": "Market data running in fallback mode",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

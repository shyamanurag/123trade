"""
Market Indices API endpoints
Shows live market data for major indices
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from datetime import datetime
import os
import logging
import pytz

logger = logging.getLogger(__name__)
router = APIRouter()

# Global variable to store market data
market_data_cache = {}

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

@router.get("/indices")
async def get_market_indices():
    """Get live market indices data"""
    try:
        # Use IST timezone for accurate market status
        now_ist = datetime.now(IST)
        
        # Check if TrueData is configured
        truedata_configured = bool(os.getenv('TRUEDATA_USERNAME'))
        
        # Return empty data if not configured or no real data available
        indices_data = {
            "success": True,
            "timestamp": now_ist.isoformat(),
            "market_status": "OPEN" if 9 <= now_ist.hour < 15 or (now_ist.hour == 15 and now_ist.minute < 30) else "CLOSED",
            "indices": [],  # Real market index data required
            "message": "Waiting for live market data..." if truedata_configured else "TrueData not configured"
        }
        
        # TODO: When TrueData is connected, fetch real data here
        # if truedata_provider and truedata_provider.is_connected():
        #     indices_data["indices"] = await truedata_provider.get_indices_data()
        
        return indices_data
        
    except Exception as e:
        logger.error(f"Error fetching market indices: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch market indices")

@router.get("/indices/{symbol}")
async def get_index_details(symbol: str):
    """Get detailed data for a specific index"""
    try:
        symbol = symbol.upper()
        now_ist = datetime.now(IST)
        
        # Real market data required
        index_details = {
            "success": True,
            "symbol": symbol,
            "timestamp": now_ist.isoformat(),
            "data": None,  # Real data required
            "constituents": {
                "top_gainers": [],
                "top_losers": []
            },
            "message": "Waiting for live market data..."
        }
        
        # TODO: Fetch real data when available
        # if truedata_provider and truedata_provider.is_connected():
        #     index_details["data"] = await truedata_provider.get_index_details(symbol)
        
        return index_details
        
    except Exception as e:
        logger.error(f"Error fetching index details for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unable to fetch details for {symbol}")

@router.get("/market-status")
async def get_market_status():
    """Get current market status and timings"""
    try:
        # Use IST timezone for accurate market timing
        now_ist = datetime.now(IST)
        current_time = now_ist.time()
        
        # Market timings (IST)
        pre_open_start = datetime.strptime("09:00", "%H:%M").time()
        pre_open_end = datetime.strptime("09:15", "%H:%M").time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        post_close_end = datetime.strptime("16:00", "%H:%M").time()
        
        # Determine market phase
        if current_time < pre_open_start:
            phase = "PRE_MARKET"
            status = "CLOSED"
        elif pre_open_start <= current_time < pre_open_end:
            phase = "PRE_OPEN"
            status = "PRE_OPEN"
        elif market_open <= current_time < market_close:
            phase = "NORMAL"
            status = "OPEN"
        elif market_close <= current_time < post_close_end:
            phase = "POST_CLOSE"
            status = "POST_CLOSE"
        else:
            phase = "CLOSED"
            status = "CLOSED"
        
        # Check if it's a weekend
        if now_ist.weekday() in [5, 6]:  # Saturday or Sunday
            phase = "WEEKEND"
            status = "CLOSED"
        
        market_status = {
            "success": True,
            "timestamp": now_ist.isoformat(),
            "market_status": status,
            "market_phase": phase,
            "current_time": current_time.strftime("%H:%M:%S"),
            "ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "timings": {
                "pre_open": "09:00 - 09:15",
                "normal": "09:15 - 15:30",
                "post_close": "15:30 - 16:00",
                "closed": "16:00 - 09:00"
            },
            "is_trading_day": now_ist.weekday() not in [5, 6],
            "next_trading_day": "Monday" if now_ist.weekday() >= 4 else "Tomorrow",
            "data_provider": {
                "name": "TrueData",
                "status": "CONNECTED" if os.getenv('TRUEDATA_USERNAME') else "NOT_CONFIGURED",
                "user": os.getenv('TRUEDATA_USERNAME', 'Not configured')
            }
        }
        
        return market_status
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch market status") 
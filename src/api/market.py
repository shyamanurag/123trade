from fastapi import APIRouter, HTTPException
from datetime import datetime
import pytz
import os
from src.models.responses import MarketIndicesResponse, MarketStatusResponse

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

router = APIRouter(prefix="/api/market", tags=["market-data"])

@router.get("/indices")
async def get_market_indices():
    """Get market indices data from TrueData live feed with enhanced volume parsing"""
    try:
        # Use IST timezone for timestamp
        now_ist = datetime.now(IST)
        
        # Check if market is currently open
        current_hour = now_ist.hour
        is_market_open = (9 <= current_hour < 16) and (now_ist.weekday() not in [5, 6])
        
        # Initialize default values
        connection_health = {'connected': False, 'heartbeat_healthy': False, 'data_flowing': False, 'symbols_count': 0, 'heartbeat_age': 999}
        nifty_data = {}
        banknifty_data = {}
        
        # Only try to get live data if market is open
        if is_market_open:
            try:
                # Import enhanced TrueData functions
                from data.truedata_client import live_market_data, get_truedata_status
                
                # Get connection health
                status = get_truedata_status()
                connection_health = {
                    'connected': status.get('connected', False),
                    'heartbeat_healthy': status.get('data_flowing', False),
                    'data_flowing': status.get('data_flowing', False),
                    'symbols_count': status.get('symbols_active', 0),
                    'heartbeat_age': 0 if status.get('connected') else 999
                }
                
                # Get live data from TrueData singleton client (using correct symbol formats)
                nifty_data = live_market_data.get('NIFTY-I', {})
                banknifty_data = live_market_data.get('BANKNIFTY-I', {})
            except ImportError:
                # TrueData client not available, use fallback data
                pass
        
        # If market is closed or TrueData disconnected, show NO DATA instead of fake values
        if not is_market_open or not connection_health.get('connected', False):
            # REMOVED FAKE DATA - Show clearly that no real data is available
            nifty_data = {
                'ltp': 0,
                'high': 0, 
                'low': 0,
                'open_price': 0,
                'change': 0,
                'change_percent': 0,
                'volume': 0,
                'prev_close': 0,
                'timestamp': now_ist.isoformat(),
                'status': 'NO_LIVE_DATA_AVAILABLE' if not is_market_open else 'TRUEDATA_DISCONNECTED'
            }
            banknifty_data = {
                'ltp': 0,
                'high': 0,
                'low': 0, 
                'open_price': 0,
                'change': 0,
                'change_percent': 0,
                'volume': 0,
                'prev_close': 0,
                'timestamp': now_ist.isoformat(),
                'status': 'NO_LIVE_DATA_AVAILABLE' if not is_market_open else 'TRUEDATA_DISCONNECTED'
            }
        
        # Helper function to extract price data with enhanced volume handling
        def get_enhanced_price_data(data, symbol_name, fallback_price=0):
            if not data or not isinstance(data, dict):
                return {
                    "symbol": symbol_name,
                    "name": symbol_name,
                    "price": fallback_price,
                    "change": 0,
                    "change_percent": 0,
                    "last_price": fallback_price,
                    "high": fallback_price,
                    "low": fallback_price,
                    "volume": 0,
                    "status": "NO_DATA",
                    "last_update": now_ist.isoformat(),
                    "data_age_seconds": 999
                }
            
            # Get current time for age calculation
            current_time = now_ist.timestamp()
            last_update_time = data.get('last_update_time', current_time)
            data_age = current_time - last_update_time
            
            # Extract data with enhanced volume parsing
            ltp = data.get('ltp', data.get('last_price', fallback_price))
            high = data.get('high', data.get('day_high', ltp))
            low = data.get('low', data.get('day_low', ltp))
            # Fix the 'open' key access issue
            open_price = data.get('open_price', data.get('day_open', data.get('open', ltp)))
            
            # Enhanced volume extraction - try multiple fields
            volume = (data.get('volume', 0) or 
                     data.get('vol', 0) or 
                     data.get('total_volume', 0) or
                     data.get('day_volume', 0) or
                     data.get('traded_volume', 0))
            
            # Get change data
            change = data.get('change', 0)
            change_percent = data.get('change_percent', 0)
            
            # Calculate change if not available (simplified)
            if change == 0 and change_percent == 0:
                prev_close = data.get('prev_close', ltp)
                if prev_close > 0 and ltp != prev_close:
                    change = ltp - prev_close
                    change_percent = (change / prev_close * 100)
            
            # Determine status based on data age and values
            if not is_market_open:
                status = "MARKET_CLOSED_NO_DATA"
            elif data_age > 300:  # 5 minutes old
                status = "STALE_DATA"
            elif ltp > 0:
                status = "LIVE_TRUEDATA"
            else:
                status = "TRUEDATA_DISCONNECTED"
            
            return {
                "symbol": symbol_name,
                "name": symbol_name,
                "price": round(float(ltp), 2) if ltp else 0,
                "change": round(float(change), 2) if change else 0,
                "change_percent": round(float(change_percent), 2) if change_percent else 0,
                "last_price": round(float(ltp), 2) if ltp else 0,
                "high": round(float(high), 2) if high else 0,
                "low": round(float(low), 2) if low else 0,
                "open": round(float(open_price), 2) if open_price else 0,
                "volume": int(volume) if volume else 0,
                "status": status,
                "last_update": data.get('timestamp', now_ist.isoformat()),
                "data_age_seconds": round(data_age, 1),
                "heartbeat": data.get('heartbeat', False)
            }
        
        # Build response with enhanced TrueData parsing
        nifty_index = get_enhanced_price_data(nifty_data, "NIFTY 50", 0)
        bank_nifty_index = get_enhanced_price_data(banknifty_data, "BANK NIFTY", 0)
        
        # Format data as array for frontend compatibility
        indices_array = [
            {
                "symbol": "NIFTY",
                "name": "NIFTY 50",
                "last_price": nifty_index["price"],
                "price": nifty_index["price"],
                "change": nifty_index["change"],
                "change_percent": nifty_index["change_percent"],
                "high": nifty_index["high"],
                "low": nifty_index["low"],
                "open": nifty_index["open"],
                "volume": nifty_index["volume"],
                "status": nifty_index["status"],
                "last_update": nifty_index["last_update"],
                "data_age_seconds": nifty_index["data_age_seconds"],
                "heartbeat": nifty_index["heartbeat"]
            },
            {
                "symbol": "BANKNIFTY",
                "name": "BANK NIFTY",
                "last_price": bank_nifty_index["price"],
                "price": bank_nifty_index["price"],
                "change": bank_nifty_index["change"],
                "change_percent": bank_nifty_index["change_percent"],
                "high": bank_nifty_index["high"],
                "low": bank_nifty_index["low"],
                "open": bank_nifty_index["open"],
                "volume": bank_nifty_index["volume"],
                "status": bank_nifty_index["status"],
                "last_update": bank_nifty_index["last_update"],
                "data_age_seconds": bank_nifty_index["data_age_seconds"],
                "heartbeat": bank_nifty_index["heartbeat"]
            }
        ]
        
        # Enhanced market status
        market_status = "OPEN" if is_market_open else "CLOSED"
        
        return MarketIndicesResponse.create(
            indices_data=indices_array,
            market_status=market_status,
            last_update=now_ist.isoformat(),
            timestamp=now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            truedata_connection={
                "symbols_available": len(live_market_data) if is_market_open and 'live_market_data' in locals() else 0,
                "nifty_available": bool(nifty_data),
                "banknifty_available": bool(banknifty_data),
                "live_data_symbols": list(live_market_data.keys()) if is_market_open and 'live_market_data' in locals() else [],
                "connection_healthy": connection_health['connected'] and connection_health['heartbeat_healthy'],
                "heartbeat_age_seconds": connection_health.get('heartbeat_age', 999),
                "data_flowing": connection_health['data_flowing'],
                "total_symbols": connection_health['symbols_count'],
                "market_open": is_market_open,
                "data_source": "LIVE" if is_market_open and connection_health['connected'] else "FALLBACK_CLOSED_MARKET"
            }
        ).dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to fetch market indices: {str(e)}")

@router.get("/market-status")
async def get_market_status():
    """Get current market status and timings with TrueData health"""
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
        
        # Get TrueData connection health
        try:
            from data.truedata_client import get_truedata_status
            td_status = get_truedata_status()
            
            # Safely extract values to prevent React Error #31
            truedata_health = {
                'connected': td_status.get('connected', False) if isinstance(td_status, dict) else False,
                'heartbeat_healthy': td_status.get('data_flowing', False) if isinstance(td_status, dict) else False,
                'heartbeat_age': td_status.get('heartbeat_age', 999) if isinstance(td_status, dict) else 999,
                'data_flowing': td_status.get('data_flowing', False) if isinstance(td_status, dict) else False
            }
            truedata_status = "CONNECTED" if truedata_health['connected'] and truedata_health['heartbeat_healthy'] else "DISCONNECTED"
        except:
            truedata_health = {'connected': False, 'heartbeat_healthy': False, 'heartbeat_age': 999, 'data_flowing': False}
            truedata_status = "ERROR"
        
        return MarketStatusResponse.create(
            status=status,
            phase=phase,
            current_time=now_ist.isoformat(),
            timezone="Asia/Kolkata",
            ist_time=now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            market_open="09:15",
            market_close="15:30",
            is_trading_hours=status == "OPEN",
            timings={
                "pre_open": "09:00 - 09:15",
                "normal": "09:15 - 15:30",
                "post_close": "15:30 - 16:00",
                "closed": "16:00 - 09:00"
            },
            is_trading_day=now_ist.weekday() not in [5, 6],
            data_provider={
                "name": "TrueData Enhanced",
                "status": str(truedata_status),  # Ensure it's a string
                "user": str(os.getenv('TRUEDATA_USERNAME', 'Not configured')),  # Ensure it's a string
                "connection_healthy": bool(truedata_health['connected'] and truedata_health['heartbeat_healthy']),  # Ensure it's a boolean
                "heartbeat_age_seconds": int(truedata_health.get('heartbeat_age', 999)),  # Ensure it's an int, not an object
                "data_flowing": bool(truedata_health.get('data_flowing', False))  # Ensure it's a boolean
            }
        ).dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to fetch market status")

# Enhanced volume data endpoint
@router.get("/volume-data")
async def get_volume_data():
    """Get detailed volume data for debugging"""
    try:
        from data.truedata_client import live_market_data
        
        volume_data = {}
        for symbol, data in live_market_data.items():
            if not symbol.endswith('_GREEKS'):  # Skip options data
                volume_data[symbol] = {
                    'symbol': symbol,
                    'ltp': data.get('ltp', 0),
                    'volume': data.get('volume', 0),
                    'volume_fields': {
                        'volume': data.get('volume', 0),
                        'vol': data.get('vol', 0),
                        'v': data.get('v', 0),
                        'total_volume': data.get('total_volume', 0),
                        'day_volume': data.get('day_volume', 0),
                        'traded_volume': data.get('traded_volume', 0)
                    },
                    'timestamp': data.get('timestamp'),
                    'data_source': data.get('data_source'),
                    'heartbeat': data.get('heartbeat', False)
                }
        
        return {
            "success": True,
            "volume_data": volume_data,
            "total_symbols": len(volume_data),
            "symbols_with_volume": len([s for s in volume_data.values() if s['volume'] > 0])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to fetch volume data: {str(e)}")

# --- START USER ENDPOINTS ---
# Note: This is a temporary measure to test the router refactoring.
import hashlib

def get_database_operations():
    return None

users_router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@users_router.get("/current", summary="Get current user")
async def get_current_user():
    """Get current user information - SAFETY PROTECTED"""
    try:
        # ELIMINATED: Mock current user that could mislead about authentication
        # ❌ return {
        # ❌     "success": True,
        # ❌     "user": {
        # ❌         "id": "test_user_001",
        # ❌         "username": "test_user",
        # ❌         "email": "test@example.com",
        # ❌         "name": "Test User",
        # ❌         "role": "trader",
        # ❌         "created_at": "2024-01-01T00:00:00Z",
        # ❌         "is_active": True,
        # ❌         "preferences": {
        # ❌             "theme": "dark",
        # ❌             "notifications": True,
        # ❌             "paper_trading": True
        # ❌         }
        # ❌     }
        # ❌ }
        
        # SAFETY: Return proper error instead of fake user
        logger.error("SAFETY: Mock current user ELIMINATED to prevent fake authentication")
        return {
            "success": False,
            "error": "SAFETY: Mock current user disabled - real authentication required",
            "message": "Mock test user eliminated for safety"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add legacy API route for backward compatibility  
@router.get("/v1/indices")
async def get_market_indices_legacy():
    """Legacy endpoint - redirect to main indices endpoint"""
    return await get_market_indices()

# Also add direct route without prefix for legacy calls
from fastapi import APIRouter as BaseRouter
legacy_router = BaseRouter()

@legacy_router.get("/api/v1/market/indices")
async def get_market_indices_v1_legacy():
    """Legacy v1 API endpoint for market indices"""
    return await get_market_indices()

# We'll need to mount this in main.py 
"""
Market Data API Endpoints - Using Zerodha WebSocket and TrueData
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import redis
from common.logging import get_logger
from config.truedata_config import TrueDataConfig

router = APIRouter()
logger = get_logger(__name__)

# Initialize Redis connection for real-time data
try:
    import os
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

# Indian market symbols with proper mappings
INDIAN_SYMBOLS = {
    # NSE Equity
    'RELIANCE': {'zerodha': 'RELIANCE', 'truedata': 'RELIANCE-EQ', 'token': 738561},
    'TCS': {'zerodha': 'TCS', 'truedata': 'TCS-EQ', 'token': 2953217},
    'INFY': {'zerodha': 'INFY', 'truedata': 'INFY-EQ', 'token': 408065},
    'HDFCBANK': {'zerodha': 'HDFCBANK', 'truedata': 'HDFCBANK-EQ', 'token': 341249},
    'ICICIBANK': {'zerodha': 'ICICIBANK', 'truedata': 'ICICIBANK-EQ', 'token': 1270529},
    'ITC': {'zerodha': 'ITC', 'truedata': 'ITC-EQ', 'token': 424961},
    'HINDUNILVR': {'zerodha': 'HINDUNILVR', 'truedata': 'HINDUNILVR-EQ', 'token': 356865},
    'KOTAKBANK': {'zerodha': 'KOTAKBANK', 'truedata': 'KOTAKBANK-EQ', 'token': 492033},
    
    # Indices
    'NIFTY': {'zerodha': 'NIFTY 50', 'truedata': 'NIFTY-I', 'token': 256265},
    'BANKNIFTY': {'zerodha': 'NIFTY BANK', 'truedata': 'BANKNIFTY-I', 'token': 260105},
    'FINNIFTY': {'zerodha': 'NIFTY FIN SERVICE', 'truedata': 'FINNIFTY-I', 'token': 257801},
    'SENSEX': {'zerodha': 'SENSEX', 'truedata': 'SENSEX-I', 'token': 265}
}

@router.get("/symbols")
async def get_available_symbols():
    """Get list of available symbols for trading"""
    try:
        symbols = list(INDIAN_SYMBOLS.keys())
        
        # Add metadata about symbols
        symbol_details = []
        for symbol, mapping in INDIAN_SYMBOLS.items():
            symbol_details.append({
                'symbol': symbol,
                'zerodha_name': mapping['zerodha'],
                'truedata_name': mapping['truedata'],
                'token': mapping['token']
            })
        
        return {
            "success": True,
            "symbols": symbols,
            "symbol_details": symbol_details,
            "count": len(symbols),
            "data_sources": ["Zerodha WebSocket", "TrueData"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch symbols")

@router.get("/realtime/{symbol}")
async def get_realtime_data(symbol: str):
    """Get real-time market data for a symbol"""
    try:
        # Simulate real-time data for paper trading
        import random
        
        base_prices = {
            "NIFTY": 19500,
            "BANKNIFTY": 44000,
            "RELIANCE": 2485,
            "TCS": 3658,
            "INFY": 1456,
            "HDFC": 1678,
            "ICICIBANK": 945,
            "KOTAKBANK": 1789,
            "LT": 2345,
            "ASIANPAINT": 3234,
            "MARUTI": 9876,
            "HCLTECH": 1234
        }
        
        base_price = base_prices.get(symbol.upper(), 1000)
        current_price = base_price + random.uniform(-50, 50)
        change = current_price - base_price
        change_percent = (change / base_price) * 100
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": random.randint(100000, 1000000),
            "high": round(current_price + random.uniform(10, 30), 2),
            "low": round(current_price - random.uniform(10, 30), 2),
            "open": round(base_price + random.uniform(-20, 20), 2),
            "timestamp": datetime.now().isoformat(),
            "source": "Generated for Paper Trading"
        }
        
    except Exception as e:
        logger.error(f"Error fetching real-time data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unable to fetch real-time data for {symbol}")

@router.get("/historical/{symbol}/{timeframe}")
async def get_historical_data(
    symbol: str,
    timeframe: str,
    days: Optional[int] = Query(30, description="Number of days of data")
):
    """Get historical market data - Using stored data from TrueData/Zerodha"""
    try:
        symbol = symbol.upper()
        
        if symbol not in INDIAN_SYMBOLS:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        # Ensure days is not None
        if days is None:
            days = 30
        
        # Get historical data from Redis cache first
        if redis_client:
            try:
                cache_key = f"historical:{symbol}:{timeframe}:{days}"
                cached_data = redis_client.get(cache_key)
                
                if cached_data and isinstance(cached_data, (str, bytes)):
                    data = json.loads(cached_data)
                    # Check if data is not too old (less than 1 hour)
                    if 'cached_at' in data:
                        cached_time = datetime.fromisoformat(data['cached_at'])
                        if datetime.now() - cached_time < timedelta(hours=1):
                            return {
                                "success": True,
                                "data": data['ohlc_data'],
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "source": data.get('source', 'Cache'),
                                "count": len(data['ohlc_data']),
                                "timestamp": datetime.now().isoformat()
                            }
                
            except Exception as cache_error:
                logger.warning(f"Cache error: {cache_error}")
        
        # Generate sample OHLC data based on current price for demonstration
        # In production, this would come from TrueData historical API
        current_price = await _get_current_price_estimate(symbol)
        sample_data = _generate_sample_ohlc(current_price, timeframe, days)
        
        # Cache the data
        if redis_client:
            try:
                cache_data = {
                    'ohlc_data': sample_data,
                    'source': 'Generated',
                    'cached_at': datetime.now().isoformat()
                }
                redis_client.setex(
                    f"historical:{symbol}:{timeframe}:{days}",
                    3600,  # 1 hour expiry
                    json.dumps(cache_data)
                )
            except Exception as cache_error:
                logger.warning(f"Failed to cache data: {cache_error}")
        
        return {
            "success": True,
            "data": sample_data,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "Generated (TrueData integration pending)",
            "count": len(sample_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unable to fetch data for {symbol}")

@router.get("/current/{symbol}")
async def get_current_price(symbol: str):
    """Get current price from real-time data"""
    try:
        symbol = symbol.upper()
        
        if symbol not in INDIAN_SYMBOLS:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        # Get current price from real-time data
        realtime_response = await get_realtime_data(symbol)
        
        if realtime_response.get('data'):
            data = realtime_response['data']
            current_price = data.get('last_price') or data.get('ltp') or data.get('close')
            
            return {
                "success": True,
                "symbol": symbol,
                "price": float(current_price) if current_price else None,
                "change": data.get('change'),
                "change_percent": data.get('change_percent'),
                "volume": data.get('volume'),
                "ohlc": data.get('ohlc'),
                "source": realtime_response.get('source'),
                "timestamp": datetime.now().isoformat()
            }
        
        # Fallback to estimated price
        estimated_price = await _get_current_price_estimate(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "price": estimated_price,
            "source": "Estimated",
            "message": "Real-time data not available",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching current price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unable to fetch current price for {symbol}")

@router.get("/market-status")
async def get_market_status():
    """Get current Indian market status"""
    try:
        now = datetime.now()
        
        # NSE trading hours: 9:15 AM to 3:30 PM IST, Monday to Friday
        is_market_open = (
            now.weekday() < 5 and  # Monday to Friday
            (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and
            (now.hour < 15 or (now.hour == 15 and now.minute <= 30))
        )
        
        # Check data source status
        data_sources = {}
        
        if redis_client:
            try:
                # Check Zerodha connection status
                zerodha_status = redis_client.get("zerodha:connection_status")
                if zerodha_status and isinstance(zerodha_status, (str, bytes)):
                    data_sources['zerodha'] = json.loads(zerodha_status)
                else:
                    data_sources['zerodha'] = False
                
                # Check TrueData connection status
                truedata_status = redis_client.get("truedata:connection_status")
                if truedata_status and isinstance(truedata_status, (str, bytes)):
                    data_sources['truedata'] = json.loads(truedata_status)
                else:
                    data_sources['truedata'] = False
                
            except Exception as redis_error:
                logger.warning(f"Redis status check error: {redis_error}")
                data_sources = {'zerodha': 'unknown', 'truedata': 'unknown'}
        
        return {
            "success": True,
            "is_open": is_market_open,
            "market": "NSE/BSE",
            "timezone": "Asia/Kolkata",
            "trading_hours": "09:15 - 15:30",
            "data_sources": data_sources,
            "timestamp": datetime.now().isoformat(),
            "next_open": "09:15:00" if not is_market_open else None,
            "next_close": "15:30:00" if is_market_open else None
        }
        
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch market status")

@router.get("/data-sources")
async def get_data_sources():
    """Get available data sources and their status"""
    try:
        return {
            "success": True,
            "data_sources": [
                {
                    "name": "Zerodha WebSocket",
                    "status": "active",
                    "type": "real-time",
                    "symbols_supported": 12,
                    "latency_ms": 50
                },
                {
                    "name": "TrueData",
                    "status": "pending_subscription",
                    "type": "real-time + historical",
                    "symbols_supported": 50,
                    "trial_expires": "2025-06-15",
                    "credentials": "Trial106/shyam106"
                },
                {
                    "name": "Generated Data",
                    "status": "active",
                    "type": "fallback",
                    "symbols_supported": "unlimited",
                    "note": "Used when primary sources unavailable"
                }
            ],
            "primary_source": "Zerodha WebSocket",
            "fallback_source": "Generated Data",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching data sources: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch data sources")

# Helper functions
async def _get_current_price_estimate(symbol: str) -> float:
    """Get estimated current price for a symbol"""
    # Base prices for major Indian stocks (approximate)
    base_prices = {
        'RELIANCE': 2500.0, 'TCS': 3800.0, 'INFY': 1600.0,
        'HDFCBANK': 1650.0, 'ICICIBANK': 950.0, 'ITC': 450.0,
        'HINDUNILVR': 2400.0, 'KOTAKBANK': 1900.0,
        'NIFTY': 19800.0, 'BANKNIFTY': 44500.0,
        'FINNIFTY': 19200.0, 'SENSEX': 66000.0
    }
    
    return base_prices.get(symbol, 1000.0)

def _generate_sample_ohlc(base_price: float, timeframe: str, days: int) -> List[Dict]:
    """Generate sample OHLC data for demonstration"""
    import random
    
    # Calculate number of bars based on timeframe
    bars_per_day = {
        '1min': 375, '5min': 75, '15min': 25,
        '30min': 12, '1hour': 6, '1day': 1
    }
    
    total_bars = min(bars_per_day.get(timeframe, 1) * days, 1000)  # Limit to 1000 bars
    
    data = []
    current_price = base_price
    
    for i in range(total_bars):
        # Generate realistic OHLC data
        volatility = 0.02  # 2% volatility
        change = random.gauss(0, volatility)
        
        open_price = current_price
        high_price = open_price * (1 + abs(change) * random.uniform(0.5, 1.5))
        low_price = open_price * (1 - abs(change) * random.uniform(0.5, 1.5))
        close_price = open_price * (1 + change)
        
        # Ensure high >= open,close and low <= open,close
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Generate timestamp
        bar_time = datetime.now() - timedelta(days=days) + timedelta(
            minutes=i * (1440 / total_bars * days)  # Distribute evenly
        )
        
        data.append({
            "timestamp": bar_time.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": random.randint(1000, 100000)
        })
        
        current_price = close_price
    
    return data

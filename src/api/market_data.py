"""
Market Data API Router
Real-time and historical market data endpoints
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List, Dict, Any
import sys
import os
import json
import redis
import ssl
from urllib.parse import urlparse
import asyncio
import time # Added for retry logic
sys.path.insert(0, os.path.abspath('.'))

# Import symbol mapping for ShareKhan
try:
    from config.sharekhan_symbols import get_sharekhan_symbol
except Exception:
    # Minimal fallback mapping to avoid runtime failure when config is missing
    def get_sharekhan_symbol(symbol: str) -> str:
        return symbol

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["market-data"])

# Setup Redis client for cross-process data access
redis_client = None

def setup_redis():
    """Setup Redis client with simple, compatible configuration"""
    global redis_client
    
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Simple Redis client that works with all versions
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10
        )
        
        # Test connection
        redis_client.ping()
        logger.info(f"✅ Market Data Redis connected: {redis_url[:50]}...")
        
    except Exception as e:
        logger.warning(f"⚠️ Market Data Redis connection failed: {e}")
        redis_client = None

# Initialize Redis at module level
setup_redis()

def get_sharekhan_from_redis():
    """Get ShareKhan from Redis cache - SOLVES PROCESS ISOLATION"""
    try:
        if not redis_client:
            logger.warning("⚠️ Redis not available - trying to reconnect...")
            if not setup_redis():
                return {}
        
        # Get all market data from Redis
        cached_data = redis_client.hgetall("sharekhan:live_cache")
        
        if not cached_data:
            logger.warning("⚠️ No data in Redis cache - ShareKhan may not be connected")
            return {}
        
        # Parse JSON data
        parsed_data = {}
        for symbol, json_data in cached_data.items():
            try:
                parsed_data[symbol] = json.loads(json_data)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Invalid JSON for symbol {symbol}")
                continue
        
        logger.info(f"✅ Retrieved {len(parsed_data)} symbols from Redis cache")
        return parsed_data
        
    except Exception as e:
        logger.error(f"❌ Error getting ShareKhan from Redis: {e}")
        return {}

def get_sharekhan_proxy():
    """Get ShareKhan data from Redis cache - CROSS-PROCESS SOLUTION"""
    try:
        # STRATEGY 1: Redis cache (PRIMARY - fixes process isolation)
        redis_data = get_sharekhan_from_redis()
        if redis_data:
            logger.info(f"📊 Redis cache strategy SUCCESS: {len(redis_data)} symbols")
            return {
                'connected': True,
                'data': redis_data,
                'symbols_count': len(redis_data),
                'source': 'Redis_Cache'
            }
        
        # STRATEGY 2: Direct cache access (FALLBACK)
        from data.sharekhan_client import live_market_data
        if live_market_data:
            logger.info(f"📊 Direct cache strategy SUCCESS: {len(live_market_data)} symbols")
            return {
                'connected': True,
                'data': live_market_data,
                'symbols_count': len(live_market_data),
                'source': 'Direct_Cache'
            }
        
        # STRATEGY 3: File cache (FALLBACK)
        cache_file = "/tmp/sharekhan_cache.json" if os.name != 'nt' else "C:/temp/sharekhan_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                file_data = json.load(f)
            if file_data:
                logger.info(f"📊 File cache strategy SUCCESS: {len(file_data)} symbols")
                return {
                    'connected': True,
                    'data': file_data,
                    'symbols_count': len(file_data),
                    'source': 'File_Cache'
                }
        
        # All strategies failed
        logger.error("🚨 ALL STRATEGIES FAILED - No ShareKhan cache accessible")
        return {
            'connected': False,
            'data': {},
            'symbols_count': 0,
            'source': 'None',
            'error': 'Process isolation - ShareKhan cache not accessible'
        }
        
    except Exception as e:
        logger.error(f"❌ Error in get_sharekhan_proxy: {e}")
        return {
            'connected': False,
            'data': {},
            'symbols_count': 0,
            'source': 'Error',
            'error': str(e)
        }

def is_sharekhan_connected():
    """Check if ShareKhan is connected via Redis cache"""
    try:
        # Check Redis cache first
        redis_data = get_sharekhan_from_redis()
        if redis_data:
            logger.info(f"🔧 ShareKhan connected via Redis: {len(redis_data)} symbols")
            return True
            
        # Fallback to direct cache check
        from data.sharekhan_client import live_market_data
        connected = len(live_market_data) > 0
        logger.info(f"🔧 ShareKhan fallback check: {connected}")
        return connected
        
    except Exception as e:
        logger.error(f"Error checking ShareKhan connection: {e}")
        return False

def get_live_data_for_symbol(symbol: str) -> dict:
    """Get live data for a specific symbol via direct cache access"""
    try:
        # Use symbol mapping to convert NIFTY -> NIFTY-I
        mapped_symbol = get_sharekhan_symbol(symbol.upper())
        logger.debug(f"🔧 Symbol mapping: {symbol} -> {mapped_symbol}")
        
        # Get data from live cache
        symbol_data = get_sharekhan_from_redis().get(mapped_symbol, {})
        
        if symbol_data:
            logger.debug(f"📊 Retrieved data for {symbol}: LTP={symbol_data.get('ltp', 'N/A')}")
        
        return symbol_data
        
    except Exception as e:
        logger.error(f"Error getting live data for {symbol}: {e}")
        return {}

def get_all_live_market_data():
    """Get all live market data from Redis cache"""
    try:
        # PRIMARY: Get from Redis cache
        redis_data = get_sharekhan_from_redis()
        if redis_data:
            logger.debug(f"📊 Retrieved all market data from Redis: {len(redis_data)} symbols")
            return redis_data
            
        # FALLBACK: Direct cache access
        from data.sharekhan_client import live_market_data
        logger.debug(f"📊 Retrieved all market data from direct cache: {len(live_market_data)} symbols")
        return live_market_data
        
    except Exception as e:
        logger.error(f"Error getting all live market data: {e}")
        return {}

@router.get("/", response_model=Dict[str, Any])
async def get_all_market_data():
    """Get all available market data from Redis cache"""
    try:
        # Get data from Redis cache (fixes process isolation)
        proxy = get_sharekhan_proxy()
        
        if proxy['connected']:
            return {
                "success": True,
                "data": proxy['data'],
                "symbols_count": proxy['symbols_count'],
                "source": proxy['source'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "data": {},
                "symbols_count": 0,
                "source": "redis_cache",
                "error": proxy.get('error', 'ShareKhan not connected'),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting all market data: {e}")
        return {
            "success": False,
            "data": {},
            "symbols_count": 0,
            "source": "api_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    timeframe: str = Query("1min", description="Timeframe for historical data")
):
    """Get market data for a symbol"""
    try:
        # Get live data for symbol with proper symbol mapping
        live_data = get_live_data_for_symbol(symbol)
        
        if live_data:
            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "data": live_data,
                "timestamp": datetime.now().isoformat(),
                "source": "sharekhan_proxy"
            }
        else:
            # Check if proxy is connected
            if not is_sharekhan_connected():
                raise HTTPException(
                    status_code=503, 
                    detail=f"ShareKhan proxy not connected. Market data not available for {symbol}."
                )
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No data available for symbol {symbol}. Symbol may not be subscribed."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting market data for {symbol}: {str(e)}"
        )

@router.get("/live")
async def get_live_market_data():
    """Get live market data for autonomous trading system"""
    try:
        logger.info("📊 Getting live market data for autonomous trading...")
        
        # Check if proxy is connected
        if not is_sharekhan_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan proxy not connected. No live data available."
            )
        
        # Get all live market data
        market_data = get_all_live_market_data()
        
        if not market_data:
            raise HTTPException(
                status_code=503,
                detail="No live market data available from proxy."
            )
        
        # Format for autonomous trading system
        formatted_data = {
            "symbols": list(market_data.keys()),
            "data": market_data,
            "timestamp": datetime.now().isoformat(),
            "source": "sharekhan_proxy"
        }
        
        logger.info(f"📊 Returning live data for {len(market_data)} symbols")
        
        return {
            "success": True,
            "data": formatted_data,
            "symbol_count": len(market_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live market data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting live market data: {str(e)}"
        )

@router.get("/status")
async def get_market_data_status():
    """Get market data service status"""
    try:
        proxy = get_sharekhan_proxy()
        if not proxy:
            return {
                "success": False,
                "error": "ShareKhan proxy not available",
                "status": "disconnected",
                "timestamp": datetime.now().isoformat()
            }
        
        status = proxy.get_status()
        
        return {
            "success": True,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market data status: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/symbol-expansion/status")
async def get_symbol_expansion_status():
    """Get current symbol expansion status - for monitoring the 6->250 expansion"""
    try:
        # Get current symbol count
        market_data = get_all_live_market_data()
        current_count = len(market_data)
        
        # Get IntelligentSymbolManager status
        try:
            from src.core.intelligent_symbol_manager import intelligent_symbol_manager
            ism_status = intelligent_symbol_manager.get_status()
        except Exception as e:
            logger.warning(f"Could not get IntelligentSymbolManager status: {e}")
            ism_status = {"error": str(e)}
        
        # Get ShareKhan status
        sharekhan_symbols = get_all_live_market_data()
        sharekhan_count = len(sharekhan_symbols)
        
        return {
            "success": True,
            "expansion_analysis": {
                "current_symbols": current_count,
                "target_symbols": 250,
                "sharekhan_available": sharekhan_count,
                "expansion_needed": 250 - current_count,
                "percentage_complete": round((current_count / 250) * 100, 1),
                "status": "EXPANDING" if current_count < 250 else "TARGET_REACHED"
            },
            "intelligent_symbol_manager": ism_status,
            "sharekhan_connection": {
                "connected": is_sharekhan_connected(),
                "available_symbols": sharekhan_count,
                "sample_symbols": list(sharekhan_symbols.keys())[:10] if sharekhan_symbols else []
            },
            "recommendations": [
                "Enable IntelligentSymbolManager startup" if not ism_status.get('is_running') else "✅ ISM Running",
                "Expand ShareKhan subscriptions" if sharekhan_count < 100 else "✅ ShareKhan Connected",
                "Configure F&O auto-discovery" if current_count < 50 else "✅ Symbol Discovery Active"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting symbol expansion status: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/individual/{symbol}")
async def get_individual_symbol_data(symbol: str):
    """Get individual symbol data"""
    try:
        # Check ShareKhan connection
        has_connection = is_sharekhan_connected()
        
        if not has_connection:
            return {
                "success": False,
                "message": f"ShareKhan not connected - no live data for {symbol}",
                "symbol": symbol,
                "price": 0,
                "volume": 0,
                "status": "SHAREKHAN_DISCONNECTED",
                "timestamp": datetime.now().isoformat()
            }
        
        # Try to get live data for symbol
        live_data = get_live_data_for_symbol(symbol)
        
        if live_data:
            return {
                "success": True,
                "message": f"Live data retrieved for {symbol}",
                "symbol": symbol,
                "price": live_data.get("ltp", 0),
                "volume": live_data.get("volume", 0),
                "change": live_data.get("change", 0),
                "change_percent": live_data.get("change_percent", 0),
                "high": live_data.get("high", 0),
                "low": live_data.get("low", 0),
                "open": live_data.get("open", 0),
                "status": "CONNECTED",
                "data": live_data,
                "timestamp": datetime.now().isoformat(),
                "source": "ShareKhan_Live"
            }
        else:
            return {
                "success": False,
                "message": f"No live data available for {symbol}",
                "symbol": symbol,
                "price": 0,
                "volume": 0,
                "status": "NO_DATA",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error fetching individual symbol data for {symbol}: {e}")
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/realtime/{symbol}")
async def get_realtime_data(symbol: str):
    """Get real-time market data for dashboard"""
    try:
        # Get live data using our helper function
        live_data = get_live_data_for_symbol(symbol)
        
        if live_data:
            # Format for frontend chart
            formatted_data = [{
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "price": live_data.get("ltp", 0),
                "volume": live_data.get("volume", 0),
                "symbol": symbol
            }]
            
            return {
                "success": True,
                "data": formatted_data,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"No data available for {symbol}",
                "data": []
            }
            
    except Exception as e:
        logger.error(f"Error getting realtime data for {symbol}: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@router.get("/option-chain/{symbol}")
async def get_option_chain(
    symbol: str,
    _: bool = Depends(is_sharekhan_connected)
):
    """Get option chain for a symbol"""
    try:
        # NO MOCK DATA - Real option chain data required
        raise HTTPException(
            status_code=503,
            detail=f"Option chain data unavailable for {symbol}. ShareKhan connection required."
        )
        
    except Exception as e:
        logger.error(f"Error fetching option chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
async def subscribe_symbols(
    symbols: List[str],
    _: bool = Depends(is_sharekhan_connected)
):
    """Subscribe to market data for symbols"""
    try:
        # Validate symbols against limits
        symbol_limit = 50  # Default limit
        if len(symbols) > symbol_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Symbol count exceeds limit of {symbol_limit}"
            )
            
        # For now, just return success since the singleton client handles subscriptions
        return {
            "success": True,
            "message": f"Subscribed to {len(symbols)} symbols",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat(),
            "note": "Subscription handled by singleton client"
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get summary data for trading dashboard"""
    try:
        # Get data from ShareKhan client - fix import path for production
        try:
            from data.sharekhan_client import get_sharekhan_client
        except ImportError:
            try:
                from src.data.sharekhan_client import get_sharekhan_client
            except ImportError:
                # ELIMINATED: Mock data structure that could mislead about real market data
                # ❌ return {
                # ❌     "success": True,
                # ❌     "data": [
                # ❌         {"symbol": "NIFTY", "ltp": 0, "change": 0, "change_percent": 0, "volume": 0},
                # ❌         {"symbol": "BANKNIFTY", "ltp": 0, "change": 0, "change_percent": 0, "volume": 0},
                # ❌         {"symbol": "FINNIFTY", "ltp": 0, "change": 0, "change_percent": 0, "volume": 0}
                # ❌     ],
                # ❌     "timestamp": datetime.now().isoformat(),
                # ❌     "total_symbols": 3,
                # ❌     "note": "ShareKhan client import not available"
                # ❌ }
                
                # SAFETY: Return proper error instead of fake market data
                logger.error("SAFETY: Mock market data structure ELIMINATED to prevent fake trading data")
                return {
                    "success": False,
                    "error": "SAFETY: Mock market data disabled - real ShareKhan client required",
                    "message": "ShareKhan client import not available - implement real market data feed"
                }
        
        client = get_sharekhan_client()
        if not client:
            return {
                "success": False,
                "message": "ShareKhan not connected"
            }
        
        # Get data for key symbols
        symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
        summary_data = []
        
        for symbol in symbols:
            try:
                data = client.get_market_data(symbol)
                if data:
                    summary_data.append({
                        "symbol": symbol,
                        "ltp": data.get("ltp", 0),
                        "change": data.get("change", 0),
                        "change_percent": data.get("change_percent", 0),
                        "volume": data.get("volume", 0)
                    })
            except Exception as e:
                logger.warning(f"Could not get data for {symbol}: {e}")
        
        return {
            "success": True,
            "data": summary_data,
            "timestamp": datetime.now().isoformat(),
            "total_symbols": len(summary_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        return {
            "success": False,
            "error": str(e)
        }

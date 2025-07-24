# api/crypto_market_data.py
"""
Crypto Market Data API Router
Enhanced for crypto symbol parsing and real-time data
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException, Depends, BackgroundTasks
from typing import Optional, List, Dict, Any
import asyncio
from decimal import Decimal
import os

# Load environment variables from config file
from dotenv import load_dotenv
load_dotenv('local-production.env')  # Load your real API keys

# Import crypto components
from ..core.crypto_cache_manager import get_cache_manager
from ..models.trading_models import CryptoSymbol, CryptoMarketData
from ..data.binance_client import BinanceClient

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/crypto", tags=["crypto-market-data"])

# Initialize Binance client with real configuration from loaded environment
binance_config = {
    'api_key': os.getenv('BINANCE_TESTNET_API_KEY', 'your_binance_testnet_api_key'),
    'api_secret': os.getenv('BINANCE_TESTNET_API_SECRET', 'your_binance_testnet_secret'),
    'testnet': os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
}

# Debug: Show what we loaded
logger.info(f"🔍 Loaded API key: {binance_config['api_key'][:8]}...{binance_config['api_key'][-4:] if len(binance_config['api_key']) > 8 else 'SHORT'}")
logger.info(f"🔍 Loaded secret: {binance_config['api_secret'][:8]}...{binance_config['api_secret'][-4:] if len(binance_config['api_secret']) > 8 else 'SHORT'}")
logger.info(f"🔍 Testnet mode: {binance_config['testnet']}")

# Only initialize if we have real keys
if (binance_config['api_key'] != 'your_binance_testnet_api_key' and 
    binance_config['api_secret'] != 'your_binance_testnet_secret' and
    len(binance_config['api_key']) > 10 and 
    len(binance_config['api_secret']) > 10):
    binance_client = BinanceClient(binance_config)
    logger.info("✅ Binance client initialized with real testnet API keys")
else:
    binance_client = None
    logger.error("❌ Binance client not initialized - real API keys required")
    logger.error(f"   API Key: {binance_config['api_key']}")
    logger.error(f"   Secret: {binance_config['api_secret'][:10]}...")

# =============================================================================
# SYMBOL MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/symbols", response_model=List[Dict])
async def get_crypto_symbols(
    active_only: bool = Query(True, description="Return only active symbols"),
    exchange: str = Query("BINANCE", description="Exchange filter")
):
    """Get cryptocurrency symbols - DYNAMIC REAL DATA ONLY"""
    try:
        cache_manager = await get_cache_manager()
        
        # Get symbols from cache
        symbols = await cache_manager.get_all_symbols()
        
        if symbols:
            # Filter by exchange and active status
            filtered_symbols = []
            for symbol in symbols:
                if exchange and symbol.get('exchange') != exchange:
                    continue
                if active_only and not symbol.get('is_active', True):
                    continue
                filtered_symbols.append(symbol)
            
            if filtered_symbols:
                return filtered_symbols
        
        # CRITICAL: NO HARD-CODED FALLBACK SYMBOLS
        # If no real symbols available, return error instead of hard-coded list
        logger.error("No real symbols available from cache or database")
        raise HTTPException(
            status_code=503,
            detail="Real symbol data not available. No fallback data provided."
        )
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}", response_model=Dict)
async def get_symbol_info(symbol: str):
    """Get detailed information for a specific crypto symbol"""
    try:
        # Parse the symbol
        parsed_symbol = CryptoSymbol.parse_symbol(symbol)
        
        cache_manager = await get_cache_manager()
        
        # Try to get from cache
        cached_info = await cache_manager.get_symbol_info(parsed_symbol.symbol)
        
        if cached_info:
            return {
                "status": "success",
                "data": cached_info,
                "source": "cache"
            }
        
        # Return parsed symbol info
        return {
            "status": "success",
            "data": parsed_symbol.to_dict(),
            "source": "parsed"
        }
        
    except Exception as e:
        logger.error(f"Error getting symbol info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting symbol info: {str(e)}")

@router.post("/symbols/parse")
async def parse_symbol(symbol_input: str):
    """Parse a crypto symbol and return structured data"""
    try:
        parsed = CryptoSymbol.parse_symbol(symbol_input)
        
        return {
            "status": "success",
            "data": {
                "input": symbol_input,
                "parsed": parsed.to_dict(),
                "is_valid": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error parsing symbol {symbol_input}: {e}")
        return {
            "status": "error",
            "data": {
                "input": symbol_input,
                "error": str(e),
                "is_valid": False
            }
        }

# =============================================================================
# MARKET DATA ENDPOINTS
# =============================================================================

@router.get("/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    interval: str = Query("1m", description="Time interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, description="Number of data points"),
    use_cache: bool = Query(True, description="Use cached data if available")
):
    """Get market data for a crypto symbol"""
    try:
        # Parse and validate symbol
        parsed_symbol = CryptoSymbol.parse_symbol(symbol)
        cache_manager = await get_cache_manager()
        
        # Try cache first
        if use_cache:
            cached_data = await cache_manager.get_market_data(parsed_symbol.symbol)
            if cached_data:
                return {
                    "status": "success",
                    "data": cached_data,
                    "symbol": parsed_symbol.symbol,
                    "source": "cache"
                }
        
        # Get live data from Binance
        try:
            if binance_client:
                klines = await binance_client.get_klines(
                    parsed_symbol.symbol, 
                    interval, 
                    limit
                )
                
                if klines:
                    # Convert to our format
                    market_data = []
                    for kline in klines:
                        data_point = {
                            "timestamp": datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                            "open_price": float(kline[1]),
                            "high_price": float(kline[2]),
                            "low_price": float(kline[3]),
                            "close_price": float(kline[4]),
                            "volume": float(kline[5]),
                            "quote_volume": float(kline[7]),
                            "trade_count": int(kline[8]),
                            "taker_buy_volume": float(kline[9]),
                            "taker_buy_quote_volume": float(kline[10])
                        }
                        market_data.append(data_point)
                    
                    # Cache the latest data
                    if market_data:
                        latest = market_data[-1]
                        await cache_manager.cache_market_data(
                            parsed_symbol.symbol,
                            CryptoMarketData(
                                symbol=parsed_symbol.symbol,
                                timestamp=datetime.fromisoformat(latest["timestamp"]),
                                open_price=Decimal(str(latest["open_price"])),
                                high_price=Decimal(str(latest["high_price"])),
                                low_price=Decimal(str(latest["low_price"])),
                                close_price=Decimal(str(latest["close_price"])),
                                volume=Decimal(str(latest["volume"])),
                                quote_volume=Decimal(str(latest["quote_volume"])),
                                trade_count=latest["trade_count"],
                                taker_buy_volume=Decimal(str(latest["taker_buy_volume"])),
                                taker_buy_quote_volume=Decimal(str(latest["taker_buy_quote_volume"]))
                            )
                        )
                    
                    return {
                        "status": "success",
                        "data": market_data,
                        "symbol": parsed_symbol.symbol,
                        "interval": interval,
                        "count": len(market_data),
                        "source": "binance_live"
                    }
            else:
                logger.warning("Binance client not available - API keys required")
            
        except Exception as binance_error:
            logger.warning(f"Binance API error for {symbol}: {binance_error}")
        
        # CRITICAL: NO FALLBACK TO SIMULATED DATA
        # If no real Binance data available, return error
        logger.error(f"No real Binance data available for {parsed_symbol.symbol}")
        raise HTTPException(
            status_code=503, 
            detail=f"Real Binance data not available for {parsed_symbol.symbol}. Configure BINANCE_TESTNET_API_KEY for live data."
        )
        
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market data: {str(e)}")

@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Get 24hr ticker statistics for a symbol"""
    try:
        parsed_symbol = CryptoSymbol.parse_symbol(symbol)
        
        # Try to get live data from Binance
        try:
            if binance_client:
                ticker = await binance_client.get_ticker_24hr(parsed_symbol.symbol)
                if ticker:
                    return {
                        "status": "success",
                        "data": ticker,
                        "symbol": parsed_symbol.symbol,
                        "source": "binance_live"
                    }
            else:
                logger.warning("Binance client not available - API keys required")
        except Exception as binance_error:
            logger.warning(f"Binance ticker error for {symbol}: {binance_error}")
        
        # CRITICAL: NO FALLBACK TO SIMULATED DATA  
        # If no real Binance data available, return error
        logger.error(f"No real Binance ticker data available for {parsed_symbol.symbol}")
        raise HTTPException(
            status_code=503,
            detail=f"Real Binance ticker data not available for {parsed_symbol.symbol}. Configure BINANCE_TESTNET_API_KEY for live data."
        )
        
    except Exception as e:
        logger.error(f"Error getting ticker for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting ticker: {str(e)}")

@router.get("/orderbook/{symbol}")
async def get_order_book(
    symbol: str,
    limit: int = Query(100, description="Number of price levels")
):
    """Get order book data for a symbol"""
    try:
        parsed_symbol = CryptoSymbol.parse_symbol(symbol)
        cache_manager = await get_cache_manager()
        
        # Try cache first
        cached_orderbook = await cache_manager.get_order_book(parsed_symbol.symbol)
        if cached_orderbook:
            return {
                "status": "success",
                "data": cached_orderbook,
                "symbol": parsed_symbol.symbol,
                "source": "cache"
            }
        
        # Try live data from Binance
        try:
            if binance_client:
                orderbook = await binance_client.get_order_book(parsed_symbol.symbol, limit)
                if orderbook:
                    # Cache the order book
                    await cache_manager.cache_order_book(parsed_symbol.symbol, orderbook)
                    
                    return {
                        "status": "success",
                        "data": orderbook,
                        "symbol": parsed_symbol.symbol,
                        "source": "binance_live"
                    }
            else:
                logger.warning("Binance client not available - API keys required")
        except Exception as binance_error:
            logger.warning(f"Binance order book error for {symbol}: {binance_error}")
        
        # CRITICAL: NO FALLBACK TO SIMULATED DATA
        # If no real Binance data available, return error
        logger.error(f"No real Binance order book data available for {parsed_symbol.symbol}")
        raise HTTPException(
            status_code=503,
            detail=f"Real Binance order book data not available for {parsed_symbol.symbol}. Configure BINANCE_TESTNET_API_KEY for live data."
        )
        
    except Exception as e:
        logger.error(f"Error getting order book for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting order book: {str(e)}")

# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for crypto market data service"""
    try:
        cache_manager = await get_cache_manager()
        cache_health = await cache_manager.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "cache": cache_health,
                "binance": "connected" if binance_client else "disconnected"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_cache_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@router.post("/cache/clear")
async def clear_cache(pattern: Optional[str] = None):
    """Clear cache by pattern"""
    try:
        cache_manager = await get_cache_manager()
        await cache_manager.clear_cache(pattern)
        
        return {
            "status": "success",
            "message": f"Cache cleared for pattern: {pattern}" if pattern else "All crypto cache cleared",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

# =============================================================================
# REAL PORTFOLIO ENDPOINTS
# =============================================================================

@router.get("/portfolio/balance")
async def get_real_portfolio_balance():
    """Get REAL portfolio balance from Binance testnet account"""
    try:
        if not binance_client:
            raise HTTPException(
                status_code=503, 
                detail="Binance client not initialized - API keys required"
            )
        
        # Get real account info from Binance testnet
        account_info = await binance_client.get_account_info()
        if not account_info:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch account info from Binance"
            )
        
        # Process real balances
        balances = account_info.get('balances', [])
        active_balances = []
        total_usdt_value = 0.0
        
        for balance in balances:
            free_amount = float(balance.get('free', 0))
            locked_amount = float(balance.get('locked', 0))
            total_amount = free_amount + locked_amount
            
            if total_amount > 0:
                asset = balance.get('asset')
                
                # Get USD value for non-USDT assets
                usd_value = total_amount
                if asset != 'USDT':
                    try:
                        # Get current price in USDT
                        ticker = await binance_client.get_ticker_24hr(f"{asset}USDT")
                        if ticker:
                            price = float(ticker.get('lastPrice', 0))
                            usd_value = total_amount * price
                    except:
                        # If no USDT pair, try BUSD or set to 0
                        usd_value = 0
                
                active_balances.append({
                    'asset': asset,
                    'free': free_amount,
                    'locked': locked_amount,
                    'total': total_amount,
                    'usd_value': round(usd_value, 2)
                })
                
                total_usdt_value += usd_value
        
        # Sort by USD value (highest first)
        active_balances.sort(key=lambda x: x['usd_value'], reverse=True)
        
        return {
            'success': True,
            'data': {
                'total_value': round(total_usdt_value, 2),
                'balances': active_balances,
                'account_type': 'SPOT',
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'binance_testnet'
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching real portfolio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch real portfolio data: {str(e)}"
        )

@router.get("/portfolio/performance")
async def get_real_portfolio_performance():
    """Get REAL portfolio performance - NO FAKE DATA"""
    try:
        # For now, return empty performance data until we have real trading history
        # This will be populated when actual trades are executed
        return {
            'success': True,
            'data': {
                'total_return': 0.0,
                'daily_return': 0.0,
                'chart_data': [],
                'message': 'REAL PERFORMANCE DATA WILL SHOW AFTER ACTUAL TRADES',
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching performance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch performance data: {str(e)}"
        )

@router.get("/market/live-prices")
async def get_live_crypto_prices():
    """Get REAL live prices for major crypto pairs"""
    try:
        if not binance_client:
            raise HTTPException(
                status_code=503,
                detail="Binance client not initialized - API keys required"
            )
        
        # Major crypto pairs to fetch
        major_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        live_prices = []
        
        for pair in major_pairs:
            try:
                ticker = await binance_client.get_ticker_24hr(pair)
                if ticker:
                    live_prices.append({
                        'symbol': pair,
                        'price': float(ticker.get('lastPrice', 0)),
                        'change_24h': float(ticker.get('priceChangePercent', 0)),
                        'volume_24h': float(ticker.get('volume', 0)),
                        'high_24h': float(ticker.get('highPrice', 0)),
                        'low_24h': float(ticker.get('lowPrice', 0)),
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch price for {pair}: {e}")
                continue
        
        return {
            'success': True,
            'data': {
                'prices': live_prices,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'binance_testnet_live'
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching live prices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch live market data: {str(e)}"
        )

@router.get("/market/ticker/{symbol}")
async def get_real_ticker(symbol: str):
    """Get REAL ticker data for a specific symbol"""
    try:
        if not binance_client:
            raise HTTPException(
                status_code=503,
                detail="Binance client not initialized - API keys required"
            )
        
        # Ensure symbol ends with USDT if not specified
        if not symbol.endswith('USDT') and not symbol.endswith('BUSD'):
            symbol = f"{symbol}USDT"
        
        ticker = await binance_client.get_ticker_24hr(symbol)
        if not ticker:
            raise HTTPException(
                status_code=404,
                detail=f"No ticker data found for {symbol}"
            )
        
        return {
            'success': True,
            'data': {
                'symbol': ticker.get('symbol'),
                'price': float(ticker.get('lastPrice', 0)),
                'change_24h': float(ticker.get('priceChangePercent', 0)),
                'volume_24h': float(ticker.get('volume', 0)),
                'high_24h': float(ticker.get('highPrice', 0)),
                'low_24h': float(ticker.get('lowPrice', 0)),
                'open_price': float(ticker.get('openPrice', 0)),
                'close_price': float(ticker.get('prevClosePrice', 0)),
                'count': int(ticker.get('count', 0)),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'binance_testnet_live'
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ticker data for {symbol}: {str(e)}"
        )

@router.get("/market/overview")
async def get_market_overview():
    """Get market overview with summary statistics"""
    try:
        if not binance_client:
            raise HTTPException(status_code=503, detail="Binance client not available")
        
        # Get some popular symbols for overview
        popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']
        
        market_data = {
            'active_pairs': len(popular_symbols),
            'total_market_cap': 'Loading...',
            'total_volume_24h': 'Loading...',
            'market_status': 'active',
            'last_updated': datetime.now().isoformat()
        }
        
        # Try to get real data for one symbol as example
        try:
            ticker = await binance_client.get_ticker('BTCUSDT')
            if ticker:
                market_data['total_market_cap'] = f"${float(ticker.get('price', 0)) * 1000000:,.0f}"
                market_data['total_volume_24h'] = f"${float(ticker.get('volume', 0)) * float(ticker.get('price', 0)):,.0f}"
        except Exception as e:
            logger.warning(f"Could not get real market data: {e}")
        
        return market_data
        
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize Binance client on startup
@router.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Only start if binance_client was initialized with real keys
        if binance_client:
            await binance_client.start()
            logger.info("✅ Binance client started")
        else:
            logger.warning("⚠️ Binance client not initialized with real keys, skipping startup.")
        logger.info("✅ Crypto market data service started")
    except Exception as e:
        logger.error(f"❌ Failed to start crypto market data service: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        # Only stop if binance_client was initialized with real keys
        if binance_client:
            await binance_client.stop()
        cache_manager = await get_cache_manager()
        await cache_manager.stop()
        logger.info("Crypto market data service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}") 
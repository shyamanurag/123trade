"""
Enhanced Market Data Manager - Zerodha API Compatible
Comprehensive data schema matching Zerodha's format with unified Redis caching
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import time
import os
import json
import redis
from contextlib import asynccontextmanager

# Zerodha imports
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

# Broker configuration system
from config.broker_config import get_active_broker_config, get_broker_config_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketDepth:
    """Zerodha market depth entry"""
    price: float
    quantity: int
    orders: int

@dataclass
class DepthData:
    """Zerodha bid/ask depth"""
    buy: List[MarketDepth]
    sell: List[MarketDepth]

@dataclass
class OHLC:
    """Zerodha OHLC data"""
    open: float
    high: float
    low: float
    close: float

@dataclass
class ZerodhaQuote:
    """Complete Zerodha quote data - matches API response exactly"""
    instrument_token: int
    timestamp: str
    last_trade_time: Optional[str]
    last_price: float
    last_quantity: int
    buy_quantity: int
    sell_quantity: int
    volume: int
    average_price: float
    oi: float  # Open Interest
    oi_day_high: float
    oi_day_low: float
    net_change: float
    lower_circuit_limit: float
    upper_circuit_limit: float
    ohlc: OHLC
    depth: DepthData

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        return result

@dataclass
class Candle:
    """Zerodha historical candle data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: Optional[float] = None  # For F&O instruments

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'oi': self.oi
        }

@dataclass
class EnhancedMarketData:
    """Enhanced market data container with all Zerodha fields"""
    # Core identification
    symbol: str
    instrument_token: int
    exchange: str
    
    # Price data
    last_price: float
    last_quantity: int
    last_trade_time: Optional[str]
    average_price: float
    net_change: float
    change_percent: float
    
    # OHLC data
    ohlc: OHLC
    
    # Volume and interest
    volume: int
    buy_quantity: int
    sell_quantity: int
    oi: float
    oi_day_high: float
    oi_day_low: float
    
    # Circuit limits
    lower_circuit_limit: float
    upper_circuit_limit: float
    
    # Market depth
    depth: DepthData
    
    # Historical data
    price_history: List[Candle]
    
    # Timestamps
    timestamp: str
    data_timestamp: datetime
    
    # Strategy-computed fields
    volatility: float = 0.0
    momentum: float = 0.0
    
    # Data quality
    data_quality: Dict[str, Any] = None
    source: str = "zerodha"

    def __post_init__(self):
        if self.data_quality is None:
            self.data_quality = {
                'has_depth': len(self.depth.buy) > 0 or len(self.depth.sell) > 0,
                'has_oi': self.oi > 0,
                'price_valid': self.last_price > 0,
                'volume_valid': self.volume >= 0,
                'within_circuits': self.lower_circuit_limit <= self.last_price <= self.upper_circuit_limit
            }
        
        # Calculate change percentage if not provided
        if self.change_percent == 0 and self.ohlc.close > 0:
            self.change_percent = (self.net_change / self.ohlc.close) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime to string
        result['data_timestamp'] = self.data_timestamp.isoformat()
        return result

    @classmethod
    def from_zerodha_quote(cls, symbol: str, quote_data: Dict[str, Any], price_history: List[Candle] = None) -> 'EnhancedMarketData':
        """Create EnhancedMarketData from Zerodha quote API response"""
        
        # Extract OHLC
        ohlc_data = quote_data.get('ohlc', {})
        ohlc = OHLC(
            open=ohlc_data.get('open', quote_data.get('last_price', 0)),
            high=ohlc_data.get('high', quote_data.get('last_price', 0)),
            low=ohlc_data.get('low', quote_data.get('last_price', 0)),
            close=ohlc_data.get('close', quote_data.get('last_price', 0))
        )
        
        # Extract market depth
        depth_data = quote_data.get('depth', {'buy': [], 'sell': []})
        
        buy_depth = []
        for entry in depth_data.get('buy', [])[:5]:  # Top 5 levels
            if entry.get('price', 0) > 0:
                buy_depth.append(MarketDepth(
                    price=entry.get('price', 0),
                    quantity=entry.get('quantity', 0),
                    orders=entry.get('orders', 0)
                ))
        
        sell_depth = []
        for entry in depth_data.get('sell', [])[:5]:  # Top 5 levels
            if entry.get('price', 0) > 0:
                sell_depth.append(MarketDepth(
                    price=entry.get('price', 0),
                    quantity=entry.get('quantity', 0),
                    orders=entry.get('orders', 0)
                ))
        
        depth = DepthData(buy=buy_depth, sell=sell_depth)
        
        # Extract exchange from symbol
        exchange = symbol.split(':')[0] if ':' in symbol else 'NSE'
        
        return cls(
            symbol=symbol,
            instrument_token=quote_data.get('instrument_token', 0),
            exchange=exchange,
            last_price=quote_data.get('last_price', 0),
            last_quantity=quote_data.get('last_quantity', 0),
            last_trade_time=quote_data.get('last_trade_time'),
            average_price=quote_data.get('average_price', quote_data.get('last_price', 0)),
            net_change=quote_data.get('net_change', 0),
            change_percent=0,  # Will be calculated in __post_init__
            ohlc=ohlc,
            volume=quote_data.get('volume', 0),
            buy_quantity=quote_data.get('buy_quantity', 0),
            sell_quantity=quote_data.get('sell_quantity', 0),
            oi=quote_data.get('oi', 0),
            oi_day_high=quote_data.get('oi_day_high', 0),
            oi_day_low=quote_data.get('oi_day_low', 0),
            lower_circuit_limit=quote_data.get('lower_circuit_limit', 0),
            upper_circuit_limit=quote_data.get('upper_circuit_limit', 0),
            depth=depth,
            price_history=price_history or [],
            timestamp=quote_data.get('timestamp', datetime.now().isoformat()),
            data_timestamp=datetime.now()
        )

class ZerodhaMarketDataCache:
    """Unified Redis caching system for Zerodha market data"""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self._setup_redis(redis_url)
        
        # Cache configuration
        self.quote_ttl = 60  # 1 minute for quotes
        self.historical_ttl = 3600  # 1 hour for historical data
        self.instruments_ttl = 86400  # 1 day for instruments list
        
    def _setup_redis(self, redis_url: str = None):
        """Setup Redis connection"""
        try:
            if not redis_url:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Parse Redis URL
            from urllib.parse import urlparse
            import ssl
            
            parsed = urlparse(redis_url)
            redis_host = parsed.hostname or 'localhost'
            redis_port = parsed.port or 6379
            redis_password = parsed.password
            redis_db = int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
            
            # Check if SSL is required
            ssl_required = 'ondigitalocean.com' in redis_host or redis_url.startswith('rediss://')
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                ssl=ssl_required,
                ssl_cert_reqs=ssl.CERT_NONE if ssl_required else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis connected for Zerodha cache: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.redis_client = None
    
    def cache_quote(self, symbol: str, market_data: EnhancedMarketData):
        """Cache market data quote"""
        if not self.redis_client:
            return
        
        try:
            # Cache individual quote
            key = f"zerodha:quote:{symbol}"
            self.redis_client.setex(key, self.quote_ttl, json.dumps(market_data.to_dict()))
            
            # Cache in live data hash
            self.redis_client.hset("zerodha:live_quotes", symbol, json.dumps(market_data.to_dict()))
            self.redis_client.expire("zerodha:live_quotes", self.quote_ttl)
            
            # Update metadata
            self.redis_client.setex(f"zerodha:last_update:{symbol}", self.quote_ttl, datetime.now().isoformat())
            self.redis_client.setex("zerodha:symbols_count", self.quote_ttl, self.redis_client.hlen("zerodha:live_quotes"))
            
        except Exception as e:
            logger.error(f"❌ Redis cache error for {symbol}: {e}")
    
    def get_quote(self, symbol: str) -> Optional[EnhancedMarketData]:
        """Get cached market data quote"""
        if not self.redis_client:
            return None
        
        try:
            key = f"zerodha:quote:{symbol}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data_dict = json.loads(cached_data)
                # Reconstruct EnhancedMarketData object
                return self._dict_to_market_data(data_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Redis get error for {symbol}: {e}")
            return None
    
    def get_all_quotes(self) -> Dict[str, EnhancedMarketData]:
        """Get all cached quotes"""
        if not self.redis_client:
            return {}
        
        try:
            cached_data = self.redis_client.hgetall("zerodha:live_quotes")
            result = {}
            
            for symbol, data_json in cached_data.items():
                try:
                    data_dict = json.loads(data_json)
                    result[symbol] = self._dict_to_market_data(data_dict)
                except json.JSONDecodeError:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Redis get all quotes error: {e}")
            return {}
    
    def cache_historical_data(self, symbol: str, interval: str, candles: List[Candle]):
        """Cache historical data"""
        if not self.redis_client:
            return
        
        try:
            key = f"zerodha:historical:{symbol}:{interval}"
            candles_data = [candle.to_dict() for candle in candles]
            self.redis_client.setex(key, self.historical_ttl, json.dumps(candles_data))
            
        except Exception as e:
            logger.error(f"❌ Redis historical cache error for {symbol}: {e}")
    
    def get_historical_data(self, symbol: str, interval: str) -> List[Candle]:
        """Get cached historical data"""
        if not self.redis_client:
            return []
        
        try:
            key = f"zerodha:historical:{symbol}:{interval}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                candles_data = json.loads(cached_data)
                candles = []
                for candle_dict in candles_data:
                    candles.append(Candle(
                        timestamp=datetime.fromisoformat(candle_dict['timestamp']),
                        open=candle_dict['open'],
                        high=candle_dict['high'],
                        low=candle_dict['low'],
                        close=candle_dict['close'],
                        volume=candle_dict['volume'],
                        oi=candle_dict.get('oi')
                    ))
                return candles
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Redis historical get error for {symbol}: {e}")
            return []
    
    def _dict_to_market_data(self, data_dict: Dict[str, Any]) -> EnhancedMarketData:
        """Convert dictionary back to EnhancedMarketData object"""
        
        # Reconstruct OHLC
        ohlc_data = data_dict.get('ohlc', {})
        ohlc = OHLC(
            open=ohlc_data.get('open', 0),
            high=ohlc_data.get('high', 0),
            low=ohlc_data.get('low', 0),
            close=ohlc_data.get('close', 0)
        )
        
        # Reconstruct depth
        depth_data = data_dict.get('depth', {'buy': [], 'sell': []})
        
        buy_depth = []
        for entry in depth_data.get('buy', []):
            buy_depth.append(MarketDepth(
                price=entry.get('price', 0),
                quantity=entry.get('quantity', 0),
                orders=entry.get('orders', 0)
            ))
        
        sell_depth = []
        for entry in depth_data.get('sell', []):
            sell_depth.append(MarketDepth(
                price=entry.get('price', 0),
                quantity=entry.get('quantity', 0),
                orders=entry.get('orders', 0)
            ))
        
        depth = DepthData(buy=buy_depth, sell=sell_depth)
        
        # Reconstruct price history
        price_history = []
        for candle_data in data_dict.get('price_history', []):
            price_history.append(Candle(
                timestamp=datetime.fromisoformat(candle_data['timestamp']),
                open=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data['volume'],
                oi=candle_data.get('oi')
            ))
        
        return EnhancedMarketData(
            symbol=data_dict.get('symbol', ''),
            instrument_token=data_dict.get('instrument_token', 0),
            exchange=data_dict.get('exchange', 'NSE'),
            last_price=data_dict.get('last_price', 0),
            last_quantity=data_dict.get('last_quantity', 0),
            last_trade_time=data_dict.get('last_trade_time'),
            average_price=data_dict.get('average_price', 0),
            net_change=data_dict.get('net_change', 0),
            change_percent=data_dict.get('change_percent', 0),
            ohlc=ohlc,
            volume=data_dict.get('volume', 0),
            buy_quantity=data_dict.get('buy_quantity', 0),
            sell_quantity=data_dict.get('sell_quantity', 0),
            oi=data_dict.get('oi', 0),
            oi_day_high=data_dict.get('oi_day_high', 0),
            oi_day_low=data_dict.get('oi_day_low', 0),
            lower_circuit_limit=data_dict.get('lower_circuit_limit', 0),
            upper_circuit_limit=data_dict.get('upper_circuit_limit', 0),
            depth=depth,
            price_history=price_history,
            timestamp=data_dict.get('timestamp', ''),
            data_timestamp=datetime.fromisoformat(data_dict.get('data_timestamp', datetime.now().isoformat())),
            volatility=data_dict.get('volatility', 0.0),
            momentum=data_dict.get('momentum', 0.0),
            data_quality=data_dict.get('data_quality', {}),
            source=data_dict.get('source', 'zerodha')
        )

class EnhancedZerodhaMarketDataManager:
    """Enhanced market data manager with complete Zerodha API compatibility"""
    
    def __init__(self, symbols: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # NO HARD-CODED SYMBOLS - ALL SYMBOLS MUST BE PROVIDED DYNAMICALLY
        if not symbols:
            raise ValueError("Symbols must be provided - no hard-coded symbols allowed")
        self.symbols = symbols
        
        # Initialize Zerodha client
        self.kite = None
        self.instruments_map = {}  # symbol -> instrument_token mapping
        
        # Initialize cache
        self.cache = ZerodhaMarketDataCache()
        
        # Configuration
        self.paper_trading_mode = (config or {}).get('paper_trading', True)
        self.update_interval = 1.0  # 1 second updates
        self.is_running = False
        
        logger.info(f"📊 Enhanced MarketDataManager initialized with {len(self.symbols)} symbols")
        logger.info(f"📝 Paper Trading: {'Enabled' if self.paper_trading_mode else 'Disabled'}")
        
        # Initialize Zerodha client
        self._init_zerodha_client()
    
    def _init_zerodha_client(self):
        """Initialize Zerodha client"""
        try:
            # Get credentials from environment
            api_key = os.environ.get('ZERODHA_API_KEY')
            access_token = os.environ.get('ZERODHA_ACCESS_TOKEN')
            
            if not all([api_key, access_token]):
                logger.error("❌ Zerodha credentials not found in environment variables")
                logger.error("Required: ZERODHA_API_KEY, ZERODHA_ACCESS_TOKEN")
                return
            
            # Create Zerodha client
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
            
            # Test connection and load instruments
            profile = self.kite.profile()
            logger.info(f"✅ Zerodha client initialized for user: {profile.get('user_name', 'Unknown')}")
            
            # Load instruments mapping
            asyncio.create_task(self._load_instruments_mapping())
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Zerodha client: {e}")
            self.kite = None
    
    async def _load_instruments_mapping(self):
        """Load instruments mapping for symbol to token conversion"""
        try:
            if not self.kite:
                return
            
            # Get instruments list
            instruments = self.kite.instruments()
            
            for instrument in instruments:
                # Create symbol mapping
                exchange = instrument['exchange']
                tradingsymbol = instrument['tradingsymbol']
                symbol_key = f"{exchange}:{tradingsymbol}"
                
                self.instruments_map[symbol_key] = {
                    'instrument_token': instrument['instrument_token'],
                    'exchange_token': instrument['exchange_token'],
                    'name': instrument['name'],
                    'exchange': exchange,
                    'tradingsymbol': tradingsymbol,
                    'instrument_type': instrument['instrument_type'],
                    'segment': instrument['segment'],
                    'tick_size': instrument['tick_size'],
                    'lot_size': instrument['lot_size']
                }
            
            logger.info(f"✅ Loaded {len(self.instruments_map)} instrument mappings")
            
        except Exception as e:
            logger.error(f"❌ Failed to load instruments mapping: {e}")
    
    def get_instrument_token(self, symbol: str) -> Optional[int]:
        """Get instrument token for symbol"""
        zerodha_symbol = self._get_zerodha_symbol(symbol)
        instrument_info = self.instruments_map.get(zerodha_symbol)
        return instrument_info['instrument_token'] if instrument_info else None
    
    def _get_zerodha_symbol(self, symbol: str) -> str:
        """Convert symbol to Zerodha format"""
        if ':' in symbol:
            return symbol
        return f"NSE:{symbol}"
    
    async def get_market_data(self, symbol: str) -> Optional[EnhancedMarketData]:
        """Get comprehensive market data for a symbol"""
        try:
            # Try cache first
            cached_data = self.cache.get_quote(symbol)
            if cached_data:
                return cached_data
            
            # Get from Zerodha API
            if not self.kite:
                logger.error("❌ Zerodha client not initialized")
                return None
            
            zerodha_symbol = self._get_zerodha_symbol(symbol)
            quote = self.kite.quote(zerodha_symbol)
            
            if zerodha_symbol not in quote:
                logger.warning(f"⚠️ No quote data for {zerodha_symbol}")
                return None
            
            quote_data = quote[zerodha_symbol]
            
            # Get historical data
            instrument_token = self.get_instrument_token(symbol)
            price_history = []
            
            if instrument_token:
                try:
                    to_date = datetime.now()
                    from_date = to_date - timedelta(days=50)
                    
                    historical_data = self.kite.historical_data(
                        instrument_token=instrument_token,
                        from_date=from_date,
                        to_date=to_date,
                        interval="day"
                    )
                    
                    for candle_data in historical_data:
                        price_history.append(Candle(
                            timestamp=candle_data['date'],
                            open=candle_data['open'],
                            high=candle_data['high'],
                            low=candle_data['low'],
                            close=candle_data['close'],
                            volume=candle_data['volume'],
                            oi=candle_data.get('oi')
                        ))
                
                except Exception as hist_error:
                    logger.warning(f"⚠️ Failed to get historical data for {symbol}: {hist_error}")
            
            # Create enhanced market data
            market_data = EnhancedMarketData.from_zerodha_quote(symbol, quote_data, price_history)
            
            # Cache the data
            self.cache.cache_quote(symbol, market_data)
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data for {symbol}: {e}")
            return None
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, EnhancedMarketData]:
        """Get market data for multiple symbols efficiently"""
        result = {}
        
        # Get symbols that aren't cached
        uncached_symbols = []
        for symbol in symbols:
            cached_data = self.cache.get_quote(symbol)
            if cached_data:
                result[symbol] = cached_data
            else:
                uncached_symbols.append(symbol)
        
        # Batch fetch uncached symbols
        if uncached_symbols and self.kite:
            try:
                zerodha_symbols = [self._get_zerodha_symbol(symbol) for symbol in uncached_symbols]
                quotes = self.kite.quote(zerodha_symbols)
                
                for symbol in uncached_symbols:
                    zerodha_symbol = self._get_zerodha_symbol(symbol)
                    if zerodha_symbol in quotes:
                        quote_data = quotes[zerodha_symbol]
                        market_data = EnhancedMarketData.from_zerodha_quote(symbol, quote_data)
                        result[symbol] = market_data
                        
                        # Cache the data
                        self.cache.cache_quote(symbol, market_data)
                
            except Exception as e:
                logger.error(f"❌ Error getting multiple quotes: {e}")
        
        return result
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection and cache status"""
        return {
            'zerodha_connected': self.kite is not None,
            'paper_trading': self.paper_trading_mode,
            'redis_connected': self.cache.redis_client is not None,
            'instruments_loaded': len(self.instruments_map),
            'symbols_configured': len(self.symbols),
            'cache_stats': {
                'quotes_cached': self.cache.redis_client.hlen("zerodha:live_quotes") if self.cache.redis_client else 0
            }
        }

# Global instance for unified access
_enhanced_market_data_manager = None

def get_enhanced_market_data_manager() -> EnhancedZerodhaMarketDataManager:
    """Get the global enhanced market data manager instance"""
    global _enhanced_market_data_manager
    if _enhanced_market_data_manager is None:
        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_config()
        # Use a default symbol list for initialization
        default_symbols = ['NSE:NIFTY50', 'NSE:BANKNIFTY', 'NSE:RELIANCE', 'NSE:TCS', 'NSE:INFY']
        _enhanced_market_data_manager = EnhancedZerodhaMarketDataManager(default_symbols, config)
    return _enhanced_market_data_manager 
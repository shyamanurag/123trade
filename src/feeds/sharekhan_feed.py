"""
ShareKhan Data Feed
Complete replacement for ShareKhan with real-time market data streaming
"""

import asyncio
import logging
import json
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from dataclasses import dataclass, asdict
import websocket
from collections import defaultdict, deque

from brokers.sharekhan import ShareKhanIntegration, ShareKhanMarketData

logger = logging.getLogger(__name__)

@dataclass
class ShareKhanTick:
    """ShareKhan tick data structure"""
    symbol: str
    exchange: str
    instrument_token: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int
    timestamp: datetime
    bid_price: float = 0
    ask_price: float = 0
    bid_qty: int = 0
    ask_qty: int = 0

@dataclass
class ShareKhanHistoricalData:
    """ShareKhan historical data structure"""
    symbol: str
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int = 0

class ShareKhanDataFeed:
    """
    Real-time data feed using ShareKhan APIs
    Complete replacement for ShareKhan with in-memory streaming
    """
    
    def __init__(self, api_key: str, access_token: str, redis_client: redis.Redis):
        self.api_key = api_key
        self.access_token = access_token
        self.redis_client = redis_client
        
        # ShareKhan integration for data
        self.sharekhan = ShareKhanIntegration(api_key, "", "")  # Only for data access
        self.sharekhan.access_token = access_token
        self.sharekhan.is_authenticated = True
        
        # Real-time data storage (in-memory)
        self.live_ticks: Dict[str, ShareKhanTick] = {}
        self.historical_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.symbol_mapping: Dict[str, str] = {}  # symbol -> instrument_token
        
        # Subscriptions and callbacks
        self.subscribed_symbols = set()
        self.tick_callbacks: List[Callable] = []
        self.data_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # WebSocket state
        self.ws_connected = False
        self.ws_thread = None
        self.last_heartbeat = datetime.now()
        
        # Rate limiting and performance
        self.update_frequency = 1  # seconds
        self.batch_size = 50
        self.last_batch_time = datetime.now()
        
        # Symbol master
        self.symbol_master: Dict[str, Dict] = {}
        
        logger.info("✅ ShareKhan data feed initialized")
    
    async def initialize(self) -> bool:
        """Initialize the data feed"""
        try:
            # Load symbol master
            await self._load_symbol_master()
            
            # Initialize WebSocket for real-time data
            await self._initialize_real_time_feed()
            
            # Start background tasks
            asyncio.create_task(self._heartbeat_monitor())
            asyncio.create_task(self._data_cleanup_task())
            
            logger.info("✅ ShareKhan data feed initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ ShareKhan data feed initialization failed: {e}")
            return False
    
    async def _load_symbol_master(self):
        """Load symbol master from ShareKhan API"""
        try:
            # Get symbol master data
            url = f"https://api.sharekhan.com/market/symbols"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-API-KEY": self.api_key
            }
            
            import requests
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    symbols = data.get('symbols', [])
                    
                    for symbol_data in symbols:
                        symbol = symbol_data.get('trading_symbol')
                        instrument_token = symbol_data.get('instrument_token')
                        
                        if symbol and instrument_token:
                            self.symbol_master[symbol] = symbol_data
                            self.symbol_mapping[symbol] = instrument_token
                    
                    logger.info(f"✅ Loaded {len(self.symbol_master)} symbols from ShareKhan")
                else:
                    logger.error("❌ Failed to load symbol master")
            else:
                logger.error(f"❌ Symbol master API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Symbol master loading error: {e}")
    
    async def _initialize_real_time_feed(self):
        """Initialize real-time WebSocket data feed"""
        try:
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self._handle_tick_data(data)
                except Exception as e:
                    logger.error(f"Tick data parsing error: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket data feed error: {error}")
                self.ws_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("WebSocket data feed closed")
                self.ws_connected = False
                # Auto-reconnect
                threading.Timer(5.0, self._reconnect_feed).start()
            
            def on_open(ws):
                logger.info("✅ ShareKhan real-time data feed connected")
                self.ws_connected = True
                self.last_heartbeat = datetime.now()
                
                # Subscribe to all requested symbols
                if self.subscribed_symbols:
                    self._send_subscription_message(list(self.subscribed_symbols))
            
            # Create WebSocket connection for data feed
            ws_url = f"wss://datafeed.sharekhan.com/ws?access_token={self.access_token}"
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            logger.info("🔌 ShareKhan real-time data feed initialized")
            
        except Exception as e:
            logger.error(f"❌ Real-time feed initialization error: {e}")
    
    def _handle_tick_data(self, data: Dict):
        """Handle incoming tick data from WebSocket"""
        try:
            if data.get('type') == 'tick':
                tick_data = data.get('data', {})
                symbol = tick_data.get('symbol')
                
                if symbol:
                    # Create ShareKhan tick object
                    tick = ShareKhanTick(
                        symbol=symbol,
                        exchange=tick_data.get('exchange', ''),
                        instrument_token=tick_data.get('instrument_token', ''),
                        ltp=float(tick_data.get('ltp', 0)),
                        open=float(tick_data.get('open', 0)),
                        high=float(tick_data.get('high', 0)),
                        low=float(tick_data.get('low', 0)),
                        close=float(tick_data.get('close', 0)),
                        volume=int(tick_data.get('volume', 0)),
                        oi=int(tick_data.get('oi', 0)),
                        timestamp=datetime.now(),
                        bid_price=float(tick_data.get('bid_price', 0)),
                        ask_price=float(tick_data.get('ask_price', 0)),
                        bid_qty=int(tick_data.get('bid_qty', 0)),
                        ask_qty=int(tick_data.get('ask_qty', 0))
                    )
                    
                    # Update live ticks in memory immediately
                    self.live_ticks[symbol] = tick
                    
                    # Add to historical cache
                    historical_point = ShareKhanHistoricalData(
                        symbol=symbol,
                        datetime=tick.timestamp,
                        open=tick.open,
                        high=tick.high,
                        low=tick.low,
                        close=tick.ltp,
                        volume=tick.volume,
                        oi=tick.oi
                    )
                    self.historical_cache[symbol].append(historical_point)
                    
                    # Update heartbeat
                    self.last_heartbeat = datetime.now()
                    
                    # Notify callbacks
                    self._notify_tick_callbacks(tick)
                    
                    # Cache in Redis for persistence (async)
                    asyncio.create_task(self._cache_tick_data(tick))
                    
            elif data.get('type') == 'heartbeat':
                self.last_heartbeat = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Tick data handling error: {e}")
    
    def _notify_tick_callbacks(self, tick: ShareKhanTick):
        """Notify all registered tick callbacks"""
        try:
            # General tick callbacks
            for callback in self.tick_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Tick callback error: {e}")
            
            # Symbol-specific callbacks
            symbol_callbacks = self.data_callbacks.get(tick.symbol, [])
            for callback in symbol_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Symbol callback error for {tick.symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Callback notification error: {e}")
    
    async def _cache_tick_data(self, tick: ShareKhanTick):
        """Cache tick data in Redis for persistence"""
        try:
            if self.redis_client:
                # Cache latest tick
                key = f"sharekhan:tick:{tick.symbol}"
                data = asdict(tick)
                data['timestamp'] = tick.timestamp.isoformat()
                
                await self.redis_client.setex(
                    key, 
                    3600,  # 1 hour expiry
                    json.dumps(data)
                )
                
                # Cache in time series for historical data
                ts_key = f"sharekhan:timeseries:{tick.symbol}"
                await self.redis_client.zadd(
                    ts_key,
                    {json.dumps(data): tick.timestamp.timestamp()}
                )
                
                # Keep only last 1000 points
                await self.redis_client.zremrangebyrank(ts_key, 0, -1001)
                
        except Exception as e:
            logger.error(f"❌ Redis caching error: {e}")
    
    async def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to real-time data for symbols"""
        try:
            # Validate symbols exist in master
            valid_symbols = []
            for symbol in symbols:
                if symbol in self.symbol_master:
                    valid_symbols.append(symbol)
                    self.subscribed_symbols.add(symbol)
                else:
                    logger.warning(f"Symbol {symbol} not found in master")
            
            if not valid_symbols:
                logger.error("❌ No valid symbols to subscribe")
                return False
            
            # Send subscription message if WebSocket is connected
            if self.ws_connected:
                self._send_subscription_message(valid_symbols)
            
            logger.info(f"✅ Subscribed to {len(valid_symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Symbol subscription error: {e}")
            return False
    
    def _send_subscription_message(self, symbols: List[str]):
        """Send subscription message via WebSocket"""
        try:
            # Convert symbols to instrument tokens
            instrument_tokens = []
            for symbol in symbols:
                token = self.symbol_mapping.get(symbol)
                if token:
                    instrument_tokens.append(token)
            
            if instrument_tokens:
                message = {
                    "action": "subscribe",
                    "instruments": instrument_tokens
                }
                
                self.ws.send(json.dumps(message))
                logger.info(f"📡 Sent subscription for {len(instrument_tokens)} instruments")
                
        except Exception as e:
            logger.error(f"❌ Subscription message error: {e}")
    
    async def unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """Unsubscribe from real-time data for symbols"""
        try:
            for symbol in symbols:
                self.subscribed_symbols.discard(symbol)
            
            if self.ws_connected:
                instrument_tokens = []
                for symbol in symbols:
                    token = self.symbol_mapping.get(symbol)
                    if token:
                        instrument_tokens.append(token)
                
                if instrument_tokens:
                    message = {
                        "action": "unsubscribe",
                        "instruments": instrument_tokens
                    }
                    
                    self.ws.send(json.dumps(message))
            
            logger.info(f"✅ Unsubscribed from {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Symbol unsubscription error: {e}")
            return False
    
    async def get_live_data(self, symbol: str) -> Optional[ShareKhanTick]:
        """Get live tick data for symbol from memory"""
        return self.live_ticks.get(symbol)
    
    async def get_historical_data(self, symbol: str, interval: str, 
                                 from_date: datetime, to_date: datetime) -> List[ShareKhanHistoricalData]:
        """Get historical data from ShareKhan API"""
        try:
            url = f"https://api.sharekhan.com/market/historical"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "symbol": symbol,
                "interval": interval,
                "from_date": from_date.strftime("%Y-%m-%d"),
                "to_date": to_date.strftime("%Y-%m-%d")
            }
            
            import requests
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    historical_data = []
                    
                    for point in data.get('data', []):
                        hist_point = ShareKhanHistoricalData(
                            symbol=symbol,
                            datetime=datetime.fromisoformat(point['datetime']),
                            open=float(point['open']),
                            high=float(point['high']),
                            low=float(point['low']),
                            close=float(point['close']),
                            volume=int(point['volume']),
                            oi=int(point.get('oi', 0))
                        )
                        historical_data.append(hist_point)
                    
                    # Cache in memory
                    self.historical_cache[symbol].extend(historical_data)
                    
                    logger.info(f"✅ Retrieved {len(historical_data)} historical points for {symbol}")
                    return historical_data
                else:
                    logger.error(f"❌ Historical data API error: {data.get('error')}")
                    return []
            else:
                logger.error(f"❌ Historical data HTTP error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Historical data error: {e}")
            return []
    
    async def get_cached_historical_data(self, symbol: str, limit: int = 100) -> List[ShareKhanHistoricalData]:
        """Get cached historical data from memory"""
        try:
            cached_data = list(self.historical_cache.get(symbol, []))
            return cached_data[-limit:] if limit else cached_data
        except Exception as e:
            logger.error(f"❌ Cached data retrieval error: {e}")
            return []
    
    def add_tick_callback(self, callback: Callable):
        """Add callback for all tick updates"""
        self.tick_callbacks.append(callback)
    
    def add_symbol_callback(self, symbol: str, callback: Callable):
        """Add callback for specific symbol updates"""
        self.data_callbacks[symbol].append(callback)
    
    def remove_tick_callback(self, callback: Callable):
        """Remove tick callback"""
        if callback in self.tick_callbacks:
            self.tick_callbacks.remove(callback)
    
    def remove_symbol_callback(self, symbol: str, callback: Callable):
        """Remove symbol-specific callback"""
        if callback in self.data_callbacks[symbol]:
            self.data_callbacks[symbol].remove(callback)
    
    async def _heartbeat_monitor(self):
        """Monitor WebSocket heartbeat and reconnect if needed"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.ws_connected:
                    time_since_heartbeat = (datetime.now() - self.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > 60:  # 1 minute without heartbeat
                        logger.warning("⚠️ No heartbeat received, reconnecting...")
                        self.ws_connected = False
                        self._reconnect_feed()
                
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
    
    async def _data_cleanup_task(self):
        """Clean up old data from memory"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up old ticks (keep only last 1000 per symbol)
                for symbol in list(self.historical_cache.keys()):
                    cache = self.historical_cache[symbol]
                    if len(cache) > 1000:
                        # Keep only the most recent 1000 points
                        recent_points = list(cache)[-1000:]
                        self.historical_cache[symbol] = deque(recent_points, maxlen=1000)
                
                logger.info("✅ Completed data cleanup")
                
            except Exception as e:
                logger.error(f"❌ Data cleanup error: {e}")
    
    def _reconnect_feed(self):
        """Reconnect WebSocket feed"""
        try:
            if not self.ws_connected:
                logger.info("🔄 Attempting to reconnect ShareKhan data feed...")
                
                if self.ws:
                    self.ws.close()
                
                # Reinitialize WebSocket connection
                asyncio.create_task(self._initialize_real_time_feed())
                
        except Exception as e:
            logger.error(f"❌ Feed reconnection error: {e}")
    
    async def disconnect(self):
        """Disconnect from data feed"""
        try:
            self.ws_connected = False
            
            if self.ws:
                self.ws.close()
            
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=5)
            
            logger.info("✅ ShareKhan data feed disconnected")
            
        except Exception as e:
            logger.error(f"❌ Disconnection error: {e}")
    
    def get_feed_status(self) -> Dict:
        """Get current feed status"""
        return {
            "connected": self.ws_connected,
            "subscribed_symbols": len(self.subscribed_symbols),
            "live_data_symbols": len(self.live_ticks),
            "cached_symbols": len(self.historical_cache),
            "symbol_master_loaded": len(self.symbol_master),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "callbacks_registered": len(self.tick_callbacks)
        }


class ShareKhanShareKhanCompatibility:
    """
    Compatibility layer to make ShareKhan data feed work with existing ShareKhan code
    Ensures seamless transition without breaking existing functionality
    """
    
    def __init__(self, sharekhan_feed: ShareKhanDataFeed):
        self.sharekhan_feed = sharekhan_feed
        self.live_market_data = {}  # ShareKhan-compatible format
        
        # Add callback to convert ShareKhan data to ShareKhan format
        self.sharekhan_feed.add_tick_callback(self._convert_to_sharekhan_format)
    
    def _convert_to_sharekhan_format(self, tick: ShareKhanTick):
        """Convert ShareKhan tick to ShareKhan-compatible format"""
        try:
            # Convert to ShareKhan format for backward compatibility
            sharekhan_tick = {
                'symbol': tick.symbol,
                'ltp': tick.ltp,
                'open': tick.open,
                'high': tick.high,
                'low': tick.low,
                'close': tick.close,
                'volume': tick.volume,
                'oi': tick.oi,
                'timestamp': tick.timestamp,
                'bid': tick.bid_price,
                'ask': tick.ask_price,
                'bid_qty': tick.bid_qty,
                'ask_qty': tick.ask_qty
            }
            
            # Update live market data cache (ShareKhan compatible)
            self.live_market_data[tick.symbol] = sharekhan_tick
            
        except Exception as e:
            logger.error(f"❌ ShareKhan format conversion error: {e}")
    
    def get_live_data_for_symbol(self, symbol: str) -> Optional[Dict]:
        """Get live data in ShareKhan-compatible format"""
        return self.live_market_data.get(symbol)
    
    def is_connected(self) -> bool:
        """Check if data feed is connected (ShareKhan compatible)"""
        return self.sharekhan_feed.ws_connected 
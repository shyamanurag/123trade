"""
Market Data Aggregator
Unifies data from ShareKhan and ShareKhan and broadcasts via WebSocket
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import redis.asyncio as redis

from ..feeds.sharekhan_feed import ShareKhanFeed
from .sharekhan import ShareKhanIntegration
from .websocket_manager import WebSocketManager, MarketDataUpdate

logger = logging.getLogger(__name__)

class MarketDataAggregator:
    """Aggregates market data from multiple sources"""
    
    def __init__(self, 
                 redis_client: redis.Redis,
                 websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.sharekhan_feed = ShareKhanFeed()
        self.sharekhan_integration = None
        self.is_running = False
        self.subscribed_symbols = set()
        
    async def initialize(self, sharekhan_integration: Optional[ShareKhanIntegration] = None):
        """Initialize the aggregator"""
        try:
            # FIXED: Use existing ShareKhan cache instead of trying to connect
            # ShareKhan is already connected and flowing data in the main app
            from data.sharekhan_client import live_market_data, is_connected
            
            if live_market_data and len(live_market_data) > 0:
                logger.info(f"✅ ShareKhan cache available: {len(live_market_data)} symbols")
                # Set up cache monitoring instead of direct connection
                self.sharekhan_feed.cache_data = live_market_data
                self.sharekhan_feed.connected = True
            else:
                logger.warning("⚠️ ShareKhan cache is empty - market data not available")
                self.sharekhan_feed.connected = False
            
            # Initialize ShareKhan if provided
            if sharekhan_integration:
                self.sharekhan_integration = sharekhan_integration
                # Set up ShareKhan callbacks
                self.sharekhan_integration.market_data_callbacks.append(
                    self._handle_sharekhan_tick
                )
            
            logger.info("Market data aggregator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize market data aggregator: {e}")
            raise
    
    async def start(self):
        """Start the aggregator"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start ShareKhan listener
        asyncio.create_task(self._sharekhan_listener())
        
        logger.info("Market data aggregator started")
    
    async def stop(self):
        """Stop the aggregator"""
        self.is_running = False
        await self.sharekhan_feed.disconnect()
        logger.info("Market data aggregator stopped")
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to a symbol across all providers"""
        if symbol in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.add(symbol)
        
        # Subscribe on ShareKhan
        await self.sharekhan_feed.subscribe([symbol])
        
        # Subscribe on ShareKhan if available
        if self.sharekhan_integration:
            await self.sharekhan_integration.subscribe_market_data([symbol])
        
        logger.info(f"Subscribed to {symbol} on all providers")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from a symbol"""
        if symbol not in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.remove(symbol)
        
        # Unsubscribe from ShareKhan
        await self.sharekhan_feed.unsubscribe([symbol])
        
        # Unsubscribe from ShareKhan if available
        if self.sharekhan_integration:
            await self.sharekhan_integration.unsubscribe_market_data([symbol])
        
        logger.info(f"Unsubscribed from {symbol} on all providers")
    
    async def _sharekhan_listener(self):
        """Listen for ShareKhan updates"""
        while self.is_running:
            try:
                if self.sharekhan_feed.connected:
                    # Process any queued messages
                    # This would be implemented based on ShareKhan's callback mechanism
                    await asyncio.sleep(0.1)
                else:
                    # Try to reconnect
                    await self.sharekhan_feed.connect()
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in ShareKhan listener: {e}")
                await asyncio.sleep(5)
    
    async def _handle_sharekhan_tick(self, tick_data: Dict):
        """Handle ShareKhan tick data"""
        try:
            # Convert ShareKhan format to unified format
            market_update = MarketDataUpdate(
                symbol=tick_data.get('trading_symbol', ''),
                price=tick_data.get('last_price', 0.0),
                volume=tick_data.get('volume', 0),
                timestamp=datetime.now().isoformat(),
                change=tick_data.get('change', 0.0),
                change_percent=tick_data.get('change_percent', 0.0),
                bid=tick_data.get('depth', {}).get('buy', [{}])[0].get('price', 0.0),
                ask=tick_data.get('depth', {}).get('sell', [{}])[0].get('price', 0.0),
                high=tick_data.get('ohlc', {}).get('high', 0.0),
                low=tick_data.get('ohlc', {}).get('low', 0.0),
                open_price=tick_data.get('ohlc', {}).get('open', 0.0)
            )
            
            await self._broadcast_market_data(market_update, 'sharekhan')
        except Exception as e:
            logger.error(f"Error handling ShareKhan tick: {e}")
    
    async def _handle_sharekhan_tick(self, tick_data: Dict):
        """Handle ShareKhan tick data"""
        try:
            # Convert ShareKhan format to unified format
            market_update = MarketDataUpdate(
                symbol=tick_data.get('symbol', ''),
                price=tick_data.get('ltp', 0.0),
                volume=tick_data.get('v', 0),
                timestamp=tick_data.get('timestamp', datetime.now().isoformat()),
                change=tick_data.get('change', 0.0),
                change_percent=tick_data.get('changeper', 0.0),
                bid=tick_data.get('bid', 0.0),
                ask=tick_data.get('ask', 0.0),
                high=tick_data.get('h', 0.0),
                low=tick_data.get('l', 0.0),
                open_price=tick_data.get('o', 0.0)
            )
            
            await self._broadcast_market_data(market_update, 'sharekhan')
        except Exception as e:
            logger.error(f"Error handling ShareKhan tick: {e}")
    
    async def _broadcast_market_data(self, market_update: MarketDataUpdate, provider: str):
        """Broadcast market data to WebSocket clients and store in database"""
        try:
            # Store in Redis for quick access
            redis_key = f"market_data:{market_update.symbol}:latest"
            await self.redis_client.hset(redis_key, mapping={
                'price': market_update.price,
                'volume': market_update.volume,
                'timestamp': market_update.timestamp,
                'provider': provider
            })
            await self.redis_client.expire(redis_key, 3600)  # 1 hour expiry
            
            # Publish to Redis channel for WebSocket broadcast
            await self.redis_client.publish(
                'market_data',
                json.dumps({
                    **market_update.__dict__,
                    'provider': provider
                })
            )
            
            # Store tick data in database (implement database storage)
            # await self._store_tick_data(market_update, provider)
            
        except Exception as e:
            logger.error(f"Error broadcasting market data: {e}") 
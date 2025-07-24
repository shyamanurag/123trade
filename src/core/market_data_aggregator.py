"""
Market Data Aggregator
Unifies data from TrueData and Zerodha and broadcasts via WebSocket
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import redis.asyncio as redis

from ..feeds.truedata_feed import TrueDataFeed
from .zerodha import ZerodhaIntegration
from .websocket_manager import WebSocketManager, MarketDataUpdate

logger = logging.getLogger(__name__)

class MarketDataAggregator:
    """Aggregates market data from multiple sources"""
    
    def __init__(self, 
                 redis_client: redis.Redis,
                 websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.truedata_feed = TrueDataFeed()
        self.zerodha_integration = None
        self.is_running = False
        self.subscribed_symbols = set()
        
    async def initialize(self, zerodha_integration: Optional[ZerodhaIntegration] = None):
        """Initialize the aggregator"""
        try:
            # FIXED: Use existing TrueData cache instead of trying to connect
            # TrueData is already connected and flowing data in the main app
            from data.truedata_client import live_market_data, is_connected
            
            if live_market_data and len(live_market_data) > 0:
                logger.info(f"✅ TrueData cache available: {len(live_market_data)} symbols")
                # Set up cache monitoring instead of direct connection
                self.truedata_feed.cache_data = live_market_data
                self.truedata_feed.connected = True
            else:
                logger.warning("⚠️ TrueData cache is empty - market data not available")
                self.truedata_feed.connected = False
            
            # Initialize Zerodha if provided
            if zerodha_integration:
                self.zerodha_integration = zerodha_integration
                # Set up Zerodha callbacks
                self.zerodha_integration.market_data_callbacks.append(
                    self._handle_zerodha_tick
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
        
        # Start TrueData listener
        asyncio.create_task(self._truedata_listener())
        
        logger.info("Market data aggregator started")
    
    async def stop(self):
        """Stop the aggregator"""
        self.is_running = False
        await self.truedata_feed.disconnect()
        logger.info("Market data aggregator stopped")
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to a symbol across all providers"""
        if symbol in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.add(symbol)
        
        # Subscribe on TrueData
        await self.truedata_feed.subscribe([symbol])
        
        # Subscribe on Zerodha if available
        if self.zerodha_integration:
            await self.zerodha_integration.subscribe_market_data([symbol])
        
        logger.info(f"Subscribed to {symbol} on all providers")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from a symbol"""
        if symbol not in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.remove(symbol)
        
        # Unsubscribe from TrueData
        await self.truedata_feed.unsubscribe([symbol])
        
        # Unsubscribe from Zerodha if available
        if self.zerodha_integration:
            await self.zerodha_integration.unsubscribe_market_data([symbol])
        
        logger.info(f"Unsubscribed from {symbol} on all providers")
    
    async def _truedata_listener(self):
        """Listen for TrueData updates"""
        while self.is_running:
            try:
                if self.truedata_feed.connected:
                    # Process any queued messages
                    # This would be implemented based on TrueData's callback mechanism
                    await asyncio.sleep(0.1)
                else:
                    # Try to reconnect
                    await self.truedata_feed.connect()
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in TrueData listener: {e}")
                await asyncio.sleep(5)
    
    async def _handle_zerodha_tick(self, tick_data: Dict):
        """Handle Zerodha tick data"""
        try:
            # Convert Zerodha format to unified format
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
            
            await self._broadcast_market_data(market_update, 'zerodha')
        except Exception as e:
            logger.error(f"Error handling Zerodha tick: {e}")
    
    async def _handle_truedata_tick(self, tick_data: Dict):
        """Handle TrueData tick data"""
        try:
            # Convert TrueData format to unified format
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
            
            await self._broadcast_market_data(market_update, 'truedata')
        except Exception as e:
            logger.error(f"Error handling TrueData tick: {e}")
    
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
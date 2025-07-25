"""
ShareKhan Market Data Aggregator
Unified market data system replacing TrueData and Zerodha integrations
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from ..feeds.sharekhan_feed import ShareKhanDataFeed, ShareKhanTrueDataCompatibility
from ...brokers.sharekhan import ShareKhanIntegration
from .websocket_manager import WebSocketManager, MarketDataUpdate

logger = logging.getLogger(__name__)

class ShareKhanMarketDataAggregator:
    """
    Unified market data aggregator using only ShareKhan
    Replaces the old TrueData + Zerodha architecture
    """
    
    def __init__(self, 
                 redis_client: redis.Redis,
                 websocket_manager: WebSocketManager,
                 api_key: str,
                 access_token: str):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.api_key = api_key
        self.access_token = access_token
        
        # ShareKhan components
        self.sharekhan_feed = ShareKhanDataFeed(api_key, access_token, redis_client)
        self.sharekhan_integration = None
        
        # Compatibility layer for old TrueData code
        self.truedata_compatibility = ShareKhanTrueDataCompatibility(self.sharekhan_feed)
        
        # Market data state
        self.is_running = False
        self.subscribed_symbols = set()
        self.symbol_callbacks = {}
        self.market_data_cache = {}
        
        # Multi-user support
        self.user_subscriptions = {}  # user_id -> set of symbols
        self.user_permissions = {}    # user_id -> permissions dict
        
        logger.info("ShareKhan market data aggregator initialized")
    
    async def initialize(self, sharekhan_integration: Optional[ShareKhanIntegration] = None):
        """Initialize the aggregator with ShareKhan integration"""
        try:
            # Initialize ShareKhan integration
            if sharekhan_integration:
                self.sharekhan_integration = sharekhan_integration
                logger.info("✅ ShareKhan integration provided")
            
            # Initialize ShareKhan data feed
            symbol_master = await self.sharekhan_feed.load_symbol_master()
            if symbol_master:
                logger.info(f"✅ Loaded {len(symbol_master)} instruments from ShareKhan")
            
            # Connect to ShareKhan WebSocket
            connected = await self.sharekhan_feed.connect()
            if connected:
                logger.info("✅ ShareKhan WebSocket connected")
            else:
                logger.warning("⚠️ ShareKhan WebSocket connection failed")
            
            # Set up data callbacks
            self.sharekhan_feed.add_data_callback(self._handle_market_data)
            self.sharekhan_feed.add_error_callback(self._handle_error)
            
            # Cache connection status
            await self._update_connection_status()
            
            logger.info("✅ ShareKhan market data aggregator initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ShareKhan aggregator: {e}")
            raise
    
    async def start(self):
        """Start the aggregator"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background tasks
        asyncio.create_task(self._market_data_monitor())
        asyncio.create_task(self._cache_cleanup_task())
        asyncio.create_task(self._connection_health_monitor())
        
        logger.info("✅ ShareKhan market data aggregator started")
    
    async def stop(self):
        """Stop the aggregator"""
        self.is_running = False
        
        # Disconnect from ShareKhan
        await self.sharekhan_feed.disconnect()
        
        # Clear caches
        self.market_data_cache.clear()
        self.subscribed_symbols.clear()
        self.user_subscriptions.clear()
        
        logger.info("✅ ShareKhan market data aggregator stopped")
    
    # SUBSCRIPTION MANAGEMENT
    
    async def subscribe_symbol(self, symbol: str, user_id: str = None):
        """Subscribe to a symbol for a specific user or system-wide"""
        try:
            if symbol in self.subscribed_symbols:
                logger.debug(f"Symbol {symbol} already subscribed")
                
                # Add to user subscriptions
                if user_id:
                    if user_id not in self.user_subscriptions:
                        self.user_subscriptions[user_id] = set()
                    self.user_subscriptions[user_id].add(symbol)
                
                return True
            
            # Subscribe via ShareKhan feed
            success = await self.sharekhan_feed.subscribe_symbols([symbol])
            
            if success:
                self.subscribed_symbols.add(symbol)
                
                # Add to user subscriptions
                if user_id:
                    if user_id not in self.user_subscriptions:
                        self.user_subscriptions[user_id] = set()
                    self.user_subscriptions[user_id].add(symbol)
                
                logger.info(f"✅ Subscribed to {symbol} for user: {user_id or 'system'}")
                return True
            else:
                logger.error(f"Failed to subscribe to {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {e}")
            return False
    
    async def unsubscribe_symbol(self, symbol: str, user_id: str = None):
        """Unsubscribe from a symbol"""
        try:
            # Remove from user subscriptions
            if user_id and user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].discard(symbol)
                
                # Check if other users are still subscribed
                still_needed = any(
                    symbol in user_symbols 
                    for user_symbols in self.user_subscriptions.values()
                )
                
                if still_needed:
                    logger.debug(f"Symbol {symbol} still needed by other users")
                    return True
            
            # If no user_id specified or no other users need it, unsubscribe
            if symbol not in self.subscribed_symbols:
                return True
            
            success = await self.sharekhan_feed.unsubscribe_symbols([symbol])
            
            if success:
                self.subscribed_symbols.discard(symbol)
                self.market_data_cache.pop(symbol, None)
                
                logger.info(f"✅ Unsubscribed from {symbol}")
                return True
            else:
                logger.error(f"Failed to unsubscribe from {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from {symbol}: {e}")
            return False
    
    async def subscribe_user_symbols(self, user_id: str, symbols: List[str]) -> Dict[str, bool]:
        """Subscribe to multiple symbols for a user"""
        results = {}
        
        for symbol in symbols:
            results[symbol] = await self.subscribe_symbol(symbol, user_id)
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"✅ Subscribed user {user_id} to {successful}/{len(symbols)} symbols")
        
        return results
    
    async def unsubscribe_user_symbols(self, user_id: str, symbols: List[str] = None) -> bool:
        """Unsubscribe user from symbols (or all if symbols=None)"""
        try:
            if symbols is None:
                # Unsubscribe from all user symbols
                symbols = list(self.user_subscriptions.get(user_id, set()))
            
            for symbol in symbols:
                await self.unsubscribe_symbol(symbol, user_id)
            
            # Clean up user subscription record
            if user_id in self.user_subscriptions:
                if symbols is None:
                    del self.user_subscriptions[user_id]
                else:
                    for symbol in symbols:
                        self.user_subscriptions[user_id].discard(symbol)
            
            logger.info(f"✅ Unsubscribed user {user_id} from {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing user {user_id}: {e}")
            return False
    
    # DATA HANDLING
    
    async def _handle_market_data(self, symbol: str, tick_data: Dict[str, Any]):
        """Handle incoming market data from ShareKhan"""
        try:
            # Update local cache
            self.market_data_cache[symbol] = {
                **tick_data,
                "last_updated": datetime.now(),
                "source": "sharekhan"
            }
            
            # Cache in Redis with expiry
            if self.redis_client:
                try:
                    cache_key = f"market_data:live:{symbol}"
                    await self.redis_client.setex(
                        cache_key,
                        300,  # 5 minutes
                        json.dumps(tick_data, default=str)
                    )
                except Exception as e:
                    logger.debug(f"Redis cache update failed for {symbol}: {e}")
            
            # Create market data update for WebSocket
            market_update = MarketDataUpdate(
                symbol=symbol,
                price=tick_data.get("ltp", 0),
                volume=tick_data.get("volume", 0),
                timestamp=tick_data.get("timestamp", datetime.now()),
                bid=tick_data.get("bid", 0),
                ask=tick_data.get("ask", 0),
                open=tick_data.get("open", 0),
                high=tick_data.get("high", 0),
                low=tick_data.get("low", 0),
                close=tick_data.get("close", 0)
            )
            
            # Broadcast via WebSocket
            await self.websocket_manager.broadcast_market_data(market_update)
            
            # Call symbol-specific callbacks
            if symbol in self.symbol_callbacks:
                for callback in self.symbol_callbacks[symbol]:
                    try:
                        await callback(symbol, tick_data)
                    except Exception as e:
                        logger.error(f"Symbol callback error for {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling market data for {symbol}: {e}")
    
    async def _handle_error(self, error_data: Dict[str, Any]):
        """Handle errors from ShareKhan feed"""
        try:
            error_msg = error_data.get("error", "Unknown error")
            logger.error(f"ShareKhan feed error: {error_msg}")
            
            # Broadcast error via WebSocket
            await self.websocket_manager.broadcast_error({
                "source": "sharekhan_feed",
                "error": error_msg,
                "timestamp": datetime.now(),
                "data": error_data
            })
            
        except Exception as e:
            logger.error(f"Error handling ShareKhan error: {e}")
    
    # DATA RETRIEVAL
    
    async def get_live_data(self, symbol: str = None) -> Dict[str, Any]:
        """Get live market data"""
        try:
            if symbol:
                # Get specific symbol
                if symbol in self.market_data_cache:
                    return self.market_data_cache[symbol]
                
                # Try ShareKhan feed
                return await self.sharekhan_feed.get_live_data(symbol)
            else:
                # Return all cached data
                return self.market_data_cache.copy()
                
        except Exception as e:
            logger.error(f"Error getting live data for {symbol}: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, interval: str, 
                                  from_date: datetime = None, to_date: datetime = None) -> List[Dict[str, Any]]:
        """Get historical OHLCV data"""
        try:
            return await self.sharekhan_feed.get_historical_data(symbol, interval, from_date, to_date)
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def get_market_depth(self, symbol: str) -> Dict[str, Any]:
        """Get market depth data"""
        try:
            return self.sharekhan_feed.get_market_depth(symbol)
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {e}")
            return {}
    
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get market data for user's subscribed symbols"""
        try:
            user_symbols = self.user_subscriptions.get(user_id, set())
            user_data = {}
            
            for symbol in user_symbols:
                if symbol in self.market_data_cache:
                    user_data[symbol] = self.market_data_cache[symbol]
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data for {user_id}: {e}")
            return {}
    
    # CALLBACK MANAGEMENT
    
    def add_symbol_callback(self, symbol: str, callback: Callable):
        """Add callback for specific symbol updates"""
        if symbol not in self.symbol_callbacks:
            self.symbol_callbacks[symbol] = []
        self.symbol_callbacks[symbol].append(callback)
    
    def remove_symbol_callback(self, symbol: str, callback: Callable):
        """Remove symbol callback"""
        if symbol in self.symbol_callbacks:
            try:
                self.symbol_callbacks[symbol].remove(callback)
                if not self.symbol_callbacks[symbol]:
                    del self.symbol_callbacks[symbol]
            except ValueError:
                pass
    
    # BACKGROUND TASKS
    
    async def _market_data_monitor(self):
        """Monitor market data flow and health"""
        while self.is_running:
            try:
                # Check data freshness
                stale_symbols = []
                current_time = datetime.now()
                
                for symbol, data in self.market_data_cache.items():
                    last_updated = data.get("last_updated")
                    if last_updated and isinstance(last_updated, datetime):
                        if (current_time - last_updated).seconds > 300:  # 5 minutes
                            stale_symbols.append(symbol)
                
                if stale_symbols:
                    logger.warning(f"Stale data detected for {len(stale_symbols)} symbols")
                
                # Update monitoring metrics
                await self._update_monitoring_metrics()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Market data monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _cache_cleanup_task(self):
        """Clean up old cache entries"""
        while self.is_running:
            try:
                current_time = datetime.now()
                cleanup_threshold = timedelta(hours=1)
                
                # Clean local cache
                symbols_to_remove = []
                for symbol, data in self.market_data_cache.items():
                    last_updated = data.get("last_updated")
                    if last_updated and isinstance(last_updated, datetime):
                        if current_time - last_updated > cleanup_threshold:
                            symbols_to_remove.append(symbol)
                
                for symbol in symbols_to_remove:
                    del self.market_data_cache[symbol]
                
                if symbols_to_remove:
                    logger.info(f"Cleaned up {len(symbols_to_remove)} stale cache entries")
                
                await asyncio.sleep(3600)  # Clean every hour
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(3600)
    
    async def _connection_health_monitor(self):
        """Monitor ShareKhan connection health"""
        while self.is_running:
            try:
                health_status = await self.sharekhan_feed.health_check()
                
                # Update connection status in Redis
                if self.redis_client:
                    try:
                        await self.redis_client.setex(
                            "sharekhan:health",
                            300,
                            json.dumps(health_status, default=str)
                        )
                    except Exception:
                        pass
                
                # Log health issues
                if health_status.get("status") != "healthy":
                    logger.warning(f"ShareKhan health check: {health_status}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _update_connection_status(self):
        """Update connection status in Redis"""
        try:
            status = {
                "connected": self.sharekhan_feed.is_connected,
                "subscribed_symbols": len(self.subscribed_symbols),
                "active_users": len(self.user_subscriptions),
                "last_updated": datetime.now(),
                "source": "sharekhan"
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    "market_data:connection_status",
                    300,
                    json.dumps(status, default=str)
                )
            
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
    
    async def _update_monitoring_metrics(self):
        """Update monitoring metrics"""
        try:
            metrics = {
                "subscribed_symbols": len(self.subscribed_symbols),
                "cached_symbols": len(self.market_data_cache),
                "active_users": len(self.user_subscriptions),
                "total_user_subscriptions": sum(
                    len(symbols) for symbols in self.user_subscriptions.values()
                ),
                "connection_status": self.sharekhan_feed.get_connection_status(),
                "timestamp": datetime.now()
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    "market_data:metrics",
                    300,
                    json.dumps(metrics, default=str)
                )
            
        except Exception as e:
            logger.error(f"Error updating monitoring metrics: {e}")
    
    # COMPATIBILITY METHODS (for migration from old system)
    
    @property
    def truedata_feed(self):
        """Compatibility property for old TrueData references"""
        return self.truedata_compatibility
    
    @property
    def zerodha_integration(self):
        """Compatibility property for old Zerodha references"""
        return self.sharekhan_integration
    
    async def get_truedata_cache(self) -> Dict[str, Any]:
        """Compatibility method for TrueData cache access"""
        return await self.get_live_data()
    
    # STATUS AND UTILITY
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get comprehensive connection status"""
        return {
            "sharekhan_feed": self.sharekhan_feed.get_connection_status(),
            "aggregator": {
                "running": self.is_running,
                "subscribed_symbols": len(self.subscribed_symbols),
                "cached_symbols": len(self.market_data_cache),
                "active_users": len(self.user_subscriptions)
            },
            "integration": {
                "api_connected": bool(self.sharekhan_integration and self.sharekhan_integration.access_token),
                "websocket_connected": self.sharekhan_feed.is_connected
            }
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        try:
            return {
                "status": "running" if self.is_running else "stopped",
                "connections": self.get_connection_status(),
                "subscriptions": {
                    "total_symbols": len(self.subscribed_symbols),
                    "user_subscriptions": {
                        user_id: len(symbols) 
                        for user_id, symbols in self.user_subscriptions.items()
                    }
                },
                "data_health": {
                    "cached_symbols": len(self.market_data_cache),
                    "latest_update": max(
                        (data.get("last_updated", datetime.min) 
                         for data in self.market_data_cache.values()
                         if isinstance(data.get("last_updated"), datetime)),
                        default=None
                    )
                },
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now()
            } 
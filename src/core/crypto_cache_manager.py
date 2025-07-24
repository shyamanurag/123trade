# core/crypto_cache_manager.py
"""
Enhanced Crypto Cache Manager
Handles Redis caching for crypto market data with advanced features
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import redis.asyncio as aioredis
import hashlib

from ..models.trading_models import CryptoMarketData, CryptoSymbol, CryptoSignal

logger = logging.getLogger(__name__)

class CryptoCacheManager:
    """
    Advanced Redis cache manager specifically designed for crypto trading data
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        self.redis_url = redis_url
        self.db = db
        self.redis_client = None
        
        # Cache key prefixes
        self.PREFIXES = {
            'market_data': 'crypto:market_data',
            'tick_data': 'crypto:tick_data',
            'symbols': 'crypto:symbols',
            'signals': 'crypto:signals',
            'order_book': 'crypto:order_book',
            'volume_profile': 'crypto:volume_profile',
            'whale_activity': 'crypto:whale_activity',
            'social_sentiment': 'crypto:social_sentiment',
            'portfolio': 'crypto:portfolio',
            'risk_metrics': 'crypto:risk_metrics'
        }
        
        # Default TTL (Time To Live) in seconds
        self.TTL = {
            'market_data': 300,      # 5 minutes
            'tick_data': 60,         # 1 minute
            'symbols': 3600,         # 1 hour
            'signals': 1800,         # 30 minutes
            'order_book': 30,        # 30 seconds
            'volume_profile': 600,   # 10 minutes
            'whale_activity': 300,   # 5 minutes
            'social_sentiment': 900, # 15 minutes
            'portfolio': 60,         # 1 minute
            'risk_metrics': 300      # 5 minutes
        }
    
    async def start(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=True,
                retry_on_timeout=True,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Crypto Cache Manager connected to Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def stop(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def _make_key(self, prefix: str, *args) -> str:
        """Create Redis key with consistent naming"""
        key_parts = [self.PREFIXES[prefix]] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def _serialize_decimal(self, obj):
        """Custom JSON serializer for Decimal objects"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    # =============================================================================
    # MARKET DATA CACHING
    # =============================================================================
    
    async def cache_market_data(self, symbol: str, market_data: CryptoMarketData):
        """Cache market data for a symbol"""
        try:
            key = self._make_key('market_data', symbol)
            data = json.dumps(market_data.to_dict(), default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key, 
                self.TTL['market_data'], 
                data
            )
            
            # Also cache in sorted set for time-series queries
            timestamp_key = self._make_key('market_data', symbol, 'timeseries')
            score = market_data.timestamp.timestamp()
            
            await self.redis_client.zadd(
                timestamp_key, 
                {data: score}
            )
            
            # Cleanup old entries (keep last 1000)
            await self.redis_client.zremrangebyrank(timestamp_key, 0, -1001)
            
            logger.debug(f"Cached market data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error caching market data for {symbol}: {e}")
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get latest market data for a symbol"""
        try:
            key = self._make_key('market_data', symbol)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_market_data_series(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get time series of market data"""
        try:
            key = self._make_key('market_data', symbol, 'timeseries')
            
            # Get latest entries
            data_list = await self.redis_client.zrevrange(key, 0, limit - 1)
            
            return [json.loads(item) for item in data_list]
            
        except Exception as e:
            logger.error(f"Error getting market data series for {symbol}: {e}")
            return []
    
    # =============================================================================
    # SYMBOL METADATA CACHING
    # =============================================================================
    
    async def cache_symbol_info(self, symbol_info: CryptoSymbol):
        """Cache symbol information"""
        try:
            key = self._make_key('symbols', symbol_info.symbol)
            data = json.dumps(symbol_info.to_dict(), default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['symbols'],
                data
            )
            
            # Cache in hash for quick lookups
            symbols_hash = self._make_key('symbols', 'all')
            await self.redis_client.hset(
                symbols_hash,
                symbol_info.symbol,
                data
            )
            
            logger.debug(f"Cached symbol info for {symbol_info.symbol}")
            
        except Exception as e:
            logger.error(f"Error caching symbol info: {e}")
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        try:
            key = self._make_key('symbols', symbol)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    async def get_all_symbols(self) -> List[Dict]:
        """Get all cached symbols"""
        try:
            symbols_hash = self._make_key('symbols', 'all')
            symbols_data = await self.redis_client.hgetall(symbols_hash)
            
            return [json.loads(data) for data in symbols_data.values()]
            
        except Exception as e:
            logger.error(f"Error getting all symbols: {e}")
            return []
    
    # =============================================================================
    # TRADING SIGNALS CACHING
    # =============================================================================
    
    async def cache_signal(self, signal: CryptoSignal):
        """Cache trading signal"""
        try:
            # Individual signal cache
            key = self._make_key('signals', signal.symbol, signal.signal_id)
            data = json.dumps(signal.to_dict(), default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['signals'],
                data
            )
            
            # Add to symbol's signals list
            signals_list_key = self._make_key('signals', signal.symbol, 'list')
            score = signal.timestamp.timestamp()
            
            await self.redis_client.zadd(
                signals_list_key,
                {signal.signal_id: score}
            )
            
            # Keep only last 50 signals per symbol
            await self.redis_client.zremrangebyrank(signals_list_key, 0, -51)
            
            logger.debug(f"Cached signal {signal.signal_id} for {signal.symbol}")
            
        except Exception as e:
            logger.error(f"Error caching signal: {e}")
    
    async def get_signals(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get latest signals for a symbol"""
        try:
            signals_list_key = self._make_key('signals', symbol, 'list')
            signal_ids = await self.redis_client.zrevrange(signals_list_key, 0, limit - 1)
            
            signals = []
            for signal_id in signal_ids:
                signal_key = self._make_key('signals', symbol, signal_id)
                signal_data = await self.redis_client.get(signal_key)
                
                if signal_data:
                    signals.append(json.loads(signal_data))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting signals for {symbol}: {e}")
            return []
    
    # =============================================================================
    # ORDER BOOK CACHING
    # =============================================================================
    
    async def cache_order_book(self, symbol: str, order_book: Dict):
        """Cache order book data"""
        try:
            key = self._make_key('order_book', symbol)
            data = json.dumps(order_book, default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['order_book'],
                data
            )
            
            logger.debug(f"Cached order book for {symbol}")
            
        except Exception as e:
            logger.error(f"Error caching order book for {symbol}: {e}")
    
    async def get_order_book(self, symbol: str) -> Optional[Dict]:
        """Get order book data"""
        try:
            key = self._make_key('order_book', symbol)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return None
    
    # =============================================================================
    # PORTFOLIO CACHING
    # =============================================================================
    
    async def cache_portfolio(self, user_id: str, portfolio: Dict):
        """Cache user portfolio data"""
        try:
            key = self._make_key('portfolio', user_id)
            data = json.dumps(portfolio, default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['portfolio'],
                data
            )
            
            logger.debug(f"Cached portfolio for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error caching portfolio for user {user_id}: {e}")
    
    async def get_portfolio(self, user_id: str) -> Optional[Dict]:
        """Get user portfolio data"""
        try:
            key = self._make_key('portfolio', user_id)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting portfolio for user {user_id}: {e}")
            return None
    
    # =============================================================================
    # WHALE ACTIVITY CACHING
    # =============================================================================
    
    async def cache_whale_activity(self, symbol: str, whale_data: Dict):
        """Cache whale activity data"""
        try:
            key = self._make_key('whale_activity', symbol)
            data = json.dumps(whale_data, default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['whale_activity'],
                data
            )
            
            # Add to whale activity timeline
            timeline_key = self._make_key('whale_activity', 'timeline')
            score = datetime.now().timestamp()
            
            await self.redis_client.zadd(
                timeline_key,
                {f"{symbol}:{score}": score}
            )
            
            # Keep last 1000 whale activities
            await self.redis_client.zremrangebyrank(timeline_key, 0, -1001)
            
            logger.debug(f"Cached whale activity for {symbol}")
            
        except Exception as e:
            logger.error(f"Error caching whale activity for {symbol}: {e}")
    
    async def get_whale_activity(self, symbol: str = None) -> Union[Dict, List[Dict]]:
        """Get whale activity data"""
        try:
            if symbol:
                # Get specific symbol whale activity
                key = self._make_key('whale_activity', symbol)
                data = await self.redis_client.get(key)
                
                if data:
                    return json.loads(data)
                return None
            else:
                # Get recent whale activities across all symbols
                timeline_key = self._make_key('whale_activity', 'timeline')
                recent_activities = await self.redis_client.zrevrange(timeline_key, 0, 19)
                
                activities = []
                for activity_key in recent_activities:
                    symbol_name = activity_key.split(':')[0]
                    whale_key = self._make_key('whale_activity', symbol_name)
                    data = await self.redis_client.get(whale_key)
                    
                    if data:
                        activity = json.loads(data)
                        activity['symbol'] = symbol_name
                        activities.append(activity)
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting whale activity: {e}")
            return [] if not symbol else None
    
    # =============================================================================
    # SOCIAL SENTIMENT CACHING
    # =============================================================================
    
    async def cache_social_sentiment(self, symbol: str, sentiment_data: Dict):
        """Cache social sentiment data"""
        try:
            key = self._make_key('social_sentiment', symbol)
            data = json.dumps(sentiment_data, default=self._serialize_decimal)
            
            await self.redis_client.setex(
                key,
                self.TTL['social_sentiment'],
                data
            )
            
            logger.debug(f"Cached social sentiment for {symbol}")
            
        except Exception as e:
            logger.error(f"Error caching social sentiment for {symbol}: {e}")
    
    async def get_social_sentiment(self, symbol: str) -> Optional[Dict]:
        """Get social sentiment data"""
        try:
            key = self._make_key('social_sentiment', symbol)
            data = await self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting social sentiment for {symbol}: {e}")
            return None
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def clear_cache(self, pattern: str = None):
        """Clear cache by pattern or all crypto cache"""
        try:
            if pattern:
                # Clear specific pattern
                keys = await self.redis_client.keys(f"crypto:*{pattern}*")
            else:
                # Clear all crypto cache
                keys = await self.redis_client.keys("crypto:*")
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            info = await self.redis_client.info()
            
            # Count keys by prefix
            key_counts = {}
            for prefix in self.PREFIXES.values():
                keys = await self.redis_client.keys(f"{prefix}:*")
                key_counts[prefix] = len(keys)
            
            return {
                'redis_info': {
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'total_commands_processed': info.get('total_commands_processed')
                },
                'key_counts': key_counts,
                'total_crypto_keys': sum(key_counts.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    async def health_check(self) -> Dict:
        """Check cache health"""
        try:
            start_time = datetime.now()
            
            # Test basic operations
            test_key = "crypto:health_check"
            await self.redis_client.set(test_key, "test_value", ex=10)
            value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy' if value == 'test_value' else 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Singleton instance
_cache_manager = None

async def get_cache_manager() -> CryptoCacheManager:
    """Get singleton cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CryptoCacheManager()
        await _cache_manager.start()
    return _cache_manager 
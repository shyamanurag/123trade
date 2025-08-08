"""
Signal Deduplication and Quality Filtering System
=================================================
Prevents multiple signals for the same symbol at the same timestamp
Implements signal quality scoring and filtering
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

class SignalDeduplicator:
    """Handles signal deduplication and quality filtering"""
    
    def __init__(self):
        self.recent_signals = defaultdict(list)  # symbol -> list of recent signals
        self.signal_history = {}  # signal_id -> signal data
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.now()
        
        # Quality thresholds - BALANCED FOR PRODUCTION TRADING
        self.min_confidence_threshold = 0.65  # Slightly lowered to capture 0.65 confidence signals
        self.max_signals_per_symbol = 2  # Allow 2 signals per symbol per period 
        self.deduplication_window = 30  # Reduced to 30 seconds window

        # 🚨 CRITICAL FIX: Redis persistence for executed signals across deploys
        self.redis_client = None
        self._init_redis_connection()
        
        # 🚨 DEPLOYMENT CACHE CLEARING: Clear old signals after deployment
        # Don't create async task during init - will be called manually when event loop is ready
        self._startup_cleanup_pending = True

    async def _clear_signal_cache_on_startup(self):
        """Clear deployment cache on startup to prevent duplicate signals"""
        try:
            # Wait a bit for Redis connection to be ready
            await asyncio.sleep(2)
            
            if not self.redis_client:
                logger.warning("⚠️ No Redis client - cannot clear deployment cache")
                return
            
            # Check if this is a fresh deployment (no cache clearing in last 5 minutes)
            cache_clear_key = "last_cache_clear"
            last_clear = await self.redis_client.get(cache_clear_key)
            
            if last_clear:
                import time
                time_since_clear = time.time() - float(last_clear)
                if time_since_clear < 300:  # 5 minutes
                    logger.info(f"⏭️ Skipping cache clear - last cleared {time_since_clear:.0f}s ago")
                    return
            
            logger.info("🧹 DEPLOYMENT STARTUP: Clearing signal execution cache (preserving order tracking)")
            
            # Clear ONLY executed signals deduplication cache for today
            today = datetime.now().strftime('%Y-%m-%d')
            pattern = f"executed_signals:{today}:*"
            
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"✅ Cleared {deleted} signal execution cache entries (not order tracking)")
                logger.info("🔒 Order tracking & position data preserved for square-off trades")
            else:
                logger.info("ℹ️ No signal execution cache found - clean slate confirmed")
            
            # Mark cache as cleared
            import time
            await self.redis_client.set(cache_clear_key, str(time.time()), ex=3600)  # 1 hour expiry
            
            logger.info("🚀 Signal processing cache cleared - ready for fresh signals")
            
        except Exception as e:
            logger.error(f"❌ Error clearing deployment cache: {e}")

    async def ensure_startup_cleanup(self):
        """Ensure startup cleanup is run when event loop is available"""
        if getattr(self, '_startup_cleanup_pending', False):
            self._startup_cleanup_pending = False
            await self._clear_signal_cache_on_startup()

    async def clear_all_executed_signals(self):
        """Clear all executed signals cache - can be called manually"""
        try:
            if not self.redis_client:
                logger.error("❌ No Redis client available")
                return 0
            
            # Clear executed signals for last 3 days
            total_cleared = 0
            for days_back in range(3):
                date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                pattern = f"executed_signals:{date}:*"
                
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted = await self.redis_client.delete(*keys)
                    total_cleared += deleted
                    logger.info(f"🧹 Cleared {deleted} executed signals for {date}")
            
            logger.info(f"✅ Total executed signals cleared: {total_cleared}")
            return total_cleared
            
        except Exception as e:
            logger.error(f"❌ Error clearing executed signals: {e}")
            return 0
        
    def _init_redis_connection(self):
        """Initialize Redis connection for persistent signal tracking"""
        try:
            import redis.asyncio as redis
            import os
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=True,
                    ssl_cert_reqs=None,
                    ssl_check_hostname=False
                )
                logger.info("✅ Signal deduplicator Redis connection initialized")
                logger.info(f"🔗 Redis URL configured: {redis_url[:20]}...")  # Log first 20 chars for debugging
            else:
                logger.warning("⚠️ No REDIS_URL - signal deduplication will be memory-only")
                logger.warning("🚨 CRITICAL: Without Redis, duplicate signals across deployments CANNOT be prevented!")
        except Exception as e:
            logger.error(f"❌ Failed to init Redis for signal deduplication: {e}")
            logger.error("🚨 CRITICAL: Redis connection failed - duplicate execution protection disabled!")
        
    async def _check_signal_already_executed(self, signal: Dict) -> bool:
        """Check if this signal was already executed today (across deploys)"""
        try:
            # 🎯 BYPASS DEDUPLICATION FOR POSITION MANAGEMENT ACTIONS
            is_management_action = signal.get('management_action', False)
            is_closing_action = signal.get('closing_action', False)
            
            if is_management_action or is_closing_action:
                logger.info(f"🎯 MANAGEMENT ACTION BYPASS: {signal.get('symbol')} {signal.get('action')} - skipping duplicate check")
                return False
            
            if not self.redis_client:
                logger.warning(f"🚨 NO REDIS CLIENT: Cannot check for duplicate signal {signal.get('symbol')} - allowing execution")
                return False
                
            symbol = signal.get('symbol')
            action = signal.get('action', 'BUY')
            
            # Check if signal was executed in last 24 hours
            today = datetime.now().strftime('%Y-%m-%d')
            executed_key = f"executed_signals:{today}:{symbol}:{action}"
            
            logger.info(f"🔍 CHECKING DUPLICATE: {executed_key}")
            executed_count = await self.redis_client.get(executed_key)
            
            if executed_count and int(executed_count) > 0:
                logger.warning(f"🚫 DUPLICATE SIGNAL BLOCKED: {symbol} {action} already executed {executed_count} times today")
                logger.warning(f"🔑 Redis key: {executed_key}")
                return True
            else:
                logger.info(f"✅ SIGNAL ALLOWED: {symbol} {action} - no previous executions found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking executed signals in Redis: {e}")
            logger.error(f"🚨 REDIS CHECK FAILED for {signal.get('symbol')} - ALLOWING execution (risky)")
            return False
    
    async def mark_signal_executed(self, signal: Dict):
        """Mark signal as executed to prevent future duplicates"""
        try:
            if not self.redis_client:
                logger.error(f"🚨 NO REDIS CLIENT: Cannot mark signal {signal.get('symbol')} as executed - DUPLICATE RISK!")
                return
                
            symbol = signal.get('symbol')
            action = signal.get('action', 'BUY')
            
            # Increment execution count for today
            today = datetime.now().strftime('%Y-%m-%d')
            executed_key = f"executed_signals:{today}:{symbol}:{action}"
            
            logger.info(f"📝 MARKING AS EXECUTED: {executed_key}")
            current_count = await self.redis_client.incr(executed_key)
            await self.redis_client.expire(executed_key, 86400)  # 24 hours
            
            logger.info(f"✅ Marked signal as executed: {symbol} {action} (count: {current_count})")
            
            if current_count > 1:
                logger.warning(f"⚠️ MULTIPLE EXECUTIONS DETECTED: {symbol} {action} now executed {current_count} times today!")
            
        except Exception as e:
            logger.error(f"❌ Error marking signal as executed in Redis: {e}")
            logger.error(f"🚨 FAILED TO MARK {signal.get('symbol')} as executed - FUTURE DUPLICATES POSSIBLE!")
    
    async def process_signals(self, signals: List[Dict]) -> List[Dict]:
        """Process and deduplicate signals, return only high-quality unique signals"""
        if not signals:
            return []
        
        # 🚨 CRITICAL FIX: Check for already executed signals first
        filtered_signals = []
        for signal in signals:
            if await self._check_signal_already_executed(signal):
                continue  # Skip this signal - already executed
            filtered_signals.append(signal)
        
        if len(filtered_signals) < len(signals):
            logger.info(f"🚫 BLOCKED {len(signals) - len(filtered_signals)} duplicate signals from previous executions")
        
        # Continue with normal processing
        signals = filtered_signals
        
        # Clean up old signals periodically
        self._cleanup_old_signals()
        
        # Filter by quality first
        quality_signals = self._filter_by_quality(signals)
        
        # Deduplicate by symbol
        deduplicated_signals = self._deduplicate_by_symbol(quality_signals)
        
        # Check for timestamp collisions and resolve
        final_signals = self._resolve_timestamp_collisions(deduplicated_signals)
        
        # Update signal history
        self._update_signal_history(final_signals)
        
        logger.info(f"📊 Signal Processing: {len(signals)} → {len(quality_signals)} → {len(final_signals)}")
        
        return final_signals
    
    def _filter_by_quality(self, signals: List[Dict]) -> List[Dict]:
        """Filter signals by quality thresholds"""
        quality_signals = []
        rejection_stats = {
            'low_confidence': 0,
            'missing_fields': 0,
            'invalid_prices': 0,
            'poor_risk_reward': 0
        }
        
        for signal in signals:
            # 🎯 BYPASS QUALITY FILTERING FOR POSITION MANAGEMENT ACTIONS
            is_management_action = signal.get('management_action', False)
            is_closing_action = signal.get('closing_action', False)
            
            if is_management_action or is_closing_action:
                logger.info(f"🎯 QUALITY BYPASS: {signal.get('symbol')} {signal.get('action')} - management action approved")
                quality_signals.append(signal)
                continue
            
            confidence = signal.get('confidence', 0)
            
            # Check minimum confidence
            if confidence < self.min_confidence_threshold:
                rejection_stats['low_confidence'] += 1
                logger.debug(f"❌ Signal rejected - low confidence: {signal['symbol']} ({confidence:.2f} < {self.min_confidence_threshold})")
                continue
            
            # Check for required fields
            required_fields = ['symbol', 'action', 'entry_price', 'stop_loss', 'target']
            if not all(field in signal for field in required_fields):
                rejection_stats['missing_fields'] += 1
                logger.debug(f"❌ Signal rejected - missing fields: {signal.get('symbol', 'UNKNOWN')}")
                continue
            
            # Check for reasonable price levels
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            target = signal.get('target', 0)
            
            if not all([entry_price > 0, stop_loss > 0, target > 0]):
                rejection_stats['invalid_prices'] += 1
                logger.debug(f"❌ Signal rejected - invalid prices: {signal['symbol']}")
                continue
            
            # Check risk-reward ratio
            if signal['action'] == 'BUY':
                risk = entry_price - stop_loss
                reward = target - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - target
            
            if risk <= 0 or reward <= 0:
                rejection_stats['invalid_prices'] += 1
                logger.debug(f"❌ Signal rejected - invalid risk/reward: {signal['symbol']}")
                continue
            
            risk_reward_ratio = reward / risk
            if risk_reward_ratio < 1.5:  # ADJUSTED: Minimum 1.5:1 profit-to-loss ratio for current market
                rejection_stats['poor_risk_reward'] += 1
                logger.debug(f"❌ Signal rejected - poor risk/reward: {signal['symbol']} ({risk_reward_ratio:.2f} < 1.5)")
                continue
            
            quality_signals.append(signal)
        
        # Log summary of rejections
        if any(rejection_stats.values()):
            logger.info(f"📊 Quality Filter Results: {len(quality_signals)} passed, {sum(rejection_stats.values())} rejected")
            for reason, count in rejection_stats.items():
                if count > 0:
                    logger.info(f"   - {reason}: {count} signals")
        
        return quality_signals
    
    def _deduplicate_by_symbol(self, signals: List[Dict]) -> List[Dict]:
        """Remove duplicate signals for the same symbol, keep highest confidence"""
        symbol_signals = defaultdict(list)
        management_signals = []  # Management actions bypass symbol deduplication
        
        # Separate management actions from regular signals
        for signal in signals:
            is_management_action = signal.get('management_action', False)
            is_closing_action = signal.get('closing_action', False)
            
            if is_management_action or is_closing_action:
                logger.info(f"🎯 SYMBOL DEDUP BYPASS: {signal.get('symbol')} {signal.get('action')} - management action")
                management_signals.append(signal)
            else:
                symbol = signal['symbol']
                symbol_signals[symbol].append(signal)
        
        deduplicated = []
        
        for symbol, symbol_signal_list in symbol_signals.items():
            # Check if we already have recent signals for this symbol
            recent_count = len([s for s in self.recent_signals[symbol] 
                              if (datetime.now() - s['timestamp']).total_seconds() < self.deduplication_window])
            
            if recent_count >= self.max_signals_per_symbol:
                logger.debug(f"❌ Signal rejected - too many recent signals: {symbol}")
                continue
            
            # If multiple signals for same symbol, keep the highest confidence
            if len(symbol_signal_list) > 1:
                best_signal = max(symbol_signal_list, key=lambda s: s.get('confidence', 0))
                logger.info(f"🔄 Deduplication: {symbol} - kept best of {len(symbol_signal_list)} signals")
                deduplicated.append(best_signal)
            else:
                deduplicated.append(symbol_signal_list[0])
        
        # Add all management signals (no deduplication)
        deduplicated.extend(management_signals)
        
        return deduplicated
    
    def _resolve_timestamp_collisions(self, signals: List[Dict]) -> List[Dict]:
        """Resolve timestamp collisions by adding microsecond precision and random suffix"""
        resolved_signals = []
        
        for i, signal in enumerate(signals):
            # Generate unique signal ID with microsecond precision
            timestamp = datetime.now()
            unique_id = f"{signal['symbol']}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{i:03d}"
            
            # Add unique identifiers
            signal['signal_id'] = unique_id
            signal['generated_at'] = timestamp
            signal['deduplication_rank'] = i + 1
            
            resolved_signals.append(signal)
        
        return resolved_signals
    
    def _update_signal_history(self, signals: List[Dict]):
        """Update signal history and recent signals tracking"""
        for signal in signals:
            symbol = signal['symbol']
            signal_id = signal['signal_id']
            
            # Add to signal history
            self.signal_history[signal_id] = signal
            
            # Add to recent signals for this symbol
            self.recent_signals[symbol].append({
                'signal_id': signal_id,
                'timestamp': signal['generated_at'],
                'confidence': signal['confidence']
            })
    
    def _cleanup_old_signals(self):
        """Clean up old signals from memory"""
        if (datetime.now() - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        cutoff_time = datetime.now() - timedelta(seconds=self.cleanup_interval)
        
        # Clean up recent signals
        for symbol in list(self.recent_signals.keys()):
            self.recent_signals[symbol] = [
                s for s in self.recent_signals[symbol] 
                if s['timestamp'] > cutoff_time
            ]
            
            # Remove empty entries
            if not self.recent_signals[symbol]:
                del self.recent_signals[symbol]
        
        # Clean up signal history
        old_signal_ids = [
            signal_id for signal_id, signal in self.signal_history.items()
            if signal['generated_at'] < cutoff_time
        ]
        
        for signal_id in old_signal_ids:
            del self.signal_history[signal_id]
        
        self.last_cleanup = datetime.now()
        logger.debug(f"🧹 Cleaned up {len(old_signal_ids)} old signals")
    
    def get_signal_stats(self) -> Dict:
        """Get statistics about signal processing"""
        total_recent = sum(len(signals) for signals in self.recent_signals.values())
        
        return {
            'total_recent_signals': total_recent,
            'symbols_with_signals': len(self.recent_signals),
            'signal_history_size': len(self.signal_history),
            'last_cleanup': self.last_cleanup.isoformat(),
            'min_confidence_threshold': self.min_confidence_threshold,
            'deduplication_window': self.deduplication_window
        }

# Global instance
signal_deduplicator = SignalDeduplicator()

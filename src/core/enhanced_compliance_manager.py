#!/usr/bin/env python3
"""
Enhanced Compliance Manager
Ensures system stays within regulatory limits including 7 trades per second
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class EnhancedComplianceManager:
    """
    Enhanced compliance manager with strict 7 trades per second enforcement
    """

    def __init__(self, config: Dict, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis = redis_client
        
        # Load configuration with defaults
        compliance_config = config.get('compliance', {})
        
        # 7 TRADES PER SECOND ENFORCEMENT
        self.max_trades_per_second = compliance_config.get('max_trades_per_second', 7)
        self.max_orders_per_second = compliance_config.get('max_orders_per_second', 7)
        self.ops_window = compliance_config.get('ops_monitoring_window', 1)  # 1 second window
        
        # Trade/Order tracking with precise timing
        self.trade_timestamps = deque(maxlen=1000)  # Keep last 1000 trades
        self.order_timestamps = deque(maxlen=1000)  # Keep last 1000 orders
        
        # Current rate tracking
        self.current_trades_per_second = 0.0
        self.current_orders_per_second = 0.0
        
        # Violation tracking
        self.violations_today = 0
        self.last_violation_time = None
        
        # Pause mechanism
        self.trading_paused = False
        self.pause_until = None
        self.pause_duration_seconds = 5  # 5 second cooldown after violation
        
        # Daily limits
        self.daily_trade_limit = compliance_config.get('max_daily_trades', 9999)  # No daily trade limit
        self.daily_trades_count = 0
        
        # User and strategy tracking
        self.user_trade_counts = defaultdict(int)
        self.strategy_trade_counts = defaultdict(int)
        
        # Monitoring active
        self.monitoring_active = False
        
        logger.info(f"✅ Enhanced Compliance Manager initialized:")
        logger.info(f"   📈 Max Trades/Second: {self.max_trades_per_second}")
        logger.info(f"   📊 Max Orders/Second: {self.max_orders_per_second}")
        logger.info(f"   ⏱️ Monitoring Window: {self.ops_window} seconds")

    async def start_monitoring(self):
        """Start compliance monitoring with precise timing"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        logger.info("🔍 Enhanced compliance monitoring started")
        
        # Start background monitoring task
        asyncio.create_task(self._continuous_monitoring())

    async def can_place_trade(self, user_id: str = None, strategy: str = None) -> Tuple[bool, str]:
        """
        Check if a trade can be placed within 7 trades per second limit
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        try:
            # Check if trading is paused
            if self.trading_paused:
                if self.pause_until and datetime.now() < self.pause_until:
                    remaining = (self.pause_until - datetime.now()).total_seconds()
                    return False, f"Trading paused for {remaining:.1f}s after rate violation"
                else:
                    # Unpause if time has passed
                    self.trading_paused = False
                    self.pause_until = None
                    logger.info("✅ Trading unpaused - compliance cooldown complete")

            # Calculate current trades per second
            current_tps = await self.calculate_trades_per_second()
            
            # STRICT 7 TRADES PER SECOND CHECK
            if current_tps >= self.max_trades_per_second:
                await self._handle_rate_violation('trades_per_second', current_tps)
                return False, f"❌ RATE LIMIT: {current_tps:.1f} >= {self.max_trades_per_second} trades/sec"
            
            # Predictive check - will this trade push us over?
            predicted_tps = await self._predict_trades_per_second_with_trade()
            if predicted_tps > self.max_trades_per_second:
                return False, f"⚠️ PREDICTED VIOLATION: {predicted_tps:.1f} > {self.max_trades_per_second} trades/sec"
            
            # Check daily limit
            if self.daily_trades_count >= self.daily_trade_limit:
                return False, f"📊 Daily trade limit reached: {self.daily_trades_count}/{self.daily_trade_limit}"
            
            # Check user-specific limits
            if user_id:
                user_limit = await self._get_user_trade_limit(user_id)
                if self.user_trade_counts[user_id] >= user_limit:
                    return False, f"👤 User trade limit reached: {self.user_trade_counts[user_id]}/{user_limit}"
            
            # Check strategy-specific limits
            if strategy:
                strategy_limit = await self._get_strategy_trade_limit(strategy)
                if self.strategy_trade_counts[strategy] >= strategy_limit:
                    return False, f"🧠 Strategy trade limit reached: {self.strategy_trade_counts[strategy]}/{strategy_limit}"
            
            # All checks passed
            return True, "✅ Trade approved"
            
        except Exception as e:
            logger.error(f"❌ Error checking trade compliance: {e}")
            return False, f"❌ Compliance check error: {str(e)}"

    async def record_trade(self, trade_data: Dict):
        """Record a trade for precise rate limit tracking"""
        try:
            timestamp = datetime.now()
            
            # Add to precise timestamp tracking
            self.trade_timestamps.append(timestamp)
            
            # Update counters
            self.daily_trades_count += 1
            
            if 'user_id' in trade_data:
                self.user_trade_counts[trade_data['user_id']] += 1
                
            if 'strategy' in trade_data:
                self.strategy_trade_counts[trade_data['strategy']] += 1
            
            # Store in Redis for persistence
            if self.redis:
                await self._store_trade_record(trade_data)
            
            # Update current rate
            self.current_trades_per_second = await self.calculate_trades_per_second()
            
            # Log significant rates
            if self.current_trades_per_second > self.max_trades_per_second * 0.8:  # 80% threshold
                logger.warning(f"⚠️ High trade rate: {self.current_trades_per_second:.2f} TPS "
                             f"({self.current_trades_per_second/self.max_trades_per_second*100:.1f}% of limit)")
            
            logger.debug(f"📈 Trade recorded - Current rate: {self.current_trades_per_second:.2f} TPS")
            
        except Exception as e:
            logger.error(f"❌ Error recording trade: {e}")

    async def calculate_trades_per_second(self) -> float:
        """Calculate current trades per second with precise timing"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.ops_window)
            
            # Count trades in the last N seconds (default 1 second)
            recent_trades = [ts for ts in self.trade_timestamps if ts > cutoff_time]
            
            # Calculate rate
            trades_per_second = len(recent_trades) / self.ops_window
            
            return trades_per_second
            
        except Exception as e:
            logger.error(f"❌ Error calculating trades per second: {e}")
            return 0.0

    async def _predict_trades_per_second_with_trade(self) -> float:
        """Predict TPS if we execute one more trade now"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.ops_window)
            
            # Count existing trades + 1 hypothetical trade
            recent_trades = [ts for ts in self.trade_timestamps if ts > cutoff_time]
            predicted_count = len(recent_trades) + 1
            
            return predicted_count / self.ops_window
            
        except Exception as e:
            logger.error(f"❌ Error predicting trades per second: {e}")
            return float('inf')  # Fail safe

    async def _handle_rate_violation(self, violation_type: str, current_rate: float):
        """Handle rate limit violation with immediate pause"""
        try:
            self.violations_today += 1
            self.last_violation_time = datetime.now()
            
            # IMMEDIATE PAUSE
            self.trading_paused = True
            self.pause_until = datetime.now() + timedelta(seconds=self.pause_duration_seconds)
            
            violation_msg = (f"🚨 RATE LIMIT VIOLATION: {violation_type} = {current_rate:.2f} "
                           f"(limit: {self.max_trades_per_second}) - Trading paused for {self.pause_duration_seconds}s")
            
            logger.critical(violation_msg)
            
            # Store violation record
            if self.redis:
                await self._store_violation_record(violation_type, current_rate)
            
            # Increase pause duration for repeated violations
            if self.violations_today > 3:
                self.pause_duration_seconds = min(30, self.pause_duration_seconds * 2)  # Max 30s
                logger.warning(f"⚠️ Repeated violations - increased pause to {self.pause_duration_seconds}s")
                
        except Exception as e:
            logger.error(f"❌ Error handling rate violation: {e}")

    async def _continuous_monitoring(self):
        """Continuous monitoring with 100ms precision"""
        while self.monitoring_active:
            try:
                # Calculate current rates
                current_tps = await self.calculate_trades_per_second()
                self.current_trades_per_second = current_tps
                
                # Store metrics in Redis
                if self.redis:
                    await self.redis.setex('compliance:current_tps', 60, str(current_tps))
                    await self.redis.setex('compliance:daily_trades', 60, str(self.daily_trades_count))
                
                # Check for warning thresholds
                if current_tps > self.max_trades_per_second * 0.9:  # 90% warning
                    logger.warning(f"⚠️ Trade rate warning: {current_tps:.2f} TPS "
                                 f"({current_tps/self.max_trades_per_second*100:.1f}% of {self.max_trades_per_second} limit)")
                
                # Sleep for 100ms for precise monitoring
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Compliance monitoring error: {e}")
                await asyncio.sleep(1)  # Longer sleep on error

    async def _store_trade_record(self, trade_data: Dict):
        """Store trade record in Redis"""
        try:
            if not self.redis:
                return
                
            # Store in daily trade list
            await self.redis.lpush(
                f"compliance:trades:{datetime.now().strftime('%Y%m%d')}",
                json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    **trade_data
                })
            )
            
            # Update daily counter
            await self.redis.hincrby('compliance:counters', 'daily_trades', 1)
            
        except Exception as e:
            logger.error(f"❌ Failed to store trade record: {e}")

    async def _store_violation_record(self, violation_type: str, rate: float):
        """Store violation record for audit"""
        try:
            if not self.redis:
                return
                
            violation_record = {
                'timestamp': datetime.now().isoformat(),
                'violation_type': violation_type,
                'rate': rate,
                'limit': self.max_trades_per_second,
                'daily_violations': self.violations_today
            }
            
            await self.redis.lpush(
                f"compliance:violations:{datetime.now().strftime('%Y%m%d')}",
                json.dumps(violation_record)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to store violation record: {e}")

    async def _get_user_trade_limit(self, user_id: str) -> int:
        """Get trade limit for specific user"""
        # Default user limits - can be customized per user
        return 100

    async def _get_strategy_trade_limit(self, strategy: str) -> int:
        """Get trade limit for specific strategy"""
        strategy_limits = {
            'high_frequency': 50,
            'news_impact': 20,
            'volatility_explosion': 30,
            'momentum_surfer': 40,
            'default': 50
        }
        return strategy_limits.get(strategy, strategy_limits['default'])

    async def get_compliance_status(self) -> Dict:
        """Get comprehensive compliance status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'rates': {
                'current_trades_per_second': self.current_trades_per_second,
                'max_trades_per_second': self.max_trades_per_second,
                'rate_percentage': (self.current_trades_per_second / self.max_trades_per_second) * 100,
                'monitoring_window_seconds': self.ops_window
            },
            'daily_stats': {
                'trades_today': self.daily_trades_count,
                'daily_limit': self.daily_trade_limit,
                'violations_today': self.violations_today
            },
            'status': {
                'trading_paused': self.trading_paused,
                'pause_until': self.pause_until.isoformat() if self.pause_until else None,
                'monitoring_active': self.monitoring_active
            },
            'user_breakdown': dict(self.user_trade_counts),
            'strategy_breakdown': dict(self.strategy_trade_counts)
        }

    async def reset_daily_counters(self):
        """Reset daily counters at end of day"""
        self.daily_trades_count = 0
        self.violations_today = 0
        self.user_trade_counts.clear()
        self.strategy_trade_counts.clear()
        logger.info("📊 Daily compliance counters reset")

    async def stop_monitoring(self):
        """Stop compliance monitoring"""
        self.monitoring_active = False
        logger.info("🛑 Enhanced compliance monitoring stopped")

if __name__ == "__main__":
    # Test the enhanced compliance manager
    import asyncio
    
    async def test_compliance():
        config = {
            'compliance': {
                'max_trades_per_second': 7,
                'ops_monitoring_window': 1
            }
        }
        
        manager = EnhancedComplianceManager(config)
        await manager.start_monitoring()
        
        # Test rapid trades
        for i in range(10):
            can_trade, reason = await manager.can_place_trade()
            print(f"Trade {i+1}: {can_trade} - {reason}")
            
            if can_trade:
                await manager.record_trade({'user_id': 'test_user', 'strategy': 'test'})
            
            await asyncio.sleep(0.1)  # 100ms between trades = 10 TPS
        
        status = await manager.get_compliance_status()
        print(f"\nFinal Status: {status}")
        
        await manager.stop_monitoring()
    
    asyncio.run(test_compliance()) 
# f_and_o_scalping_system/risk/compliance_manager.py
"""
Compliance Manager
Ensures system stays within regulatory limits
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
import redis.asyncio as redis

from ..events import EventBus, EventType, TradingEvent
from ..utils.decorators import synchronized_state

logger = logging.getLogger(__name__
class ComplianceManager:
    """
    Manages compliance with:
    - Orders Per Second (OPS) limits
    - Daily order limits
    - Symbol-wise position limits
    - Regulatory reporting requirements
    """

    def __init__(self, event_bus: EventBus, redis_client: redis.Redis,:
    pass

    # Order tracking

    # OPS tracking

    # Daily limits

    # User/Strategy limits

    # Compliance state

    # Setup event handlers
    self._setup_event_handlers(
    # Start monitoring task

    def _setup_event_handlers(self):
        """Setup event subscriptions"""
        self.event_bus.subscribe(
        EventType.ORDER_PLACED,
        self._handle_order_placed

        async def start_monitoring(self):
        """Start compliance monitoring"""
        logger.info("Compliance monitoring started"
        """
        Check if order can be placed within compliance limits

        Returns:
        Tuple of (allowed, reason
        """
        # Check if compliance is paused
        if self.compliance_paused:
            if self.pause_until and datetime.now() < self.pause_until:
            return False, f"Compliance paused until {self.pause_until}"
            else:

                # Check OPS limit
                current_ops=await self.calculate_ops(
            return False, f"OPS limit reached ({current_ops:.1f}/{self.max_ops})"

            # Predictive check - will this order push us over?
            predicted_ops=await self._predict_ops_with_order(
            if predicted_ops > self.max_ops * 0.95:  # 95% threshold
            return False, f"Predicted OPS too high ({predicted_ops:.1f})"

            # Check daily order limit
        return False, f"Daily order limit reached ({self.daily_orders}/{self.daily_order_limit})"

        # Check user-specific limits if provided
        if user_id:
            user_limit=await self._get_user_limit(user_id
        return False, f"User order limit reached"

        # Check strategy-specific limits if provided
        if strategy:
            strategy_limit=await self._get_strategy_limit(strategy
        return False, f"Strategy order limit reached"

    return True, None

    @ synchronized_state
    async def record_order(self, order_data: Dict):
    """Record an order for compliance tracking"""
    timestamp=datetime.now(
    # Add to timestamp tracking
    self.order_timestamps.append(timestamp
    # Update counters

    if 'user_id' in order_data:

        if 'strategy' in order_data:

            # Store in Redis for persistence
            await self._store_order_record(order_data
            # Update OPS

            # Check for violations
            if self.current_ops > self.max_ops:
                await self._handle_ops_violation(
                # Log compliance metrics
                logger.info(f"Compliance update - Daily orders: {self.daily_orders}, "
                f"Current OPS: {self.current_ops:.2f}"
                async def calculate_ops(self) -> float:
                """Calculate current orders per second"""
                current_time=datetime.now(
                cutoff_time=current_time - timedelta(seconds=self.ops_window
                # Count orders in window
                recent_orders=[
                ts for ts in self.order_timestamps
                if ts > cutoff_time]

                    # Calculate rate
                    ops=len(recent_orders) / self.ops_window

                    # Store in history
                    self.ops_history.append((current_time, ops
                return ops

                async def _predict_ops_with_order(self) -> float:
                """Predict OPS if we place an order now"""
                current_time=datetime.now(
                cutoff_time=current_time - timedelta(seconds=self.ops_window
                # Count existing orders + 1
                recent_orders=[
                ts for ts in self.order_timestamps
                if ts > cutoff_time]

                    predicted_count=len(recent_orders) + 1
                return predicted_count / self.ops_window

                async def _monitor_ops(self):
                """Continuous OPS monitoring"""
                while True:
                    try:
                        current_ops=await self.calculate_ops(
                        # Store in Redis
                        await self.redis.set(
                        'compliance:current_ops',
                        str(current_ops),

                        # Check thresholds
                        if current_ops > self.max_ops * 0.9:  # 90% warning
                            await self.event_bus.publish(TradingEvent(

                            if current_ops > self.max_ops * 0.95:  # 95% critical
                                await self.event_bus.publish(TradingEvent(

                                await asyncio.sleep(0.5)  # Check every 500ms

                                except Exception as e:
                                    logger.error(f"OPS monitoring error: {e}"
                                    await asyncio.sleep(1
                                    async def _handle_order_placed(self, event: TradingEvent):
                                    """Handle order placed event"""
                                    order_data=event.data
                                    await self.record_order(order_data
                                    async def _handle_ops_violation(self):
                                    """Handle OPS limit violation"""
                                    logger.critical(f"OPS VIOLATION: {self.current_ops:.2f} > {self.max_ops}"
                                    # Pause for cooldown

                                    # Publish critical event
                                    await self.event_bus.publish(TradingEvent(
                                    'violation': True,
                                    'current_ops': self.current_ops,
                                    'max_ops': self.max_ops,
                                    'pause_until': self.pause_until.isoformat(

                                    async def get_metrics(self) -> Dict:
                                    """Get current compliance metrics"""
                                return {
                                'orders_per_second': self.current_ops,
                                'max_ops_today': self.max_ops_today,
                                'daily_orders': self.daily_orders,
                                'daily_order_limit': self.daily_order_limit,
                                'ops_violations': self.ops_violations,
                                'compliance_paused': self.compliance_paused,
                                'user_order_counts': dict(self.user_order_counts),
                                'strategy_order_counts': dict(self.strategy_order_counts

                                """Get OPS history for specified minutes"""
                                cutoff_time=datetime.now() - timedelta(minutes=minutes
                            return [(ts, ops) for ts, ops in self.ops_history if ts > cutoff_time]
                            async def reset_daily_counters(self):
                            """Reset daily counters at EOD"""
                            self.user_order_counts.clear(
                            self.strategy_order_counts.clear(
                            logger.info("Daily compliance counters reset"
                            async def _store_order_record(self, order_data: Dict):
                            """Store order record in Redis"""
                            try:
                                # Store in daily list
                                await self.redis.lpush(
                                f"compliance:orders:{datetime.now().strftime('%Y%m%d')}",
                                json.dumps({
                                'timestamp': datetime.now().isoformat(),
                                **order_data

                                # Update counters
                                await self.redis.hincrby('compliance:counters', 'daily_orders', 1
                                except Exception as e:
                                    logger.error(f"Failed to store order record: {e}"
                                    async def _get_user_limit(self, user_id: str) -> int:
                                    """Get order limit for specific user"""
                                    # This would be loaded from configuration or database
                                    # For now, return a default
                                return 100

                                async def _get_strategy_limit(self, strategy: str) -> int:
                                """Get order limit for specific strategy"""
                                # Strategy-specific limits
                                limits={
                                'high_frequency': 200,
                                'news_impact': 50,
                                'default': 100

                            return limits.get(strategy, limits['default'
                            async def generate_compliance_report(self} -> Dict:
                            """Generate compliance report"""
                        return {
                        'timestamp': datetime.now(].isoformat(),
                        'summary': {
                        'total_orders': self.daily_orders,
                        'max_ops_reached': self.max_ops_today,
                        'ops_violations': self.ops_violations,
                        'avg_ops': sum(ops for _, ops in self.ops_history) / len(self.ops_history) if self.ops_history else 0},
                        'user_breakdown': dict(self.user_order_counts),
                        'strategy_breakdown': dict(self.strategy_order_counts),
                        'hourly_ops': await self._calculate_hourly_ops(),

                        async def _calculate_hourly_ops(self) -> Dict[str, float]:
                        """Calculate average OPS by hour"""
                        hourly_ops = defaultdict(list
                        for timestamp, ops in self.ops_history:
                            hour=timestamp.hour
                            hourly_ops[f"{hour:02d}:00"].append(ops
                        return {
                        hour: sum(ops_list) / len(ops_list
                        for hour, ops_list in hourly_ops.items(

                            def get_max_ops_today(self) -> float:
                                """Get maximum OPS reached today"""
                            return self.max_ops_today

                            def get_violations_count(self) -> int:
                                """Get number of OPS violations today"""
                            return self.ops_violations

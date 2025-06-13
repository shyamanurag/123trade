import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import redis.asyncio as redis

from .models import (
    Order, OrderStatus, OrderType, OrderSide, OptionType,
    MultiLegOrder, BracketOrder, ConditionalOrder, ExecutionStrategy
)
from .user_tracker import UserTracker
from .risk_manager import RiskManager
from .notification_manager import NotificationManager
from .trade_allocator import TradeAllocator
from core.exceptions import OrderError
from .system_evolution import SystemEvolution
from .capital_manager import CapitalManager
from ..models.schema import Trade

logger = logging.getLogger(__name__)

class OrderManager:
    """Enhanced order manager with multi-user support, system evolution, and advanced order types"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = redis.Redis(
            host=config['redis']['host'],
            port=config['redis']['port'],
            db=config['redis']['db']
        )
        self.user_tracker = UserTracker(config)
        self.risk_manager = RiskManager(config)
        self.notification_manager = NotificationManager(config)
        self.trade_allocator = TradeAllocator(config)
        self.system_evolution = SystemEvolution(config)
        self.capital_manager = CapitalManager(config)
        
        # Initialize order queues and locks
        self.order_queues = {}
        self.order_locks = {}
        self.active_orders = {}
        self.order_history = {}
        self.active_trailing_stops = {}
        
        # Initialize execution strategies
        self.execution_strategies = {
            ExecutionStrategy.MARKET: self._execute_market_order,
            ExecutionStrategy.LIMIT: self._execute_limit_order,
            ExecutionStrategy.SMART: self._execute_smart_order,
            ExecutionStrategy.TWAP: self._execute_twap_order,
            ExecutionStrategy.VWAP: self._execute_vwap_order,
            ExecutionStrategy.ICEBERG: self._execute_iceberg_order
        }
        
        # Start background tasks
        self._start_background_tasks()

    async def place_strategy_order(self, strategy_name: str, signal: Dict[str, Any]) -> List[Tuple[str, Order]]:
        """Place an order based on a strategy signal with trade allocation and system evolution"""
        try:
            # Get strategy performance metrics
            strategy_metrics = await self.system_evolution.get_strategy_metrics(strategy_name)
            
            # Adjust signal based on strategy performance
            adjusted_signal = self._adjust_signal_with_metrics(signal, strategy_metrics)
            
            # Allocate trades to users
            allocated_orders = await self.trade_allocator.allocate_trade(strategy_name, adjusted_signal)
            
            # Place orders for each user
            placed_orders = []
            for user_id, order in allocated_orders:
                try:
                    # Get user performance metrics
                    user_metrics = await self.system_evolution.get_user_metrics(user_id)
                    
                    # Adjust order based on user performance
                    adjusted_order = self._adjust_order_with_metrics(order, user_metrics)
                    
                    # Place the order
                    placed_order = await self.place_order(user_id, adjusted_order)
                    placed_orders.append((user_id, placed_order))
                    
                    # Send notification
                    await self._send_order_notification(user_id, strategy_name, placed_order)

                except Exception as e:
                    logger.error(f"Error placing order for user {user_id}: {str(e)}")
                    continue
            
            return placed_orders

        except Exception as e:
            logger.error(f"Error placing strategy order: {str(e)}")
            raise OrderError(f"Failed to place strategy order: {str(e)}")

    async def place_order(self, user_id: str, order: Order) -> str:
        """Place a new order with user-specific handling and capital management"""
        try:
            # Validate user and order
            if not await self._validate_user_order(user_id, order):
                raise OrderError(f"Order validation failed for user {user_id}")
            
            # Get current capital
            current_capital = await self.capital_manager.get_user_capital(user_id)
            
            # Check if user has sufficient capital
            required_capital = order.quantity * order.price
            if required_capital > current_capital:
                raise OrderError("Insufficient capital")
            
            # Generate order ID and set user ID
            order.order_id = str(uuid.uuid4())
            order.user_id = user_id
            
            # Initialize user-specific queues if needed
            if user_id not in self.order_queues:
                self.order_queues[user_id] = asyncio.Queue()
                self.order_locks[user_id] = asyncio.Lock()
                self.active_orders[user_id] = set()
                self.order_history[user_id] = []
            
            # Queue the order
            await self.order_queues[user_id].put(order)
            
            # Track the order
            await self.user_tracker.track_order(user_id, order)
            
            # Execute order
            result = await self.execute_order(order)
            
            if result['status'] == 'FILLED':
                # Update capital after trade
                trade = Trade(
                    trade_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    user_id=user_id,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=order.price,
                    execution_price=result['average_price'],
                    order_type=order.order_type,
                    timestamp=datetime.now()
                )
                
                await self.capital_manager.update_capital_after_trade(user_id, trade)
                
                # Update system evolution
                await self.system_evolution.record_trade(trade)
                
                # Send notification
                await self._send_order_notification(user_id, order, result)
            
            return order.order_id

        except Exception as e:
            logger.error(f"Error placing order for user {user_id}: {str(e)}")
            raise OrderError(f"Failed to place order: {str(e)}")

    async def place_multi_leg_order(self, user_id: str, multi_leg_order: MultiLegOrder) -> str:
        """Place a multi-leg order with enhanced validation"""
        try:
            # Validate all legs
            for leg in multi_leg_order.legs:
                if not await self._validate_user_order(user_id, leg):
                    raise OrderError(f"Multi-leg order validation failed for user {user_id}")
            
            # Generate order ID
            multi_leg_order.order_id = str(uuid.uuid4())
            multi_leg_order.user_id = user_id
            
            # Place each leg
            for leg in multi_leg_order.legs:
                leg.parent_order_id = multi_leg_order.order_id
                await self.place_order(user_id, leg)
            
            return multi_leg_order.order_id

        except Exception as e:
            logger.error(f"Error placing multi-leg order for user {user_id}: {str(e)}")
            raise OrderError(f"Failed to place multi-leg order: {str(e)}")

    async def place_bracket_order(self, user_id: str, bracket_order: BracketOrder) -> str:
        """Place a bracket order with enhanced monitoring"""
        try:
            # Validate all orders
            for order in [bracket_order.entry_order, bracket_order.take_profit_order, bracket_order.stop_loss_order]:
                if not await self._validate_user_order(user_id, order):
                    raise OrderError(f"Bracket order validation failed for user {user_id}")
            
            # Generate order ID
            bracket_order.order_id = str(uuid.uuid4())
            bracket_order.user_id = user_id
            
            # Place entry order first
            bracket_order.entry_order.parent_order_id = bracket_order.order_id
            await self.place_order(user_id, bracket_order.entry_order)
            
            # Place take profit and stop loss orders
            bracket_order.take_profit_order.parent_order_id = bracket_order.order_id
            bracket_order.stop_loss_order.parent_order_id = bracket_order.order_id
            
            # Store bracket order for monitoring
            await self._store_bracket_order(bracket_order)
            
            return bracket_order.order_id

        except Exception as e:
            logger.error(f"Error placing bracket order for user {user_id}: {str(e)}")
            raise OrderError(f"Failed to place bracket order: {str(e)}")

    async def place_conditional_order(self, user_id: str, conditional_order: ConditionalOrder) -> str:
        """Place a conditional order with enhanced monitoring"""
        try:
            # Validate both orders
            for order in [conditional_order.trigger_order, conditional_order.triggered_order]:
                if not await self._validate_user_order(user_id, order):
                    raise OrderError(f"Conditional order validation failed for user {user_id}")
            
            # Generate order ID
            conditional_order.order_id = str(uuid.uuid4())
            conditional_order.user_id = user_id
            
            # Place trigger order
            conditional_order.trigger_order.parent_order_id = conditional_order.order_id
            await self.place_order(user_id, conditional_order.trigger_order)
            
            # Store conditional order for monitoring
            await self._store_conditional_order(conditional_order)
            
            return conditional_order.order_id

        except Exception as e:
            logger.error(f"Error placing conditional order for user {user_id}: {str(e)}")
            raise OrderError(f"Failed to place conditional order: {str(e)}")

    def _adjust_signal_with_metrics(self, signal: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust signal based on strategy performance metrics"""
        try:
            adjusted_signal = signal.copy()
            
            # Adjust quantity based on win rate
            win_rate = metrics.get('win_rate', 0.5)
            if win_rate > 0.7:  # High performing strategy
                adjusted_signal['quantity'] = int(signal['quantity'] * 1.2)  # Increase size
            elif win_rate < 0.3:  # Low performing strategy
                adjusted_signal['quantity'] = int(signal['quantity'] * 0.8)  # Decrease size
            
            # Adjust price based on average return
            avg_return = metrics.get('average_return', 0)
            if avg_return > 0:
                if signal.get('side') == OrderSide.BUY:
                    adjusted_signal['price'] = signal['price'] * (1 + avg_return/100)
                else:
                    adjusted_signal['price'] = signal['price'] * (1 - avg_return/100)
            
            return adjusted_signal

        except Exception as e:
            logger.error(f"Error adjusting signal with metrics: {str(e)}")
            return signal

    def _adjust_order_with_metrics(self, order: Order, metrics: Dict[str, Any]) -> Order:
        """Adjust order based on user performance metrics"""
        try:
            adjusted_order = order.copy()
            
            # Adjust quantity based on user's success rate
            success_rate = metrics.get('success_rate', 0.5)
            if success_rate > 0.7:  # High performing user
                adjusted_order.quantity = int(order.quantity * 1.1)  # Slight increase
            elif success_rate < 0.3:  # Low performing user
                adjusted_order.quantity = int(order.quantity * 0.9)  # Slight decrease
            
            # Adjust price based on user's average return
            avg_return = metrics.get('average_return', 0)
            if avg_return > 0:
                if order.side == OrderSide.BUY:
                    adjusted_order.price = order.price * (1 + avg_return/200)  # Half the impact
                else:
                    adjusted_order.price = order.price * (1 - avg_return/200)
            
            return adjusted_order

        except Exception as e:
            logger.error(f"Error adjusting order with metrics: {str(e)}")
            return order

    async def _validate_user_order(self, user_id: str, order: Order) -> bool:
        """Validate order against user-specific risk limits"""
        try:
            # Check risk limits
            if not await self.risk_manager.check_order_risk(user_id, order):
                return False

            # Check user's active orders limit
            if len(self.active_orders[user_id]) >= self.config['user_management']['limits']['max_active_orders']:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating order for user {user_id}: {str(e)}")
            return False

    async def _store_bracket_order(self, bracket_order: BracketOrder):
        """Store bracket order for monitoring"""
        key = f"bracket_orders:{bracket_order.user_id}:{bracket_order.order_id}"
        await self.redis.set(key, json.dumps(bracket_order.__dict__))

    async def _store_conditional_order(self, conditional_order: ConditionalOrder):
        """Store conditional order for monitoring"""
        key = f"conditional_orders:{conditional_order.user_id}:{conditional_order.order_id}"
        await self.redis.set(key, json.dumps(conditional_order.__dict__))

    async def _monitor_bracket_orders(self):
        """Monitor and manage bracket orders"""
        while True:
            try:
                # Get all bracket orders
                keys = await self.redis.keys("bracket_orders:*")
                for key in keys:
                    data = await self.redis.get(key)
                    if data:
                        bracket_order = BracketOrder(**json.loads(data))
                        
                        # Check if entry order is filled
                        if bracket_order.entry_order.status == OrderStatus.FILLED:
                            # Place take profit and stop loss orders
                            await self.place_order(bracket_order.user_id, bracket_order.take_profit_order)
                            await self.place_order(bracket_order.user_id, bracket_order.stop_loss_order)
                            
                            # Remove from monitoring
                            await self.redis.delete(key)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring bracket orders: {str(e)}")
                await asyncio.sleep(5)

    async def _monitor_conditional_orders(self):
        """Monitor and manage conditional orders"""
        while True:
            try:
                # Get all conditional orders
                keys = await self.redis.keys("conditional_orders:*")
                for key in keys:
                    data = await self.redis.get(key)
                    if data:
                        conditional_order = ConditionalOrder(**json.loads(data))
                        
                        # Check condition
                        if await self._check_condition(conditional_order):
                            # Place triggered order
                            await self.place_order(conditional_order.user_id, conditional_order.triggered_order)
                            
                            # Remove from monitoring
                            await self.redis.delete(key)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring conditional orders: {str(e)}")
                await asyncio.sleep(5)

    async def _check_condition(self, conditional_order: ConditionalOrder) -> bool:
        """Check if condition is met for conditional order"""
        try:
            # Get current market data for the symbol
            symbol = conditional_order.trigger_order.symbol
            current_price = await self._get_current_price(symbol)
            
            if not current_price:
                return False
            
            # Check different condition types
            condition_type = conditional_order.condition.get('type')
            condition_value = conditional_order.condition.get('value')
            
            if condition_type == 'price_above':
                return current_price > condition_value
            elif condition_type == 'price_below':
                return current_price < condition_value
            elif condition_type == 'price_crosses':
                # Check if price crossed the threshold
                last_price = await self._get_last_price(symbol)
                if last_price:
                    return (last_price < condition_value and current_price >= condition_value) or \
                           (last_price > condition_value and current_price <= condition_value)
            elif condition_type == 'volume_above':
                current_volume = await self._get_current_volume(symbol)
                return current_volume and current_volume > condition_value
            elif condition_type == 'time_based':
                # Check if current time matches the condition
                current_time = datetime.now()
                trigger_time = datetime.fromisoformat(condition_value)
                return current_time >= trigger_time
            elif condition_type == 'order_filled':
                # Check if the trigger order is filled
                return conditional_order.trigger_order.status == OrderStatus.FILLED
            
            # Default case - condition not recognized
            logger.warning(f"Unknown condition type: {condition_type}")
            return False

        except Exception as e:
            logger.error(f"Error checking condition: {str(e)}")
            return False
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Try to get from Redis cache first
            price_key = f"price:{symbol}"
            price_data = await self.redis.get(price_key)
            if price_data:
                return float(price_data)
            
            # If not in cache, return None (would need market data provider in production)
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    async def _get_last_price(self, symbol: str) -> Optional[float]:
        """Get last recorded price for a symbol"""
        try:
            # Get from price history
            history_key = f"price_history:{symbol}"
            history = await self.redis.lrange(history_key, -2, -2)
            if history:
                return float(history[0])
            return None
        except Exception as e:
            logger.error(f"Error getting last price for {symbol}: {str(e)}")
            return None
    
    async def _get_current_volume(self, symbol: str) -> Optional[int]:
        """Get current volume for a symbol"""
        try:
            # Try to get from Redis cache
            volume_key = f"volume:{symbol}"
            volume_data = await self.redis.get(volume_key)
            if volume_data:
                return int(volume_data)
            return None
        except Exception as e:
            logger.error(f"Error getting current volume for {symbol}: {str(e)}")
            return None

    async def execute_order(self, order: Order) -> Dict[str, Any]:
        """Execute an order based on its execution strategy"""
        try:
            # Get the execution strategy handler
            strategy_handler = self.execution_strategies.get(
                order.execution_strategy, 
                self._execute_market_order  # Default to market order
            )
            
            # Execute the order using the appropriate strategy
            result = await strategy_handler(order)
            
            # Update order status
            order.status = OrderStatus(result['status'])
            
            # Store order in history
            if order.user_id in self.order_history:
                self.order_history[order.user_id].append(order)
            
            # Remove from active orders if completed
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                if order.user_id in self.active_orders:
                    self.active_orders[order.user_id].discard(order.order_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing order {order.order_id}: {str(e)}")
            return {
                'status': 'REJECTED',
                'reason': str(e),
                'order_id': order.order_id
            }
    
    async def _execute_market_order(self, order: Order) -> Dict[str, Any]:
        """Execute a market order"""
        # In production, this would connect to the broker API
        # For now, simulate execution
        return {
            'status': 'FILLED',
            'average_price': order.price,
            'filled_quantity': order.quantity,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_limit_order(self, order: Order) -> Dict[str, Any]:
        """Execute a limit order"""
        # In production, this would place a limit order with the broker
        return {
            'status': 'PENDING',
            'order_id': order.order_id,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_smart_order(self, order: Order) -> Dict[str, Any]:
        """Execute a smart order with intelligent routing"""
        # Smart order routing logic would go here
        return await self._execute_market_order(order)
    
    async def _execute_twap_order(self, order: Order) -> Dict[str, Any]:
        """Execute a TWAP (Time Weighted Average Price) order"""
        # TWAP execution logic would go here
        return await self._execute_market_order(order)
    
    async def _execute_vwap_order(self, order: Order) -> Dict[str, Any]:
        """Execute a VWAP (Volume Weighted Average Price) order"""
        # VWAP execution logic would go here
        return await self._execute_market_order(order)
    
    async def _execute_iceberg_order(self, order: Order) -> Dict[str, Any]:
        """Execute an iceberg order"""
        # Iceberg order logic would go here
        return await self._execute_market_order(order)
    
    async def _send_order_notification(self, user_id: str, *args):
        """Send order notification to user"""
        try:
            if len(args) == 2:
                # Called with order and result
                order, result = args
                message = f"Order {order.order_id} for {order.symbol} - Status: {result['status']}"
            else:
                # Called with strategy_name and order
                strategy_name, order = args
                message = f"Strategy {strategy_name} placed order for {order.symbol}"
            
            await self.notification_manager.send_notification(
                user_id=user_id,
                notification_type='order_update',
                message=message,
                data={
                    'order_id': order.order_id if hasattr(order, 'order_id') else None,
                    'symbol': order.symbol if hasattr(order, 'symbol') else None,
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error sending order notification: {str(e)}")

    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_bracket_orders())
        asyncio.create_task(self._monitor_conditional_orders())
        asyncio.create_task(self.capital_manager.end_of_day_update())
        # Start other background tasks... 
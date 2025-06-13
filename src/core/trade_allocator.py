import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from .models import Order, OrderType, OrderSide
from .exceptions import OrderError
from .system_evolution import SystemEvolution

logger = logging.getLogger(__name__)

class TradeAllocator:
    """Handles trade rotation and pro-rata order sizing based on user capital and margin"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_capital = {}  # user_id -> capital
        self.user_margin = {}   # user_id -> available margin
        self.trade_rotation = {}  # strategy -> [user_id, ...]
        self.last_trade_time = {}  # user_id -> timestamp
        self.min_trade_interval = config.get('trade_rotation', {}).get('min_interval_seconds', 300)
        self.max_position_size = config.get('trade_rotation', {}).get('max_position_size_percent', 0.1)
        
        # Initialize system evolution
        self.system_evolution = SystemEvolution(config)
    
    async def allocate_trade(self, strategy_name: str, signal: Dict[str, Any]) -> List[Tuple[str, Order]]:
        """
        Allocate trade to users based on capital, margin, and rotation rules
        Returns list of (user_id, order) tuples
        """
        try:
            # Get strategy weight
            strategy_weight = await self.system_evolution.get_strategy_weight(strategy_name)
            
            # Predict trade outcome
            trade_features = self._extract_trade_features(signal)
            prediction = await self.system_evolution.predict_trade_outcome(strategy_name, trade_features)
            
            # Adjust allocation based on prediction
            if prediction['confidence'] < 0.5 or prediction['predicted_return'] < 0:
                logger.info(f"Low confidence or negative predicted return for strategy {strategy_name}")
                return []
            
            # Get eligible users for this strategy
            eligible_users = await self._get_eligible_users(strategy_name)
            if not eligible_users:
                raise OrderError("No eligible users found for trade allocation")
            
            # Calculate total capital of eligible users
            total_capital = sum(self.user_capital[user_id] for user_id in eligible_users)
            
            # Calculate pro-rata order sizes with user weights
            allocated_orders = []
            remaining_quantity = signal['quantity']
            
            for user_id in eligible_users:
                # Get user weight
                user_weight = await self.system_evolution.get_user_weight(user_id)
                
                # Calculate user's share based on capital and weight
                user_share = (self.user_capital[user_id] / total_capital) * user_weight
                user_quantity = int(remaining_quantity * user_share)
                
                if user_quantity > 0:
                    # Check margin availability
                    if not await self._check_margin_availability(user_id, signal, user_quantity):
                        # Try to find alternative user with margin
                        alt_user_id = await self._find_alternative_user(eligible_users, signal, user_quantity)
                        if alt_user_id:
                            user_id = alt_user_id
                        else:
                            logger.warning(f"No alternative user found with sufficient margin for {user_quantity} shares")
                            continue
                    
                    # Create order for user
                    order = await self._create_user_order(user_id, signal, user_quantity)
                    allocated_orders.append((user_id, order))
                    
                    # Update rotation tracking
                    self.last_trade_time[user_id] = datetime.now()
                    
                    # Record trade for learning
                    await self._record_trade_for_learning(strategy_name, user_id, signal, order)
            
            return allocated_orders
            
        except Exception as e:
            logger.error(f"Error allocating trade: {str(e)}")
            raise OrderError(f"Failed to allocate trade: {str(e)}")
    
    def _extract_trade_features(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for trade prediction"""
        try:
            return {
                'market_volatility': signal.get('market_volatility', 0),
                'volume': signal.get('volume', 0),
                'price_momentum': signal.get('price_momentum', 0),
                'time_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'position_size': signal.get('quantity', 0)
            }
        except Exception as e:
            logger.error(f"Error extracting trade features: {str(e)}")
            return {}
    
    async def _record_trade_for_learning(self, strategy_name: str, user_id: str, signal: Dict[str, Any], order: Order):
        """Record trade data for system learning"""
        try:
            # Record strategy performance
            strategy_data = {
                'strategy_name': strategy_name,
                'symbol': signal['symbol'],
                'quantity': order.quantity,
                'price': order.price,
                'timestamp': datetime.now(),
                'market_volatility': signal.get('market_volatility', 0),
                'volume': signal.get('volume', 0),
                'price_momentum': signal.get('price_momentum', 0),
                'time_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'position_size': order.quantity
            }
            await self.system_evolution.record_trade_performance(strategy_name, strategy_data)
            
            # Record user performance
            user_data = {
                'user_id': user_id,
                'strategy_name': strategy_name,
                'symbol': signal['symbol'],
                'quantity': order.quantity,
                'price': order.price,
                'timestamp': datetime.now()
            }
            await self.system_evolution.record_user_performance(user_id, user_data)
            
        except Exception as e:
            logger.error(f"Error recording trade for learning: {str(e)}")
    
    async def _get_eligible_users(self, strategy_name: str) -> List[str]:
        """Get list of eligible users for trade rotation"""
        try:
            # Initialize rotation if needed
            if strategy_name not in self.trade_rotation:
                self.trade_rotation[strategy_name] = []
            
            # Get all users with capital
            eligible_users = []
            current_time = datetime.now()
            
            for user_id in self.user_capital.keys():
                # Check if user has capital
                if self.user_capital[user_id] <= 0:
                    continue
                
                # Check trade rotation timing
                last_trade = self.last_trade_time.get(user_id)
                if last_trade and (current_time - last_trade).total_seconds() < self.min_trade_interval:
                    continue
                
                eligible_users.append(user_id)
            
            # Rotate users if needed
            if not eligible_users:
                # Reset rotation if no eligible users
                self.trade_rotation[strategy_name] = []
                return list(self.user_capital.keys())
            
            # Sort by last trade time
            eligible_users.sort(key=lambda x: self.last_trade_time.get(x, datetime.min))
            
            return eligible_users
            
        except Exception as e:
            logger.error(f"Error getting eligible users: {str(e)}")
            return []
    
    async def _check_margin_availability(self, user_id: str, signal: Dict[str, Any], quantity: int) -> bool:
        """Check if user has sufficient margin for the trade"""
        try:
            required_margin = await self._calculate_required_margin(signal, quantity)
            available_margin = self.user_margin.get(user_id, 0)
            
            return available_margin >= required_margin
            
        except Exception as e:
            logger.error(f"Error checking margin availability: {str(e)}")
            return False
    
    async def _find_alternative_user(self, eligible_users: List[str], signal: Dict[str, Any], quantity: int) -> Optional[str]:
        """Find alternative user with sufficient margin"""
        try:
            for user_id in eligible_users:
                if await self._check_margin_availability(user_id, signal, quantity):
                    return user_id
            return None
            
        except Exception as e:
            logger.error(f"Error finding alternative user: {str(e)}")
            return None
    
    async def _calculate_required_margin(self, signal: Dict[str, Any], quantity: int) -> float:
        """Calculate required margin for the trade"""
        try:
            # Get current price
            price = signal.get('entry_price', 0)
            
            # Calculate position value
            position_value = price * quantity
            
            # Apply margin requirements
            margin_requirement = self.config.get('margin', {}).get('requirement_percent', 0.2)
            required_margin = position_value * margin_requirement
            
            return required_margin
            
        except Exception as e:
            logger.error(f"Error calculating required margin: {str(e)}")
            return float('inf')
    
    async def _create_user_order(self, user_id: str, signal: Dict[str, Any], quantity: int) -> Order:
        """Create order for user with pro-rata sizing"""
        try:
            # Calculate position size limits
            max_position = self.user_capital[user_id] * self.max_position_size
            current_position = await self._get_current_position(user_id, signal['symbol'])
            
            # Adjust quantity if needed
            if current_position + quantity > max_position:
                quantity = int(max_position - current_position)
            
            # Create order
            return Order(
                order_id=str(uuid.uuid4()),
                user_id=user_id,
                signal_id=signal.get('signal_id'),
                symbol=signal['symbol'],
                option_type=signal.get('option_type'),
                strike=signal.get('strike'),
                quantity=quantity,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY if signal['action'] == 'BUY' else OrderSide.SELL,
                price=signal.get('entry_price'),
                strategy_name=signal.get('strategy_name'),
                metadata={
                    'allocation_type': 'pro_rata',
                    'original_quantity': signal['quantity'],
                    'allocation_percent': quantity / signal['quantity']
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating user order: {str(e)}")
            raise OrderError(f"Failed to create user order: {str(e)}")
    
    async def _get_current_position(self, user_id: str, symbol: str) -> float:
        """Get user's current position size for symbol"""
        # Implementation would fetch from position tracker
        return 0.0
    
    async def update_user_capital(self, user_id: str, capital: float):
        """Update user's capital"""
        self.user_capital[user_id] = capital
    
    async def update_user_margin(self, user_id: str, margin: float):
        """Update user's available margin"""
        self.user_margin[user_id] = margin 
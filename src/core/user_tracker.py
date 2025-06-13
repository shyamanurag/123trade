"""
User-specific Order and Position Tracking
Manages user-specific order and position tracking with Redis
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class UserTracker:
    """Tracks user-specific orders and positions"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis = redis.from_url(config['redis_url'])
        
    async def track_order(self, user_id: str, order_data: Dict):
        """Track a new order"""
        try:
            # Store order data
            await self.redis.hset(
                f"user:{user_id}:orders",
                order_data['order_id'],
                json.dumps({
                    **order_data,
                    'tracked_at': datetime.now().isoformat()
                })
            )
            
            # Add to user's active orders
            if order_data['status'] in ['PENDING', 'OPEN']:
                await self.redis.sadd(f"user:{user_id}:active_orders", order_data['order_id'])
                
            # Add to daily orders
            date_key = datetime.now().strftime('%Y%m%d')
            await self.redis.sadd(f"user:{user_id}:orders:{date_key}", order_data['order_id'])
            
            logger.info(f"Order tracked for user {user_id}: {order_data['order_id']}")
            
        except Exception as e:
            logger.error(f"Failed to track order for user {user_id}: {e}")
            
    async def update_order(self, user_id: str, order_id: str, update_data: Dict):
        """Update order status"""
        try:
            # Get existing order
            order_data = await self.redis.hget(f"user:{user_id}:orders", order_id)
            if not order_data:
                logger.warning(f"Order {order_id} not found for user {user_id}")
                return
                
            # Update order data
            order = json.loads(order_data)
            order.update(update_data)
            order['updated_at'] = datetime.now().isoformat()
            
            # Store updated order
            await self.redis.hset(
                f"user:{user_id}:orders",
                order_id,
                json.dumps(order)
            )
            
            # Update active orders set
            if update_data['status'] in ['FILLED', 'CANCELLED', 'REJECTED']:
                await self.redis.srem(f"user:{user_id}:active_orders", order_id)
                
            logger.info(f"Order updated for user {user_id}: {order_id}")
            
        except Exception as e:
            logger.error(f"Failed to update order for user {user_id}: {e}")
            
    async def track_position(self, user_id: str, position_data: Dict):
        """Track a new position"""
        try:
            # Store position data
            await self.redis.hset(
                f"user:{user_id}:positions",
                position_data['symbol'],
                json.dumps({
                    **position_data,
                    'tracked_at': datetime.now().isoformat()
                })
            )
            
            # Add to user's active positions
            if position_data['quantity'] != 0:
                await self.redis.sadd(f"user:{user_id}:active_positions", position_data['symbol'])
                
            # Add to daily positions
            date_key = datetime.now().strftime('%Y%m%d')
            await self.redis.sadd(f"user:{user_id}:positions:{date_key}", position_data['symbol'])
            
            logger.info(f"Position tracked for user {user_id}: {position_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to track position for user {user_id}: {e}")
            
    async def update_position(self, user_id: str, symbol: str, update_data: Dict):
        """Update position"""
        try:
            # Get existing position
            position_data = await self.redis.hget(f"user:{user_id}:positions", symbol)
            if not position_data:
                logger.warning(f"Position {symbol} not found for user {user_id}")
                return
                
            # Update position data
            position = json.loads(position_data)
            position.update(update_data)
            position['updated_at'] = datetime.now().isoformat()
            
            # Store updated position
            await self.redis.hset(
                f"user:{user_id}:positions",
                symbol,
                json.dumps(position)
            )
            
            # Update active positions set
            if update_data['quantity'] == 0:
                await self.redis.srem(f"user:{user_id}:active_positions", symbol)
                
            logger.info(f"Position updated for user {user_id}: {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to update position for user {user_id}: {e}")
            
    async def get_user_orders(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Get user's orders"""
        try:
            # Get all orders
            orders = await self.redis.hgetall(f"user:{user_id}:orders")
            
            # Filter by status if specified
            if status:
                return [
                    json.loads(order_data)
                    for order_data in orders.values()
                    if json.loads(order_data)['status'] == status
                ]
            
            return [json.loads(order_data) for order_data in orders.values()]
            
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            return []
            
    async def get_user_positions(self, user_id: str, active_only: bool = False) -> List[Dict]:
        """Get user's positions"""
        try:
            if active_only:
                # Get only active positions
                active_symbols = await self.redis.smembers(f"user:{user_id}:active_positions")
                positions = []
                for symbol in active_symbols:
                    position_data = await self.redis.hget(f"user:{user_id}:positions", symbol)
                    if position_data:
                        positions.append(json.loads(position_data))
                return positions
            else:
                # Get all positions
                positions = await self.redis.hgetall(f"user:{user_id}:positions")
                return [json.loads(position_data) for position_data in positions.values()]
            
        except Exception as e:
            logger.error(f"Failed to get positions for user {user_id}: {e}")
            return []
            
    async def get_user_daily_summary(self, user_id: str, date: Optional[str] = None) -> Dict:
        """Get user's daily trading summary"""
        try:
            date_key = date or datetime.now().strftime('%Y%m%d')
            
            # Get daily orders
            order_ids = await self.redis.smembers(f"user:{user_id}:orders:{date_key}")
            orders = []
            for order_id in order_ids:
                order_data = await self.redis.hget(f"user:{user_id}:orders", order_id)
                if order_data:
                    orders.append(json.loads(order_data))
                    
            # Get daily positions
            position_symbols = await self.redis.smembers(f"user:{user_id}:positions:{date_key}")
            positions = []
            for symbol in position_symbols:
                position_data = await self.redis.hget(f"user:{user_id}:positions", symbol)
                if position_data:
                    positions.append(json.loads(position_data))
                    
            # Calculate summary
            total_trades = len(orders)
            filled_trades = len([o for o in orders if o['status'] == 'FILLED'])
            total_volume = sum(o['quantity'] for o in orders if o['status'] == 'FILLED')
            total_pnl = sum(p['pnl'] for p in positions)
            
            return {
                'date': date_key,
                'total_trades': total_trades,
                'filled_trades': filled_trades,
                'total_volume': total_volume,
                'total_pnl': total_pnl,
                'orders': orders,
                'positions': positions
            }
            
        except Exception as e:
            logger.error(f"Failed to get daily summary for user {user_id}: {e}")
            return {
                'date': date_key,
                'total_trades': 0,
                'filled_trades': 0,
                'total_volume': 0,
                'total_pnl': 0,
                'orders': [],
                'positions': []
            }
            
    async def cleanup_old_data(self, user_id: str, days_to_keep: int = 30):
        """Clean up old order and position data"""
        try:
            current_date = datetime.now()
            cutoff_date = current_date - timedelta(days=days_to_keep)
            
            # Clean up old orders
            async for key in self.redis.scan_iter(f"user:{user_id}:orders:*"):
                date_str = key.split(':')[-1]
                try:
                    date = datetime.strptime(date_str, '%Y%m%d')
                    if date < cutoff_date:
                        await self.redis.delete(key)
                except ValueError:
                    continue
                    
            # Clean up old positions
            async for key in self.redis.scan_iter(f"user:{user_id}:positions:*"):
                date_str = key.split(':')[-1]
                try:
                    date = datetime.strptime(date_str, '%Y%m%d')
                    if date < cutoff_date:
                        await self.redis.delete(key)
                except ValueError:
                    continue
                    
            logger.info(f"Cleaned up old data for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data for user {user_id}: {e}") 
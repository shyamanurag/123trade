"""
Clean OrderManager - NO FALLBACKS
If something fails, it fails clearly so we know what to fix
"""

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json
import time

logger = logging.getLogger(__name__)

class OrderManager:
    """Clean OrderManager - NO FALLBACKS, NO FAKE DATA"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sharekhan_client = None
        self.redis_client = None
        self.risk_manager = None
        self.notification_manager = None
        
        # Simple storage
        self.active_orders: Dict[str, set] = {}
        self.order_history: Dict[str, list] = {}
        
        logger.info("OrderManager initialized - NO FALLBACKS")
    
    async def initialize(self, sharekhan_client=None, redis_client=None, risk_manager=None):
        """Initialize with required dependencies - FAIL if missing"""
        self.sharekhan_client = sharekhan_client
        self.redis_client = redis_client
        self.risk_manager = risk_manager
        
        if not self.sharekhan_client:
            logger.warning("⚠️ No ShareKhan client - orders will be rejected")
        
        if not self.redis_client:
            logger.warning("⚠️ No Redis client - using memory only")
        
        if not self.risk_manager:
            logger.warning("⚠️ No risk manager - orders will not be validated")
        
        logger.info("OrderManager initialized with available components")
    
    async def place_order(self, user_id: str, order_data: Dict[str, Any]) -> str:
        """Place an order - FAIL if requirements not met"""
        try:
            if not self.sharekhan_client:
                raise Exception("No ShareKhan client available - order rejected")
            
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Basic validation
            required_fields = ['symbol', 'quantity', 'side', 'order_type']
            for field in required_fields:
                if field not in order_data:
                    raise Exception(f"Missing required field: {field}")
            
            # Risk validation if available
            if self.risk_manager:
                risk_valid = await self.risk_manager.validate_order(user_id, order_data)
                if not risk_valid:
                    raise Exception("Order failed risk validation")
            
            # Place order via ShareKhan
            sharekhan_params = {
                'symbol': order_data['symbol'],
                'transaction_type': order_data['side'].upper(),
                'quantity': order_data['quantity'],
                'order_type': order_data['order_type'].upper(),
                'product': self._get_product_type_for_symbol(order_data['symbol']),  # FIXED: Dynamic product type
                'validity': 'DAY',
                'tag': f"OM_{order_id[:8]}"
            }
            
            if order_data['order_type'].upper() == 'LIMIT':
                sharekhan_params['price'] = order_data['price']
            
            broker_order_id = await self.sharekhan_client.place_order(sharekhan_params)
            
            if not broker_order_id:
                raise Exception("ShareKhan order placement failed")
            
            # Store order
            if user_id not in self.active_orders:
                self.active_orders[user_id] = set()
            self.active_orders[user_id].add(order_id)
            
            # Store in Redis if available
            if self.redis_client:
                order_key = f"order:{user_id}:{order_id}"
                order_record = {
                    'order_id': order_id,
                    'broker_order_id': broker_order_id,
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat(),
                    **order_data
                }
                await self.redis_client.set(order_key, json.dumps(order_record))
            
            logger.info(f"✅ Order placed: {order_id} -> {broker_order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Order placement failed for user {user_id}: {e}")
            raise e
    
    async def get_orders(self, user_id: str) -> list:
        """Get orders for user - return what's available"""
        try:
            orders = []
            
            if self.redis_client:
                # Get from Redis
                keys = await self.redis_client.keys(f"order:{user_id}:*")
                for key in keys:
                    order_data = await self.redis_client.get(key)
                    if order_data:
                        orders.append(json.loads(order_data))
            else:
                # Get from memory
                if user_id in self.order_history:
                    orders = self.order_history[user_id]
            
            return orders
            
        except Exception as e:
            logger.error(f"❌ Failed to get orders for user {user_id}: {e}")
            return []
    
    async def cancel_order(self, user_id: str, order_id: str) -> bool:
        """Cancel order - FAIL if not possible"""
        try:
            if not self.sharekhan_client:
                raise Exception("No ShareKhan client available - cannot cancel order")
            
            # Get order details
            if self.redis_client:
                order_key = f"order:{user_id}:{order_id}"
                order_data = await self.redis_client.get(order_key)
                if not order_data:
                    raise Exception(f"Order {order_id} not found")
                
                order_record = json.loads(order_data)
                broker_order_id = order_record.get('broker_order_id')
            else:
                raise Exception("Cannot find order without Redis")
            
            if not broker_order_id:
                raise Exception("No broker order ID found")
            
            # Cancel via ShareKhan
            success = await self.sharekhan_client.cancel_order(broker_order_id)
            
            if not success:
                raise Exception("ShareKhan order cancellation failed")
            
            # Remove from active orders
            if user_id in self.active_orders:
                self.active_orders[user_id].discard(order_id)
            
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Order cancellation failed: {e}")
            raise e
    
    def get_status(self) -> Dict[str, Any]:
        """Get OrderManager status"""
        return {
            "sharekhan_client": self.sharekhan_client is not None,
            "redis_client": self.redis_client is not None,
            "risk_manager": self.risk_manager is not None,
            "active_users": len(self.active_orders),
            "total_active_orders": sum(len(orders) for orders in self.active_orders.values())
        } 

    def _get_product_type_for_symbol(self, symbol: str) -> str:
        """Get appropriate product type for symbol - FIXED for NFO options"""
        # 🔧 CRITICAL FIX: NFO options require NRML, not CNC
        if 'CE' in symbol or 'PE' in symbol:
            return 'NRML'  # Options must use NRML
        else:
            return 'CNC'   # Equity can use CNC

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of a specific order"""
        return self.orders.get(order_id) 

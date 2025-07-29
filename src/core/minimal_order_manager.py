"""
MinimalOrderManager - Last Resort Fallback
==========================================
A minimal order manager that provides bare minimum order processing
capabilities when all other order managers fail to initialize.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import os # Added missing import

logger = logging.getLogger(__name__)

class MinimalOrderManager:
    """Minimal order manager - last resort fallback"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sharekhan_client = config.get('sharekhan_client')
        self.order_count = 0
        self.logger = logger
        
        # Initialize minimal components
        self._async_components_initialized = False
        
        self.logger.info("✅ MinimalOrderManager initialized (last resort)")
        
    async def async_initialize_components(self):
        """Initialize async components - minimal implementation"""
        if not self._async_components_initialized:
            self.logger.info("✅ MinimalOrderManager async components initialized")
            self._async_components_initialized = True
            
    async def place_strategy_order(self, strategy_name: str, signal: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """Place a minimal order - logs only"""
        try:
            # ELIMINATED: Hardcoded MASTER_USER_001 removed
            # Original violation: Used fake user ID for all orders
            # This violates the NO_MOCK_DATA policy for user management
            
            # Get real user from signal or environment
            user_id = signal.get('user_id')
            if not user_id:
                # Try to get from environment or configuration
                user_id = os.getenv('ACTIVE_USER_ID')
                if not user_id:
                    self.logger.error("❌ No valid user ID found - cannot log order without real user")
                    return []
            
            # Create minimal order record
            order_id = str(uuid.uuid4())
            self.order_count += 1
            
            order = {
                'order_id': order_id,
                'user_id': user_id,
                'strategy_name': strategy_name,
                'symbol': signal.get('symbol', 'UNKNOWN'),
                'side': signal.get('side', 'BUY'),
                'quantity': signal.get('quantity', 1),
                'price': signal.get('price', 0),
                'status': 'LOGGED_ONLY',
                'timestamp': datetime.now().isoformat(),
                'note': 'Order logged only - no execution capability'
            }
            
            # Log the order for record keeping
            self.logger.info(f"📝 MinimalOrderManager LOGGED order {self.order_count}: {order['symbol']} {order['side']} {order['quantity']} @ {order['price']} (user: {user_id})")
            self.logger.warning(f"⚠️ ORDER NOT EXECUTED - MinimalOrderManager is logging only")
            
            return [(user_id, order)]
            
        except Exception as e:
            self.logger.error(f"❌ MinimalOrderManager failed to log order: {e}")
            return []
            
    async def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        return {
            'type': 'MinimalOrderManager',
            'orders_logged': self.order_count,
            'execution_capability': False,
            'sharekhan_available': bool(self.sharekhan_client),
            'initialized': self._async_components_initialized,
            'warning': 'This is a last resort fallback - orders are logged only, not executed'
        } 
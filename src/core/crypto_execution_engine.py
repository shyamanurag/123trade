"""
Crypto Execution Engine
Handles order execution for crypto trading with real Binance integration
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"

class CryptoExecutionEngine:
    """Real crypto execution engine with Binance integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_initialized = False
        self.binance_client = None
        self.active_orders: Dict[str, Dict] = {}
        
    async def initialize(self) -> bool:
        """Initialize the execution engine"""
        try:
            logger.info("🔧 Initializing Crypto Execution Engine...")
            
            # Initialize Binance client
            from src.data.binance_client import BinanceClient
            self.binance_client = BinanceClient()
            await self.binance_client.initialize()
            
            self.is_initialized = True
            logger.info("✅ Crypto Execution Engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize execution engine: {e}")
            return False
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Place a real order on Binance"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Execution engine not initialized")
            
            order_data = {
                'symbol': symbol,
                'side': side.value,
                'type': order_type.value,
                'quantity': str(quantity)
            }
            
            if price and order_type == OrderType.LIMIT:
                order_data['price'] = str(price)
            
            # Execute on Binance testnet
            result = await self.binance_client.place_order(**order_data)
            
            # Store order locally
            order_id = result.get('orderId', str(datetime.now().timestamp()))
            self.active_orders[order_id] = {
                **result,
                'local_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Order placed: {symbol} {side.value} {quantity}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            result = await self.binance_client.cancel_order(symbol, order_id)
            
            if order_id in self.active_orders:
                self.active_orders[order_id]['status'] = OrderStatus.CANCELED.value
            
            logger.info(f"✅ Order canceled: {order_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Order cancellation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get status of an order"""
        try:
            if self.binance_client:
                return await self.binance_client.get_order_status(symbol, order_id)
            else:
                return self.active_orders.get(order_id, {})
                
        except Exception as e:
            logger.error(f"❌ Failed to get order status: {e}")
            return {'error': str(e)}
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            if self.binance_client:
                return await self.binance_client.get_account_info()
            else:
                return {'error': 'Binance client not available'}
                
        except Exception as e:
            logger.error(f"❌ Failed to get account info: {e}")
            return {'error': str(e)}
    
    def get_active_orders(self) -> Dict[str, Dict]:
        """Get all active orders"""
        return self.active_orders.copy()
    
    async def stop(self):
        """Stop the execution engine"""
        logger.info("🛑 Stopping Crypto Execution Engine...")
        if self.binance_client:
            await self.binance_client.close()
        self.is_initialized = False
        logger.info("✅ Crypto Execution Engine stopped")

# Alias for backwards compatibility
QuantumExecutionEngine = CryptoExecutionEngine 
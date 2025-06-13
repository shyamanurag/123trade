from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime
from collections import deque

from ..models.schema import Order, OrderStatus, OrderType
from ..core.order_manager import OrderManager
from ..core.risk_manager import RiskManager
from ..core.position_tracker import PositionTracker

logger = logging.getLogger(__name__)

class TradeExecutionQueue:
    def __init__(
        self,
        order_manager: OrderManager,
        risk_manager: RiskManager,
        position_tracker: PositionTracker,
        max_queue_size: int = 1000
    ):
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        
        # Queue for pending orders
        self.pending_orders: deque[Order] = deque(maxlen=max_queue_size)
        
        # Queue for high priority orders (e.g., stop losses)
        self.priority_orders: deque[Order] = deque(maxlen=max_queue_size)
        
        # Lock for queue operations
        self.queue_lock = asyncio.Lock()
        
        # Event for queue processing
        self.processing_event = asyncio.Event()
        
        # Start queue processing
        asyncio.create_task(self._process_queue())
        
    async def add_order(self, order: Order, priority: bool = False):
        """Add order to execution queue"""
        async with self.queue_lock:
            if priority:
                self.priority_orders.append(order)
            else:
                self.pending_orders.append(order)
                
            # Signal queue processing
            self.processing_event.set()
            
        logger.info(f"Added order {order.order_id} to {'priority' if priority else 'pending'} queue")
        
    async def process_order_update(self, update: Dict):
        """Process order status update"""
        order_id = update.get("order_id")
        new_status = update.get("status")
        
        if not order_id or not new_status:
            logger.error("Invalid order update received")
            return
            
        # Update order status in queues
        async with self.queue_lock:
            # Check priority queue
            for order in self.priority_orders:
                if order.order_id == order_id:
                    order.status = OrderStatus(new_status)
                    break
                    
            # Check pending queue
            for order in self.pending_orders:
                if order.order_id == order_id:
                    order.status = OrderStatus(new_status)
                    break
                    
        logger.info(f"Updated order {order_id} status to {new_status}")
        
    async def _process_queue(self):
        """Process orders in queue"""
        while True:
            try:
                # Wait for processing signal
                await self.processing_event.wait()
                
                # Process priority orders first
                await self._process_priority_orders()
                
                # Process pending orders
                await self._process_pending_orders()
                
                # Clear processing event
                self.processing_event.clear()
                
            except Exception as e:
                logger.error(f"Error processing order queue: {str(e)}")
                
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
            
    async def _process_priority_orders(self):
        """Process high priority orders"""
        async with self.queue_lock:
            while self.priority_orders:
                order = self.priority_orders[0]
                
                # Check if order can be executed
                if await self._can_execute_order(order):
                    # Execute order
                    await self._execute_order(order)
                    
                    # Remove from queue
                    self.priority_orders.popleft()
                else:
                    # Skip to next order
                    break
                    
    async def _process_pending_orders(self):
        """Process regular pending orders"""
        async with self.queue_lock:
            while self.pending_orders:
                order = self.pending_orders[0]
                
                # Check if order can be executed
                if await self._can_execute_order(order):
                    # Execute order
                    await self._execute_order(order)
                    
                    # Remove from queue
                    self.pending_orders.popleft()
                else:
                    # Skip to next order
                    break
                    
    async def _can_execute_order(self, order: Order) -> bool:
        """Check if order can be executed"""
        try:
            # Check risk limits
            risk_check = await self.risk_manager.check_order_risk(order)
            if not risk_check["allowed"]:
                logger.warning(f"Order {order.order_id} rejected by risk check: {risk_check['reason']}")
                return False
                
            # Check position limits
            position_check = await self.position_tracker.check_position_limits(order)
            if not position_check["allowed"]:
                logger.warning(f"Order {order.order_id} rejected by position check: {position_check['reason']}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking order execution: {str(e)}")
            return False
            
    async def _execute_order(self, order: Order):
        """Execute order"""
        try:
            # Execute order through order manager
            result = await self.order_manager.execute_order(order)
            
            if result["status"] == "FILLED":
                logger.info(f"Order {order.order_id} executed successfully")
            else:
                logger.warning(f"Order {order.order_id} execution failed: {result.get('reason')}")
                
        except Exception as e:
            logger.error(f"Error executing order {order.order_id}: {str(e)}")
            
    async def get_queue_status(self) -> Dict:
        """Get current queue status"""
        async with self.queue_lock:
            return {
                "priority_queue_size": len(self.priority_orders),
                "pending_queue_size": len(self.pending_orders),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def clear_queue(self):
        """Clear all orders from queue"""
        async with self.queue_lock:
            self.priority_orders.clear()
            self.pending_orders.clear()
            
        logger.info("Order queue cleared") 
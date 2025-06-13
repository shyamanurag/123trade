"""
Resilient Zerodha Connection
Manages resilient connection to Zerodha broker with automatic recovery
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import time

from ..core.connection_manager import ResilientConnection
from .zerodha import ZerodhaIntegration

logger = logging.getLogger(__name__)

class ResilientZerodhaConnection(ResilientConnection):
    """Resilient connection wrapper for Zerodha broker"""
    
    def __init__(self, broker: ZerodhaIntegration, config: Dict):
        super().__init__(config)
        self.broker = broker
        self._last_order_time = None
        self._order_rate_limit = config.get('order_rate_limit', 1.0)  # orders per second
        self._order_semaphore = asyncio.Semaphore(1)
        self._ws_reconnect_delay = config.get('ws_reconnect_delay', 5)
        self._ws_max_reconnect_attempts = config.get('ws_max_reconnect_attempts', 10)
        self._ws_reconnect_attempts = 0
        self._ws_last_reconnect = None
    
    async def _connect_impl(self) -> None:
        """Establish connection to Zerodha"""
        try:
            await self.broker.initialize()
            
            # Verify connection by fetching account details
            account_info = await self.broker.get_account_info()
            if not account_info:
                raise ConnectionError("Failed to fetch account information")
                
            # Set up WebSocket reconnection monitoring
            asyncio.create_task(self._monitor_websocket())
            
        except Exception as e:
            logger.error(f"Failed to establish connection: {e}")
            raise
    
    async def _disconnect_impl(self) -> None:
        """Disconnect from Zerodha"""
        try:
            await self.broker.disconnect()
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")
    
    async def _health_check_impl(self) -> bool:
        """Check Zerodha connection health"""
        try:
            # Check if we can fetch account info
            account_info = await self.broker.get_account_info()
            if not account_info:
                return False
                
            # Check WebSocket connection
            if not self.broker.ticker_connected:
                return False
                
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _monitor_websocket(self):
        """Monitor WebSocket connection and handle reconnection"""
        while True:
            try:
                if not self.broker.ticker_connected:
                    current_time = time.time()
                    
                    # Check if we should attempt reconnection
                    if (self._ws_last_reconnect is None or 
                        current_time - self._ws_last_reconnect >= self._ws_reconnect_delay):
                        
                        if self._ws_reconnect_attempts < self._ws_max_reconnect_attempts:
                            logger.info(f"Attempting WebSocket reconnection (attempt {self._ws_reconnect_attempts + 1})")
                            await self.broker._initialize_websocket()
                            self._ws_reconnect_attempts += 1
                            self._ws_last_reconnect = current_time
                        else:
                            logger.error("Max WebSocket reconnection attempts reached")
                            # Reset attempts after a longer delay
                            await asyncio.sleep(self._ws_reconnect_delay * 2)
                            self._ws_reconnect_attempts = 0
                
                # Reset reconnection attempts if connection is stable
                if self.broker.ticker_connected:
                    self._ws_reconnect_attempts = 0
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in WebSocket monitoring: {e}")
                await asyncio.sleep(1)
    
    async def place_order(self, order_params: Dict) -> Dict:
        """Place order with rate limiting and retry"""
        async with self._order_semaphore:
            # Rate limiting
            if self._last_order_time:
                elapsed = time.time() - self._last_order_time
                if elapsed < self._order_rate_limit:
                    await asyncio.sleep(self._order_rate_limit - elapsed)
            
            try:
                order = await self.execute(
                    self.broker.place_order,
                    order_params
                )
                self._last_order_time = time.time()
                return order
            except Exception as e:
                logger.error(f"Failed to place order: {e}")
                raise
    
    async def modify_order(self, order_id: str, order_params: Dict) -> Dict:
        """Modify order with retry"""
        return await self.execute(
            self.broker.modify_order,
            order_id,
            order_params
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order with retry"""
        return await self.execute(
            self.broker.cancel_order,
            order_id
        )
    
    async def get_order_status(self, order_id: str) -> Dict:
        """Get order status with retry"""
        return await self.execute(
            self.broker.get_order_status,
            order_id
        )
    
    async def get_positions(self) -> Dict:
        """Get positions with retry"""
        return await self.execute(
            self.broker.get_positions
        )
    
    async def get_holdings(self) -> Dict:
        """Get holdings with retry"""
        return await self.execute(
            self.broker.get_holdings
        )
    
    async def get_margins(self) -> Dict:
        """Get margins with retry"""
        return await self.execute(
            self.broker.get_margins
        )
    
    @property
    def connection_status(self) -> Dict:
        """Get detailed connection status"""
        status = super().connection_status
        status.update({
            'broker': 'zerodha',
            'order_rate_limit': self._order_rate_limit,
            'last_order_time': self._last_order_time,
            'ws_connected': self.broker.ticker_connected,
            'ws_reconnect_attempts': self._ws_reconnect_attempts,
            'ws_last_reconnect': self._ws_last_reconnect
        })
        return status 
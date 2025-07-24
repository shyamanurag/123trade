"""
Connection resilience patterns with automatic recovery
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp
from collections import deque

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"

@dataclass
class ConnectionHealth:
    state: ConnectionState
    last_connected: Optional[datetime]
    last_error: Optional[str]
    reconnect_attempts: int
    latency_ms: float
    uptime_seconds: float

class ResilientConnection:
    """Base class for resilient connections with automatic recovery"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        
        # Connection parameters
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        self.reconnect_delay = config.get('reconnect_delay', 5)
        self.exponential_backoff = config.get('exponential_backoff', True)
        self.health_check_interval = config.get('health_check_interval', 30)
        
        # State tracking
        self.state = ConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        self.last_connected = None
        self.last_error = None
        self.connection_start = None
        
        # Callbacks
        self.on_connect_callbacks = []
        self.on_disconnect_callbacks = []
        self.on_error_callbacks = []
        
        # Health monitoring
        self.latency_history = deque(maxlen=100)
        self.health_check_task = None

    async def connect(self):
        """Connect with automatic retry logic"""
        self.state = ConnectionState.CONNECTING
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Attempting to connect {self.name}...")
                
                # Implement in subclass
                await self._do_connect()
                
                # Success
                self.state = ConnectionState.CONNECTED
                self.last_connected = datetime.now()
                self.connection_start = datetime.now()
                self.reconnect_attempts = 0
                
                # Start health monitoring
                self.health_check_task = asyncio.create_task(self._health_check_loop())
                
                # Notify callbacks
                await self._notify_connect()
                
                logger.info(f"{self.name} connected successfully")
                return True
                
            except Exception as e:
                self.last_error = str(e)
                self.reconnect_attempts += 1
                
                logger.error(f"{self.name} connection failed: {e}")
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    self.state = ConnectionState.FAILED
                    await self._notify_error(e)
                    return False
                
                # Calculate backoff delay
                delay = self._calculate_backoff_delay()
                logger.info(f"Retrying {self.name} connection in {delay}s...")
                
                await asyncio.sleep(delay)
                self.state = ConnectionState.RECONNECTING
        
        return False

    async def disconnect(self):
        """Graceful disconnection"""
        if self.state == ConnectionState.CONNECTED:
            try:
                # Cancel health check
                if self.health_check_task:
                    self.health_check_task.cancel()
                
                # Implement in subclass
                await self._do_disconnect()
                
                self.state = ConnectionState.DISCONNECTED
                await self._notify_disconnect()
                
                logger.info(f"{self.name} disconnected")
                
            except Exception as e:
                logger.error(f"Error disconnecting {self.name}: {e}")

    async def ensure_connected(self):
        """Ensure connection is active, reconnect if needed"""
        if self.state != ConnectionState.CONNECTED:
            return await self.connect()
        
        # Verify connection is actually alive
        if not await self._check_connection_alive():
            logger.warning(f"{self.name} connection lost, reconnecting...")
            self.state = ConnectionState.DISCONNECTED
            return await self.connect()
        
        return True

    async def _health_check_loop(self):
        """Continuous health monitoring"""
        while self.state == ConnectionState.CONNECTED:
            try:
                # Measure latency
                start = datetime.now()
                is_healthy = await self._check_connection_alive()
                latency = (datetime.now() - start).total_seconds() * 1000
                
                self.latency_history.append(latency)
                
                if not is_healthy:
                    logger.warning(f"{self.name} health check failed")
                    await self.ensure_connected()
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{self.name} health check error: {e}")

    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        if not self.exponential_backoff:
            return self.reconnect_delay
        
        # Exponential backoff with jitter
        base_delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        max_delay = 300  # 5 minutes max
        delay = min(base_delay, max_delay)
        
        # Add jitter (±20%)
        import random
        jitter = delay * 0.2 * (2 * random.random() - 1)
        
        return max(1, delay + jitter)

    def get_health(self) -> ConnectionHealth:
        """Get connection health status"""
        uptime = 0
        if self.connection_start and self.state == ConnectionState.CONNECTED:
            uptime = (datetime.now() - self.connection_start).total_seconds()
        
        avg_latency = 0
        if self.latency_history:
            avg_latency = sum(self.latency_history) / len(self.latency_history)
        
        return ConnectionHealth(
            state=self.state,
            last_connected=self.last_connected,
            last_error=self.last_error,
            reconnect_attempts=self.reconnect_attempts,
            latency_ms=avg_latency,
            uptime_seconds=uptime
        )

    # Abstract methods to implement in subclasses
    async def _do_connect(self):
        """Actual connection logic - implement in subclass"""
        raise NotImplementedError

    async def _do_disconnect(self):
        """Actual disconnection logic - implement in subclass"""
        raise NotImplementedError

    async def _check_connection_alive(self) -> bool:
        """Check if connection is alive - implement in subclass"""
        raise NotImplementedError

    # Callback management
    def on_connect(self, callback: Callable):
        """Register connection callback"""
        self.on_connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable):
        """Register disconnection callback"""
        self.on_disconnect_callbacks.append(callback)

    def on_error(self, callback: Callable):
        """Register error callback"""
        self.on_error_callbacks.append(callback)

    async def _notify_connect(self):
        """Notify connection callbacks"""
        for callback in self.on_connect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Connection callback error: {e}")

    async def _notify_disconnect(self):
        """Notify disconnection callbacks"""
        for callback in self.on_disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Disconnection callback error: {e}")

    async def _notify_error(self, error: Exception):
        """Notify error callbacks"""
        for callback in self.on_error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}") 
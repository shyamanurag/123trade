"""
Event system for trading application
"""

from enum import Enum
from typing import Any, Dict, Callable, List
import asyncio
import logging

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Trading event types"""
    ORDER_FILLED = "order_filled"
    POSITION_ADDED = "position_added"
    POSITION_UPDATED = "position_updated"
    POSITION_CLOSED = "position_closed"
    MARKET_DATA = "market_data"
    TRADE_SIGNAL = "trade_signal"
    SYSTEM_ALERT = "system_alert"

class TradingEvent:
    """Trading event with type and data"""
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = asyncio.get_event_loop().time()

class EventBus:
    """Event bus for publishing and subscribing to events"""
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the event bus"""
        # EventBus doesn't need special initialization, but orchestrator expects this method
        pass

    async def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    async def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type"""
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(callback)

    async def publish(self, event: TradingEvent):
        """Publish an event to all subscribers"""
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}") 
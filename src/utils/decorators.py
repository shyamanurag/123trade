"""
Decorators for the trading system
"""

import asyncio
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def synchronized_state(func: Callable) -> Callable:
    """
    Decorator to ensure thread-safe state modifications.
    Uses asyncio.Lock to synchronize access to shared state.
    """
    @functools.wraps(func)
    async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        if not hasattr(self, '_lock'):
            logger.warning(f"Class {self.__class__.__name__} missing _lock attribute")
            return await func(self, *args, **kwargs)
        
        async with self._lock:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in synchronized operation: {e}")
                raise
    return wrapper 
"""
Async utilities for handling CPU-bound operations and coroutines
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps
from typing import Any, Callable, TypeVar, Optional, Dict
import time

logger = logging.getLogger(__name__)

# Global executors
thread_pool = ThreadPoolExecutor(max_workers=10)
process_pool = ProcessPoolExecutor(max_workers=4)

T = TypeVar('T')

def ensure_coroutine(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure a function is properly awaited"""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in coroutine {func.__name__}: {e}")
            raise
    return wrapper

async def run_cpu_bound(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run CPU-bound function in process pool"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            process_pool,
            lambda: func(*args, **kwargs)
        )
    except Exception as e:
        logger.error(f"Error in CPU-bound task {func.__name__}: {e}")
        raise

async def run_io_bound(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run IO-bound function in thread pool"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            thread_pool,
            lambda: func(*args, **kwargs)
        )
    except Exception as e:
        logger.error(f"Error in IO-bound task {func.__name__}: {e}")
        raise

class AsyncTaskManager:
    """Manages async tasks with proper cleanup"""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        
    async def start_task(self, name: str, coro: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Start a new task with proper error handling"""
        if name in self._tasks and not self._tasks[name].done():
            logger.warning(f"Task {name} already running")
            return
            
        task = asyncio.create_task(coro(*args, **kwargs))
        self._tasks[name] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task {name} was cancelled")
        except Exception as e:
            logger.error(f"Task {name} failed: {e}")
            raise
            
    async def stop_task(self, name: str) -> None:
        """Stop a running task"""
        if name in self._tasks:
            task = self._tasks[name]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._tasks[name]
            
    async def stop_all(self) -> None:
        """Stop all running tasks"""
        for name in list(self._tasks.keys()):
            await self.stop_task(name)
            
    def is_running(self, name: str) -> bool:
        """Check if a task is running"""
        return name in self._tasks and not self._tasks[name].done()

async def cleanup() -> None:
    """Cleanup executors"""
    thread_pool.shutdown(wait=True)
    process_pool.shutdown(wait=True) 
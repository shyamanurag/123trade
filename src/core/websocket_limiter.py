"""
WebSocket rate limiting and circuit breaker implementation
"""
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
        
    async def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed under rate limiting"""
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Clean old requests
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                if req_time > window_start]
            
            # Check if under limit
            if len(self.requests[key]) < self.max_requests:
                self.requests[key].append(now)
                return True
            return False
            
    def check(self, key: str) -> bool:
        """Synchronous check for rate limiting (for use in FastAPI dependencies)"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                            if req_time > window_start]
        
        # Check if under limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        return False
            
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window"""
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Clean old requests
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                if req_time > window_start]
            
            return max(0, self.max_requests - len(self.requests[key]))

class CircuitBreaker:
    def __init__(self, threshold: int, timeout_seconds: int):
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failures: Dict[str, int] = defaultdict(int)
        self.last_failure: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        
    async def record_success(self, key: str):
        """Record a successful operation"""
        async with self._lock:
            self.failures[key] = 0
            if key in self.last_failure:
                del self.last_failure[key]
                
    async def record_failure(self, key: str):
        """Record a failed operation"""
        async with self._lock:
            self.failures[key] += 1
            self.last_failure[key] = datetime.now()
            
    async def is_allowed(self, key: str) -> bool:
        """Check if operation is allowed under circuit breaker"""
        async with self._lock:
            if key not in self.failures:
                return True
                
            if self.failures[key] < self.threshold:
                return True
                
            if key in self.last_failure:
                time_since_last_failure = (datetime.now() - self.last_failure[key]).total_seconds()
                if time_since_last_failure >= self.timeout_seconds:
                    # Reset after timeout
                    self.failures[key] = 0
                    del self.last_failure[key]
                    return True
                    
            return False
            
    def is_open(self) -> bool:
        """Synchronous check if circuit breaker is open (for use in FastAPI dependencies)"""
        for key in self.failures:
            if self.failures[key] >= self.threshold:
                if key in self.last_failure:
                    time_since_last_failure = (datetime.now() - self.last_failure[key]).total_seconds()
                    if time_since_last_failure < self.timeout_seconds:
                        return True
        return False
            
    async def get_status(self, key: str) -> Dict[str, Any]:
        """Get circuit breaker status for a key"""
        async with self._lock:
            return {
                'failures': self.failures.get(key, 0),
                'threshold': self.threshold,
                'last_failure': self.last_failure.get(key),
                'is_open': not await self.is_allowed(key)
            } 
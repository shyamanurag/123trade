"""
Rate Limiter Middleware
Provides configurable rate limiting to protect API endpoints from abuse and excessive traffic.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import ipaddress

from fastapi import Request, Response, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging_config import get_logger

# Try to use redis for distributed rate limiting if available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = get_logger(__name__)

# Cache for in-memory rate limiting
# Structure: {ip_or_key: {endpoint: [(timestamp, count)]}}
RATE_LIMIT_CACHE: Dict[str, Dict[str, List[tuple]]] = {}

class RateLimitConfig:
    """Configuration for rate limiting"""
    
    def __init__(self, 
                 limit: int = 60,
                 period: int = 60,
                 redis_client: Optional[redis.Redis] = None,
                 redis_prefix: str = "ratelimit:",
                 exempt_ips: List[str] = None,
                 exempt_paths: List[str] = None,
                 burst_multiplier: float = 2.0,
                 block_duration: int = 300,
                 strict_ip_check: bool = True,
                 header_name: str = "X-RateLimit"):
        """
        Initialize rate limit configuration.
        
        Args:
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            redis_client: Optional Redis client for distributed rate limiting
            redis_prefix: Prefix for Redis keys
            exempt_ips: List of IPs exempt from rate limiting (CIDR notation supported)
            exempt_paths: List of URL paths exempt from rate limiting
            burst_multiplier: Allow short bursts up to this multiple of the limit
            block_duration: Duration to block IPs that exceed the burst limit (seconds)
            strict_ip_check: Whether to use strict IP validation
            header_name: Header name prefix for rate limit headers
        """
        self.limit = limit
        self.period = period
        self.redis_client = redis_client
        self.redis_prefix = redis_prefix
        self.exempt_ips = exempt_ips or ["127.0.0.1/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        self.exempt_paths = exempt_paths or ["/health/liveness", "/health/readiness", "/docs", "/redoc", "/openapi.json"]
        self.burst_multiplier = burst_multiplier
        self.block_duration = block_duration
        self.strict_ip_check = strict_ip_check
        self.header_name = header_name
        
        # Parse exempt IP networks
        self.exempt_networks = []
        for ip_range in self.exempt_ips:
            try:
                self.exempt_networks.append(ipaddress.ip_network(ip_range, strict=False))
            except ValueError:
                logger.warning(f"Invalid IP range in exempt_ips: {ip_range}")
                
    def is_path_exempt(self, path: str) -> bool:
        """Check if a path is exempt from rate limiting"""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
        
    def is_ip_exempt(self, ip: str) -> bool:
        """Check if an IP is exempt from rate limiting"""
        if not ip or ip == "unknown":
            return False
            
        try:
            client_ip = ipaddress.ip_address(ip)
            for network in self.exempt_networks:
                if client_ip in network:
                    return True
        except ValueError:
            if self.strict_ip_check:
                logger.warning(f"Invalid IP address: {ip}")
            return False
            
        return False

class RateLimiter:
    """Rate limiter implementation that supports both in-memory and Redis backends"""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config
        
    async def check_rate_limit(self, key: str, endpoint: str) -> Dict[str, Union[bool, int]]:
        """
        Check if a request exceeds the rate limit.
        
        Args:
            key: Rate limit key (usually IP address or user ID)
            endpoint: API endpoint path
            
        Returns:
            Dict containing:
                - allowed: Whether the request is allowed
                - remaining: Number of requests remaining in the period
                - reset: Seconds until the rate limit resets
                - blocked: Whether the key is blocked due to excessive requests
        """
        # Use Redis if available
        if REDIS_AVAILABLE and self.config.redis_client:
            return await self._check_rate_limit_redis(key, endpoint)
        else:
            return await self._check_rate_limit_memory(key, endpoint)
            
    async def _check_rate_limit_redis(self, key: str, endpoint: str) -> Dict[str, Union[bool, int]]:
        """Implement rate limiting using Redis"""
        now = int(time.time())
        redis_client = self.config.redis_client
        window_key = f"{self.config.redis_prefix}{key}:{endpoint}"
        block_key = f"{self.config.redis_prefix}block:{key}"
        
        # Check if the key is blocked
        is_blocked = await redis_client.exists(block_key)
        if is_blocked:
            ttl = await redis_client.ttl(block_key)
            return {
                "allowed": False,
                "remaining": 0,
                "reset": ttl,
                "blocked": True,
                "block_expires": ttl
            }
            
        # Get current request count in the window
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(window_key, 0, now - self.config.period)  # Remove expired entries
        pipe.zcard(window_key)  # Get current count
        pipe.zadd(window_key, {str(now): now})  # Add current request
        pipe.expire(window_key, self.config.period)  # Ensure key expiration
        results = await pipe.execute()
        
        current_count = results[1] + 1  # Add 1 for the request we just added
        
        # Calculate burst limit and check if it's exceeded
        burst_limit = int(self.config.limit * self.config.burst_multiplier)
        
        # Calculate remaining requests and reset time
        remaining = max(0, self.config.limit - current_count)
        reset = self.config.period
        
        if current_count > burst_limit:
            # Block the key for a specified duration
            await redis_client.setex(block_key, self.config.block_duration, 1)
            return {
                "allowed": False,
                "remaining": 0,
                "reset": self.config.block_duration,
                "blocked": True,
                "block_expires": self.config.block_duration
            }
        elif current_count > self.config.limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset": reset,
                "blocked": False
            }
        else:
            return {
                "allowed": True,
                "remaining": remaining,
                "reset": reset,
                "blocked": False
            }
            
    async def _check_rate_limit_memory(self, key: str, endpoint: str) -> Dict[str, Union[bool, int]]:
        """Implement rate limiting using in-memory cache"""
        now = time.time()
        window_start = now - self.config.period
        
        # Initialize cache structure if needed
        if key not in RATE_LIMIT_CACHE:
            RATE_LIMIT_CACHE[key] = {}
        if endpoint not in RATE_LIMIT_CACHE[key]:
            RATE_LIMIT_CACHE[key][endpoint] = []
            
        # Check for block status in memory
        for path, requests in RATE_LIMIT_CACHE[key].items():
            if path == f"block:{endpoint}":
                block_time, _ = requests[0]
                if now < block_time:
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset": int(block_time - now),
                        "blocked": True,
                        "block_expires": int(block_time - now)
                    }
                else:
                    # Remove expired block
                    RATE_LIMIT_CACHE[key].pop(path)
                    break
        
        # Clean up old requests
        RATE_LIMIT_CACHE[key][endpoint] = [
            (timestamp, count) for timestamp, count in RATE_LIMIT_CACHE[key][endpoint]
            if timestamp >= window_start
        ]
        
        # Add current request
        RATE_LIMIT_CACHE[key][endpoint].append((now, 1))
        
        # Calculate current count in the window
        current_count = sum(count for timestamp, count in RATE_LIMIT_CACHE[key][endpoint])
        
        # Calculate burst limit and check if it's exceeded
        burst_limit = int(self.config.limit * self.config.burst_multiplier)
        
        # Calculate remaining requests and reset time
        remaining = max(0, self.config.limit - current_count)
        if RATE_LIMIT_CACHE[key][endpoint]:
            oldest = min(timestamp for timestamp, _ in RATE_LIMIT_CACHE[key][endpoint])
            reset = int(self.config.period - (now - oldest))
        else:
            reset = self.config.period
            
        if current_count > burst_limit:
            # Block the key for a specified duration
            block_until = now + self.config.block_duration
            block_path = f"block:{endpoint}"
            RATE_LIMIT_CACHE[key][block_path] = [(block_until, 1)]
            return {
                "allowed": False,
                "remaining": 0,
                "reset": self.config.block_duration,
                "blocked": True,
                "block_expires": self.config.block_duration
            }
        elif current_count > self.config.limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset": reset,
                "blocked": False
            }
        else:
            return {
                "allowed": True,
                "remaining": remaining,
                "reset": reset,
                "blocked": False
            }
            
    async def cleanup_memory_cache(self):
        """Cleanup expired entries from memory cache"""
        now = time.time()
        
        for key in list(RATE_LIMIT_CACHE.keys()):
            for endpoint in list(RATE_LIMIT_CACHE[key].keys()):
                if endpoint.startswith("block:"):
                    block_time, _ = RATE_LIMIT_CACHE[key][endpoint][0]
                    if now > block_time:
                        RATE_LIMIT_CACHE[key].pop(endpoint, None)
                else:
                    window_start = now - self.config.period
                    RATE_LIMIT_CACHE[key][endpoint] = [
                        (timestamp, count) for timestamp, count in RATE_LIMIT_CACHE[key][endpoint]
                        if timestamp >= window_start
                    ]
                    
                    if not RATE_LIMIT_CACHE[key][endpoint]:
                        RATE_LIMIT_CACHE[key].pop(endpoint, None)
                        
            if not RATE_LIMIT_CACHE[key]:
                RATE_LIMIT_CACHE.pop(key, None)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, considering proxy headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Try to get IP from X-Forwarded-For header (common for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the first IP (client IP) from the comma-separated list
        return forwarded_for.split(",")[0].strip()
        
    # Try other common headers
    for header in ["X-Real-IP", "CF-Connecting-IP", "True-Client-IP"]:
        if header in request.headers:
            return request.headers.get(header)
            
    # Fall back to direct client address
    if request.client and request.client.host:
        return request.client.host
        
    return "unknown"


class RateLimitExceededError(HTTPException):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, detail: str = "Rate limit exceeded", headers: Dict[str, str] = None):
        """Initialize rate limit exception"""
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers or {}
        )


class RateLimitDependency:
    """
    FastAPI dependency for rate limiting specific endpoints.
    
    Usage:
    ```
    @app.get("/api/endpoint")
    def my_endpoint(rate_limit: None = Depends(RateLimitDependency(limit=10, period=60))):
        return {"message": "Rate limited endpoint"}
    ```
    """
    
    def __init__(self, 
                limit: int = 60, 
                period: int = 60,
                key_func: Callable = get_client_ip,
                burst_multiplier: float = 2.0):
        """
        Initialize the rate limit dependency.
        
        Args:
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            key_func: Function to extract the rate limit key (default: IP address)
            burst_multiplier: Allow short bursts up to this multiple of the limit
        """
        self.limit = limit
        self.period = period
        self.key_func = key_func
        self.burst_multiplier = burst_multiplier
        
    async def get_limiter(self) -> RateLimiter:
        """Get a configured rate limiter instance"""
        # Attempt to get Redis client from main module if available
        redis_client = None
        try:
            from main import redis_client as app_redis_client
            redis_client = app_redis_client
        except (ImportError, AttributeError):
            pass
            
        config = RateLimitConfig(
            limit=self.limit,
            period=self.period,
            redis_client=redis_client,
            burst_multiplier=self.burst_multiplier
        )
        return RateLimiter(config)
        
    async def __call__(self, request: Request) -> None:
        """
        Check rate limit for the current request.
        
        Args:
            request: FastAPI request object
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        # Get rate limiter instance
        limiter = await self.get_limiter()
        
        # Get rate limit key (default is client IP)
        key = self.key_func(request)
        
        # Skip rate limiting for exempt IPs
        if limiter.config.is_ip_exempt(key):
            return None
            
        # Check rate limit
        endpoint = request.url.path
        result = await limiter.check_rate_limit(key, endpoint)
        
        # Add rate limit headers
        headers = {
            f"{limiter.config.header_name}-Limit": str(self.limit),
            f"{limiter.config.header_name}-Remaining": str(result["remaining"]),
            f"{limiter.config.header_name}-Reset": str(result["reset"]),
        }
        
        # If blocked, add block expiry header
        if result.get("blocked", False):
            headers[f"{limiter.config.header_name}-Block-Expires"] = str(result.get("block_expires", 0))
            
        # Raise exception if rate limit exceeded
        if not result["allowed"]:
            if result.get("blocked", False):
                detail = f"Rate limit exceeded. Your IP has been temporarily blocked for {result.get('block_expires', 0)} seconds."
            else:
                detail = f"Rate limit exceeded. Try again in {result['reset']} seconds."
                
            raise RateLimitExceededError(detail=detail, headers=headers)
            
        # Rate limit not exceeded, continue
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global rate limiting across the application.
    
    This middleware applies rate limiting to all routes by default,
    with options to exempt specific paths and IPs.
    """
    
    def __init__(self, 
                app: ASGIApp, 
                limit: int = 120,
                period: int = 60,
                redis_client: Optional[redis.Redis] = None,
                exempt_paths: List[str] = None,
                exempt_ips: List[str] = None,
                burst_multiplier: float = 2.0,
                block_duration: int = 300,
                cleanup_interval: int = 60):
        """
        Initialize the rate limit middleware.
        
        Args:
            app: ASGI application
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            redis_client: Optional Redis client for distributed rate limiting
            exempt_paths: List of URL paths exempt from rate limiting
            exempt_ips: List of IPs exempt from rate limiting
            burst_multiplier: Allow short bursts up to this multiple of the limit
            block_duration: Duration to block IPs that exceed the burst limit
            cleanup_interval: Interval for cleaning up the memory cache
        """
        super().__init__(app)
        
        # If Redis client not provided, try to get from main app
        if redis_client is None and REDIS_AVAILABLE:
            try:
                from main import redis_client as app_redis_client
                redis_client = app_redis_client
            except (ImportError, AttributeError):
                pass
                
        self.config = RateLimitConfig(
            limit=limit,
            period=period,
            redis_client=redis_client,
            exempt_paths=exempt_paths,
            exempt_ips=exempt_ips,
            burst_multiplier=burst_multiplier,
            block_duration=block_duration
        )
        
        self.rate_limiter = RateLimiter(self.config)
        self.cleanup_task = None
        self.cleanup_interval = cleanup_interval
        
    async def start_cleanup_task(self):
        """Start the background task to clean up expired cache entries"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _cleanup_loop(self):
        """Background task to periodically clean up expired cache entries"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.rate_limiter.cleanup_memory_cache()
        except asyncio.CancelledError:
            logger.debug("Rate limit cleanup task cancelled")
            
    async def stop_cleanup_task(self):
        """Stop the cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process an incoming request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Function to call the next middleware or route handler
            
        Returns:
            Response: HTTP response
        """
        # Start cleanup task if not started
        if not self.cleanup_task:
            await self.start_cleanup_task()
            
        # Skip rate limiting for exempt paths
        path = request.url.path
        if self.config.is_path_exempt(path):
            return await call_next(request)
            
        # Get client IP
        client_ip = get_client_ip(request)
        
        # Skip rate limiting for exempt IPs
        if self.config.is_ip_exempt(client_ip):
            return await call_next(request)
            
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(client_ip, "*")  # Global rate limit
        
        # Add rate limit headers
        headers = {
            f"{self.config.header_name}-Limit": str(self.config.limit),
            f"{self.config.header_name}-Remaining": str(result["remaining"]),
            f"{self.config.header_name}-Reset": str(result["reset"]),
        }
        
        # If rate limit exceeded, return 429 response
        if not result["allowed"]:
            if result.get("blocked", False):
                detail = f"Rate limit exceeded. Your IP has been temporarily blocked for {result.get('block_expires', 0)} seconds."
                headers[f"{self.config.header_name}-Block-Expires"] = str(result.get("block_expires", 0))
            else:
                detail = f"Rate limit exceeded. Try again in {result['reset']} seconds."
                
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on path {path}",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "blocked": result.get("blocked", False),
                    "reset": result["reset"]
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": detail,
                    "timestamp": datetime.now().isoformat()
                },
                headers=headers
            )
            
        # Process the request normally
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
            
        return response


def configure_rate_limiter(app: ASGIApp, redis_client=None) -> RateLimitMiddleware:
    """
    Configure and add rate limiting middleware to the FastAPI application.
    
    Args:
        app: FastAPI application
        redis_client: Optional Redis client for distributed rate limiting
        
    Returns:
        RateLimitMiddleware: Configured middleware instance
    """
    # Create and add the middleware
    middleware = RateLimitMiddleware(
        app,
        limit=int(os.getenv("RATE_LIMIT", "120")),
        period=int(os.getenv("RATE_LIMIT_PERIOD", "60")),
        redis_client=redis_client,
        exempt_paths=[
            "/health/liveness",
            "/health/readiness",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static"
        ],
        burst_multiplier=float(os.getenv("RATE_LIMIT_BURST_MULTIPLIER", "2.0")),
        block_duration=int(os.getenv("RATE_LIMIT_BLOCK_DURATION", "300")),
    )
    
    return middleware
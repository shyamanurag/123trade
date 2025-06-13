"""
Security Decorators
Provides decorators for securing routes and functions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
import functools
import jwt
from fastapi import HTTPException, Request, Security, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps

logger = logging.getLogger(__name__)

def require_auth(security_manager):
    """Decorator to require authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, authorization: str = Header(None), *args, **kwargs):
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = authorization.split(" ")[1]
            payload = await security_manager.verify_token(token)
            
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
            # Add user info to request
            request.state.user_id = payload['user_id']
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def require_ip(security_manager):
    """Decorator to require specific IP addresses"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                raise HTTPException(status_code=400, detail="Request object not found")
            
            # Get client IP
            client_ip = request.client.host
            
            # Check if IP is allowed
            if not await security_manager.validate_ip_whitelist(client_ip):
                raise HTTPException(status_code=403, detail="IP not allowed")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_webhook(security_manager):
    """Decorator to verify webhook signatures"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get signature and timestamp from headers
            signature = request.headers.get('X-Webhook-Signature')
            timestamp = request.headers.get('X-Webhook-Timestamp')
            
            if not signature or not timestamp:
                logger.warning("Missing webhook signature or timestamp")
                raise HTTPException(status_code=401, detail="Invalid webhook request")
            
            # Get request body
            body = await request.body()
            
            # Verify signature
            if not await security_manager.verify_webhook_signature(body, signature, timestamp):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
            # Verify IP whitelist
            client_ip = request.client.host
            if not await security_manager.validate_ip_whitelist(client_ip):
                logger.warning(f"Webhook request from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail="IP not whitelisted")
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def rate_limit(limit: int = 100, window: int = 60):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get identifier (IP or user)
            identifier = request.client.host
            if hasattr(request.state, 'user_id'):
                identifier = f"user:{request.state.user_id}"
            
            security_manager = request.app.state.security_manager
            allowed, retry_after = await security_manager.check_rate_limit(identifier, limit, window)
            
            if not allowed:
                raise HTTPException(
                    status_code=429, 
                    detail=f"Rate limit exceeded. Retry after {retry_after} seconds",
                    headers={"Retry-After": str(retry_after)}
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def require_permission(permission: str):
    """Decorator to require specific permissions"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                raise HTTPException(status_code=400, detail="Request object not found")
            
            # Get user from request state
            user = getattr(request.state, 'user', None)
            if not user:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            # Check permission
            if permission not in user.get('permissions', []):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def audit_log(action: str):
    """Decorator to log actions for audit purposes"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                raise HTTPException(status_code=400, detail="Request object not found")
            
            # Get user from request state
            user = getattr(request.state, 'user', None)
            username = user.get('username') if user else 'anonymous'
            
            # Log action
            logger.info(f"Audit: {username} performed {action}")
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Audit: {username} failed {action}: {e}")
                raise
        
        return wrapper
    return decorator

def encrypt_sensitive_data(security_manager):
    """Decorator to encrypt sensitive data in responses"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Encrypt sensitive fields
            if isinstance(result, dict):
                for key in result:
                    if any(sensitive in key.lower() for sensitive in
                          ['password', 'token', 'key', 'secret']):
                        result[key] = security_manager.encrypt_data(str(result[key]))
            
            return result
        
        return wrapper
    return decorator

def validate_input(schema):
    """Decorator to validate input data against a schema"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                raise HTTPException(status_code=400, detail="Request object not found")
            
            # Get request body
            body = await request.json()
            
            # Validate against schema
            try:
                validated_data = schema(**body)
                # Replace body with validated data
                request.state.validated_data = validated_data
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator 
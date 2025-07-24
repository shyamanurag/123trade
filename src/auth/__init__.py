"""
Authentication module for trading system
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current authenticated user from JWT token
    For now, returns a default user for development
    """
    try:
        # In production, this would validate the JWT token
        # For now, return default user to keep system running
        if credentials and credentials.credentials:
            return "production_user"
        else:
            # Allow unauthenticated access for development
            return "dev_user"
            
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        # Don't block the system - return default user
        return "system_user"

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """
    Get current user but allow None (optional authentication)
    """
    try:
        if credentials and credentials.credentials:
            return await get_current_user(credentials)
        return None
    except Exception:
        return None

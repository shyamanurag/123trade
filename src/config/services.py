"""
Service configuration for the trading system
Manages different web services (FastAPI, Flask, Dash) and their interactions
"""

from typing import Dict, Any, Optional
from pydantic import BaseSettings, validator
import os

class ServiceConfig(BaseSettings):
    """Service configuration settings"""
    
    # Service URLs (for inter-service communication)
    MAIN_API_URL: str = "http://localhost:8000"
    DASH_URL: str = "http://localhost:8050"
    SECURITY_API_URL: str = "http://localhost:8001"
    
    # Service authentication
    SERVICE_AUTH_TOKEN: Optional[str] = None
    
    @validator("SERVICE_AUTH_TOKEN", pre=True)
    def validate_auth_token(cls, v: Optional[str]) -> str:
        """Validate or generate service authentication token"""
        if not v:
            return os.urandom(32).hex()
        return v
    
    class Config:
        env_prefix = "SERVICE_"
        case_sensitive = True

# Service endpoints
class ServiceEndpoints:
    """Service endpoint definitions"""
    
    # Main API endpoints
    MAIN_API = {
        "health": "/health",
        "market_data": "/api/v1/market-data",
        "orders": "/api/v1/orders",
        "positions": "/api/v1/positions",
        "risk": "/api/v1/risk",
    }
    
    # Security API endpoints
    SECURITY_API = {
        "auth": "/auth",
        "verify": "/verify",
        "refresh": "/refresh",
    }
    
    # Dash endpoints
    DASH = {
        "dashboard": "/",
        "portfolio": "/portfolio",
        "trades": "/trades",
        "analysis": "/analysis",
    }

# Service roles and permissions
class ServiceRoles:
    """Service role definitions"""
    
    MAIN_API = {
        "read": ["market_data", "positions", "risk"],
        "write": ["orders", "positions"],
        "admin": ["*"],
    }
    
    DASH = {
        "read": ["dashboard", "portfolio", "trades", "analysis"],
        "write": ["portfolio"],
        "admin": ["*"],
    }
    
    SECURITY_API = {
        "read": ["verify"],
        "write": ["auth", "refresh"],
        "admin": ["*"],
    }

# Initialize configuration
service_config = ServiceConfig()
service_endpoints = ServiceEndpoints()
service_roles = ServiceRoles() 
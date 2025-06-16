"""
Production Enhancer Module

Integrates production-ready components including:
- Health check router
- Request validation middleware
- Rate limiting middleware

This module centralizes the integration of these components with the main FastAPI application.
"""

import os
import logging
from typing import Dict, Optional, Any
from fastapi import FastAPI
import redis.asyncio as redis

from core.logging_config import get_logger
from routers.health_check_router import health_router
from middleware.request_validation import RequestValidationMiddleware, ValidationConfig
from middleware.rate_limiter import RateLimitMiddleware, RateLimitConfig

logger = get_logger(__name__)

def enhance_production_readiness(
    app: FastAPI,
    redis_client: Optional[redis.Redis] = None,
    config: Dict[str, Any] = None
) -> FastAPI:
    """
    Enhance the FastAPI application with production-ready features.
    
    Args:
        app: FastAPI application instance
        redis_client: Optional Redis client for distributed rate limiting
        config: Optional configuration dictionary
        
    Returns:
        FastAPI: The enhanced application
    """
    logger.info("Enhancing application with production features")
    
    # Add health check router
    logger.info("Registering health check routes")
    app.include_router(health_router)
    
    # Add request validation middleware with custom configuration
    logger.info("Adding request validation middleware")
    validation_config = ValidationConfig(
        max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "10485760")),  # 10MB default
        exempt_paths={
            "/health/liveness", 
            "/health/readiness",
            "/metrics",
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/assets",
            "/static"
        },
        strict_content_type=os.getenv("ENVIRONMENT", "development") == "production"
    )
    app.add_middleware(RequestValidationMiddleware, config=validation_config)
    
    # Add rate limiting middleware if Redis is available
    if redis_client:
        logger.info("Adding rate limiting middleware with Redis")
        app.add_middleware(
            RateLimitMiddleware,
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
    else:
        logger.warning("Redis not available, using in-memory rate limiting")
        app.add_middleware(
            RateLimitMiddleware,
            limit=int(os.getenv("RATE_LIMIT", "60")),  # More conservative without Redis
            period=int(os.getenv("RATE_LIMIT_PERIOD", "60")),
            exempt_paths=[
                "/health/liveness",
                "/health/readiness",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/static"
            ]
        )
    
    return app

def integrate_with_main(app: FastAPI, redis_client: Optional[redis.Redis] = None) -> None:
    """
    Integration function to be called from main.py
    
    Args:
        app: FastAPI application instance
        redis_client: Redis client from the main application
    """
    try:
        # Enhance application with production features
        enhance_production_readiness(app, redis_client)
        
        logger.info("✅ Production enhancements successfully integrated")
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate production enhancements: {e}")
        # Don't re-raise - application should continue without these enhancements
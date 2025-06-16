"""
Health Check API Router
Provides comprehensive system health monitoring endpoints
"""

import os
import sys
import json
import time
import shutil
import asyncio
import psutil
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import redis.asyncio as redis
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge, Counter, Histogram

# Import database and monitoring tools
from database_manager import get_database_manager
from main import redis_client, config
from core.logging_config import get_logger
from monitoring.health_check import HealthCheck
from middleware.rate_limiter import RateLimitDependency, get_client_ip
from middleware.security_middleware import verify_token, optional_auth

# Setup logger
logger = get_logger(__name__)

# Define metrics
SYSTEM_CPU_USAGE = Gauge('system_cpu_usage', 'CPU usage percentage')
SYSTEM_MEMORY_USAGE = Gauge('system_memory_usage', 'Memory usage percentage')
SYSTEM_DISK_USAGE = Gauge('system_disk_usage', 'Disk usage percentage')
API_REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'API request latency', ['endpoint'])
API_REQUEST_COUNT = Counter('api_request_count_total', 'API request count', ['endpoint', 'status'])

# Create router
health_router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str = Field(..., description="Overall health status (healthy, degraded, unhealthy)")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    version: str = Field(..., description="Application version")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Component health statuses")
    uptime: float = Field(..., description="Server uptime in seconds")
    hostname: str = Field(..., description="Server hostname")
    environment: str = Field(..., description="Deployment environment")


class ComponentHealth(BaseModel):
    """Component health details"""
    status: str = Field(..., description="Component status (healthy, degraded, unhealthy)")
    latency_ms: float = Field(..., description="Response time in milliseconds")
    details: Dict[str, Any] = Field({}, description="Additional component-specific details")
    last_check: str = Field(..., description="ISO timestamp of last check")


class SystemResources(BaseModel):
    """System resource usage"""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_percent: float = Field(..., description="Disk usage percentage")
    memory_available_mb: float = Field(..., description="Available memory in MB")
    disk_available_gb: float = Field(..., description="Available disk space in GB")
    load_avg: List[float] = Field(..., description="System load average (1, 5, 15 minutes)")


@health_router.get("/liveness", summary="Simple liveness check", response_model=Dict[str, str])
async def liveness_check(response: Response) -> Dict[str, str]:
    """
    Simple liveness check that returns a 200 OK response if the server is running.
    This is used by Kubernetes and other orchestration systems to determine if the
    container is live.
    """
    start_time = time.time()
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    # Record metrics
    API_REQUEST_COUNT.labels(endpoint="/health/liveness", status="200").inc()
    API_REQUEST_LATENCY.labels(endpoint="/health/liveness").observe(time.time() - start_time)
    
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@health_router.get("/readiness", summary="Application readiness check", response_model=Dict[str, str])
async def readiness_check(response: Response) -> Dict[str, str]:
    """
    Readiness check that verifies if the application can handle requests.
    This is used by Kubernetes and other orchestration systems to determine if
    traffic should be sent to this instance.
    """
    start_time = time.time()
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    # Check if critical services are available
    db_manager = get_database_manager()
    
    status = "ready"
    details = {}
    
    # Check database connectivity
    try:
        if db_manager and db_manager.is_initialized:
            db_status = await db_manager.health_check()
            if db_status["status"] != "healthy":
                status = "not_ready"
                details["database"] = "unavailable"
        else:
            status = "not_ready"
            details["database"] = "not_initialized"
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        status = "not_ready"
        details["database"] = str(e)
    
    # Check Redis connectivity
    try:
        if redis_client:
            await redis_client.ping()
        else:
            # Redis may be optional in development
            if os.getenv("ENVIRONMENT", "development") == "production":
                status = "not_ready"
                details["redis"] = "not_initialized"
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        status = "not_ready"
        details["redis"] = str(e)
    
    # Record metrics
    http_status = status_code = 200 if status == "ready" else 503
    response.status_code = status_code
    
    API_REQUEST_COUNT.labels(endpoint="/health/readiness", status=str(status_code)).inc()
    API_REQUEST_LATENCY.labels(endpoint="/health/readiness").observe(time.time() - start_time)
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        **details
    }


@health_router.get("", summary="Comprehensive health status", response_model=HealthStatus)
@health_router.get("/", summary="Comprehensive health status", response_model=HealthStatus)
async def health_status(
    response: Response,
    detailed: bool = Query(False, description="Include detailed component metrics"),
    user_token: Optional[Dict] = Depends(optional_auth),
    rate_limit: None = Depends(RateLimitDependency(limit=10, period=60))
) -> Dict[str, Any]:
    """
    Comprehensive health check that returns detailed information about all system components.
    This endpoint provides a detailed view of the application's health status.
    
    Rate limited to 10 requests per minute per client.
    """
    start_time = time.time()
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    # Check if user has admin access for detailed view
    is_admin = False
    if user_token and "role" in user_token and user_token["role"] == "admin":
        is_admin = True
    
    # If detailed view requested but not admin, require authentication
    if detailed and not is_admin and not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for detailed health view",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Collect health information
    db_manager = get_database_manager()
    health_components = {}
    overall_status = "healthy"
    
    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        SYSTEM_CPU_USAGE.set(cpu_percent)
        SYSTEM_MEMORY_USAGE.set(memory.percent)
        SYSTEM_DISK_USAGE.set(disk.percent)
        
        system_resources = {
            "status": "healthy",
            "latency_ms": 0.0,
            "last_check": datetime.now().isoformat(),
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": disk.percent,
                "disk_available_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        }
        
        # Check thresholds and adjust status
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            system_resources["status"] = "unhealthy"
            overall_status = "degraded"
        elif cpu_percent > 75 or memory.percent > 80 or disk.percent > 85:
            system_resources["status"] = "degraded"
            if overall_status == "healthy":
                overall_status = "degraded"
                
        health_components["system"] = system_resources
    except Exception as e:
        logger.error(f"System resources check failed: {e}")
        health_components["system"] = {
            "status": "unknown",
            "latency_ms": 0.0,
            "last_check": datetime.now().isoformat(),
            "details": {"error": str(e)}
        }
        overall_status = "degraded"
    
    # Database status
    try:
        if db_manager and db_manager.is_initialized:
            db_check_start = time.time()
            db_status = await db_manager.health_check()
            db_latency = (time.time() - db_check_start) * 1000  # ms
            
            db_health = {
                "status": db_status["status"],
                "latency_ms": round(db_latency, 2),
                "last_check": datetime.now().isoformat(),
                "details": db_status["pool_stats"] if detailed else {"database_size": db_status.get("database_size", "unknown")}
            }
            
            if db_status["status"] != "healthy":
                overall_status = "degraded"
                
            health_components["database"] = db_health
        else:
            health_components["database"] = {
                "status": "unavailable",
                "latency_ms": 0.0,
                "last_check": datetime.now().isoformat(),
                "details": {"error": "Database manager not initialized"}
            }
            overall_status = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_components["database"] = {
            "status": "error",
            "latency_ms": 0.0,
            "last_check": datetime.now().isoformat(),
            "details": {"error": str(e)}
        }
        overall_status = "degraded"
    
    # Redis status
    try:
        if redis_client:
            redis_check_start = time.time()
            redis_ping = await redis_client.ping()
            redis_latency = (time.time() - redis_check_start) * 1000  # ms
            
            if redis_ping:
                # Check memory usage if detailed
                redis_details = {}
                if detailed:
                    try:
                        info = await redis_client.info("memory")
                        used_memory = info.get("used_memory_human", "unknown")
                        peak_memory = info.get("used_memory_peak_human", "unknown")
                        redis_details = {
                            "used_memory": used_memory,
                            "peak_memory": peak_memory
                        }
                    except Exception as e:
                        redis_details = {"memory_info_error": str(e)}
                
                health_components["redis"] = {
                    "status": "healthy",
                    "latency_ms": round(redis_latency, 2),
                    "last_check": datetime.now().isoformat(),
                    "details": redis_details
                }
            else:
                health_components["redis"] = {
                    "status": "unhealthy",
                    "latency_ms": round(redis_latency, 2),
                    "last_check": datetime.now().isoformat(),
                    "details": {"error": "Redis ping failed"}
                }
                overall_status = "degraded"
        else:
            health_components["redis"] = {
                "status": "disabled",
                "latency_ms": 0.0,
                "last_check": datetime.now().isoformat(),
                "details": {"info": "Redis client not initialized"}
            }
            if os.getenv("ENVIRONMENT", "development") == "production":
                overall_status = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_components["redis"] = {
            "status": "error",
            "latency_ms": 0.0,
            "last_check": datetime.now().isoformat(),
            "details": {"error": str(e)}
        }
        if os.getenv("ENVIRONMENT", "development") == "production":
            overall_status = "degraded"
    
    # Build full response
    health_response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "components": health_components,
        "uptime": time.time() - psutil.boot_time(),
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    # Record metrics
    status_code = 200 if overall_status == "healthy" else 503 if overall_status == "unhealthy" else 200
    response.status_code = status_code
    
    API_REQUEST_COUNT.labels(endpoint="/health", status=str(status_code)).inc()
    API_REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start_time)
    
    return health_response


@health_router.get("/metrics", summary="Prometheus metrics", response_class=Response)
async def metrics(
    response: Response,
    user_token: Optional[Dict] = Depends(optional_auth)
) -> Response:
    """
    Prometheus metrics endpoint that returns all collected metrics.
    This endpoint is used by Prometheus for scraping metrics.
    
    Requires authentication in production environment.
    """
    # Check if authentication is required
    if os.getenv("ENVIRONMENT", "development") == "production" and not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for metrics in production",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    response.headers["Content-Type"] = CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@health_router.get("/database", summary="Database connectivity check", response_model=Dict[str, Any])
async def database_health(
    response: Response,
    detailed: bool = Query(False, description="Include detailed metrics"),
    user_token: Optional[Dict] = Depends(optional_auth),
    rate_limit: None = Depends(RateLimitDependency(limit=5, period=60))
) -> Dict[str, Any]:
    """
    Database health check that verifies connectivity and reports performance metrics.
    
    Rate limited to 5 requests per minute per client.
    """
    start_time = time.time()
    
    # Check if user has admin access for detailed view
    is_admin = False
    if user_token and "role" in user_token and user_token["role"] == "admin":
        is_admin = True
    
    # If detailed view requested but not admin, require authentication
    if detailed and not is_admin and not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for detailed database health",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    db_manager = get_database_manager()
    if not db_manager or not db_manager.is_initialized:
        response.status_code = 503
        return {
            "status": "unavailable",
            "error": "Database manager not initialized",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        db_status = await db_manager.health_check()
        
        # Limit details for non-admin users
        if not is_admin and not detailed:
            db_status.pop("pool_stats", None)
        
        # Record metrics
        status_code = 200 if db_status["status"] == "healthy" else 503
        response.status_code = status_code
        
        API_REQUEST_COUNT.labels(endpoint="/health/database", status=str(status_code)).inc()
        API_REQUEST_LATENCY.labels(endpoint="/health/database").observe(time.time() - start_time)
        
        return db_status
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        response.status_code = 500
        
        API_REQUEST_COUNT.labels(endpoint="/health/database", status="500").inc()
        API_REQUEST_LATENCY.labels(endpoint="/health/database").observe(time.time() - start_time)
        
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@health_router.post("/optimize-database", summary="Optimize database performance", response_model=Dict[str, Any])
async def optimize_database(
    response: Response,
    user_token: Dict = Depends(verify_token),
    rate_limit: None = Depends(RateLimitDependency(limit=1, period=3600))  # Once per hour
) -> Dict[str, Any]:
    """
    Trigger database optimization tasks (ANALYZE, VACUUM, etc.).
    This endpoint will run maintenance operations to improve database performance.
    
    Requires admin authentication and is rate limited to once per hour.
    """
    start_time = time.time()
    
    # Check if user has admin access
    if "role" not in user_token or user_token["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for database optimization"
        )
    
    db_manager = get_database_manager()
    if not db_manager or not db_manager.is_initialized:
        response.status_code = 503
        return {
            "status": "unavailable",
            "error": "Database manager not initialized",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        logger.info("Database optimization requested by admin")
        await db_manager.optimize_performance()
        
        API_REQUEST_COUNT.labels(endpoint="/health/optimize-database", status="200").inc()
        API_REQUEST_LATENCY.labels(endpoint="/health/optimize-database").observe(time.time() - start_time)
        
        return {
            "status": "success",
            "message": "Database optimization completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        response.status_code = 500
        
        API_REQUEST_COUNT.labels(endpoint="/health/optimize-database", status="500").inc()
        API_REQUEST_LATENCY.labels(endpoint="/health/optimize-database").observe(time.time() - start_time)
        
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
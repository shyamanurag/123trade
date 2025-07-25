"""
Enhanced Health Check API
Provides comprehensive health monitoring for the trading system
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel
import httpx
import redis
import sqlalchemy
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

class ComponentStatus(BaseModel):
    name: str
    status: str
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "4.0.1"
    uptime_seconds: int
    system_metrics: Dict[str, Any]
    components: List[ComponentStatus]
    overall_health_score: int

class DependencyChecker:
    """Check health of various system dependencies"""
    
    @staticmethod
    async def check_database(db_url: str) -> ComponentStatus:
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="database",
                status="healthy",
                response_time_ms=response_time,
                metadata={"type": "postgresql", "query": "SELECT 1"}
            )
        except Exception as e:
            return ComponentStatus(
                name="database",
                status="unhealthy",
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    @staticmethod
    async def check_redis(redis_url: str) -> ComponentStatus:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        try:
            client = redis.from_url(redis_url)
            client.ping()
            client.close()
            
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="redis",
                status="healthy",
                response_time_ms=response_time,
                metadata={"operation": "ping"}
            )
        except Exception as e:
            return ComponentStatus(
                name="redis",
                status="unhealthy",
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    @staticmethod
    async def check_external_api(name: str, url: str, timeout: int = 5) -> ComponentStatus:
        """Check external API availability"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name=name,
                status="healthy",
                response_time_ms=response_time,
                metadata={"status_code": response.status_code}
            )
        except Exception as e:
            return ComponentStatus(
                name=name,
                status="unhealthy",
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

@router.get("/", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        uptime_seconds=int(time.time()),
        system_metrics={
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        components=[],
        overall_health_score=100
    )

@router.get("/detailed", response_model=HealthCheckResponse)
async def detailed_health_check():
    """Comprehensive health check with all dependencies"""
    start_time = time.time()
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_metrics = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
    }
    
    # Check dependencies
    components = []
    
    # Database check
    try:
        import os
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/trading_system')
        db_status = await DependencyChecker.check_database(db_url)
        components.append(db_status)
    except Exception as e:
        components.append(ComponentStatus(
            name="database",
            status="unknown",
            error=f"Failed to check: {str(e)}"
        ))
    
    # Redis check
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_status = await DependencyChecker.check_redis(redis_url)
        components.append(redis_status)
    except Exception as e:
        components.append(ComponentStatus(
            name="redis",
            status="unknown",
            error=f"Failed to check: {str(e)}"
        ))
    
    # Calculate overall health score
    healthy_components = len([c for c in components if c.status == "healthy"])
    total_components = len(components)
    health_score = int((healthy_components / total_components * 100)) if total_components > 0 else 100
    
    # Adjust score based on system metrics
    if cpu_percent > 90:
        health_score -= 20
    elif cpu_percent > 80:
        health_score -= 10
    
    if memory.percent > 90:
        health_score -= 20
    elif memory.percent > 80:
        health_score -= 10
    
    overall_status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        uptime_seconds=int(time.time() - start_time),
        system_metrics=system_metrics,
        components=components,
        overall_health_score=max(0, health_score)
    )

@router.get("/readiness")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check if critical services are available
        import os
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            db_status = await DependencyChecker.check_database(db_url)
            if db_status.status != "healthy":
                raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/liveness")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow()}

@router.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    metrics = [
        f"# HELP system_cpu_percent CPU usage percentage",
        f"# TYPE system_cpu_percent gauge", 
        f"system_cpu_percent {cpu_percent}",
        f"",
        f"# HELP system_memory_percent Memory usage percentage",
        f"# TYPE system_memory_percent gauge",
        f"system_memory_percent {memory.percent}",
        f"",
        f"# HELP system_disk_percent Disk usage percentage", 
        f"# TYPE system_disk_percent gauge",
        f"system_disk_percent {disk.percent}",
    ]
    
    return "\n".join(metrics)
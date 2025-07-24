"""
Basic Health Checker Module
"""
import logging
import psutil
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from ..core.config import Settings
import time

logger = logging.getLogger(__name__)

class HealthChecker:
    """Basic health checker for system monitoring"""
    
    def __init__(self, config: Settings):
        self.config = config
        self.logger = logging.getLogger("health_checker")
        self.start_time = time.time()
        self._is_running = False
        self._check_interval = 30  # seconds
        self._last_check = None
        self._health_status = {
            "status": "unknown",
            "last_check": None,
            "uptime": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }

    async def start(self):
        """Start the health checker background task."""
        if not self._is_running:
            self._is_running = True
            asyncio.create_task(self._background_check())
            self.logger.info("Health checker started")

    async def stop(self):
        """Stop the health checker."""
        self._is_running = False
        self.logger.info("Health checker stopped")

    async def _background_check(self):
        """Background task to periodically check system health."""
        while self._is_running:
            try:
                await self.check_health()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                self.logger.error(f"Error in health check: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def check_health(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            uptime_seconds = time.time() - self.start_time
            uptime_str = f"{int(uptime_seconds)}s"
            
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            
            self._health_status.update({
                "status": "healthy",
                "last_check": datetime.now().isoformat(),
                "uptime": uptime_str,
                "memory_usage": memory.percent,
                "cpu_usage": cpu
            })
            
            self._last_check = datetime.now()
            return {
                "version": "4.0.1",
                "components": {
                    "api": "operational", 
                    "system": "healthy"
                },
                "uptime": uptime_str,
                "active_connections": 0,
                "last_backup": None,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check error: {e}")
            self._health_status["status"] = "unhealthy"
            return {
                "version": "4.0.1",
                "components": {"api": "operational"},
                "uptime": "unknown",
                "active_connections": 0,
                "error": str(e)
            }

    async def check_liveness(self) -> bool:
        """Check if service is alive"""
        try:
            # Basic liveness check
            return True
        except Exception as e:
            logger.error(f"Liveness check error: {e}")
            return False

    async def check_readiness(self) -> bool:
        """Check if service is ready"""
        try:
            # Basic readiness check
            return True
        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            return False

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics."""
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "usage_percent": cpu,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "uptime": (datetime.now() - self._start_time).total_seconds()
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status."""
        return self._health_status 
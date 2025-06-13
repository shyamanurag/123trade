"""
Unified Health Check System for Trading Application
Consolidates all health monitoring into a single, comprehensive system
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
from prometheus_client import Gauge, Counter
import os

# Prometheus metrics
health_status_gauge = Gauge(
    'trading_system_health_status',
    'Health status of system components (1=healthy, 0=unhealthy)',
    ['component']
)

health_check_counter = Counter(
    'trading_system_health_checks_total',
    'Total number of health checks performed',
    ['component', 'status']
)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms
        }


@dataclass
class SystemHealthReport:
    """Overall system health report"""
    overall_status: HealthStatus
    components: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    system_uptime: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "system_uptime": self.system_uptime,
            "components": [comp.to_dict() for comp in self.components],
            "summary": {
                "total_components": len(self.components),
                "healthy": len([c for c in self.components if c.status == HealthStatus.HEALTHY]),
                "degraded": len([c for c in self.components if c.status == HealthStatus.DEGRADED]),
                "unhealthy": len([c for c in self.components if c.status == HealthStatus.UNHEALTHY]),
                "unknown": len([c for c in self.components if c.status == HealthStatus.UNKNOWN])
            }
        }


class HealthChecker:
    """Unified health checking system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("health_checker")
        self.start_time = datetime.now()
        
        # Registry of health check functions
        self.checks: Dict[str, Callable] = {}
        self.check_intervals: Dict[str, int] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        # Redis client for caching results
        self.redis_client: Optional[redis.Redis] = None
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the health checker"""
        try:
            # Initialize Redis connection if configured
            if 'redis' in self.config or os.getenv('REDIS_URL'):
                # Prioritize environment variables for DigitalOcean deployment
                redis_url = os.getenv('REDIS_URL')
                if redis_url:
                    # Handle SSL Redis URLs (rediss://)
                    if redis_url.startswith('rediss://'):
                        self.redis_client = redis.from_url(
                            redis_url, 
                            decode_responses=True,
                            ssl_cert_reqs=None,
                            ssl_check_hostname=False
                        )
                    else:
                        self.redis_client = redis.from_url(redis_url, decode_responses=True)
                    self.logger.info(f"Redis client initialized with URL: {redis_url[:30]}...")
                else:
                    # Fallback to config
                    redis_config = self.config.get('redis', {})
                    redis_url = redis_config.get('url', 'redis://localhost:6379')
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                    self.logger.info(f"Redis client initialized from config: {redis_url}")
                
            # Register default health checks
            await self._register_default_checks()
            
            # Start background monitoring
            self._running = True
            self._monitoring_task = asyncio.create_task(self._background_monitoring())
            
            self.logger.info("Health checker started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start health checker: {e}")
            raise
            
    async def stop(self) -> None:
        """Stop the health checker"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        if self.redis_client:
            await self.redis_client.close()
            
        self.logger.info("Health checker stopped")
        
    def register_check(
        self,
        name: str,
        check_func: Callable,
        interval_seconds: int = 30
    ) -> None:
        """Register a new health check
        
        Args:
            name: Unique name for the health check
            check_func: Async function that returns HealthCheckResult
            interval_seconds: How often to run this check
        """
        self.checks[name] = check_func
        self.check_intervals[name] = interval_seconds
        self.logger.info(f"Registered health check: {name}")
        
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check
        
        Args:
            name: Name of the health check to run
            
        Returns:
            HealthCheckResult: Result of the health check
        """
        if name not in self.checks:
            return HealthCheckResult(
                component=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )
            
        start_time = datetime.now()
        
        try:
            result = await self.checks[name]()
            result.response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update metrics
            health_status_gauge.labels(component=name).set(
                1 if result.status == HealthStatus.HEALTHY else 0
            )
            health_check_counter.labels(
                component=name,
                status=result.status.value
            ).inc()
            
            # Cache result
            self.last_results[name] = result
            
            return result
            
        except Exception as e:
            result = HealthCheckResult(
                component=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            # Update metrics
            health_status_gauge.labels(component=name).set(0)
            health_check_counter.labels(
                component=name,
                status=HealthStatus.UNHEALTHY.value
            ).inc()
            
            self.last_results[name] = result
            return result
            
    async def run_all_checks(self) -> SystemHealthReport:
        """Run all registered health checks
        
        Returns:
            SystemHealthReport: Comprehensive health report
        """
        results = []
        
        # Run all checks concurrently
        tasks = [self.run_check(name) for name in self.checks.keys()]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions from gather
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    check_name = list(self.checks.keys())[i]
                    final_results.append(HealthCheckResult(
                        component=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed with exception: {str(result)}"
                    ))
                else:
                    final_results.append(result)
            results = final_results
        
        # Determine overall status
        overall_status = self._determine_overall_status(results)
        
        # Calculate uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return SystemHealthReport(
            overall_status=overall_status,
            components=results,
            system_uptime=uptime
        )
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status (main API endpoint)
        
        Returns:
            Dict: Health status suitable for API response
        """
        report = await self.run_all_checks()
        return report.to_dict()
        
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system status from component results"""
        if not results:
            return HealthStatus.UNKNOWN
            
        statuses = [result.status for result in results]
        
        # If any component is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
            
        # If any component is degraded, system is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
            
        # If any component is unknown, system is degraded
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.DEGRADED
            
        # All components healthy
        return HealthStatus.HEALTHY
        
    async def _background_monitoring(self) -> None:
        """Background task for continuous health monitoring"""
        while self._running:
            try:
                # Run health checks based on their intervals
                current_time = datetime.now()
                
                for check_name, interval in self.check_intervals.items():
                    last_result = self.last_results.get(check_name)
                    
                    # Check if it's time to run this check
                    should_run = (
                        last_result is None or
                        (current_time - last_result.timestamp).total_seconds() >= interval
                    )
                    
                    if should_run:
                        await self.run_check(check_name)
                        
                # Cache overall health status
                if self.redis_client:
                    try:
                        report = await self.run_all_checks()
                        await self.redis_client.setex(
                            "system:health_status",
                            30,  # Cache for 30 seconds
                            report.overall_status.value
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to cache health status: {e}")
                        
                # Wait before next monitoring cycle
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {e}")
                await asyncio.sleep(5)
                
    async def _register_default_checks(self) -> None:
        """Register default system health checks"""
        
        async def redis_check() -> HealthCheckResult:
            """Check Redis connection"""
            if not self.redis_client:
                return HealthCheckResult(
                    component="redis",
                    status=HealthStatus.UNKNOWN,
                    message="Redis client not configured"
                )
                
            try:
                await self.redis_client.ping()
                return HealthCheckResult(
                    component="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection is healthy"
                )
            except Exception as e:
                return HealthCheckResult(
                    component="redis",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Redis connection failed: {str(e)}"
                )
                
        async def memory_check() -> HealthCheckResult:
            """Check memory usage"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                if memory.percent > 90:
                    status = HealthStatus.UNHEALTHY
                    message = f"Memory usage critically high: {memory.percent}%"
                elif memory.percent > 80:
                    status = HealthStatus.DEGRADED
                    message = f"Memory usage high: {memory.percent}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Memory usage normal: {memory.percent}%"
                    
                return HealthCheckResult(
                    component="memory",
                    status=status,
                    message=message,
                    details={"percent": memory.percent, "available": memory.available}
                )
            except Exception as e:
                return HealthCheckResult(
                    component="memory",
                    status=HealthStatus.UNKNOWN,
                    message=f"Memory check failed: {str(e)}"
                )
                
        async def disk_check() -> HealthCheckResult:
            """Check disk usage"""
            try:
                import psutil
                disk = psutil.disk_usage('/')
                percent = (disk.used / disk.total) * 100
                
                if percent > 90:
                    status = HealthStatus.UNHEALTHY
                    message = f"Disk usage critically high: {percent:.1f}%"
                elif percent > 80:
                    status = HealthStatus.DEGRADED
                    message = f"Disk usage high: {percent:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Disk usage normal: {percent:.1f}%"
                    
                return HealthCheckResult(
                    component="disk",
                    status=status,
                    message=message,
                    details={"percent": percent, "free": disk.free}
                )
            except Exception as e:
                return HealthCheckResult(
                    component="disk",
                    status=HealthStatus.UNKNOWN,
                    message=f"Disk check failed: {str(e)}"
                )
        
        # Register default checks
        self.register_check("redis", redis_check, 30)
        self.register_check("memory", memory_check, 60)
        self.register_check("disk", disk_check, 300) 
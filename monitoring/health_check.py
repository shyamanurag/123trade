"""
Health Check Module
Monitors system components and provides health status
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import redis.asyncio as redis
from prometheus_client import Gauge, Counter

logger = logging.getLogger(__name__)

# Prometheus metrics
COMPONENT_HEALTH = Gauge(
    'component_health',
    'Health status of system components',
    ['component']
)

HEALTH_CHECK_LATENCY = Histogram(
    'health_check_latency_seconds',
    'Latency of health checks',
    ['component']
)

HEALTH_CHECK_ERRORS = Counter(
    'health_check_errors_total',
    'Number of health check errors',
    ['component', 'error_type']
)

class HealthCheck:
    def __init__(self, config: Dict, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.components = config.get('health_check', {}).get('components', {})
        self.check_interval = config.get('health_check', {}).get('interval', 60)
        self._health_task = None
        self._health_status = {}
        self._last_check = {}

    async def start(self):
        """Start health check monitoring"""
        self._health_task = asyncio.create_task(self._run_health_checks())
        logger.info("Health check monitor started")

    async def stop(self):
        """Stop health check monitoring"""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        logger.info("Health check monitor stopped")

    async def _run_health_checks(self):
        """Run periodic health checks"""
        while True:
            try:
                for component, check_config in self.components.items():
                    await self._check_component(component, check_config)
                
                # Wait until next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)

    async def _check_component(self, component: str, check_config: Dict):
        """Check health of a specific component"""
        try:
            start_time = datetime.now()
            
            if check_config['type'] == 'http':
                status = await self._check_http(component, check_config)
            elif check_config['type'] == 'redis':
                status = await self._check_redis(component, check_config)
            elif check_config['type'] == 'custom':
                status = await self._check_custom(component, check_config)
            else:
                raise ValueError(f"Unknown check type: {check_config['type']}")
            
            # Update metrics
            latency = (datetime.now() - start_time).total_seconds()
            HEALTH_CHECK_LATENCY.labels(component=component).observe(latency)
            
            # Update status
            self._health_status[component] = {
                'status': status,
                'last_check': datetime.now().isoformat(),
                'latency': latency
            }
            
            # Update Prometheus metric
            COMPONENT_HEALTH.labels(component=component).set(1 if status else 0)
            
            # Store in Redis
            await self.redis.setex(
                f"health:{component}",
                timedelta(minutes=5),
                json.dumps(self._health_status[component])
            )
            
        except Exception as e:
            logger.error(f"Error checking component {component}: {e}")
            HEALTH_CHECK_ERRORS.labels(
                component=component,
                error_type=type(e).__name__
            ).inc()
            
            self._health_status[component] = {
                'status': False,
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }
            
            COMPONENT_HEALTH.labels(component=component).set(0)

    async def _check_http(self, component: str, check_config: Dict) -> bool:
        """Check HTTP endpoint health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    check_config['url'],
                    timeout=check_config.get('timeout', 5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"HTTP check failed for {component}: {e}")
            return False

    async def _check_redis(self, component: str, check_config: Dict) -> bool:
        """Check Redis connection health"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis check failed for {component}: {e}")
            return False

    async def _check_custom(self, component: str, check_config: Dict) -> bool:
        """Run custom health check"""
        try:
            check_func = check_config['check_func']
            return await check_func()
        except Exception as e:
            logger.error(f"Custom check failed for {component}: {e}")
            return False

    async def get_health_status(self) -> Dict:
        """Get current health status of all components"""
        try:
            status = {}
            
            # Get status from Redis
            for component in self.components:
                health_data = await self.redis.get(f"health:{component}")
                if health_data:
                    status[component] = json.loads(health_data)
                else:
                    status[component] = self._health_status.get(component, {
                        'status': False,
                        'last_check': None
                    })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {}

    async def get_component_health(self, component: str) -> Optional[Dict]:
        """Get health status of a specific component"""
        try:
            health_data = await self.redis.get(f"health:{component}")
            if health_data:
                return json.loads(health_data)
            return self._health_status.get(component)
            
        except Exception as e:
            logger.error(f"Error getting component health: {e}")
            return None

    def is_healthy(self) -> bool:
        """Check if all components are healthy"""
        return all(
            status.get('status', False)
            for status in self._health_status.values()
        ) 
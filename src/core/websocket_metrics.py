"""
WebSocket metrics collection and monitoring
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging
from collections import deque
import statistics

logger = logging.getLogger(__name__)

class WebSocketMetrics:
    def __init__(self, max_samples: int = 1000):
        self.metrics: Dict[str, Any] = {
            'connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'latency': deque(maxlen=max_samples),
            'user_connections': {},
            'room_subscriptions': {},
            'message_types': {},
            'error_types': {},
            'last_updated': datetime.now()
        }
        self._lock = asyncio.Lock()
        
    async def increment(self, metric: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a metric with optional labels"""
        async with self._lock:
            if metric in self.metrics:
                if isinstance(self.metrics[metric], dict):
                    if labels:
                        key = '_'.join(f"{k}={v}" for k, v in labels.items())
                        self.metrics[metric][key] = self.metrics[metric].get(key, 0) + value
                    else:
                        self.metrics[metric] += value
                else:
                    self.metrics[metric] += value
            self.metrics['last_updated'] = datetime.now()
            
    async def increment_connections(self):
        """Increment connection count"""
        await self.increment('connections')
        
    async def decrement_connections(self):
        """Decrement connection count"""
        async with self._lock:
            if self.metrics['connections'] > 0:
                self.metrics['connections'] -= 1
                self.metrics['last_updated'] = datetime.now()
                
    async def increment_messages(self):
        """Increment message count"""
        await self.increment('messages_sent')
            
    async def record_latency(self, latency_ms: float):
        """Record a latency measurement"""
        async with self._lock:
            self.metrics['latency'].append(latency_ms)
            
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics with computed statistics"""
        async with self._lock:
            metrics = self.metrics.copy()
            
            # Calculate latency statistics
            if metrics['latency']:
                metrics['latency_stats'] = {
                    'min': min(metrics['latency']),
                    'max': max(metrics['latency']),
                    'avg': statistics.mean(metrics['latency']),
                    'p95': statistics.quantiles(metrics['latency'], n=20)[18],
                    'p99': statistics.quantiles(metrics['latency'], n=100)[98]
                }
            
            # Calculate rates
            time_diff = (datetime.now() - metrics['last_updated']).total_seconds()
            if time_diff > 0:
                metrics['rates'] = {
                    'messages_per_second': metrics['messages_received'] / time_diff,
                    'errors_per_second': metrics['errors'] / time_diff
                }
            
            return metrics
            
    async def reset(self):
        """Reset all metrics"""
        async with self._lock:
            self.metrics = {
                'connections': 0,
                'messages_sent': 0,
                'messages_received': 0,
                'errors': 0,
                'latency': deque(maxlen=self.metrics['latency'].maxlen),
                'user_connections': {},
                'room_subscriptions': {},
                'message_types': {},
                'error_types': {},
                'last_updated': datetime.now()
            }
            
    async def alert(self, metric: str, threshold: float, message: str):
        """Generate an alert if a metric exceeds threshold"""
        async with self._lock:
            if metric in self.metrics:
                value = self.metrics[metric]
                if value > threshold:
                    logger.warning(f"Alert: {message} (Current value: {value}, Threshold: {threshold})")
                    return True
            return False 
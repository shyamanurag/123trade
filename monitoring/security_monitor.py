"""
Security Monitoring Module
Tracks security events and generates alerts
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
from dataclasses import dataclass
import redis.asyncio as redis
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
SECURITY_EVENTS = Counter(
    'security_events_total',
    'Total number of security events',
    ['event_type', 'severity']
)

AUTH_ATTEMPTS = Counter(
    'auth_attempts_total',
    'Total number of authentication attempts',
    ['status']
)

RATE_LIMIT_HITS = Counter(
    'rate_limit_hits_total',
    'Number of rate limit hits',
    ['endpoint']
)

WEBHOOK_VERIFICATIONS = Counter(
    'webhook_verifications_total',
    'Number of webhook verifications',
    ['status']
)

@dataclass
class SecurityEvent:
    timestamp: datetime
    event_type: str
    severity: str
    details: Dict
    source_ip: str
    user_id: Optional[str] = None

class SecurityMonitor:
    def __init__(self, config: Dict, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.alert_thresholds = config.get('security_monitoring', {}).get('alert_thresholds', {})
        self.alert_channels = config.get('security_monitoring', {}).get('alert_channels', [])
        self._event_buffer = []
        self._buffer_lock = asyncio.Lock()
        self._alert_task = None

    async def start(self):
        """Start the security monitor"""
        self._alert_task = asyncio.create_task(self._process_alerts())
        logger.info("Security monitor started")

    async def stop(self):
        """Stop the security monitor"""
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
        logger.info("Security monitor stopped")

    async def record_event(self, event: SecurityEvent):
        """Record a security event"""
        async with self._buffer_lock:
            self._event_buffer.append(event)
            
            # Update Prometheus metrics
            SECURITY_EVENTS.labels(
                event_type=event.event_type,
                severity=event.severity
            ).inc()
            
            # Store in Redis for persistence
            await self._store_event(event)
            
            # Check if we need to flush the buffer
            if len(self._event_buffer) >= 100:
                await self._flush_buffer()

    async def _store_event(self, event: SecurityEvent):
        """Store event in Redis"""
        try:
            event_data = {
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'severity': event.severity,
                'details': event.details,
                'source_ip': event.source_ip,
                'user_id': event.user_id
            }
            
            # Store in Redis with TTL
            key = f"security_event:{event.timestamp.timestamp()}"
            await self.redis.setex(
                key,
                timedelta(days=30),  # Keep events for 30 days
                json.dumps(event_data)
            )
            
        except Exception as e:
            logger.error(f"Error storing security event: {e}")

    async def _flush_buffer(self):
        """Flush event buffer to persistent storage"""
        if not self._event_buffer:
            return
            
        async with self._buffer_lock:
            events = self._event_buffer
            self._event_buffer = []
            
            # Store events in bulk
            pipeline = self.redis.pipeline()
            for event in events:
                await self._store_event(event)
            await pipeline.execute()

    async def _process_alerts(self):
        """Process events and generate alerts"""
        while True:
            try:
                # Get recent events
                recent_events = await self._get_recent_events()
                
                # Check thresholds
                alerts = await self._check_thresholds(recent_events)
                
                # Send alerts
                if alerts:
                    await self._send_alerts(alerts)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing alerts: {e}")
                await asyncio.sleep(60)

    async def _get_recent_events(self, window: int = 300) -> List[SecurityEvent]:
        """Get recent events from Redis"""
        try:
            # Get keys for recent events
            now = datetime.now()
            start_time = now - timedelta(seconds=window)
            
            # Scan Redis for recent events
            events = []
            async for key in self.redis.scan_iter("security_event:*"):
                event_data = await self.redis.get(key)
                if event_data:
                    event_dict = json.loads(event_data)
                    event = SecurityEvent(
                        timestamp=datetime.fromisoformat(event_dict['timestamp']),
                        event_type=event_dict['event_type'],
                        severity=event_dict['severity'],
                        details=event_dict['details'],
                        source_ip=event_dict['source_ip'],
                        user_id=event_dict.get('user_id')
                    )
                    if event.timestamp >= start_time:
                        events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []

    async def _check_thresholds(self, events: List[SecurityEvent]) -> List[Dict]:
        """Check if any thresholds are exceeded"""
        alerts = []
        
        # Group events by type
        event_counts = {}
        for event in events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        
        # Check each threshold
        for event_type, threshold in self.alert_thresholds.items():
            if event_counts.get(event_type, 0) >= threshold:
                alerts.append({
                    'type': 'threshold_exceeded',
                    'event_type': event_type,
                    'count': event_counts[event_type],
                    'threshold': threshold,
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts

    async def _send_alerts(self, alerts: List[Dict]):
        """Send alerts through configured channels"""
        for alert in alerts:
            for channel in self.alert_channels:
                try:
                    if channel['type'] == 'email':
                        await self._send_email_alert(alert, channel)
                    elif channel['type'] == 'webhook':
                        await self._send_webhook_alert(alert, channel)
                    elif channel['type'] == 'slack':
                        await self._send_slack_alert(alert, channel)
                except Exception as e:
                    logger.error(f"Error sending alert to {channel['type']}: {e}")

    async def _send_email_alert(self, alert: Dict, channel: Dict):
        """Send alert via email"""
        # Implement email sending logic
        pass

    async def _send_webhook_alert(self, alert: Dict, channel: Dict):
        """Send alert via webhook"""
        # Implement webhook sending logic
        pass

    async def _send_slack_alert(self, alert: Dict, channel: Dict):
        """Send alert via Slack"""
        # Implement Slack sending logic
        pass

    async def get_security_metrics(self) -> Dict:
        """Get security metrics for monitoring"""
        try:
            metrics = {
                'total_events': await self._get_total_events(),
                'events_by_type': await self._get_events_by_type(),
                'events_by_severity': await self._get_events_by_severity(),
                'recent_alerts': await self._get_recent_alerts()
            }
            return metrics
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}")
            return {} 
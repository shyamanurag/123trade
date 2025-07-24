"""
Event Monitor for Trading System
Monitors and tracks trading events for analysis and debugging
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

class EventMonitor:
    """Monitors and tracks trading events"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.event_counts = defaultdict(int)
        self.error_events = deque(maxlen=100)
        self.performance_metrics = defaultdict(list)
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for monitoring"""
        # This will be implemented when event bus is available
        pass
    
    def record_event(self, event_type: str, data: Dict, timestamp: Optional[datetime] = None):
        """Record an event for monitoring"""
        if timestamp is None:
            timestamp = datetime.now()
        
        event = {
            'type': event_type,
            'data': data,
            'timestamp': timestamp.isoformat(),
            'id': f"{event_type}_{timestamp.timestamp()}"
        }
        
        self.events.append(event)
        self.event_counts[event_type] += 1
        
        # Track performance metrics
        if 'latency' in data:
            self.performance_metrics[f"{event_type}_latency"].append(data['latency'])
        
        logger.debug(f"Event recorded: {event_type}")
    
    def record_error(self, error_type: str, error_message: str, context: Dict = None):
        """Record an error event"""
        error_event = {
            'type': 'error',
            'error_type': error_type,
            'message': error_message,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.error_events.append(error_event)
        self.event_counts['error'] += 1
        
        logger.error(f"Error recorded: {error_type} - {error_message}")
    
    def get_event_summary(self) -> Dict:
        """Get summary of recorded events"""
        return {
            'total_events': len(self.events),
            'event_counts': dict(self.event_counts),
            'error_count': len(self.error_events),
            'recent_errors': list(self.error_events)[-10:],  # Last 10 errors
            'performance_metrics': {
                k: {
                    'count': len(v),
                    'avg': sum(v) / len(v) if v else 0,
                    'min': min(v) if v else 0,
                    'max': max(v) if v else 0
                }
                for k, v in self.performance_metrics.items()
            }
        }
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict]:
        """Get events of a specific type"""
        return [
            event for event in self.events 
            if event['type'] == event_type
        ][-limit:]
    
    def get_recent_events(self, minutes: int = 60) -> List[Dict]:
        """Get events from the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            event for event in self.events
            if datetime.fromisoformat(event['timestamp']) > cutoff
        ]
    
    def clear_old_events(self, days: int = 7):
        """Clear events older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        # Clear old events from deque
        while self.events and datetime.fromisoformat(self.events[0]['timestamp']) < cutoff:
            self.events.popleft()
        
        # Clear old error events
        while self.error_events and datetime.fromisoformat(self.error_events[0]['timestamp']) < cutoff:
            self.error_events.popleft()
        
        logger.info(f"Cleared events older than {days} days")
    
    async def start_monitoring(self):
        """Start the event monitoring service"""
        logger.info("Starting event monitoring service")
        
        # Start periodic cleanup task
        asyncio.create_task(self._cleanup_task())
        
        # Start performance monitoring task
        asyncio.create_task(self._performance_monitoring_task())
    
    async def stop_monitoring(self):
        """Stop the event monitoring service"""
        logger.info("Stopping event monitoring service")
    
    async def _cleanup_task(self):
        """Periodic cleanup of old events"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.clear_old_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def _performance_monitoring_task(self):
        """Monitor performance metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Log performance summary
                summary = self.get_event_summary()
                if summary['total_events'] > 0:
                    logger.info(f"Event monitoring summary: {summary['total_events']} total events, {summary['error_count']} errors")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring task: {e}") 
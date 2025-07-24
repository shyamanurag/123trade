"""
Enhanced Monitoring and Observability System
Comprehensive monitoring with metrics, alerting, distributed tracing, and real-time dashboards
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
import json
import psutil
import threading
from collections import deque, defaultdict
from functools import wraps

# Prometheus metrics
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available - metrics will be collected internally")

logger = logging.getLogger(__name__)

# Metric types
class MetricType(str, Enum):
    """Types of metrics for classification"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"

# Alert levels
class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    quantiles: Optional[List[float]] = None  # For summaries

@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 0.8", "< 100"
    threshold: float
    duration: int  # seconds
    level: AlertLevel
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class TraceSpan:
    """Distributed tracing span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "in_progress"  # in_progress, success, error

class InternalMetricsCollector:
    """Internal metrics collector when Prometheus is not available"""
    
    def __init__(self):
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.summaries: Dict[str, List[float]] = defaultdict(list)
        self.info: Dict[str, Dict[str, str]] = {}
        self.lock = threading.Lock()
    
    def inc_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment counter"""
        key = self._make_key(name, labels)
        with self.lock:
            self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set gauge value"""
        key = self._make_key(name, labels)
        with self.lock:
            self.gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe histogram value"""
        key = self._make_key(name, labels)
        with self.lock:
            self.histograms[key].append(value)
            # Keep only last 1000 observations
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
    
    def observe_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe summary value"""
        key = self._make_key(name, labels)
        with self.lock:
            self.summaries[key].append(value)
            # Keep only last 1000 observations
            if len(self.summaries[key]) > 1000:
                self.summaries[key] = self.summaries[key][-1000:]
    
    def set_info(self, name: str, info_dict: Dict[str, str]):
        """Set info metric"""
        with self.lock:
            self.info[name] = info_dict
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create key from name and labels"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self.lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {},
                "summaries": {},
                "info": dict(self.info)
            }
            
            # Calculate histogram statistics
            for key, values in self.histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "p50": self._percentile(values, 0.5),
                        "p95": self._percentile(values, 0.95),
                        "p99": self._percentile(values, 0.99)
                    }
            
            # Calculate summary statistics
            for key, values in self.summaries.items():
                if values:
                    summary["summaries"][key] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values)
                    }
        
        return summary
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

class DistributedTracer:
    """Distributed tracing implementation"""
    
    def __init__(self, max_spans: int = 10000):
        self.spans: Dict[str, TraceSpan] = {}
        self.active_spans: Dict[str, str] = {}  # thread_id -> span_id
        self.max_spans = max_spans
        self.lock = threading.Lock()
    
    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new span"""
        span_id = str(uuid.uuid4())
        thread_id = str(threading.get_ident())
        
        # If no parent specified, use current active span
        if parent_span_id is None and thread_id in self.active_spans:
            parent_span_id = self.active_spans[thread_id]
        
        # Generate trace ID
        trace_id = parent_span_id.split('-')[0] if parent_span_id else str(uuid.uuid4())
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            tags=tags or {}
        )
        
        with self.lock:
            self.spans[span_id] = span
            self.active_spans[thread_id] = span_id
            
            # Clean up old spans if needed
            if len(self.spans) > self.max_spans:
                oldest_spans = sorted(
                    self.spans.items(),
                    key=lambda x: x[1].start_time
                )[:len(self.spans) - self.max_spans + 1000]
                
                for old_span_id, _ in oldest_spans:
                    del self.spans[old_span_id]
        
        return span_id
    
    def finish_span(self, span_id: str, status: str = "success", tags: Optional[Dict[str, Any]] = None):
        """Finish a span"""
        with self.lock:
            if span_id in self.spans:
                span = self.spans[span_id]
                span.end_time = datetime.now()
                span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
                span.status = status
                
                if tags:
                    span.tags.update(tags)
        
        # Remove from active spans
        thread_id = str(threading.get_ident())
        if thread_id in self.active_spans and self.active_spans[thread_id] == span_id:
            del self.active_spans[thread_id]
    
    def add_log(self, span_id: str, message: str, level: str = "info", **kwargs):
        """Add log to span"""
        with self.lock:
            if span_id in self.spans:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                    "message": message,
                    **kwargs
                }
                self.spans[span_id].logs.append(log_entry)
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace"""
        with self.lock:
            return [span for span in self.spans.values() if span.trace_id == trace_id]
    
    def get_span_metrics(self) -> Dict[str, Any]:
        """Get span metrics"""
        with self.lock:
            total_spans = len(self.spans)
            active_spans = len(self.active_spans)
            
            # Calculate operation statistics
            operation_stats = defaultdict(lambda: {"count": 0, "durations": []})
            for span in self.spans.values():
                operation_stats[span.operation_name]["count"] += 1
                if span.duration_ms is not None:
                    operation_stats[span.operation_name]["durations"].append(span.duration_ms)
            
            # Calculate averages
            for op_name, stats in operation_stats.items():
                durations = stats["durations"]
                if durations:
                    stats["avg_duration_ms"] = sum(durations) / len(durations)
                    stats["max_duration_ms"] = max(durations)
                    stats["min_duration_ms"] = min(durations)
                else:
                    stats["avg_duration_ms"] = 0
                    stats["max_duration_ms"] = 0
                    stats["min_duration_ms"] = 0
                
                # Remove raw durations from output
                del stats["durations"]
            
            return {
                "total_spans": total_spans,
                "active_spans": active_spans,
                "operation_stats": dict(operation_stats)
            }

class AlertManager:
    """Alert management and notification system"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.notification_handlers: List[Callable] = []
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
    
    def add_notification_handler(self, handler: Callable):
        """Add notification handler"""
        self.notification_handlers.append(handler)
    
    def check_metrics(self, metrics: Dict[str, float]):
        """Check metrics against alert rules"""
        current_time = datetime.now()
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            metric_value = metrics.get(rule.metric_name)
            if metric_value is None:
                continue
            
            # Evaluate condition
            triggered = self._evaluate_condition(metric_value, rule.condition, rule.threshold)
            
            if triggered:
                # Check if this is a new alert or continuing alert
                if rule_name not in self.active_alerts:
                    # New alert
                    alert = {
                        "rule_name": rule_name,
                        "description": rule.description,
                        "level": rule.level.value,
                        "metric_name": rule.metric_name,
                        "current_value": metric_value,
                        "threshold": rule.threshold,
                        "triggered_at": current_time.isoformat(),
                        "duration": 0
                    }
                    
                    self.active_alerts[rule_name] = alert
                    self.alert_history.append(alert.copy())
                    rule.trigger_count += 1
                    rule.last_triggered = current_time
                    
                    # Send notification
                    self._send_notifications(alert)
                    
                    logger.warning(f"Alert triggered: {rule_name} - {rule.description}")
                else:
                    # Update existing alert
                    alert = self.active_alerts[rule_name]
                    alert["current_value"] = metric_value
                    alert["duration"] = (current_time - datetime.fromisoformat(alert["triggered_at"])).total_seconds()
            else:
                # Alert resolved
                if rule_name in self.active_alerts:
                    resolved_alert = self.active_alerts.pop(rule_name)
                    resolved_alert["resolved_at"] = current_time.isoformat()
                    resolved_alert["status"] = "resolved"
                    
                    self.alert_history.append(resolved_alert)
                    
                    # Send resolution notification
                    self._send_notifications(resolved_alert)
                    
                    logger.info(f"Alert resolved: {rule_name}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition"""
        condition = condition.strip()
        
        if condition.startswith(">"):
            return value > threshold
        elif condition.startswith(">="):
            return value >= threshold
        elif condition.startswith("<"):
            return value < threshold
        elif condition.startswith("<="):
            return value <= threshold
        elif condition.startswith("=="):
            return value == threshold
        elif condition.startswith("!="):
            return value != threshold
        else:
            return False
    
    def _send_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history"""
        return list(self.alert_history)[-limit:]

class PerformanceMonitor:
    """Performance monitoring for system resources"""
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)
        self.monitoring = False
    
    async def start_monitoring(self, interval: int = 30):
        """Start performance monitoring"""
        self.monitoring = True
        while self.monitoring:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_latest_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest performance metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages and peaks
        cpu_values = [m.get("cpu_usage_percent", 0) for m in recent_metrics]
        memory_values = [m.get("memory_usage_percent", 0) for m in recent_metrics]
        disk_values = [m.get("disk_usage_percent", 0) for m in recent_metrics]
        
        return {
            "period_minutes": minutes,
            "sample_count": len(recent_metrics),
            "cpu_usage": {
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0
            },
            "memory_usage": {
                "avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0
            },
            "disk_usage": {
                "avg": sum(disk_values) / len(disk_values) if disk_values else 0,
                "max": max(disk_values) if disk_values else 0,
                "min": min(disk_values) if disk_values else 0
            }
        }

class EnhancedMonitoringSystem:
    """Main monitoring system that coordinates all components"""
    
    def __init__(self):
        self.metrics_collector = InternalMetricsCollector()
        self.tracer = DistributedTracer()
        self.alert_manager = AlertManager()
        self.performance_monitor = PerformanceMonitor()
        
        # Prometheus registry if available
        self.prometheus_registry = None
        self.prometheus_metrics = {}
        
        if PROMETHEUS_AVAILABLE:
            self.prometheus_registry = CollectorRegistry()
            self._setup_prometheus_metrics()
        
        # Setup default alert rules
        self._setup_default_alerts()
        
        logger.info("Enhanced monitoring system initialized")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # Define core metrics
        metrics_definitions = [
            MetricDefinition("http_requests_total", "Total HTTP requests", MetricType.COUNTER, ["method", "endpoint", "status"]),
            MetricDefinition("http_request_duration_seconds", "HTTP request duration", MetricType.HISTOGRAM, ["method", "endpoint"]),
            MetricDefinition("trading_operations_total", "Total trading operations", MetricType.COUNTER, ["operation", "status"]),
            MetricDefinition("trading_pnl", "Trading P&L", MetricType.GAUGE, ["strategy", "symbol"]),
            MetricDefinition("active_positions", "Number of active positions", MetricType.GAUGE, ["strategy"]),
            MetricDefinition("system_cpu_usage", "System CPU usage", MetricType.GAUGE),
            MetricDefinition("system_memory_usage", "System memory usage", MetricType.GAUGE),
            MetricDefinition("database_connections", "Database connection pool", MetricType.GAUGE, ["status"]),
            MetricDefinition("external_service_calls", "External service calls", MetricType.COUNTER, ["service", "status"]),
            MetricDefinition("error_count", "Error count", MetricType.COUNTER, ["error_type", "severity"])
        ]
        
        for metric_def in metrics_definitions:
            if metric_def.metric_type == MetricType.COUNTER:
                self.prometheus_metrics[metric_def.name] = Counter(
                    metric_def.name, metric_def.description, metric_def.labels, registry=self.prometheus_registry
                )
            elif metric_def.metric_type == MetricType.GAUGE:
                self.prometheus_metrics[metric_def.name] = Gauge(
                    metric_def.name, metric_def.description, metric_def.labels, registry=self.prometheus_registry
                )
            elif metric_def.metric_type == MetricType.HISTOGRAM:
                self.prometheus_metrics[metric_def.name] = Histogram(
                    metric_def.name, metric_def.description, metric_def.labels, 
                    buckets=metric_def.buckets, registry=self.prometheus_registry
                )
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule("high_cpu_usage", "High CPU usage", "system_cpu_usage", ">", 80.0, 300, AlertLevel.WARNING),
            AlertRule("high_memory_usage", "High memory usage", "system_memory_usage", ">", 85.0, 300, AlertLevel.WARNING),
            AlertRule("critical_memory_usage", "Critical memory usage", "system_memory_usage", ">", 95.0, 60, AlertLevel.CRITICAL),
            AlertRule("high_error_rate", "High error rate", "error_count", ">", 10.0, 300, AlertLevel.ERROR),
            AlertRule("trading_loss_limit", "Trading loss limit exceeded", "trading_pnl", "<", -1000.0, 60, AlertLevel.CRITICAL),
        ]
        
        for rule in default_rules:
            self.alert_manager.add_rule(rule)
    
    @contextmanager
    def trace(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """Context manager for tracing operations"""
        span_id = self.tracer.start_span(operation_name, tags=tags)
        try:
            yield span_id
            self.tracer.finish_span(span_id, "success")
        except Exception as e:
            self.tracer.finish_span(span_id, "error", {"error": str(e)})
            self.record_error("trace_error", str(e))
            raise
    
    @asynccontextmanager
    async def async_trace(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """Async context manager for tracing operations"""
        span_id = self.tracer.start_span(operation_name, tags=tags)
        try:
            yield span_id
            self.tracer.finish_span(span_id, "success")
        except Exception as e:
            self.tracer.finish_span(span_id, "error", {"error": str(e)})
            self.record_error("trace_error", str(e))
            raise
    
    def record_metric(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        # Record in internal collector
        if name.endswith("_total") or name.endswith("_count"):
            self.metrics_collector.inc_counter(name, value, labels)
        else:
            self.metrics_collector.set_gauge(name, value, labels)
        
        # Record in Prometheus if available
        if PROMETHEUS_AVAILABLE and name in self.prometheus_metrics:
            metric = self.prometheus_metrics[name]
            if labels:
                if hasattr(metric, 'labels'):
                    metric.labels(**labels).inc(value) if hasattr(metric, 'inc') else metric.labels(**labels).set(value)
                else:
                    metric.inc(value) if hasattr(metric, 'inc') else metric.set(value)
            else:
                metric.inc(value) if hasattr(metric, 'inc') else metric.set(value)
    
    def record_timing(self, name: str, duration_seconds: float, labels: Optional[Dict[str, str]] = None):
        """Record timing metric"""
        # Record in internal collector
        self.metrics_collector.observe_histogram(name, duration_seconds, labels)
        
        # Record in Prometheus if available
        if PROMETHEUS_AVAILABLE and name in self.prometheus_metrics:
            metric = self.prometheus_metrics[name]
            if labels:
                metric.labels(**labels).observe(duration_seconds)
            else:
                metric.observe(duration_seconds)
    
    def record_error(self, error_type: str, error_message: str, severity: str = "error"):
        """Record error occurrence"""
        self.record_metric("error_count", 1, {"error_type": error_type, "severity": severity})
        
        # Log error details
        logger.error(f"Error recorded: {error_type} - {error_message}")
    
    async def start_monitoring(self):
        """Start all monitoring components"""
        # Start performance monitoring
        asyncio.create_task(self.performance_monitor.start_monitoring())
        
        # Start alert checking loop
        asyncio.create_task(self._alert_checking_loop())
        
        logger.info("Enhanced monitoring started")
    
    async def _alert_checking_loop(self):
        """Periodic alert checking"""
        while True:
            try:
                # Get current metrics
                metrics = {}
                
                # Add system metrics
                latest_perf = self.performance_monitor.get_latest_metrics()
                if latest_perf:
                    metrics.update({
                        "system_cpu_usage": latest_perf.get("cpu_usage_percent", 0),
                        "system_memory_usage": latest_perf.get("memory_usage_percent", 0)
                    })
                
                # Add internal metrics
                internal_metrics = self.metrics_collector.get_metrics_summary()
                for gauge_name, value in internal_metrics.get("gauges", {}).items():
                    metrics[gauge_name] = value
                
                # Check alerts
                self.alert_manager.check_metrics(metrics)
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Alert checking error: {e}")
                await asyncio.sleep(30)
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        return {
            "system_metrics": self.performance_monitor.get_latest_metrics(),
            "performance_summary": self.performance_monitor.get_metrics_summary(60),
            "trace_metrics": self.tracer.get_span_metrics(),
            "active_alerts": self.alert_manager.get_active_alerts(),
            "recent_alerts": self.alert_manager.get_alert_history(10),
            "metric_summary": self.metrics_collector.get_metrics_summary(),
            "monitoring_status": {
                "prometheus_enabled": PROMETHEUS_AVAILABLE,
                "tracing_enabled": True,
                "alerting_enabled": True,
                "performance_monitoring": self.performance_monitor.monitoring
            }
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in exposition format"""
        if PROMETHEUS_AVAILABLE and self.prometheus_registry:
            return generate_latest(self.prometheus_registry)
        return "# Prometheus not available\n"
    
    def add_notification_handler(self, handler: Callable):
        """Add notification handler for alerts"""
        self.alert_manager.add_notification_handler(handler)

# Global monitoring instance
_monitoring_system: Optional[EnhancedMonitoringSystem] = None

def get_monitoring_system() -> EnhancedMonitoringSystem:
    """Get or create global monitoring system"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = EnhancedMonitoringSystem()
    return _monitoring_system

# Decorators for easy monitoring
def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitoring = get_monitoring_system()
            async with monitoring.async_trace(operation_name) as span_id:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    monitoring.record_timing(f"{operation_name}_duration", duration)
                    monitoring.tracer.add_log(span_id, f"Operation completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    monitoring.record_error(operation_name, str(e))
                    monitoring.tracer.add_log(span_id, f"Operation failed after {duration:.3f}s: {str(e)}", "error")
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitoring = get_monitoring_system()
            with monitoring.trace(operation_name) as span_id:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    monitoring.record_timing(f"{operation_name}_duration", duration)
                    monitoring.tracer.add_log(span_id, f"Operation completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    monitoring.record_error(operation_name, str(e))
                    monitoring.tracer.add_log(span_id, f"Operation failed after {duration:.3f}s: {str(e)}", "error")
                    raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Export main components
__all__ = [
    "EnhancedMonitoringSystem",
    "get_monitoring_system",
    "monitor_performance",
    "MetricType",
    "AlertLevel",
    "AlertRule",
    "TraceSpan"
] 
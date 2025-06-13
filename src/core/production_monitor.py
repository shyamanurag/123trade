# monitoring/production_monitor.py
"""
Production-grade logging and monitoring system
Provides real-time metrics, alerts, and comprehensive audit trail
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

import redis
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import structlog
from dataclasses import dataclass, asdict
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = structlog.get_logger()

@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]
    metadata: Dict[str, Any]

class ProductionMonitor:
    """
    Comprehensive monitoring system for production trading
    Features: Metrics collection, alerting, logging, and dashboards
    """

    def __init__(self, config: Dict):
        # Initialize structured logger
        self.logger = self._setup_structured_logging()

        # Redis for real-time metrics
        self.redis_client = redis.Redis(
            host=config.get('redis_host', 'localhost'),
            port=config.get('redis_port', 6379),
            db=config.get('redis_db', 0)
        )

        # InfluxDB for time-series data
        self.influx_client = InfluxDBClient(
            url=config.get('influx_url', 'http://localhost:8086'),
            token=config.get('influx_token', ''),
            org=config.get('influx_org', 'trading')
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

        # Prometheus metrics
        self._setup_prometheus_metrics()

        # Alert thresholds and rules
        self.alert_rules = self._load_alert_rules()

        # Performance tracking
        self.trade_log = deque(maxlen=10000)
        self.metric_history = defaultdict(list)

    def _setup_structured_logging(self) -> structlog.BoundLogger:
        """Configure structured logging for production"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ]
        )
        return structlog.get_logger()

    def _setup_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # Trading metrics
        self.orders_total = Counter(
            'trading_orders_total',
            'Total number of orders placed',
            ['strategy', 'symbol', 'side', 'status']
        )

        self.order_latency = Histogram(
            'trading_order_latency_seconds',
            'Order execution latency',
            ['strategy', 'broker']
        )

        self.positions_active = Gauge(
            'trading_positions_active',
            'Number of active positions',
            ['strategy', 'symbol']
        )

        self.pnl_total = Gauge(
            'trading_pnl_total',
            'Total P&L',
            ['strategy', 'symbol']
        )

        # System metrics
        self.api_calls = Counter(
            'system_api_calls_total',
            'Total API calls',
            ['endpoint', 'status']
        )

        self.orders_per_second = Gauge(
            'system_orders_per_second',
            'Current orders per second rate'
        )

        self.error_rate = Counter(
            'system_errors_total',
            'Total system errors',
            ['component', 'error_type']
        )

        # Risk metrics
        self.risk_utilization = Gauge(
            'risk_utilization_percent',
            'Risk capital utilization percentage'
        )

        self.drawdown_current = Gauge(
            'risk_drawdown_current',
            'Current drawdown percentage'
        )

    def _load_alert_rules(self) -> Dict:
        """Load alert rules and thresholds"""
        return {
            'critical': {
                'daily_loss_percent': -2.0,
                'orders_per_second': 9.0,
                'error_rate_per_minute': 10,
                'api_error_rate': 0.1,
                'position_concentration': 0.3
            },
            'warning': {
                'daily_loss_percent': -1.5,
                'orders_per_second': 7.0,
                'error_rate_per_minute': 5,
                'api_error_rate': 0.05,
                'position_concentration': 0.2
            },
            'info': {
                'winning_streak': 10,
                'losing_streak': 5,
                'idle_minutes': 30
            }
        }

    async def log_order(self, order_data: Dict):
        """Log order with full context"""
        # Structure log entry
        log_entry = self.logger.bind(
            strategy=order_data['strategy'],
            symbol=order_data['symbol'],
            timestamp=datetime.now().isoformat()
        )

        # Update Prometheus metrics
        self.orders_total.labels(
            strategy=order_data['strategy'],
            symbol=order_data['symbol']
        ).inc()

        # Store in Redis for real-time access
        await self._store_redis_metric(
            f"order:{order_data['order_id']}",
            order_data,
            expire=3600
        )

        # Write to InfluxDB
        point = Point("orders") \
            .tag("strategy", order_data['strategy']) \
            .tag("symbol", order_data['symbol']) \
            .tag("side", order_data['side']) \
            .field("price", float(order_data['price'])) \
            .field("quantity", int(order_data['quantity'])) \
            .time(datetime.utcnow())
        self.write_api.write(bucket="trading", record=point)

    async def log_trade_execution(self, trade_data: Dict):
        """Log completed trade with performance metrics"""
        # Calculate metrics
        duration = (datetime.fromisoformat(trade_data['exit_time']) -
                   datetime.fromisoformat(trade_data['entry_time'])).total_seconds()

        # Structured log
        self.logger.info(
            "Trade completed",
            strategy=trade_data['strategy'],
            symbol=trade_data['symbol']
        )

        # Update metrics
        self.pnl_total.labels(
            strategy=trade_data['strategy'],
            symbol=trade_data['symbol']
        ).set(trade_data['cumulative_pnl'])

        # Store trade for analysis
        self.trade_log.append(trade_data)

        # Check for alerts
        await self._check_trade_alerts(trade_data)

    async def log_error(self, error_data: Dict):
        """Log errors with context"""
        self.logger.error(
            error_data.get('message', 'Unknown error'),
            context=error_data.get('context', {})
        )

        # Update error metrics
        self.error_rate.labels().inc()

        # Check if error rate exceeds threshold
        await self._check_error_rate_alerts()

    async def update_system_metrics(self, metrics: Dict):
        """Update system-wide metrics"""
        # Orders per second
        self.orders_per_second.set(metrics.get('orders_per_second', 0))

        # Risk metrics
        self.risk_utilization.set(metrics.get('risk_utilization', 0))
        self.drawdown_current.set(metrics.get('current_drawdown', 0))

        # Active positions
        for strategy, positions in metrics.get('active_positions', {}).items():
            for symbol, count in positions.items():
                self.positions_active.labels(
                    strategy=strategy,
                    symbol=symbol
                ).set(count)

        # Store snapshot
        await self._store_metrics_snapshot(metrics)

        # Check system alerts
        await self._check_system_alerts(metrics)

    async def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        # Get trades from last 24 hours
        recent_trades = [t for t in self.trade_log]
        return {
            'total_trades': len(recent_trades),
            'win_rate': self._calculate_win_rate(recent_trades),
            'avg_profit': self._calculate_avg_profit(recent_trades),
            'max_drawdown': self._calculate_max_drawdown(recent_trades)
        }

    async def _store_redis_metric(self, key: str, value: Any, expire: Optional[int] = None):
        """Store metric in Redis"""
        try:
            if isinstance(value, dict):
                value = json.dumps(value)
            if expire:
                await self.redis_client.setex(key, expire, value)
            else:
                await self.redis_client.set(key, value)
        except Exception as e:
            self.logger.error(f"Redis storage error: {e}")

    async def _store_metrics_snapshot(self, metrics: Dict):
        """Store metrics snapshot in time-series database"""
        try:
            # Create InfluxDB points
            points = []

            # System metrics
            point = Point("system_metrics") \
                .field("orders_per_second", metrics.get('orders_per_second', 0)) \
                .field("risk_utilization", metrics.get('risk_utilization', 0)) \
                .field("active_positions", metrics.get('total_positions', 0)) \
                .field("daily_pnl", metrics.get('daily_pnl', 0)) \
                .time(datetime.utcnow())
            points.append(point)

            # Write all points
            self.write_api.write(bucket="trading", record=points)
        except Exception as e:
            self.logger.error(f"InfluxDB write error: {e}")

    async def _check_trade_alerts(self, trade_data: Dict):
        """Check for trade-based alerts"""
        # Large loss alert
        if trade_data['pnl_percent'] < -1.0:
            await self._send_alert(
                level='WARNING',
                title='Large Loss Detected',
                message=f"Trade {trade_data['trade_id']} lost {trade_data['pnl_percent']:.2f}%",
                context=trade_data
            )

        # Winning/losing streak detection
        recent_trades = self.trade_log[-10:]
        if all(t['pnl'] > 0 for t in recent_trades[-5:]):
            await self._send_alert(
                level='INFO',
                title='Winning Streak',
                message='5 consecutive winning trades',
                context={'trades': recent_trades[-5:]}
            )
        elif all(t['pnl'] < 0 for t in recent_trades[-5:]):
            await self._send_alert(
                level='WARNING',
                title='Losing Streak',
                message='5 consecutive losing trades - Review strategy',
                context={'trades': recent_trades[-5:]}
            )

    async def _check_system_alerts(self, metrics: Dict):
        """Check system-wide alerts"""
        alerts = []

        # Check each metric against thresholds
        ops = metrics.get('orders_per_second', 0)
        if ops > self.alert_rules['critical']['orders_per_second']:
            alerts.append(('CRITICAL', f'Orders per second critical: {ops:.1f}'))
        elif ops > self.alert_rules['warning']['orders_per_second']:
            alerts.append(('WARNING', f'Orders per second high: {ops:.1f}'))

        # Daily loss check
        daily_pnl = metrics.get('daily_pnl_percent', 0)
        if daily_pnl < self.alert_rules['critical']['daily_loss_percent']:
            alerts.append(('CRITICAL', f'Daily loss critical: {daily_pnl:.2f}%'))
        elif daily_pnl < self.alert_rules['warning']['daily_loss_percent']:
            alerts.append(('WARNING', f'Daily loss warning: {daily_pnl:.2f}%'))

        # Send alerts
        for level, message in alerts:
            await self._send_alert(
                level=level,
                title='System Alert',
                message=message,
                context=metrics
            )

    async def _check_error_rate_alerts(self):
        """Check if error rate exceeds thresholds"""
        # Get error count from last minute
        error_count = await self._get_recent_error_count(60)
        if error_count > self.alert_rules['critical']['error_rate_per_minute']:
            await self._send_alert(
                level='CRITICAL',
                title='High Error Rate',
                message=f'{error_count} errors in last minute',
                context={'error_count': error_count}
            )

    async def _send_alert(self, level: str, title: str, message: str, context: Dict):
        """Send alert through configured channels"""
        # Implement based on config (Telegram, Slack, Email, etc.)
        pass

    async def _get_recent_error_count(self, seconds: int) -> int:
        """Get error count from last N seconds"""
        # Implement based on your error tracking
        return 0

    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from trades"""
        if len(trades) == 0:
            return 0.0
        return len([t for t in trades if t['pnl'] > 0]) / len(trades)

    def _calculate_avg_profit(self, trades: List[Dict]) -> float:
        """Calculate average profit from trades"""
        if len(trades) == 0:
            return 0.0
        return sum(t['pnl'] for t in trades) / len(trades)

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown from trades"""
        if len(trades) == 0:
            return 0.0
        max_drawdown = 0.0
        cumulative_max = 0.0
        for t in trades:
            cumulative_max = max(cumulative_max + t['pnl'], 0)
            max_drawdown = max(max_drawdown, cumulative_max - cumulative_max)
        return max_drawdown

    def get_prometheus_metrics(self) -> bytes:
        """Get Prometheus metrics for scraping"""
        return generate_latest(self.registry)

    async def cleanup(self):
        """Cleanup resources"""
        self.influx_client.close()
        await self.redis_client.close()

    # Monitoring Dashboard API
    class MonitoringAPI:
        """REST API for monitoring data"""

        def __init__(self, monitor: ProductionMonitor):
            self.monitor = monitor

        async def get_metrics(self) -> Dict:
            """Get current metrics snapshot"""
            return {
                'timestamp': datetime.now().isoformat(),
                'orders_per_second': float(self.monitor.orders_per_second._value.get()),
                'active_positions': self._get_active_positions(),
                'daily_pnl': self._get_daily_pnl(),
                'risk_utilization': float(self.monitor.risk_utilization._value.get()),
                'recent_alerts': list(self.monitor.alert_history)[-10:]
            }

        async def get_performance_report(self) -> Dict:
            """Get performance report"""
            return await self.monitor.generate_performance_report()

        """Get recent trades"""
        def get_recent_trades(self, limit: int) -> List[Dict]:
            return self.monitor.trade_log[-limit:]

        def _get_active_positions(self) -> int:
            """Get total active positions"""
            total = 0
            for metric in self.monitor.positions_active._metrics.values():
                total += int(metric._value)
            return total

        def _get_daily_pnl(self) -> float:
            """Get total daily P&L"""
            total = 0.0
            for metric in self.monitor.pnl_total._metrics.values():
                total += float(metric._value)
            return total

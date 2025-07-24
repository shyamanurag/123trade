"""
Metrics configuration for the trading system.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)
from typing import Dict, Any

# Trading metrics
order_counter = Counter(
    'trading_system_orders_total',
    'Total number of orders',
    ['symbol', 'side', 'type', 'status']
)

position_gauge = Gauge(
    'trading_system_positions',
    'Current positions',
    ['symbol', 'side']
)

pnl_gauge = Gauge(
    'trading_system_pnl',
    'Current PnL',
    ['symbol']
)

order_latency = Histogram(
    'trading_system_order_latency_seconds',
    'Order execution latency in seconds',
    ['symbol', 'type']
)

# Risk metrics
risk_level_gauge = Gauge(
    'trading_system_risk_level',
    'Current risk level',
    ['type']
)

drawdown_gauge = Gauge(
    'trading_system_drawdown',
    'Current drawdown',
    ['type']
)

correlation_gauge = Gauge(
    'trading_system_correlation',
    'Asset correlation',
    ['asset1', 'asset2']
)

# Market data metrics
market_data_latency = Histogram(
    'trading_system_market_data_latency_seconds',
    'Market data update latency in seconds',
    ['symbol']
)

price_gauge = Gauge(
    'trading_system_price',
    'Current price',
    ['symbol']
)

volume_gauge = Gauge(
    'trading_system_volume',
    'Current volume',
    ['symbol']
)

# System metrics
memory_usage = Gauge(
    'trading_system_memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage = Gauge(
    'trading_system_cpu_usage_percent',
    'CPU usage percentage'
)

disk_usage = Gauge(
    'trading_system_disk_usage_bytes',
    'Disk usage in bytes'
)

# API metrics
api_request_counter = Counter(
    'trading_system_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_latency = Histogram(
    'trading_system_api_latency_seconds',
    'API request latency in seconds',
    ['method', 'endpoint']
)

# Database metrics
db_connection_gauge = Gauge(
    'trading_system_db_connections',
    'Number of active database connections'
)

db_query_latency = Histogram(
    'trading_system_db_query_latency_seconds',
    'Database query latency in seconds',
    ['operation']
)

# Redis metrics
redis_connection_gauge = Gauge(
    'trading_system_redis_connections',
    'Number of active Redis connections'
)

redis_operation_latency = Histogram(
    'trading_system_redis_operation_latency_seconds',
    'Redis operation latency in seconds',
    ['operation']
)

def setup_metrics() -> None:
    """Initialize metrics configuration."""
    # Initialize system metrics
    memory_usage.set(0)
    cpu_usage.set(0)
    disk_usage.set(0)
    
    # Initialize database metrics
    db_connection_gauge.set(0)
    
    # Initialize Redis metrics
    redis_connection_gauge.set(0)

def get_metrics() -> bytes:
    """
    Get the latest metrics in Prometheus format.
    
    Returns:
        bytes: Latest metrics data
    """
    return generate_latest(REGISTRY)

def update_system_metrics(metrics: Dict[str, Any]) -> None:
    """
    Update system metrics.
    
    Args:
        metrics: Dictionary containing system metrics
    """
    if 'memory_usage' in metrics:
        memory_usage.set(metrics['memory_usage'])
    if 'cpu_usage' in metrics:
        cpu_usage.set(metrics['cpu_usage'])
    if 'disk_usage' in metrics:
        disk_usage.set(metrics['disk_usage'])

def update_trading_metrics(metrics: Dict[str, Any]) -> None:
    """
    Update trading metrics.
    
    Args:
        metrics: Dictionary containing trading metrics
    """
    if 'positions' in metrics:
        for symbol, position in metrics['positions'].items():
            position_gauge.labels(
                symbol=symbol,
                side=position['side']
            ).set(position['size'])
    
    if 'pnl' in metrics:
        for symbol, pnl in metrics['pnl'].items():
            pnl_gauge.labels(symbol=symbol).set(pnl)
    
    if 'risk_level' in metrics:
        for risk_type, level in metrics['risk_level'].items():
            risk_level_gauge.labels(type=risk_type).set(level)

def update_market_metrics(metrics: Dict[str, Any]) -> None:
    """
    Update market data metrics.
    
    Args:
        metrics: Dictionary containing market data metrics
    """
    if 'prices' in metrics:
        for symbol, price in metrics['prices'].items():
            price_gauge.labels(symbol=symbol).set(price)
    
    if 'volumes' in metrics:
        for symbol, volume in metrics['volumes'].items():
            volume_gauge.labels(symbol=symbol).set(volume) 
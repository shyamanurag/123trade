"""
Advanced Grafana Dashboard Generator
Creates comprehensive monitoring dashboards for trading system
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    title: str
    tags: List[str]
    refresh_interval: str = "5s"
    time_range: str = "1h"
    timezone: str = "UTC"
    auto_refresh: bool = True

@dataclass
class PanelConfig:
    """Panel configuration"""
    title: str
    panel_type: str
    targets: List[Dict]
    grid_pos: Dict[str, int]
    thresholds: Optional[List[Dict]] = None
    unit: str = "short"
    decimals: int = 2
    legend: Optional[Dict] = None

class GrafanaDashboardGenerator:
    """Generate Grafana dashboards for trading system monitoring"""
    
    def __init__(self, datasource_name: str = "Prometheus"):
        self.datasource = datasource_name
        self.dashboard_uid_counter = 1000
        
    def generate_all_dashboards(self) -> Dict[str, Dict]:
        """Generate all monitoring dashboards"""
        dashboards = {
            'trading_overview': self.create_trading_overview_dashboard(),
            'system_health': self.create_system_health_dashboard(),
            'security_monitoring': self.create_security_monitoring_dashboard(),
            'business_metrics': self.create_business_metrics_dashboard(),
            'performance_analytics': self.create_performance_analytics_dashboard(),
            'risk_management': self.create_risk_management_dashboard(),
            'infrastructure': self.create_infrastructure_dashboard()
        }
        
        return dashboards
    
    def create_trading_overview_dashboard(self) -> Dict:
        """Create main trading overview dashboard"""
        config = DashboardConfig(
            title="Trading System Overview",
            tags=["trading", "overview", "real-time"],
            refresh_interval="5s"
        )
        
        panels = [
            # Top row - Key metrics
            self._create_stat_panel(
                title="Active Positions",
                query="trading_positions_active_total",
                grid_pos={"h": 4, "w": 3, "x": 0, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 50}, {"color": "red", "value": 100}]
            ),
            
            self._create_stat_panel(
                title="Daily P&L",
                query="sum(trading_pnl_daily_total)",
                grid_pos={"h": 4, "w": 3, "x": 3, "y": 0},
                unit="currencyUSD",
                thresholds=[{"color": "red", "value": -10000}, {"color": "yellow", "value": 0}, {"color": "green", "value": 5000}]
            ),
            
            self._create_stat_panel(
                title="Win Rate %",
                query="(sum(trading_winning_trades_total) / sum(trading_total_trades_total)) * 100",
                grid_pos={"h": 4, "w": 3, "x": 6, "y": 0},
                unit="percent",
                thresholds=[{"color": "red", "value": 30}, {"color": "yellow", "value": 60}, {"color": "green", "value": 75}]
            ),
            
            self._create_stat_panel(
                title="Orders/Min",
                query="rate(trading_orders_total[1m]) * 60",
                grid_pos={"h": 4, "w": 3, "x": 9, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 100}, {"color": "red", "value": 200}]
            ),
            
            # Second row - Real-time charts
            self._create_time_series_panel(
                title="P&L Over Time",
                queries=[
                    "sum(trading_pnl_total) by (strategy)",
                    "sum(trading_pnl_unrealized_total)",
                    "sum(trading_pnl_realized_total)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 4},
                unit="currencyUSD",
                legend={"displayMode": "table", "placement": "bottom"}
            ),
            
            self._create_time_series_panel(
                title="Order Flow",
                queries=[
                    "rate(trading_orders_total{status='filled'}[5m]) * 300",
                    "rate(trading_orders_total{status='rejected'}[5m]) * 300",
                    "rate(trading_orders_total{status='cancelled'}[5m]) * 300"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 4},
                legend={"displayMode": "table", "placement": "bottom"}
            ),
            
            # Third row - Strategy performance
            self._create_time_series_panel(
                title="Strategy Performance",
                queries=[
                    "trading_strategy_pnl_total by (strategy_name)",
                    "trading_strategy_win_rate by (strategy_name)"
                ],
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 12},
                legend={"displayMode": "table", "placement": "right"}
            ),
            
            self._create_pie_chart_panel(
                title="Position Distribution",
                query="trading_positions_value_total by (symbol)",
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 12},
                unit="currencyUSD"
            ),
            
            # Fourth row - Risk metrics
            self._create_gauge_panel(
                title="Portfolio Risk Level",
                query="trading_portfolio_risk_score",
                grid_pos={"h": 6, "w": 4, "x": 0, "y": 20},
                min_value=0,
                max_value=100,
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 60}, {"color": "red", "value": 80}]
            ),
            
            self._create_gauge_panel(
                title="Drawdown %",
                query="trading_max_drawdown_percent",
                grid_pos={"h": 6, "w": 4, "x": 4, "y": 20},
                min_value=0,
                max_value=50,
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 10}, {"color": "red", "value": 20}]
            ),
            
            self._create_time_series_panel(
                title="Market Data Latency",
                queries=[
                    "histogram_quantile(0.50, trading_market_data_latency_seconds)",
                    "histogram_quantile(0.95, trading_market_data_latency_seconds)",
                    "histogram_quantile(0.99, trading_market_data_latency_seconds)"
                ],
                grid_pos={"h": 6, "w": 4, "x": 8, "y": 20},
                unit="s"
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_system_health_dashboard(self) -> Dict:
        """Create system health monitoring dashboard"""
        config = DashboardConfig(
            title="System Health & Performance",
            tags=["system", "health", "performance"],
            refresh_interval="10s"
        )
        
        panels = [
            # System overview
            self._create_stat_panel(
                title="System Uptime",
                query="time() - process_start_time_seconds",
                grid_pos={"h": 4, "w": 3, "x": 0, "y": 0},
                unit="s"
            ),
            
            self._create_stat_panel(
                title="Memory Usage %",
                query="(process_resident_memory_bytes / node_memory_MemTotal_bytes) * 100",
                grid_pos={"h": 4, "w": 3, "x": 3, "y": 0},
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 70}, {"color": "red", "value": 90}]
            ),
            
            self._create_stat_panel(
                title="CPU Usage %",
                query="rate(process_cpu_seconds_total[5m]) * 100",
                grid_pos={"h": 4, "w": 3, "x": 6, "y": 0},
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 70}, {"color": "red", "value": 90}]
            ),
            
            self._create_stat_panel(
                title="Error Rate %",
                query="rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) * 100",
                grid_pos={"h": 4, "w": 3, "x": 9, "y": 0},
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 1}, {"color": "red", "value": 5}]
            ),
            
            # Resource usage over time
            self._create_time_series_panel(
                title="Memory Usage",
                queries=[
                    "process_resident_memory_bytes",
                    "go_memstats_heap_inuse_bytes",
                    "go_memstats_stack_inuse_bytes"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 4},
                unit="bytes"
            ),
            
            self._create_time_series_panel(
                title="CPU Usage",
                queries=[
                    "rate(process_cpu_seconds_total[5m]) * 100",
                    "rate(node_cpu_seconds_total{mode!='idle'}[5m]) * 100"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 4},
                unit="percent"
            ),
            
            # Network and I/O
            self._create_time_series_panel(
                title="Network Traffic",
                queries=[
                    "rate(node_network_receive_bytes_total[5m])",
                    "rate(node_network_transmit_bytes_total[5m])"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 12},
                unit="Bps"
            ),
            
            self._create_time_series_panel(
                title="Disk I/O",
                queries=[
                    "rate(node_disk_read_bytes_total[5m])",
                    "rate(node_disk_written_bytes_total[5m])"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 12},
                unit="Bps"
            ),
            
            # API Performance
            self._create_time_series_panel(
                title="API Response Time",
                queries=[
                    "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
                    "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                    "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 20},
                unit="s"
            ),
            
            self._create_time_series_panel(
                title="Request Rate",
                queries=[
                    "rate(http_requests_total[5m]) by (method, endpoint)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 20}
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_security_monitoring_dashboard(self) -> Dict:
        """Create security monitoring dashboard"""
        config = DashboardConfig(
            title="Security Monitoring",
            tags=["security", "authentication", "threats"],
            refresh_interval="30s"
        )
        
        panels = [
            # Security metrics
            self._create_stat_panel(
                title="Failed Logins (1h)",
                query="increase(auth_attempts_total{status='failed'}[1h])",
                grid_pos={"h": 4, "w": 3, "x": 0, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 10}, {"color": "red", "value": 50}]
            ),
            
            self._create_stat_panel(
                title="Rate Limit Hits",
                query="increase(rate_limit_hits_total[1h])",
                grid_pos={"h": 4, "w": 3, "x": 3, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 100}, {"color": "red", "value": 500}]
            ),
            
            self._create_stat_panel(
                title="Security Events",
                query="increase(security_events_total[1h])",
                grid_pos={"h": 4, "w": 3, "x": 6, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 10}, {"color": "red", "value": 50}]
            ),
            
            self._create_stat_panel(
                title="Active Sessions",
                query="active_sessions_total",
                grid_pos={"h": 4, "w": 3, "x": 9, "y": 0}
            ),
            
            # Authentication trends
            self._create_time_series_panel(
                title="Authentication Attempts",
                queries=[
                    "rate(auth_attempts_total{status='success'}[5m]) * 300",
                    "rate(auth_attempts_total{status='failed'}[5m]) * 300",
                    "rate(auth_attempts_total{status='blocked'}[5m]) * 300"
                ],
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 4}
            ),
            
            self._create_pie_chart_panel(
                title="Auth Methods",
                query="auth_attempts_total by (method)",
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 4}
            ),
            
            # Rate limiting
            self._create_time_series_panel(
                title="Rate Limit Violations",
                queries=[
                    "rate(rate_limit_hits_total[5m]) by (endpoint)",
                    "rate(rate_limit_hits_total[5m]) by (client_type)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 12}
            ),
            
            self._create_time_series_panel(
                title="Security Events by Type",
                queries=[
                    "rate(security_events_total[5m]) by (event_type)",
                    "rate(security_events_total[5m]) by (severity)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 12}
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_business_metrics_dashboard(self) -> Dict:
        """Create business-specific metrics dashboard"""
        config = DashboardConfig(
            title="Business Metrics & KPIs",
            tags=["business", "kpi", "trading"],
            refresh_interval="1m"
        )
        
        panels = [
            # Business KPIs
            self._create_stat_panel(
                title="Total Volume Traded",
                query="sum(trading_volume_total)",
                grid_pos={"h": 4, "w": 3, "x": 0, "y": 0},
                unit="currencyUSD"
            ),
            
            self._create_stat_panel(
                title="Sharpe Ratio",
                query="trading_sharpe_ratio",
                grid_pos={"h": 4, "w": 3, "x": 3, "y": 0},
                decimals=3,
                thresholds=[{"color": "red", "value": 0}, {"color": "yellow", "value": 1}, {"color": "green", "value": 2}]
            ),
            
            self._create_stat_panel(
                title="Max Drawdown",
                query="trading_max_drawdown_amount",
                grid_pos={"h": 4, "w": 3, "x": 6, "y": 0},
                unit="currencyUSD",
                thresholds=[{"color": "green", "value": -5000}, {"color": "yellow", "value": -10000}, {"color": "red", "value": -20000}]
            ),
            
            self._create_stat_panel(
                title="Profit Factor",
                query="trading_profit_factor",
                grid_pos={"h": 4, "w": 3, "x": 9, "y": 0},
                decimals=2,
                thresholds=[{"color": "red", "value": 0}, {"color": "yellow", "value": 1.2}, {"color": "green", "value": 2}]
            ),
            
            # Performance trends
            self._create_time_series_panel(
                title="Cumulative P&L",
                queries=[
                    "sum(trading_pnl_total)",
                    "sum(trading_pnl_total) by (strategy_name)"
                ],
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 4},
                unit="currencyUSD"
            ),
            
            self._create_time_series_panel(
                title="Rolling Sharpe Ratio",
                queries=[
                    "trading_rolling_sharpe_ratio_30d",
                    "trading_rolling_sharpe_ratio_7d"
                ],
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 4}
            ),
            
            # Volume and turnover
            self._create_time_series_panel(
                title="Trading Volume",
                queries=[
                    "rate(trading_volume_total[1h]) * 3600",
                    "rate(trading_volume_total[1h]) * 3600 by (symbol)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 12},
                unit="currencyUSD"
            ),
            
            self._create_time_series_panel(
                title="Trade Frequency",
                queries=[
                    "rate(trading_trades_total[1h]) * 3600",
                    "rate(trading_trades_total[1h]) * 3600 by (strategy_name)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 12}
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_risk_management_dashboard(self) -> Dict:
        """Create risk management dashboard"""
        config = DashboardConfig(
            title="Risk Management",
            tags=["risk", "compliance", "limits"],
            refresh_interval="30s"
        )
        
        panels = [
            # Risk metrics
            self._create_gauge_panel(
                title="VaR (Value at Risk)",
                query="trading_var_95_percent",
                grid_pos={"h": 6, "w": 4, "x": 0, "y": 0},
                min_value=0,
                max_value=100000,
                unit="currencyUSD",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 50000}, {"color": "red", "value": 75000}]
            ),
            
            self._create_gauge_panel(
                title="Position Concentration",
                query="trading_position_concentration_max",
                grid_pos={"h": 6, "w": 4, "x": 4, "y": 0},
                min_value=0,
                max_value=100,
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 20}, {"color": "red", "value": 30}]
            ),
            
            self._create_gauge_panel(
                title="Leverage Ratio",
                query="trading_leverage_ratio",
                grid_pos={"h": 6, "w": 4, "x": 8, "y": 0},
                min_value=0,
                max_value=10,
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 3}, {"color": "red", "value": 5}]
            ),
            
            # Risk trends
            self._create_time_series_panel(
                title="Portfolio Risk Score",
                queries=[
                    "trading_portfolio_risk_score",
                    "trading_portfolio_risk_score by (risk_category)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 6}
            ),
            
            self._create_time_series_panel(
                title="Risk Limits Utilization",
                queries=[
                    "trading_risk_limit_utilization by (limit_type)",
                    "trading_position_limit_utilization by (symbol)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 6},
                unit="percent"
            ),
            
            # Greeks and options risk
            self._create_time_series_panel(
                title="Portfolio Greeks",
                queries=[
                    "trading_portfolio_delta",
                    "trading_portfolio_gamma",
                    "trading_portfolio_theta",
                    "trading_portfolio_vega"
                ],
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 14}
            ),
            
            self._create_time_series_panel(
                title="Volatility Risk",
                queries=[
                    "trading_implied_volatility_avg",
                    "trading_realized_volatility_30d"
                ],
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 14},
                unit="percent"
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_performance_analytics_dashboard(self) -> Dict:
        """Create performance analytics dashboard"""
        config = DashboardConfig(
            title="Performance Analytics",
            tags=["performance", "analytics", "optimization"],
            refresh_interval="1m"
        )
        
        panels = [
            # Performance distribution
            self._create_heatmap_panel(
                title="P&L Heatmap by Hour",
                query="sum(rate(trading_pnl_total[1h])) by (hour)",
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 0}
            ),
            
            self._create_histogram_panel(
                title="Trade P&L Distribution",
                query="histogram_quantile(0.5, trading_trade_pnl_bucket)",
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 0}
            ),
            
            # Strategy comparison
            self._create_table_panel(
                title="Strategy Performance",
                queries=[
                    "trading_strategy_win_rate by (strategy_name)",
                    "trading_strategy_profit_factor by (strategy_name)",
                    "trading_strategy_sharpe_ratio by (strategy_name)",
                    "trading_strategy_max_drawdown by (strategy_name)"
                ],
                grid_pos={"h": 8, "w": 12, "x": 0, "y": 8}
            ),
            
            # Execution quality
            self._create_time_series_panel(
                title="Execution Quality",
                queries=[
                    "trading_slippage_avg",
                    "trading_fill_rate",
                    "histogram_quantile(0.95, trading_order_latency_seconds)"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 16}
            ),
            
            self._create_time_series_panel(
                title="Market Impact",
                queries=[
                    "trading_market_impact_bps",
                    "trading_bid_ask_spread_avg"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 16}
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def create_infrastructure_dashboard(self) -> Dict:
        """Create infrastructure monitoring dashboard"""
        config = DashboardConfig(
            title="Infrastructure & Dependencies",
            tags=["infrastructure", "database", "redis"],
            refresh_interval="30s"
        )
        
        panels = [
            # Database metrics
            self._create_stat_panel(
                title="DB Connections",
                query="pg_stat_database_numbackends",
                grid_pos={"h": 4, "w": 3, "x": 0, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 80}, {"color": "red", "value": 95}]
            ),
            
            self._create_stat_panel(
                title="Redis Memory",
                query="redis_memory_used_bytes / redis_memory_max_bytes * 100",
                grid_pos={"h": 4, "w": 3, "x": 3, "y": 0},
                unit="percent",
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 70}, {"color": "red", "value": 90}]
            ),
            
            self._create_stat_panel(
                title="Queue Depth",
                query="redis_list_length",
                grid_pos={"h": 4, "w": 3, "x": 6, "y": 0},
                thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 1000}, {"color": "red", "value": 5000}]
            ),
            
            self._create_stat_panel(
                title="Cache Hit Rate",
                query="redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100",
                grid_pos={"h": 4, "w": 3, "x": 9, "y": 0},
                unit="percent",
                thresholds=[{"color": "red", "value": 0}, {"color": "yellow", "value": 80}, {"color": "green", "value": 95}]
            ),
            
            # Database performance
            self._create_time_series_panel(
                title="Database Query Performance",
                queries=[
                    "histogram_quantile(0.95, pg_stat_statements_mean_time_seconds)",
                    "rate(pg_stat_database_xact_commit[5m])",
                    "rate(pg_stat_database_xact_rollback[5m])"
                ],
                grid_pos={"h": 8, "w": 6, "x": 0, "y": 4}
            ),
            
            self._create_time_series_panel(
                title="Redis Performance",
                queries=[
                    "rate(redis_commands_processed_total[5m])",
                    "redis_connected_clients",
                    "rate(redis_keyspace_hits_total[5m])",
                    "rate(redis_keyspace_misses_total[5m])"
                ],
                grid_pos={"h": 8, "w": 6, "x": 6, "y": 4}
            ),
            
            # Message queues
            self._create_time_series_panel(
                title="Message Queue Metrics",
                queries=[
                    "rabbitmq_queue_messages",
                    "rate(rabbitmq_queue_messages_published_total[5m])",
                    "rate(rabbitmq_queue_messages_delivered_total[5m])"
                ],
                grid_pos={"h": 8, "w": 8, "x": 0, "y": 12}
            ),
            
            self._create_time_series_panel(
                title="WebSocket Connections",
                queries=[
                    "websocket_connections_active",
                    "rate(websocket_messages_sent_total[5m])",
                    "rate(websocket_messages_received_total[5m])"
                ],
                grid_pos={"h": 8, "w": 4, "x": 8, "y": 12}
            )
        ]
        
        return self._build_dashboard(config, panels)
    
    def _create_stat_panel(self, title: str, query: str, grid_pos: Dict, 
                          unit: str = "short", thresholds: List[Dict] = None, 
                          decimals: int = 2) -> Dict:
        """Create a stat panel"""
        panel = {
            "title": title,
            "type": "stat",
            "gridPos": grid_pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": {"type": "prometheus", "uid": self.datasource}
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "decimals": decimals,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": thresholds or [{"color": "green", "value": None}]
                    }
                }
            },
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "orientation": "auto",
                "textMode": "auto",
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto"
            }
        }
        return panel
    
    def _create_time_series_panel(self, title: str, queries: List[str], grid_pos: Dict,
                                 unit: str = "short", legend: Dict = None) -> Dict:
        """Create a time series panel"""
        targets = []
        for i, query in enumerate(queries):
            targets.append({
                "expr": query,
                "refId": chr(65 + i),  # A, B, C, etc.
                "datasource": {"type": "prometheus", "uid": self.datasource}
            })
        
        panel = {
            "title": title,
            "type": "timeseries",
            "gridPos": grid_pos,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {
                        "drawStyle": "line",
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "spanNulls": False,
                        "insertNulls": False,
                        "showPoints": "never",
                        "pointSize": 5,
                        "stacking": {"mode": "none", "group": "A"},
                        "axisPlacement": "auto",
                        "axisLabel": "",
                        "scaleDistribution": {"type": "linear"},
                        "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                        "thresholdsStyle": {"mode": "off"}
                    }
                }
            },
            "options": {
                "tooltip": {"mode": "single", "sort": "none"},
                "legend": legend or {"displayMode": "list", "placement": "bottom"}
            }
        }
        return panel
    
    def _create_gauge_panel(self, title: str, query: str, grid_pos: Dict,
                           min_value: float = 0, max_value: float = 100,
                           unit: str = "short", thresholds: List[Dict] = None) -> Dict:
        """Create a gauge panel"""
        panel = {
            "title": title,
            "type": "gauge",
            "gridPos": grid_pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": {"type": "prometheus", "uid": self.datasource}
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "min": min_value,
                    "max": max_value,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": thresholds or [
                            {"color": "green", "value": None},
                            {"color": "red", "value": max_value * 0.8}
                        ]
                    }
                }
            },
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "orientation": "auto",
                "textMode": "auto",
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto"
            }
        }
        return panel
    
    def _create_pie_chart_panel(self, title: str, query: str, grid_pos: Dict,
                               unit: str = "short") -> Dict:
        """Create a pie chart panel"""
        panel = {
            "title": title,
            "type": "piechart",
            "gridPos": grid_pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": {"type": "prometheus", "uid": self.datasource}
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": unit
                }
            },
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "pieType": "pie",
                "tooltip": {"mode": "single", "sort": "none"},
                "legend": {"displayMode": "list", "placement": "bottom"}
            }
        }
        return panel
    
    def _create_heatmap_panel(self, title: str, query: str, grid_pos: Dict) -> Dict:
        """Create a heatmap panel"""
        panel = {
            "title": title,
            "type": "heatmap",
            "gridPos": grid_pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": {"type": "prometheus", "uid": self.datasource}
            }],
            "options": {
                "calculate": False,
                "calculation": {},
                "color": {"mode": "spectrum", "scheme": "Spectral", "steps": 64},
                "yAxis": {"axisPlacement": "left", "reverse": False}
            }
        }
        return panel
    
    def _create_histogram_panel(self, title: str, query: str, grid_pos: Dict) -> Dict:
        """Create a histogram panel"""
        panel = {
            "title": title,
            "type": "histogram",
            "gridPos": grid_pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": {"type": "prometheus", "uid": self.datasource}
            }],
            "options": {
                "bucketSize": 10,
                "bucketOffset": 0,
                "bucketBound": "auto"
            }
        }
        return panel
    
    def _create_table_panel(self, title: str, queries: List[str], grid_pos: Dict) -> Dict:
        """Create a table panel"""
        targets = []
        for i, query in enumerate(queries):
            targets.append({
                "expr": query,
                "refId": chr(65 + i),
                "format": "table",
                "instant": True,
                "datasource": {"type": "prometheus", "uid": self.datasource}
            })
        
        panel = {
            "title": title,
            "type": "table",
            "gridPos": grid_pos,
            "targets": targets,
            "transformations": [{
                "id": "organize",
                "options": {
                    "excludeByName": {},
                    "indexByName": {},
                    "renameByName": {}
                }
            }],
            "options": {
                "showHeader": True,
                "sortBy": [{"desc": True, "displayName": "Value"}]
            }
        }
        return panel
    
    def _build_dashboard(self, config: DashboardConfig, panels: List[Dict]) -> Dict:
        """Build complete dashboard JSON"""
        dashboard = {
            "id": None,
            "uid": f"trading_dashboard_{self.dashboard_uid_counter}",
            "title": config.title,
            "tags": config.tags,
            "timezone": config.timezone,
            "refresh": config.refresh_interval,
            "time": {
                "from": f"now-{config.time_range}",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
            },
            "templating": {"list": []},
            "annotations": {"list": []},
            "panels": panels,
            "editable": True,
            "fiscalYearStartMonth": 0,
            "graphTooltip": 0,
            "hideControls": False,
            "links": [],
            "liveNow": config.auto_refresh,
            "schemaVersion": 30,
            "style": "dark",
            "version": 1,
            "weekStart": ""
        }
        
        self.dashboard_uid_counter += 1
        return dashboard

# Factory function
def create_grafana_dashboards(datasource_name: str = "Prometheus") -> Dict[str, Dict]:
    """Create all Grafana dashboards"""
    generator = GrafanaDashboardGenerator(datasource_name)
    return generator.generate_all_dashboards()

# Export dashboards to files
def export_dashboards_to_files(output_dir: str = "monitoring/dashboards"):
    """Export all dashboards to JSON files"""
    import os
    
    dashboards = create_grafana_dashboards()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    for name, dashboard in dashboards.items():
        filename = f"{output_dir}/{name}.json"
        with open(filename, 'w') as f:
            json.dump(dashboard, f, indent=2)
        logger.info(f"Exported dashboard: {filename}")
    
    logger.info(f"Exported {len(dashboards)} dashboards to {output_dir}")

if __name__ == "__main__":
    # Export dashboards when run directly
    export_dashboards_to_files() 
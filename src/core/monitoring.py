"""
Monitoring and Reporting System
Tracks system performance and generates reports
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import json
from pathlib import Path
import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .trade_engine import TradeEngine
from .position_manager import PositionManager
from .risk_manager import RiskManager
from .config import settings

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    active_connections: int
    orders_per_second: float
    latency_ms: float
    error_rate: float

@dataclass
class TradingMetrics:
    """Trading performance metrics"""
    timestamp: datetime
    total_pnl: float
    open_positions: int
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    daily_returns: pd.Series

class MonitoringSystem:
    """System for monitoring and reporting"""
    
    def __init__(self,
                 trade_engine: TradeEngine,
                 position_manager: PositionManager,
                 risk_manager: RiskManager):
        self.trade_engine = trade_engine
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.system_metrics: List[SystemMetrics] = []
        self.trading_metrics: List[TradingMetrics] = []
        self.websocket_clients: List[WebSocket] = []
        self.is_running = False
        
    async def start(self):
        """Start monitoring system"""
        try:
            self.is_running = True
            # Start metrics collection
            asyncio.create_task(self._collect_metrics())
            # Start websocket server
            asyncio.create_task(self._start_websocket_server())
            logger.info("Monitoring system started")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise
            
    async def stop(self):
        """Stop monitoring system"""
        try:
            self.is_running = False
            # Close websocket connections
            for client in self.websocket_clients:
                await client.close()
            logger.info("Monitoring system stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            raise
            
    async def _collect_metrics(self):
        """Collect system and trading metrics"""
        while self.is_running:
            try:
                # Collect system metrics
                system_metrics = await self._get_system_metrics()
                self.system_metrics.append(system_metrics)
                
                # Collect trading metrics
                trading_metrics = await self._get_trading_metrics()
                self.trading_metrics.append(trading_metrics)
                
                # Broadcast to websocket clients
                await self._broadcast_metrics(system_metrics, trading_metrics)
                
                # Keep only last 24 hours of metrics
                cutoff = datetime.now() - timedelta(hours=24)
                self.system_metrics = [m for m in self.system_metrics if m.timestamp > cutoff]
                self.trading_metrics = [m for m in self.trading_metrics if m.timestamp > cutoff]
                
                await asyncio.sleep(1)  # Collect every second
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(1)
                
    async def _get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # Get CPU and memory usage
            import psutil
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            # Get active connections
            active_connections = len(self.websocket_clients)
            
            # Calculate orders per second
            orders_per_second = len(self.trade_engine.trade_queue) / 1.0
            
            # Calculate latency
            latency_ms = await self._measure_latency()
            
            # Calculate error rate
            error_rate = self._calculate_error_rate()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                active_connections=active_connections,
                orders_per_second=orders_per_second,
                latency_ms=latency_ms,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            raise
            
    async def _get_trading_metrics(self) -> TradingMetrics:
        """Get current trading metrics"""
        try:
            # Get positions and trades
            positions = await self.position_manager.get_all_positions()
            trades = await self.position_manager.get_all_trades()
            
            # Calculate PnL
            total_pnl = sum(p['unrealized_pnl'] for p in positions)
            
            # Calculate trade metrics
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            total_trades = len(trades)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate profit factor
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
            
            # Calculate drawdown
            equity_curve = pd.Series([t['cumulative_pnl'] for t in trades])
            rolling_max = equity_curve.expanding().max()
            drawdowns = equity_curve / rolling_max - 1
            max_drawdown = drawdowns.min()
            
            # Calculate daily returns
            daily_returns = pd.Series([t['pnl'] for t in trades], index=[t['timestamp'] for t in trades])
            daily_returns = daily_returns.resample('D').sum()
            
            # Calculate Sharpe ratio
            if len(daily_returns) > 0:
                sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            else:
                sharpe_ratio = 0
                
            return TradingMetrics(
                timestamp=datetime.now(),
                total_pnl=total_pnl,
                open_positions=len(positions),
                total_trades=total_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                daily_returns=daily_returns
            )
            
        except Exception as e:
            logger.error(f"Error getting trading metrics: {e}")
            raise
            
    async def _measure_latency(self) -> float:
        """Measure system latency"""
        try:
            start = datetime.now()
            # Make a test API call
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{settings.API_HOST}:{settings.API_PORT}/health") as response:
                    await response.text()
            end = datetime.now()
            return (end - start).total_seconds() * 1000  # Convert to milliseconds
        except Exception:
            return float('inf')
            
    def _calculate_error_rate(self) -> float:
        """Calculate system error rate"""
        try:
            # Get last hour of metrics
            cutoff = datetime.now() - timedelta(hours=1)
            recent_metrics = [m for m in self.system_metrics if m.timestamp > cutoff]
            
            if not recent_metrics:
                return 0.0
                
            # Count errors in logs
            error_count = 0
            for record in logger.handlers[0].buffer:
                if record.levelno >= logging.ERROR:
                    error_count += 1
                    
            return error_count / len(recent_metrics)
            
        except Exception:
            return 0.0
            
    async def _broadcast_metrics(self, system_metrics: SystemMetrics, trading_metrics: TradingMetrics):
        """Broadcast metrics to websocket clients"""
        try:
            message = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_usage': system_metrics.cpu_usage,
                    'memory_usage': system_metrics.memory_usage,
                    'active_connections': system_metrics.active_connections,
                    'orders_per_second': system_metrics.orders_per_second,
                    'latency_ms': system_metrics.latency_ms,
                    'error_rate': system_metrics.error_rate
                },
                'trading': {
                    'total_pnl': trading_metrics.total_pnl,
                    'open_positions': trading_metrics.open_positions,
                    'total_trades': trading_metrics.total_trades,
                    'win_rate': trading_metrics.win_rate,
                    'profit_factor': trading_metrics.profit_factor,
                    'max_drawdown': trading_metrics.max_drawdown,
                    'sharpe_ratio': trading_metrics.sharpe_ratio
                }
            }
            
            # Send to all connected clients
            for client in self.websocket_clients:
                try:
                    await client.send_json(message)
                except Exception:
                    self.websocket_clients.remove(client)
                    
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")
            
    async def _start_websocket_server(self):
        """Start websocket server for real-time updates"""
        app = FastAPI()
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_clients.append(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except Exception:
                self.websocket_clients.remove(websocket)
                
        # Start server
        import uvicorn
        config = uvicorn.Config(
            app,
            host=settings.API_HOST,
            port=settings.API_PORT + 1,  # Use next port
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    def generate_report(self, output_dir: str):
        """Generate performance report"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create report
            report = {
                'system_performance': self._generate_system_report(),
                'trading_performance': self._generate_trading_report(),
                'risk_metrics': self._generate_risk_report(),
                'charts': self._generate_charts(output_path)
            }
            
            # Save report
            report_file = output_path / "performance_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Performance report generated at {report_file}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
            
    def _generate_system_report(self) -> Dict[str, Any]:
        """Generate system performance report"""
        try:
            metrics_df = pd.DataFrame([vars(m) for m in self.system_metrics])
            
            return {
                'cpu_usage': {
                    'mean': metrics_df['cpu_usage'].mean(),
                    'max': metrics_df['cpu_usage'].max(),
                    'min': metrics_df['cpu_usage'].min()
                },
                'memory_usage': {
                    'mean': metrics_df['memory_usage'].mean(),
                    'max': metrics_df['memory_usage'].max(),
                    'min': metrics_df['memory_usage'].min()
                },
                'latency': {
                    'mean': metrics_df['latency_ms'].mean(),
                    'max': metrics_df['latency_ms'].max(),
                    'min': metrics_df['latency_ms'].min()
                },
                'error_rate': metrics_df['error_rate'].mean()
            }
            
        except Exception as e:
            logger.error(f"Error generating system report: {e}")
            return {}
            
    def _generate_trading_report(self) -> Dict[str, Any]:
        """Generate trading performance report"""
        try:
            metrics_df = pd.DataFrame([vars(m) for m in self.trading_metrics])
            
            return {
                'total_pnl': metrics_df['total_pnl'].iloc[-1],
                'total_trades': metrics_df['total_trades'].iloc[-1],
                'win_rate': metrics_df['win_rate'].iloc[-1],
                'profit_factor': metrics_df['profit_factor'].iloc[-1],
                'max_drawdown': metrics_df['max_drawdown'].iloc[-1],
                'sharpe_ratio': metrics_df['sharpe_ratio'].iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"Error generating trading report: {e}")
            return {}
            
    def _generate_risk_report(self) -> Dict[str, Any]:
        """Generate risk metrics report"""
        try:
            return {
                'position_limits': self.risk_manager.get_position_limits(),
                'daily_limits': self.risk_manager.get_daily_limits(),
                'current_exposure': self.risk_manager.get_current_exposure(),
                'risk_metrics': self.risk_manager.get_risk_metrics()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {}
            
    def _generate_charts(self, output_path: Path) -> Dict[str, str]:
        """Generate performance charts"""
        try:
            charts = {}
            
            # Equity curve
            equity_fig = go.Figure()
            equity_fig.add_trace(go.Scatter(
                x=[m.timestamp for m in self.trading_metrics],
                y=[m.total_pnl for m in self.trading_metrics],
                name='Equity'
            ))
            equity_fig.update_layout(title='Equity Curve')
            equity_file = output_path / "equity_curve.html"
            equity_fig.write_html(str(equity_file))
            charts['equity_curve'] = str(equity_file)
            
            # System metrics
            system_fig = make_subplots(rows=2, cols=2)
            system_fig.add_trace(
                go.Scatter(
                    x=[m.timestamp for m in self.system_metrics],
                    y=[m.cpu_usage for m in self.system_metrics],
                    name='CPU Usage'
                ),
                row=1, col=1
            )
            system_fig.add_trace(
                go.Scatter(
                    x=[m.timestamp for m in self.system_metrics],
                    y=[m.memory_usage for m in self.system_metrics],
                    name='Memory Usage'
                ),
                row=1, col=2
            )
            system_fig.add_trace(
                go.Scatter(
                    x=[m.timestamp for m in self.system_metrics],
                    y=[m.latency_ms for m in self.system_metrics],
                    name='Latency'
                ),
                row=2, col=1
            )
            system_fig.add_trace(
                go.Scatter(
                    x=[m.timestamp for m in self.system_metrics],
                    y=[m.error_rate for m in self.system_metrics],
                    name='Error Rate'
                ),
                row=2, col=2
            )
            system_fig.update_layout(title='System Metrics')
            system_file = output_path / "system_metrics.html"
            system_fig.write_html(str(system_file))
            charts['system_metrics'] = str(system_file)
            
            return charts
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            return {} 
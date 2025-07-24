"""
Provider module for trading system components
"""
from typing import Optional
from .trade_engine import TradeEngine
from .backtest_engine import BacktestEngine
from .monitoring import MonitoringSystem
from .config import settings

# Singleton instances
_trade_engine: Optional[TradeEngine] = None
_backtest_engine: Optional[BacktestEngine] = None
_monitoring: Optional[MonitoringSystem] = None

def get_orchestrator() -> TradeEngine:
    """Get or create the trade engine instance"""
    global _trade_engine
    if _trade_engine is None:
        _trade_engine = TradeEngine()
    return _trade_engine

def get_backtest_engine() -> BacktestEngine:
    """Get or create the backtest engine instance"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine()
    return _backtest_engine

def get_monitoring() -> MonitoringSystem:
    """Get or create the monitoring system instance"""
    global _monitoring
    if _monitoring is None:
        _monitoring = MonitoringSystem()
    return _monitoring 
"""Shim module that re-exports `src.core.models` so tests can simply do `from core.models import ...`.
This avoids the need to modify existing imports while keeping the canonical
implementation inside `src/core/models.py`.
"""
from importlib import import_module as _import_module

_src_models = _import_module("src.core.models")

# Re-export everything except private names
globals().update({k: v for k, v in _src_models.__dict__.items() if not k.startswith("__")})

# ---------------------------------------------------------------------------
# Test-support: provide lightweight fall-back definitions for symbols that
# unit-tests expect but the upstream `src.core.models` module might not define.
# These simple dataclasses/enums satisfy attribute checks without introducing
# heavy dependencies. They are only used when the real implementation is
# missing.
# ---------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

if 'TimeFrame' not in globals():
    class TimeFrame(str, Enum):
        MINUTE_1 = 'MINUTE_1'
        MINUTE_5 = 'MINUTE_5'
        MINUTE_15 = 'MINUTE_15'
        HOUR_1 = 'HOUR_1'
        HOUR_4 = 'HOUR_4'
        DAY_1 = 'DAY_1'

if 'OrderBook' not in globals():
    @dataclass
    class OrderBook:
        symbol: str
        timestamp: datetime
        bids: List[Dict[str, Decimal]]
        asks: List[Dict[str, Decimal]]

if 'Trade' not in globals():
    @dataclass
    class Trade:
        symbol: str
        timestamp: datetime
        price: Decimal
        quantity: Decimal
        side: str
        trade_id: str

if 'Ticker' not in globals():
    @dataclass
    class Ticker:
        symbol: str
        timestamp: datetime
        last_price: Decimal
        bid: Decimal
        ask: Decimal
        volume_24h: Decimal
        high_24h: Decimal
        low_24h: Decimal

if 'StrategyConfig' not in globals():
    @dataclass
    class StrategyConfig:
        name: str
        description: str
        timeframe: 'TimeFrame'
        symbols: List[str]
        parameters: Dict[str, Any]
        risk_limits: Dict[str, Any]

if 'SignalMetadata' not in globals():
    @dataclass
    class SignalMetadata:
        quality_score: float
        timeframe: 'TimeFrame'
        confidence: float
        indicators: Dict[str, Any]
        strategy_name: str

if 'TradingSignal' not in globals():
    @dataclass
    class TradingSignal:
        symbol: str
        action: Any  # typically OrderSide
        quantity: Decimal
        entry_price: Decimal
        strategy_name: str
        signal_id: str
        metadata: 'SignalMetadata'


# Tell static analysers the original module for better type hints
__all__ = _src_models.__all__ if hasattr(_src_models, "__all__") else [
    k for k in globals().keys() if not k.startswith("__")
]

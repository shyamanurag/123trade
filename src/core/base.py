# strategies/base.py
"""
Enhanced Base Strategy Class
Consolidates common functionality to eliminate duplication
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import numpy as np
import pytz  # Add pytz import for timezone handling

from ..models import Signal
from .models import Position, OptionType, OrderSide
from ..utils import get_atm_strike, get_strike_with_offset

logger = logging.getLogger(__name__)

@dataclass
class StrategyMetrics:
    """Unified metrics tracking for all strategies"""
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_signals: int = 0
    executed_signals: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_holding_time: timedelta = timedelta(0)
    last_signal_time: Optional[datetime] = None

    @property
    def win_rate(self) -> float:
        total = self.winning_trades + self.losing_trades
        return (self.winning_trades / total * 100) if total > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        if self.losing_trades == 0:
            return float('inf')
        avg_win = self.total_pnl / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = abs(self.total_pnl / self.losing_trades) if self.losing_trades > 0 else 0
        return avg_win / avg_loss if avg_loss > 0 else 0.0

class SignalScorer:
    """Unified signal quality scoring system"""
    def __init__(self, base_score: float = 5.0, max_score: float = 10.0):
        self.base_score = base_score
        self.max_score = max_score
        self.modifiers = []

    def add_condition(self, condition: bool, weight: float, description: str):
        """Add a scoring condition"""
        if condition:
            self.modifiers.append({
                'weight': weight,
                'description': description
            })
        return self

    def add_range_modifier(self, value: float, ranges: List[Tuple[float, float, float]]):
        """Add modifier based on value ranges"""
        for min_val, max_val, weight in ranges:
            if min_val <= value <= max_val:
                self.modifiers.append({
                    'weight': weight,
                    'description': f"Range [{min_val}, {max_val}]"
                })
                break
        return self

    def calculate(self) -> Tuple[float, List[Dict]]:
        """Calculate final score and return breakdown"""
        total_modifier = sum(m['weight'] for m in self.modifiers)
        final_score = min(self.base_score + total_modifier, self.max_score)
        return final_score, self.modifiers

class BaseStrategy(ABC):
    """
    Enhanced base strategy class with common functionality
    """

    def __init__(self, config: Dict):
        # Basic configuration
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.is_enabled = config.get('enabled', True)
        self.allocation = config.get('allocation', 0.2)

        # Common timing parameters
        self.signal_cooldown = config.get('signal_cooldown_seconds', 300)
        self.last_signal_time = None
        self.symbol_cooldowns = {}

        # Risk parameters (common defaults)
        self.default_stop_loss = config.get('default_stop_loss', 0.6)
        self.default_target = config.get('default_target', 1.0)

        # Cooldown management
        self.recent_signals = deque(maxlen=100)

        # Performance tracking
        self.metrics = StrategyMetrics()
        self.performance_history = []

        # Initialize strategy-specific components
        self._initialize_strategy()

    @abstractmethod
    def _initialize_strategy(self):
        """Initialize strategy-specific components"""
        pass

    @abstractmethod
    async def generate_signals(self, market_data: Dict) -> List[Signal]:
        """Generate trading signals - must be implemented by each strategy"""
        pass

    def _is_trading_hours(self) -> bool:
        """Check if within trading hours - FIXED: Now uses IST timezone like orchestrator"""
        try:
            # Get current time in IST (same as orchestrator)
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            current_time = now.time()
            
            # NSE trading hours: 9:15 AM to 3:30 PM IST
            market_open = time(9, 15)
            market_close = time(15, 30)
            
            # Check if it's a weekday (Monday=0, Sunday=6)
            if now.weekday() >= 5:  # Saturday or Sunday
                logger.info(f"🚫 SAFETY: Trading blocked on weekend. Current day: {now.strftime('%A')}")
                return False
            
            is_trading_time = market_open <= current_time <= market_close
            
            if not is_trading_time:
                logger.info(f"🚫 SAFETY: Trading blocked outside market hours. Current IST time: {current_time} "
                           f"(Market: {market_open} - {market_close})")
            else:
                logger.info(f"✅ TRADING HOURS: Market open. Current IST time: {current_time}")
            
            return is_trading_time
            
        except Exception as e:
            logger.error(f"Error checking trading hours: {e}")
            # SAFETY: If timezone check fails, default to False (safer)
            return False

    def _is_cooldown_passed(self, symbol: Optional[str] = None) -> bool:
        """Check if cooldown period has passed"""
        current_time = datetime.now()
        
        # Global cooldown
        if self.last_signal_time:
            if (current_time - self.last_signal_time).total_seconds() < self.signal_cooldown:
                return False

        # Symbol-specific cooldown
        if symbol and symbol in self.symbol_cooldowns:
            symbol_cooldown = self.config.get('symbol_cooldown_seconds', 300)
            if (current_time - self.symbol_cooldowns[symbol]).total_seconds() < symbol_cooldown:
                return False

        return True

    def _update_cooldowns(self, symbol: str):
        """Update cooldown timers"""
        current_time = datetime.now()
        self.last_signal_time = current_time
        self.symbol_cooldowns[symbol] = current_time

    def _should_exit_intraday(self, entry_time: datetime) -> bool:
        """Common intraday exit logic - FIXED: Now uses IST timezone"""
        try:
            # Get current time in IST (consistent with trading hours check)
            ist = pytz.timezone('Asia/Kolkata')
            current_time = datetime.now(ist)
            
            # Force exit after 3:15 PM IST
            if current_time.time() >= time(15, 15):
                logger.info(f"🚫 INTRADAY EXIT: Force closing positions at {current_time.time()} IST")
                return True

            # Exit if position held too long without profit
            time_in_position = current_time - entry_time
            max_hold_time = timedelta(minutes=self.config.get('max_hold_time', 120))
            if time_in_position > max_hold_time:
                logger.info(f"🚫 INTRADAY EXIT: Position held too long ({time_in_position})")
                return True

            return False
            
        except Exception as e:
            logger.error(f"Error checking intraday exit: {e}")
            # SAFETY: If timezone check fails, default to False (don't force exit)
            return False

    def _calculate_quantity(self, market_data: Dict, position_multiplier: float = 1.0) -> int:
        """Common position sizing logic"""
        capital = market_data.get('available_capital', 500000)
        allocation_amount = capital * self.allocation * position_multiplier

        # Get lot size based on symbol
        symbol = market_data.get('symbol', 'NIFTY')
        lot_size = self._get_lot_size(symbol)
        
        # Calculate lots (minimum 1 lot)
        avg_option_price = market_data.get('avg_option_price', 100)
        lots = max(1, int(allocation_amount / (avg_option_price * lot_size)))
        return lots * lot_size

    def _get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol"""
        lot_sizes = {
            'NIFTY': 50,
            'BANKNIFTY': 25,
            'FINNIFTY': 40
        }

        for key, size in lot_sizes.items():
            if key in symbol.upper():
                return size

        return 1

    def _create_signal(self, symbol: str, option_type: OptionType, strike: float,
                      quality_score: float, metadata: Dict, quantity: Optional[int] = None,
                      stop_loss_percent: Optional[float] = None,
                      target_percent: Optional[float] = None) -> Signal:
        """Create signal with common defaults"""
        return Signal(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            quality_score=quality_score,
            quantity=quantity or self._calculate_quantity({'symbol': symbol}),
            stop_loss_percent=stop_loss_percent or self.default_stop_loss,
            target_percent=target_percent or self.default_target,
            metadata={
                'strategy_version': self.config.get('version', '1.0'),
                'signal_timestamp': datetime.now().isoformat(),
                **metadata
            }
        )

    def _log_signal(self, signal: Signal):
        """Log signal generation"""
        self.recent_signals.append(signal)
        self._update_cooldowns(signal.symbol)
        logger.info(f"{self.name} generated signal: {signal.symbol} "
                   f"Score: {signal.quality_score:.1f} "
                   f"Metadata: {signal.metadata}")

    def update_performance(self, trade_result: Dict):
        """Update strategy performance metrics"""
        pnl = trade_result.get('pnl', 0)
        
        # Update metrics
        if pnl > 0:
            self.metrics.winning_trades += 1
            self.metrics.largest_win = max(self.metrics.largest_win, pnl)
        else:
            self.metrics.losing_trades += 1
            self.metrics.largest_loss = min(self.metrics.largest_loss, pnl)

        # Update holding time
        if 'entry_time' in trade_result and 'exit_time' in trade_result:
            holding_time = trade_result['exit_time'] - trade_result['entry_time']
            
            # Calculate weighted average
            total_trades = self.metrics.winning_trades + self.metrics.losing_trades
            if total_trades > 1:
                prev_avg = self.metrics.average_holding_time
                self.metrics.average_holding_time = (prev_avg * (total_trades - 1) + holding_time) / total_trades
            else:
                self.metrics.average_holding_time = holding_time

        # Store in history
        self.performance_history.append({
            'timestamp': datetime.now(),
            'trade_result': trade_result,
            'cumulative_pnl': self.metrics.total_pnl
        })

    def get_strategy_metrics(self) -> Dict:
        """Get comprehensive strategy metrics"""
        base_metrics = {
            'name': self.name,
            'enabled': self.is_enabled,
            'allocation': self.allocation,
            'total_signals': self.metrics.total_signals,
            'executed_signals': self.metrics.executed_signals,
            'total_pnl': self.metrics.total_pnl,
            'win_rate': self.metrics.win_rate,
            'profit_factor': self.metrics.profit_factor,
            'winning_trades': self.metrics.winning_trades,
            'losing_trades': self.metrics.losing_trades,
            'largest_win': self.metrics.largest_win,
            'largest_loss': self.metrics.largest_loss,
            'average_holding_time': str(self.metrics.average_holding_time),
            'last_signal_time': self.metrics.last_signal_time.isoformat() if self.metrics.last_signal_time else None
        }

        # Add strategy-specific metrics
        specific_metrics = self._get_specific_metrics()
        base_metrics.update(specific_metrics)
        return base_metrics

    def _get_specific_metrics(self) -> Dict:
        """Override to add strategy-specific metrics"""
        return {}

    def is_healthy(self) -> bool:
        """Check if strategy is healthy"""
        # Check if getting signals
        if self.metrics.last_signal_time:
            time_since_signal = (datetime.now() - self.metrics.last_signal_time).total_seconds()
            if time_since_signal > 3600:  # No signals for 1 hour
                return False
        return True

class BaseBroker(ABC):
    """Base class for broker integrations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_connected = False
        self.session_token = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Dict) -> Dict:
        """Place an order"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_orders(self) -> List[Dict]:
        """Get orders"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass

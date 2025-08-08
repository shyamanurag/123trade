"""
Smart Intraday Options - EQUITY STOCKS SPECIALIST
Comprehensive intraday options strategy covering all market conditions.
Re-implemented within EnhancedMomentumSurfer to keep existing name.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class EnhancedMomentumSurfer(BaseStrategy):
    """Smart Intraday Options logic under existing strategy name."""

    def __init__(self, config: Dict = None):
        super().__init__(config or {})
        self.strategy_name = "smart_intraday_options"
        self.description = "Smart Intraday Options with dynamic strike selection"

        # Market regime parameters
        self.trending_threshold = 1.0
        self.sideways_range = 0.5
        self.breakout_threshold = 1.5

        # Stock selection
        self.focus_stocks = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ITC',
            'BHARTIARTL', 'KOTAKBANK', 'LT', 'SBIN', 'WIPRO', 'AXISBANK',
            'MARUTI', 'ASIANPAINT', 'HCLTECH', 'POWERGRID', 'NTPC'
        ]

        # Position management
        self.max_intraday_positions = 5
        self.profit_booking_threshold = 0.3
        self.stop_loss_threshold = 0.15

        self._condition_map = {
            'trending_up': self._trending_up_strategy,
            'trending_down': self._trending_down_strategy,
            'sideways': self._sideways_strategy,
            'breakout_up': self._breakout_up_strategy,
            'breakout_down': self._breakout_down_strategy,
            'reversal_up': self._reversal_up_strategy,
            'reversal_down': self._reversal_down_strategy,
            'high_volatility': self._high_volatility_strategy,
            'low_volatility': self._low_volatility_strategy,
        }

    async def initialize(self):
        self.is_active = True
        logger.info("✅ Smart Intraday Options (as EnhancedMomentumSurfer) initialized")

    async def on_market_data(self, data: Dict):
        if not self.is_active:
            return
        try:
            signals = await self.generate_signals(data)
            for signal in signals:
                symbol = signal.get('symbol')
                if symbol:
                    self.current_positions[symbol] = signal
                    logger.info(
                        f"🎯 SMART INTRADAY: {signal['symbol']} {signal['action']} Confidence: {signal.get('confidence', 0):.1f}/10"
                    )
        except Exception as e:
            logger.error(f"Error in Smart Intraday Options: {e}")

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        try:
            if not market_data:
                return signals
            for stock in self.focus_stocks:
                if stock in market_data:
                    condition = self._detect_market_condition(stock, market_data)
                    sig = await self._generate_condition_based_signal(stock, condition, market_data)
                    if sig:
                        signals.append(sig)
            return signals
        except Exception as e:
            logger.error(f"Error in Smart Intraday Options generate_signals: {e}")
            return []

    def _detect_market_condition(self, symbol: str, market_data: Dict[str, Any]) -> str:
        try:
            data = market_data.get(symbol, {})
            if not data:
                return 'sideways'
            change_percent = data.get('change_percent', 0)
            volume = data.get('volume', 0)
            avg_volume = volume * 0.8
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            if abs(change_percent) >= self.breakout_threshold and volume_ratio > 1.5:
                return 'breakout_up' if change_percent > 0 else 'breakout_down'
            if change_percent >= self.trending_threshold:
                return 'trending_up'
            if change_percent <= -self.trending_threshold:
                return 'trending_down'
            if abs(change_percent) <= self.sideways_range:
                return 'sideways'
            if volume_ratio > 2.0:
                return 'high_volatility'
            if volume_ratio < 0.5:
                return 'low_volatility'
            if 0.5 < change_percent < self.trending_threshold:
                return 'reversal_up'
            if -self.trending_threshold < change_percent < -0.5:
                return 'reversal_down'
            return 'sideways'
        except Exception as e:
            logger.debug(f"Error detecting market condition for {symbol}: {e}")
            return 'sideways'

    async def _generate_condition_based_signal(self, symbol: str, condition: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            func = self._condition_map.get(condition)
            return await func(symbol, market_data) if func else None
        except Exception as e:
            logger.debug(f"Error generating condition-based signal for {symbol}: {e}")
            return None

    async def _trending_up_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if change_percent > 1.0:
            confidence = 9.2 + min(change_percent * 0.2, 0.8)
            return await self._create_options_signal(symbol, 'buy', confidence, market_data,
                                                     f"Uptrending stock - Change: {change_percent:.1f}%", 100)
        return None

    async def _trending_down_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if change_percent < -1.0:
            confidence = 9.2 + min(abs(change_percent) * 0.2, 0.8)
            return await self._create_options_signal(symbol, 'sell', confidence, market_data,
                                                     f"Downtrending stock SHORT - Change: {change_percent:.1f}%", 100)
        return None

    async def _sideways_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if change_percent < -0.3:
            return await self._create_options_signal(symbol, 'buy', 9.1, market_data,
                                                     f"Range trading: Buy at support - Change: {change_percent:.1f}%", 150)
        if change_percent > 0.3:
            return await self._create_options_signal(symbol, 'sell', 9.1, market_data,
                                                     f"Range trading: Sell at resistance - Change: {change_percent:.1f}%", 150)
        return None

    async def _breakout_up_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        volume = data.get('volume', 0)
        if change_percent > 1.5 and volume > 100000:
            confidence = 9.5 + min(change_percent * 0.1, 0.5)
            return await self._create_options_signal(symbol, 'buy', confidence, market_data,
                                                     f"Upward breakout with volume - Change: {change_percent:.1f}%, Volume: {volume:,}", 200)
        return None

    async def _breakout_down_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        volume = data.get('volume', 0)
        if change_percent < -1.5 and volume > 100000:
            confidence = 9.5 + min(abs(change_percent) * 0.1, 0.5)
            return await self._create_options_signal(symbol, 'sell', confidence, market_data,
                                                     f"Downward breakout with volume - Change: {change_percent:.1f}%, Volume: {volume:,}", 200)
        return None

    async def _reversal_up_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if 0.5 <= change_percent <= 1.0:
            return await self._create_options_signal(symbol, 'buy', 9.0, market_data,
                                                     f"Upward reversal pattern - Change: {change_percent:.1f}%", 100)
        return None

    async def _reversal_down_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if -1.0 <= change_percent <= -0.5:
            return await self._create_options_signal(symbol, 'sell', 9.0, market_data,
                                                     f"Downward reversal pattern - Change: {change_percent:.1f}%", 100)
        return None

    async def _high_volatility_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        volume = data.get('volume', 0)
        if volume > 200000 and abs(change_percent) > 0.5:
            action = 'buy' if change_percent > 0 else 'sell'
            return await self._create_options_signal(symbol, action, 9.3, market_data,
                                                     f"High volatility momentum - Change: {change_percent:.1f}%, Volume: {volume:,}", 125)
        return None

    async def _low_volatility_strategy(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        change_percent = data.get('change_percent', 0)
        if abs(change_percent) > 0.2:
            action = 'buy' if change_percent > 0 else 'sell'
            return await self._create_options_signal(symbol, action, 9.0, market_data,
                                                     f"Low volatility opportunity - Change: {change_percent:.1f}%", 75)
        return None

    async def _create_options_signal(self, symbol: str, signal_type: str, confidence: float,
                                     market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_impl(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_impl(self, symbol: str, signal_type: str, confidence: float,
                                          market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_compat(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_compat(self, symbol: str, signal_type: str, confidence: float,
                                            market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_base(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_base(self, symbol: str, signal_type: str, confidence: float,
                                          market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_forward(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_forward(self, symbol: str, signal_type: str, confidence: float,
                                             market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_output(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_output(self, symbol: str, signal_type: str, confidence: float,
                                            market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal_entry(symbol, signal_type, confidence, market_data, reasoning, position_size)

    async def _create_options_signal_entry(self, symbol: str, signal_type: str, confidence: float,
                                           market_data: Dict[str, Any], reasoning: str, position_size: int) -> Dict[str, Any]:
        return await self._create_options_signal(symbol=symbol, signal_type=signal_type, confidence=confidence,
                                                market_data=market_data, reasoning=reasoning, position_size=position_size)
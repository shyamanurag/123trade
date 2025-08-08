"""
Volatility Explosion strategy replaced with Nifty Intelligence Engine logic, keeping class name.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class EnhancedVolatilityExplosion(BaseStrategy):
    """Nifty Intelligence Engine logic under existing strategy name."""

    def __init__(self, config: Dict = None):
        super().__init__(config or {})
        self.strategy_name = "nifty_intelligence_engine"
        self.description = "Nifty Intelligence Engine with advanced pattern recognition"
        self.nifty_symbols = ['NIFTY-I', 'NIFTY-FUT', 'BANKNIFTY-I', 'FINNIFTY-I']
        self.nifty_target_points = 75
        self.nifty_stop_points = 12
        self.volatility_window = 20
        self.volatility_history: List[float] = []
        self.current_regime = 'sideways'

    async def initialize(self):
        self.is_active = True
        logger.info("✅ Nifty Intelligence (as EnhancedVolatilityExplosion) initialized")

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
                        f"🎯 NIFTY INTELLIGENCE: {signal['symbol']} {signal['action']} Confidence: {signal.get('confidence', 0):.1f}/10"
                    )
        except Exception as e:
            logger.error(f"Error in Nifty Intelligence: {e}")

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        if not market_data:
            return signals
        self._update_volatility_model(market_data)
        self._detect_market_regime(market_data)
        for symbol in self.nifty_symbols:
            if symbol in market_data:
                s = await self._analyze_nifty_opportunity(symbol, market_data)
                if s:
                    signals.append(s)
        return signals

    def _update_volatility_model(self, market_data: Dict[str, Any]):
        nifty_data = market_data.get('NIFTY-I', {})
        if not nifty_data:
            return
        change_percent = float(nifty_data.get('change_percent', 0) or 0)
        self.volatility_history.append(abs(change_percent))
        if len(self.volatility_history) > self.volatility_window:
            self.volatility_history.pop(0)

    def _detect_market_regime(self, market_data: Dict[str, Any]):
        nifty_data = market_data.get('NIFTY-I', {})
        if not nifty_data:
            return
        change_percent = float(nifty_data.get('change_percent', 0) or 0)
        if abs(change_percent) > 1.5:
            self.current_regime = 'trending_up' if change_percent > 0 else 'trending_down'
        elif np.std(self.volatility_history[-10:]) if len(self.volatility_history) >= 10 else 0 > 2.0:
            self.current_regime = 'volatile'
        else:
            self.current_regime = 'sideways'

    async def _analyze_nifty_opportunity(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = market_data.get(symbol, {})
        if not data:
            return None
        ltp = float(data.get('ltp', 0) or 0)
        change_percent = float(data.get('change_percent', 0) or 0)
        volume = int(data.get('volume', 0) or 0)
        if ltp <= 0:
            return None

        action: Optional[str] = None
        confidence = 5.0
        reasoning = f"Regime: {self.current_regime}"
        if self.current_regime == 'trending_up' and change_percent > 0.5:
            action = 'BUY'; confidence += 2.0; reasoning += f" | Uptrend {change_percent:.1f}%"
        elif self.current_regime == 'trending_down' and change_percent < -0.5:
            action = 'SELL'; confidence += 2.0; reasoning += f" | Downtrend {change_percent:.1f}%"
        elif self.current_regime == 'volatile' and abs(change_percent) > 1.0:
            action = 'BUY' if change_percent > 0 else 'SELL'; confidence += 1.5; reasoning += " | Volatile momentum"
        elif self.current_regime == 'sideways' and abs(change_percent) > 0.3:
            action = 'SELL' if change_percent > 0 else 'BUY'; confidence += 1.0; reasoning += " | Mean reversion"
        if not action:
            return None

        if volume > 1_000_000:
            confidence += 1.0
        elif volume > 500_000:
            confidence += 0.5

        # Convert points target/stop to price levels
        if 'FUT' in symbol:
            target = ltp + self.nifty_target_points if action == 'BUY' else ltp - self.nifty_target_points
            stop = ltp - self.nifty_stop_points if action == 'BUY' else ltp + self.nifty_stop_points
        else:
            # For index spot, use proportional adjustments
            target = ltp * (1 + (self.nifty_target_points / max(ltp, 1))) if action == 'BUY' else ltp * (1 - (self.nifty_target_points / max(ltp, 1)))
            stop = ltp * (1 - (self.nifty_stop_points / max(ltp, 1))) if action == 'BUY' else ltp * (1 + (self.nifty_stop_points / max(ltp, 1)))

        # Only accept high-confidence signals
        if confidence < 9.0:
            return None

        return self.create_standard_signal(
            symbol=symbol,
            action=action,
            entry_price=ltp,
            stop_loss=stop,
            target=target,
            confidence=min(confidence / 10.0, 0.95),
            metadata={
                'reasoning': reasoning,
                'regime': self.current_regime,
                'strategy': 'nifty_intelligence_engine'
            }
        )
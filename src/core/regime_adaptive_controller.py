# strategies/regime_adaptive_controller.py
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
import asyncio
from .base import BaseStrategy

class RegimeAdaptiveController(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.regime_thresholds = {
            'ULTRA_HIGH_VOL': {'vix': 25, 'atr_ratio': 1.5},
            'TRENDING': {'adx': 30, 'directional_movement': 0.7},
            'RANGE_BOUND': {'adx': 20, 'atr_ratio': 0.5}
        }
        self.allocation_adjustments = {
            'ULTRA_HIGH_VOL': {
                'volatility_explosion': 1.4,
                'momentum_surfer': 0.6,
                'volume_profile_scalper': 1.0,
                'news_impact_scalper': 1.0
            },
            'TRENDING': {
                'momentum_surfer': 1.4,
                'volume_profile_scalper': 1.2,
                'volatility_explosion': 0.7,
                'news_impact_scalper': 0.7
            },
            'RANGE_BOUND': {
                'volume_profile_scalper': 1.5,
                'volatility_explosion': 1.2,
                'momentum_surfer': 0.6,
                'news_impact_scalper': 0.7
            }
        }
        self.regime_history = []
        self._regime_lock = asyncio.Lock()
        self._current_regime = 'NORMAL'

    async def detect_regime(self, market_data: Dict) -> str:
        async with self._regime_lock:
            vix = market_data.get('vix', 0)
            adx = market_data.get('adx', 0)
            atr_ratio = market_data.get('atr_ratio', 1.0)
            
            if vix > self.regime_thresholds['ULTRA_HIGH_VOL']['vix']:
                new_regime = 'ULTRA_HIGH_VOL'
            elif adx > self.regime_thresholds['TRENDING']['adx']:
                new_regime = 'TRENDING'
            elif adx < self.regime_thresholds['RANGE_BOUND']['adx']:
                new_regime = 'RANGE_BOUND'
            else:
                new_regime = 'NORMAL'
                
            if new_regime != self._current_regime:
                self._current_regime = new_regime
                self.regime_history.append({
                    'timestamp': datetime.now(),
                    'regime': new_regime,
                    'vix': vix,
                    'adx': adx
                })
            
            return self._current_regime

    def get_allocation_multiplier(self, strategy_name: str, regime: str) -> float:
        return self.allocation_adjustments.get(regime, {}).get(strategy_name, 1.0)

    async def generate_signals(self, market_data: Dict) -> List[Signal]:
        # Meta-strategy doesn't generate direct signals
        # It adjusts other strategies' allocations
        new_regime = await self.detect_regime(market_data)
        return []

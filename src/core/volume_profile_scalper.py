# strategies/volume_profile_scalper.py
"""
Enhanced Volume Profile Scalper Strategy
Combines Set 1's sophisticated analysis with Set 2's async architecture
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Deque
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
from decimal import Decimal

from ..models import Signal, OptionType, OrderSide, MarketRegime
from ..utils.helpers import get_atm_strike, calculate_value_area, to_decimal, round_price_to_tick
from .base import BaseStrategy

logger = logging.getLogger(__name__)

@dataclass
class VolumeProfile:
    """Volume profile data structure"""
    price_levels: List[float] = field(default_factory=list)
    volumes: List[float] = field(default_factory=list)
    poc_price: Optional[float] = None
    value_area_high: Optional[float] = None
    value_area_low: Optional[float] = None

    @property
    def total_volume(self) -> float:
        return sum(self.volumes)

    @property
    def is_valid(self) -> bool:
        return len(self.price_levels) > 0 and self.poc_price is not None

@dataclass
class ScalperConfig:
    """Configuration for volume profile scalper"""
    min_volume_threshold: float = 1.5
    max_spread_percent: float = 0.5
    min_profit_target: float = 0.3
    max_loss_percent: float = 0.5
    value_area_percent: float = 0.7
    lookback_periods: int = 20
    min_trades_per_day: int = 3
    max_trades_per_day: int = 10

@dataclass
class ScalperState:
    """Trading state for scalper"""
    trades_today: int = 0
    last_trade_time: Optional[datetime] = None
    current_position: Optional[Dict] = None
    volume_profile: Optional[VolumeProfile] = None
    last_update_time: Optional[datetime] = None

    @property
    def can_trade(self) -> bool:
        if not self.last_trade_time:
            return True
        time_since_last = datetime.now() - self.last_trade_time
        return time_since_last.total_seconds() > 300  # 5 min cooldown

    @property
    def is_position_open(self) -> bool:
        return self.current_position is not None

    @property
    def needs_update(self) -> bool:
        if not self.last_update_time:
            return True
        time_since_update = datetime.now() - self.last_update_time
        return time_since_update.total_seconds() > 60  # Update every minute

class VolumeProfileScalper(BaseStrategy):
    """Volume profile based scalping strategy"""
    def __init__(self, config: Dict):
        super().__init__(config)
        self.scalper_config = ScalperConfig(**config.get('scalper_config', {}))
        self.state = ScalperState()
        self._initialize_strategy()

    def _initialize_strategy(self):
        """Initialize strategy-specific components"""
        pass

    async def generate_signals(self, market_data: Dict) -> List[Signal]:
        """Generate trading signals based on volume profile"""
        if not self._is_trading_hours():
            return []

        # Update volume profile if needed
        if self.state.needs_update:
            await self._update_volume_profile(market_data)

        # Check if we can trade
        if not self.state.can_trade or self.state.is_position_open:
            return []

        # Generate signals based on volume profile
        signals = []
        if self.state.volume_profile and self.state.volume_profile.is_valid:
            signals.extend(self._generate_volume_signals(market_data))

        return signals

    async def _update_volume_profile(self, market_data: Dict):
        """Update volume profile with latest data"""
        try:
            # Get historical data
            symbol = market_data['symbol']
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=self.scalper_config.lookback_periods)
            
            df = await self.data_provider.get_historical_data(
                symbol=symbol,
                interval='1min',
                from_date=start_time,
                to_date=end_time
            )

            if df.empty:
                return

            # Calculate volume profile
            self.state.volume_profile = self._calculate_volume_profile(df)
            self.state.last_update_time = datetime.now()

        except Exception as e:
            logger.error(f"Error updating volume profile: {e}")

    def _calculate_volume_profile(self, df: pd.DataFrame) -> VolumeProfile:
        """Calculate volume profile from price data"""
        profile = VolumeProfile()

        # Get price range
        price_range = df['high'].max() - df['low'].min()
        num_levels = 50
        level_size = price_range / num_levels

        # Create price levels
        profile.price_levels = [df['low'].min() + i * level_size for i in range(num_levels + 1)]
        profile.volumes = [0] * (num_levels + 1)

        # Calculate volume at each level
        for _, row in df.iterrows():
            for i in range(num_levels):
                if profile.price_levels[i] <= row['close'] < profile.price_levels[i + 1]:
                    profile.volumes[i] += row['volume']
                    break

        # Find POC (Point of Control)
        poc_idx = np.argmax(profile.volumes)
        profile.poc_price = profile.price_levels[poc_idx]

        # Calculate Value Area
        total_volume = sum(profile.volumes)
        target_volume = total_volume * self.scalper_config.value_area_percent
        current_volume = 0
        va_high_idx = poc_idx
        va_low_idx = poc_idx

        while current_volume < target_volume and (va_high_idx < num_levels or va_low_idx > 0):
            if va_high_idx < num_levels and (va_low_idx == 0 or profile.volumes[va_high_idx + 1] > profile.volumes[va_low_idx - 1]):
                va_high_idx += 1
                current_volume += profile.volumes[va_high_idx]
            elif va_low_idx > 0:
                va_low_idx -= 1
                current_volume += profile.volumes[va_low_idx]

        profile.value_area_high = profile.price_levels[va_high_idx]
        profile.value_area_low = profile.price_levels[va_low_idx]

        return profile

    def _generate_volume_signals(self, market_data: Dict) -> List[Signal]:
        """Generate signals based on volume profile"""
        signals = []
        profile = self.state.volume_profile
        current_price = market_data['ltp']

        # Check if price is near POC
        if abs(current_price - profile.poc_price) / profile.poc_price < 0.001:
            # Generate signals for both calls and puts
            for option_type in [OptionType.CALL, OptionType.PUT]:
                strike = get_atm_strike(current_price)
                signal = self._create_signal(
                    symbol=market_data['symbol'],
                    option_type=option_type,
                    strike=strike,
                    quality_score=7.0,
                    metadata={
                        'strategy': 'volume_profile',
                        'poc_price': profile.poc_price,
                        'value_area_high': profile.value_area_high,
                        'value_area_low': profile.value_area_low
                    }
                )
                signals.append(signal)

        return signals

    def _get_specific_metrics(self) -> Dict:
        """Get strategy-specific metrics"""
        return {
            'trades_today': self.state.trades_today,
            'last_trade_time': self.state.last_trade_time.isoformat() if self.state.last_trade_time else None,
            'current_position': self.state.current_position,
            'volume_profile': {
                'poc_price': self.state.volume_profile.poc_price if self.state.volume_profile else None,
                'value_area_high': self.state.volume_profile.value_area_high if self.state.volume_profile else None,
                'value_area_low': self.state.volume_profile.value_area_low if self.state.volume_profile else None
            } if self.state.volume_profile else None
        }

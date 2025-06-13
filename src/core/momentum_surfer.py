# strategies/momentum_surfer.py
"""
Enhanced Momentum Surfer Strategy - 25% allocation
Combines Set 1's sophisticated logic with Set 2's async architecture
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from .base import BaseStrategy
from ..models import Signal, OptionType, OrderSide, MarketRegime
from ..utils.indicators import ADX, RSI, VWAP
from ..utils.helpers import get_atm_strike, get_strike_with_offset, to_decimal, round_price_to_tick

logger = logging.getLogger(__name__
@ dataclass
class MomentumState:
    """Enhanced momentum state tracking"""

    class EnhancedMomentumSurfer(BaseStrategy):
        """
        Enhanced momentum strategy with sophisticated signal generation:
        - Advanced VWAP band analysis with volume confirmation
        - Multi-timeframe ADX trend strength filtering
        - Dynamic RSI positioning for optimal entries
        - Expected move calculation using ATR proxy
        - Quality scoring with multiple factors
        - Market regime awareness
        """

        def _initialize_strategy(self):
            """Initialize enhanced momentum components"""
            # Enhanced strategy parameters from Set 1

            # Risk parameters

            # Enhanced indicators

            # State tracking with enhanced features

            # Performance tracking by setup type
            'vwap_break_bullish': {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            'vwap_break_bearish': {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            'morning_momentum': {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            'trend_continuation': {'count': 0, 'pnl': 0.0, 'win_rate': 0.0

            logger.info(f"Enhanced MomentumSurfer initialized with allocation: {self.allocation}"
            async def generate_signals(self, market_data: Dict) -> List[Signal]:
            """Generate enhanced momentum trading signals with sophisticated logic"""
            signals=[]

            try:
                # Check if enabled and in trading hours
                if not self.is_enabled or not self._is_trading_hours():
                return signals

                # Get current data
                spot_price=market_data.get('spot_price', 0
                current_vix=market_data.get('vix'
                symbol=market_data.get('symbol', 'NIFTY'
            return signals

            # Check cooldown for this symbol
            if not self._check_symbol_cooldown(symbol):
            return signals

            # Update indicators with enhanced calculations
            indicator_data=await self._update_enhanced_indicators(market_data
            if not indicator_data:
            return signals

            # Get or create momentum state
            if symbol not in self.momentum_states:

                state=self.momentum_states[symbol]

                # Enhanced signal generation with Set 1 logic
                main_signal=await self._check_enhanced_momentum_conditions(
                market_data, indicator_data, state, current_vix

                if main_signal:
                    signals.append(main_signal
                    # Morning momentum setup (enhanced
                    if self._is_morning_session():
                        morning_signal=await self._check_enhanced_morning_momentum(
                        market_data, indicator_data, state, current_vix

                        if morning_signal:
                            signals.append(morning_signal
                            # Trend continuation setup
                            trend_signal=await self._check_trend_continuation(
                            market_data, indicator_data, state, current_vix

                            if trend_signal:
                                signals.append(trend_signal
                                # Filter by enhanced quality scoring
                                qualified_signals=[]
                                for signal in signals:
                                    enhanced_score=await self._calculate_enhanced_quality_score(
                                    signal, indicator_data, state, current_vix

                                    qualified_signals.append(signal
                                    # Update state and log signals
                                    for signal in qualified_signals:
                                        self._update_momentum_state(state, signal, indicator_data
                                        self._log_enhanced_signal(signal, indicator_data
                                        self.signal_history.append({
                                        'timestamp': datetime.now(),
                                        'signal': signal,
                                        'indicators': indicator_data,
                                        'state': state

                                    return qualified_signals

                                    except Exception as e:
                                        logger.error(f"Error generating enhanced momentum signals: {e}"
                                    return []

                                    async def _update_enhanced_indicators(
                                    self, market_data: Dict) -> Optional[Dict]:
                                    """Enhanced indicator calculation with Set 1 sophistication"""
                                    try:
                                        # Extract comprehensive data
                                        candles_5min=market_data.get('candles_5min', []
                                        if len(candles_5min) < 20:
                                        return None

                                        # Convert to DataFrame for advanced calculations
                                        df=pd.DataFrame(candles_5min
                                        symbol=market_data.get('symbol', 'NIFTY'
                                        # Enhanced VWAP calculation with bands
                                        vwap_data=self.vwap.calculate(df
                                        current_vwap=vwap_data['vwap'].iloc[-1]

                                        # Dynamic VWAP bands based on volatility
                                        atr=self._calculate_enhanced_atr(df
                                        vwap_band_width=atr * 0.5  # Dynamic band width
                                        vwap_upper=current_vwap + vwap_band_width
                                        vwap_lower=current_vwap - vwap_band_width

                                        # Enhanced ADX with directional components
                                        adx_data=self.adx.calculate(df
                                        current_adx=adx_data['adx'].iloc[-1]
                                        plus_di=adx_data['plus_di'].iloc[-1]
                                        minus_di=adx_data['minus_di'].iloc[-1]

                                        # Enhanced RSI with momentum
                                        rsi_data=self.rsi.calculate(df
                                        current_rsi=rsi_data['rsi'].iloc[-1]

                                        # Enhanced volume analysis
                                        current_volume=df['volume'].iloc[-1]
                                        avg_volume=self._calculate_enhanced_average_volume(symbol, df
                                        volume_ratio=current_volume / avg_volume if avg_volume > 0 else 1.0
                                        volume_surge=volume_ratio > float(self.volume_surge_multiplier
                                        # Daily ATR proxy for expected move
                                        daily_atr_proxy=self._calculate_daily_atr_proxy(df
                                        expected_move_met=daily_atr_proxy >= float(self.min_expected_move_points
                                        # Market regime detection
                                        market_regime=self._detect_market_regime(
                                        current_adx, plus_di, minus_di, current_rsi, volume_ratio

                                    return {
                                    'vwap': current_vwap,
                                    'vwap_upper': vwap_upper,
                                    'vwap_lower': vwap_lower,
                                    'vwap_band_width': vwap_band_width,
                                    'adx': current_adx,
                                    'plus_di': plus_di,
                                    'minus_di': minus_di,
                                    'rsi': current_rsi,
                                    'volume_ratio': volume_ratio,
                                    'volume_surge': volume_surge,
                                    'avg_volume': avg_volume,
                                    'current_volume': current_volume,
                                    'atr': atr,
                                    'daily_atr_proxy': daily_atr_proxy,
                                    'expected_move_met': expected_move_met,
                                    'market_regime': market_regime,
                                    'current_price': df['close'}.iloc[-1],
                                    'high': df['high'].iloc[-1],
                                    'low': df['low'].iloc[-1]

                                    except Exception as e:
                                        logger.error(f"Error updating enhanced indicators: {e}"
                                    return None

                                    async def _check_enhanced_momentum_conditions(self, market_data: Dict,
                                    indicators: Dict, state: MomentumState,
                                    current_vix: Optional[float]) -> Optional[Signal]:
                                    """Enhanced momentum condition checking with Set 1 logic"""
                                    current_price=indicators['current_price']
                                    symbol=market_data.get('symbol', 'NIFTY'
                                    spot_price=market_data.get('spot_price', current_price
                                    # Enhanced trend detection
                                    is_trending=indicators['adx'] > float(self.adx_threshold
                                    if not is_trending:
                                    return None

                                    # Enhanced volume confirmation
                                    if not indicators['volume_surge']:
                                    return None

                                    # Enhanced expected move requirement
                                    if not indicators['expected_move_met']:
                                    return None

                                    signal_type=None
                                    setup_type=None

                                    # Enhanced bullish conditions (Set 1 logic
                                    if (current_price > indicators['vwap_upper'] and
                                        is_trending and
                                        indicators['plus_di'] > indicators['minus_di'] and

                                        signal_type=OptionType.CALL
                                        setup_type='vwap_break_bullish'

                                        # Enhanced bearish conditions (Set 1 logic
                                        elif (current_price < indicators['vwap_lower'] and
                                            is_trending and
                                            indicators['minus_di'] > indicators['plus_di'] and

                                            signal_type=OptionType.PUT
                                            setup_type='vwap_break_bearish'

                                            if not signal_type:
                                            return None

                                            # Enhanced strike selection
                                            strike=await self._select_enhanced_strike(
                                            spot_price, signal_type, indicators, current_vix

                                            # Enhanced position sizing
                                            quantity=await self._calculate_enhanced_quantity(
                                            market_data, indicators, current_vix

                                            # Create enhanced signal
                                            signal=Signal(
                                            symbol=f"{symbol}{strike}{signal_type.value}",
                                            option_type=signal_type,
                                            strike=strike,
                                            quantity=quantity,
                                            'setup_type': setup_type,
                                            'vwap': indicators['vwap'],
                                            'vwap_band_width': indicators['vwap_band_width'],
                                            'adx': indicators['adx'],
                                            'rsi': indicators['rsi'],
                                            'volume_surge': f"{indicators['volume_ratio'}:.1f}x",
                                            'expected_move': indicators['daily_atr_proxy'],
                                            'trend_strength': indicators['adx'],
                                            'market_regime': indicators['market_regime'],
                                            'entry_time': datetime.now().strftime('%H:%M:%S'),
                                            'plus_di': indicators['plus_di'],
                                            'minus_di': indicators['minus_di'],
                                            'vix': current_vix

                                        return signal

                                        async def _check_enhanced_morning_momentum(self, market_data: Dict,
                                        indicators: Dict, state: MomentumState,
                                        current_vix: Optional[float]) -> Optional[Signal]:
                                        """Enhanced morning momentum with opening range analysis"""
                                        current_time=datetime.now().time(
                                        # Morning session window
                                    return None

                                    # Enhanced morning conditions
                                    strong_trend=indicators['adx'] > 30
                                    significant_volume=indicators['volume_ratio'] > 1.2
                                    price_displacement=abs(
                                    indicators['current_price'] - indicators['vwap']) / indicators['vwap'] > 0.002

                                    if not (strong_trend and significant_volume and price_displacement):
                                    return None

                                    # Determine direction with enhanced logic
                                    if (indicators['plus_di'] > indicators['minus_di'] and
                                        indicators['rsi'] > 55 and
                                        indicators['current_price'] > indicators['vwap']):
                                        signal_type=OptionType.CALL
                                        elif (indicators['minus_di'] > indicators['plus_di'] and
                                            indicators['rsi'] < 45 and
                                            indicators['current_price'] < indicators['vwap']):
                                            signal_type=OptionType.PUT
                                            else:
                                            return None

                                            # Enhanced strike and quantity
                                            spot_price=market_data.get('spot_price', indicators['current_price']
                                            strike=await self._select_enhanced_strike(spot_price, signal_type, indicators, current_vix
                                            quantity=await self._calculate_enhanced_quantity(market_data, indicators, current_vix, multiplier=1.2
                                            symbol=market_data.get('symbol', 'NIFTY'
                                        return Signal(
                                        symbol=f"{symbol}{strike}{signal_type.value}",
                                        option_type=signal_type,
                                        strike=strike,
                                        quantity=quantity,
                                        'setup_type': 'morning_momentum',
                                        'adx': indicators['adx'],
                                        'volume_surge': indicators['volume_ratio'],
                                        'price_displacement': price_displacement,
                                        'time': current_time.strftime('%H:%M'),
                                        'vix': current_vix

                                        async def _check_trend_continuation(self, market_data: Dict,
                                        indicators: Dict, state: MomentumState,
                                        current_vix: Optional[float]) -> Optional[Signal]:
                                        """Check for trend continuation opportunities"""
                                        # Only if we have an established trend
                                    return None

                                    # Trend must be strong and continuing
                                    if indicators['adx'] < 25:
                                    return None

                                    # Price should be pulling back to VWAP but not breaking trend
                                    current_price=indicators['current_price']
                                    vwap_distance=abs(
                                    current_price - indicators['vwap']) / indicators['vwap']

                                    # Look for pullbacks (0.1% to 0.3% from VWAP
                                return None

                                # Volume should be moderately elevated
                                if indicators['volume_ratio'] < 1.1:
                                return None

                                # Direction confirmation
                                indicators['plus_di'] > indicators['minus_di'] and
                                indicators['rsi'] > 45):
                                signal_type=OptionType.CALL
                                indicators['minus_di'] > indicators['plus_di'] and
                                indicators['rsi'] < 55):
                                signal_type=OptionType.PUT
                                else:
                                return None

                                spot_price=market_data.get('spot_price', current_price
                                strike=await self._select_enhanced_strike(spot_price, signal_type, indicators, current_vix
                                quantity=await self._calculate_enhanced_quantity(market_data, indicators, current_vix, multiplier=0.8
                                symbol=market_data.get('symbol', 'NIFTY'
                            return Signal(
                            symbol=f"{symbol}{strike}{signal_type.value}",
                            option_type=signal_type,
                            strike=strike,
                            quantity=quantity,
                            'setup_type': 'trend_continuation',
                            'trend_direction': state.trend_direction,
                            'vwap_distance': vwap_distance,
                            'adx': indicators['adx'],
                            'rsi': indicators['rsi'],
                            'vix': current_vix

                            async def _calculate_enhanced_quality_score(self, signal: Signal, indicators: Dict,
                            state: MomentumState, current_vix: Optional[float]) -> float:
                            """Enhanced quality scoring with multiple factors from Set 1"""
                            base_score=float(self.base_quality_score
                            # Volume surge scoring (Set 1 logic
                            volume_ratio=indicators['volume_ratio']

                            # ADX strength scoring
                            adx=indicators['adx']

                            # Expected move scoring
                            expected_move=indicators['daily_atr_proxy']

                            # RSI positioning bonus
                            rsi=indicators['rsi']
                            else:

                                # Market regime bonus
                                regime=indicators.get('market_regime', 'NORMAL'
                                if regime in ['TRENDING_UP', 'TRENDING_DOWN']:
                                    elif regime in ['HIGH_VOL', 'ULTRA_HIGH_VOL']:

                                        # VIX level adjustment
                                        if current_vix:
                                            elif current_vix > 30:
                                                elif current_vix < 12:

                                                    # Time of day bonus
                                                    current_hour=datetime.now().hour

                                                    # Consecutive signals penalty (avoid overtrading
                                                    if state.consecutive_signals > 2:

                                                        # Setup type bonus
                                                        setup_type=signal.metadata.get('setup_type', ''
                                                        elif setup_type in ['vwap_break_bullish', 'vwap_break_bearish']:

                                                        return min(base_score, 10.0
                                                        async def _select_enhanced_strike(self, spot_price: float, option_type: OptionType,
                                                        indicators: Dict, current_vix: Optional[float]) -> int:
                                                        """Enhanced strike selection based on market conditions"""
                                                        # ATM as base
                                                        base_strike=get_atm_strike(spot_price
                                                        # Adjust based on trend strength and volatility
                                                        adx=indicators['adx']

                                                        # For very strong trends, go slightly OTM
                                                        if adx > 35:
                                                        return get_strike_with_offset(
                                                        spot_price, -1, option_type)  # Slightly OTM
                                                        else:
                                                        return get_strike_with_offset(spot_price, -1, option_type
                                                        # For normal trends, stay ATM
                                                    return base_strike

                                                    async def _calculate_enhanced_quantity(self, market_data: Dict, indicators: Dict,
                                                    """Enhanced quantity calculation with risk adjustment"""
                                                    base_quantity=self._calculate_quantity(market_data
                                                    # Adjust based on volatility
                                                    if current_vix:
                                                        if current_vix > 25:
                                                            elif current_vix < 15:

                                                                # Adjust based on trend strength
                                                                adx=indicators['adx']
                                                                if adx > 35:
                                                                    elif adx < 25:

                                                                        # Adjust based on volume surge
                                                                        volume_ratio=indicators['volume_ratio']
                                                                        if volume_ratio > 2.0:

                                                                            adjusted_quantity=int(base_quantity * multiplier
                                                                        return max(1, adjusted_quantity
                                                                        """Enhanced ATR calculation"""
                                                                        high=df['high']
                                                                        low=df['low']
                                                                        close=df['close']

                                                                        tr1=high - low
                                                                        tr2=abs(high - close.shift(
                                                                        tr3=abs(low - close.shift(
                                                                        tr=pd.concat([tr1, tr2, tr3], axis=1).max(axis=1
                                                                        atr=tr.rolling(window=period).mean().iloc[-1]

                                                                    return float(atr) if not pd.isna(atr) else 50.0

                                                                    def _calculate_enhanced_average_volume(:
                                                                    pass
                                                                    self, symbol: str, df: pd.DataFrame) -> float:
                                                                    """Enhanced average volume calculation with EMA"""
                                                                    if symbol not in self.volume_averages:
                                                                        # Initialize with 20-period SMA
                                                                        else:
                                                                            # Update with EMA (faster adaptation
                                                                            current_avg=self.volume_averages[symbol]
                                                                            new_volume=df['volume'].iloc[-1]
                                                                            alpha=0.1  # EMA smoothing factor

                                                                        return self.volume_averages[symbol]

                                                                        def _calculate_daily_atr_proxy(self, df: pd.DataFrame) -> float:
                                                                            """Calculate daily ATR proxy for expected move"""
                                                                            # Use larger timeframe for daily ATR estimation
                                                                            daily_ranges=[]
                                                                            for i in range(max(1, len(df) - 20), len(df)):
                                                                                if i > 0:
                                                                                    high=df['high'].iloc[i]
                                                                                    low=df['low'].iloc[i]
                                                                                    prev_close=df['close'].iloc[i-1]
                                                                                    tr=max(high - low, abs(high - prev_close), abs(low - prev_close
                                                                                    daily_ranges.append(tr
                                                                                    if daily_ranges:
                                                                                    return np.mean(daily_ranges) * 2.5  # Scale for daily estimation
                                                                                return 80.0  # Default fallback

                                                                                def _detect_market_regime(self, adx: float, plus_di: float, minus_di: float,:
                                                                                pass
                                                                                rsi: float, volume_ratio: float) -> str:
                                                                                """Detect current market regime"""
                                                                                if adx > 35:
                                                                                    if plus_di > minus_di:
                                                                                    return 'TRENDING_UP'
                                                                                    else:
                                                                                    return 'TRENDING_DOWN'
                                                                                    elif volume_ratio > 2.0:
                                                                                    return 'HIGH_VOL'
                                                                                    elif rsi > 70 or rsi < 30:
                                                                                    return 'EXTREME'
                                                                                    elif 20 < adx < 35:
                                                                                    return 'NORMAL'
                                                                                    else:
                                                                                    return 'RANGE_BOUND'

                                                                                    def _check_symbol_cooldown(self, symbol: str) -> bool:
                                                                                        """Check if symbol is in cooldown period"""
                                                                                        if symbol not in self.signal_cooldowns:
                                                                                        return True

                                                                                        last_signal=self.signal_cooldowns[symbol]
                                                                                        cooldown_period=timedelta(minutes=5)  # 5-minute cooldown

                                                                                    return datetime.now() - last_signal > cooldown_period

                                                                                    def _update_momentum_state(:
                                                                                    pass
                                                                                    self, state: MomentumState, signal: Signal, indicators: Dict):
                                                                                    """Update momentum state after signal generation"""

                                                                                    def _log_enhanced_signal(self, signal: Signal, indicators: Dict):
                                                                                        """Enhanced signal logging"""
                                                                                        setup_type=signal.metadata.get('setup_type', 'unknown'
                                                                                        logger.info(f"Enhanced Momentum Signal Generated:"
                                                                                        logger.info(f"  Type: {setup_type} - {signal.option_type.value}"
                                                                                        logger.info(f"  Strike: {signal.strike}"
                                                                                        logger.info(f"  Quality: {signal.quality_score:.2f}"
                                                                                        logger.info(f"  ADX: {indicators['adx'}:.1f}"
                                                                                        logger.info(f"  RSI: {indicators['rsi'}:.1f}"
                                                                                        logger.info(f"  Volume: {indicators['volume_ratio'}:.1f}x"
                                                                                        logger.info(f"  Expected Move: {indicators['daily_atr_proxy'}:.0f} pts"
                                                                                        def _is_morning_session(self] -> bool:
                                                                                            """Check if in morning trading session"""
                                                                                            current_time=datetime.now().time(
                                                                                            async def update_market_data(self, market_data: Dict):
                                                                                            """Update strategy with latest market data"""
                                                                                            symbol=market_data.get('symbol'
                                                                                            if symbol and 'spot_price' in market_data:
                                                                                                # Update any real-time calculations if needed
                                                                                            pass

                                                                                            def update_performance(self, trade_result: Dict):
                                                                                                """Update strategy performance metrics"""
                                                                                                setup_type=trade_result.get('metadata', {}).get('setup_type', 'unknown'
                                                                                                pnl=trade_result.get('pnl', 0
                                                                                                if setup_type in self.trades_by_setup:

                                                                                                    # Update win rate
                                                                                                    if pnl > 0:
                                                                                                        wins=self.trades_by_setup[setup_type].get('wins', 0) + 1
                                                                                                        wins / self.trades_by_setup[setup_type]['count']

                                                                                                        super().update_performance(trade_result
                                                                                                        def get_strategy_metrics(self) -> Dict:
                                                                                                            """Get enhanced strategy metrics"""
                                                                                                            base_metrics=super().get_strategy_metrics(
                                                                                                            active_states=sum(1 for state in self.momentum_states.values(
                                                                                                            enhanced_metrics={
                                                                                                            'trades_by_setup': self.trades_by_setup,
                                                                                                            'active_momentum_symbols': active_states,
                                                                                                            'recent_signals': len(self.signal_history),
                                                                                                            'symbol_cooldowns': len(self.signal_cooldowns),
                                                                                                            'current_parameters': {
                                                                                                            'volume_surge_multiplier': float(self.volume_surge_multiplier),
                                                                                                            'adx_threshold': float(self.adx_threshold),
                                                                                                            'min_expected_move': float(self.min_expected_move_points),
                                                                                                            'profit_target': float(self.profit_target_percent),
                                                                                                            'stop_loss': float(self.stop_loss_percent},
                                                                                                            'momentum_states': {
                                                                                                            symbol: {
                                                                                                            'trend_direction': state.trend_direction,
                                                                                                            'trend_strength': state.trend_strength,
                                                                                                            'consecutive_signals': state.consecutive_signals,
                                                                                                            'last_signal': state.last_signal_time.isoformat() if state.last_signal_time else None

                                                                                                            for symbol, state in self.momentum_states.items(

                                                                                                                base_metrics.update(enhanced_metrics
                                                                                                            return base_metrics

                                                                                                            def reset_daily_metrics(self):
                                                                                                                """Reset daily tracking metrics"""
                                                                                                                super().reset(
                                                                                                                # Reset momentum states
                                                                                                                self.momentum_states.clear(
                                                                                                                self.signal_cooldowns.clear(
                                                                                                                # Clear signal history
                                                                                                                self.signal_history.clear(
                                                                                                                # Reset daily performance tracking
                                                                                                                for setup in self.trades_by_setup.values():

                                                                                                                    logger.info("Enhanced Momentum Surfer daily metrics reset"

"""
Advanced Trading Strategies Implementation
Comprehensive business logic with risk management and performance tracking
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod

from .base import BaseStrategy, StrategyMetrics
from .risk_manager import RiskManager
from ..models import Signal, Position, OrderSide, MarketData
from ..utils import calculate_technical_indicators

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY = "volatility"
    ARBITRAGE = "arbitrage"
    SCALPING = "scalping"

@dataclass
class StrategyParameters:
    """Dynamic strategy parameters with optimization support"""
    # Common parameters
    lookback_period: int = 20
    risk_per_trade: float = 0.01
    max_positions: int = 5
    
    # Technical indicators
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    macd_threshold: float = 0.0
    bollinger_std: float = 2.0
    
    # Risk management
    stop_loss: float = 0.02
    take_profit: float = 0.04
    trailing_stop: float = 0.015
    
    # Market conditions
    min_volume: int = 100000
    min_volatility: float = 0.005
    max_spread: float = 0.001
    
    # Momentum specific
    momentum_threshold: float = 0.02
    momentum_confirmation: int = 3
    
    # Mean reversion specific
    reversion_threshold: float = 2.0
    reversion_period: int = 5
    
    # Volatility specific
    vol_breakout_threshold: float = 1.5
    vol_mean_period: int = 20

class MomentumStrategy(BaseStrategy):
    """Advanced momentum trading strategy with trend confirmation"""
    
    def __init__(self, params: StrategyParameters):
        super().__init__(
            name="Momentum_v2",
            description="Advanced momentum strategy with trend confirmation",
            strategy_type=StrategyType.MOMENTUM
        )
        self.params = params
        self.trend_confirmation = {}
        self.breakout_levels = {}
        
    async def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate momentum-based trading signals"""
        signals = []
        
        for symbol, data in market_data.items():
            try:
                # Skip if insufficient data
                if len(data.price_history) < self.params.lookback_period:
                    continue
                    
                # Calculate technical indicators
                indicators = await self._calculate_indicators(data)
                
                # Check market conditions
                if not self._check_market_conditions(data, indicators):
                    continue
                
                # Generate momentum signal
                signal = await self._analyze_momentum(symbol, data, indicators)
                if signal and self._validate_signal(signal):
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating momentum signal for {symbol}: {e}")
                
        return signals
    
    async def _calculate_indicators(self, data: MarketData) -> Dict:
        """Calculate technical indicators for momentum analysis"""
        prices = np.array([candle.close for candle in data.price_history])
        volumes = np.array([candle.volume for candle in data.price_history])
        
        # Price-based indicators
        sma_20 = np.mean(prices[-20:])
        sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else sma_20
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        # Momentum indicators
        rsi = self._calculate_rsi(prices, 14)
        macd = ema_12 - ema_26
        macd_signal = self._calculate_ema(np.array([macd] * 9), 9)
        
        # Volatility indicators
        atr = self._calculate_atr(data.price_history[-20:])
        bollinger_upper, bollinger_lower = self._calculate_bollinger_bands(prices)
        
        # Volume indicators
        volume_sma = np.mean(volumes[-20:])
        volume_ratio = volumes[-1] / volume_sma if volume_sma > 0 else 1
        
        return {
            'sma_20': sma_20,
            'sma_50': sma_50,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'atr': atr,
            'bollinger_upper': bollinger_upper,
            'bollinger_lower': bollinger_lower,
            'volume_ratio': volume_ratio,
            'current_price': prices[-1]
        }
    
    async def _analyze_momentum(self, symbol: str, data: MarketData, indicators: Dict) -> Optional[Signal]:
        """Analyze momentum patterns and generate signals"""
        current_price = indicators['current_price']
        
        # Trend confirmation
        trend_score = self._calculate_trend_score(indicators)
        
        # Momentum confirmation
        momentum_score = self._calculate_momentum_score(indicators)
        
        # Volume confirmation
        volume_score = self._calculate_volume_score(indicators)
        
        # Combined signal strength
        signal_strength = (trend_score + momentum_score + volume_score) / 3
        
        # Determine signal direction
        if signal_strength > 0.7:  # Strong bullish momentum
            side = OrderSide.BUY
            quality_score = signal_strength * 100
            stop_loss = current_price * (1 - self.params.stop_loss)
            take_profit = current_price * (1 + self.params.take_profit)
            
        elif signal_strength < -0.7:  # Strong bearish momentum
            side = OrderSide.SELL
            quality_score = abs(signal_strength) * 100
            stop_loss = current_price * (1 + self.params.stop_loss)
            take_profit = current_price * (1 - self.params.take_profit)
            
        else:
            return None
        
        return Signal(
            symbol=symbol,
            side=side,
            quantity=0,  # Will be calculated by position sizer
            expected_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=self.name,
            quality_score=quality_score,
            metadata={
                'trend_score': trend_score,
                'momentum_score': momentum_score,
                'volume_score': volume_score,
                'rsi': indicators['rsi'],
                'macd': indicators['macd'],
                'atr': indicators['atr'],
                'signal_type': 'momentum_breakout'
            }
        )
    
    def _calculate_trend_score(self, indicators: Dict) -> float:
        """Calculate trend strength score (-1 to 1)"""
        score = 0
        
        # SMA trend
        if indicators['sma_20'] > indicators['sma_50']:
            score += 0.3
        else:
            score -= 0.3
            
        # Price vs SMA
        if indicators['current_price'] > indicators['sma_20']:
            score += 0.3
        else:
            score -= 0.3
            
        # MACD trend
        if indicators['macd'] > indicators['macd_signal']:
            score += 0.4
        else:
            score -= 0.4
            
        return max(-1, min(1, score))
    
    def _calculate_momentum_score(self, indicators: Dict) -> float:
        """Calculate momentum strength score (-1 to 1)"""
        score = 0
        
        # RSI momentum
        rsi = indicators['rsi']
        if 50 < rsi < 70:
            score += 0.4
        elif 30 < rsi < 50:
            score -= 0.4
        elif rsi >= 70:
            score -= 0.2  # Overbought
        elif rsi <= 30:
            score += 0.2  # Oversold
            
        # MACD momentum
        macd_strength = abs(indicators['macd']) / indicators['atr'] if indicators['atr'] > 0 else 0
        if macd_strength > 0.5:
            score += 0.3 * (1 if indicators['macd'] > 0 else -1)
        
        # Price momentum
        price_change = (indicators['current_price'] - indicators['sma_20']) / indicators['sma_20']
        if abs(price_change) > self.params.momentum_threshold:
            score += 0.3 * (1 if price_change > 0 else -1)
            
        return max(-1, min(1, score))
    
    def _calculate_volume_score(self, indicators: Dict) -> float:
        """Calculate volume confirmation score (0 to 1)"""
        volume_ratio = indicators['volume_ratio']
        
        if volume_ratio > 1.5:
            return 1.0  # Strong volume confirmation
        elif volume_ratio > 1.2:
            return 0.7  # Good volume confirmation
        elif volume_ratio > 1.0:
            return 0.4  # Adequate volume
        else:
            return 0.1  # Weak volume
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, candles: List) -> float:
        """Calculate Average True Range"""
        if len(candles) < 2:
            return 0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i-1].close)
            low_close = abs(candles[i].low - candles[i-1].close)
            true_ranges.append(max(high_low, high_close, low_close))
            
        return np.mean(true_ranges)
    
    def _calculate_bollinger_bands(self, prices: np.ndarray) -> Tuple[float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < 20:
            return prices[-1] * 1.02, prices[-1] * 0.98
        
        sma = np.mean(prices[-20:])
        std = np.std(prices[-20:])
        
        upper = sma + (self.params.bollinger_std * std)
        lower = sma - (self.params.bollinger_std * std)
        
        return upper, lower

class MeanReversionStrategy(BaseStrategy):
    """Advanced mean reversion strategy with statistical analysis"""
    
    def __init__(self, params: StrategyParameters):
        super().__init__(
            name="MeanReversion_v2",
            description="Advanced mean reversion with statistical analysis",
            strategy_type=StrategyType.MEAN_REVERSION
        )
        self.params = params
        self.price_deviations = {}
        
    async def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate mean reversion signals"""
        signals = []
        
        for symbol, data in market_data.items():
            try:
                if len(data.price_history) < self.params.lookback_period:
                    continue
                
                # Calculate statistical metrics
                stats = await self._calculate_statistics(data)
                
                # Check for mean reversion opportunities
                signal = await self._analyze_reversion(symbol, data, stats)
                if signal and self._validate_signal(signal):
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating mean reversion signal for {symbol}: {e}")
                
        return signals
    
    async def _calculate_statistics(self, data: MarketData) -> Dict:
        """Calculate statistical metrics for mean reversion"""
        prices = np.array([candle.close for candle in data.price_history])
        
        # Statistical measures
        mean_price = np.mean(prices[-self.params.lookback_period:])
        std_price = np.std(prices[-self.params.lookback_period:])
        current_price = prices[-1]
        
        # Z-score calculation
        z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
        
        # Bollinger position
        bollinger_upper = mean_price + (2 * std_price)
        bollinger_lower = mean_price - (2 * std_price)
        
        # Calculate RSI for momentum confirmation
        rsi = self._calculate_rsi(prices)
        
        # Linear regression trend
        x = np.arange(len(prices[-self.params.lookback_period:]))
        y = prices[-self.params.lookback_period:]
        slope = np.polyfit(x, y, 1)[0]
        
        return {
            'mean_price': mean_price,
            'std_price': std_price,
            'current_price': current_price,
            'z_score': z_score,
            'bollinger_upper': bollinger_upper,
            'bollinger_lower': bollinger_lower,
            'rsi': rsi,
            'trend_slope': slope
        }
    
    async def _analyze_reversion(self, symbol: str, data: MarketData, stats: Dict) -> Optional[Signal]:
        """Analyze mean reversion opportunities"""
        z_score = stats['z_score']
        current_price = stats['current_price']
        mean_price = stats['mean_price']
        
        # Check for extreme deviation
        if abs(z_score) < self.params.reversion_threshold:
            return None
        
        # Determine signal direction
        if z_score > self.params.reversion_threshold:  # Price too high, expect reversion down
            side = OrderSide.SELL
            quality_score = min(100, abs(z_score) * 30)
            stop_loss = current_price * (1 + self.params.stop_loss)
            take_profit = mean_price
            
        elif z_score < -self.params.reversion_threshold:  # Price too low, expect reversion up
            side = OrderSide.BUY
            quality_score = min(100, abs(z_score) * 30)
            stop_loss = current_price * (1 - self.params.stop_loss)
            take_profit = mean_price
            
        else:
            return None
        
        # Additional confirmations
        rsi_confirmation = self._check_rsi_confirmation(stats['rsi'], side)
        trend_confirmation = self._check_trend_confirmation(stats['trend_slope'], side)
        
        if not (rsi_confirmation and trend_confirmation):
            quality_score *= 0.7  # Reduce quality without full confirmation
        
        return Signal(
            symbol=symbol,
            side=side,
            quantity=0,  # Will be calculated by position sizer
            expected_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=self.name,
            quality_score=quality_score,
            metadata={
                'z_score': z_score,
                'mean_price': mean_price,
                'std_price': stats['std_price'],
                'rsi': stats['rsi'],
                'trend_slope': stats['trend_slope'],
                'signal_type': 'mean_reversion'
            }
        )
    
    def _check_rsi_confirmation(self, rsi: float, side: OrderSide) -> bool:
        """Check if RSI confirms the mean reversion signal"""
        if side == OrderSide.BUY:
            return rsi < 40  # Oversold for buy signals
        else:
            return rsi > 60  # Overbought for sell signals
    
    def _check_trend_confirmation(self, slope: float, side: OrderSide) -> bool:
        """Check if trend slope confirms the reversion signal"""
        if side == OrderSide.BUY:
            return slope < 0  # Downward trend for buy (reversion) signals
        else:
            return slope > 0  # Upward trend for sell (reversion) signals

class VolatilityStrategy(BaseStrategy):
    """Advanced volatility-based trading strategy"""
    
    def __init__(self, params: StrategyParameters):
        super().__init__(
            name="Volatility_v2",
            description="Advanced volatility breakout strategy",
            strategy_type=StrategyType.VOLATILITY
        )
        self.params = params
        self.volatility_history = {}
        
    async def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate volatility-based signals"""
        signals = []
        
        for symbol, data in market_data.items():
            try:
                if len(data.price_history) < self.params.vol_mean_period:
                    continue
                
                # Calculate volatility metrics
                vol_metrics = await self._calculate_volatility_metrics(data)
                
                # Check for volatility breakout
                signal = await self._analyze_volatility_breakout(symbol, data, vol_metrics)
                if signal and self._validate_signal(signal):
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating volatility signal for {symbol}: {e}")
                
        return signals
    
    async def _calculate_volatility_metrics(self, data: MarketData) -> Dict:
        """Calculate volatility-based metrics"""
        prices = np.array([candle.close for candle in data.price_history])
        returns = np.diff(np.log(prices))
        
        # Current volatility
        current_vol = np.std(returns[-5:]) * np.sqrt(252)  # Annualized
        
        # Historical volatility
        hist_vol = np.std(returns[-self.params.vol_mean_period:]) * np.sqrt(252)
        
        # Volatility ratio
        vol_ratio = current_vol / hist_vol if hist_vol > 0 else 1
        
        # ATR-based volatility
        atr = self._calculate_atr(data.price_history[-20:])
        current_price = prices[-1]
        atr_pct = atr / current_price if current_price > 0 else 0
        
        return {
            'current_vol': current_vol,
            'hist_vol': hist_vol,
            'vol_ratio': vol_ratio,
            'atr': atr,
            'atr_pct': atr_pct,
            'current_price': current_price
        }
    
    async def _analyze_volatility_breakout(self, symbol: str, data: MarketData, vol_metrics: Dict) -> Optional[Signal]:
        """Analyze volatility breakout patterns"""
        vol_ratio = vol_metrics['vol_ratio']
        
        # Check for volatility expansion
        if vol_ratio < self.params.vol_breakout_threshold:
            return None
        
        # Determine breakout direction using price action
        prices = np.array([candle.close for candle in data.price_history[-10:]])
        price_momentum = (prices[-1] - prices[0]) / prices[0]
        
        current_price = vol_metrics['current_price']
        atr = vol_metrics['atr']
        
        if price_momentum > 0.01:  # Upward breakout
            side = OrderSide.BUY
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 3)
        elif price_momentum < -0.01:  # Downward breakout
            side = OrderSide.SELL
            stop_loss = current_price + (atr * 2)
            take_profit = current_price - (atr * 3)
        else:
            return None  # No clear direction
        
        # Quality score based on volatility expansion
        quality_score = min(100, vol_ratio * 50)
        
        return Signal(
            symbol=symbol,
            side=side,
            quantity=0,  # Will be calculated by position sizer
            expected_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=self.name,
            quality_score=quality_score,
            metadata={
                'vol_ratio': vol_ratio,
                'current_vol': vol_metrics['current_vol'],
                'hist_vol': vol_metrics['hist_vol'],
                'atr_pct': vol_metrics['atr_pct'],
                'price_momentum': price_momentum,
                'signal_type': 'volatility_breakout'
            }
        )

class AdvancedTradingEngine:
    """Advanced trading engine orchestrating multiple strategies"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.strategies = {}
        self.strategy_allocations = {}
        self.performance_tracker = {}
        
        # Initialize strategies with different parameters
        self._initialize_strategies()
        
    def _initialize_strategies(self):
        """Initialize different strategy instances"""
        # Momentum strategies with different parameters
        momentum_aggressive = StrategyParameters(
            lookback_period=10,
            momentum_threshold=0.03,
            stop_loss=0.015,
            take_profit=0.045
        )
        
        momentum_conservative = StrategyParameters(
            lookback_period=20,
            momentum_threshold=0.02,
            stop_loss=0.02,
            take_profit=0.04
        )
        
        # Mean reversion strategies
        reversion_short = StrategyParameters(
            lookback_period=15,
            reversion_threshold=1.8,
            stop_loss=0.015,
            take_profit=0.03
        )
        
        reversion_long = StrategyParameters(
            lookback_period=30,
            reversion_threshold=2.2,
            stop_loss=0.02,
            take_profit=0.04
        )
        
        # Volatility strategy
        vol_params = StrategyParameters(
            vol_mean_period=20,
            vol_breakout_threshold=1.5,
            stop_loss=0.025,
            take_profit=0.05
        )
        
        # Create strategy instances
        self.strategies = {
            'momentum_aggressive': MomentumStrategy(momentum_aggressive),
            'momentum_conservative': MomentumStrategy(momentum_conservative),
            'mean_reversion_short': MeanReversionStrategy(reversion_short),
            'mean_reversion_long': MeanReversionStrategy(reversion_long),
            'volatility_breakout': VolatilityStrategy(vol_params)
        }
        
        # Set equal allocations initially
        allocation = 1.0 / len(self.strategies)
        self.strategy_allocations = {name: allocation for name in self.strategies.keys()}
    
    async def generate_all_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate signals from all strategies"""
        all_signals = []
        
        # Generate signals from each strategy
        for strategy_name, strategy in self.strategies.items():
            try:
                signals = await strategy.generate_signals(market_data)
                
                # Apply strategy allocation to signal quality
                allocation = self.strategy_allocations[strategy_name]
                for signal in signals:
                    signal.quality_score *= allocation
                    
                all_signals.extend(signals)
                
            except Exception as e:
                logger.error(f"Error generating signals from {strategy_name}: {e}")
        
        # Remove duplicate signals and rank by quality
        unique_signals = self._remove_duplicate_signals(all_signals)
        ranked_signals = sorted(unique_signals, key=lambda s: s.quality_score, reverse=True)
        
        return ranked_signals[:10]  # Return top 10 signals
    
    def _remove_duplicate_signals(self, signals: List[Signal]) -> List[Signal]:
        """Remove duplicate signals for the same symbol"""
        symbol_signals = {}
        
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = signal
            else:
                # Keep the higher quality signal
                if signal.quality_score > symbol_signals[signal.symbol].quality_score:
                    symbol_signals[signal.symbol] = signal
        
        return list(symbol_signals.values())
    
    async def update_strategy_performance(self, strategy_name: str, performance_data: Dict):
        """Update strategy performance and adjust allocations"""
        if strategy_name not in self.performance_tracker:
            self.performance_tracker[strategy_name] = {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0
            }
        
        tracker = self.performance_tracker[strategy_name]
        tracker['total_trades'] += 1
        
        if performance_data['pnl'] > 0:
            tracker['winning_trades'] += 1
        
        tracker['total_pnl'] += performance_data['pnl']
        
        # Rebalance allocations based on performance
        await self._rebalance_strategy_allocations()
    
    async def _rebalance_strategy_allocations(self):
        """Rebalance strategy allocations based on performance"""
        if not self.performance_tracker:
            return
        
        # Calculate performance scores
        performance_scores = {}
        for strategy_name, data in self.performance_tracker.items():
            if data['total_trades'] > 0:
                win_rate = data['winning_trades'] / data['total_trades']
                avg_pnl = data['total_pnl'] / data['total_trades']
                performance_scores[strategy_name] = win_rate * avg_pnl
            else:
                performance_scores[strategy_name] = 0
        
        # Normalize scores to allocations
        total_score = sum(max(0, score) for score in performance_scores.values())
        if total_score > 0:
            for strategy_name in self.strategies.keys():
                score = max(0, performance_scores.get(strategy_name, 0))
                self.strategy_allocations[strategy_name] = score / total_score
        
        logger.info(f"Updated strategy allocations: {self.strategy_allocations}") 
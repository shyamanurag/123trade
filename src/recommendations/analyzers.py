"""
Perfect Analyzer Classes for Elite Trade Recommendations
These analyzers ensure only 10/10 quality setups are identified
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PerfectTechnicalAnalyzer:
    """Analyzer for perfect technical setups"""
    
    async def analyze(self, data: pd.DataFrame, all_timeframes: Dict) -> Dict:
        """Analyze for perfect technical confluence"""
        score = 0.0
        analysis = {}
        
        # 1. Trend alignment across all timeframes (2 points)
        trend_alignment = self._check_trend_alignment(all_timeframes)
        if trend_alignment['perfect_alignment']:
            score += 2.0
            analysis['trend_direction'] = trend_alignment['direction']
        else:
            return {'score': score, 'analysis': analysis}
        
        # 2. Support/Resistance at key level (2 points)
        sr_analysis = self._analyze_support_resistance(data)
        if sr_analysis['at_major_level']:
            score += 2.0
            analysis.update(sr_analysis)
        else:
            return {'score': score, 'analysis': analysis}
        
        # 3. Momentum confirmation (2 points)
        momentum = self._analyze_momentum(data)
        if momentum['perfect_momentum']:
            score += 2.0
            analysis.update(momentum)
        else:
            return {'score': score, 'analysis': analysis}
        
        # 4. Divergence confirmation (2 points)
        divergence = self._check_divergences(data)
        if divergence['confirmed']:
            score += 2.0
            analysis.update(divergence)
        
        # 5. Moving average setup (2 points)
        ma_setup = self._check_ma_setup(data)
        if ma_setup['perfect_setup']:
            score += 2.0
            analysis.update(ma_setup)
        
        analysis['score'] = score
        analysis['current_price'] = float(data['close'].iloc[-1])
        
        return analysis
    
    def _check_trend_alignment(self, timeframes: Dict) -> Dict:
        """Check if all timeframes show same trend"""
        trends = {}
        
        for tf_name, tf_data in timeframes.items():
            if tf_data is None or len(tf_data) < 50:
                continue
                
            sma_20 = tf_data['close'].rolling(20).mean()
            sma_50 = tf_data['close'].rolling(50).mean()
            
            if len(sma_20) > 0 and len(sma_50) > 0:
                if sma_20.iloc[-1] > sma_50.iloc[-1]:
                    trends[tf_name] = 'bullish'
                else:
                    trends[tf_name] = 'bearish'
        
        # Check if all trends align
        trend_values = list(trends.values())
        if len(trend_values) >= 3 and all(t == trend_values[0] for t in trend_values):
            return {
                'perfect_alignment': True,
                'direction': trend_values[0]
            }
        
        return {'perfect_alignment': False}
    
    def _analyze_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Analyze support/resistance levels"""
        # Find major levels using pivot points and historical data
        highs = data['high'].rolling(20).max()
        lows = data['low'].rolling(20).min()
        
        current = data['close'].iloc[-1]
        
        # Check if at major level
        major_levels = []
        
        # Add recent highs/lows
        for i in range(20, len(data), 20):
            major_levels.append(highs.iloc[i])
            major_levels.append(lows.iloc[i])
        
        # Check proximity to major level
        for level in major_levels:
            if abs(current - level) / level < 0.002:  # Within 0.2%
                return {
                    'at_major_level': True,
                    'major_support': min(l for l in major_levels if l < current),
                    'major_resistance': min(l for l in major_levels if l > current),
                    'support_resistance_type': 'support' if current > level else 'resistance'
                }
        
        return {'at_major_level': False}
    
    def _analyze_momentum(self, data: pd.DataFrame) -> Dict:
        """Analyze momentum indicators"""
        # RSI
        rsi = self._calculate_rsi(data['close'])
        
        # MACD
        exp1 = data['close'].ewm(span=12).mean()
        exp2 = data['close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        
        # Check conditions
        perfect_momentum = False
        
        if 40 < rsi < 60:  # RSI in neutral zone
            if macd.iloc[-1] > signal.iloc[-1] and histogram.iloc[-1] > histogram.iloc[-2]:
                # Bullish momentum
                perfect_momentum = True
                momentum_state = 'building_bullish'
            elif macd.iloc[-1] < signal.iloc[-1] and histogram.iloc[-1] < histogram.iloc[-2]:
                # Bearish momentum
                perfect_momentum = True
                momentum_state = 'building_bearish'
        
        return {
            'perfect_momentum': perfect_momentum,
            'rsi': rsi,
            'rsi_condition': 'neutral' if 40 < rsi < 60 else 'overbought' if rsi > 70 else 'oversold',
            'macd_state': 'bullish' if macd.iloc[-1] > signal.iloc[-1] else 'bearish',
            'momentum_state': momentum_state if perfect_momentum else 'unclear'
        }
    
    def _check_divergences(self, data: pd.DataFrame) -> Dict:
        """Check for price/momentum divergences"""
        prices = data['close'].values[-20:]
        rsi_values = [self._calculate_rsi(data['close'].iloc[:i]) for i in range(len(data)-20, len(data))]
        
        # Look for divergence
        price_trend = 'up' if prices[-1] > prices[0] else 'down'
        rsi_trend = 'up' if rsi_values[-1] > rsi_values[0] else 'down'
        
        if price_trend != rsi_trend:
            return {
                'confirmed': True,
                'divergence_type': 'bullish' if price_trend == 'down' else 'bearish'
            }
        
        return {'confirmed': False}
    
    def _check_ma_setup(self, data: pd.DataFrame) -> Dict:
        """Check moving average setup"""
        sma_10 = data['close'].rolling(10).mean()
        sma_20 = data['close'].rolling(20).mean()
        sma_50 = data['close'].rolling(50).mean()
        sma_200 = data['close'].rolling(200).mean()
        
        current = data['close'].iloc[-1]
        
        # Perfect bullish setup
        if (current > sma_10.iloc[-1] > sma_20.iloc[-1] > 
            sma_50.iloc[-1] > sma_200.iloc[-1]):
            return {
                'perfect_setup': True,
                'ma_alignment': 'perfect_bullish'
            }
        
        # Perfect bearish setup
        if (current < sma_10.iloc[-1] < sma_20.iloc[-1] < 
            sma_50.iloc[-1] < sma_200.iloc[-1]):
            return {
                'perfect_setup': True,
                'ma_alignment': 'perfect_bearish'
            }
        
        return {'perfect_setup': False}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])


class PerfectVolumeAnalyzer:
    """Analyzer for perfect volume setups"""
    
    async def analyze(self, data: pd.DataFrame, microstructure: Dict) -> Dict:
        """Analyze for perfect volume confluence"""
        score = 0.0
        analysis = {}
        
        # 1. Volume surge (3 points)
        volume_surge = self._check_volume_surge(data)
        if volume_surge['significant_surge']:
            score += 3.0
            analysis.update(volume_surge)
        else:
            return {'score': score, 'analysis': analysis}
        
        # 2. Volume profile structure (3 points)
        profile = self._analyze_volume_profile(data)
        if profile['perfect_profile']:
            score += 3.0
            analysis.update(profile)
        
        # 3. Order flow analysis (2 points)
        order_flow = self._analyze_order_flow(microstructure)
        if order_flow['smart_money_detected']:
            score += 2.0
            analysis.update(order_flow)
        
        # 4. Volume patterns (2 points)
        patterns = self._check_volume_patterns(data)
        if patterns['bullish_pattern'] or patterns['bearish_pattern']:
            score += 2.0
            analysis.update(patterns)
        
        analysis['score'] = score
        
        return analysis
    
    def _check_volume_surge(self, data: pd.DataFrame) -> Dict:
        """Check for significant volume surge"""
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        return {
            'significant_surge': volume_ratio > 2.0,
            'volume_multiplier': volume_ratio,
            'current_volume': current_volume,
            'average_volume': avg_volume
        }
    
    def _analyze_volume_profile(self, data: pd.DataFrame) -> Dict:
        """Analyze volume profile structure"""
        # Calculate POC and value area
        prices = data['close'].values
        volumes = data['volume'].values
        
        price_levels = np.linspace(prices.min(), prices.max(), 50)
        volume_profile = np.zeros(len(price_levels) - 1)
        
        for i, price in enumerate(prices):
            level_idx = np.searchsorted(price_levels, price) - 1
            if 0 <= level_idx < len(volume_profile):
                volume_profile[level_idx] += volumes[i]
        
        # Find POC
        poc_idx = np.argmax(volume_profile)
        poc_price = price_levels[poc_idx]
        
        # Calculate value area
        total_volume = volume_profile.sum()
        target_volume = total_volume * 0.7
        
        # Determine profile type
        current_price = prices[-1]
        
        if abs(current_price - poc_price) / poc_price < 0.01:
            profile_type = 'at_poc'
            perfect = True
        elif current_price > poc_price * 1.02:
            profile_type = 'above_value'
            perfect = True
        else:
            profile_type = 'normal'
            perfect = False
        
        return {
            'perfect_profile': perfect,
            'profile_type': profile_type,
            'poc': poc_price,
            'vwap': np.average(prices, weights=volumes)
        }
    
    def _analyze_order_flow(self, microstructure: Dict) -> Dict:
        """Analyze order flow for smart money"""
        order_book = microstructure.get('order_book', {})
        recent_trades = microstructure.get('recent_trades', [])
        
        if not order_book or not recent_trades:
            return {'smart_money_detected': False}
        
        # Analyze order book imbalance
        bid_volume = sum(order['quantity'] for order in order_book.get('bids', [])[:5])
        ask_volume = sum(order['quantity'] for order in order_book.get('asks', [])[:5])
        
        imbalance_ratio = bid_volume / ask_volume if ask_volume > 0 else 1
        
        # Analyze large trades
        large_trades = [t for t in recent_trades if t.get('quantity', 0) > 1000]
        
        smart_money = (imbalance_ratio > 1.5 or imbalance_ratio < 0.67) and len(large_trades) > 5
        
        return {
            'smart_money_detected': smart_money,
            'order_flow_ratio': imbalance_ratio,
            'footprint_type': 'accumulation' if imbalance_ratio > 1.5 else 'distribution'
        }
    
    def _check_volume_patterns(self, data: pd.DataFrame) -> Dict:
        """Check for volume patterns"""
        recent_volumes = data['volume'].values[-10:]
        recent_closes = data['close'].values[-10:]
        
        # Check for accumulation/distribution
        up_volume = sum(recent_volumes[i] for i in range(len(recent_closes)-1) 
                       if recent_closes[i+1] > recent_closes[i])
        down_volume = sum(recent_volumes[i] for i in range(len(recent_closes)-1) 
                         if recent_closes[i+1] < recent_closes[i])
        
        bullish = up_volume > down_volume * 1.5
        bearish = down_volume > up_volume * 1.5
        
        return {
            'bullish_pattern': bullish,
            'bearish_pattern': bearish,
            'volume_trend': 'accumulation' if bullish else 'distribution' if bearish else 'neutral'
        }


class PerfectPatternAnalyzer:
    """Analyzer for perfect chart patterns"""
    
    async def analyze(self, data: pd.DataFrame, all_timeframes: Dict) -> Dict:
        """Analyze for perfect patterns"""
        score = 0.0
        analysis = {}
        
        # Check multiple pattern types
        patterns_found = []
        
        # 1. Classical patterns
        classical = self._check_classical_patterns(data)
        if classical['found']:
            patterns_found.append(classical)
        
        # 2. Harmonic patterns
        harmonic = self._check_harmonic_patterns(data)
        if harmonic['found']:
            patterns_found.append(harmonic)
        
        # 3. Candlestick patterns
        candlestick = self._check_candlestick_patterns(data)
        if candlestick['found']:
            patterns_found.append(candlestick)
        
        # Select best pattern
        if patterns_found:
            best_pattern = max(patterns_found, key=lambda x: x['quality_score'])
            
            if best_pattern['quality_score'] >= 9.0:
                score = 10.0
                analysis['primary_pattern'] = best_pattern
                analysis['historical_reliability'] = self._get_pattern_reliability(
                    best_pattern['type']
                )
        
        analysis['score'] = score
        
        return analysis
    
    def _check_classical_patterns(self, data: pd.DataFrame) -> Dict:
        """Check for classical chart patterns"""
        # Simplified - would implement full pattern recognition
        
        # Example: Check for cup and handle
        prices = data['close'].values[-60:]
        
        if len(prices) < 60:
            return {'found': False}
        
        # Find potential cup
        mid_point = len(prices) // 2
        left_peak = prices[:20].max()
        right_peak = prices[-20:].max()
        bottom = prices[mid_point-10:mid_point+10].min()
        
        # Check cup characteristics
        if (abs(left_peak - right_peak) / left_peak < 0.05 and  # Similar peaks
            bottom < left_peak * 0.85):  # Significant depth
            
            # Check for handle
            handle_data = prices[-10:]
            if handle_data.max() < right_peak * 0.98:  # Slight pullback
                return {
                    'found': True,
                    'type': 'cup_and_handle',
                    'direction': 'LONG',
                    'entry_trigger': right_peak * 1.001,
                    'stop_level': handle_data.min(),
                    'target': right_peak + (right_peak - bottom),
                    'quality_score': 9.5
                }
        
        return {'found': False}
    
    def _check_harmonic_patterns(self, data: pd.DataFrame) -> Dict:
        """Check for harmonic patterns"""
        # Would implement Gartley, Butterfly, Bat, Crab patterns
        # Placeholder for now
        return {'found': False}
    
    def _check_candlestick_patterns(self, data: pd.DataFrame) -> Dict:
        """Check for candlestick patterns"""
        # Check last few candles for powerful patterns
        
        # Example: Engulfing pattern
        if len(data) >= 2:
            prev_candle = data.iloc[-2]
            curr_candle = data.iloc[-1]
            
            # Bullish engulfing
            if (prev_candle['close'] < prev_candle['open'] and  # Previous bearish
                curr_candle['close'] > curr_candle['open'] and  # Current bullish
                curr_candle['open'] < prev_candle['close'] and  # Opens below prev close
                curr_candle['close'] > prev_candle['open']):    # Closes above prev open
                
                return {
                    'found': True,
                    'type': 'bullish_engulfing',
                    'direction': 'LONG',
                    'entry_trigger': curr_candle['high'],
                    'stop_level': curr_candle['low'],
                    'quality_score': 9.0
                }
        
        return {'found': False}
    
    def _get_pattern_reliability(self, pattern_type: str) -> float:
        """Get historical reliability percentage"""
        reliability_map = {
            'cup_and_handle': 82,
            'inverse_head_shoulders': 78,
            'ascending_triangle': 75,
            'bull_flag': 80,
            'bullish_engulfing': 72,
            'morning_star': 74,
            'double_bottom': 76
        }
        
        return reliability_map.get(pattern_type, 70)


class PerfectRegimeAnalyzer:
    """Analyzer for perfect market regime"""
    
    async def analyze(self, internals: Dict, daily_data: pd.DataFrame) -> Dict:
        """Analyze market regime perfection"""
        score = 0.0
        analysis = {}
        
        # 1. VIX analysis (3 points)
        vix_analysis = self._analyze_vix(internals.get('vix', {}))
        if vix_analysis['optimal_vix']:
            score += 3.0
            analysis.update(vix_analysis)
        else:
            return {'score': score, 'analysis': analysis}
        
        # 2. Market breadth (3 points)
        breadth = self._analyze_breadth(internals.get('breadth', {}))
        if breadth['strong_breadth']:
            score += 3.0
            analysis.update(breadth)
        
        # 3. Trend quality (2 points)
        trend = self._analyze_trend_quality(daily_data)
        if trend['high_quality_trend']:
            score += 2.0
            analysis.update(trend)
        
        # 4. Volatility regime (2 points)
        volatility = self._analyze_volatility_regime(daily_data)
        if volatility['optimal_volatility']:
            score += 2.0
            analysis.update(volatility)
        
        analysis['score'] = score
        
        return analysis
    
    def _analyze_vix(self, vix_data: Dict) -> Dict:
        """Analyze VIX conditions"""
        current_vix = vix_data.get('current', 20)
        vix_ma = vix_data.get('ma_20', 20)
        
        # Optimal VIX is between 12-20
        optimal = 12 <= current_vix <= 20
        
        condition = 'optimal'
        if current_vix < 12:
            condition = 'too_low'
        elif current_vix > 30:
            condition = 'too_high'
        elif current_vix > 20:
            condition = 'elevated'
        
        return {
            'optimal_vix': optimal,
            'vix_level': current_vix,
            'vix_condition': condition,
            'vix_trend': 'rising' if current_vix > vix_ma else 'falling'
        }
    
    def _analyze_breadth(self, breadth_data: Dict) -> Dict:
        """Analyze market breadth"""
        adv_dec = breadth_data.get('advance_decline_ratio', 1.0)
        new_highs = breadth_data.get('new_highs', 0)
        new_lows = breadth_data.get('new_lows', 0)
        
        # Strong breadth conditions
        strong = adv_dec > 2.0 or adv_dec < 0.5
        
        return {
            'strong_breadth': strong,
            'breadth_direction': 'bullish' if adv_dec > 1.5 else 'bearish' if adv_dec < 0.67 else 'neutral',
            'new_highs_lows': new_highs - new_lows
        }
    
    def _analyze_trend_quality(self, data: pd.DataFrame) -> Dict:
        """Analyze trend quality"""
        if len(data) < 50:
            return {'high_quality_trend': False}
        
        # Calculate ADX
        adx = self._calculate_adx(data)
        
        # High quality trend has ADX > 25
        high_quality = adx > 25
        
        regime_type = 'trending' if adx > 25 else 'ranging' if adx < 20 else 'transitional'
        
        return {
            'high_quality_trend': high_quality,
            'regime_type': regime_type,
            'adx_value': adx
        }
    
    def _analyze_volatility_regime(self, data: pd.DataFrame) -> Dict:
        """Analyze volatility regime"""
        # Calculate ATR
        atr = self._calculate_atr(data)
        atr_ma = atr.rolling(20).mean().iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Optimal is moderate volatility
        atr_ratio = current_atr / atr_ma
        optimal = 0.8 <= atr_ratio <= 1.5
        
        return {
            'optimal_volatility': optimal,
            'volatility_state': 'expanding' if atr_ratio > 1.2 else 'contracting' if atr_ratio < 0.8 else 'stable'
        }
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        atr = self._calculate_atr(data)
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr.rolling(window=period).mean())
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return float(adx.iloc[-1])
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr


class PerfectMomentumAnalyzer:
    """Analyzer for perfect momentum alignment"""
    
    async def analyze(self, timeframes: Dict) -> Dict:
        """Analyze momentum across timeframes"""
        score = 0.0
        analysis = {}
        
        # Check momentum in each timeframe
        momentum_scores = {}
        
        for tf_name, tf_data in timeframes.items():
            if tf_data is not None and len(tf_data) >= 50:
                tf_momentum = self._analyze_timeframe_momentum(tf_data)
                momentum_scores[tf_name] = tf_momentum
        
        # Check alignment
        if self._check_momentum_alignment(momentum_scores):
            score = 10.0
            
            # Determine overall momentum state
            direction = momentum_scores[list(momentum_scores.keys())[0]]['direction']
            
            analysis['momentum_state'] = f"perfectly_aligned_{direction}"
            analysis['momentum_scores'] = momentum_scores
            
            # Relative strength
            rs = self._calculate_relative_strength(timeframes.get('daily'))
            analysis['rs_condition'] = rs
        
        analysis['score'] = score
        
        return analysis
    
    def _analyze_timeframe_momentum(self, data: pd.DataFrame) -> Dict:
        """Analyze momentum for single timeframe"""
        # Rate of change
        roc = ((data['close'].iloc[-1] - data['close'].iloc[-10]) / 
               data['close'].iloc[-10] * 100)
        
        # RSI
        rsi = self._calculate_rsi(data['close'])
        
        # MACD
        macd, signal = self._calculate_macd(data['close'])
        
        # Determine direction
        if roc > 0 and rsi > 50 and macd > signal:
            direction = 'bullish'
            strength = min(roc / 2, 5.0)  # Cap at 5
        elif roc < 0 and rsi < 50 and macd < signal:
            direction = 'bearish'
            strength = min(abs(roc) / 2, 5.0)
        else:
            direction = 'neutral'
            strength = 0
        
        return {
            'direction': direction,
            'strength': strength,
            'roc': roc,
            'rsi': rsi
        }
    
    def _check_momentum_alignment(self, momentum_scores: Dict) -> bool:
        """Check if momentum aligns across timeframes"""
        if len(momentum_scores) < 3:
            return False
        
        directions = [m['direction'] for m in momentum_scores.values()]
        
        # All must be same direction and not neutral
        return (all(d == directions[0] for d in directions) and 
                directions[0] != 'neutral')
    
    def _calculate_relative_strength(self, daily_data: pd.DataFrame) -> str:
        """Calculate relative strength"""
        if daily_data is None or len(daily_data) < 20:
            return 'unknown'
        
        # Simple RS: compare to 20-day average
        current = daily_data['close'].iloc[-1]
        ma_20 = daily_data['close'].rolling(20).mean().iloc[-1]
        
        rs_ratio = current / ma_20
        
        if rs_ratio > 1.05:
            return 'strong_outperformance'
        elif rs_ratio > 1.02:
            return 'moderate_outperformance'
        elif rs_ratio < 0.95:
            return 'strong_underperformance'
        elif rs_ratio < 0.98:
            return 'moderate_underperformance'
        else:
            return 'neutral'
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[float, float]:
        """Calculate MACD"""
        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        
        return float(macd.iloc[-1]), float(signal.iloc[-1])


class SmartMoneyAnalyzer:
    """Analyzer for smart money activity"""
    
    async def analyze(self, options_data: pd.DataFrame, microstructure: Dict) -> Dict:
        """Analyze smart money activity"""
        score = 0.0
        analysis = {}
        
        # 1. Options flow analysis (5 points)
        options_flow = self._analyze_options_flow(options_data)
        if options_flow['smart_money_signal']:
            score += 5.0
            analysis.update(options_flow)
        else:
            return {'score': score, 'analysis': analysis}
        
        # 2. Large order detection (5 points)
        large_orders = self._detect_large_orders(microstructure)
        if large_orders['institutional_activity']:
            score += 5.0
            analysis.update(large_orders)
        
        analysis['score'] = score
        
        return analysis
    
    def _analyze_options_flow(self, options_data: pd.DataFrame) -> Dict:
        """Analyze options flow"""
        if options_data.empty:
            return {'smart_money_signal': False}
        
        # Calculate metrics
        call_oi = options_data[options_data['option_type'] == 'CE']['oi'].sum()
        put_oi = options_data[options_data['option_type'] == 'PE']['oi'].sum()
        
        pc_ratio = put_oi / call_oi if call_oi > 0 else 1
        
        # Look for unusual activity
        oi_changes = []
        for _, row in options_data.iterrows():
            if 'oi_change' in row:
                oi_changes.append(row['oi_change'])
        
        # Smart money signal when PC ratio is extreme but not too extreme
        smart_signal = (0.5 < pc_ratio < 0.7) or (1.3 < pc_ratio < 1.5)
        
        return {
            'smart_money_signal': smart_signal,
            'pc_ratio': pc_ratio,
            'institutional_bias': 'bullish' if pc_ratio < 0.7 else 'bearish' if pc_ratio > 1.3 else 'neutral',
            'unusual_options_activity': len(oi_changes) > 10
        }
    
    def _detect_large_orders(self, microstructure: Dict) -> Dict:
        """Detect large/institutional orders"""
        recent_trades = microstructure.get('recent_trades', [])
        
        if not recent_trades:
            return {'institutional_activity': False}
        
        # Identify large trades
        trade_sizes = [t.get('quantity', 0) for t in recent_trades]
        avg_size = np.mean(trade_sizes) if trade_sizes else 0
        
        large_trades = [t for t in recent_trades if t.get('quantity', 0) > avg_size * 5]
        
        # Calculate buy/sell imbalance
        large_buys = sum(t['quantity'] for t in large_trades if t.get('side') == 'buy')
        large_sells = sum(t['quantity'] for t in large_trades if t.get('side') == 'sell')
        
        imbalance = large_buys / large_sells if large_sells > 0 else 2.0
        
        return {
            'institutional_activity': len(large_trades) > 5,
            'large_trade_count': len(large_trades),
            'order_flow_imbalance': imbalance,
            'institutional_direction': 'buying' if imbalance > 1.5 else 'selling' if imbalance < 0.67 else 'mixed'
        } 
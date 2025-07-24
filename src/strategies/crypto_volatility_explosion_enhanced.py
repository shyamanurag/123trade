# strategies/crypto_volatility_explosion_enhanced.py
"""
Enhanced Crypto Volatility Explosion Strategy
Trades volatility breakouts with black swan detection and risk management
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class VolatilityState:
    """Represents volatility state for a symbol"""
    symbol: str
    current_volatility: float
    historical_volatility: float
    volatility_percentile: float
    direction_bias: str  # UP, DOWN, NEUTRAL
    explosion_probability: float
    black_swan_risk: float
    last_updated: datetime

class EnhancedCryptoVolatilityExplosion:
    """
    Enhanced volatility explosion strategy with black swan detection
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Volatility parameters
        self.normal_volatility_threshold = config.get('normal_volatility_threshold', 0.06)
        self.extreme_volatility_threshold = config.get('extreme_volatility_threshold', 0.20)
        self.explosion_threshold = config.get('explosion_threshold', 0.75)
        
        # Black swan detection
        self.black_swan_threshold = config.get('black_swan_threshold', 0.60)
        self.correlation_break_threshold = config.get('correlation_break_threshold', 0.5)
        
        # Analysis windows
        self.short_window = config.get('short_window_minutes', 15)
        self.long_window = config.get('long_window_minutes', 240)
        self.volatility_lookback_days = config.get('volatility_lookback_days', 30)
        
        # Symbol tracking
        self.volatility_states = {}
        self.price_history = {}
        self.volatility_history = deque(maxlen=1000)
        
        # Performance tracking
        self.signals_generated = 0
        self.explosion_signals = 0
        self.black_swan_warnings = 0
        
        logger.info("Enhanced Crypto Volatility Explosion initialized")

    async def start(self):
        """Start the volatility explosion strategy"""
        logger.info("💥 Starting Enhanced Crypto Volatility Explosion...")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_volatility())
        asyncio.create_task(self._detect_explosions())
        asyncio.create_task(self._monitor_black_swan_risks())
        
        logger.info("✅ Enhanced Crypto Volatility Explosion started")

    async def get_volatility_signals(self) -> List[Dict]:
        """Get current volatility-based trading signals"""
        try:
            signals = []
            
            for symbol, state in self.volatility_states.items():
                # Check for volatility explosion
                if state.explosion_probability > self.explosion_threshold:
                    signal = await self._create_explosion_signal(state)
                    if signal:
                        signals.append(signal)
                
                # Check for black swan warning
                if state.black_swan_risk > self.black_swan_threshold:
                    warning = await self._create_black_swan_warning(state)
                    if warning:
                        signals.append(warning)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting volatility signals: {e}")
            return []

    async def update_price_data(self, symbol: str, price: float, timestamp: datetime):
        """Update price data for volatility analysis"""
        try:
            if symbol not in self.price_history:
                self.price_history[symbol] = deque(maxlen=500)
            
            self.price_history[symbol].append({
                'price': price,
                'timestamp': timestamp
            })
            
            # Update volatility state
            await self._update_volatility_state(symbol)
            
        except Exception as e:
            logger.error(f"Error updating price data for {symbol}: {e}")

    async def _update_volatility_state(self, symbol: str):
        """Update volatility state for a symbol"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
                return
            
            # Get recent price data
            prices = [data['price'] for data in list(self.price_history[symbol])]
            
            # Calculate returns
            returns = np.diff(prices) / prices[:-1]
            
            # Calculate volatilities
            short_returns = returns[-self.short_window:] if len(returns) >= self.short_window else returns
            long_returns = returns[-self.long_window:] if len(returns) >= self.long_window else returns
            
            current_volatility = np.std(short_returns) * np.sqrt(1440)  # Annualized (1440 minutes per day)
            historical_volatility = np.std(long_returns) * np.sqrt(1440)
            
            # Calculate volatility percentile
            if len(returns) >= 100:
                volatility_percentile = self._calculate_volatility_percentile(current_volatility, returns)
            else:
                volatility_percentile = 0.5
            
            # Determine direction bias
            direction_bias = self._calculate_direction_bias(prices)
            
            # Calculate explosion probability
            explosion_probability = self._calculate_explosion_probability(
                current_volatility, historical_volatility, volatility_percentile
            )
            
            # Calculate black swan risk
            black_swan_risk = await self._calculate_black_swan_risk(symbol, current_volatility)
            
            # Update state
            self.volatility_states[symbol] = VolatilityState(
                symbol=symbol,
                current_volatility=current_volatility,
                historical_volatility=historical_volatility,
                volatility_percentile=volatility_percentile,
                direction_bias=direction_bias,
                explosion_probability=explosion_probability,
                black_swan_risk=black_swan_risk,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error updating volatility state for {symbol}: {e}")

    def _calculate_volatility_percentile(self, current_vol: float, returns: np.ndarray) -> float:
        """Calculate volatility percentile"""
        try:
            # Calculate rolling volatilities
            window_size = 20
            rolling_vols = []
            
            for i in range(window_size, len(returns)):
                window_returns = returns[i-window_size:i]
                rolling_vol = np.std(window_returns) * np.sqrt(1440)
                rolling_vols.append(rolling_vol)
            
            if not rolling_vols:
                return 0.5
            
            # Calculate percentile
            percentile = (np.sum(np.array(rolling_vols) < current_vol) / len(rolling_vols))
            return percentile
            
        except Exception as e:
            logger.error(f"Error calculating volatility percentile: {e}")
            return 0.5

    def _calculate_direction_bias(self, prices: List[float]) -> str:
        """Calculate directional bias"""
        try:
            if len(prices) < 10:
                return 'NEUTRAL'
            
            # Calculate trend using linear regression
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            
            # Calculate momentum
            short_ma = np.mean(prices[-5:])
            long_ma = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
            
            # Combine trend and momentum
            trend_bias = 'UP' if slope > 0 else 'DOWN'
            momentum_bias = 'UP' if short_ma > long_ma else 'DOWN'
            
            if trend_bias == momentum_bias:
                return trend_bias
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"Error calculating direction bias: {e}")
            return 'NEUTRAL'

    def _calculate_explosion_probability(self, current_vol: float, historical_vol: float, 
                                       percentile: float) -> float:
        """Calculate volatility explosion probability"""
        try:
            # Volatility spike factor
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            vol_spike_score = min(1.0, (vol_ratio - 1.0) / 2.0)  # Normalize to 0-1
            
            # Percentile score (higher percentile = higher probability)
            percentile_score = percentile
            
            # Volume spike consideration (simplified)
            volume_score = 0.5  # Would be calculated from actual volume data
            
            # Combine factors
            explosion_probability = (vol_spike_score * 0.5 + percentile_score * 0.3 + volume_score * 0.2)
            
            return min(1.0, explosion_probability)
            
        except Exception as e:
            logger.error(f"Error calculating explosion probability: {e}")
            return 0.0

    async def _calculate_black_swan_risk(self, symbol: str, current_vol: float) -> float:
        """Calculate black swan risk"""
        try:
            risk_factors = []
            
            # Extreme volatility factor
            if current_vol > self.extreme_volatility_threshold:
                vol_risk = (current_vol - self.extreme_volatility_threshold) / self.extreme_volatility_threshold
                risk_factors.append(min(1.0, vol_risk))
            
            # Market correlation breakdown (simplified)
            correlation_risk = 0.3  # Would calculate from actual correlation data
            risk_factors.append(correlation_risk)
            
            # Liquidity risk (simplified)
            liquidity_risk = 0.2  # Would calculate from order book data
            risk_factors.append(liquidity_risk)
            
            # System-wide stress (simplified)
            system_stress = 0.25  # Would calculate from multiple market indicators
            risk_factors.append(system_stress)
            
            # Calculate weighted average
            if risk_factors:
                black_swan_risk = sum(risk_factors) / len(risk_factors)
            else:
                black_swan_risk = 0.0
            
            return min(1.0, black_swan_risk)
            
        except Exception as e:
            logger.error(f"Error calculating black swan risk for {symbol}: {e}")
            return 0.0

    async def _create_explosion_signal(self, state: VolatilityState) -> Optional[Dict]:
        """Create volatility explosion signal"""
        try:
            # Determine signal direction based on bias
            if state.direction_bias == 'UP':
                direction = 'BUY'
            elif state.direction_bias == 'DOWN':
                direction = 'SELL'
            else:
                # For neutral bias, choose based on momentum
                direction = 'BUY'  # Default to buy on volatility explosions
            
            # Calculate signal strength
            strength = state.explosion_probability
            
            # Adjust for black swan risk (reduce strength if high risk)
            if state.black_swan_risk > self.black_swan_threshold:
                strength *= (1 - (state.black_swan_risk - self.black_swan_threshold))
            
            # Calculate confidence
            confidence = (state.volatility_percentile + state.explosion_probability) / 2
            
            return {
                'symbol': state.symbol,
                'direction': direction,
                'strength': strength,
                'confidence': confidence,
                'current_volatility': state.current_volatility,
                'explosion_probability': state.explosion_probability,
                'black_swan_risk': state.black_swan_risk,
                'direction_bias': state.direction_bias,
                'signal_type': 'volatility_explosion',
                'timestamp': datetime.now(),
                'strategy': 'crypto_volatility_explosion'
            }
            
        except Exception as e:
            logger.error(f"Error creating explosion signal: {e}")
            return None

    async def _create_black_swan_warning(self, state: VolatilityState) -> Optional[Dict]:
        """Create black swan warning signal"""
        try:
            return {
                'symbol': state.symbol,
                'signal_type': 'black_swan_warning',
                'black_swan_risk': state.black_swan_risk,
                'current_volatility': state.current_volatility,
                'recommended_action': 'REDUCE_EXPOSURE',
                'urgency': 'HIGH' if state.black_swan_risk > 0.8 else 'MEDIUM',
                'timestamp': datetime.now(),
                'strategy': 'crypto_volatility_explosion'
            }
            
        except Exception as e:
            logger.error(f"Error creating black swan warning: {e}")
            return None

    async def _monitor_volatility(self):
        """Monitor volatility across all symbols - REAL DATA ONLY"""
        while True:
            try:
                # Get real symbols from database
                from ..core.database import get_db_session
                
                async with get_db_session() as session:
                    result = await session.execute("""
                        SELECT DISTINCT symbol 
                        FROM crypto_market_data 
                        WHERE timestamp >= NOW() - INTERVAL '1 hour'
                        AND close_price > 0
                        ORDER BY symbol
                        LIMIT 10
                    """)
                    
                    symbols = [row.symbol for row in result.fetchall()]
                
                if not symbols:
                    logger.warning("No symbols with real market data available")
                    await asyncio.sleep(60)
                    continue
                
                for symbol in symbols:
                    try:
                        # Get real price data
                        volatility_data = await self._calculate_real_volatility(symbol)
                        if volatility_data:
                            await self.update_price_data(symbol, volatility_data['current_price'], datetime.now())
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error monitoring volatility: {e}")
                await asyncio.sleep(60)

    async def _detect_explosions(self):
        """Detect and signal volatility explosions"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for symbol, state in self.volatility_states.items():
                    if state.explosion_probability > self.explosion_threshold:
                        self.explosion_signals += 1
                        
                        logger.info(f"💥 VOLATILITY EXPLOSION: {state.symbol} "
                                  f"Probability: {state.explosion_probability:.3f} "
                                  f"Current Vol: {state.current_volatility:.3f} "
                                  f"Bias: {state.direction_bias}")
                
            except Exception as e:
                logger.error(f"Error detecting explosions: {e}")
                await asyncio.sleep(60)

    async def _monitor_black_swan_risks(self):
        """Monitor for black swan risk events"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                high_risk_symbols = []
                for symbol, state in self.volatility_states.items():
                    if state.black_swan_risk > self.black_swan_threshold:
                        high_risk_symbols.append(symbol)
                
                if high_risk_symbols:
                    self.black_swan_warnings += 1
                    logger.warning(f"🚨 BLACK SWAN RISK WARNING: {high_risk_symbols} "
                                 f"Average Risk: {np.mean([self.volatility_states[s].black_swan_risk for s in high_risk_symbols]):.3f}")
                
            except Exception as e:
                logger.error(f"Error monitoring black swan risks: {e}")
                await asyncio.sleep(60)

    def get_performance_metrics(self) -> Dict:
        """Get volatility strategy performance metrics"""
        try:
            active_symbols = len(self.volatility_states)
            
            if active_symbols == 0:
                return {
                    'signals_generated': self.signals_generated,
                    'explosion_signals': self.explosion_signals,
                    'black_swan_warnings': self.black_swan_warnings
                }
            
            # Calculate average metrics
            avg_volatility = np.mean([state.current_volatility for state in self.volatility_states.values()])
            avg_explosion_prob = np.mean([state.explosion_probability for state in self.volatility_states.values()])
            avg_black_swan_risk = np.mean([state.black_swan_risk for state in self.volatility_states.values()])
            
            # Count high-risk symbols
            high_vol_symbols = len([s for s in self.volatility_states.values() if s.current_volatility > self.extreme_volatility_threshold])
            high_risk_symbols = len([s for s in self.volatility_states.values() if s.black_swan_risk > self.black_swan_threshold])
            
            return {
                'signals_generated': self.signals_generated,
                'explosion_signals': self.explosion_signals,
                'black_swan_warnings': self.black_swan_warnings,
                'active_symbols': active_symbols,
                'average_volatility': avg_volatility,
                'average_explosion_probability': avg_explosion_prob,
                'average_black_swan_risk': avg_black_swan_risk,
                'high_volatility_symbols': high_vol_symbols,
                'high_risk_symbols': high_risk_symbols
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    def get_volatility_report(self) -> Dict:
        """Get detailed volatility report"""
        try:
            report = {
                'timestamp': datetime.now(),
                'symbols': {}
            }
            
            for symbol, state in self.volatility_states.items():
                report['symbols'][symbol] = {
                    'current_volatility': state.current_volatility,
                    'historical_volatility': state.historical_volatility,
                    'volatility_percentile': state.volatility_percentile,
                    'direction_bias': state.direction_bias,
                    'explosion_probability': state.explosion_probability,
                    'black_swan_risk': state.black_swan_risk,
                    'last_updated': state.last_updated
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating volatility report: {e}")
            return {'error': str(e)} 

    async def _run_volatility_analysis(self):
        """Run enhanced volatility explosion analysis - REAL DATA ONLY"""
        try:
            # CRITICAL: NO HARD-CODED SYMBOLS - GET FROM DYNAMIC SOURCES
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                # Get active volatile symbols from database
                result = await session.execute("""
                    SELECT symbol, 
                           AVG(ABS((high_price - low_price) / close_price)) as volatility
                    FROM crypto_market_data 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    AND close_price > 0
                    GROUP BY symbol
                    HAVING COUNT(*) >= 100  -- Minimum data points
                    ORDER BY volatility DESC
                    LIMIT 5
                """)
                
                symbol_rows = result.fetchall()
                if not symbol_rows:
                    logger.warning("No volatile symbols found in database")
                    return
                
                dynamic_symbols = [row.symbol for row in symbol_rows]
            
            logger.info(f"Running volatility analysis with real symbols: {dynamic_symbols}")
            
            for symbol in dynamic_symbols:
                try:
                    # Get real volatility data
                    volatility_data = await self._calculate_real_volatility(symbol)
                    if not volatility_data:
                        continue
                    
                    # Check for volatility explosion
                    if await self._detect_volatility_explosion(symbol, volatility_data):
                        signal = await self._generate_volatility_signal(symbol, volatility_data)
                        if signal:
                            logger.info(f"Volatility explosion detected for {symbol}: {signal.action}")
                            
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Enhanced volatility analysis error: {e}")

    async def _calculate_real_volatility(self, symbol: str) -> Optional[Dict]:
        """Calculate real volatility from market data"""
        try:
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                # Get recent price data for volatility calculation
                result = await session.execute("""
                    SELECT close_price, high_price, low_price, timestamp
                    FROM crypto_market_data 
                    WHERE symbol = %s 
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                    ORDER BY timestamp DESC
                    LIMIT 60
                """, (symbol,))
                
                rows = result.fetchall()
                if len(rows) < 20:
                    return None
                
                # Calculate real volatility metrics
                prices = [float(row.close_price) for row in rows]
                highs = [float(row.high_price) for row in rows]
                lows = [float(row.low_price) for row in rows]
                
                # True Range Volatility
                true_ranges = []
                for i in range(1, len(rows)):
                    tr = max(
                        highs[i] - lows[i],
                        abs(highs[i] - prices[i-1]),
                        abs(lows[i] - prices[i-1])
                    )
                    true_ranges.append(tr / prices[i])
                
                avg_true_range = sum(true_ranges) / len(true_ranges)
                current_volatility = true_ranges[-1] if true_ranges else 0
                
                return {
                    'symbol': symbol,
                    'current_volatility': current_volatility,
                    'avg_volatility': avg_true_range,
                    'volatility_ratio': current_volatility / avg_true_range if avg_true_range > 0 else 1,
                    'current_price': prices[0],
                    'price_data_points': len(prices)
                }
                
        except Exception as e:
            logger.error(f"Error calculating real volatility for {symbol}: {e}")
            return None 
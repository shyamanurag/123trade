# strategies/crypto_regime_adaptive_controller.py
"""
Crypto Regime Adaptive Controller Strategy
Adapts to market regimes: Bull, Bear, Sideways, Alt Season
"""

import logging
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    BULL_MARKET = "bull"
    BEAR_MARKET = "bear" 
    SIDEWAYS = "sideways"
    ALT_SEASON = "alt_season"
    UNCERTAINTY = "uncertainty"

@dataclass
class RegimeState:
    """Market regime state"""
    current_regime: MarketRegime
    confidence: float
    btc_dominance: float
    fear_greed_index: float
    volatility_regime: str
    trend_strength: float
    last_updated: datetime

class CryptoRegimeAdaptiveController:
    """Adaptive controller that adjusts strategy based on market regime"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Regime parameters
        self.btc_dominance_threshold = config.get('btc_dominance_threshold', 45)
        self.fear_greed_threshold = config.get('fear_greed_threshold', 50)
        self.volatility_threshold = config.get('volatility_threshold', 0.05)
        
        # Regime tracking
        self.current_regime_state = None
        self.regime_history = deque(maxlen=100)
        self.price_data = {}
        
        # Strategy adjustments per regime
        self.regime_adjustments = {
            MarketRegime.BULL_MARKET: {
                'risk_multiplier': 1.3,
                'position_size_multiplier': 1.2,
                'stop_loss_multiplier': 1.1,
                'strategies_emphasis': ['momentum', 'breakout']
            },
            MarketRegime.BEAR_MARKET: {
                'risk_multiplier': 0.7,
                'position_size_multiplier': 0.8,
                'stop_loss_multiplier': 0.9,
                'strategies_emphasis': ['mean_reversion', 'volatility']
            },
            MarketRegime.SIDEWAYS: {
                'risk_multiplier': 0.8,
                'position_size_multiplier': 0.9,
                'stop_loss_multiplier': 1.0,
                'strategies_emphasis': ['mean_reversion', 'volume']
            },
            MarketRegime.ALT_SEASON: {
                'risk_multiplier': 1.5,
                'position_size_multiplier': 1.3,
                'stop_loss_multiplier': 1.2,
                'strategies_emphasis': ['momentum', 'news']
            }
        }
        
        logger.info("Crypto Regime Adaptive Controller initialized")

    async def start(self):
        """Start the regime controller"""
        logger.info("🎯 Starting Crypto Regime Adaptive Controller...")
        
        asyncio.create_task(self._monitor_market_regime())
        asyncio.create_task(self._update_regime_state())
        
        logger.info("✅ Crypto Regime Adaptive Controller started")

    async def get_regime_adjustments(self) -> Dict:
        """Get current regime-based strategy adjustments"""
        try:
            if not self.current_regime_state:
                return self._get_default_adjustments()
            
            base_adjustments = self.regime_adjustments.get(
                self.current_regime_state.current_regime,
                self._get_default_adjustments()
            )
            
            # Apply confidence weighting
            confidence = self.current_regime_state.confidence
            
            adjusted = {}
            for key, value in base_adjustments.items():
                if isinstance(value, (int, float)) and key.endswith('_multiplier'):
                    # Blend with neutral (1.0) based on confidence
                    adjusted[key] = 1.0 + (value - 1.0) * confidence
                else:
                    adjusted[key] = value
            
            adjusted['regime'] = self.current_regime_state.current_regime.value
            adjusted['confidence'] = confidence
            
            return adjusted
            
        except Exception as e:
            logger.error(f"Error getting regime adjustments: {e}")
            return self._get_default_adjustments()

    def _get_default_adjustments(self) -> Dict:
        """Get default adjustments for uncertain regime"""
        return {
            'risk_multiplier': 1.0,
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'strategies_emphasis': ['momentum', 'volume'],
            'regime': 'uncertainty',
            'confidence': 0.5
        }

    async def _monitor_market_regime(self):
        """Monitor and classify market regime"""
        while True:
            try:
                # Update regime classification
                regime = await self._classify_market_regime()
                
                if regime != (self.current_regime_state.current_regime if self.current_regime_state else None):
                    await self._on_regime_change(regime)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring market regime: {e}")
                await asyncio.sleep(600)

    async def _classify_market_regime(self) -> MarketRegime:
        """Classify current market regime"""
        try:
            # Get market indicators
            btc_dominance = await self._get_btc_dominance()
            fear_greed = await self._get_fear_greed_index()
            market_trend = await self._analyze_market_trend()
            volatility = await self._calculate_market_volatility()
            
            # Classification logic
            if market_trend > 0.15 and fear_greed > 70:
                return MarketRegime.BULL_MARKET
            elif market_trend < -0.15 and fear_greed < 30:
                return MarketRegime.BEAR_MARKET
            elif btc_dominance < self.btc_dominance_threshold and market_trend > 0.05:
                return MarketRegime.ALT_SEASON
            elif abs(market_trend) < 0.05 and volatility < self.volatility_threshold:
                return MarketRegime.SIDEWAYS
            else:
                return MarketRegime.UNCERTAINTY
                
        except Exception as e:
            logger.error(f"Error classifying market regime: {e}")
            return MarketRegime.UNCERTAINTY

    async def _get_btc_dominance(self) -> float:
        """Get Bitcoin dominance percentage - REAL DATA ONLY"""
        try:
            # Get real BTC dominance from database or API
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT (btc_market_cap / total_market_cap) * 100 as btc_dominance
                    FROM market_cap_data 
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                
                row = result.fetchone()
                if row and row.btc_dominance:
                    return float(row.btc_dominance)
                else:
                    raise RuntimeError("No real BTC dominance data available")
                    
        except Exception as e:
            logger.error(f"Error getting BTC dominance: {e}")
            raise RuntimeError(f"Failed to get real BTC dominance data: {e}")

    async def _get_fear_greed_index(self) -> float:
        """Get Fear & Greed Index - REAL DATA ONLY"""
        try:
            # Get real Fear & Greed Index from API or database
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT fear_greed_value
                    FROM market_sentiment_data 
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                
                row = result.fetchone()
                if row and row.fear_greed_value:
                    return float(row.fear_greed_value)
                else:
                    raise RuntimeError("No real Fear & Greed Index data available")
                    
        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {e}")
            raise RuntimeError(f"Failed to get real Fear & Greed Index data: {e}")

    async def _analyze_market_trend(self) -> float:
        """Analyze overall market trend - REAL DATA ONLY"""
        try:
            # Get real market trend from database
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT AVG((close_price - open_price) / open_price) as trend
                    FROM crypto_market_data 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    AND close_price > 0 AND open_price > 0
                """)
                
                row = result.fetchone()
                if row and row.trend is not None:
                    return float(row.trend)
                else:
                    raise RuntimeError("No real market trend data available")
                    
        except Exception as e:
            logger.error(f"Error analyzing market trend: {e}")
            raise RuntimeError(f"Failed to get real market trend data: {e}")

    async def _calculate_market_volatility(self) -> float:
        """Calculate market volatility - REAL DATA ONLY"""
        try:
            # Get real market volatility from database
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT AVG(ABS((high_price - low_price) / close_price)) as volatility
                    FROM crypto_market_data 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    AND close_price > 0
                """)
                
                row = result.fetchone()
                if row and row.volatility is not None:
                    return float(row.volatility)
                else:
                    raise RuntimeError("No real market volatility data available")
                    
        except Exception as e:
            logger.error(f"Error calculating market volatility: {e}")
            raise RuntimeError(f"Failed to get real market volatility data: {e}")

    async def _update_regime_state(self):
        """Update current regime state"""
        while True:
            try:
                regime = await self._classify_market_regime()
                btc_dominance = await self._get_btc_dominance()
                fear_greed = await self._get_fear_greed_index()
                volatility = await self._calculate_market_volatility()
                trend = await self._analyze_market_trend()
                
                # Calculate confidence
                confidence = self._calculate_regime_confidence(regime, btc_dominance, fear_greed, trend, volatility)
                
                # Determine volatility regime
                if volatility > 0.10:
                    vol_regime = "high"
                elif volatility > 0.05:
                    vol_regime = "medium"
                else:
                    vol_regime = "low"
                
                self.current_regime_state = RegimeState(
                    current_regime=regime,
                    confidence=confidence,
                    btc_dominance=btc_dominance,
                    fear_greed_index=fear_greed,
                    volatility_regime=vol_regime,
                    trend_strength=abs(trend),
                    last_updated=datetime.now()
                )
                
                self.regime_history.append(self.current_regime_state)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating regime state: {e}")
                await asyncio.sleep(600)

    def _calculate_regime_confidence(self, regime: MarketRegime, btc_dom: float, 
                                   fear_greed: float, trend: float, volatility: float) -> float:
        """Calculate confidence in regime classification"""
        try:
            confidence_factors = []
            
            # Trend strength factor
            trend_confidence = min(1.0, abs(trend) / 0.2)
            confidence_factors.append(trend_confidence)
            
            # Fear & Greed extremes
            if regime == MarketRegime.BULL_MARKET and fear_greed > 70:
                confidence_factors.append(0.8)
            elif regime == MarketRegime.BEAR_MARKET and fear_greed < 30:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.5)
            
            # BTC dominance for alt season
            if regime == MarketRegime.ALT_SEASON and btc_dom < 40:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
            
            # Volatility consistency
            if regime == MarketRegime.SIDEWAYS and volatility < 0.03:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            logger.error(f"Error calculating regime confidence: {e}")
            return 0.5

    async def _on_regime_change(self, new_regime: MarketRegime):
        """Handle regime change event"""
        try:
            old_regime = self.current_regime_state.current_regime if self.current_regime_state else None
            
            logger.info(f"🎯 REGIME CHANGE: {old_regime} → {new_regime.value}")
            
            # Get new adjustments
            new_adjustments = self.regime_adjustments.get(new_regime, self._get_default_adjustments())
            
            logger.info(f"📊 New Strategy Adjustments:")
            logger.info(f"   Risk Multiplier: {new_adjustments['risk_multiplier']:.2f}")
            logger.info(f"   Position Size: {new_adjustments['position_size_multiplier']:.2f}")
            logger.info(f"   Emphasis: {new_adjustments['strategies_emphasis']}")
            
        except Exception as e:
            logger.error(f"Error handling regime change: {e}")

    def get_current_regime(self) -> Dict:
        """Get current regime information"""
        try:
            if not self.current_regime_state:
                return {'regime': 'unknown', 'confidence': 0.0}
            
            return {
                'regime': self.current_regime_state.current_regime.value,
                'confidence': self.current_regime_state.confidence,
                'btc_dominance': self.current_regime_state.btc_dominance,
                'fear_greed_index': self.current_regime_state.fear_greed_index,
                'volatility_regime': self.current_regime_state.volatility_regime,
                'trend_strength': self.current_regime_state.trend_strength,
                'last_updated': self.current_regime_state.last_updated
            }
            
        except Exception as e:
            logger.error(f"Error getting current regime: {e}")
            return {'regime': 'error', 'confidence': 0.0}

    def get_performance_metrics(self) -> Dict:
        """Get regime controller performance metrics"""
        try:
            if not self.regime_history:
                return {'regime_changes': 0, 'average_confidence': 0.0}
            
            # Count regime changes
            regime_changes = 0
            prev_regime = None
            
            for state in self.regime_history:
                if prev_regime and state.current_regime != prev_regime:
                    regime_changes += 1
                prev_regime = state.current_regime
            
            # Calculate average confidence
            avg_confidence = sum(state.confidence for state in self.regime_history) / len(self.regime_history)
            
            # Regime distribution
            regime_counts = {}
            for state in self.regime_history:
                regime = state.current_regime.value
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            return {
                'regime_changes': regime_changes,
                'average_confidence': avg_confidence,
                'current_regime': self.current_regime_state.current_regime.value if self.current_regime_state else 'unknown',
                'current_confidence': self.current_regime_state.confidence if self.current_regime_state else 0.0,
                'regime_distribution': regime_counts,
                'states_tracked': len(self.regime_history)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def simulate_regime_change(self, target_regime: str):
        """Simulate regime change for testing"""
        try:
            regime_map = {
                'bull': MarketRegime.BULL_MARKET,
                'bear': MarketRegime.BEAR_MARKET,
                'sideways': MarketRegime.SIDEWAYS,
                'alt_season': MarketRegime.ALT_SEASON,
                'uncertainty': MarketRegime.UNCERTAINTY
            }
            
            if target_regime in regime_map:
                new_regime = regime_map[target_regime]
                await self._on_regime_change(new_regime)
                
                # Update state
                self.current_regime_state = RegimeState(
                    current_regime=new_regime,
                    confidence=0.8,
                    btc_dominance=45.0,
                    fear_greed_index=50.0,
                    volatility_regime="medium",
                    trend_strength=0.1,
                    last_updated=datetime.now()
                )
                
                logger.info(f"🎯 Simulated regime change to {target_regime}")
            
        except Exception as e:
            logger.error(f"Error simulating regime change: {e}") 
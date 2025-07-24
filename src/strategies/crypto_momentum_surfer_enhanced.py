# strategies/crypto_momentum_surfer_enhanced.py
"""
Enhanced Crypto Momentum Surfer Strategy with Edge Intelligence
Integrates on-chain data, AI predictions, and smart money tracking
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class EnhancedMomentumState:
    """Enhanced momentum state with edge intelligence"""
    symbol: str
    trend_direction: Optional[str] = None
    trend_strength: float = 0.0
    
    # Edge intelligence additions
    smart_money_score: float = 0.0
    ai_prediction_confidence: float = 0.0
    social_momentum: float = 0.0
    liquidation_levels: List[float] = None
    whale_activity: str = 'NEUTRAL'  # ACCUMULATING, DISTRIBUTING, NEUTRAL

class CryptoSignal:
    """Crypto trading signal"""
    def __init__(self, symbol: str, side: str, entry_price: float, stop_loss: float, 
                 take_profit: float, quality_score: float = 0.0):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.quality_score = quality_score
        self.quantum_score = 0.0
        self.strategy_name = ""
        self.intelligence_score = 0.0
        self.position_size = 0.0
        self.timestamp = datetime.now()

class EnhancedCryptoMomentumSurfer:
    """
    Enhanced Momentum Strategy with Edge Intelligence
    Now includes:
    - Smart money tracking
    - AI-powered predictions
    - Social sentiment analysis
    - Liquidation level awareness
    """

    def __init__(self, config: Dict):
        # Original configuration
        self.allocation = config.get('allocation', 0.25)
        self.volume_surge_multiplier = config.get('volume_surge_multiplier', 2.5)
        self.adx_threshold = config.get('adx_threshold', 35)
        self.profit_target_percent = config.get('profit_target_percent', 0.04)
        self.stop_loss_percent = config.get('stop_loss_percent', 0.02)
        
        # Edge intelligence components
        self.onchain_intel = config.get('onchain_intel')
        self.ai_predictor = config.get('ai_predictor')
        self.social_analyzer = config.get('social_analyzer')
        
        # Enhanced parameters with edge intelligence
        self.smart_money_weight = config.get('smart_money_weight', 0.3)
        self.ai_confidence_threshold = config.get('ai_confidence_threshold', 0.7)
        self.liquidation_hunt_enabled = config.get('liquidation_hunt_enabled', True)
        
        # Crypto pairs to trade
        self.crypto_pairs = config.get('crypto_pairs', [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'
        ])
        
        # Enhanced state tracking
        self.momentum_states = {}
        self.smart_money_cache = {}
        self.ai_prediction_cache = {}
        self.is_enabled = True
        
        logger.info("Enhanced Crypto Momentum Surfer initialized with edge intelligence")

    async def start(self):
        """Start the momentum strategy"""
        self.is_enabled = True
        logger.info("Enhanced Crypto Momentum Surfer started")

    async def stop(self):
        """Stop the momentum strategy"""
        self.is_enabled = False
        logger.info("Enhanced Crypto Momentum Surfer stopped")

    async def generate_signals_with_intelligence(self, intelligence: Dict) -> List[CryptoSignal]:
        """Generate enhanced momentum signals with edge intelligence"""
        signals = []

        try:
            if not self.is_enabled:
                return signals

            # Process each crypto pair with enhanced analysis
            for symbol in self.crypto_pairs:
                try:
                    # Get market data (simulated for now)
                    market_data = await self._get_market_data(symbol)
                    if not market_data:
                        continue

                    # Get enhanced state with edge intelligence
                    state = await self._get_enhanced_momentum_state(symbol, market_data, intelligence)
                    
                    # Skip if no momentum
                    if not self._check_enhanced_momentum_conditions(state):
                        continue

                    # Generate signals with edge intelligence
                    edge_signals = await self._generate_edge_enhanced_signals(
                        symbol, market_data, state, intelligence
                    )
                    
                    signals.extend(edge_signals)
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error generating momentum signals: {e}")

        return signals

    async def _get_market_data(self, symbol: str) -> Dict:
        """Get market data for symbol (placeholder)"""
        # This would connect to real market data
        return {
            'price': 50000.0,  # Current price
            'volume': 1000000.0,  # Volume
            'change_24h': 0.025,  # 2.5% change
            'volatility': 0.05,   # 5% volatility
        }

    async def _get_enhanced_momentum_state(self, symbol: str, market_data: Dict, intelligence: Dict) -> EnhancedMomentumState:
        """Get enhanced momentum state with edge intelligence"""
        state = EnhancedMomentumState(symbol=symbol)
        
        try:
            # Traditional momentum analysis
            price_change = market_data.get('change_24h', 0)
            volume_ratio = market_data.get('volume', 0) / 1000000  # Normalized
            
            # Calculate trend direction and strength
            if abs(price_change) > 0.02:  # 2% threshold
                state.trend_direction = 'UP' if price_change > 0 else 'DOWN'
                state.trend_strength = abs(price_change) * volume_ratio
            
            # Add edge intelligence
            smart_money_data = intelligence.get('smart_money', {})
            if symbol in smart_money_data:
                state.smart_money_score = smart_money_data[symbol].get('score', 0)
                state.whale_activity = smart_money_data[symbol].get('activity', 'NEUTRAL')
            
            # AI predictions
            ai_data = intelligence.get('ai_predictions', {})
            if symbol in ai_data:
                state.ai_prediction_confidence = ai_data[symbol].get('confidence', 0)
            
            # Social momentum
            social_data = intelligence.get('social_signals', {})
            if symbol in social_data:
                state.social_momentum = social_data[symbol].get('momentum', 0)
            
            # Liquidation levels
            if self.liquidation_hunt_enabled and symbol in intelligence.get('liquidation_levels', {}):
                state.liquidation_levels = intelligence['liquidation_levels'][symbol]
            
        except Exception as e:
            logger.error(f"Error getting enhanced state for {symbol}: {e}")
        
        return state

    def _check_enhanced_momentum_conditions(self, state: EnhancedMomentumState) -> bool:
        """Check if enhanced momentum conditions are met"""
        try:
            # Basic momentum check
            if not state.trend_direction or state.trend_strength < 0.5:
                return False
            
            # Edge intelligence enhancements
            edge_score = 0
            
            # Smart money confirmation
            if state.smart_money_score > 0.6:
                edge_score += 1
            
            # AI confidence
            if state.ai_prediction_confidence > self.ai_confidence_threshold:
                edge_score += 1
            
            # Social momentum
            if state.social_momentum > 0.7:
                edge_score += 1
            
            # Require at least one edge confirmation
            return edge_score >= 1
            
        except Exception as e:
            logger.error(f"Error checking momentum conditions: {e}")
            return False

    async def _generate_edge_enhanced_signals(self, symbol: str, market_data: Dict, 
                                           state: EnhancedMomentumState, intelligence: Dict) -> List[CryptoSignal]:
        """Generate signals enhanced with edge intelligence"""
        signals = []
        
        try:
            current_price = market_data.get('price', 0)
            if current_price <= 0:
                return signals
            
            # Determine signal direction
            side = 'BUY' if state.trend_direction == 'UP' else 'SELL'
            
            # Calculate entry, stop loss, and take profit
            if side == 'BUY':
                entry_price = current_price
                stop_loss = current_price * (1 - self.stop_loss_percent)
                take_profit = current_price * (1 + self.profit_target_percent)
            else:
                entry_price = current_price
                stop_loss = current_price * (1 + self.stop_loss_percent)
                take_profit = current_price * (1 - self.profit_target_percent)
            
            # Calculate quality score with edge intelligence
            quality_score = self._calculate_enhanced_quality_score(state, intelligence)
            
            # Create enhanced signal
            signal = CryptoSignal(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                quality_score=quality_score
            )
            
            # Add edge intelligence metadata
            signal.intelligence_score = self._calculate_intelligence_score(state)
            
            signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error generating enhanced signals for {symbol}: {e}")
        
        return signals

    def _calculate_enhanced_quality_score(self, state: EnhancedMomentumState, intelligence: Dict) -> float:
        """Calculate quality score enhanced with edge intelligence"""
        try:
            base_score = state.trend_strength * 5.0  # Base momentum score
            
            # Edge intelligence multipliers
            edge_multiplier = 1.0
            
            # Smart money boost
            if state.smart_money_score > 0.6:
                edge_multiplier *= (1 + state.smart_money_score * self.smart_money_weight)
            
            # AI confidence boost
            if state.ai_prediction_confidence > self.ai_confidence_threshold:
                edge_multiplier *= (1 + state.ai_prediction_confidence * 0.5)
            
            # Social momentum boost
            if state.social_momentum > 0.7:
                edge_multiplier *= (1 + state.social_momentum * 0.3)
            
            # Whale activity boost
            if state.whale_activity == 'ACCUMULATING':
                edge_multiplier *= 1.2
            elif state.whale_activity == 'DISTRIBUTING':
                edge_multiplier *= 0.8
            
            return min(base_score * edge_multiplier, 10.0)  # Cap at 10
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 1.0

    def _calculate_intelligence_score(self, state: EnhancedMomentumState) -> float:
        """Calculate intelligence score for edge components"""
        try:
            score = 1.0
            
            # Smart money factor
            if state.smart_money_score > 0.6:
                score *= (1 + state.smart_money_score * 0.5)
            
            # AI confidence factor
            if state.ai_prediction_confidence > 0.7:
                score *= (1 + state.ai_prediction_confidence * 0.4)
            
            # Social momentum factor
            if state.social_momentum > 0.7:
                score *= (1 + state.social_momentum * 0.3)
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating intelligence score: {e}")
            return 1.0

    def get_performance_metrics(self) -> Dict:
        """Get strategy performance metrics"""
        return {
            'trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        } 
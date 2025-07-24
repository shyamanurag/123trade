# strategies/crypto_confluence_amplifier_enhanced.py
"""
Enhanced Crypto Confluence Amplifier Strategy
Combines signals from multiple strategies and edge intelligence components
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
class ConfluenceSignal:
    """Represents a confluence signal"""
    symbol: str
    strategy_source: str
    signal_type: str  # BUY, SELL, HOLD
    strength: float  # 0-1
    confidence: float  # 0-1
    timestamp: datetime
    additional_data: Dict

class EnhancedCryptoConfluenceAmplifier:
    """
    Enhanced confluence amplifier for crypto trading with edge intelligence
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Confluence parameters
        self.min_confluence_signals = config.get('min_confluence_signals', 2)
        self.confluence_window_seconds = config.get('confluence_window_seconds', 120)
        self.confluence_threshold = config.get('confluence_threshold', 0.70)
        
        # Signal storage
        self.signal_buffer = deque(maxlen=1000)
        self.confluence_history = deque(maxlen=500)
        
        # Strategy weights
        self.strategy_weights = {
            'momentum_surfer': 0.25,
            'news_impact': 0.20,
            'volatility_explosion': 0.15,
            'volume_profile': 0.15,
            'regime_adaptive': 0.10,
            'smart_money': 0.30,  # Higher weight for smart money
            'ai_predictor': 0.25,
            'liquidation_hunt': 0.20,
            'social_sentiment': 0.15
        }
        
        # Edge intelligence integration
        self.smart_money_boost = config.get('smart_money_confirmation_boost', 1.5)
        self.ai_confidence_requirement = config.get('ai_confluence_threshold', 0.75)
        self.social_momentum_boost = config.get('social_momentum_boost', 1.3)
        
        # Performance tracking
        self.confluence_success_rate = deque(maxlen=100)
        self.signals_generated = 0
        self.successful_confluences = 0
        
        logger.info("Enhanced Crypto Confluence Amplifier initialized")

    async def start(self):
        """Start the confluence amplifier"""
        logger.info("🔗 Starting Enhanced Crypto Confluence Amplifier...")
        
        # Start signal processing
        asyncio.create_task(self._process_confluence_signals())
        asyncio.create_task(self._cleanup_old_signals())
        
        logger.info("✅ Enhanced Crypto Confluence Amplifier started")

    async def add_signal(self, signal: ConfluenceSignal):
        """Add a signal to the confluence buffer"""
        try:
            # Add timestamp if not present
            if not signal.timestamp:
                signal.timestamp = datetime.now()
            
            # Add to buffer
            self.signal_buffer.append(signal)
            
            # Check for immediate confluence
            await self._check_confluence(signal.symbol)
            
        except Exception as e:
            logger.error(f"Error adding signal: {e}")

    async def get_confluence_signals(self) -> List[Dict]:
        """Get current confluence signals for all symbols"""
        try:
            confluence_signals = []
            
            # Get unique symbols from recent signals
            recent_signals = [s for s in self.signal_buffer if s.timestamp > datetime.now() - timedelta(seconds=self.confluence_window_seconds)]
            symbols = set(s.symbol for s in recent_signals)
            
            for symbol in symbols:
                confluence = await self._calculate_confluence(symbol)
                if confluence and confluence['strength'] >= self.confluence_threshold:
                    confluence_signals.append(confluence)
            
            return confluence_signals
            
        except Exception as e:
            logger.error(f"Error getting confluence signals: {e}")
            return []

    async def _process_confluence_signals(self):
        """Main confluence processing loop"""
        while True:
            try:
                # Process confluence every 30 seconds
                await asyncio.sleep(30)
                
                # Get recent signals
                cutoff_time = datetime.now() - timedelta(seconds=self.confluence_window_seconds)
                recent_signals = [s for s in self.signal_buffer if s.timestamp > cutoff_time]
                
                if len(recent_signals) < self.min_confluence_signals:
                    continue
                
                # Group by symbol
                symbol_signals = {}
                for signal in recent_signals:
                    if signal.symbol not in symbol_signals:
                        symbol_signals[signal.symbol] = []
                    symbol_signals[signal.symbol].append(signal)
                
                # Check confluence for each symbol
                for symbol, signals in symbol_signals.items():
                    if len(signals) >= self.min_confluence_signals:
                        confluence = await self._calculate_confluence_from_signals(symbol, signals)
                        if confluence and confluence['strength'] >= self.confluence_threshold:
                            await self._emit_confluence_signal(confluence)
                
            except Exception as e:
                logger.error(f"Error in confluence processing: {e}")
                await asyncio.sleep(60)

    async def _check_confluence(self, symbol: str):
        """Check for immediate confluence on a symbol"""
        try:
            # Get recent signals for this symbol
            cutoff_time = datetime.now() - timedelta(seconds=self.confluence_window_seconds)
            symbol_signals = [
                s for s in self.signal_buffer 
                if s.symbol == symbol and s.timestamp > cutoff_time
            ]
            
            if len(symbol_signals) >= self.min_confluence_signals:
                confluence = await self._calculate_confluence_from_signals(symbol, symbol_signals)
                if confluence and confluence['strength'] >= self.confluence_threshold:
                    await self._emit_confluence_signal(confluence)
            
        except Exception as e:
            logger.error(f"Error checking confluence for {symbol}: {e}")

    async def _calculate_confluence(self, symbol: str) -> Optional[Dict]:
        """Calculate confluence for a symbol"""
        try:
            # Get recent signals for this symbol
            cutoff_time = datetime.now() - timedelta(seconds=self.confluence_window_seconds)
            symbol_signals = [
                s for s in self.signal_buffer 
                if s.symbol == symbol and s.timestamp > cutoff_time
            ]
            
            if len(symbol_signals) < self.min_confluence_signals:
                return None
            
            return await self._calculate_confluence_from_signals(symbol, symbol_signals)
            
        except Exception as e:
            logger.error(f"Error calculating confluence for {symbol}: {e}")
            return None

    async def _calculate_confluence_from_signals(self, symbol: str, signals: List[ConfluenceSignal]) -> Optional[Dict]:
        """Calculate confluence from a list of signals"""
        try:
            if len(signals) < self.min_confluence_signals:
                return None
            
            # Group signals by direction
            buy_signals = [s for s in signals if s.signal_type == 'BUY']
            sell_signals = [s for s in signals if s.signal_type == 'SELL']
            
            # Determine dominant direction
            if len(buy_signals) > len(sell_signals):
                direction = 'BUY'
                relevant_signals = buy_signals
            elif len(sell_signals) > len(buy_signals):
                direction = 'SELL'
                relevant_signals = sell_signals
            else:
                # Equal signals, no confluence
                return None
            
            if len(relevant_signals) < self.min_confluence_signals:
                return None
            
            # Calculate weighted confluence strength
            total_weight = 0
            weighted_strength = 0
            weighted_confidence = 0
            
            edge_intelligence_boost = 1.0
            
            for signal in relevant_signals:
                weight = self.strategy_weights.get(signal.strategy_source, 0.1)
                
                # Apply edge intelligence boosts
                if signal.strategy_source == 'smart_money':
                    weight *= self.smart_money_boost
                    edge_intelligence_boost *= 1.2
                elif signal.strategy_source == 'ai_predictor' and signal.confidence > self.ai_confidence_requirement:
                    weight *= 1.4
                    edge_intelligence_boost *= 1.15
                elif signal.strategy_source == 'social_sentiment' and signal.strength > 0.8:
                    weight *= self.social_momentum_boost
                    edge_intelligence_boost *= 1.1
                
                total_weight += weight
                weighted_strength += signal.strength * weight
                weighted_confidence += signal.confidence * weight
            
            if total_weight == 0:
                return None
            
            # Calculate final metrics
            final_strength = (weighted_strength / total_weight) * edge_intelligence_boost
            final_confidence = weighted_confidence / total_weight
            
            # Normalize strength to max 1.0
            final_strength = min(1.0, final_strength)
            
            # Calculate confluence score
            strategy_diversity = len(set(s.strategy_source for s in relevant_signals))
            confluence_score = final_strength * (strategy_diversity / len(self.strategy_weights))
            
            return {
                'symbol': symbol,
                'direction': direction,
                'strength': final_strength,
                'confidence': final_confidence,
                'confluence_score': confluence_score,
                'signal_count': len(relevant_signals),
                'strategy_diversity': strategy_diversity,
                'edge_intelligence_boost': edge_intelligence_boost,
                'contributing_strategies': [s.strategy_source for s in relevant_signals],
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error calculating confluence: {e}")
            return None

    async def _emit_confluence_signal(self, confluence: Dict):
        """Emit a confluence signal"""
        try:
            self.signals_generated += 1
            
            # Add to history
            self.confluence_history.append(confluence)
            
            logger.info(f"🔗 CONFLUENCE SIGNAL: {confluence['symbol']} {confluence['direction']} "
                       f"Strength: {confluence['strength']:.3f} "
                       f"Strategies: {confluence['signal_count']} "
                       f"Boost: {confluence['edge_intelligence_boost']:.2f}x")
            
            # Could emit to other systems here
            
        except Exception as e:
            logger.error(f"Error emitting confluence signal: {e}")

    async def _cleanup_old_signals(self):
        """Clean up old signals from buffer"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes
                
                cutoff_time = datetime.now() - timedelta(seconds=self.confluence_window_seconds * 2)
                
                # Remove old signals
                old_count = len(self.signal_buffer)
                self.signal_buffer = deque([
                    s for s in self.signal_buffer if s.timestamp > cutoff_time
                ], maxlen=1000)
                
                removed = old_count - len(self.signal_buffer)
                if removed > 0:
                    logger.debug(f"Cleaned up {removed} old signals")
                
            except Exception as e:
                logger.error(f"Error cleaning up signals: {e}")
                await asyncio.sleep(300)

    def get_performance_metrics(self) -> Dict:
        """Get confluence amplifier performance metrics"""
        try:
            if len(self.confluence_history) == 0:
                return {
                    'signals_generated': 0,
                    'average_strength': 0,
                    'average_confidence': 0,
                    'strategy_diversity_avg': 0
                }
            
            recent_confluences = [
                c for c in self.confluence_history 
                if c['timestamp'] > datetime.now() - timedelta(hours=24)
            ]
            
            if not recent_confluences:
                return {
                    'signals_generated': self.signals_generated,
                    'average_strength': 0,
                    'average_confidence': 0,
                    'strategy_diversity_avg': 0
                }
            
            return {
                'signals_generated': self.signals_generated,
                'signals_24h': len(recent_confluences),
                'average_strength': np.mean([c['strength'] for c in recent_confluences]),
                'average_confidence': np.mean([c['confidence'] for c in recent_confluences]),
                'strategy_diversity_avg': np.mean([c['strategy_diversity'] for c in recent_confluences]),
                'edge_boost_avg': np.mean([c['edge_intelligence_boost'] for c in recent_confluences])
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def update_strategy_weights(self, performance_data: Dict):
        """Update strategy weights based on performance"""
        try:
            logger.info("📊 Updating confluence strategy weights based on performance...")
            
            for strategy, performance in performance_data.items():
                if strategy in self.strategy_weights:
                    # Adjust weight based on win rate and profitability
                    win_rate = performance.get('win_rate', 0.5)
                    profit_factor = performance.get('profit_factor', 1.0)
                    
                    # Calculate adjustment factor
                    adjustment = (win_rate - 0.5) * 0.5 + (profit_factor - 1.0) * 0.3
                    
                    # Apply gradual adjustment
                    self.strategy_weights[strategy] *= (1 + adjustment * 0.1)
                    
                    # Keep weights reasonable
                    self.strategy_weights[strategy] = max(0.05, min(0.5, self.strategy_weights[strategy]))
            
            # Normalize weights
            total_weight = sum(self.strategy_weights.values())
            for strategy in self.strategy_weights:
                self.strategy_weights[strategy] /= total_weight
            
            logger.info("✅ Strategy weights updated")
            
        except Exception as e:
            logger.error(f"Error updating strategy weights: {e}")

    def get_confluence_history(self, hours: int = 24) -> List[Dict]:
        """Get confluence history for the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [
                c for c in self.confluence_history 
                if c['timestamp'] > cutoff_time
            ]
        except Exception as e:
            logger.error(f"Error getting confluence history: {e}")
            return []

    async def simulate_confluence_signal(self, symbol: str = "BTCUSDT") -> Dict:
        """Simulate a confluence signal for testing"""
        try:
            # Generate real confluence signal
            market_data = await self.get_latest_market_data(symbol)
            if not market_data:
                return None
                
            # Get real signals from multiple sources
            real_signals = await self._get_real_signals(symbol, market_data)
            
            if not real_signals:
                logger.warning(f"No real signals available for {symbol}")
                return None
            
            # Calculate confluence from real signals
            confluence = await self._calculate_confluence_from_signals(symbol, real_signals)
            
            if confluence['score'] > self.confluence_threshold:
                return CryptoSignal(
                    symbol=symbol,
                    action=confluence['action'],
                    confidence=confluence['score'],
                    timestamp=datetime.now(),
                    strategy="enhanced_confluence_amplifier",
                    metadata={
                        'confluence_score': confluence['score'],
                        'signal_count': len(real_signals),
                        'data_source': 'real_signals'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating confluence signal for {symbol}: {e}")
            return None

    async def _get_real_signals(self, symbol: str, market_data: Dict) -> List[Dict]:
        """Get real signals from multiple technical indicators"""
        try:
            real_signals = []
            
            # Get real price history for technical analysis
            price_history = await self._get_price_history(symbol)
            if len(price_history) < 20:
                return []
            
            # Generate real technical signals
            current_price = market_data.get('close_price', 0)
            
            # RSI Signal
            rsi = self._calculate_real_rsi(price_history)
            if rsi < 30:
                real_signals.append({'type': 'RSI', 'action': 'BUY', 'strength': 0.8})
            elif rsi > 70:
                real_signals.append({'type': 'RSI', 'action': 'SELL', 'strength': 0.8})
            
            # Moving Average Signal
            sma_20 = sum(price_history[-20:]) / 20
            if current_price > sma_20 * 1.02:
                real_signals.append({'type': 'SMA', 'action': 'BUY', 'strength': 0.6})
            elif current_price < sma_20 * 0.98:
                real_signals.append({'type': 'SMA', 'action': 'SELL', 'strength': 0.6})
            
            # Volume Signal
            volume = market_data.get('volume', 0)
            avg_volume = await self._get_average_volume(symbol)
            if volume > avg_volume * 1.5:
                real_signals.append({'type': 'VOLUME', 'action': 'BUY', 'strength': 0.7})
            
            return real_signals
            
        except Exception as e:
            logger.error(f"Error getting real signals for {symbol}: {e}")
            return []

    async def _get_price_history(self, symbol: str) -> List[float]:
        """Get real price history from database"""
        try:
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT close_price FROM crypto_market_data 
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """, (symbol,))
                
                rows = result.fetchall()
                return [float(row.close_price) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return [] 
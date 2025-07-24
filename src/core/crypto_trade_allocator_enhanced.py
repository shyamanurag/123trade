# core/crypto_trade_allocator_enhanced.py
"""
Enhanced Crypto Trade Allocator
Intelligent position sizing with risk-adjusted allocation and Kelly criterion
"""

import logging
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import math

logger = logging.getLogger(__name__)

@dataclass
class AllocationSignal:
    """Trade allocation signal"""
    symbol: str
    direction: str
    strength: float
    confidence: float
    strategy_source: str
    market_cap_tier: str
    volatility_adjusted_size: float
    kelly_allocation: float
    risk_score: float

@dataclass
class PositionAllocation:
    """Position allocation result"""
    symbol: str
    recommended_quantity: float
    recommended_value: float
    risk_adjusted_size: float
    max_loss_amount: float
    stop_loss_price: float
    take_profit_price: float
    allocation_confidence: float

class EnhancedCryptoTradeAllocator:
    """
    Enhanced trade allocator with intelligent position sizing
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Allocation parameters
        self.base_allocation = config.get('base_allocation_percent', 0.02)  # 2%
        self.max_allocation = config.get('max_allocation_percent', 0.10)  # 10%
        self.min_allocation = config.get('min_allocation_percent', 0.005)  # 0.5%
        
        # Risk parameters
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.01)  # 1%
        self.volatility_lookback_days = config.get('volatility_lookback_days', 30)
        self.correlation_adjustment = config.get('correlation_adjustment', True)
        
        # Market cap tiers
        self.market_cap_multipliers = {
            'large': 1.2,    # BTC, ETH
            'mid': 1.0,      # Top 10-50
            'small': 0.8,    # Top 50-200
            'micro': 0.5     # Below 200
        }
        
        # Strategy confidence multipliers
        self.strategy_multipliers = {
            'confluence_amplifier': 1.3,
            'smart_money': 1.2,
            'ai_predictor': 1.1,
            'momentum_surfer': 1.0,
            'volatility_explosion': 0.9,
            'volume_profile': 0.8,
            'news_impact': 0.7,
            'regime_adaptive': 1.0
        }
        
        # Allocation tracking
        self.allocation_history = deque(maxlen=1000)
        self.performance_tracking = {}
        self.current_allocations = {}
        
        # Performance metrics
        self.allocations_made = 0
        self.total_allocated_value = 0
        self.successful_allocations = 0
        
        logger.info("Enhanced Crypto Trade Allocator initialized")

    async def start(self):
        """Start the trade allocator"""
        logger.info("🎯 Starting Enhanced Crypto Trade Allocator...")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_allocation_performance())
        asyncio.create_task(self._optimize_allocation_parameters())
        
        logger.info("✅ Enhanced Crypto Trade Allocator started")

    async def calculate_allocation(self, signal: AllocationSignal, 
                                 current_portfolio_value: float,
                                 current_price: float) -> PositionAllocation:
        """Calculate optimal position allocation"""
        try:
            # Base allocation calculation
            base_allocation = await self._calculate_base_allocation(signal, current_portfolio_value)
            
            # Risk-adjusted allocation
            risk_adjusted = await self._apply_risk_adjustments(base_allocation, signal, current_price)
            
            # Volatility adjustment
            volatility_adjusted = await self._apply_volatility_adjustment(risk_adjusted, signal.symbol, current_price)
            
            # Correlation adjustment
            correlation_adjusted = await self._apply_correlation_adjustment(volatility_adjusted, signal.symbol, current_portfolio_value)
            
            # Kelly criterion optimization
            kelly_optimized = await self._apply_kelly_criterion(correlation_adjusted, signal)
            
            # Final allocation
            final_allocation = min(kelly_optimized, self.max_allocation * current_portfolio_value)
            final_allocation = max(final_allocation, self.min_allocation * current_portfolio_value)
            
            # Calculate quantity
            recommended_quantity = final_allocation / current_price
            
            # Calculate stop loss and take profit
            stop_loss_price, take_profit_price = await self._calculate_exit_levels(
                signal, current_price, recommended_quantity
            )
            
            # Calculate max loss
            max_loss = abs(current_price - stop_loss_price) * recommended_quantity
            
            allocation = PositionAllocation(
                symbol=signal.symbol,
                recommended_quantity=recommended_quantity,
                recommended_value=final_allocation,
                risk_adjusted_size=final_allocation / current_portfolio_value,
                max_loss_amount=max_loss,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                allocation_confidence=signal.confidence
            )
            
            # Track allocation
            self.allocations_made += 1
            self.total_allocated_value += final_allocation
            self.allocation_history.append({
                'symbol': signal.symbol,
                'allocation': allocation,
                'signal': signal,
                'timestamp': datetime.now()
            })
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error calculating allocation: {e}")
            return self._get_minimal_allocation(signal.symbol, current_portfolio_value, current_price)

    async def _calculate_base_allocation(self, signal: AllocationSignal, portfolio_value: float) -> float:
        """Calculate base allocation amount"""
        try:
            # Start with base allocation
            base_amount = self.base_allocation * portfolio_value
            
            # Adjust for signal strength
            strength_multiplier = 0.5 + (signal.strength * 1.5)  # 0.5 to 2.0
            base_amount *= strength_multiplier
            
            # Adjust for confidence
            confidence_multiplier = 0.7 + (signal.confidence * 0.6)  # 0.7 to 1.3
            base_amount *= confidence_multiplier
            
            # Adjust for strategy source
            strategy_multiplier = self.strategy_multipliers.get(signal.strategy_source, 1.0)
            base_amount *= strategy_multiplier
            
            # Adjust for market cap tier
            market_cap_multiplier = self.market_cap_multipliers.get(signal.market_cap_tier, 1.0)
            base_amount *= market_cap_multiplier
            
            return base_amount
            
        except Exception as e:
            logger.error(f"Error calculating base allocation: {e}")
            return self.min_allocation * portfolio_value

    async def _apply_risk_adjustments(self, base_allocation: float, signal: AllocationSignal, 
                                    current_price: float) -> float:
        """Apply risk-based adjustments"""
        try:
            # Risk score adjustment (lower risk score = higher allocation)
            risk_adjustment = 1.0 - (signal.risk_score * 0.3)  # Max 30% reduction
            adjusted_allocation = base_allocation * risk_adjustment
            
            # Ensure we don't exceed max risk per trade
            max_risk_amount = self.max_risk_per_trade * base_allocation  # Simplified
            if adjusted_allocation > max_risk_amount * 10:  # Assuming 10% risk per position
                adjusted_allocation = max_risk_amount * 10
            
            return adjusted_allocation
            
        except Exception as e:
            logger.error(f"Error applying risk adjustments: {e}")
            return base_allocation * 0.8  # Conservative fallback

    async def _apply_volatility_adjustment(self, allocation: float, symbol: str, 
                                         current_price: float) -> float:
        """Apply volatility-based position sizing"""
        try:
            # Get volatility estimate
            volatility = await self._estimate_volatility(symbol)
            
            # Higher volatility = smaller position
            if volatility > 0.15:  # Very high volatility (>15%)
                volatility_multiplier = 0.6
            elif volatility > 0.10:  # High volatility (10-15%)
                volatility_multiplier = 0.8
            elif volatility > 0.05:  # Medium volatility (5-10%)
                volatility_multiplier = 1.0
            else:  # Low volatility (<5%)
                volatility_multiplier = 1.2
            
            return allocation * volatility_multiplier
            
        except Exception as e:
            logger.error(f"Error applying volatility adjustment: {e}")
            return allocation

    async def _estimate_volatility(self, symbol: str) -> float:
        """Estimate volatility for a symbol"""
        try:
            # Simplified volatility estimation
            # In real implementation, would use price history
            
            volatility_estimates = {
                'BTCUSDT': 0.06,   # 6% daily
                'ETHUSDT': 0.08,   # 8% daily
                'ADAUSDT': 0.12,   # 12% daily
                'DOTUSDT': 0.10,   # 10% daily
                'LINKUSDT': 0.11   # 11% daily
            }
            
            return volatility_estimates.get(symbol, 0.10)  # Default 10%
            
        except Exception as e:
            logger.error(f"Error estimating volatility for {symbol}: {e}")
            return 0.10

    async def _apply_correlation_adjustment(self, allocation: float, symbol: str, 
                                          portfolio_value: float) -> float:
        """Apply correlation-based adjustments"""
        try:
            if not self.correlation_adjustment:
                return allocation
            
            # Get current positions (simplified)
            existing_allocation = self.current_allocations.get(symbol, 0)
            
            # If we already have a large position, reduce new allocation
            existing_ratio = existing_allocation / portfolio_value
            if existing_ratio > 0.05:  # Already 5%+ allocated
                correlation_multiplier = 1.0 - (existing_ratio * 2)  # Reduce allocation
                correlation_multiplier = max(0.3, correlation_multiplier)  # Min 30%
                return allocation * correlation_multiplier
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error applying correlation adjustment: {e}")
            return allocation

    async def _apply_kelly_criterion(self, allocation: float, signal: AllocationSignal) -> float:
        """Apply Kelly criterion for optimal allocation"""
        try:
            # Estimate win probability and win/loss ratio
            win_probability = 0.4 + (signal.confidence * 0.4)  # 40% to 80%
            
            # Estimate average win/loss ratio based on signal strength
            avg_win = 1.0 + (signal.strength * 1.5)  # 1.0 to 2.5
            avg_loss = 1.0  # Normalized
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds, p = win probability, q = loss probability
            b = avg_win / avg_loss
            p = win_probability
            q = 1 - p
            
            kelly_fraction = (b * p - q) / b
            kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25%
            
            # Apply Kelly with safety factor
            safety_factor = 0.5  # Use half Kelly for safety
            kelly_allocation = allocation * (kelly_fraction * safety_factor / self.base_allocation)
            
            return min(kelly_allocation, allocation * 1.5)  # Max 50% increase
            
        except Exception as e:
            logger.error(f"Error applying Kelly criterion: {e}")
            return allocation

    async def _calculate_exit_levels(self, signal: AllocationSignal, current_price: float, 
                                   quantity: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        try:
            # Stop loss based on volatility and risk tolerance
            volatility = await self._estimate_volatility(signal.symbol)
            
            # Stop loss: 1.5x daily volatility or 3% max
            stop_loss_percent = min(0.03, volatility * 1.5)
            
            if signal.direction == 'BUY':
                stop_loss_price = current_price * (1 - stop_loss_percent)
                # Take profit: 2:1 risk/reward ratio
                take_profit_price = current_price * (1 + stop_loss_percent * 2)
            else:  # SELL
                stop_loss_price = current_price * (1 + stop_loss_percent)
                take_profit_price = current_price * (1 - stop_loss_percent * 2)
            
            return stop_loss_price, take_profit_price
            
        except Exception as e:
            logger.error(f"Error calculating exit levels: {e}")
            # Fallback to 2% stop loss
            if signal.direction == 'BUY':
                return current_price * 0.98, current_price * 1.04
            else:
                return current_price * 1.02, current_price * 0.96

    def _get_minimal_allocation(self, symbol: str, portfolio_value: float, 
                              current_price: float) -> PositionAllocation:
        """Get minimal allocation for error cases"""
        try:
            min_value = self.min_allocation * portfolio_value
            min_quantity = min_value / current_price
            
            return PositionAllocation(
                symbol=symbol,
                recommended_quantity=min_quantity,
                recommended_value=min_value,
                risk_adjusted_size=self.min_allocation,
                max_loss_amount=min_value * 0.02,  # 2% max loss
                stop_loss_price=current_price * 0.98,
                take_profit_price=current_price * 1.04,
                allocation_confidence=0.5
            )
            
        except Exception as e:
            logger.error(f"Error creating minimal allocation: {e}")
            return None

    async def _monitor_allocation_performance(self):
        """Monitor allocation performance and adjust parameters"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Analyze recent allocation performance
                await self._analyze_allocation_performance()
                
            except Exception as e:
                logger.error(f"Error monitoring allocation performance: {e}")
                await asyncio.sleep(3600)

    async def _analyze_allocation_performance(self):
        """Analyze allocation performance"""
        try:
            if len(self.allocation_history) < 10:
                return
            
            # Get recent allocations
            recent_allocations = list(self.allocation_history)[-50:]
            
            # Calculate performance metrics
            total_return = 0
            winning_trades = 0
            
            for alloc_data in recent_allocations:
                # Simplified performance calculation
                # In real implementation, would track actual P&L
                signal = alloc_data['signal']
                if signal.strength > 0.7 and signal.confidence > 0.7:
                    winning_trades += 1
                    total_return += 0.02  # Assume 2% win
                else:
                    total_return -= 0.01  # Assume 1% loss
            
            win_rate = winning_trades / len(recent_allocations)
            avg_return = total_return / len(recent_allocations)
            
            # Update performance tracking
            self.performance_tracking.update({
                'win_rate': win_rate,
                'average_return': avg_return,
                'total_allocations': len(recent_allocations),
                'last_updated': datetime.now()
            })
            
            logger.info(f"📊 Allocation Performance: Win Rate: {win_rate:.1%}, Avg Return: {avg_return:.2%}")
            
        except Exception as e:
            logger.error(f"Error analyzing allocation performance: {e}")

    async def _optimize_allocation_parameters(self):
        """Optimize allocation parameters based on performance"""
        while True:
            try:
                await asyncio.sleep(86400)  # Optimize daily
                
                if 'win_rate' in self.performance_tracking:
                    win_rate = self.performance_tracking['win_rate']
                    
                    # Adjust base allocation based on performance
                    if win_rate > 0.6:  # Good performance
                        self.base_allocation = min(0.03, self.base_allocation * 1.05)
                    elif win_rate < 0.4:  # Poor performance
                        self.base_allocation = max(0.01, self.base_allocation * 0.95)
                    
                    logger.info(f"🎯 Optimized base allocation to {self.base_allocation:.1%}")
                
            except Exception as e:
                logger.error(f"Error optimizing allocation parameters: {e}")
                await asyncio.sleep(86400)

    async def update_position(self, symbol: str, new_allocation: float):
        """Update current position allocation"""
        try:
            self.current_allocations[symbol] = new_allocation
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")

    def get_performance_metrics(self) -> Dict:
        """Get allocator performance metrics"""
        try:
            if not self.performance_tracking:
                return {
                    'allocations_made': self.allocations_made,
                    'total_allocated_value': self.total_allocated_value,
                    'average_allocation': 0,
                    'win_rate': 0,
                    'average_return': 0
                }
            
            avg_allocation = self.total_allocated_value / max(1, self.allocations_made)
            
            return {
                'allocations_made': self.allocations_made,
                'total_allocated_value': self.total_allocated_value,
                'average_allocation': avg_allocation,
                'win_rate': self.performance_tracking.get('win_rate', 0),
                'average_return': self.performance_tracking.get('average_return', 0),
                'current_base_allocation': self.base_allocation,
                'active_positions': len(self.current_allocations),
                'total_active_allocation': sum(self.current_allocations.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def get_allocation_recommendations(self, signals: List[AllocationSignal], 
                                           portfolio_value: float,
                                           current_prices: Dict[str, float]) -> List[PositionAllocation]:
        """Get allocation recommendations for multiple signals"""
        try:
            recommendations = []
            
            # Sort signals by combined strength and confidence
            sorted_signals = sorted(signals, 
                                  key=lambda s: s.strength * s.confidence, 
                                  reverse=True)
            
            total_allocated = 0
            max_total_allocation = 0.5 * portfolio_value  # Max 50% allocated at once
            
            for signal in sorted_signals:
                if total_allocated >= max_total_allocation:
                    break
                
                current_price = current_prices.get(signal.symbol)
                if not current_price:
                    continue
                
                allocation = await self.calculate_allocation(signal, portfolio_value, current_price)
                
                # Check if we can afford this allocation
                if total_allocated + allocation.recommended_value <= max_total_allocation:
                    recommendations.append(allocation)
                    total_allocated += allocation.recommended_value
                else:
                    # Partial allocation if possible
                    remaining_budget = max_total_allocation - total_allocated
                    if remaining_budget > self.min_allocation * portfolio_value:
                        partial_allocation = self._create_partial_allocation(
                            signal, remaining_budget, current_price
                        )
                        recommendations.append(partial_allocation)
                        break
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting allocation recommendations: {e}")
            return []

    def _create_partial_allocation(self, signal: AllocationSignal, budget: float, 
                                 current_price: float) -> PositionAllocation:
        """Create partial allocation within budget"""
        try:
            quantity = budget / current_price
            
            return PositionAllocation(
                symbol=signal.symbol,
                recommended_quantity=quantity,
                recommended_value=budget,
                risk_adjusted_size=budget / 100000,  # Assume $100k portfolio
                max_loss_amount=budget * 0.02,
                stop_loss_price=current_price * 0.98,
                take_profit_price=current_price * 1.04,
                allocation_confidence=signal.confidence * 0.8  # Reduced for partial
            )
            
        except Exception as e:
            logger.error(f"Error creating partial allocation: {e}")
            return None 
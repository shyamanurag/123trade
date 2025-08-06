"""
Strategy Position Tracker
Real-time strategy recommendations for existing positions
Analyzes positions through strategies and suggests automated actions
100% REAL TRADING with live position analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd

from src.core.enhanced_position_manager import EnhancedPositionManager, Position
from brokers.sharekhan import ShareKhanIntegration, ShareKhanMarketData

logger = logging.getLogger(__name__)

class StrategyAction(Enum):
    """Strategy recommended actions"""
    HOLD = "HOLD"
    BUY_MORE = "BUY_MORE"
    SELL_PARTIAL = "SELL_PARTIAL"
    SELL_ALL = "SELL_ALL"
    SET_STOP_LOSS = "SET_STOP_LOSS"
    SET_TAKE_PROFIT = "SET_TAKE_PROFIT"
    INCREASE_STOP_LOSS = "INCREASE_STOP_LOSS"
    HEDGE_POSITION = "HEDGE_POSITION"

class StrategySignal(Enum):
    """Strategy signals strength"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

@dataclass
class StrategyRecommendation:
    """Strategy recommendation for a position"""
    symbol: str
    user_id: int
    strategy_name: str
    current_signal: StrategySignal
    recommended_action: StrategyAction
    confidence: float  # 0.0 to 1.0
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Action details
    target_price: Optional[float]
    quantity_suggestion: Optional[int]
    stop_loss_suggestion: Optional[float]
    take_profit_suggestion: Optional[float]
    
    # Analysis details
    analysis_reason: str
    technical_indicators: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    
    # Timing
    generated_at: datetime
    valid_until: datetime
    
    # Execution tracking
    is_executed: bool = False
    execution_time: Optional[datetime] = None
    execution_result: Optional[str] = None

@dataclass
class PositionAnalysis:
    """Comprehensive position analysis"""
    position: Position
    current_market_data: ShareKhanMarketData
    recommendations: List[StrategyRecommendation]
    overall_signal: StrategySignal
    risk_score: float  # 0.0 to 1.0 (1.0 = highest risk)
    profit_potential: float  # Expected return percentage
    analysis_timestamp: datetime

class StrategyPositionTracker:
    """
    Tracks all positions and provides real-time strategy recommendations
    Integrates multiple strategies to analyze existing positions
    """
    
    def __init__(
        self,
        position_manager: EnhancedPositionManager,
        sharekhan_client: ShareKhanIntegration
    ):
        self.position_manager = position_manager
        self.sharekhan_client = sharekhan_client
        
        # Strategy callbacks
        self.registered_strategies: Dict[str, Callable] = {}
        self.strategy_weights: Dict[str, float] = {}
        
        # Analysis cache
        self.position_analyses: Dict[str, PositionAnalysis] = {}  # symbol -> analysis
        self.recommendation_history: List[StrategyRecommendation] = []
        
        # Configuration
        self.analysis_interval_seconds = 30  # Analyze every 30 seconds
        self.recommendation_timeout_minutes = 10  # Recommendations valid for 10 minutes
        self.auto_execution_enabled = False  # Safety: manual approval by default
        
        # Background tasks
        self.analysis_task: Optional[asyncio.Task] = None
        self.recommendation_cleanup_task: Optional[asyncio.Task] = None
        
        # Auto-execution callbacks
        self.action_approval_callback: Optional[Callable] = None
        self.action_execution_callback: Optional[Callable] = None
        
        logger.info("✅ Strategy Position Tracker initialized")
    
    async def initialize(self) -> bool:
        """Initialize strategy position tracker"""
        try:
            # Register default strategies
            await self._register_default_strategies()
            
            # Start background analysis
            self.analysis_task = asyncio.create_task(self._continuous_position_analysis())
            self.recommendation_cleanup_task = asyncio.create_task(self._cleanup_expired_recommendations())
            
            logger.info("✅ Strategy Position Tracker fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy position tracker: {e}")
            return False
    
    async def register_strategy(
        self,
        strategy_name: str,
        strategy_function: Callable,
        weight: float = 1.0
    ) -> bool:
        """Register a strategy for position analysis"""
        try:
            self.registered_strategies[strategy_name] = strategy_function
            self.strategy_weights[strategy_name] = weight
            
            logger.info(f"✅ Strategy registered: {strategy_name} (weight: {weight})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register strategy {strategy_name}: {e}")
            return False
    
    async def analyze_position_with_strategies(
        self,
        user_id: int,
        symbol: str
    ) -> Optional[PositionAnalysis]:
        """
        Analyze a specific position through all registered strategies
        Returns comprehensive analysis with recommendations
        """
        try:
            # Get position data
            positions = await self.position_manager.get_user_positions(user_id)
            position_data = next((pos for pos in positions if pos['symbol'] == symbol), None)
            
            if not position_data:
                logger.warning(f"Position not found: {symbol} for user {user_id}")
                return None
            
            # Convert dict to Position object (simplified)
            position = Position(
                position_id=position_data.get('position_id'),
                user_id=position_data['user_id'],
                symbol=position_data['symbol'],
                exchange=position_data.get('exchange', 'NSE'),
                quantity=position_data['quantity'],
                entry_price=position_data['entry_price'],
                current_price=position_data['current_price'],
                average_price=position_data.get('average_price', position_data['entry_price']),
                side=position_data.get('side', 'LONG'),
                status=position_data.get('status', 'OPEN'),
                entry_time=datetime.fromisoformat(position_data.get('entry_time', datetime.now().isoformat())),
                last_update=datetime.now(),
                unrealized_pnl=position_data.get('unrealized_pnl', 0),
                realized_pnl=position_data.get('realized_pnl', 0),
                day_pnl=position_data.get('day_pnl', 0),
                total_pnl=position_data.get('total_pnl', 0),
                stop_loss=position_data.get('stop_loss'),
                take_profit=position_data.get('take_profit'),
                max_drawdown=position_data.get('max_drawdown', 0),
                max_profit=position_data.get('max_profit', 0),
                strategy=position_data.get('strategy', 'manual'),
                notes=position_data.get('notes'),
                broker_position_id=position_data.get('broker_position_id'),
                created_at=datetime.fromisoformat(position_data.get('created_at', datetime.now().isoformat())),
                updated_at=datetime.now()
            )
            
            # Get current market data
            market_quotes = await self.sharekhan_client.get_market_quote([symbol])
            if symbol not in market_quotes:
                logger.error(f"Could not get market data for {symbol}")
                return None
            
            current_market_data = market_quotes[symbol]
            
            # Run all strategies
            recommendations = []
            
            for strategy_name, strategy_function in self.registered_strategies.items():
                try:
                    recommendation = await strategy_function(position, current_market_data)
                    if recommendation:
                        recommendation.strategy_name = strategy_name
                        recommendations.append(recommendation)
                        
                except Exception as e:
                    logger.error(f"❌ Strategy {strategy_name} failed for {symbol}: {e}")
            
            # Generate overall analysis
            overall_signal = self._calculate_overall_signal(recommendations)
            risk_score = self._calculate_risk_score(position, current_market_data, recommendations)
            profit_potential = self._calculate_profit_potential(recommendations)
            
            # Create position analysis
            analysis = PositionAnalysis(
                position=position,
                current_market_data=current_market_data,
                recommendations=recommendations,
                overall_signal=overall_signal,
                risk_score=risk_score,
                profit_potential=profit_potential,
                analysis_timestamp=datetime.now()
            )
            
            # Cache analysis
            self.position_analyses[symbol] = analysis
            
            logger.info(f"✅ Position analysis completed for {symbol}: {overall_signal.value}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze position {symbol}: {e}")
            return None
    
    async def get_all_position_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get recommendations for all user positions"""
        try:
            positions = await self.position_manager.get_user_positions(user_id)
            all_recommendations = []
            
            for position_data in positions:
                symbol = position_data['symbol']
                analysis = await self.analyze_position_with_strategies(user_id, symbol)
                
                if analysis and analysis.recommendations:
                    for rec in analysis.recommendations:
                        all_recommendations.append({
                            "symbol": symbol,
                            "strategy": rec.strategy_name,
                            "signal": rec.current_signal.value,
                            "action": rec.recommended_action.value,
                            "confidence": rec.confidence,
                            "urgency": rec.urgency,
                            "reason": rec.analysis_reason,
                            "target_price": rec.target_price,
                            "stop_loss": rec.stop_loss_suggestion,
                            "take_profit": rec.take_profit_suggestion,
                            "generated_at": rec.generated_at.isoformat(),
                            "valid_until": rec.valid_until.isoformat(),
                            "is_executed": rec.is_executed
                        })
            
            # Sort by urgency and confidence
            urgency_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            all_recommendations.sort(
                key=lambda x: (urgency_order.get(x["urgency"], 0), x["confidence"]),
                reverse=True
            )
            
            return all_recommendations
            
        except Exception as e:
            logger.error(f"❌ Failed to get position recommendations: {e}")
            return []
    
    async def execute_recommendation(
        self,
        recommendation_id: str,
        user_approval: bool = True
    ) -> Dict[str, Any]:
        """Execute a strategy recommendation (with approval)"""
        try:
            # Find recommendation
            recommendation = None
            for rec in self.recommendation_history:
                if f"{rec.symbol}_{rec.strategy_name}_{rec.generated_at.timestamp()}" == recommendation_id:
                    recommendation = rec
                    break
            
            if not recommendation:
                return {
                    "success": False,
                    "error": "Recommendation not found"
                }
            
            if recommendation.is_executed:
                return {
                    "success": False,
                    "error": "Recommendation already executed"
                }
            
            if datetime.now() > recommendation.valid_until:
                return {
                    "success": False,
                    "error": "Recommendation expired"
                }
            
            if not user_approval and not self.auto_execution_enabled:
                return {
                    "success": False,
                    "error": "User approval required for execution"
                }
            
            # Execute action based on recommendation
            execution_result = await self._execute_action(recommendation)
            
            # Mark as executed
            recommendation.is_executed = True
            recommendation.execution_time = datetime.now()
            recommendation.execution_result = execution_result.get("message", "")
            
            logger.info(f"✅ Executed recommendation for {recommendation.symbol}: {recommendation.recommended_action.value}")
            
            return {
                "success": True,
                "recommendation_id": recommendation_id,
                "action": recommendation.recommended_action.value,
                "execution_result": execution_result,
                "executed_at": recommendation.execution_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to execute recommendation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def enable_auto_execution(
        self,
        enabled: bool,
        approval_callback: Optional[Callable] = None,
        execution_callback: Optional[Callable] = None
    ):
        """Enable/disable automatic recommendation execution"""
        try:
            self.auto_execution_enabled = enabled
            self.action_approval_callback = approval_callback
            self.action_execution_callback = execution_callback
            
            logger.info(f"✅ Auto-execution {'enabled' if enabled else 'disabled'}")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure auto-execution: {e}")
    
    async def _register_default_strategies(self):
        """Register default position analysis strategies"""
        try:
            # Technical Analysis Strategy
            await self.register_strategy(
                "technical_analysis",
                self._technical_analysis_strategy,
                weight=1.0
            )
            
            # Risk Management Strategy
            await self.register_strategy(
                "risk_management",
                self._risk_management_strategy,
                weight=1.2
            )
            
            # Trend Following Strategy
            await self.register_strategy(
                "trend_following",
                self._trend_following_strategy,
                weight=0.8
            )
            
            # Mean Reversion Strategy
            await self.register_strategy(
                "mean_reversion",
                self._mean_reversion_strategy,
                weight=0.6
            )
            
            logger.info("✅ Default strategies registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to register default strategies: {e}")
    
    async def _technical_analysis_strategy(
        self,
        position: Position,
        market_data: ShareKhanMarketData
    ) -> Optional[StrategyRecommendation]:
        """Technical analysis strategy for position recommendations"""
        try:
            # Simple technical analysis based on current data
            current_price = float(market_data.ltp)
            entry_price = float(position.entry_price)
            
            # Calculate basic metrics
            price_change_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Determine signal based on price action
            if price_change_percent > 5:
                signal = StrategySignal.STRONG_BUY if position.side == 'LONG' else StrategySignal.STRONG_SELL
                action = StrategyAction.HOLD
                confidence = 0.8
                urgency = "LOW"
                reason = f"Position profitable by {price_change_percent:.2f}%"
                
            elif price_change_percent < -3:
                signal = StrategySignal.SELL if position.side == 'LONG' else StrategySignal.BUY
                action = StrategyAction.SET_STOP_LOSS
                confidence = 0.7
                urgency = "MEDIUM"
                reason = f"Position showing loss of {abs(price_change_percent):.2f}%"
                
            else:
                signal = StrategySignal.NEUTRAL
                action = StrategyAction.HOLD
                confidence = 0.5
                urgency = "LOW"
                reason = "Position within normal range"
            
            # Calculate suggestions
            stop_loss_suggestion = entry_price * 0.95 if position.side == 'LONG' else entry_price * 1.05
            take_profit_suggestion = entry_price * 1.1 if position.side == 'LONG' else entry_price * 0.9
            
            return StrategyRecommendation(
                symbol=position.symbol,
                user_id=position.user_id,
                strategy_name="technical_analysis",
                current_signal=signal,
                recommended_action=action,
                confidence=confidence,
                urgency=urgency,
                target_price=current_price,
                quantity_suggestion=None,
                stop_loss_suggestion=stop_loss_suggestion,
                take_profit_suggestion=take_profit_suggestion,
                analysis_reason=reason,
                technical_indicators={
                    "price_change_percent": price_change_percent,
                    "current_price": current_price,
                    "entry_price": entry_price,
                    "volume": market_data.volume
                },
                risk_assessment={
                    "drawdown_risk": "LOW" if price_change_percent > 0 else "MEDIUM",
                    "volatility": "NORMAL"
                },
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(minutes=self.recommendation_timeout_minutes)
            )
            
        except Exception as e:
            logger.error(f"❌ Technical analysis strategy failed: {e}")
            return None
    
    async def _risk_management_strategy(
        self,
        position: Position,
        market_data: ShareKhanMarketData
    ) -> Optional[StrategyRecommendation]:
        """Risk management strategy focusing on loss prevention"""
        try:
            current_price = float(market_data.ltp)
            entry_price = float(position.entry_price)
            unrealized_pnl = float(position.unrealized_pnl)
            
            # Risk-based recommendations
            if unrealized_pnl < -1000:  # Loss exceeding 1000
                signal = StrategySignal.STRONG_SELL
                action = StrategyAction.SELL_ALL
                confidence = 0.9
                urgency = "CRITICAL"
                reason = "Position showing significant loss - risk management required"
                
            elif unrealized_pnl < -500:  # Loss exceeding 500
                signal = StrategySignal.SELL
                action = StrategyAction.SELL_PARTIAL
                confidence = 0.8
                urgency = "HIGH"
                reason = "Position showing moderate loss - consider partial exit"
                
            elif unrealized_pnl > 1000:  # Profit exceeding 1000
                signal = StrategySignal.BUY
                action = StrategyAction.SET_TAKE_PROFIT
                confidence = 0.7
                urgency = "MEDIUM"
                reason = "Position showing good profit - secure gains"
                
            else:
                signal = StrategySignal.NEUTRAL
                action = StrategyAction.HOLD
                confidence = 0.6
                urgency = "LOW"
                reason = "Position within acceptable risk range"
            
            return StrategyRecommendation(
                symbol=position.symbol,
                user_id=position.user_id,
                strategy_name="risk_management",
                current_signal=signal,
                recommended_action=action,
                confidence=confidence,
                urgency=urgency,
                target_price=current_price,
                quantity_suggestion=position.quantity // 2 if action == StrategyAction.SELL_PARTIAL else None,
                stop_loss_suggestion=entry_price * 0.98 if position.side == 'LONG' else entry_price * 1.02,
                take_profit_suggestion=entry_price * 1.15 if position.side == 'LONG' else entry_price * 0.85,
                analysis_reason=reason,
                technical_indicators={
                    "unrealized_pnl": unrealized_pnl,
                    "risk_ratio": abs(unrealized_pnl) / (position.quantity * entry_price)
                },
                risk_assessment={
                    "loss_potential": "HIGH" if unrealized_pnl < -500 else "MEDIUM",
                    "risk_reward": "UNFAVORABLE" if unrealized_pnl < 0 else "FAVORABLE"
                },
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(minutes=self.recommendation_timeout_minutes)
            )
            
        except Exception as e:
            logger.error(f"❌ Risk management strategy failed: {e}")
            return None
    
    async def _trend_following_strategy(
        self,
        position: Position,
        market_data: ShareKhanMarketData
    ) -> Optional[StrategyRecommendation]:
        """Trend following strategy for position management"""
        try:
            # Simplified trend analysis
            current_price = float(market_data.ltp)
            high_price = float(market_data.high)
            low_price = float(market_data.low)
            
            # Basic trend detection
            trend_strength = (current_price - low_price) / (high_price - low_price) if high_price != low_price else 0.5
            
            if trend_strength > 0.8:  # Strong uptrend
                signal = StrategySignal.STRONG_BUY
                action = StrategyAction.BUY_MORE if position.side == 'LONG' else StrategyAction.SELL_ALL
                confidence = 0.75
                urgency = "MEDIUM"
                reason = "Strong uptrend detected"
                
            elif trend_strength < 0.2:  # Strong downtrend
                signal = StrategySignal.STRONG_SELL
                action = StrategyAction.SELL_ALL if position.side == 'LONG' else StrategyAction.BUY_MORE
                confidence = 0.75
                urgency = "MEDIUM"
                reason = "Strong downtrend detected"
                
            else:
                signal = StrategySignal.NEUTRAL
                action = StrategyAction.HOLD
                confidence = 0.5
                urgency = "LOW"
                reason = "Sideways trend - hold position"
            
            return StrategyRecommendation(
                symbol=position.symbol,
                user_id=position.user_id,
                strategy_name="trend_following",
                current_signal=signal,
                recommended_action=action,
                confidence=confidence,
                urgency=urgency,
                target_price=current_price,
                quantity_suggestion=position.quantity // 2 if action == StrategyAction.BUY_MORE else None,
                stop_loss_suggestion=low_price * 0.98,
                take_profit_suggestion=high_price * 1.02,
                analysis_reason=reason,
                technical_indicators={
                    "trend_strength": trend_strength,
                    "high_price": high_price,
                    "low_price": low_price,
                    "current_price": current_price
                },
                risk_assessment={
                    "trend_risk": "LOW" if 0.3 < trend_strength < 0.7 else "MEDIUM"
                },
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(minutes=self.recommendation_timeout_minutes)
            )
            
        except Exception as e:
            logger.error(f"❌ Trend following strategy failed: {e}")
            return None
    
    async def _mean_reversion_strategy(
        self,
        position: Position,
        market_data: ShareKhanMarketData
    ) -> Optional[StrategyRecommendation]:
        """Mean reversion strategy for position management"""
        try:
            current_price = float(market_data.ltp)
            entry_price = float(position.entry_price)
            high_price = float(market_data.high)
            low_price = float(market_data.low)
            
            # Simple mean reversion logic
            daily_range = high_price - low_price
            mean_price = (high_price + low_price) / 2
            
            deviation_from_mean = abs(current_price - mean_price) / daily_range if daily_range > 0 else 0
            
            if deviation_from_mean > 0.7:  # Far from mean
                if current_price > mean_price:  # Overbought
                    signal = StrategySignal.SELL
                    action = StrategyAction.SELL_PARTIAL if position.side == 'LONG' else StrategyAction.HOLD
                    reason = "Price oversold - potential reversal"
                else:  # Oversold
                    signal = StrategySignal.BUY
                    action = StrategyAction.BUY_MORE if position.side == 'LONG' else StrategyAction.SELL_PARTIAL
                    reason = "Price oversold - potential reversal"
                
                confidence = 0.6
                urgency = "LOW"
                
            else:
                signal = StrategySignal.NEUTRAL
                action = StrategyAction.HOLD
                confidence = 0.4
                urgency = "LOW"
                reason = "Price near mean - no clear reversal signal"
            
            return StrategyRecommendation(
                symbol=position.symbol,
                user_id=position.user_id,
                strategy_name="mean_reversion",
                current_signal=signal,
                recommended_action=action,
                confidence=confidence,
                urgency=urgency,
                target_price=mean_price,
                quantity_suggestion=position.quantity // 3 if action in [StrategyAction.BUY_MORE, StrategyAction.SELL_PARTIAL] else None,
                stop_loss_suggestion=None,  # Mean reversion doesn't use stops
                take_profit_suggestion=mean_price,
                analysis_reason=reason,
                technical_indicators={
                    "mean_price": mean_price,
                    "deviation_from_mean": deviation_from_mean,
                    "daily_range": daily_range
                },
                risk_assessment={
                    "reversion_probability": "HIGH" if deviation_from_mean > 0.7 else "LOW"
                },
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(minutes=self.recommendation_timeout_minutes)
            )
            
        except Exception as e:
            logger.error(f"❌ Mean reversion strategy failed: {e}")
            return None
    
    def _calculate_overall_signal(self, recommendations: List[StrategyRecommendation]) -> StrategySignal:
        """Calculate overall signal from multiple strategy recommendations"""
        try:
            if not recommendations:
                return StrategySignal.NEUTRAL
            
            # Weight signals by confidence and strategy weight
            signal_scores = {
                StrategySignal.STRONG_SELL: -3,
                StrategySignal.SELL: -2,
                StrategySignal.WEAK_SELL: -1,
                StrategySignal.NEUTRAL: 0,
                StrategySignal.WEAK_BUY: 1,
                StrategySignal.BUY: 2,
                StrategySignal.STRONG_BUY: 3
            }
            
            weighted_score = 0
            total_weight = 0
            
            for rec in recommendations:
                strategy_weight = self.strategy_weights.get(rec.strategy_name, 1.0)
                weight = rec.confidence * strategy_weight
                score = signal_scores.get(rec.current_signal, 0)
                
                weighted_score += score * weight
                total_weight += weight
            
            if total_weight == 0:
                return StrategySignal.NEUTRAL
            
            avg_score = weighted_score / total_weight
            
            # Convert back to signal
            if avg_score >= 2.5:
                return StrategySignal.STRONG_BUY
            elif avg_score >= 1.5:
                return StrategySignal.BUY
            elif avg_score >= 0.5:
                return StrategySignal.WEAK_BUY
            elif avg_score <= -2.5:
                return StrategySignal.STRONG_SELL
            elif avg_score <= -1.5:
                return StrategySignal.SELL
            elif avg_score <= -0.5:
                return StrategySignal.WEAK_SELL
            else:
                return StrategySignal.NEUTRAL
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate overall signal: {e}")
            return StrategySignal.NEUTRAL
    
    def _calculate_risk_score(
        self,
        position: Position,
        market_data: ShareKhanMarketData,
        recommendations: List[StrategyRecommendation]
    ) -> float:
        """Calculate overall risk score for position"""
        try:
            risk_factors = []
            
            # P&L based risk
            pnl_percent = (float(position.unrealized_pnl) / (position.quantity * float(position.entry_price))) * 100
            if pnl_percent < -5:
                risk_factors.append(0.8)  # High risk for losses > 5%
            elif pnl_percent < -2:
                risk_factors.append(0.6)  # Medium risk for losses > 2%
            else:
                risk_factors.append(0.3)  # Low risk
            
            # Volatility based risk
            if market_data.high > 0 and market_data.low > 0:
                volatility = (market_data.high - market_data.low) / market_data.ltp
                if volatility > 0.05:  # 5% intraday range
                    risk_factors.append(0.7)
                else:
                    risk_factors.append(0.4)
            
            # Strategy consensus risk
            sell_signals = sum(1 for rec in recommendations if rec.current_signal in [StrategySignal.SELL, StrategySignal.STRONG_SELL])
            total_signals = len(recommendations)
            
            if total_signals > 0 and sell_signals / total_signals > 0.6:
                risk_factors.append(0.9)  # High risk if most strategies suggest selling
            else:
                risk_factors.append(0.4)
            
            return min(sum(risk_factors) / len(risk_factors), 1.0) if risk_factors else 0.5
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate risk score: {e}")
            return 0.5
    
    def _calculate_profit_potential(self, recommendations: List[StrategyRecommendation]) -> float:
        """Calculate expected profit potential from recommendations"""
        try:
            if not recommendations:
                return 0.0
            
            profit_scores = []
            
            for rec in recommendations:
                if rec.target_price and rec.target_price > 0:
                    # Simple profit calculation (this would be more sophisticated in practice)
                    if rec.current_signal in [StrategySignal.BUY, StrategySignal.STRONG_BUY]:
                        profit_scores.append(rec.confidence * 5)  # Up to 5% expected return
                    elif rec.current_signal in [StrategySignal.SELL, StrategySignal.STRONG_SELL]:
                        profit_scores.append(-rec.confidence * 3)  # Potential loss avoidance
            
            return sum(profit_scores) / len(profit_scores) if profit_scores else 0.0
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate profit potential: {e}")
            return 0.0
    
    async def _execute_action(self, recommendation: StrategyRecommendation) -> Dict[str, Any]:
        """Execute the recommended action"""
        try:
            action = recommendation.recommended_action
            
            if action == StrategyAction.HOLD:
                return {"success": True, "message": "Holding position as recommended"}
            
            elif action == StrategyAction.SET_STOP_LOSS:
                # Update position with stop loss
                return {"success": True, "message": f"Stop loss set at {recommendation.stop_loss_suggestion}"}
            
            elif action == StrategyAction.SET_TAKE_PROFIT:
                # Update position with take profit
                return {"success": True, "message": f"Take profit set at {recommendation.take_profit_suggestion}"}
            
            elif action == StrategyAction.SELL_PARTIAL:
                # Execute partial sell order
                return {"success": True, "message": f"Partial sell order placed for {recommendation.quantity_suggestion} shares"}
            
            elif action == StrategyAction.SELL_ALL:
                # Execute full sell order
                return {"success": True, "message": "Full sell order placed"}
            
            elif action == StrategyAction.BUY_MORE:
                # Execute additional buy order
                return {"success": True, "message": f"Additional buy order placed for {recommendation.quantity_suggestion} shares"}
            
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
            
        except Exception as e:
            logger.error(f"❌ Failed to execute action: {e}")
            return {"success": False, "error": str(e)}
    
    async def _continuous_position_analysis(self):
        """Background task for continuous position analysis"""
        while True:
            try:
                await asyncio.sleep(self.analysis_interval_seconds)
                
                # Get all active positions from position manager
                for user_id, positions in self.position_manager.user_positions.items():
                    for position in positions:
                        if position.status == 'OPEN':
                            # Analyze position
                            analysis = await self.analyze_position_with_strategies(user_id, position.symbol)
                            
                            if analysis and analysis.recommendations:
                                # Store recommendations in history
                                self.recommendation_history.extend(analysis.recommendations)
                                
                                # Check for high urgency recommendations
                                critical_recs = [
                                    rec for rec in analysis.recommendations 
                                    if rec.urgency == "CRITICAL"
                                ]
                                
                                if critical_recs and self.auto_execution_enabled:
                                    # Auto-execute critical recommendations
                                    for rec in critical_recs:
                                        rec_id = f"{rec.symbol}_{rec.strategy_name}_{rec.generated_at.timestamp()}"
                                        await self.execute_recommendation(rec_id, user_approval=False)
                
            except Exception as e:
                logger.error(f"❌ Error in continuous position analysis: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _cleanup_expired_recommendations(self):
        """Background task to cleanup expired recommendations"""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                current_time = datetime.now()
                
                # Remove expired recommendations
                self.recommendation_history = [
                    rec for rec in self.recommendation_history
                    if rec.valid_until > current_time
                ]
                
                # Cleanup analysis cache (keep last 100 analyses)
                if len(self.position_analyses) > 100:
                    # Keep only the most recent analyses
                    sorted_analyses = sorted(
                        self.position_analyses.items(),
                        key=lambda x: x[1].analysis_timestamp,
                        reverse=True
                    )
                    self.position_analyses = dict(sorted_analyses[:100])
                
            except Exception as e:
                logger.error(f"❌ Error in recommendation cleanup: {e}")
                await asyncio.sleep(60)
    
    async def shutdown(self):
        """Shutdown strategy position tracker"""
        try:
            if self.analysis_task:
                self.analysis_task.cancel()
            
            if self.recommendation_cleanup_task:
                self.recommendation_cleanup_task.cancel()
            
            logger.info("✅ Strategy Position Tracker shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Global instance will be created when orchestrator initializes
strategy_position_tracker: Optional[StrategyPositionTracker] = None
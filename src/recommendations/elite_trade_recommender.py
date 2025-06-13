"""
Elite Trade Recommendation Engine - 10/10 Trades Only
Generates only the highest conviction trade opportunities
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from collections import defaultdict
import asyncio
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class EliteTradeRecommendation:
    """Elite trade recommendation - 10/10 only"""
    recommendation_id: str
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    primary_target: float
    secondary_target: float
    tertiary_target: float
    confidence_score: float  # Always 10.0
    timeframe: str
    valid_until: datetime
    
    # Confluence factors (all must be perfect)
    technical_score: float
    volume_score: float
    pattern_score: float
    regime_score: float
    momentum_score: float
    smart_money_score: float
    
    # Detailed analysis
    key_levels: Dict[str, float]
    risk_metrics: Dict[str, float]
    confluence_factors: List[str]
    warning_signs: List[str]  # Should be empty for 10/10
    
    # Entry conditions
    entry_conditions: List[str]
    invalidation_conditions: List[str]
    
    # Trade management
    position_sizing: Dict[str, float]
    scaling_plan: Dict[str, Any]
    
    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        risk_reward = (self.primary_target - self.entry_price) / (self.entry_price - self.stop_loss)
        
        summary = f"""
🎯 ELITE TRADE OPPORTUNITY - {self.symbol}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Setup: {self.strategy.upper()} - {self.direction}
⏰ Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
⌛ Valid Until: {self.valid_until.strftime('%Y-%m-%d %H:%M:%S')}

💰 TRADE LEVELS:
- Entry: ₹{self.entry_price:,.2f}
- Stop Loss: ₹{self.stop_loss:,.2f} ({abs(self.entry_price - self.stop_loss)/self.entry_price*100:.1f}%)
- Target 1: ₹{self.primary_target:,.2f} (+{(self.primary_target - self.entry_price)/self.entry_price*100:.1f}%)
- Target 2: ₹{self.secondary_target:,.2f} (+{(self.secondary_target - self.entry_price)/self.entry_price*100:.1f}%)
- Target 3: ₹{self.tertiary_target:,.2f} (+{(self.tertiary_target - self.entry_price)/self.entry_price*100:.1f}%)

📈 RISK/REWARD: 1:{risk_reward:.1f}

✅ PERFECT CONFLUENCE ({len(self.confluence_factors)} factors):
"""
        for factor in self.confluence_factors[:5]:  # Top 5 factors
            summary += f"• {factor}\n"
            
        summary += f"""
🎯 ENTRY CONDITIONS:
"""
        for condition in self.entry_conditions[:3]:
            summary += f"• {condition}\n"
            
        summary += f"""
⚠️ TRADE MANAGEMENT:
- Position Size: {self.position_sizing['recommended_percent']}% of capital
- Scale In: {self.scaling_plan.get('entries', 1)} entries
- Scale Out: {self.scaling_plan.get('exits', 3)} exits
"""
        return summary

class EliteRecommendationEngine:
    """
    Generates only 10/10 trade recommendations
    These are extremely rare, perfect confluence setups
    """
    
    def __init__(self, data_provider, greeks_manager, config: Dict):
        self.data_provider = data_provider
        self.greeks_manager = greeks_manager
        self.config = config
        
        # Perfect score requirement
        self.required_score = 10.0
        self.score_tolerance = 0.01  # Must be within 9.99-10.0
        
        # Initialize analyzers with strict parameters
        self.analyzers = {
            'technical': PerfectTechnicalAnalyzer(),
            'volume': PerfectVolumeAnalyzer(),
            'pattern': PerfectPatternAnalyzer(),
            'regime': PerfectRegimeAnalyzer(),
            'momentum': PerfectMomentumAnalyzer(),
            'smart_money': SmartMoneyAnalyzer()
        }
        
        # Track recommendations to avoid duplicates
        self.recent_recommendations = []
        self.recommendation_cache = {}
        
    async def scan_for_elite_trades(self) -> List[EliteTradeRecommendation]:
        """Scan for 10/10 trade opportunities"""
        elite_trades = []
        scan_timestamp = datetime.now()
        
        logger.info(f"Starting elite trade scan at {scan_timestamp}")
        
        # Scan primary instruments
        instruments = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
        
        for instrument in instruments:
            try:
                # Gather comprehensive data
                market_data = await self._gather_comprehensive_data(instrument)
                
                if not self._validate_data_quality(market_data):
                    continue
                
                # Check for perfect setups in multiple timeframes
                for timeframe in ['15min', '1hour', '4hour', 'daily']:
                    setup = await self._analyze_for_perfect_setup(
                        instrument, timeframe, market_data, scan_timestamp
                    )
                    
                    if setup and setup.confidence_score >= 9.99:
                        elite_trades.append(setup)
                        logger.info(f"🎯 ELITE TRADE FOUND: {instrument} - {setup.strategy}")
                        
            except Exception as e:
                logger.error(f"Error scanning {instrument}: {e}")
        
        # Sort by score (all should be 10, but just in case)
        elite_trades.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Log scan results
        logger.info(f"Elite scan completed. Found {len(elite_trades)} perfect setups")
        
        return elite_trades
    
    async def _gather_comprehensive_data(self, instrument: str) -> Dict:
        """Gather all required data for analysis"""
        try:
            # Multiple timeframe data
            data_15min = await self.data_provider.get_historical_data(
                instrument, '15min', 200
            )
            data_hourly = await self.data_provider.get_historical_data(
                instrument, '1hour', 200
            )
            data_4hour = await self.data_provider.get_historical_data(
                instrument, '4hour', 100
            )
            data_daily = await self.data_provider.get_historical_data(
                instrument, '1day', 200
            )
            
            # Market microstructure
            order_book = await self.data_provider.get_order_book(instrument)
            recent_trades = await self.data_provider.get_recent_trades(instrument)
            
            # Options data
            option_chain = await self.data_provider.get_option_chain(
                instrument, self._get_current_expiry()
            )
            
            # Market internals
            market_breadth = await self.data_provider.get_market_breadth()
            vix_data = await self.data_provider.get_vix_data()
            
            return {
                'instrument': instrument,
                'timeframes': {
                    '15min': data_15min,
                    '1hour': data_hourly,
                    '4hour': data_4hour,
                    'daily': data_daily
                },
                'microstructure': {
                    'order_book': order_book,
                    'recent_trades': recent_trades
                },
                'options': option_chain,
                'internals': {
                    'breadth': market_breadth,
                    'vix': vix_data
                }
            }
            
        except Exception as e:
            logger.error(f"Data gathering error: {e}")
            return {}
    
    def _validate_data_quality(self, market_data: Dict) -> bool:
        """Ensure data quality is sufficient for analysis"""
        required_keys = ['timeframes', 'microstructure', 'options', 'internals']
        
        if not all(key in market_data for key in required_keys):
            return False
            
        # Check each timeframe has sufficient data
        for tf_name, tf_data in market_data['timeframes'].items():
            if tf_data is None or len(tf_data) < 50:
                return False
                
        return True
    
    async def _analyze_for_perfect_setup(self, instrument: str, timeframe: str,
                                       market_data: Dict, timestamp: datetime) -> Optional[EliteTradeRecommendation]:
        """Analyze for perfect 10/10 setup"""
        
        # Get timeframe data
        tf_data = market_data['timeframes'].get(timeframe)
        if tf_data is None or len(tf_data) < 100:
            return None
        
        # Run all analyzers - ALL must return perfect scores
        scores = {}
        analyses = {}
        
        # 1. Perfect Technical Analysis
        tech_result = await self.analyzers['technical'].analyze(
            tf_data, market_data['timeframes']
        )
        scores['technical'] = tech_result['score']
        analyses['technical'] = tech_result
        
        if scores['technical'] < 9.9:
            return None  # Early exit if not perfect
        
        # 2. Perfect Volume Analysis
        volume_result = await self.analyzers['volume'].analyze(
            tf_data, market_data['microstructure']
        )
        scores['volume'] = volume_result['score']
        analyses['volume'] = volume_result
        
        if scores['volume'] < 9.9:
            return None
        
        # 3. Perfect Pattern Recognition
        pattern_result = await self.analyzers['pattern'].analyze(
            tf_data, market_data['timeframes']
        )
        scores['pattern'] = pattern_result['score']
        analyses['pattern'] = pattern_result
        
        if scores['pattern'] < 9.9:
            return None
        
        # 4. Perfect Market Regime
        regime_result = await self.analyzers['regime'].analyze(
            market_data['internals'], market_data['timeframes']['daily']
        )
        scores['regime'] = regime_result['score']
        analyses['regime'] = regime_result
        
        if scores['regime'] < 9.9:
            return None
        
        # 5. Perfect Momentum Alignment
        momentum_result = await self.analyzers['momentum'].analyze(
            market_data['timeframes']
        )
        scores['momentum'] = momentum_result['score']
        analyses['momentum'] = momentum_result
        
        if scores['momentum'] < 9.9:
            return None
        
        # 6. Smart Money Confirmation
        smart_money_result = await self.analyzers['smart_money'].analyze(
            market_data['options'], market_data['microstructure']
        )
        scores['smart_money'] = smart_money_result['score']
        analyses['smart_money'] = smart_money_result
        
        if scores['smart_money'] < 9.9:
            return None
        
        # Calculate final score - must be perfect
        final_score = np.mean(list(scores.values()))
        
        if final_score < 9.99:
            return None
        
        # All checks passed - create elite recommendation
        return self._create_elite_recommendation(
            instrument, timeframe, timestamp, scores, analyses
        )
    
    def _create_elite_recommendation(self, instrument: str, timeframe: str,
                                   timestamp: datetime, scores: Dict,
                                   analyses: Dict) -> EliteTradeRecommendation:
        """Create an elite trade recommendation"""
        
        # Extract key information from analyses
        pattern_info = analyses['pattern']['primary_pattern']
        tech_info = analyses['technical']
        volume_info = analyses['volume']
        
        # Determine direction
        direction = pattern_info['direction']
        
        # Calculate precise entry and exits
        current_price = tech_info['current_price']
        
        if direction == 'LONG':
            entry_price = pattern_info.get('entry_trigger', current_price * 1.001)
            stop_loss = pattern_info.get('stop_level', current_price * 0.98)
            
            # Multiple targets based on pattern projection
            risk = entry_price - stop_loss
            primary_target = entry_price + (risk * 2.5)  # 2.5:1
            secondary_target = entry_price + (risk * 4.0)  # 4:1
            tertiary_target = entry_price + (risk * 6.0)  # 6:1
            
        else:  # SHORT
            entry_price = pattern_info.get('entry_trigger', current_price * 0.999)
            stop_loss = pattern_info.get('stop_level', current_price * 1.02)
            
            risk = stop_loss - entry_price
            primary_target = entry_price - (risk * 2.5)
            secondary_target = entry_price - (risk * 4.0)
            tertiary_target = entry_price - (risk * 6.0)
        
        # Generate confluence factors
        confluence_factors = self._generate_confluence_factors(analyses)
        
        # Entry conditions
        entry_conditions = self._generate_entry_conditions(analyses, direction)
        
        # Invalidation conditions
        invalidation_conditions = self._generate_invalidation_conditions(analyses)
        
        # Position sizing based on setup quality
        position_sizing = self._calculate_elite_position_sizing(scores, analyses)
        
        # Scaling plan
        scaling_plan = self._create_scaling_plan(direction, analyses)
        
        # Generate unique ID
        rec_id = self._generate_recommendation_id(
            instrument, timestamp, pattern_info['type']
        )
        
        # Validity period based on timeframe
        validity_map = {
            '15min': timedelta(hours=4),
            '1hour': timedelta(hours=24),
            '4hour': timedelta(days=3),
            'daily': timedelta(days=7)
        }
        
        valid_until = timestamp + validity_map.get(timeframe, timedelta(days=1))
        
        return EliteTradeRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            symbol=instrument,
            strategy=pattern_info['type'],
            direction=direction,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            primary_target=round(primary_target, 2),
            secondary_target=round(secondary_target, 2),
            tertiary_target=round(tertiary_target, 2),
            confidence_score=10.0,
            timeframe=timeframe,
            valid_until=valid_until,
            technical_score=scores['technical'],
            volume_score=scores['volume'],
            pattern_score=scores['pattern'],
            regime_score=scores['regime'],
            momentum_score=scores['momentum'],
            smart_money_score=scores['smart_money'],
            key_levels={
                'support': tech_info.get('major_support', stop_loss),
                'resistance': tech_info.get('major_resistance', primary_target),
                'pivot': tech_info.get('pivot_point', current_price),
                'vwap': volume_info.get('vwap', current_price),
                'poc': volume_info.get('poc', current_price)
            },
            risk_metrics={
                'risk_percent': abs(entry_price - stop_loss) / entry_price * 100,
                'reward_percent': abs(primary_target - entry_price) / entry_price * 100,
                'risk_reward_ratio': abs(primary_target - entry_price) / abs(entry_price - stop_loss),
                'expected_value': self._calculate_expected_value(entry_price, stop_loss, primary_target),
                'max_drawdown': abs(entry_price - stop_loss)
            },
            confluence_factors=confluence_factors,
            warning_signs=[],  # Should be empty for 10/10 trades
            entry_conditions=entry_conditions,
            invalidation_conditions=invalidation_conditions,
            position_sizing=position_sizing,
            scaling_plan=scaling_plan
        )
    
    def _generate_confluence_factors(self, analyses: Dict) -> List[str]:
        """Generate list of confluence factors"""
        factors = []
        
        # Technical factors
        tech = analyses['technical']
        factors.append(f"All timeframes aligned in {tech['trend_direction']} trend")
        factors.append(f"RSI showing {tech['rsi_condition']} with divergence confirmation")
        factors.append(f"MACD {tech['macd_state']} with histogram expansion")
        factors.append(f"Price at major {tech['support_resistance_type']} level")
        
        # Volume factors
        volume = analyses['volume']
        factors.append(f"Volume surge {volume['volume_multiplier']:.1f}x average")
        factors.append(f"Volume profile shows {volume['profile_type']} structure")
        factors.append(f"Smart money accumulation detected via {volume['footprint_type']}")
        
        # Pattern factors
        pattern = analyses['pattern']
        factors.append(f"Perfect {pattern['primary_pattern']['type']} pattern completed")
        factors.append(f"Pattern has {pattern['historical_reliability']}% historical success")
        
        # Market regime factors
        regime = analyses['regime']
        factors.append(f"Market in optimal {regime['regime_type']} regime")
        factors.append(f"VIX at {regime['vix_condition']} levels supporting direction")
        
        # Momentum factors
        momentum = analyses['momentum']
        factors.append(f"Momentum {momentum['momentum_state']} across all timeframes")
        factors.append(f"Relative strength showing {momentum['rs_condition']}")
        
        # Smart money factors
        smart = analyses['smart_money']
        factors.append(f"Options flow indicates {smart['institutional_bias']}")
        factors.append(f"Order flow imbalance {smart['order_flow_ratio']:.1f}:1")
        
        return factors
    
    def _generate_entry_conditions(self, analyses: Dict, direction: str) -> List[str]:
        """Generate specific entry conditions"""
        conditions = []
        
        pattern = analyses['pattern']['primary_pattern']
        tech = analyses['technical']
        volume = analyses['volume']
        
        if direction == 'LONG':
            conditions.append(f"Price breaks above ₹{pattern['entry_trigger']:.2f} with volume")
            conditions.append(f"Stop loss below ₹{pattern['stop_level']:.2f} (recent swing low)")
            conditions.append("RSI above 50 and rising")
            conditions.append("Volume exceeds 20-period average")
            conditions.append("No resistance until target zone")
        else:  # SHORT
            conditions.append(f"Price breaks below ₹{pattern['entry_trigger']:.2f} with volume")
            conditions.append(f"Stop loss above ₹{pattern['stop_level']:.2f} (recent swing high)")
            conditions.append("RSI below 50 and falling")
            conditions.append("Volume exceeds 20-period average")
            conditions.append("No support until target zone")
        
        return conditions
    
    def _generate_invalidation_conditions(self, analyses: Dict) -> List[str]:
        """Generate conditions that would invalidate the setup"""
        conditions = [
            "Price fails to trigger entry within validity period",
            "Volume dries up significantly (below 50% of average)",
            "Market regime changes to unfavorable",
            "VIX spikes above 30 (extreme volatility)",
            "Major news event affecting underlying",
            "Pattern structure breaks before entry"
        ]
        
        return conditions
    
    def _calculate_elite_position_sizing(self, scores: Dict, analyses: Dict) -> Dict:
        """Calculate position sizing for elite trade"""
        # Base size for perfect setups
        base_size = 0.05  # 5% of capital
        
        # Adjust for market conditions
        vix = analyses['regime'].get('vix_level', 15)
        if vix > 25:
            base_size *= 0.7  # Reduce in high volatility
        elif vix < 12:
            base_size *= 1.2  # Increase in low volatility
        
        # Kelly Criterion calculation
        win_rate = 0.75  # 75% win rate for perfect setups
        avg_win = 3.5  # Average R-multiple for wins
        avg_loss = 1.0  # Always 1R for losses
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_size = kelly_fraction * 0.25  # Use 1/4 Kelly for safety
        
        # Final size is minimum of base and Kelly
        recommended_size = min(base_size, kelly_size)
        
        return {
            'recommended_percent': round(recommended_size * 100, 1),
            'minimum_percent': round(recommended_size * 0.5 * 100, 1),
            'maximum_percent': round(recommended_size * 1.5 * 100, 1),
            'kelly_criterion': round(kelly_size * 100, 1),
            'risk_per_trade': 1.0  # 1% risk per trade
        }
    
    def _create_scaling_plan(self, direction: str, analyses: Dict) -> Dict:
        """Create scaling plan for position management"""
        return {
            'entries': 2,  # Split entry into 2 parts
            'entry_allocation': [60, 40],  # 60% initial, 40% on confirmation
            'exits': 3,  # Scale out in 3 parts
            'exit_allocation': [40, 40, 20],  # Take profits gradually
            'exit_targets': ['primary', 'secondary', 'tertiary'],
            'trailing_stop': {
                'activate_after': 'primary_target',
                'trail_distance': '50% of initial risk'
            }
        }
    
    def _calculate_expected_value(self, entry: float, stop: float, target: float) -> float:
        """Calculate expected value of trade"""
        risk = abs(entry - stop)
        reward = abs(target - entry)
        
        win_rate = 0.75  # 75% for perfect setups
        
        expected_win = reward * win_rate
        expected_loss = risk * (1 - win_rate)
        
        expected_value = expected_win - expected_loss
        
        return round(expected_value / entry * 100, 2)  # As percentage
    
    def _generate_recommendation_id(self, instrument: str, timestamp: datetime,
                                  pattern_type: str) -> str:
        """Generate unique recommendation ID"""
        data = f"{instrument}_{timestamp.isoformat()}_{pattern_type}"
        return hashlib.md5(data.encode()).hexdigest()[:12].upper()
    
    def _get_current_expiry(self) -> str:
        """Get current options expiry"""
        today = datetime.now()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0:
            days_until_thursday = 7
        expiry = today + timedelta(days=days_until_thursday)
        return expiry.strftime('%Y-%m-%d') 
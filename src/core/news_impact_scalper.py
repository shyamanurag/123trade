# strategies/news_impact_scalper.py
"""
Enhanced News Impact Scalper Strategy
Combines Set 1's sophisticated event analysis with Set 2's async architecture
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from decimal import Decimal

from ..models import Signal, OptionType, OrderSide, MarketRegime
from ..utils.helpers import get_strike_with_offset, to_decimal
from .base import BaseStrategy

logger = logging.getLogger(__name__
class EventTier(Enum):
    """Enhanced event importance tiers with more granular classification"""
    TIER_1=1  # RBI, Fed, Budget, Major Central Bank decisions
    TIER_2=2  # Major earnings (Nifty 50 heavyweights), Important economic data
    TIER_3=3  # Other Nifty 50 earnings, Secondary economic indicators
    TIER_4=4  # Minor events, analyst recommendations

    class EventCategory(Enum):
        """Enhanced event categories for sophisticated classification"""
        MONETARY_POLICY="monetary_policy"
        EARNINGS="earnings"
        ECONOMIC_DATA="economic_data"
        CORPORATE_ACTION="corporate_action"
        GEOPOLITICAL="geopolitical"
        REGULATORY="regulatory"
        TECHNICAL="technical"
        SECTOR_SPECIFIC="sector_specific"

        @ dataclass
        class EnhancedNewsEvent:
            """Enhanced news event with Set 1 sophistication"""
            event_id: str
            timestamp: datetime
            category: EventCategory
            tier: EventTier
            headline: str
            symbols_affected: List[str]

            @ dataclass
            class EventScoreFactors:
                """Factors used in enhanced event scoring"""
                base_score: Decimal
                timing_multiplier: Decimal
                surprise_multiplier: Decimal
                market_condition_multiplier: Decimal
                historical_multiplier: Decimal
                volatility_adjustment: Decimal
                final_score: Decimal

                class EnhancedNewsImpactScalper(BaseStrategy):
                    """
                    Enhanced event-driven strategy with Set 1 sophistication:
                    - Sophisticated event impact scoring with multiple factors
                    - Advanced surprise factor analysis with consensus comparison
                    - Market timing multipliers based on session and volatility
                    - Tiered position sizing with dynamic risk adjustment
                    - Historical impact analysis for better predictions
                    - Advanced OTM strike selection for lottery-style plays
                    - Strict time-based exits with tier-specific holding periods
                    """

                    def __init__(self, config: Dict):
                        super().__init__(config
                        # Enhanced strategy parameters

                        # Enhanced execution parameters

                        # Enhanced risk parameters with dynamic adjustment

                        # Enhanced strike selection

                        # Enhanced event scoring configuration from Set 1
                        EventCategory.MONETARY_POLICY: {
                        EventTier.TIER_1: to_decimal("9.5"),  # RBI, Fed
                        EventTier.TIER_2: to_decimal("7.5"),  # Other central banks
                        EventTier.TIER_3: to_decimal("5.5"),  # Regional banks
                        EventTier.TIER_4: to_decimal("3.5")   # Minor policy},
                        EventCategory.EARNINGS: {
                        # Nifty50 heavyweights (RIL, TCS, INFY, HDFC
                        EventTier.TIER_1: to_decimal("8.5"),
                        EventTier.TIER_2: to_decimal("7.0"),  # Other Nifty50
                        EventTier.TIER_3: to_decimal("5.5"),  # Large caps
                        EventTier.TIER_4: to_decimal("4.0")   # Mid/small caps},
                        EventCategory.ECONOMIC_DATA: {
                        EventTier.TIER_1: to_decimal("8.5"),  # GDP, CPI, WPI
                        EventTier.TIER_2: to_decimal("7.0"),  # PMI, IIP, Trade data
                        # Employment, Infrastructure
                        EventTier.TIER_3: to_decimal("5.5"),
                        EventTier.TIER_4: to_decimal("4.0")   # Regional data},
                        EventCategory.GEOPOLITICAL: {
                        # Major conflicts, Elections
                        EventTier.TIER_1: to_decimal("8.0"),
                        EventTier.TIER_2: to_decimal("6.0"),  # Trade wars, Sanctions
                        EventTier.TIER_3: to_decimal("4.5"),  # Diplomatic tensions
                        EventTier.TIER_4: to_decimal("3.0")   # Minor events

                        # Enhanced market timing multipliers from Set 1
                        'pre_market': to_decimal("1.5"),     # Before 9:15
                        'first_hour': to_decimal("1.3"),     # 9:15-10:15
                        'mid_morning': to_decimal("1.1"),    # 10:15-11:15
                        'mid_day': to_decimal("1.0"),        # 11:15-14:30
                        'afternoon': to_decimal("0.9"),      # 14:30-15:00
                        'last_hour': to_decimal("0.8"),      # 15:00-15:30
                        'post_market': to_decimal("0.5")     # After 15:30

                        # Enhanced surprise factor configuration
                        'strong_beat': to_decimal("10.0"),    # >10% beat
                        'moderate_beat': to_decimal("5.0"),   # 5-10% beat
                        'slight_beat': to_decimal("2.0"),     # 2-5% beat
                        'inline': to_decimal("2.0"),          # Within ±2%
                        'slight_miss': to_decimal("-2.0"),    # 2-5% miss
                        'moderate_miss': to_decimal("-5.0"),  # 5-10% miss
                        'strong_miss': to_decimal("-10.0")    # >10% miss

                        'strong_beat': to_decimal("2.2"),
                        'moderate_beat': to_decimal("1.7"),
                        'slight_beat': to_decimal("1.3"),
                        'inline': to_decimal("0.7"),
                        'slight_miss': to_decimal("1.4"),     # Contrarian opportunity
                        'moderate_miss': to_decimal("1.8"),   # Strong contrarian
                        'strong_miss': to_decimal("2.5")      # Very strong contrarian

                        # Enhanced market condition multipliers
                        MarketRegime.ULTRA_HIGH_VOL: to_decimal("1.6"),
                        MarketRegime.HIGH_VOL: to_decimal("1.4"),
                        MarketRegime.TRENDING_UP: to_decimal("1.2"),
                        MarketRegime.TRENDING_DOWN: to_decimal("1.2"),
                        MarketRegime.NORMAL: to_decimal("1.0"),
                        MarketRegime.RANGE_BOUND: to_decimal("0.8"),
                        MarketRegime.LOW_VOL: to_decimal("0.6"

                        # Enhanced event tracking

                        # Enhanced performance tracking
                        'by_category': {},
                        'by_tier': {},
                        'by_surprise': {},
                        'by_timing': {},
                        'by_market_regime': {

                        # Historical impact tracking for learning

                        logger.info(f"Enhanced NewsImpactScalper initialized with sophisticated analysis"
                        async def process_enhanced_news_event(
                        self, event: EnhancedNewsEvent) -> List[Signal}:
                        """Enhanced news event processing with Set 1 sophistication"""
                        try:
                            signals=[]

                            # Enhanced duplicate processing check
                            if event.event_id in self.processed_events:
                                logger.debug(f"Event {event.event_id} already processed"
                            return signals

                            # Enhanced execution window check
                            time_since_event=(datetime.now() - event.timestamp).total_seconds(
                            if time_since_event > self.execution_window_seconds:
                                logger.info(f"Event {event.event_id} outside execution window ({time_since_event:.1f}s)"
                            return signals

                            # Enhanced strategy state checks
                            if not self.is_enabled or not self._is_trading_hours():
                            return signals

                            # Enhanced cooldown check per symbol
                            if not self._check_enhanced_symbol_cooldowns(
                                event.symbols_affected):
                            return signals

                            # Enhanced impact score calculation with Set 1 methodology
                            score_factors=await self._calculate_enhanced_impact_score(event
                            # Enhanced signal generation with sophisticated analysis
                            event_signals=await self._create_enhanced_event_signals(event, score_factors
                            signals.extend(event_signals
                            # Enhanced event tracking
                            self.processed_events.add(event.event_id
                            self._update_enhanced_cooldowns(event.symbols_affected
                            # Store scoring factors for analysis

                            logger.info(f"Generated {len(signals)} enhanced signals for event {event.event_id} "
                            f"(score: {score_factors.final_score:.2f})"
                            else:
                                logger.debug(f"Event {event.event_id} score {score_factors.final_score:.2f} "
                                f"below threshold {self.min_quality_score}"
                            return signals

                            except Exception as e:
                                logger.error(f"Error processing enhanced news event {event.event_id}: {e}"
                            return []

                            async def _calculate_enhanced_impact_score(
                            self, event: EnhancedNewsEvent) -> EventScoreFactors:
                            """Enhanced impact score calculation with Set 1 sophistication"""
                            # Get enhanced base score
                            category_scores=self.event_base_scores.get(event.category, {
                            base_score= category_scores.get(event.tier, to_decimal("5.0"
                            # Enhanced timing multiplier with more granular periods
                            timing_mult=self._get_enhanced_timing_multiplier(
                            # Enhanced surprise multiplier with sophisticated analysis
                            surprise_mult=self._calculate_enhanced_surprise_multiplier(event
                            # Enhanced market condition multiplier
                            market_mult=await self._get_enhanced_market_condition_multiplier(
                            # Enhanced historical impact multiplier (new in Set 1 style
                            historical_mult=self._get_historical_impact_multiplier(event
                            # Enhanced volatility adjustment
                            volatility_adj=await self._get_volatility_adjustment(
                            # Enhanced final score calculation
                            final_score=(base_score * timing_mult * surprise_mult *
                            market_mult * historical_mult * volatility_adj
                            score_factors=EventScoreFactors(
                            base_score=base_score,
                            timing_multiplier=timing_mult,
                            surprise_multiplier=surprise_mult,
                            market_condition_multiplier=market_mult,
                            historical_multiplier=historical_mult,
                            volatility_adjustment=volatility_adj,
                            final_score=min(final_score, to_decimal("10.0"
                            logger.debug(f"Enhanced scoring for {event.event_id}: "

                        return score_factors

                        def _get_enhanced_timing_multiplier(self) -> Decimal:
                            """Enhanced timing multiplier with more granular periods"""
                            current_time=datetime.now().time(
                            if current_time < time(9, 15):
                            return self.timing_multipliers['pre_market']
                            elif current_time < time(10, 15):
                            return self.timing_multipliers['first_hour']
                            elif current_time < time(11, 15):
                            return self.timing_multipliers['mid_morning']
                            elif current_time < time(14, 30):
                            return self.timing_multipliers['mid_day']
                            elif current_time < time(15, 0):
                            return self.timing_multipliers['afternoon']
                            elif current_time < time(15, 30):
                            return self.timing_multipliers['last_hour']
                            else:
                            return self.timing_multipliers['post_market']

                            def _calculate_enhanced_surprise_multiplier(:
                            pass
                            self, event: EnhancedNewsEvent) -> Decimal:
                            """Enhanced surprise factor calculation with Set 1 sophistication"""
                            if event.actual is None or event.consensus is None:
                                # Use historical impact if no surprise data
                                if event.historical_impact:
                                return min(event.historical_impact, to_decimal("2.0"
                            return to_decimal("1.0"
                            # Enhanced surprise percentage calculation
                            surprise_pct=to_decimal("100.0") if event.actual > 0 else to_decimal("-100.0"
                            else:
                                surprise_pct=((event.actual - event.consensus) / abs(event.consensus)) * to_decimal("100"
                                # Enhanced surprise categorization
                                surprise_category='strong_beat'
                                surprise_category='moderate_beat'
                                surprise_category='slight_beat'
                                surprise_category='strong_miss'
                                surprise_category='moderate_miss'
                                surprise_category='slight_miss'
                                else:
                                    surprise_category='inline'

                                    # Store surprise factor for direction inference

                                return self.surprise_multipliers[surprise_category]

                                async def _get_enhanced_market_condition_multiplier(self) -> Decimal:
                                """Enhanced market condition multiplier with regime detection"""
                                # This would integrate with market regime detection
                                current_vix=await self._get_current_vix(
                                regime=MarketRegime.ULTRA_HIGH_VOL
                                regime=MarketRegime.HIGH_VOL
                                regime=MarketRegime.NORMAL
                                regime=MarketRegime.LOW_VOL
                                else:
                                    regime=MarketRegime.NORMAL

                                return self.market_condition_multipliers.get(regime, to_decimal("1.0"
                                def _get_historical_impact_multiplier(:
                                pass
                                self, event: EnhancedNewsEvent) -> Decimal:
                                """Get historical impact multiplier based on past similar events"""
                                event_key=f"{event.category.value}_{event.tier.value}"

                                if event_key in self.historical_impacts:
                                    impacts=self.historical_impacts[event_key]
                                    if impacts:
                                        avg_impact=sum(impacts) / len(impacts
                                        # Normalize to multiplier range (0.5 to 1.5
                                    return to_decimal("0.5") + (avg_impact / to_decimal("10.0"
                                return to_decimal("1.0")  # Neutral if no history

                                async def _get_volatility_adjustment(self) -> Decimal:
                                """Get volatility-based adjustment factor"""
                                current_vix=await self._get_current_vix(
                            return to_decimal("1.3")  # Very high volatility amplifies impact
                        return to_decimal("1.2")  # High volatility
                    return to_decimal("1.0")  # Normal volatility
                return to_decimal("0.9")  # Low volatility
                else:
                return to_decimal("0.8")  # Very low volatility dampens impact

                async def _create_enhanced_event_signals(self, event: EnhancedNewsEvent,
                score_factors: EventScoreFactors) -> List[Signal]:
                """Enhanced signal creation with Set 1 sophistication"""
                signals=[]

                # Enhanced direction determination
                if direction is None:
                    logger.debug(f"No clear direction determined for event {event.event_id}"
                return signals

                # Enhanced position parameters based on tier
                position_params=self._get_enhanced_position_parameters(event
                # Enhanced strike selection
                spot_price=await self._get_current_spot_price(
                if not spot_price:
                return signals

                strike=self._calculate_enhanced_strike(spot_price, direction, position_params['otm_strikes']
                option_type=OptionType.CALL if direction == 'bullish' else OptionType.PUT

                # Enhanced quantity calculation
                quantity=await self._calculate_enhanced_event_quantity(
                position_params['max_risk'], spot_price, confidence

                # Enhanced signal creation
                signal=Signal(
                symbol=f"NIFTY{strike}{option_type.value}",
                option_type=option_type,
                strike=strike,
                quantity=quantity,
                metadata={
                'event_id': event.event_id,
                'event_category': event.category.value,
                'event_tier': event.tier.value,
                'headline': event.headline[:100},
                'direction': direction,
                'direction_confidence': confidence,
                'surprise_factor': event.surprise_factor,
                'surprise_pct': self._calculate_surprise_pct(event],
                'execution_delay': (datetime.now() - event.timestamp).total_seconds(),
                'max_risk': float(position_params['max_risk']),
                'otm_strikes': position_params['otm_strikes'],
                'score_factors': {
                'base_score': float(score_factors.base_score),
                'timing_mult': float(score_factors.timing_multiplier),
                'surprise_mult': float(score_factors.surprise_multiplier),
                'market_mult': float(score_factors.market_condition_multiplier),
                'historical_mult': float(score_factors.historical_multiplier),
                'volatility_adj': float(score_factors.volatility_adjustment

                signals.append(signal
                logger.info(f"Created enhanced {option_type.value} signal at strike {strike} "
                f"for event: {event.headline[:50}}... (confidence: {confidence:.2f}]"
            return signals

            def _determine_enhanced_event_direction(:
            pass
            self, event: EnhancedNewsEvent) -> Tuple[Optional[str], float]:
            """Enhanced direction determination with confidence scoring"""
            direction=None
            confidence=0.5  # Base confidence

            # Enhanced monetary policy analysis
            headline_lower=event.headline.lower(
            if any(word in headline_lower for word in [
                'cut', 'dovish', 'easing', 'stimulus']):
                direction='bullish'
                confidence=0.8
                elif any(word in headline_lower for word in ['hike', 'hawkish', 'tightening', 'restrictive']):
                    direction='bearish'
                    confidence=0.8

                    # Enhanced earnings analysis
                    if event.surprise_factor:
                        if 'beat' in event.surprise_factor:
                            direction='bullish'
                            confidence=0.9 if 'strong' in event.surprise_factor else 0.7
                            elif 'miss' in event.surprise_factor:
                                direction='bearish'
                                confidence=0.9 if 'strong' in event.surprise_factor else 0.7
                                # For inline results, check guidance or other factors
                                headline_lower=event.headline.lower(
                                if any(word in headline_lower for word in [
                                    'guidance', 'outlook', 'positive']):
                                    direction='bullish'
                                    confidence=0.6
                                    elif any(word in headline_lower for word in ['concerns', 'challenges', 'negative']):
                                        direction='bearish'
                                        confidence=0.6

                                        # Enhanced economic data analysis
                                        headline_lower=event.headline.lower(
                                        if any(word in headline_lower for word in [
                                            'better', 'beat', 'above', 'strong', 'growth']):
                                            direction='bullish'
                                            confidence=0.7
                                            elif any(word in headline_lower for word in ['worse', 'miss', 'below', 'weak', 'decline']):
                                                direction='bearish'
                                                confidence=0.7

                                                # Enhanced geopolitical analysis
                                                headline_lower=event.headline.lower(
                                                if any(word in headline_lower for word in [
                                                    'resolution', 'peace', 'agreement', 'positive']):
                                                    direction='bullish'
                                                    confidence=0.6
                                                    elif any(word in headline_lower for word in ['conflict', 'tension', 'war', 'sanctions']):
                                                        direction='bearish'
                                                        confidence=0.6

                                                        # Default direction for high-impact events without clear bias
                                                        direction='bullish'  # Default to call for major events
                                                        confidence=0.5

                                                    return direction, confidence

                                                    def _get_enhanced_position_parameters(:
                                                    pass
                                                    self, event: EnhancedNewsEvent) -> Dict:
                                                    """Get enhanced position parameters based on event tier"""
                                                return {
                                                'otm_strikes': self.tier1_otm_strikes,
                                                'max_risk': self.tier1_max_risk,
                                                'holding_time': self.tier1_holding_minutes

                                            return {
                                            'otm_strikes': self.tier2_otm_strikes,
                                            'max_risk': self.tier2_max_risk,
                                            'holding_time': self.tier2_holding_minutes

                                        return {
                                        'otm_strikes': self.tier3_otm_strikes,
                                        'max_risk': self.tier3_max_risk,
                                        'holding_time': self.tier3_holding_minutes

                                        else:  # TIER_4
                                        return {
                                        'otm_strikes': self.tier4_otm_strikes,
                                        'max_risk': self.tier4_max_risk,
                                        'holding_time': self.tier4_holding_minutes

                                        def _calculate_enhanced_strike(:
                                        pass
                                        self, spot_price: float, direction: str, otm_strikes: int) -> int:
                                        """Enhanced strike calculation with sophisticated OTM selection"""
                                        base_strike= int(round(spot_price / 50) * 50)  # Round to nearest 50

                                    return base_strike + (otm_strikes * 50)  # OTM calls
                                    else:
                                    return base_strike - (otm_strikes * 50)  # OTM puts

                                    async def _calculate_enhanced_event_quantity(self, max_risk: Decimal, spot_price: float,
                                    confidence: float) -> int:
                                    """Enhanced quantity calculation with confidence adjustment"""
                                    # Get available capital
                                    capital= await self._get_available_capital(
                                    if not capital:
                                    return 1

                                    # Base risk amount
                                    risk_amount=capital * max_risk

                                    # Adjust based on confidence
                                    confidence_multiplier=Decimal(
                                    str(confidence * 1.5))  # Scale confidence
                                    adjusted_risk=risk_amount * confidence_multiplier

                                    # Estimate option price (simplified
                                    estimated_option_price=spot_price * 0.05  # Rough estimate for OTM options

                                    quantity=int(adjusted_risk / estimated_option_price
                                return max(1, quantity
                                def _calculate_enhanced_stop_loss(:
                                pass
                                self, event: EnhancedNewsEvent, confidence: float) -> float:
                                """Enhanced stop loss calculation based on event characteristics"""
                                base_stop=0.5  # 50% stop loss

                                # Adjust based on event tier
                                base_stop=0.6  # Wider stop for major events
                                base_stop=0.3  # Tighter stop for minor events

                                # Adjust based on confidence
                                confidence_adj=1.0 + (confidence - 0.5)  # Range: 0.5 to 1.5

                            return base_stop * confidence_adj

                            def _calculate_enhanced_target(:
                            pass
                            self, event: EnhancedNewsEvent, confidence: float) -> float:
                            """Enhanced target calculation based on event characteristics"""
                            base_target=1.5  # 150% target

                            # Adjust based on event tier
                            base_target=2.5  # Higher target for major events
                            base_target=2.0
                            base_target=1.0  # Conservative target for minor events

                            # Adjust based on confidence and surprise factor
                            confidence_adj=1.0 + confidence  # Range: 1.0 to 2.0

                            if hasattr(event, 'surprise_factor') and event.surprise_factor:
                                if 'strong' in event.surprise_factor:

                                return base_target * confidence_adj

                                def _calculate_surprise_pct(:
                                pass
                                self, event: EnhancedNewsEvent) -> Optional[float}:
                                """Calculate surprise percentage for metadata"""
                                if event.actual is None or event.consensus is None:
                                return None

                            return 100.0 if event.actual > 0 else -100.0

                        return float(((event.actual - event.consensus] / abs(event.consensus)) * Decimal("100"
                        def _check_enhanced_symbol_cooldowns(:
                        pass
                        self, symbols_affected: List[str]) -> bool:
                        """Enhanced cooldown check per symbol"""
                        current_time=datetime.now(
                        cooldown_period=timedelta(seconds=300)  # 5 minutes

                        for symbol in symbols_affected:
                            if symbol in self.event_cooldowns:
                                if current_time -
                                    self.event_cooldowns[symbol] < cooldown_period:
                                    logger.debug(f"Symbol {symbol} in cooldown period"
                                return False

                            return True

                            def _update_enhanced_cooldowns(self, symbols_affected: List[str]):
                                """Update cooldown times for affected symbols"""
                                current_time=datetime.now(
                                for symbol in symbols_affected:

                                    async def _get_current_vix(self) -> float:
                                    """Get current VIX value"""
                                    # This would integrate with actual market data
                                    # For now, return a simulated value
                                return 18.0

                                async def _get_current_spot_price(self) -> Optional[float]:
                                """Get current spot price"""
                                # This would integrate with actual market data
                                # For now, return a simulated value
                            return 24000.0

                            async def _get_available_capital(self) -> Optional[float]:
                            """Get available capital for trading"""
                            # This would integrate with actual capital management
                            # For now, return a simulated value
                        return 1000000.0  # 10 lakhs

                        # Standard strategy interface methods

                        async def generate_signals(self, market_data: Dict) -> List[Signal]:
                        """Standard signal generation - primarily uses process_enhanced_news_event"""
                        signals=[]

                        # Check for scheduled events
                        scheduled_signals=await self._check_enhanced_scheduled_events(market_data
                        signals.extend(scheduled_signals
                    return signals

                    async def _check_enhanced_scheduled_events(
                    self, market_data: Dict) -> List[Signal]:
                    """Enhanced scheduled event checking with calendar integration"""
                    signals=[]
                    current_time=datetime.now(
                    # Enhanced scheduled event detection
                    # This would integrate with an economic calendar API

                    # Example: RBI policy days (enhanced detection
                    event=EnhancedNewsEvent(
                    event_id=f"RBI_POLICY_{current_time.date()}",
                    timestamp=current_time,
                    category=EventCategory.MONETARY_POLICY,
                    tier=EventTier.TIER_1,
                    headline="RBI Monetary Policy Decision",
                    symbols_affected=["NIFTY", "BANKNIFTY"],
                    impact_magnitude="HIGH",
                    market_sensitivity=to_decimal("9.0"),
                    metadata={'scheduled': True, 'source': 'calendar'
                    event_signals= await self.process_enhanced_news_event(event
                    signals.extend(event_signals
                    # Example: Major earnings (enhanced detection
                    earnings_events=self._get_scheduled_earnings(current_time
                    for earnings_event in earnings_events:
                        event_signals=await self.process_enhanced_news_event(earnings_event
                        signals.extend(event_signals
                    return signals

                    def _is_rbi_policy_day(self, current_time: datetime) -> bool:
                        """Check if current day is an RBI policy day"""
                        # Simplified implementation - would use actual RBI calendar
                        # RBI typically meets every 2 months

                        def _get_scheduled_earnings(:
                        pass
                        self, current_time: datetime) -> List[EnhancedNewsEvent}:
                        """Get scheduled earnings events for today"""
                        # This would integrate with earnings calendar
                        earnings_events=[]

                        # Simplified example
                        # Example: TCS earnings
                        event=EnhancedNewsEvent(
                        event_id=f"TCS_EARNINGS_{current_time.date()}",
                        timestamp=current_time.replace(hour=16, minute=0),
                        category=EventCategory.EARNINGS,
                        tier=EventTier.TIER_1,
                        headline="TCS Q3 Earnings Results",
                        symbols_affected=["NIFTY", "TCS"],
                        impact_magnitude="HIGH",
                        market_sensitivity=to_decimal("8.5"),
                        metadata={'scheduled': True, 'company': 'TCS'
                        earnings_events.append(event
                    return earnings_events

                    def update_performance(self, trade_result: Dict):
                        """Enhanced performance tracking"""
                        metadata=trade_result.get('metadata', {
                        pnl= trade_result.get('pnl', 0
                        # Track by multiple dimensions
                        category=metadata.get('event_category'
                        tier=metadata.get('event_tier'
                        surprise=metadata.get('surprise_factor', 'unknown'
                        direction=metadata.get('direction', 'unknown'
                        # Update category performance
                        if category:
                            if category not in self.event_performance['by_category'}:
                                if pnl > 0:

                                    # Update tier performance
                                    if tier:
                                        if tier not in self.event_performance['by_tier']:
                                            if pnl > 0:

                                                # Update surprise factor performance
                                                if surprise not in self.event_performance['by_surprise']:
                                                    if pnl > 0:

                                                        # Update historical impacts for learning
                                                        event_category=metadata.get('event_category'
                                                        event_tier=metadata.get('event_tier'
                                                        if event_category and event_tier:
                                                            event_key=f"{event_category}_{event_tier}"
                                                            if event_key not in self.historical_impacts:

                                                                # Store impact score (normalized PnL
                                                                impact_score=min(max(pnl / 1000, 0), 10)  # Normalize to 0-10 scale
                                                                self.historical_impacts[event_key].append(impact_score
                                                                # Keep only recent history
                                                                if len(self.historical_impacts[event_key]) > 50:

                                                                    super().update_performance(trade_result
                                                                    def get_strategy_metrics(self) -> Dict:
                                                                        """Enhanced strategy metrics"""
                                                                        base_metrics=super().get_strategy_metrics(
                                                                        # Enhanced event performance metrics
                                                                        enhanced_metrics={
                                                                        'processed_events': len(self.processed_events),
                                                                        'event_performance': self.event_performance,
                                                                        'active_cooldowns': len([
                                                                        symbol for symbol, last_time in self.event_cooldowns.items(
                                                                        if (datetime.now(} - last_time].total_seconds() < 300}),
                                                                            'scoring_accuracy': self._calculate_scoring_accuracy(),
                                                                            'historical_learning': {
                                                                            event_type: {
                                                                            'sample_count': len(impacts),
                                                                            'avg_impact': sum(impacts) / len(impacts) if impacts else 0,
                                                                            'impact_consistency': self._calculate_impact_consistency(impacts

                                                                            for event_type, impacts in self.historical_impacts.items(},
                                                                                'configuration': {
                                                                                'tier_risk_allocation': {
                                                                                'tier_1': float(self.tier1_max_risk),
                                                                                'tier_2': float(self.tier2_max_risk),
                                                                                'tier_3': float(self.tier3_max_risk),
                                                                                'tier_4': float(self.tier4_max_risk},
                                                                                'holding_periods': {
                                                                                'tier_1': self.tier1_holding_minutes,
                                                                                'tier_2': self.tier2_holding_minutes,
                                                                                'tier_3': self.tier3_holding_minutes,
                                                                                'tier_4': self.tier4_holding_minutes},
                                                                                'strike_selection': {
                                                                                'tier_1': self.tier1_otm_strikes,
                                                                                'tier_2': self.tier2_otm_strikes,
                                                                                'tier_3': self.tier3_otm_strikes,
                                                                                'tier_4': self.tier4_otm_strikes

                                                                                base_metrics.update(enhanced_metrics
                                                                            return base_metrics

                                                                            def _calculate_scoring_accuracy(self) -> Dict:
                                                                                """Calculate accuracy of event scoring"""
                                                                                if not self.event_score_history:
                                                                                return {'sample_size': 0
                                                                                # This would correlate predicted scores with actual outcomes
                                                                                # For now, return basic statistics
                                                                                scores= [float(factors.final_score} for factors in self.event_score_history.values(]
                                                                            return {
                                                                            'sample_size': len(scores),
                                                                            'avg_score': sum(scores) / len(scores) if scores else 0,
                                                                            'score_range': {'min': min(scores), 'max': max(scores)} if scores else None,
                                                                            'low_score_events': len([s for s in scores if s < 6.0]

                                                                            def _calculate_impact_consistency(self, impacts: List[float]) -> float:
                                                                                """Calculate consistency of impact predictions"""
                                                                                if len(impacts) < 2:
                                                                                return 0.0

                                                                                mean_impact=sum(impacts) / len(impacts
                                                                                variance=sum((x - mean_impact) ** 2 for x in impacts) / len(impacts
                                                                                std_dev=variance ** 0.5

                                                                                if mean_impact > 0:
                                                                                return max(0, 1 - (std_dev / mean_impact
                                                                            return 0.0

                                                                            def reset_daily_metrics(self):
                                                                                """Enhanced daily metrics reset"""
                                                                                super().reset(
                                                                                # Reset enhanced daily tracking
                                                                                self.processed_events.clear(
                                                                                self.event_cooldowns.clear(
                                                                                # Keep scoring history for learning but limit size
                                                                                if len(self.event_score_history) > 200:
                                                                                    # Keep only recent history
                                                                                    recent_events=list(self.event_score_history.items())[-100:]

                                                                                    # Reset daily performance tracking
                                                                                    for category in ['by_category', 'by_tier',
                                                                                        'by_surprise', 'by_timing', 'by_market_regime']:
                                                                                        for key in self.event_performance[category]:

                                                                                            logger.info("Enhanced News Impact Scalper daily metrics reset"
                                                                                            def _is_trading_hours(self) -> bool:
                                                                                                """Check if within trading hours"""
                                                                                                current_time=datetime.now().time(

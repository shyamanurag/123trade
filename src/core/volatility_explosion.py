async def _process_volatility_trigger(self, trigger: VolatilityTrigger,
market_context: Dict) -> List[Signal]:
    """Process enhanced volatility trigger into trading signals"""
    try:
        signals = []

        # Enhanced quality scoring for the trigger
        quality_score = await self._calculate_enhanced_trigger_quality(trigger, market_context)
        if quality_score < float(self.config.min_quality_score):
            logger.debug(f"Trigger {trigger.trigger_type} quality {quality_score:.2f} below threshold")
            return signals

        # Enhanced position sizing based on regime and trigger
        position_multiplier = await self._calculate_position_multiplier(trigger, market_context)
        # Enhanced time stop calculation
        time_stop_minutes = await self._calculate_time_stop(trigger, market_context)
        # Create enhanced straddle signals
        straddle_signals = await self._create_enhanced_straddle_signals(
            trigger, market_context, quality_score, position_multiplier, time_stop_minutes
        )
        signals.extend(straddle_signals)
        # Record trigger for analysis
        self.recent_triggers.append(trigger)
        return signals
    except Exception as e:
        logger.error(f"Error processing volatility trigger: {e}")
        return []

async def _calculate_enhanced_trigger_quality(self, trigger: VolatilityTrigger,
market_context: Dict) -> float:
    """Enhanced quality scoring for volatility triggers"""
    base_score = float(self.config.base_quality_score)
    # Trigger type base adjustments
    if trigger.trigger_type == "CLUSTER":
        base_score += 0.5  # Clustering is sophisticated
    elif trigger.trigger_type == "MORNING_EXPLOSION":
        base_score += 1.0  # Morning explosions are high-quality
    elif trigger.trigger_type == "VIX_SURGE":
        base_score += 0.8  # VIX surges are reliable

    # Intensity bonus
    intensity_bonus = min(float(trigger.intensity - Decimal("1")), 2.0)
    base_score += intensity_bonus

    # Confidence bonus
    confidence_bonus = float(trigger.confidence) * 1.5
    base_score += confidence_bonus

    # Supporting factors bonus
    factor_bonus = len(trigger.supporting_factors) * 0.3
    base_score += factor_bonus

    # Regime bonus
    regime = self.volatility_regime.regime
    if regime == "EXTREME":
        base_score += 1.5
    elif regime == "HIGH":
        base_score += 1.0
    elif regime == "ELEVATED":
        base_score += 0.5

    # Volume support bonus
    volume_ratio = market_context['volume_ratio']
    if volume_ratio >= Decimal("3.0"):
        base_score += 1.0
    elif volume_ratio >= Decimal("2.0"):
        base_score += 0.7
    elif volume_ratio >= Decimal("1.5"):
        base_score += 0.4

    # VIX level bonus
    current_vix = market_context['current_vix']
    if current_vix >= self.config.vix_threshold_extreme:
        base_score += 1.0
    elif current_vix >= self.config.vix_threshold_high:
        base_score += 0.6

    # Time of day adjustment
    current_hour = datetime.now().hour
    if 9 <= current_hour <= 11:
        base_score += 0.5  # Morning premium
    elif 14 <= current_hour <= 15:
        base_score -= 0.3  # Late session penalty

    # Regime persistence bonus
    if self.volatility_regime.regime_persistence >= 3:
        base_score += 0.4  # Sustained regime

    return min(base_score, 10.0)

async def _calculate_position_multiplier(self, trigger: VolatilityTrigger,
market_context: Dict) -> Decimal:
    """Calculate position size multiplier based on conditions"""
    base_multiplier = Decimal("1.0")
    current_vix = market_context['current_vix']

    # VIX-based adjustment
    if current_vix >= self.config.vix_threshold_extreme:
        base_multiplier = self.config.position_reduction_extreme_vix
    elif current_vix >= self.config.vix_threshold_high:
        base_multiplier = self.config.position_reduction_high_vix

    # Trigger confidence adjustment
    confidence_adj = Decimal("0.7") + (trigger.confidence * Decimal("0.6"))  # Range: 0.7 to 1.3
    base_multiplier *= confidence_adj

    # Regime adjustment
    regime = self.volatility_regime.regime
    if regime == "EXTREME":
        # Reduce size in extreme conditions
        base_multiplier *= Decimal("0.8")
    elif regime == "LOW":
        # Increase size in low volatility
        base_multiplier *= Decimal("1.2")
    return min(base_multiplier, Decimal("1.5"))  # Cap at 1.5x

async def _calculate_time_stop(self, trigger: VolatilityTrigger, market_context: Dict) -> int:
    """Calculate time stop based on trigger and market conditions"""
    base_time=self.config.time_stop_minutes_normal
    current_vix=market_context['current_vix']

    # Adjust based on VIX level
    if current_vix >= self.config.vix_threshold_extreme:
        base_time=self.config.time_stop_minutes_extreme

    # Adjust based on trigger type
    if trigger.trigger_type == "MORNING_EXPLOSION":
        base_time=int(base_time * 1.2)  # Longer for morning explosions
    elif trigger.trigger_type == "VIX_SURGE":
        base_time=int(base_time * 0.8)  # Shorter for VIX surges

    # Adjust based on intensity
    intensity_factor=float(trigger.intensity)
    if intensity_factor > 2.0:
        base_time=int(base_time * 1.3)  # Longer for intense moves

    return max(base_time, 10)  # Minimum 10 minutes

async def _create_enhanced_straddle_signals(self, trigger: VolatilityTrigger,
market_context: Dict, quality_score: float, position_multiplier: Decimal, time_stop_minutes: int) -> List[Signal]:
    """Create enhanced straddle signals with sophisticated parameters"""
    signals = []
    spot_price = float(market_context['spot_price'])
    # Enhanced strike selection
    atm_strike = get_atm_strike(spot_price)
    # Enhanced quantity calculation
    base_quantity = self._calculate_quantity({'symbol': 'NIFTY'})
    adjusted_quantity = int(base_quantity * float(position_multiplier))
    # Half size per leg, minimum 1
    adjusted_quantity = max(1, adjusted_quantity // 2)
    # Enhanced premium estimation and targets
    estimated_premium = spot_price * 0.04  # 4% of spot for ATM options

    # Dynamic targets based on trigger characteristics
    if trigger.trigger_type == "MORNING_EXPLOSION":
        stop_loss_pct = 0.40  # Wider stops for morning
        profit_target_pct = 2.00  # Higher targets for morning
    elif trigger.trigger_type == "CLUSTER":
        stop_loss_pct = 0.45  # Wider stops for clustering
        profit_target_pct = 1.80  # Good targets for clustering
    elif trigger.trigger_type == "VIX_SURGE":
        stop_loss_pct = 0.35  # Tighter stops for VIX
        profit_target_pct = 1.60  # Moderate targets for VIX
    else:  # INTRADAY_SPIKE
        stop_loss_pct = 0.50  # Widest stops for spikes
        profit_target_pct = 1.50  # Conservative targets for spikes

    # Enhanced metadata
    enhanced_metadata = {
        'trigger_type': trigger.trigger_type,
        'trigger_intensity': float(trigger.intensity),
        'trigger_confidence': float(trigger.confidence),
        'supporting_factors': trigger.supporting_factors,
        'volatility_regime': self.volatility_regime.regime,
        'regime_persistence': self.volatility_regime.regime_persistence,
        'clustering_score': float(self.volatility_regime.clustering_score),
        'volatility_trend': self.volatility_regime.volatility_trend,
        'current_vix': float(market_context['current_vix']),
        'volume_ratio': float(market_context['volume_ratio']),
        'position_multiplier': float(position_multiplier),
        'time_stop_minutes': time_stop_minutes,
        'trigger_time': trigger.trigger_time.isoformat()
    }

    # Call leg
    call_signal = Signal(
        strategy_name='enhanced_volatility_explosion',
        symbol=f"NIFTY{atm_strike}CE",
        option_type=OptionType.CALL,
        strike=atm_strike,
        action=OrderSide.BUY,
        quality_score=quality_score,
        quantity=adjusted_quantity,
        entry_price=estimated_premium,
        stop_loss_percent=stop_loss_pct,
        target_percent=profit_target_pct,
        time_stop=datetime.now() + timedelta(minutes=time_stop_minutes),
        metadata={**enhanced_metadata, 'leg': 'call', 'pair_symbol': f"NIFTY{atm_strike}PE"}
    )
    signals.append(call_signal)

    # Put leg
    put_signal = Signal(
        strategy_name='enhanced_volatility_explosion',
        symbol=f"NIFTY{atm_strike}PE",
        option_type=OptionType.PUT,
        strike=atm_strike,
        action=OrderSide.BUY,
        quality_score=quality_score,
        quantity=adjusted_quantity,
        entry_price=estimated_premium,
        stop_loss_percent=stop_loss_pct,
        target_percent=profit_target_pct,
        time_stop=datetime.now() + timedelta(minutes=time_stop_minutes),
        metadata={**enhanced_metadata, 'leg': 'put', 'pair_symbol': f"NIFTY{atm_strike}CE"}
    )
    signals.append(put_signal)

    return signals

async def _filter_and_rank_signals(self, signals: List[Signal], market_context: Dict) -> List[Signal]:
    """Enhanced signal filtering and ranking"""
    if not signals:
        return signals

    # Filter by quality threshold
    qualified_signals=[
        s for s in signals if s.quality_score >= float(self.config.min_quality_score)]

    # Rank by quality score and trigger characteristics
    def signal_rank_key(signal):
        metadata=signal.metadata
        base_score=signal.quality_score

        # Bonus for high-intensity triggers
        intensity_bonus=metadata.get('trigger_intensity', 0) * 2

        # Bonus for strong supporting factors
        factor_bonus=len(metadata.get('supporting_factors', [])) * 0.5

        # Bonus for confidence
        confidence_bonus=metadata.get('trigger_confidence', 0) * 3

        # Penalty for extreme VIX (too volatile)
        vix_penalty=0
        current_vix=metadata.get('current_vix', 20)
        if current_vix > 35:
            vix_penalty=(current_vix - 35) * 0.1

        return base_score + intensity_bonus + factor_bonus + confidence_bonus - vix_penalty

    # Sort by ranking key
    qualified_signals.sort(key=signal_rank_key, reverse=True)
    # Limit to top signals to avoid overtrading
    max_signals=4  # Maximum 2 straddles (4 legs) per trigger event
    return qualified_signals[:max_signals]

# Helper methods

def _check_enhanced_constraints(self) -> bool:
    """Check enhanced strategy constraints"""
    # Cooldown check
    if self.last_signal_time:
        time_since_last=(datetime.now() - self.last_signal_time).total_seconds()
        if time_since_last < self.config.signal_cooldown_seconds:
            return False

    # Daily signal limit
    if self.daily_signal_count >= self.max_daily_signals:
        logger.debug(f"Daily signal limit reached: {self.daily_signal_count}")
        return False

    return True

def _update_signal_tracking(self, signals: List[Signal]):
    """Update signal tracking state"""
    if signals:
        self.last_signal_time=datetime.now()
        self.daily_signal_count += len(signals)

async def _calculate_enhanced_average_volume(self, recent_bars: List) -> Decimal:
    """Calculate enhanced average volume with trend weighting"""
    try:
        if len(recent_bars) < 20:
            return Decimal("0")
        volumes = [to_decimal(str(bar.get('volume', 0))) for bar in recent_bars[-20:]]
        volumes = [v for v in volumes if v > 0]
        if not volumes:
            return Decimal("0")
        # Use EMA for more responsive average
        ema_volume = volumes[0]
        alpha = Decimal("0.1")  # EMA smoothing factor
        for volume in volumes[1:]:
            ema_volume = alpha * volume + (Decimal("1") - alpha) * ema_volume
        return ema_volume
    except Exception as e:
        logger.error(f"Error calculating enhanced average volume: {e}")
        return Decimal("0")

async def _calculate_enhanced_daily_atr(self, recent_bars: List) -> Decimal:
    """Calculate enhanced daily ATR with multiple timeframes"""
    try:
        if len(recent_bars) < 20:
            return Decimal("100")  # Default ATR
        atr_values = []
        for i in range(1, min(20, len(recent_bars))):
            current_bar = recent_bars[i]
            previous_bar = recent_bars[i-1]
            high = to_decimal(str(current_bar.get('high', 0)))
            low = to_decimal(str(current_bar.get('low', 0)))
            prev_close = to_decimal(str(previous_bar.get('close', 0)))
            if high > 0 and low > 0 and prev_close > 0:
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                true_range = max(tr1, tr2, tr3)
                atr_values.append(true_range)
        if atr_values:
            # Use EMA for ATR calculation
            ema_atr = atr_values[0]
            alpha = Decimal("0.1")
            for atr in atr_values[1:]:
                ema_atr = alpha * atr + (Decimal("1") - alpha) * ema_atr
            return ema_atr
        return Decimal("100")
    except Exception as e:
        logger.error(f"Error calculating enhanced daily ATR: {e}")
        return Decimal("100")

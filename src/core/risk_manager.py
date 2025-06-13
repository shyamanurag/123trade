# core/risk_manager.py
"""
Complete Risk Manager with Advanced Risk Analytics and Greeks Integration
Implements portfolio risk management, position sizing, and risk monitoring
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import json
import redis.asyncio as redis

from ..models import Signal, Position, OptionType
from ..events import EventBus, EventType, TradingEvent
from .position_tracker import PositionTracker
from .greeks_risk_manager import GreeksRiskManager

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Container for risk metrics"""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0

    @dataclass
    class PositionRiskMetrics:
        """Risk metrics for individual position"""
        delta: float = 0.0
        gamma: float = 0.0
        theta: float = 0.0
        vega: float = 0.0
        rho: float = 0.0

    class RiskState:
        """Current risk state of the portfolio"""
        def __init__(self):
            # Greeks state
            self.delta = 0.0
            self.gamma = 0.0
            self.theta = 0.0
            self.vega = 0.0
            self.rho = 0.0

    class PortfolioHeatMap:
        """Track portfolio concentration and heat levels"""
        def __init__(self):
            self.heat_scores = {}
            self.symbol_exposure = defaultdict(float)
            self.time_concentration = defaultdict(list)

        def update_exposure(self, position: Position):
            """Update exposure tracking"""
            symbol_base = self._get_base_symbol(position.symbol)
            position_value = position.quantity * position.current_price
            self.time_concentration[datetime.now().hour].append(position_value)
            # Calculate heat score
            self._calculate_heat_scores()

        def remove_exposure(self, position: Position):
            """Remove position from exposure tracking"""
            symbol_base = self._get_base_symbol(position.symbol)
            position_value = position.quantity * position.entry_price
            # Recalculate heat scores
            self._calculate_heat_scores()

        def get_heat_level(self, symbol: str) -> float:
            """Get heat level for symbol or overall"""
            if symbol:
                return self.heat_scores.get(self._get_base_symbol(symbol), 0.0)
            return max(self.heat_scores.values()) if self.heat_scores else 0.0

        def can_add_position(self, symbol: str, value: float, total_capital: float) -> bool:
            """Check if we can add position without exceeding concentration"""
            symbol_base = self._get_base_symbol(symbol)
            current_concentration = self.symbol_exposure[symbol_base] / total_capital
            new_concentration = (self.symbol_exposure[symbol_base] + value) / total_capital
            return new_concentration <= 0.2  # Max 20% concentration

        def _calculate_heat_scores(self):
            """Calculate heat scores for all symbols"""
            total_exposure = sum(self.symbol_exposure.values())
            if total_exposure > 0:
                for symbol, exposure in self.symbol_exposure.items():
                    concentration = exposure / total_exposure
                    # Heat score increases exponentially as we approach max concentration
                    self.heat_scores[symbol] = concentration * 100
            else:
                self.heat_scores.clear()

        def _get_base_symbol(self, symbol: str) -> str:
            """Extract base symbol from option symbol"""
            if 'BANKNIFTY' in symbol:
                return 'BANKNIFTY'
            elif 'NIFTY' in symbol:
                return 'NIFTY'
            elif 'FINNIFTY' in symbol:
                return 'FINNIFTY'
            return symbol.split('_')[0] if '_' in symbol else symbol

class ValueAtRiskCalculator:
    """Calculate portfolio Value at Risk (VaR) and CVaR"""

    def __init__(self):
        self.returns_history = []
        self.position_returns = defaultdict(list)

    def add_return(self, daily_return: float, position_returns: Optional[Dict[str, float]] = None):
        """Add daily return data"""
        self.returns_history.append(daily_return)
        if position_returns:
            for position_id, ret in position_returns.items():
                self.position_returns[position_id].append(ret)

    def calculate_portfolio_var(self, portfolio_value: float, time_horizon: float, confidence_level: float) -> Tuple[float, float]:
        """Calculate VaR and CVaR for portfolio

        Returns:
        Tuple of (VaR, CVaR) in currency terms
        """
        if len(self.returns_history) < 20:  # Need minimum history
            return 0.0, 0.0

        returns = np.array(self.returns_history)
        # Scale returns for time horizon (square root of time)
        scaled_returns = returns * np.sqrt(time_horizon)
        # Calculate VaR (percentile method)
        var_percentile = (1 - confidence_level) * 100
        var_return = np.percentile(scaled_returns, var_percentile)
        var_amount = abs(var_return * portfolio_value)
        # Calculate CVaR (expected shortfall)
        cvar_returns = scaled_returns[scaled_returns <= var_return]
        cvar_return = np.mean(cvar_returns) if len(cvar_returns) > 0 else var_return
        cvar_amount = abs(cvar_return * portfolio_value)
        return var_amount, cvar_amount

    def calculate_position_var(self, position: Position, portfolio_var: float, confidence_level: float = 0.95) -> float:
        """Calculate VaR for individual position"""
        position_id = position.position_id

        if position_id not in self.position_returns or len(self.position_returns[position_id]) < 5:
            # Use portfolio VaR scaled by position size
            position_value = position.quantity * position.current_price
            return portfolio_var * 0.5  # Conservative estimate

        # Calculate from position-specific returns
        returns = np.array(self.position_returns[position_id])
        var_percentile = (1 - confidence_level) * 100
        var_return = np.percentile(returns, var_percentile)
        position_value = position.quantity * position.current_price
        return abs(var_return * position_value)

class CorrelationTracker:
    """Track and analyze correlations between positions"""

    def __init__(self):
        self.price_history = defaultdict(list)
        self.correlation_matrix = pd.DataFrame()
        self.last_update = None

    def update_price(self, symbol: str, price: float):
        """Update price history for symbol"""
        self.price_history[symbol].append(price)
        # Update correlation matrix periodically
        if (not self.last_update or
            (datetime.now() - self.last_update).seconds > 300):  # Every 5 minutes
            self._update_correlation_matrix()

    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        if symbol1 in self.correlation_matrix.index and symbol2 in self.correlation_matrix.columns:
            return self.correlation_matrix.loc[symbol1, symbol2]
        return 0.0

    def get_portfolio_correlation_risk(self, positions: List[Position]) -> float:
        """Calculate overall portfolio correlation risk"""
        if len(positions) < 2:
            return 0.0

        # Get unique symbols
        symbols = list(set(self._get_base_symbol(p.symbol) for p in positions))
        if len(symbols) < 2:
            return 0.0

        # Calculate average pairwise correlation
        correlations = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                corr = self.get_correlation(symbols[i], symbols[j])
                correlations.append(abs(corr))
        if correlations:
            avg_correlation = np.mean(correlations)
            # High correlation increases risk
            return min(avg_correlation * 100, 100)  # Scale to 0-100
        return 0.0

    def _update_correlation_matrix(self):
        """Update correlation matrix from price history"""
        if len(self.price_history) < 2:
            return

        # Convert price histories to returns
        returns_data = {}
        for symbol, prices in self.price_history.items():
            if len(prices) > 1:
                returns = np.diff(prices) / prices[:-1]
                returns_data[symbol] = returns

        if len(returns_data) < 2:
            return

        # Create correlation matrix
        df = pd.DataFrame(returns_data)
        self.correlation_matrix = df.corr()
        self.last_update = datetime.now()

    def _get_base_symbol(self, symbol: str) -> str:
        """Extract base symbol from option symbol"""
        if 'BANKNIFTY' in symbol:
            return 'BANKNIFTY'
        elif 'NIFTY' in symbol:
            return 'NIFTY'
        elif 'FINNIFTY' in symbol:
            return 'FINNIFTY'
        return symbol.split('_')[0] if '_' in symbol else symbol

class DynamicPositionSizer:
    """Advanced position sizing with multiple methods"""

    def __init__(self):
        self.strategy_stats = defaultdict(lambda: {
            'wins': 0,
            'losses': 0,
            'total_win': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        })
        self.base_size = 0.02
        self.max_position_size = 1000000  # Assuming a default max_position_size
        self.kelly_fraction = 0.25

    def calculate_fixed_fractional(self, capital: float, risk_score: float) -> float:
        """Fixed fractional position sizing adjusted for risk"""
        # Reduce size as risk increases
        risk_multiplier = 1.0 - (risk_score / 100) * 0.5  # Max 50% reduction
        position_size = capital * self.base_size * risk_multiplier
        return min(position_size, capital * self.max_position_size)

    def calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float, capital: float) -> float:
        """Kelly criterion position sizing"""
        p = win_rate
        q = 1 - win_rate
        b = abs(avg_win / avg_loss)
        kelly_percentage = (p * b - q) / b

        # Apply fractional Kelly for safety
        safe_kelly = kelly_percentage * self.kelly_fraction

        # Ensure within bounds
        safe_kelly = max(0, min(safe_kelly, self.max_position_size))
        return capital * safe_kelly

    def update_strategy_stats(self, strategy: str, trade_result: Dict):
        """Update strategy statistics with trade result"""
        stats = self.strategy_stats[strategy]
        if trade_result['pnl'] > 0:
            stats['wins'] += 1
            stats['total_win'] += trade_result['pnl']
            stats['avg_win'] = stats['total_win'] / stats['wins']
        else:
            stats['losses'] += 1
            stats['total_loss'] += abs(trade_result['pnl'])
            stats['avg_loss'] = stats['total_loss'] / stats['losses']

        total_trades = stats['wins'] + stats['losses']
        stats['win_rate'] = stats['wins'] / total_trades if total_trades > 0 else 0.0

class RiskManager:
    """Complete Risk Manager with Advanced Risk Analytics and Greeks Integration
    Implements portfolio risk management, position sizing, and risk monitoring
    """

    def __init__(self, config: Dict, position_tracker: PositionTracker, event_bus: EventBus):
        self.config = config
        self.position_tracker = position_tracker
        self.event_bus = event_bus
        self.redis_client = redis.Redis(host=config['redis']['host'], port=config['redis']['port'])
        
        # Risk components
        self.var_calculator = ValueAtRiskCalculator()
        self.correlation_tracker = CorrelationTracker()
        self.portfolio_heat = RiskMetrics.PortfolioHeatMap()
        self.position_sizer = DynamicPositionSizer()
        self.greeks_manager = GreeksRiskManager(config)

        # Risk state
        self.risk_state = RiskMetrics.RiskState()
        self.risk_regime = "NORMAL"  # NORMAL, HIGH, EXTREME
        self.risk_regime_multipliers = {
            "NORMAL": 1.0,
            "HIGH": 0.8,
            "EXTREME": 0.5
        }
        
        # User risk tracking
        self.user_risk_limits = {}
        self.user_daily_risk = {}
        self.user_hard_stops = set()

        # Setup event handlers
        self._setup_event_handlers()

    async def initialize_user_risk(self, user_id: str, capital: float) -> bool:
        """Initialize risk tracking for a new user"""
        try:
            # Set default risk limits
            self.user_risk_limits[user_id] = RiskLimits(
                max_position_size=capital * 0.1,  # 10% of capital
                max_daily_loss=capital * 0.02,    # 2% daily loss
                max_drawdown=capital * 0.05,      # 5% max drawdown
                risk_per_trade=0.02,              # 2% per trade
                max_positions=10,
                max_correlation=0.7,
                max_concentration=0.2,
                vix_threshold_high=25,
                vix_threshold_extreme=35
            )
            
            # Initialize daily risk tracking
            self.user_daily_risk[user_id] = {
                'opening_capital': capital,
                'current_capital': capital,
                'daily_pnl': 0.0,
                'max_drawdown': 0.0,
                'positions': set()
            }
            
            return True
        except Exception as e:
            logger.error(f"Error initializing user risk: {str(e)}")
            return False

    async def check_order_risk(self, user_id: str, order_params: Dict) -> Dict:
        """Check if order meets risk parameters"""
        try:
            # Get user risk limits
            risk_limits = await self.get_user_risk_limits(user_id)
            if not risk_limits:
                return {'allowed': False, 'reason': 'User risk limits not found'}
            
            # Check if user is hard stopped
            if await self._is_user_hard_stopped(user_id):
                return {'allowed': False, 'reason': 'User is hard stopped'}
            
            # Check position size
            position_value = order_params['quantity'] * order_params['price']
            if position_value > risk_limits.max_position_size:
                return {'allowed': False, 'reason': 'Position size exceeds limit'}
            
            # Check correlation
            if not await self._check_correlation(user_id, order_params['symbol'], risk_limits.max_correlation):
                return {'allowed': False, 'reason': 'Correlation risk too high'}
            
            # Check concentration
            if not await self._check_concentration(user_id, order_params['symbol'], risk_limits.max_concentration):
                return {'allowed': False, 'reason': 'Concentration risk too high'}
            
            # Check daily loss limit
            daily_risk = await self.get_user_daily_risk(user_id)
            if daily_risk and daily_risk['daily_pnl'] < -risk_limits.max_daily_loss:
                return {'allowed': False, 'reason': 'Daily loss limit reached'}
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Error checking order risk: {str(e)}")
            return {'allowed': False, 'reason': f'Error: {str(e)}'}

    async def update_daily_risk(self, user_id: str, pnl: float, capital: float):
        """Update daily risk metrics for user"""
        try:
            if user_id not in self.user_daily_risk:
                return
                
            daily_risk = self.user_daily_risk[user_id]
            daily_risk['daily_pnl'] += pnl
            daily_risk['current_capital'] = capital
            
            # Update max drawdown
            drawdown = (daily_risk['opening_capital'] - capital) / daily_risk['opening_capital']
            daily_risk['max_drawdown'] = max(daily_risk['max_drawdown'], drawdown)
            
            # Check for hard stop
            risk_limits = await self.get_user_risk_limits(user_id)
            if risk_limits and (
                daily_risk['daily_pnl'] < -risk_limits.max_daily_loss or
                drawdown > risk_limits.max_drawdown
            ):
                await self._trigger_hard_stop(user_id)
                
        except Exception as e:
            logger.error(f"Error updating daily risk: {str(e)}")

    async def reset_daily_risk(self, user_id: str):
        """Reset daily risk metrics for user"""
        try:
            if user_id not in self.user_daily_risk:
                return
                
            daily_risk = self.user_daily_risk[user_id]
            daily_risk['opening_capital'] = daily_risk['current_capital']
            daily_risk['daily_pnl'] = 0.0
            daily_risk['max_drawdown'] = 0.0
            daily_risk['positions'].clear()
            
        except Exception as e:
            logger.error(f"Error resetting daily risk: {str(e)}")

    async def get_user_risk_limits(self, user_id: str) -> Optional[Dict]:
        """Get risk limits for user"""
        return self.user_risk_limits.get(user_id)

    async def get_user_daily_risk(self, user_id: str) -> Optional[Dict]:
        """Get daily risk metrics for user"""
        return self.user_daily_risk.get(user_id)

    async def _check_correlation(self, user_id: str, symbol: str, max_correlation: float) -> bool:
        """Check if new position would exceed correlation limits"""
        try:
            daily_risk = await self.get_user_daily_risk(user_id)
            if not daily_risk:
                return True
                
            # Get existing positions
            positions = daily_risk['positions']
            if not positions:
                return True
                
            # Check correlation with each existing position
            for pos in positions:
                correlation = self.correlation_tracker.get_correlation(symbol, pos)
                if abs(correlation) > max_correlation:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking correlation: {str(e)}")
            return False

    async def _check_concentration(self, user_id: str, symbol: str, max_concentration: float) -> bool:
        """Check if new position would exceed concentration limits"""
        try:
            daily_risk = await self.get_user_daily_risk(user_id)
            if not daily_risk:
                return True
                
            # Get total portfolio value
            total_value = daily_risk['current_capital']
            if total_value <= 0:
                return True
                
            # Get position value
            position_value = self.position_tracker.get_position_value(symbol)
            if not position_value:
                return True
                
            # Check concentration
            concentration = position_value / total_value
            return concentration <= max_concentration
            
        except Exception as e:
            logger.error(f"Error checking concentration: {str(e)}")
            return False

    async def _get_current_vix(self) -> float:
        """Get current VIX value"""
        try:
            vix_data = await self.redis_client.get('market:vix')
            if vix_data:
                return float(vix_data)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting VIX: {str(e)}")
            return 0.0

    def _setup_event_handlers(self):
        """Setup event subscriptions"""
        self.event_bus.subscribe(EventType.POSITION_OPENED, self._handle_position_opened)
        self.event_bus.subscribe(EventType.POSITION_CLOSED, self._handle_position_closed)
        self.event_bus.subscribe(EventType.POSITION_UPDATED, self._handle_position_updated)

    async def start_monitoring(self):
        """Start risk monitoring task"""
        logger.info("Risk monitoring started with Greeks integration")
        while True:
            try:
                # Update risk metrics including Greeks
                metrics = await self.get_risk_metrics()
                # Check for risk limit breaches
                await self._check_risk_limits(metrics)
                # Update portfolio VaR
                await self._update_portfolio_var()
                # Update Greeks state
                await self._update_greeks_state()
                # Log risk state
                logger.warning(f"Risk regime: {self.risk_state.risk_regime}, "
                             f"Score: {self.risk_state.risk_score:.1f}, "
                             f"Portfolio Delta: {self.risk_state.portfolio_greeks['delta']:.1f}")
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in risk monitoring: {e}")
                await asyncio.sleep(60)

    async def validate_signal(self, signal: Signal) -> Dict[str, Any]:
        """Comprehensive signal validation with risk checks including Greeks"""
        risk_checks = []

        try:
            # 1. Portfolio heat check
            heat_check = await self._check_portfolio_heat(signal)
            risk_checks.append(('portfolio_heat', heat_check))
            # 2. Correlation risk check
            correlation_check = await self._check_correlation_risk(signal)
            risk_checks.append(('correlation', correlation_check))
            # 3. VaR impact check
            var_check = await self._check_var_impact(signal)
            risk_checks.append(('var_impact', var_check))
            # 4. Concentration check
            concentration_check = await self._check_concentration(signal)
            risk_checks.append(('concentration', concentration_check))
            # 5. Daily loss check
            daily_loss_check = await self._check_daily_loss()
            risk_checks.append(('daily_loss', daily_loss_check))
            # 6. Position risk check
            position_risk_check = await self._check_position_risk(signal)
            risk_checks.append(('position_risk', position_risk_check))
            # 7. Greeks risk check
            greeks_check = await self._check_greeks_risk(signal)
            risk_checks.append(('greeks_risk', greeks_check))

            # Aggregate results
            all_passed = all(check[1]['passed'] for check in risk_checks)
            risk_score = self._calculate_aggregate_risk_score(risk_checks)

            # Update risk state including Greeks
            await self._update_greeks_state()

            # Determine risk regime
            self._update_risk_regime(risk_score)

            # Calculate position size if approved
            position_size = 0
            if all_passed:
                position_size = await self.calculate_position_size(signal, risk_score)

            # Final check - ensure position size is reasonable
            if position_size < signal.quantity * 0.5:
                # Risk too high, reduce position
                logger.warning(f"Position size reduced due to high risk: {position_size}")

            result = {
                'approved': all_passed,
                'reason': next((check[1]['reason'] for check in risk_checks if not check[1]['passed']), None),
                'risk_score': risk_score,
                'risk_regime': self.risk_state.risk_regime,
                'position_size': int(position_size),
                'risk_checks': dict(risk_checks),
                'greeks_impact': greeks_check  # Include Greeks analysis
            }

            # Publish risk assessment event
            await self.event_bus.publish(TradingEvent(
                data=result
            ))

            # Log high risk situations
            if risk_score > 80:
                logger.warning(f"High risk signal: {signal.symbol} - Risk score: {risk_score}")
                await self._publish_risk_alert('HIGH_RISK_SIGNAL', result)

            return result

        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return {
                'approved': False,
                'reason': f'Risk validation error: {str(e)}',
                'risk_score': 100,
                'position_size': 0
            }

    async def _check_greeks_risk(self, signal: Signal) -> Dict[str, Any]:
        """Check Greeks risk for new position - CRITICAL for options trading"""
        try:
            # Get current spot price (simplified - would get from market data)
            spot_price = 24000.0  # Would get actual spot price

            # Create temporary position from signal for Greeks validation
            temp_position = Position(
                position_id="TEMP_" + signal.signal_id,
                symbol=signal.symbol,
                quantity=signal.quantity,
                strategy_name=signal.strategy_name
            )

            # Validate with Greeks manager
            greeks_validation = await self.greeks_manager.validate_new_position_greeks(
                temp_position, spot_price
            )

            return {
                'passed': greeks_validation['approved'],
                'reason': 'Greeks limits exceeded' if not greeks_validation['approved'] else None,
                'violations': greeks_validation.get('violations', []),
                'projected_greeks': greeks_validation.get('projected_portfolio_greeks', {}),
                'position_greeks': greeks_validation.get('new_position_greeks', {})
            }

        except Exception as e:
            logger.error(f"Error checking Greeks risk: {e}")
            return {
                'passed': False,
                'reason': f'Greeks validation error: {str(e)}',
                'violations': [],
                'projected_greeks': {},
                'position_greeks': {}
            }

    async def calculate_position_size(self, signal: Signal, risk_score: float) -> int:
        """Calculate optimal position size using multiple methods"""
        async with self._position_lock:
            try:
                capital = self.position_tracker.capital

                # Get strategy statistics
                strategy_stats = await self._get_strategy_statistics(signal.strategy_name)

                # Method 1: Fixed Fractional
                fixed_size = self.position_sizer.calculate_fixed_fractional(capital, risk_score)

                # Method 2: Kelly Criterion
                kelly_size = self.position_sizer.calculate_kelly(
                    strategy_stats['win_rate'],
                    strategy_stats['avg_win'],
                    strategy_stats['avg_loss'],
                    capital
                )

                # Method 3: Greeks-adjusted sizing
                greeks_adjusted_size = await self._calculate_greeks_adjusted_size(signal, capital)

                # Take minimum of all methods for safety
                position_value = min(fixed_size, kelly_size, greeks_adjusted_size)

                # Apply regime-based adjustments
                regime_multiplier = self._get_regime_multiplier()

                # Convert to quantity based on expected price
                expected_price = signal.expected_price if signal.expected_price > 0 else 100
                quantity = position_value / expected_price

                # Convert to lots
                lot_size = self._get_lot_size(signal.symbol)
                lots = max(1, int(quantity / lot_size))

                return lots * lot_size

            except Exception as e:
                logger.error(f"Error calculating position size: {e}")
                return 0

    async def _calculate_greeks_adjusted_size(self, signal: Signal, capital: float) -> float:
        """Calculate position size adjusted for Greeks exposure"""
        try:
            # Estimate position Greeks impact
            base_size = capital * 0.02  # 2% base size

            # Get current portfolio Greeks
            current_greeks = self.risk_state.portfolio_greeks

            # Estimate new position's Greeks (simplified)
            estimated_delta = signal.quantity * 0.5  # Rough ATM delta estimate
            estimated_gamma = signal.quantity * 0.1  # Rough gamma estimate
            estimated_vega = signal.quantity * 0.2   # Rough vega estimate

            # Check if adding position would breach Greeks limits
            greeks_limits = self.greeks_manager.greeks_profile

            # Delta limit check
            new_delta = abs(current_greeks['delta'] + estimated_delta)
            if new_delta > greeks_limits.max_delta_exposure:
                delta_reduction = greeks_limits.max_delta_exposure / new_delta
                base_size *= delta_reduction

            # Vega limit check
            new_vega = abs(current_greeks['vega'] + estimated_vega)
            if new_vega > greeks_limits.max_vega_exposure:
                vega_reduction = greeks_limits.max_vega_exposure / new_vega
                base_size *= vega_reduction

            return base_size

        except Exception as e:
            logger.error(f"Error calculating Greeks-adjusted size: {e}")
            return capital * 0.01  # Conservative fallback

    async def get_risk_metrics(self) -> Dict:
        """Get comprehensive risk metrics including Greeks"""
        positions = self.position_tracker.get_open_positions()

        # Calculate portfolio metrics
        portfolio_value = self.position_tracker.capital + self.position_tracker.total_pnl

        # Get correlation risk
        correlation_risk = self.correlation_tracker.get_portfolio_correlation_risk(positions)

        # Calculate exposure metrics
        total_exposure = sum(p.quantity * p.current_price for p in positions)
        exposure_percent = (total_exposure / self.position_tracker.capital) * 100

        # Get concentration risk
        max_concentration = max(self.portfolio_heat.symbol_exposure.values()) / self.position_tracker.capital if self.portfolio_heat.symbol_exposure else 0

        # Calculate drawdown
        current_drawdown = self._calculate_current_drawdown()

        # Get Greeks metrics
        greeks_report = await self.greeks_manager.get_greeks_report(positions)

        # Calculate VaR
        var, cvar = self.var_calculator.calculate_portfolio_var(
            portfolio_value,
            time_horizon=1.0,
            confidence_level=0.95
        )

        return {
            'portfolio_var': var,
            'portfolio_cvar': cvar,
            'var_95': var,
            'var_99': cvar,
            'correlation_risk': correlation_risk,
            'concentration_risk': max_concentration * 100,
            'total_exposure': total_exposure,
            'exposure_percent': exposure_percent,
            'risk_score': self.risk_state.risk_score,
            'risk_regime': self.risk_state.risk_regime,
            'daily_pnl': self.position_tracker.daily_pnl,
            'daily_pnl_percent': (self.position_tracker.daily_pnl / self.position_tracker.capital) * 100,
            'max_drawdown': self.risk_state.max_drawdown,
            'current_drawdown': current_drawdown,
            'open_positions': len(positions),
            'capital_at_risk': self._calculate_capital_at_risk(positions),
            'potential_loss': sum(p.current_risk for p in positions),

            # Greeks metrics integration
            'portfolio_greeks': greeks_report['portfolio_greeks'],
            'greeks_risk_utilization': greeks_report['risk_utilization'],
            'greeks_limits': greeks_report['risk_limits'],
            'delta_hedging_needed': greeks_report['hedging_recommendation']['hedging_required'],
            'daily_theta_decay': greeks_report['daily_theta_decay']
        }

    async def _update_greeks_state(self):
        """Update Greeks state in risk state"""
        try:
            positions = self.position_tracker.get_open_positions()
            market_data = {}  # Would get actual market data

            # Update portfolio Greeks
            greeks_profile = await self.greeks_manager.update_portfolio_greeks(positions, market_data)

            # Update risk state
            self.risk_state.portfolio_delta = greeks_profile.portfolio_delta
            self.risk_state.portfolio_gamma = greeks_profile.portfolio_gamma
            self.risk_state.portfolio_theta = greeks_profile.portfolio_theta
            self.risk_state.portfolio_vega = greeks_profile.portfolio_vega
            self.risk_state.portfolio_rho = greeks_profile.portfolio_rho

        except Exception as e:
            logger.error(f"Error updating Greeks state: {e}")

    async def _check_portfolio_heat(self, signal: Signal) -> Dict[str, Any]:
        """Check portfolio heat/concentration"""
        position_value = signal.quantity * (signal.expected_price or 100)
        capital = self.position_tracker.capital

        can_add = self.portfolio_heat.can_add_position(
            signal.symbol, position_value, capital
        )

        heat_level = self.portfolio_heat.get_heat_level(signal.symbol)
        return {
            'passed': can_add and heat_level < 0.8,
            'reason': 'Portfolio concentration too high' if not can_add else None,
            'heat_level': heat_level,
            'concentration': (self.portfolio_heat.symbol_exposure[self._get_base_symbol(signal.symbol)] + position_value) / capital
        }

    async def _check_correlation_risk(self, signal: Signal) -> Dict[str, Any]:
        """Check correlation with existing positions"""
        positions = self.position_tracker.get_open_positions()
        if not positions:
            return {'passed': True, 'correlation_risk': 0}

        # Get correlations with existing positions
        signal_symbol = self._get_base_symbol(signal.symbol)
        max_correlation = 0

        for position in positions:
            pos_symbol = self._get_base_symbol(position.symbol)
            correlation = abs(self.correlation_tracker.get_correlation(signal_symbol, pos_symbol))
            max_correlation = max(max_correlation, correlation)

        passed = max_correlation < self.max_correlation
        return {
            'passed': passed,
            'reason': 'High correlation with existing positions' if not passed else None,
            'max_correlation': max_correlation
        }

    async def _check_var_impact(self, signal: Signal) -> Dict[str, Any]:
        """Check VaR impact of new position"""
        try:
            # Calculate current portfolio VaR
            portfolio_value = self.position_tracker.capital + self.position_tracker.total_pnl
            current_var, _ = self.var_calculator.calculate_portfolio_var(
                portfolio_value,
                time_horizon=1.0,
                confidence_level=0.95
            )

            # Estimate new position VaR
            position_var = self.var_calculator.calculate_position_var(
                Position(
                    position_id="TEMP_" + signal.signal_id,
                    symbol=signal.symbol,
                    quantity=signal.quantity,
                    strategy_name=signal.strategy_name
                ),
                current_var
            )

            # Check if adding position would exceed VaR limits
            max_var_increase = portfolio_value * 0.1  # Max 10% increase in VaR
            passed = position_var <= max_var_increase

            return {
                'passed': passed,
                'reason': 'VaR impact too high' if not passed else None,
                'var_impact': position_var,
                'current_var': current_var
            }

        except Exception as e:
            logger.error(f"Error checking VaR impact: {e}")
            return {
                'passed': False,
                'reason': f'VaR calculation error: {str(e)}',
                'var_impact': float('inf'),
                'current_var': 0.0
            }

    async def _check_concentration(self, signal: Signal) -> Dict[str, Any]:
        """Check position concentration"""
        position_value = signal.quantity * (signal.expected_price or 100)
        capital = self.position_tracker.capital

        # Check symbol concentration
        symbol_base = self._get_base_symbol(signal.symbol)
        current_exposure = self.portfolio_heat.symbol_exposure.get(symbol_base, 0)
        new_concentration = (current_exposure + position_value) / capital

        # Check strategy concentration
        strategy_positions = [p for p in self.position_tracker.get_open_positions()
                           if p.strategy_name == signal.strategy_name]
        strategy_exposure = sum(p.quantity * p.current_price for p in strategy_positions)
        strategy_concentration = (strategy_exposure + position_value) / capital

        passed = (new_concentration <= 0.2 and  # Max 20% per symbol
                 strategy_concentration <= 0.4)  # Max 40% per strategy

        return {
            'passed': passed,
            'reason': 'Concentration limits exceeded' if not passed else None,
            'symbol_concentration': new_concentration * 100,
            'strategy_concentration': strategy_concentration * 100
        }

    async def _check_daily_loss(self) -> Dict[str, Any]:
        """Check daily loss limits"""
        daily_pnl = self.position_tracker.daily_pnl
        daily_pnl_percent = (daily_pnl / self.position_tracker.capital) * 100

        # Check against configurable limits
        max_daily_loss = self.config.get('max_daily_loss_percent', -2.0)
        passed = daily_pnl_percent >= max_daily_loss

        return {
            'passed': passed,
            'reason': 'Daily loss limit exceeded' if not passed else None,
            'daily_pnl': daily_pnl,
            'daily_pnl_percent': daily_pnl_percent
        }

    async def _check_position_risk(self, signal: Signal) -> Dict[str, Any]:
        """Check individual position risk"""
        position_value = signal.quantity * (signal.expected_price or 100)
        capital = self.position_tracker.capital

        # Check position size
        max_position_size = self.config.get('max_position_size', 0.1)  # Max 10% of capital
        position_size_percent = (position_value / capital) * 100
        passed = position_size_percent <= max_position_size * 100

        return {
            'passed': passed,
            'reason': 'Position size too large' if not passed else None,
            'position_size_percent': position_size_percent
        }

    async def _get_strategy_statistics(self, strategy_name: str) -> Dict:
        """Get strategy statistics with synchronization"""
        async with self._stats_lock:
            if strategy_name not in self.strategy_stats:
                self.strategy_stats[strategy_name] = {
                    'win_rate': 0.5,
                    'avg_win': 100,
                    'avg_loss': 50,
                    'total_trades': 0
                }
            return self.strategy_stats[strategy_name]

    def _calculate_aggregate_risk_score(self, risk_checks: List[Tuple[str, Dict]]) -> float:
        """Calculate aggregate risk score from all checks"""
        weights = {
            'portfolio_heat': 0.15,
            'correlation': 0.15,
            'var_impact': 0.2,
            'concentration': 0.15,
            'daily_loss': 0.15,
            'position_risk': 0.1,
            'greeks_risk': 0.1
        }

        score = 0.0
        for check_name, check_result in risk_checks:
            if check_name in weights:
                if not check_result['passed']:
                    score += weights[check_name] * 100
                else:
                    # Add partial score based on risk level
                    if 'heat_level' in check_result:
                        score += weights[check_name] * check_result['heat_level']
                    elif 'max_correlation' in check_result:
                        score += weights[check_name] * (check_result['max_correlation'] * 100)
                    elif 'var_impact' in check_result:
                        impact_percent = (check_result['var_impact'] / check_result['current_var']) * 100
                        score += weights[check_name] * min(impact_percent, 100)
                    elif 'symbol_concentration' in check_result:
                        score += weights[check_name] * (check_result['symbol_concentration'] / 20 * 100)
                    elif 'daily_pnl_percent' in check_result:
                        loss_percent = abs(min(check_result['daily_pnl_percent'], 0))
                        score += weights[check_name] * (loss_percent / 2 * 100)
                    elif 'position_size_percent' in check_result:
                        score += weights[check_name] * (check_result['position_size_percent'] / 10 * 100)

        return min(score, 100)  # Cap at 100

    def _update_risk_regime(self, risk_score: float):
        """Update risk regime based on score"""
        if risk_score >= 80:
            self.risk_state.risk_regime = 'HIGH_RISK'
        elif risk_score >= 60:
            self.risk_state.risk_regime = 'ELEVATED'
        elif risk_score >= 40:
            self.risk_state.risk_regime = 'MODERATE'
        else:
            self.risk_state.risk_regime = 'LOW_RISK'

    def _get_regime_multiplier(self) -> float:
        """Get position size multiplier based on current market regime"""
        current_regime = self.position_tracker.current_regime
        return self.risk_regime_multipliers.get(current_regime, 1.0)

    def _get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol"""
        if 'NIFTY' in symbol:
            return 50
        elif 'BANKNIFTY' in symbol:
            return 25
        elif 'FINNIFTY' in symbol:
            return 40
        return 1

    def _get_base_symbol(self, symbol: str) -> str:
        """Extract base symbol from option symbol"""
        if 'BANKNIFTY' in symbol:
            return 'BANKNIFTY'
        elif 'NIFTY' in symbol:
            return 'NIFTY'
        elif 'FINNIFTY' in symbol:
            return 'FINNIFTY'
        return symbol.split('_')[0] if '_' in symbol else symbol

    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown"""
        if not self.position_tracker.peak_capital:
            return 0.0
        return ((self.position_tracker.peak_capital - self.position_tracker.capital) /
                self.position_tracker.peak_capital * 100)

    def _calculate_capital_at_risk(self, positions: List[Position]) -> float:
        """Calculate total capital at risk"""
        return sum(p.quantity * p.current_price for p in positions)

    async def _check_risk_limits(self, metrics: Dict):
        """Check if any risk limits are breached"""
        alerts = []

        # Check daily loss
        if metrics['daily_pnl_percent'] < self.config.get('max_daily_loss_percent', -2.0):
            alerts.append(('CRITICAL', f'Daily loss limit exceeded: {metrics["daily_pnl_percent"]:.2f}%'))

        # Check drawdown
        if metrics['current_drawdown'] > self.config.get('max_drawdown_percent', 5.0):
            alerts.append(('CRITICAL', f'Drawdown limit exceeded: {metrics["current_drawdown"]:.2f}%'))

        # Check exposure
        if metrics['exposure_percent'] > self.config.get('max_exposure_percent', 100.0):
            alerts.append(('WARNING', f'Exposure limit exceeded: {metrics["exposure_percent"]:.2f}%'))

        # Check correlation risk
        if metrics['correlation_risk'] > self.config.get('max_correlation_risk', 70.0):
            alerts.append(('WARNING', f'High correlation risk: {metrics["correlation_risk"]:.2f}%'))

        # Check concentration risk
        if metrics['concentration_risk'] > self.config.get('max_concentration_percent', 20.0):
            alerts.append(('WARNING', f'High concentration risk: {metrics["concentration_risk"]:.2f}%'))

        # Check Greeks risk
        if metrics['greeks_risk_utilization'] > self.config.get('max_greeks_utilization', 80.0):
            alerts.append(('WARNING', f'High Greeks utilization: {metrics["greeks_risk_utilization"]:.2f}%'))

        # Send alerts
        for level, message in alerts:
            await self._publish_risk_alert(level, {
                'message': message,
                'metrics': metrics
            })

    async def _publish_risk_alert(self, alert_type: str, data: Dict):
        """Publish risk alert event"""
        await self.event_bus.publish(TradingEvent(
            event_type=EventType.RISK_ALERT,
            data={
                'alert_type': alert_type,
                'timestamp': datetime.now().isoformat(),
                **data
            }
        ))

    async def _handle_position_opened(self, event: TradingEvent):
        """Handle position opened event"""
        position = event.data['position']
        # Update portfolio heat
        self.portfolio_heat.update_exposure(position)
        # Update correlation tracking
        self.correlation_tracker.update_price(position.symbol, position.current_price)
        # Log risk metrics
        metrics = await self.get_risk_metrics()
        logger.info(f"Position opened - Risk metrics: {metrics}")

    async def _handle_position_closed(self, event: TradingEvent):
        """Handle position closed event"""
        position = event.data['position']
        # Update portfolio heat
        self.portfolio_heat.remove_exposure(position)
        # Update strategy statistics
        self.position_sizer.update_strategy_stats(
            position.strategy_name,
            event.data['trade_result']
        )
        # Log risk metrics
        metrics = await self.get_risk_metrics()
        logger.info(f"Position closed - Risk metrics: {metrics}")

    async def _handle_position_updated(self, event: TradingEvent):
        """Handle position updated event"""
        position = event.data['position']
        # Update correlation tracking
        self.correlation_tracker.update_price(position.symbol, position.current_price)
        # Check risk limits
        metrics = await self.get_risk_metrics()
        await self._check_risk_limits(metrics)

    async def _update_portfolio_var(self):
        """Update portfolio VaR"""
        try:
            portfolio_value = self.position_tracker.capital + self.position_tracker.total_pnl
            daily_return = (portfolio_value - self.position_tracker.previous_capital) / self.position_tracker.previous_capital
            self.var_calculator.add_return(daily_return)
        except Exception as e:
            logger.error(f"Error updating portfolio VaR: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close any open connections
            pass
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _is_user_hard_stopped(self, user_id: str) -> bool:
        """Check if user is under hard stop"""
        try:
            if self.redis_client:
                status = await self.redis_client.get(f"user:{user_id}:hard_stop_status")
                return status == "STOPPED"
            return self.user_hard_stops.get(user_id, False)
        except Exception as e:
            logger.error(f"Error checking hard stop status: {str(e)}")
            return False

    async def _trigger_hard_stop(self, user_id: str):
        """Trigger hard stop for user"""
        try:
            # Update hard stop status
            self.user_hard_stops.add(user_id)
            if self.redis_client:
                await self.redis_client.set(f"user:{user_id}:hard_stop_status", "STOPPED")
            
            # Store hard stop event
            await self._store_hard_stop_event(user_id)
            
            # Send notification
            await self._send_hard_stop_notification(user_id)
            
            logger.info(f"Hard stop triggered for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error triggering hard stop: {str(e)}")

    async def _store_hard_stop_event(self, user_id: str):
        """Store hard stop event in Redis"""
        try:
            if self.redis_client:
                current_capital = await self._get_user_capital(user_id)
                opening_capital = await self._get_opening_capital(user_id)
                
                event = {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "opening_capital": opening_capital,
                    "current_capital": current_capital,
                    "loss_percentage": (opening_capital - current_capital) / opening_capital * 100 if opening_capital else 0,
                    "threshold": self.config.get('hard_stop_threshold', 0.02) * 100
                }
                
                await self.redis_client.set(
                    f"user:{user_id}:hard_stop_event:{datetime.now().strftime('%Y-%m-%d')}",
                    json.dumps(event)
                )
                
        except Exception as e:
            logger.error(f"Error storing hard stop event: {str(e)}")

    async def _send_hard_stop_notification(self, user_id: str):
        """Send notification about hard stop"""
        try:
            current_capital = await self._get_user_capital(user_id)
            opening_capital = await self._get_opening_capital(user_id)
            
            notification = {
                "user_id": user_id,
                "type": "HARD_STOP",
                "message": f"Trading stopped due to 2% capital loss. Opening capital: ${opening_capital:,.2f}, Current capital: ${current_capital:,.2f}",
                "timestamp": datetime.now().isoformat()
            }
            
            if self.redis_client:
                await self.redis_client.publish(
                    f"notifications:{user_id}",
                    json.dumps(notification)
                )
                
            logger.info(f"Hard stop notification sent for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending hard stop notification: {str(e)}")

    async def _get_user_capital(self, user_id: str) -> float:
        """Get user's current capital"""
        try:
            if self.redis_client:
                capital = await self.redis_client.get(f"user:{user_id}:capital")
                return float(capital) if capital else None
            return None
        except Exception as e:
            logger.error(f"Error getting user capital: {str(e)}")
            return None

    async def _get_opening_capital(self, user_id: str) -> float:
        """Get user's opening day capital"""
        try:
            if self.redis_client:
                date = datetime.now().strftime("%Y-%m-%d")
                capital = await self.redis_client.get(f"user:{user_id}:opening_capital:{date}")
                return float(capital) if capital else None
            return None
        except Exception as e:
            logger.error(f"Error getting opening capital: {str(e)}")
            return None

    async def _get_daily_pnl(self, user_id: str) -> float:
        """Get user's daily P&L"""
        try:
            if self.redis_client:
                pnl = await self.redis_client.get(f"user:{user_id}:daily_pnl")
                return float(pnl) if pnl else 0.0
            return 0.0
        except Exception as e:
            logger.error(f"Error getting daily P&L: {str(e)}")
            return 0.0

@dataclass
class RiskLimits:
    """User risk limits"""
    max_position_size: float
    max_daily_loss: float
    max_drawdown: float
    risk_per_trade: float
    max_positions: int
    max_correlation: float
    max_concentration: float
    vix_threshold_high: float
    vix_threshold_extreme: float

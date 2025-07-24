# core/crypto_risk_manager_enhanced.py
"""
Enhanced Crypto Risk Manager
Advanced risk management with black swan detection and correlation monitoring
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    total_exposure: float
    portfolio_var: float  # Value at Risk
    max_drawdown: float
    correlation_risk: float
    concentration_risk: float
    volatility_risk: float
    black_swan_probability: float
    last_updated: datetime

@dataclass
class PositionRisk:
    """Individual position risk"""
    symbol: str
    position_size: float
    unrealized_pnl: float
    var_contribution: float
    correlation_exposure: float
    stop_loss_level: float
    risk_score: float

class EnhancedCryptoRiskManager:
    """
    Enhanced risk manager for crypto trading with black swan protection
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Risk limits
        self.max_position_size = config.get('max_position_size', 0.10)  # 10%
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.15)  # 15%
        self.max_daily_loss = config.get('max_daily_loss', 0.02)  # 2%
        self.max_correlation = config.get('max_correlation', 0.70)  # 70%
        self.max_concentration = config.get('max_concentration', 0.25)  # 25%
        
        # Black swan thresholds
        self.black_swan_threshold = config.get('black_swan_threshold', 0.60)
        self.emergency_threshold = config.get('emergency_threshold', 0.80)
        self.correlation_break_threshold = config.get('correlation_break_threshold', 0.50)
        
        # Risk tracking
        self.current_positions = {}
        self.risk_metrics = None
        self.risk_history = deque(maxlen=1000)
        self.correlation_matrix = {}
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        
        # Emergency state
        self.emergency_mode = False
        self.risk_alerts = deque(maxlen=100)
        
        # Performance tracking
        self.risk_checks_performed = 0
        self.trades_blocked = 0
        self.emergency_activations = 0
        
        logger.info("Enhanced Crypto Risk Manager initialized")

    async def start(self):
        """Start the risk manager"""
        logger.info("🛡️ Starting Enhanced Crypto Risk Manager...")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_portfolio_risk())
        asyncio.create_task(self._monitor_correlations())
        asyncio.create_task(self._monitor_black_swan_risks())
        
        logger.info("✅ Enhanced Crypto Risk Manager started")

    async def check_trade_risk(self, symbol: str, side: str, quantity: float, 
                              price: float) -> Dict:
        """Check if a trade is within risk limits"""
        try:
            self.risk_checks_performed += 1
            
            # Calculate trade value
            trade_value = quantity * price
            current_portfolio_value = self._get_portfolio_value()
            
            if current_portfolio_value == 0:
                return {'approved': False, 'reason': 'No portfolio value'}
            
            position_size_percent = trade_value / current_portfolio_value
            
            # Check position size limit
            if position_size_percent > self.max_position_size:
                self.trades_blocked += 1
                return {
                    'approved': False,
                    'reason': f'Position size {position_size_percent:.1%} exceeds limit {self.max_position_size:.1%}',
                    'risk_score': 1.0
                }
            
            # Check if in emergency mode
            if self.emergency_mode:
                self.trades_blocked += 1
                return {
                    'approved': False,
                    'reason': 'Emergency mode active - trading suspended',
                    'risk_score': 1.0
                }
            
            # Check correlation risk
            correlation_risk = await self._calculate_correlation_risk(symbol, trade_value)
            if correlation_risk > self.max_correlation:
                self.trades_blocked += 1
                return {
                    'approved': False,
                    'reason': f'Correlation risk {correlation_risk:.1%} exceeds limit {self.max_correlation:.1%}',
                    'risk_score': correlation_risk
                }
            
            # Check concentration risk
            concentration_risk = await self._calculate_concentration_risk(symbol, trade_value)
            if concentration_risk > self.max_concentration:
                self.trades_blocked += 1
                return {
                    'approved': False,
                    'reason': f'Concentration risk {concentration_risk:.1%} exceeds limit {self.max_concentration:.1%}',
                    'risk_score': concentration_risk
                }
            
            # Check daily loss limit
            daily_pnl = await self._get_daily_pnl()
            if daily_pnl < -self.max_daily_loss:
                self.trades_blocked += 1
                return {
                    'approved': False,
                    'reason': f'Daily loss limit {self.max_daily_loss:.1%} exceeded',
                    'risk_score': abs(daily_pnl)
                }
            
            # Calculate overall risk score
            risk_score = max(position_size_percent, correlation_risk, concentration_risk)
            
            return {
                'approved': True,
                'risk_score': risk_score,
                'position_size_percent': position_size_percent,
                'correlation_risk': correlation_risk,
                'concentration_risk': concentration_risk,
                'recommended_quantity': quantity  # Could adjust based on risk
            }
            
        except Exception as e:
            logger.error(f"Error checking trade risk: {e}")
            return {'approved': False, 'reason': f'Risk check error: {e}'}

    async def update_position(self, symbol: str, quantity: float, price: float, side: str):
        """Update position information"""
        try:
            if symbol not in self.current_positions:
                self.current_positions[symbol] = {
                    'quantity': 0.0,
                    'avg_price': 0.0,
                    'unrealized_pnl': 0.0,
                    'last_updated': datetime.now()
                }
            
            position = self.current_positions[symbol]
            
            # Update position
            if side == 'BUY':
                total_cost = position['quantity'] * position['avg_price'] + quantity * price
                total_quantity = position['quantity'] + quantity
                position['avg_price'] = total_cost / total_quantity if total_quantity > 0 else price
                position['quantity'] = total_quantity
            else:  # SELL
                position['quantity'] -= quantity
                if position['quantity'] <= 0:
                    position['quantity'] = 0
                    position['avg_price'] = 0
            
            position['last_updated'] = datetime.now()
            
            # Update unrealized P&L
            if position['quantity'] > 0:
                position['unrealized_pnl'] = (price - position['avg_price']) * position['quantity']
            else:
                position['unrealized_pnl'] = 0
            
            # Update price history for correlation calculation
            self.price_history[symbol].append({'price': price, 'timestamp': datetime.now()})
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")

    async def _monitor_portfolio_risk(self):
        """Monitor overall portfolio risk"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Calculate risk metrics
                risk_metrics = await self._calculate_risk_metrics()
                self.risk_metrics = risk_metrics
                self.risk_history.append(risk_metrics)
                
                # Check for risk alerts
                await self._check_risk_alerts(risk_metrics)
                
            except Exception as e:
                logger.error(f"Error monitoring portfolio risk: {e}")
                await asyncio.sleep(300)

    async def _calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            portfolio_value = self._get_portfolio_value()
            
            if portfolio_value == 0:
                return RiskMetrics(
                    total_exposure=0, portfolio_var=0, max_drawdown=0,
                    correlation_risk=0, concentration_risk=0, volatility_risk=0,
                    black_swan_probability=0, last_updated=datetime.now()
                )
            
            # Calculate total exposure
            total_exposure = sum(abs(pos['quantity'] * pos['avg_price']) for pos in self.current_positions.values())
            exposure_ratio = total_exposure / portfolio_value
            
            # Calculate portfolio VaR (simplified)
            portfolio_var = await self._calculate_portfolio_var()
            
            # Calculate max drawdown
            max_drawdown = await self._calculate_max_drawdown()
            
            # Calculate correlation risk
            correlation_risk = await self._calculate_portfolio_correlation_risk()
            
            # Calculate concentration risk
            concentration_risk = await self._calculate_portfolio_concentration_risk()
            
            # Calculate volatility risk
            volatility_risk = await self._calculate_volatility_risk()
            
            # Calculate black swan probability
            black_swan_prob = await self._calculate_black_swan_probability()
            
            return RiskMetrics(
                total_exposure=exposure_ratio,
                portfolio_var=portfolio_var,
                max_drawdown=max_drawdown,
                correlation_risk=correlation_risk,
                concentration_risk=concentration_risk,
                volatility_risk=volatility_risk,
                black_swan_probability=black_swan_prob,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0, datetime.now())

    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            # Simplified portfolio value calculation
            total_value = 100000  # Assume $100k portfolio
            
            # Add unrealized P&L
            for position in self.current_positions.values():
                total_value += position['unrealized_pnl']
            
            return max(0, total_value)
            
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0

    async def _calculate_portfolio_var(self) -> float:
        """Calculate portfolio Value at Risk"""
        try:
            # Simplified VaR calculation
            if not self.current_positions:
                return 0
            
            # Use historical simulation method
            portfolio_returns = []
            for symbol, position in self.current_positions.items():
                if symbol in self.price_history and len(self.price_history[symbol]) > 1:
                    prices = [p['price'] for p in self.price_history[symbol]]
                    returns = np.diff(prices) / prices[:-1]
                    position_value = position['quantity'] * position['avg_price']
                    position_returns = returns * position_value
                    portfolio_returns.extend(position_returns)
            
            if portfolio_returns:
                # 95% VaR
                var_95 = np.percentile(portfolio_returns, 5)
                return abs(var_95) / self._get_portfolio_value()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating portfolio VaR: {e}")
            return 0

    async def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(self.risk_history) < 10:
                return 0
            
            # Calculate portfolio values from history
            portfolio_values = []
            base_value = 100000
            
            for metrics in self.risk_history:
                # Estimate portfolio value change
                value_change = -metrics.portfolio_var * base_value
                base_value += value_change
                portfolio_values.append(base_value)
            
            if not portfolio_values:
                return 0
            
            # Calculate drawdown
            peak = portfolio_values[0]
            max_dd = 0
            
            for value in portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
            
            return max_dd
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0

    async def _calculate_correlation_risk(self, symbol: str, trade_value: float) -> float:
        """Calculate correlation risk for a new trade"""
        try:
            if not self.current_positions:
                return 0
            
            portfolio_value = self._get_portfolio_value()
            if portfolio_value == 0:
                return 0
            
            # Calculate weighted correlation
            total_correlation = 0
            total_weight = 0
            
            for pos_symbol, position in self.current_positions.items():
                if pos_symbol != symbol:
                    position_value = position['quantity'] * position['avg_price']
                    weight = position_value / portfolio_value
                    
                    # Get correlation (simplified)
                    correlation = await self._get_correlation(symbol, pos_symbol)
                    
                    total_correlation += correlation * weight
                    total_weight += weight
            
            if total_weight > 0:
                avg_correlation = total_correlation / total_weight
                # Adjust for new trade size
                trade_weight = trade_value / portfolio_value
                risk_adjusted_correlation = avg_correlation * (1 + trade_weight)
                return min(1.0, abs(risk_adjusted_correlation))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0

    async def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        try:
            if symbol1 == symbol2:
                return 1.0
            
            # Simplified correlation calculation
            # In reality, would calculate from price history
            crypto_correlations = {
                ('BTCUSDT', 'ETHUSDT'): 0.8,
                ('BTCUSDT', 'ADAUSDT'): 0.7,
                ('ETHUSDT', 'ADAUSDT'): 0.75,
                ('BTCUSDT', 'DOTUSDT'): 0.65,
                ('ETHUSDT', 'LINKUSDT'): 0.70
            }
            
            key1 = (symbol1, symbol2)
            key2 = (symbol2, symbol1)
            
            return crypto_correlations.get(key1, crypto_correlations.get(key2, 0.6))
            
        except Exception as e:
            logger.error(f"Error getting correlation: {e}")
            return 0.6  # Default moderate correlation

    async def _calculate_concentration_risk(self, symbol: str, trade_value: float) -> float:
        """Calculate concentration risk"""
        try:
            portfolio_value = self._get_portfolio_value()
            if portfolio_value == 0:
                return 0
            
            # Current position value
            current_value = 0
            if symbol in self.current_positions:
                position = self.current_positions[symbol]
                current_value = position['quantity'] * position['avg_price']
            
            # New total value for this symbol
            new_total_value = current_value + trade_value
            concentration = new_total_value / portfolio_value
            
            return concentration
            
        except Exception as e:
            logger.error(f"Error calculating concentration risk: {e}")
            return 0

    async def _calculate_portfolio_correlation_risk(self) -> float:
        """Calculate overall portfolio correlation risk"""
        try:
            if len(self.current_positions) < 2:
                return 0
            
            symbols = list(self.current_positions.keys())
            correlations = []
            
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    correlation = await self._get_correlation(symbols[i], symbols[j])
                    correlations.append(abs(correlation))
            
            if correlations:
                return sum(correlations) / len(correlations)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating portfolio correlation risk: {e}")
            return 0

    async def _calculate_portfolio_concentration_risk(self) -> float:
        """Calculate portfolio concentration risk"""
        try:
            if not self.current_positions:
                return 0
            
            portfolio_value = self._get_portfolio_value()
            if portfolio_value == 0:
                return 0
            
            # Calculate Herfindahl index
            concentrations = []
            for position in self.current_positions.values():
                position_value = position['quantity'] * position['avg_price']
                concentration = position_value / portfolio_value
                concentrations.append(concentration ** 2)
            
            herfindahl_index = sum(concentrations)
            return herfindahl_index
            
        except Exception as e:
            logger.error(f"Error calculating concentration risk: {e}")
            return 0

    async def _calculate_volatility_risk(self) -> float:
        """Calculate portfolio volatility risk"""
        try:
            # Simplified volatility calculation
            if not self.price_history:
                return 0
            
            volatilities = []
            for symbol, history in self.price_history.items():
                if len(history) > 5:
                    prices = [p['price'] for p in history]
                    returns = np.diff(prices) / prices[:-1]
                    volatility = np.std(returns) * np.sqrt(1440)  # Daily volatility
                    volatilities.append(volatility)
            
            if volatilities:
                avg_volatility = np.mean(volatilities)
                return min(1.0, avg_volatility / 0.20)  # Normalize to 20% max
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating volatility risk: {e}")
            return 0

    async def _calculate_black_swan_probability(self) -> float:
        """Calculate black swan event probability"""
        try:
            risk_factors = []
            
            # High correlation factor
            if self.risk_metrics:
                if self.risk_metrics.correlation_risk > 0.8:
                    risk_factors.append(0.4)
                
                # High concentration factor
                if self.risk_metrics.concentration_risk > 0.5:
                    risk_factors.append(0.3)
                
                # High volatility factor
                if self.risk_metrics.volatility_risk > 0.8:
                    risk_factors.append(0.3)
            
            # Market stress factor (simplified)
            market_stress = 0.2  # Would be calculated from market indicators
            risk_factors.append(market_stress)
            
            if risk_factors:
                return min(1.0, sum(risk_factors) / len(risk_factors))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating black swan probability: {e}")
            return 0

    async def _monitor_correlations(self):
        """Monitor correlation changes"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Update correlation matrix
                await self._update_correlation_matrix()
                
                # Check for correlation breaks
                await self._check_correlation_breaks()
                
            except Exception as e:
                logger.error(f"Error monitoring correlations: {e}")
                await asyncio.sleep(600)

    async def _update_correlation_matrix(self):
        """Update correlation matrix"""
        try:
            symbols = list(self.price_history.keys())
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i <= j:
                        correlation = await self._get_correlation(symbol1, symbol2)
                        self.correlation_matrix[f"{symbol1}_{symbol2}"] = correlation
            
        except Exception as e:
            logger.error(f"Error updating correlation matrix: {e}")

    async def _check_correlation_breaks(self):
        """Check for correlation breakdown events"""
        try:
            # This would analyze correlation changes over time
            # For now, simplified
            pass
            
        except Exception as e:
            logger.error(f"Error checking correlation breaks: {e}")

    async def _monitor_black_swan_risks(self):
        """Monitor black swan risk indicators"""
        while True:
            try:
                await asyncio.sleep(120)  # Check every 2 minutes
                
                if self.risk_metrics:
                    black_swan_prob = self.risk_metrics.black_swan_probability
                    
                    # Check emergency threshold
                    if black_swan_prob > self.emergency_threshold and not self.emergency_mode:
                        await self._activate_emergency_mode()
                    elif black_swan_prob < self.emergency_threshold * 0.8 and self.emergency_mode:
                        await self._deactivate_emergency_mode()
                    
                    # Check warning threshold
                    if black_swan_prob > self.black_swan_threshold:
                        await self._issue_risk_alert('black_swan_warning', black_swan_prob)
                
            except Exception as e:
                logger.error(f"Error monitoring black swan risks: {e}")
                await asyncio.sleep(300)

    async def _check_risk_alerts(self, metrics: RiskMetrics):
        """Check for risk alert conditions"""
        try:
            alerts = []
            
            # Check various risk thresholds
            if metrics.correlation_risk > self.max_correlation:
                alerts.append(f"High correlation risk: {metrics.correlation_risk:.1%}")
            
            if metrics.concentration_risk > self.max_concentration:
                alerts.append(f"High concentration risk: {metrics.concentration_risk:.1%}")
            
            if metrics.total_exposure > 1.5:  # 150% exposure
                alerts.append(f"High leverage: {metrics.total_exposure:.1%}")
            
            if metrics.black_swan_probability > self.black_swan_threshold:
                alerts.append(f"Black swan risk: {metrics.black_swan_probability:.1%}")
            
            # Issue alerts
            for alert in alerts:
                await self._issue_risk_alert('risk_warning', alert)
            
        except Exception as e:
            logger.error(f"Error checking risk alerts: {e}")

    async def _issue_risk_alert(self, alert_type: str, details):
        """Issue a risk alert"""
        try:
            alert = {
                'type': alert_type,
                'details': details,
                'timestamp': datetime.now(),
                'severity': 'HIGH' if 'black_swan' in alert_type else 'MEDIUM'
            }
            
            self.risk_alerts.append(alert)
            
            logger.warning(f"🚨 RISK ALERT [{alert_type}]: {details}")
            
        except Exception as e:
            logger.error(f"Error issuing risk alert: {e}")

    async def _activate_emergency_mode(self):
        """Activate emergency risk mode"""
        try:
            self.emergency_mode = True
            self.emergency_activations += 1
            
            logger.critical(f"🚨 EMERGENCY MODE ACTIVATED! Black Swan Probability: {self.risk_metrics.black_swan_probability:.1%}")
            logger.critical("   🛑 All new trading suspended")
            logger.critical("   📉 Consider reducing positions")
            
            await self._issue_risk_alert('emergency_mode_activated', 'Trading suspended due to extreme risk')
            
        except Exception as e:
            logger.error(f"Error activating emergency mode: {e}")

    async def _deactivate_emergency_mode(self):
        """Deactivate emergency risk mode"""
        try:
            self.emergency_mode = False
            
            logger.info(f"✅ Emergency mode deactivated. Risk normalized.")
            
            await self._issue_risk_alert('emergency_mode_deactivated', 'Trading resumed - risk levels normalized')
            
        except Exception as e:
            logger.error(f"Error deactivating emergency mode: {e}")

    async def _get_daily_pnl(self) -> float:
        """Get daily P&L percentage"""
        try:
            # Simplified daily P&L calculation
            total_unrealized = sum(pos['unrealized_pnl'] for pos in self.current_positions.values())
            portfolio_value = self._get_portfolio_value()
            
            if portfolio_value > 0:
                return total_unrealized / portfolio_value
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting daily P&L: {e}")
            return 0

    def get_performance_metrics(self) -> Dict:
        """Get risk manager performance metrics"""
        try:
            current_risk = self.risk_metrics
            
            return {
                'risk_checks_performed': self.risk_checks_performed,
                'trades_blocked': self.trades_blocked,
                'block_rate': self.trades_blocked / max(1, self.risk_checks_performed),
                'emergency_activations': self.emergency_activations,
                'emergency_mode_active': self.emergency_mode,
                'current_risk_score': current_risk.black_swan_probability if current_risk else 0,
                'portfolio_exposure': current_risk.total_exposure if current_risk else 0,
                'correlation_risk': current_risk.correlation_risk if current_risk else 0,
                'concentration_risk': current_risk.concentration_risk if current_risk else 0,
                'positions_monitored': len(self.current_positions),
                'recent_alerts': len([alert for alert in self.risk_alerts if alert['timestamp'] > datetime.now() - timedelta(hours=24)])
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report"""
        try:
            if not self.risk_metrics:
                return {'status': 'No risk data available'}
            
            return {
                'timestamp': datetime.now(),
                'emergency_mode': self.emergency_mode,
                'risk_metrics': {
                    'total_exposure': self.risk_metrics.total_exposure,
                    'portfolio_var': self.risk_metrics.portfolio_var,
                    'max_drawdown': self.risk_metrics.max_drawdown,
                    'correlation_risk': self.risk_metrics.correlation_risk,
                    'concentration_risk': self.risk_metrics.concentration_risk,
                    'volatility_risk': self.risk_metrics.volatility_risk,
                    'black_swan_probability': self.risk_metrics.black_swan_probability
                },
                'positions': {
                    symbol: {
                        'quantity': pos['quantity'],
                        'avg_price': pos['avg_price'],
                        'unrealized_pnl': pos['unrealized_pnl']
                    }
                    for symbol, pos in self.current_positions.items()
                },
                'recent_alerts': [
                    {
                        'type': alert['type'],
                        'details': alert['details'],
                        'timestamp': alert['timestamp'],
                        'severity': alert['severity']
                    }
                    for alert in list(self.risk_alerts)[-10:]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {'error': str(e)} 
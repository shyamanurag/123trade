# edge/risk_predictor.py
"""
Quantum Risk Predictor - Black Swan Detection & Market Crash Prediction
Advanced risk analysis with correlation breakdown detection and stablecoin monitoring
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class RiskEvent:
    """Represents a detected risk event"""
    event_type: str
    severity: float  # 0-1 scale
    probability: float  # 0-1 scale
    description: str
    affected_assets: List[str]
    timestamp: datetime
    indicators: Dict[str, float]

class CorrelationMonitor:
    """Monitors asset correlations for breakdown detection"""
    
    def __init__(self, window_days: int = 30):
        self.window_days = window_days
        self.correlation_history = deque(maxlen=1000)
        self.price_history = defaultdict(lambda: deque(maxlen=window_days * 24))  # Hourly data
        
    def add_price_data(self, symbol: str, price: float, timestamp: datetime):
        """Add price data for correlation calculation"""
        self.price_history[symbol].append({
            'price': price,
            'timestamp': timestamp
        })
    
    def calculate_correlations(self) -> Dict[str, Dict[str, float]]:
        """Calculate current correlation matrix"""
        try:
            symbols = list(self.price_history.keys())
            if len(symbols) < 2:
                return {}
            
            # Prepare data for correlation calculation
            price_data = {}
            min_length = min(len(self.price_history[symbol]) for symbol in symbols)
            
            if min_length < 24:  # Need at least 24 hours of data
                return {}
            
            for symbol in symbols:
                prices = [data['price'] for data in list(self.price_history[symbol])[-min_length:]]
                price_data[symbol] = np.array(prices)
            
            # Calculate correlation matrix
            correlations = {}
            for i, symbol1 in enumerate(symbols):
                correlations[symbol1] = {}
                for j, symbol2 in enumerate(symbols):
                    if i != j:
                        corr = np.corrcoef(price_data[symbol1], price_data[symbol2])[0, 1]
                        correlations[symbol1][symbol2] = corr if not np.isnan(corr) else 0.0
                    else:
                        correlations[symbol1][symbol2] = 1.0
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            return {}
    
    def detect_correlation_breakdown(self, current_correlations: Dict, 
                                   historical_correlations: Dict, 
                                   threshold: float = 0.3) -> List[RiskEvent]:
        """Detect significant correlation breakdowns"""
        events = []
        
        try:
            for symbol1 in current_correlations:
                for symbol2 in current_correlations[symbol1]:
                    if symbol1 >= symbol2:  # Avoid duplicates
                        continue
                    
                    current_corr = current_correlations[symbol1][symbol2]
                    historical_corr = historical_correlations.get(symbol1, {}).get(symbol2, current_corr)
                    
                    correlation_drop = historical_corr - current_corr
                    
                    if correlation_drop > threshold:
                        severity = min(1.0, correlation_drop / 0.5)  # Max severity at 50% drop
                        
                        event = RiskEvent(
                            event_type='correlation_breakdown',
                            severity=severity,
                            probability=0.8,  # High confidence in correlation data
                            description=f"Correlation breakdown between {symbol1} and {symbol2}",
                            affected_assets=[symbol1, symbol2],
                            timestamp=datetime.now(),
                            indicators={
                                'current_correlation': current_corr,
                                'historical_correlation': historical_corr,
                                'correlation_drop': correlation_drop
                            }
                        )
                        events.append(event)
            
        except Exception as e:
            logger.error(f"Error detecting correlation breakdown: {e}")
        
        return events

class StablecoinMonitor:
    """Monitors stablecoin depegging events"""
    
    def __init__(self, config: Dict):
        self.stablecoins = config.get('stablecoins_to_monitor', ['USDT', 'USDC', 'DAI', 'BUSD'])
        self.depeg_threshold = config.get('depeg_threshold', 0.02)  # 2% deviation
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        
    def add_stablecoin_price(self, symbol: str, price: float, timestamp: datetime):
        """Add stablecoin price data"""
        if symbol in self.stablecoins:
            self.price_history[symbol].append({
                'price': price,
                'timestamp': timestamp
            })
    
    def detect_depeg_events(self) -> List[RiskEvent]:
        """Detect stablecoin depegging events"""
        events = []
        
        try:
            for stablecoin in self.stablecoins:
                if len(self.price_history[stablecoin]) < 10:
                    continue
                
                recent_prices = [data['price'] for data in list(self.price_history[stablecoin])[-10:]]
                avg_price = np.mean(recent_prices)
                deviation = abs(avg_price - 1.0)
                
                if deviation > self.depeg_threshold:
                    severity = min(1.0, deviation / 0.1)  # Max severity at 10% deviation
                    
                    event = RiskEvent(
                        event_type='stablecoin_depeg',
                        severity=severity,
                        probability=0.9,  # High confidence in price data
                        description=f"{stablecoin} depegging detected",
                        affected_assets=[stablecoin],
                        timestamp=datetime.now(),
                        indicators={
                            'current_price': avg_price,
                            'deviation_percent': deviation * 100,
                            'threshold_percent': self.depeg_threshold * 100
                        }
                    )
                    events.append(event)
            
        except Exception as e:
            logger.error(f"Error detecting depeg events: {e}")
        
        return events

class LiquidityMonitor:
    """Monitors liquidity across DeFi protocols"""
    
    def __init__(self, config: Dict):
        self.protocols = config.get('liquidity_protocols', ['uniswap', 'curve', 'balancer'])
        self.crisis_threshold = config.get('liquidity_crisis_threshold', 0.40)  # 40% drop
        self.liquidity_history = defaultdict(lambda: deque(maxlen=100))
        
    def add_liquidity_data(self, protocol: str, symbol: str, liquidity: float, timestamp: datetime):
        """Add liquidity data for a protocol"""
        key = f"{protocol}_{symbol}"
        self.liquidity_history[key].append({
            'liquidity': liquidity,
            'timestamp': timestamp
        })
    
    def detect_liquidity_crisis(self) -> List[RiskEvent]:
        """Detect liquidity crisis events"""
        events = []
        
        try:
            for key, history in self.liquidity_history.items():
                if len(history) < 20:
                    continue
                
                recent_liquidity = [data['liquidity'] for data in list(history)[-10:]]
                historical_liquidity = [data['liquidity'] for data in list(history)[-20:-10]]
                
                if not recent_liquidity or not historical_liquidity:
                    continue
                
                recent_avg = np.mean(recent_liquidity)
                historical_avg = np.mean(historical_liquidity)
                
                if historical_avg > 0:
                    liquidity_drop = (historical_avg - recent_avg) / historical_avg
                    
                    if liquidity_drop > self.crisis_threshold:
                        protocol, symbol = key.split('_', 1)
                        severity = min(1.0, liquidity_drop / 0.6)  # Max severity at 60% drop
                        
                        event = RiskEvent(
                            event_type='liquidity_crisis',
                            severity=severity,
                            probability=0.8,
                            description=f"Liquidity crisis in {protocol} for {symbol}",
                            affected_assets=[symbol],
                            timestamp=datetime.now(),
                            indicators={
                                'protocol': protocol,
                                'current_liquidity': recent_avg,
                                'historical_liquidity': historical_avg,
                                'liquidity_drop_percent': liquidity_drop * 100
                            }
                        )
                        events.append(event)
            
        except Exception as e:
            logger.error(f"Error detecting liquidity crisis: {e}")
        
        return events

class QuantumRiskPredictor:
    """
    Advanced risk predictor with black swan detection capabilities
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize monitors
        self.correlation_monitor = CorrelationMonitor(
            window_days=config.get('correlation_window_days', 30)
        )
        self.stablecoin_monitor = StablecoinMonitor(config)
        self.liquidity_monitor = LiquidityMonitor(config)
        
        # Risk thresholds
        self.black_swan_action_threshold = config.get('black_swan_action_threshold', 0.60)
        self.emergency_mode_threshold = config.get('emergency_mode_threshold', 0.80)
        self.correlation_breakdown_threshold = config.get('correlation_breakdown_threshold', 0.80)
        
        # Risk tracking
        self.risk_events = deque(maxlen=1000)
        self.black_swan_probability = 0.0
        self.overall_risk_score = 0.0
        self.emergency_mode = False
        
        # Historical data for baseline
        self.historical_correlations = {}
        self.market_data_history = defaultdict(lambda: deque(maxlen=1000))
        
        self.is_running = False
        
        logger.info("Quantum Risk Predictor initialized")

    async def start(self):
        """Start risk prediction monitoring"""
        try:
            self.is_running = True
            
            # Start monitoring tasks
            asyncio.create_task(self._collect_market_data())
            asyncio.create_task(self._analyze_risk_indicators())
            asyncio.create_task(self._update_risk_scores())
            
            logger.info("🛡️ Quantum Risk Predictor started")
            
        except Exception as e:
            logger.error(f"Failed to start risk predictor: {e}")

    async def stop(self):
        """Stop risk prediction monitoring"""
        self.is_running = False
        logger.info("🛑 Quantum Risk Predictor stopped")

    async def get_risk_predictions(self) -> Dict:
        """Get current risk predictions"""
        try:
            # Get recent risk events
            recent_events = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for event in self.risk_events:
                if event.timestamp > cutoff_time:
                    recent_events.append({
                        'type': event.event_type,
                        'severity': event.severity,
                        'probability': event.probability,
                        'description': event.description,
                        'affected_assets': event.affected_assets,
                        'indicators': event.indicators
                    })
            
            # Calculate aggregate risk metrics
            correlation_risk = await self._calculate_correlation_risk()
            stablecoin_risk = await self._calculate_stablecoin_risk()
            liquidity_risk = await self._calculate_liquidity_risk()
            
            return {
                'black_swan_probability': self.black_swan_probability,
                'overall_risk_score': self.overall_risk_score,
                'emergency_mode': self.emergency_mode,
                'correlation_risk': correlation_risk,
                'stablecoin_risk': stablecoin_risk,
                'liquidity_risk': liquidity_risk,
                'recent_events': recent_events,
                'risk_breakdown': {
                    'correlation': correlation_risk * 0.4,
                    'stablecoin': stablecoin_risk * 0.3,
                    'liquidity': liquidity_risk * 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting risk predictions: {e}")
            return {'error': str(e)}

    async def _collect_market_data(self):
        """Collect market data for risk analysis"""
        while self.is_running:
            try:
                # Simulate market data collection
                await self._simulate_market_data()
                
                await asyncio.sleep(300)  # Collect every 5 minutes
                
            except Exception as e:
                logger.error(f"Error collecting market data: {e}")
                await asyncio.sleep(300)

    async def _simulate_market_data(self):
        """Simulate market data for testing"""
        try:
            import random
            
            # Use valid Binance testnet symbols
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']
            stablecoins = ['USDT', 'USDC', 'DAI', 'BUSD']
            
            timestamp = datetime.now()
            
            # Simulate crypto prices
            for symbol in symbols:
                base_prices = {
                    'BTCUSDT': 50000,
                    'ETHUSDT': 3000,
                    'ADAUSDT': 1.2,
                    'DOTUSDT': 25,
                    'BNBUSDT': 300
                }
                
                base_price = base_prices.get(symbol, 1000)
                
                # Add some volatility
                price_change = random.uniform(-0.05, 0.05)  # ±5%
                price = base_price * (1 + price_change)
                
                # Add to correlation monitor
                self.correlation_monitor.add_price_data(symbol, price, timestamp)
                
                # Store in history
                self.market_data_history[symbol].append({
                    'price': price,
                    'timestamp': timestamp
                })
            
            # Simulate stablecoin prices
            for stablecoin in stablecoins:
                # Usually close to $1, but sometimes depeg
                if random.random() < 0.05:  # 5% chance of depeg event
                    price = random.uniform(0.95, 1.05)  # ±5% depeg
                else:
                    price = random.uniform(0.998, 1.002)  # Normal ±0.2%
                
                self.stablecoin_monitor.add_stablecoin_price(stablecoin, price, timestamp)
            
            # Simulate liquidity data
            protocols = ['uniswap', 'curve', 'balancer']
            for protocol in protocols:
                for symbol in symbols[:3]:  # Limit to 3 symbols
                    base_liquidity = random.uniform(1000000, 10000000)  # $1M - $10M
                    liquidity_change = random.uniform(-0.2, 0.1)  # -20% to +10%
                    liquidity = base_liquidity * (1 + liquidity_change)
                    
                    self.liquidity_monitor.add_liquidity_data(protocol, symbol, liquidity, timestamp)
            
        except Exception as e:
            logger.error(f"Error simulating market data: {e}")

    async def _analyze_risk_indicators(self):
        """Analyze various risk indicators"""
        while self.is_running:
            try:
                # Detect correlation breakdowns
                current_correlations = self.correlation_monitor.calculate_correlations()
                if current_correlations and self.historical_correlations:
                    correlation_events = self.correlation_monitor.detect_correlation_breakdown(
                        current_correlations, self.historical_correlations
                    )
                    self.risk_events.extend(correlation_events)
                
                # Update historical correlations baseline
                if current_correlations:
                    self.historical_correlations = current_correlations
                
                # Detect stablecoin depeg events
                depeg_events = self.stablecoin_monitor.detect_depeg_events()
                self.risk_events.extend(depeg_events)
                
                # Detect liquidity crises
                liquidity_events = self.liquidity_monitor.detect_liquidity_crisis()
                self.risk_events.extend(liquidity_events)
                
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                logger.error(f"Error analyzing risk indicators: {e}")
                await asyncio.sleep(60)

    async def _update_risk_scores(self):
        """Update overall risk scores and black swan probability"""
        while self.is_running:
            try:
                # Calculate component risk scores
                correlation_risk = await self._calculate_correlation_risk()
                stablecoin_risk = await self._calculate_stablecoin_risk()
                liquidity_risk = await self._calculate_liquidity_risk()
                
                # Calculate overall risk score (weighted average)
                self.overall_risk_score = (
                    correlation_risk * 0.4 +
                    stablecoin_risk * 0.3 +
                    liquidity_risk * 0.3
                )
                
                # Calculate black swan probability
                self.black_swan_probability = await self._calculate_black_swan_probability(
                    correlation_risk, stablecoin_risk, liquidity_risk
                )
                
                # Update emergency mode
                if self.black_swan_probability > self.emergency_mode_threshold:
                    if not self.emergency_mode:
                        logger.critical(f"🚨 EMERGENCY MODE ACTIVATED! Black Swan Probability: {self.black_swan_probability:.1%}")
                        self.emergency_mode = True
                elif self.black_swan_probability < self.emergency_mode_threshold * 0.8:
                    if self.emergency_mode:
                        logger.info(f"✅ Emergency mode deactivated. Risk level normalized.")
                        self.emergency_mode = False
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error updating risk scores: {e}")
                await asyncio.sleep(60)

    async def _calculate_correlation_risk(self) -> float:
        """Calculate correlation breakdown risk"""
        try:
            recent_events = [
                event for event in self.risk_events
                if event.event_type == 'correlation_breakdown' and
                event.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            if not recent_events:
                return 0.0
            
            # Weight by severity and recency
            risk_score = 0.0
            for event in recent_events:
                age_hours = (datetime.now() - event.timestamp).seconds / 3600
                time_weight = max(0, 1 - age_hours / 24)  # Decay over 24 hours
                risk_score += event.severity * time_weight
            
            return min(1.0, risk_score / len(recent_events))
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0.0

    async def _calculate_stablecoin_risk(self) -> float:
        """Calculate stablecoin depegging risk"""
        try:
            recent_events = [
                event for event in self.risk_events
                if event.event_type == 'stablecoin_depeg' and
                event.timestamp > datetime.now() - timedelta(hours=6)
            ]
            
            if not recent_events:
                return 0.0
            
            # Calculate weighted risk
            total_severity = sum(event.severity for event in recent_events)
            max_possible_severity = len(self.stablecoin_monitor.stablecoins)
            
            return min(1.0, total_severity / max_possible_severity)
            
        except Exception as e:
            logger.error(f"Error calculating stablecoin risk: {e}")
            return 0.0

    async def _calculate_liquidity_risk(self) -> float:
        """Calculate liquidity crisis risk"""
        try:
            recent_events = [
                event for event in self.risk_events
                if event.event_type == 'liquidity_crisis' and
                event.timestamp > datetime.now() - timedelta(hours=2)
            ]
            
            if not recent_events:
                return 0.0
            
            # Calculate average severity
            avg_severity = sum(event.severity for event in recent_events) / len(recent_events)
            
            return min(1.0, avg_severity)
            
        except Exception as e:
            logger.error(f"Error calculating liquidity risk: {e}")
            return 0.0

    async def _calculate_black_swan_probability(self, correlation_risk: float, 
                                              stablecoin_risk: float, liquidity_risk: float) -> float:
        """Calculate black swan event probability"""
        try:
            # Base probability from individual risks
            base_probability = (correlation_risk * 0.4 + stablecoin_risk * 0.3 + liquidity_risk * 0.3)
            
            # Amplification factor when multiple risks are high
            risk_count = sum(1 for risk in [correlation_risk, stablecoin_risk, liquidity_risk] if risk > 0.5)
            
            if risk_count >= 2:
                amplification = 1.5  # 50% amplification
            elif risk_count >= 1:
                amplification = 1.2  # 20% amplification
            else:
                amplification = 1.0
            
            # Historical volatility factor (simplified)
            volatility_factor = await self._calculate_market_volatility()
            
            black_swan_prob = base_probability * amplification * (1 + volatility_factor)
            
            return min(1.0, black_swan_prob)
            
        except Exception as e:
            logger.error(f"Error calculating black swan probability: {e}")
            return 0.0

    async def _calculate_market_volatility(self) -> float:
        """Calculate current market volatility factor"""
        try:
            volatilities = []
            
            for symbol, history in self.market_data_history.items():
                if len(history) < 24:  # Need at least 24 data points
                    continue
                
                prices = [data['price'] for data in list(history)[-24:]]
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns)
                volatilities.append(volatility)
            
            if not volatilities:
                return 0.0
            
            avg_volatility = np.mean(volatilities)
            
            # Normalize to 0-1 scale (0.1 = high volatility threshold)
            return min(1.0, avg_volatility / 0.1)
            
        except Exception as e:
            logger.error(f"Error calculating market volatility: {e}")
            return 0.0

    def get_performance_metrics(self) -> Dict:
        """Get risk predictor performance metrics"""
        try:
            recent_events = len([
                event for event in self.risk_events
                if event.timestamp > datetime.now() - timedelta(hours=24)
            ])
            
            event_breakdown = defaultdict(int)
            for event in self.risk_events:
                if event.timestamp > datetime.now() - timedelta(hours=24):
                    event_breakdown[event.event_type] += 1
            
            return {
                'black_swan_probability': self.black_swan_probability,
                'overall_risk_score': self.overall_risk_score,
                'emergency_mode': self.emergency_mode,
                'events_24h': recent_events,
                'event_breakdown': dict(event_breakdown),
                'correlation_pairs_monitored': len(self.correlation_monitor.price_history),
                'stablecoins_monitored': len(self.stablecoin_monitor.stablecoins),
                'liquidity_pools_monitored': len(self.liquidity_monitor.liquidity_history)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {} 
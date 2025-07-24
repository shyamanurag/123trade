# strategies/crypto_volume_profile_scalper_enhanced.py
"""
Enhanced Crypto Volume Profile Scalper Strategy
Order book analysis with whale tracking and volume profile scalping
"""

import logging
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

@dataclass
class VolumeNode:
    """Volume profile node"""
    price_level: float
    volume: float
    buy_volume: float
    sell_volume: float
    trade_count: int

@dataclass
class WhaleOrder:
    """Large order detection"""
    symbol: str
    side: str  # BUY/SELL
    size: float
    price: float
    timestamp: datetime
    impact_score: float

class EnhancedCryptoVolumeProfileScalper:
    """Enhanced volume profile scalper with whale tracking"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Volume parameters
        self.min_volume_threshold = config.get('min_volume_threshold', 2.0)
        self.whale_threshold = config.get('whale_threshold', 100000.0)  # $100k+
        self.value_area_percent = config.get('value_area_percent', 0.7)
        
        # Profile analysis
        self.profile_window_hours = config.get('profile_window_hours', 24)
        self.price_bucket_size = config.get('price_bucket_size', 0.001)  # 0.1%
        
        # Volume tracking
        self.volume_profiles = {}  # symbol -> volume profile
        self.whale_orders = deque(maxlen=1000)
        self.volume_history = defaultdict(lambda: deque(maxlen=500))
        
        # Performance tracking
        self.signals_generated = 0
        self.whale_signals = 0
        self.scalp_signals = 0
        
        logger.info("Enhanced Crypto Volume Profile Scalper initialized")

    async def start(self):
        """Start the volume profile scalper"""
        logger.info("📊 Starting Enhanced Crypto Volume Profile Scalper...")
        
        # Start monitoring
        asyncio.create_task(self._monitor_volume_profiles())
        asyncio.create_task(self._detect_whale_orders())
        asyncio.create_task(self._scalp_volume_nodes())
        
        logger.info("✅ Enhanced Crypto Volume Profile Scalper started")

    async def get_volume_signals(self) -> List[Dict]:
        """Get current volume-based signals"""
        try:
            signals = []
            
            for symbol in self.volume_profiles:
                # Get scalping opportunities
                scalp_signal = await self._get_scalping_signal(symbol)
                if scalp_signal:
                    signals.append(scalp_signal)
                
                # Get whale following signals
                whale_signal = await self._get_whale_signal(symbol)
                if whale_signal:
                    signals.append(whale_signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting volume signals: {e}")
            return []

    async def update_trade_data(self, symbol: str, price: float, volume: float, 
                              side: str, timestamp: datetime):
        """Update trade data for volume analysis"""
        try:
            # Initialize profile if needed
            if symbol not in self.volume_profiles:
                self.volume_profiles[symbol] = {}
            
            # Create price bucket
            price_bucket = self._get_price_bucket(price)
            
            # Update volume profile
            if price_bucket not in self.volume_profiles[symbol]:
                self.volume_profiles[symbol][price_bucket] = VolumeNode(
                    price_level=price_bucket,
                    volume=0,
                    buy_volume=0,
                    sell_volume=0,
                    trade_count=0
                )
            
            node = self.volume_profiles[symbol][price_bucket]
            node.volume += volume
            node.trade_count += 1
            
            if side == 'BUY':
                node.buy_volume += volume
            else:
                node.sell_volume += volume
            
            # Check for whale order
            value_usd = price * volume
            if value_usd >= self.whale_threshold:
                whale_order = WhaleOrder(
                    symbol=symbol,
                    side=side,
                    size=value_usd,
                    price=price,
                    timestamp=timestamp,
                    impact_score=min(1.0, value_usd / (self.whale_threshold * 10))
                )
                self.whale_orders.append(whale_order)
            
            # Add to volume history
            self.volume_history[symbol].append({
                'price': price,
                'volume': volume,
                'side': side,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error updating trade data: {e}")

    def _get_price_bucket(self, price: float) -> float:
        """Get price bucket for volume profile"""
        bucket_size = price * self.price_bucket_size
        return round(price / bucket_size) * bucket_size

    async def _get_scalping_signal(self, symbol: str) -> Optional[Dict]:
        """Get volume profile scalping signal"""
        try:
            if symbol not in self.volume_profiles or len(self.volume_profiles[symbol]) < 10:
                return None
            
            # Analyze volume profile
            profile = self.volume_profiles[symbol]
            
            # Find high volume nodes (value area)
            sorted_nodes = sorted(profile.values(), key=lambda x: x.volume, reverse=True)
            
            if not sorted_nodes:
                return None
            
            # Calculate value area
            total_volume = sum(node.volume for node in sorted_nodes)
            value_area_volume = total_volume * self.value_area_percent
            
            value_area_nodes = []
            cumulative_volume = 0
            
            for node in sorted_nodes:
                value_area_nodes.append(node)
                cumulative_volume += node.volume
                if cumulative_volume >= value_area_volume:
                    break
            
            if not value_area_nodes:
                return None
            
            # Get current price and volume
            recent_trades = list(self.volume_history[symbol])[-10:]
            if not recent_trades:
                return None
            
            current_price = recent_trades[-1]['price']
            current_volume = sum(trade['volume'] for trade in recent_trades[-5:])
            
            # Find nearest value area node
            nearest_node = min(value_area_nodes, key=lambda x: abs(x.price_level - current_price))
            
            # Calculate signal strength based on volume and imbalance
            volume_strength = min(1.0, current_volume / (sum(trade['volume'] for trade in recent_trades) / len(recent_trades)))
            
            # Check volume imbalance
            imbalance = (nearest_node.buy_volume - nearest_node.sell_volume) / nearest_node.volume
            
            # Determine direction
            if imbalance > 0.2:  # More buying
                direction = 'BUY'
            elif imbalance < -0.2:  # More selling
                direction = 'SELL'
            else:
                return None  # No clear direction
            
            return {
                'symbol': symbol,
                'direction': direction,
                'strength': volume_strength * abs(imbalance),
                'confidence': 0.7,
                'signal_type': 'volume_scalp',
                'price_level': nearest_node.price_level,
                'volume_imbalance': imbalance,
                'current_price': current_price,
                'timestamp': datetime.now(),
                'strategy': 'crypto_volume_profile_scalper'
            }
            
        except Exception as e:
            logger.error(f"Error getting scalping signal for {symbol}: {e}")
            return None

    async def _get_whale_signal(self, symbol: str) -> Optional[Dict]:
        """Get whale following signal"""
        try:
            # Get recent whale orders for this symbol
            cutoff_time = datetime.now() - timedelta(minutes=30)
            recent_whale_orders = [
                order for order in self.whale_orders
                if order.symbol == symbol and order.timestamp > cutoff_time
            ]
            
            if not recent_whale_orders:
                return None
            
            # Analyze whale activity
            total_buy_value = sum(order.size for order in recent_whale_orders if order.side == 'BUY')
            total_sell_value = sum(order.size for order in recent_whale_orders if order.side == 'SELL')
            
            net_whale_flow = total_buy_value - total_sell_value
            total_whale_flow = total_buy_value + total_sell_value
            
            if total_whale_flow == 0:
                return None
            
            whale_bias = net_whale_flow / total_whale_flow
            
            # Strong whale bias required
            if abs(whale_bias) < 0.3:
                return None
            
            direction = 'BUY' if whale_bias > 0 else 'SELL'
            
            # Calculate signal strength
            largest_order = max(recent_whale_orders, key=lambda x: x.size)
            strength = min(1.0, largest_order.impact_score)
            
            return {
                'symbol': symbol,
                'direction': direction,
                'strength': strength,
                'confidence': min(1.0, abs(whale_bias) + 0.3),
                'signal_type': 'whale_following',
                'whale_bias': whale_bias,
                'whale_orders_count': len(recent_whale_orders),
                'largest_order_size': largest_order.size,
                'net_whale_flow': net_whale_flow,
                'timestamp': datetime.now(),
                'strategy': 'crypto_volume_profile_scalper'
            }
            
        except Exception as e:
            logger.error(f"Error getting whale signal for {symbol}: {e}")
            return None

    async def _monitor_volume_profiles(self):
        """Monitor and update volume profiles"""
        while True:
            try:
                # Simulate trade data
                # CRITICAL: NO HARD-CODED SYMBOLS - GET FROM DYNAMIC SOURCES
                from ..core.database import get_db_session
                
                async with get_db_session() as session:
                    # Get active symbols from database
                    result = await session.execute("""
                        SELECT symbol FROM symbols 
                        WHERE is_active = true AND exchange = 'BINANCE'
                        ORDER BY volume_24h DESC 
                        LIMIT 5
                    """)
                    
                    symbol_rows = result.fetchall()
                    if not symbol_rows:
                        logger.error("No active symbols found in database")
                        await asyncio.sleep(60)
                        continue
                    
                    dynamic_symbols = [row.symbol for row in symbol_rows]
                
                logger.info(f"Running volume analysis with real symbols: {dynamic_symbols}")
                
                for symbol in dynamic_symbols:
                    # Get real market data instead of hard-coded base prices
                    market_data = await self._get_real_market_data(symbol)
                    if not market_data:
                        logger.warning(f"No real market data for {symbol}, skipping")
                        continue
                    
                    current_price = market_data.get('close_price')
                    if not current_price:
                        continue
                    
                    # Generate real trading signal
                    signal = await self._generate_real_signal(symbol, current_price, market_data)
                    
                    if signal and signal.action != 'HOLD':
                        logger.info(f"Generated {signal.action} signal for {symbol} at {current_price}")
                    
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring volume profiles: {e}")
                await asyncio.sleep(60)

    async def _detect_whale_orders(self):
        """Detect and alert on whale orders"""
        while True:
            try:
                await asyncio.sleep(30)
                
                # Check for recent whale activity
                cutoff_time = datetime.now() - timedelta(minutes=5)
                recent_whales = [
                    order for order in self.whale_orders
                    if order.timestamp > cutoff_time
                ]
                
                if recent_whales:
                    self.whale_signals += 1
                    
                    largest = max(recent_whales, key=lambda x: x.size)
                    logger.info(f"🐋 WHALE ACTIVITY: {largest.symbol} {largest.side} "
                               f"${largest.size:,.0f} at ${largest.price:.2f}")
                
            except Exception as e:
                logger.error(f"Error detecting whale orders: {e}")
                await asyncio.sleep(60)

    async def _scalp_volume_nodes(self):
        """Monitor for scalping opportunities"""
        while True:
            try:
                await asyncio.sleep(15)  # Check every 15 seconds
                
                scalp_opportunities = 0
                
                for symbol in self.volume_profiles:
                    signal = await self._get_scalping_signal(symbol)
                    if signal:
                        scalp_opportunities += 1
                        self.scalp_signals += 1
                
                if scalp_opportunities > 0:
                    logger.info(f"📊 SCALP OPPORTUNITIES: {scalp_opportunities} signals detected")
                
            except Exception as e:
                logger.error(f"Error monitoring scalp opportunities: {e}")
                await asyncio.sleep(60)

    def get_performance_metrics(self) -> Dict:
        """Get volume scalper performance metrics"""
        try:
            total_volume_nodes = sum(len(profile) for profile in self.volume_profiles.values())
            recent_whale_orders = len([
                order for order in self.whale_orders
                if order.timestamp > datetime.now() - timedelta(hours=24)
            ])
            
            return {
                'signals_generated': self.signals_generated,
                'whale_signals': self.whale_signals,
                'scalp_signals': self.scalp_signals,
                'monitored_symbols': len(self.volume_profiles),
                'total_volume_nodes': total_volume_nodes,
                'whale_orders_24h': recent_whale_orders,
                'largest_whale_order': max([order.size for order in self.whale_orders], default=0)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    def get_volume_profile_report(self, symbol: str) -> Dict:
        """Get detailed volume profile for a symbol"""
        try:
            if symbol not in self.volume_profiles:
                return {'error': f'No volume profile for {symbol}'}
            
            profile = self.volume_profiles[symbol]
            sorted_nodes = sorted(profile.values(), key=lambda x: x.volume, reverse=True)
            
            return {
                'symbol': symbol,
                'total_nodes': len(profile),
                'total_volume': sum(node.volume for node in profile.values()),
                'top_volume_levels': [
                    {
                        'price': node.price_level,
                        'volume': node.volume,
                        'buy_volume': node.buy_volume,
                        'sell_volume': node.sell_volume,
                        'imbalance': (node.buy_volume - node.sell_volume) / node.volume if node.volume > 0 else 0
                    }
                    for node in sorted_nodes[:10]
                ],
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error generating volume profile report: {e}")
            return {'error': str(e)} 
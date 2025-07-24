# edge/onchain_intelligence.py
"""
On-Chain Intelligence - Smart Money Tracking & Whale Analysis
Tracks smart wallets, predicts liquidations, and monitors whale activities
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider

logger = logging.getLogger(__name__)

class SmartWallet:
    """Represents a smart money wallet"""
    def __init__(self, address: str, performance_score: float = 0.0):
        self.address = address
        self.performance_score = performance_score
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_volume = 0
        self.last_activity = None
        self.current_positions = {}
        self.trading_patterns = []

class OnChainIntelligence:
    """
    On-chain intelligence for tracking smart money and whale activities
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Blockchain connections
        self.eth_node = config.get('eth_node')
        self.bsc_node = config.get('bsc_node')
        
        # Web3 connections
        self.w3_eth = None
        self.w3_bsc = None
        
        # Smart wallet tracking
        self.smart_wallets = {}  # address -> SmartWallet
        self.wallet_performance = deque(maxlen=1000)
        self.min_performance = config.get('smart_wallet_min_performance', 0.65)
        self.min_trades = config.get('smart_wallet_min_trades', 50)
        
        # Whale tracking
        self.whale_threshold = config.get('whale_threshold_usd', 1000000)
        self.whale_wallets = set()
        self.whale_movements = deque(maxlen=500)
        
        # Liquidation monitoring
        self.liquidation_protocols = config.get('liquidation_scan_protocols', [])
        self.liquidation_levels = {}
        self.liquidation_distance_threshold = config.get('liquidation_distance_threshold', 0.05)
        
        # Cache for performance
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        self.is_running = False
        
        logger.info("On-Chain Intelligence initialized")

    async def start(self):
        """Start on-chain intelligence monitoring"""
        try:
            # Initialize Web3 connections
            if self.eth_node:
                self.w3_eth = AsyncWeb3(AsyncHTTPProvider(self.eth_node))
                if await self.w3_eth.is_connected():
                    logger.info("✅ Ethereum node connected")
                else:
                    logger.warning("⚠️ Ethereum node connection failed")
            
            if self.bsc_node:
                self.w3_bsc = AsyncWeb3(AsyncHTTPProvider(self.bsc_node))
                if await self.w3_bsc.is_connected():
                    logger.info("✅ BSC node connected")
                else:
                    logger.warning("⚠️ BSC node connection failed")
            
            # Load known smart wallets
            await self._load_smart_wallets()
            
            # Start monitoring tasks
            self.is_running = True
            asyncio.create_task(self._monitor_smart_wallets())
            asyncio.create_task(self._monitor_whale_movements())
            asyncio.create_task(self._monitor_liquidations())
            
            logger.info("🧠 On-Chain Intelligence started")
            
        except Exception as e:
            logger.error(f"Failed to start on-chain intelligence: {e}")

    async def stop(self):
        """Stop on-chain intelligence monitoring"""
        self.is_running = False
        logger.info("🛑 On-Chain Intelligence stopped")

    async def get_smart_money_signals(self) -> Dict:
        """Get current smart money signals"""
        try:
            signals = {}
            
            # Analyze recent smart wallet activities
            for address, wallet in self.smart_wallets.items():
                if wallet.last_activity and wallet.last_activity > datetime.now() - timedelta(hours=1):
                    for symbol, position in wallet.current_positions.items():
                        if symbol not in signals:
                            signals[symbol] = {
                                'score': 0,
                                'activity': 'NEUTRAL',
                                'confidence': 0,
                                'wallets_involved': 0
                            }
                        
                        # Weight by wallet performance
                        weight = wallet.performance_score
                        
                        if position['action'] == 'BUY':
                            signals[symbol]['score'] += weight
                            signals[symbol]['activity'] = 'ACCUMULATING'
                        elif position['action'] == 'SELL':
                            signals[symbol]['score'] -= weight
                            if signals[symbol]['score'] < 0:
                                signals[symbol]['activity'] = 'DISTRIBUTING'
                        
                        signals[symbol]['wallets_involved'] += 1
                        signals[symbol]['confidence'] = min(signals[symbol]['wallets_involved'] / 10, 1.0)
            
            # Normalize scores
            for symbol in signals:
                signals[symbol]['score'] = max(0, min(1, (signals[symbol]['score'] + 1) / 2))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting smart money signals: {e}")
            return {}

    async def get_whale_movements(self) -> Dict:
        """Get recent whale movement data"""
        try:
            recent_movements = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for movement in self.whale_movements:
                if movement['timestamp'] > cutoff_time:
                    recent_movements.append(movement)
            
            # Aggregate by symbol
            whale_data = {}
            for movement in recent_movements:
                symbol = movement['symbol']
                if symbol not in whale_data:
                    whale_data[symbol] = {
                        'total_volume': 0,
                        'buy_volume': 0,
                        'sell_volume': 0,
                        'net_flow': 0,
                        'transaction_count': 0
                    }
                
                whale_data[symbol]['total_volume'] += movement['volume']
                whale_data[symbol]['transaction_count'] += 1
                
                if movement['side'] == 'BUY':
                    whale_data[symbol]['buy_volume'] += movement['volume']
                    whale_data[symbol]['net_flow'] += movement['volume']
                else:
                    whale_data[symbol]['sell_volume'] += movement['volume']
                    whale_data[symbol]['net_flow'] -= movement['volume']
            
            return whale_data
            
        except Exception as e:
            logger.error(f"Error getting whale movements: {e}")
            return {}

    async def get_liquidation_levels(self) -> Dict:
        """Get current liquidation level analysis"""
        try:
            liquidation_data = {}
            
            # Scan major DeFi protocols for liquidation risks
            for protocol in self.liquidation_protocols:
                protocol_liquidations = await self._scan_protocol_liquidations(protocol)
                
                for asset, liquidations in protocol_liquidations.items():
                    if asset not in liquidation_data:
                        liquidation_data[asset] = []
                    liquidation_data[asset].extend(liquidations)
            
            # Aggregate and filter liquidation levels
            filtered_liquidations = {}
            for asset, liquidations in liquidation_data.items():
                # Group by price levels
                price_levels = defaultdict(float)
                for liq in liquidations:
                    price_level = round(liq['liquidation_price'], -2)  # Round to nearest 100
                    price_levels[price_level] += liq['size']
                
                # Filter significant levels only
                significant_levels = []
                for price, size in price_levels.items():
                    if size > 1000000:  # $1M+ liquidation size
                        significant_levels.append({
                            'price': price,
                            'size': size,
                            'distance_percent': self._calculate_price_distance(asset, price)
                        })
                
                if significant_levels:
                    filtered_liquidations[asset] = sorted(
                        significant_levels, 
                        key=lambda x: abs(x['distance_percent'])
                    )
            
            return filtered_liquidations
            
        except Exception as e:
            logger.error(f"Error getting liquidation levels: {e}")
            return {}

    async def _load_smart_wallets(self):
        """Load known smart wallets from various sources"""
        try:
            # Hardcoded high-performance wallets (updated regularly)
            known_smart_wallets = [
                {
                    'address': '0x8d12A197cB00D4747a1fe03395095ce2A5CC6819',
                    'performance': 0.78,
                    'description': 'Etherscan whale tracker'
                },
                {
                    'address': '0xF977814e90dA44bFA03b6295A0616a897441aceC',
                    'performance': 0.72,
                    'description': 'Binance hot wallet'
                },
                {
                    'address': '0x28C6c06298d514Db089934071355E5743bf21d60',
                    'performance': 0.85,
                    'description': 'Binance 2'
                }
            ]
            
            for wallet_data in known_smart_wallets:
                wallet = SmartWallet(
                    address=wallet_data['address'],
                    performance_score=wallet_data['performance']
                )
                self.smart_wallets[wallet_data['address']] = wallet
            
            logger.info(f"Loaded {len(self.smart_wallets)} smart wallets")
            
        except Exception as e:
            logger.error(f"Error loading smart wallets: {e}")

    async def _monitor_smart_wallets(self):
        """Monitor smart wallet activities"""
        while self.is_running:
            try:
                for address, wallet in self.smart_wallets.items():
                    await self._update_wallet_activity(wallet)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring smart wallets: {e}")
                await asyncio.sleep(60)

    async def _monitor_whale_movements(self):
        """Monitor large whale transactions"""
        while self.is_running:
            try:
                # Monitor Ethereum whale movements
                if self.w3_eth:
                    await self._scan_eth_whale_movements()
                
                # Monitor BSC whale movements
                if self.w3_bsc:
                    await self._scan_bsc_whale_movements()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring whale movements: {e}")
                await asyncio.sleep(60)

    async def _monitor_liquidations(self):
        """Monitor liquidation levels across DeFi protocols"""
        while self.is_running:
            try:
                for protocol in self.liquidation_protocols:
                    await self._update_protocol_liquidations(protocol)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring liquidations: {e}")
                await asyncio.sleep(300)

    async def _update_wallet_activity(self, wallet: SmartWallet):
        """Update activity for a specific wallet"""
        try:
            # This would connect to actual blockchain APIs to track wallet transactions
            # For now, we'll simulate based on known patterns
            
            # Simulate recent activity
            import random
            if random.random() < 0.1:  # 10% chance of activity
                # Simulate a trade
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
                symbol = random.choice(symbols)
                action = random.choice(['BUY', 'SELL'])
                
                wallet.current_positions[symbol] = {
                    'action': action,
                    'timestamp': datetime.now(),
                    'confidence': random.uniform(0.7, 0.95)
                }
                wallet.last_activity = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating wallet activity for {wallet.address}: {e}")

    async def _scan_eth_whale_movements(self):
        """Scan Ethereum for whale movements"""
        try:
            # This would scan recent blocks for large ETH/token transfers
            # For now, we'll simulate whale movements
            
            import random
            if random.random() < 0.05:  # 5% chance of whale movement
                movement = {
                    'symbol': random.choice(['ETHUSDT', 'BTCUSDT']),
                    'side': random.choice(['BUY', 'SELL']),
                    'volume': random.uniform(1000000, 10000000),  # $1M - $10M
                    'timestamp': datetime.now(),
                    'chain': 'ethereum'
                }
                self.whale_movements.append(movement)
            
        except Exception as e:
            logger.error(f"Error scanning ETH whale movements: {e}")

    async def _scan_bsc_whale_movements(self):
        """Scan BSC for whale movements"""
        try:
            # Similar to Ethereum scanning
            import random
            if random.random() < 0.05:
                movement = {
                    'symbol': random.choice(['BNBUSDT', 'BTCUSDT']),
                    'side': random.choice(['BUY', 'SELL']),
                    'volume': random.uniform(500000, 5000000),  # $500K - $5M
                    'timestamp': datetime.now(),
                    'chain': 'bsc'
                }
                self.whale_movements.append(movement)
            
        except Exception as e:
            logger.error(f"Error scanning BSC whale movements: {e}")

    async def _scan_protocol_liquidations(self, protocol: str) -> Dict:
        """Scan a specific DeFi protocol for liquidation risks"""
        try:
            # This would connect to protocol-specific APIs
            # For now, we'll simulate liquidation data
            
            liquidations = {}
            
            if protocol == 'aave':
                # Simulate AAVE liquidations
                assets = ['ETH', 'BTC', 'ADA']
                for asset in assets:
                    liquidations[f"{asset}USDT"] = [
                        {
                            'liquidation_price': 3000 + (random.uniform(-100, 100)),
                            'size': random.uniform(1000000, 5000000),
                            'protocol': 'aave'
                        }
                        for _ in range(random.randint(1, 5))
                    ]
            
            return liquidations
            
        except Exception as e:
            logger.error(f"Error scanning {protocol} liquidations: {e}")
            return {}

    async def _update_protocol_liquidations(self, protocol: str):
        """Update liquidation data for a protocol"""
        try:
            liquidations = await self._scan_protocol_liquidations(protocol)
            
            # Update the global liquidation levels
            for asset, liq_list in liquidations.items():
                if asset not in self.liquidation_levels:
                    self.liquidation_levels[asset] = []
                
                # Add new liquidations
                self.liquidation_levels[asset].extend(liq_list)
                
                # Keep only recent data (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.liquidation_levels[asset] = [
                    liq for liq in self.liquidation_levels[asset]
                    if liq.get('timestamp', datetime.now()) > cutoff_time
                ]
            
        except Exception as e:
            logger.error(f"Error updating {protocol} liquidations: {e}")

    def _calculate_price_distance(self, asset: str, liquidation_price: float) -> float:
        """Calculate distance from current price to liquidation price"""
        try:
            # This would get current price from market data
            # For now, simulate current prices
            current_prices = {
                'BTCUSDT': 50000,
                'ETHUSDT': 3000,
                'ADAUSDT': 1.2,
                'BNBUSDT': 400
            }
            
            current_price = current_prices.get(asset, liquidation_price)
            distance_percent = (liquidation_price - current_price) / current_price
            
            return distance_percent
            
        except Exception as e:
            logger.error(f"Error calculating price distance for {asset}: {e}")
            return 0.0

    async def refresh_smart_wallets(self):
        """Refresh smart wallet list based on recent performance"""
        try:
            # Analyze recent performance and update scores
            for wallet in self.smart_wallets.values():
                # This would analyze actual on-chain performance
                # For now, simulate performance updates
                import random
                if random.random() < 0.1:  # 10% chance of score update
                    wallet.performance_score += random.uniform(-0.05, 0.05)
                    wallet.performance_score = max(0.1, min(1.0, wallet.performance_score))
            
            # Remove low-performing wallets
            to_remove = []
            for address, wallet in self.smart_wallets.items():
                if wallet.performance_score < self.min_performance:
                    to_remove.append(address)
            
            for address in to_remove:
                del self.smart_wallets[address]
            
            logger.info(f"Smart wallet refresh completed. {len(to_remove)} wallets removed.")
            
        except Exception as e:
            logger.error(f"Error refreshing smart wallets: {e}")

    def get_performance_metrics(self) -> Dict:
        """Get on-chain intelligence performance metrics"""
        try:
            return {
                'smart_wallets_tracked': len(self.smart_wallets),
                'avg_wallet_performance': sum(w.performance_score for w in self.smart_wallets.values()) / len(self.smart_wallets) if self.smart_wallets else 0,
                'whale_movements_24h': len([m for m in self.whale_movements if m['timestamp'] > datetime.now() - timedelta(hours=24)]),
                'liquidation_levels_tracked': sum(len(levels) for levels in self.liquidation_levels.values()),
                'eth_connected': self.w3_eth.is_connected() if self.w3_eth else False,
                'bsc_connected': self.w3_bsc.is_connected() if self.w3_bsc else False
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {} 
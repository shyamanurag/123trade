# edge/arbitrage_engine.py
"""
Cross-Chain Arbitrage Engine - Risk-Free Profit Detection
Finds arbitrage opportunities across multiple exchanges and blockchains
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    buy_exchange: str
    sell_exchange: str
    symbol: str
    buy_price: float
    sell_price: float
    profit_percent: float
    profit_usd: float
    volume_available: float
    execution_time_estimate: float
    gas_cost_estimate: float
    net_profit: float
    confidence_score: float
    timestamp: datetime

class ExchangeConnector:
    """Connector for exchange APIs"""
    
    def __init__(self, exchange_name: str, config: Dict):
        self.name = exchange_name
        self.config = config
        self.session = None
        self.last_request_time = 0
        self.rate_limit_delay = config.get('rate_limit_delay', 0.1)
        
    async def start(self):
        """Start the exchange connector"""
        self.session = aiohttp.ClientSession()
        
    async def stop(self):
        """Stop the exchange connector"""
        if self.session:
            await self.session.close()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker data for a symbol"""
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        try:
            # This would connect to actual exchange APIs
            # For now, simulate different exchange prices
            import random
            
            base_prices = {
                'BTCUSDT': 50000,
                'ETHUSDT': 3000,
                'ADAUSDT': 1.2,
                'DOTUSDT': 25,
                'BNBUSDT': 300
            }
            
            base_price = base_prices.get(symbol, 1000)
            
            # Add exchange-specific price variations
            exchange_variations = {
                'binance': random.uniform(-0.001, 0.001),
                'coinbase': random.uniform(-0.002, 0.002),
                'kraken': random.uniform(-0.0015, 0.0015),
                'ftx': random.uniform(-0.0025, 0.0025),
                'uniswap': random.uniform(-0.005, 0.005),
                'pancakeswap': random.uniform(-0.003, 0.003)
            }
            
            variation = exchange_variations.get(self.name, 0)
            price = base_price * (1 + variation)
            
            self.last_request_time = time.time()
            
            return {
                'symbol': symbol,
                'price': price,
                'volume': random.uniform(1000000, 10000000),
                'timestamp': datetime.now(),
                'exchange': self.name
            }
            
        except Exception as e:
            logger.error(f"Error getting ticker from {self.name}: {e}")
            return None

class CrossChainArbitrageEngine:
    """
    Advanced arbitrage engine for cross-chain and cross-exchange opportunities
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Exchange configuration
        self.exchanges = {}
        self._initialize_exchanges()
        
        # Blockchain configuration
        self.chains = config.get('chains', [])
        self.dexs = config.get('dexs', {})
        
        # Arbitrage parameters
        self.min_profit_percent = config.get('min_profit_percent', 0.3)  # 0.3% minimum
        self.max_gas_price_gwei = config.get('max_gas_price_gwei', 100)
        self.flash_loan_providers = config.get('flash_loan_providers', [])
        
        # Opportunity tracking
        self.opportunities = deque(maxlen=1000)
        self.executed_arbitrages = deque(maxlen=500)
        self.price_feeds = {}
        
        # Performance tracking
        self.total_profit = 0.0
        self.success_rate = 0.0
        self.average_execution_time = 0.0
        
        # Symbols to monitor
        self.monitored_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'BNBUSDT']
        
        self.is_running = False
        
        logger.info("Cross-Chain Arbitrage Engine initialized")

    def _initialize_exchanges(self):
        """Initialize exchange connectors"""
        exchange_configs = {
            'binance': {'rate_limit_delay': 0.1},
            'coinbase': {'rate_limit_delay': 0.2},
            'kraken': {'rate_limit_delay': 0.15},
            'ftx': {'rate_limit_delay': 0.1},
            'uniswap': {'rate_limit_delay': 0.5},
            'pancakeswap': {'rate_limit_delay': 0.3}
        }
        
        for exchange_name, config in exchange_configs.items():
            self.exchanges[exchange_name] = ExchangeConnector(exchange_name, config)

    async def start(self):
        """Start the arbitrage engine"""
        try:
            # Start all exchange connectors
            for exchange in self.exchanges.values():
                await exchange.start()
            
            self.is_running = True
            
            # Start monitoring tasks
            asyncio.create_task(self._monitor_arbitrage_opportunities())
            asyncio.create_task(self._execute_arbitrages())
            asyncio.create_task(self._update_performance_metrics())
            
            logger.info("💰 Cross-Chain Arbitrage Engine started")
            
        except Exception as e:
            logger.error(f"Failed to start arbitrage engine: {e}")

    async def stop(self):
        """Stop the arbitrage engine"""
        self.is_running = False
        
        # Stop all exchange connectors
        for exchange in self.exchanges.values():
            await exchange.stop()
        
        logger.info("🛑 Cross-Chain Arbitrage Engine stopped")

    async def get_arbitrage_opportunities(self) -> Dict:
        """Get current arbitrage opportunities"""
        try:
            # Get recent opportunities (last 5 minutes)
            recent_opportunities = []
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            for opportunity in self.opportunities:
                if opportunity.timestamp > cutoff_time:
                    recent_opportunities.append({
                        'buy_exchange': opportunity.buy_exchange,
                        'sell_exchange': opportunity.sell_exchange,
                        'symbol': opportunity.symbol,
                        'profit_percent': opportunity.profit_percent,
                        'net_profit': opportunity.net_profit,
                        'confidence_score': opportunity.confidence_score,
                        'execution_time_estimate': opportunity.execution_time_estimate
                    })
            
            # Group by symbol
            opportunities_by_symbol = defaultdict(list)
            for opp in recent_opportunities:
                opportunities_by_symbol[opp['symbol']].append(opp)
            
            # Return best opportunity per symbol
            best_opportunities = {}
            for symbol, opps in opportunities_by_symbol.items():
                best_opp = max(opps, key=lambda x: x['net_profit'])
                best_opportunities[symbol] = best_opp
            
            return best_opportunities
            
        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {e}")
            return {}

    async def _monitor_arbitrage_opportunities(self):
        """Monitor for arbitrage opportunities"""
        while self.is_running:
            try:
                # Get price data from all exchanges
                price_data = await self._collect_price_data()
                
                # Find arbitrage opportunities
                opportunities = await self._find_arbitrage_opportunities(price_data)
                
                # Add profitable opportunities to queue
                for opportunity in opportunities:
                    if opportunity.net_profit > 0:
                        self.opportunities.append(opportunity)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring arbitrage opportunities: {e}")
                await asyncio.sleep(30)

    async def _collect_price_data(self) -> Dict:
        """Collect price data from all exchanges"""
        price_data = defaultdict(dict)
        
        tasks = []
        for exchange_name, exchange in self.exchanges.items():
            for symbol in self.monitored_symbols:
                task = asyncio.create_task(
                    self._get_exchange_price(exchange, symbol),
                    name=f"{exchange_name}_{symbol}"
                )
                tasks.append(task)
        
        # Wait for all price data
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Price fetch failed for task {tasks[i].get_name()}: {result}")
                continue
            
            if result:
                exchange_name = result['exchange']
                symbol = result['symbol']
                price_data[symbol][exchange_name] = result
        
        return price_data

    async def _get_exchange_price(self, exchange: ExchangeConnector, symbol: str) -> Optional[Dict]:
        """Get price from a specific exchange"""
        try:
            return await exchange.get_ticker(symbol)
        except Exception as e:
            logger.error(f"Error getting price from {exchange.name} for {symbol}: {e}")
            return None

    async def _find_arbitrage_opportunities(self, price_data: Dict) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities in price data"""
        opportunities = []
        
        try:
            for symbol, exchange_prices in price_data.items():
                if len(exchange_prices) < 2:
                    continue
                
                # Find all exchange pairs
                exchange_names = list(exchange_prices.keys())
                
                for i in range(len(exchange_names)):
                    for j in range(i + 1, len(exchange_names)):
                        buy_exchange = exchange_names[i]
                        sell_exchange = exchange_names[j]
                        
                        buy_data = exchange_prices[buy_exchange]
                        sell_data = exchange_prices[sell_exchange]
                        
                        # Check both directions
                        opp1 = await self._calculate_arbitrage(
                            symbol, buy_exchange, sell_exchange, buy_data, sell_data
                        )
                        if opp1:
                            opportunities.append(opp1)
                        
                        opp2 = await self._calculate_arbitrage(
                            symbol, sell_exchange, buy_exchange, sell_data, buy_data
                        )
                        if opp2:
                            opportunities.append(opp2)
            
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
        
        return opportunities

    async def _calculate_arbitrage(self, symbol: str, buy_exchange: str, sell_exchange: str,
                                 buy_data: Dict, sell_data: Dict) -> Optional[ArbitrageOpportunity]:
        """Calculate arbitrage opportunity between two exchanges"""
        try:
            buy_price = buy_data['price']
            sell_price = sell_data['price']
            
            # Check if profitable
            if sell_price <= buy_price:
                return None
            
            profit_percent = (sell_price - buy_price) / buy_price * 100
            
            # Check minimum profit threshold
            if profit_percent < self.min_profit_percent:
                return None
            
            # Calculate volume constraints
            buy_volume = buy_data['volume']
            sell_volume = sell_data['volume']
            max_volume = min(buy_volume, sell_volume) * 0.1  # Use 10% of available volume
            
            # Estimate costs
            gas_cost = await self._estimate_gas_cost(symbol, buy_exchange, sell_exchange)
            trading_fees = await self._estimate_trading_fees(symbol, buy_exchange, sell_exchange, max_volume)
            
            total_costs = gas_cost + trading_fees
            profit_usd = (sell_price - buy_price) * max_volume
            net_profit = profit_usd - total_costs
            
            # Check if still profitable after costs
            if net_profit <= 0:
                return None
            
            # Estimate execution time
            execution_time = await self._estimate_execution_time(buy_exchange, sell_exchange)
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(
                symbol, buy_exchange, sell_exchange, profit_percent, execution_time
            )
            
            return ArbitrageOpportunity(
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                symbol=symbol,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_percent=profit_percent,
                profit_usd=profit_usd,
                volume_available=max_volume,
                execution_time_estimate=execution_time,
                gas_cost_estimate=gas_cost,
                net_profit=net_profit,
                confidence_score=confidence_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculating arbitrage for {symbol}: {e}")
            return None

    async def _estimate_gas_cost(self, symbol: str, buy_exchange: str, sell_exchange: str) -> float:
        """Estimate gas costs for the arbitrage"""
        try:
            # Different cost structures for different exchange types
            if 'uniswap' in [buy_exchange, sell_exchange] or 'pancakeswap' in [buy_exchange, sell_exchange]:
                # DEX transactions are more expensive
                return 50.0  # $50 estimated gas cost for DEX
            else:
                # CEX to CEX arbitrage (lower cost)
                return 5.0   # $5 estimated withdrawal/transfer fees
                
        except Exception as e:
            logger.error(f"Error estimating gas cost: {e}")
            return 20.0  # Default estimate

    async def _estimate_trading_fees(self, symbol: str, buy_exchange: str, sell_exchange: str, volume: float) -> float:
        """Estimate trading fees"""
        try:
            # Exchange fee structures
            fee_rates = {
                'binance': 0.001,      # 0.1%
                'coinbase': 0.005,     # 0.5%
                'kraken': 0.0026,      # 0.26%
                'ftx': 0.0007,         # 0.07%
                'uniswap': 0.003,      # 0.3%
                'pancakeswap': 0.0025  # 0.25%
            }
            
            buy_fee_rate = fee_rates.get(buy_exchange, 0.002)
            sell_fee_rate = fee_rates.get(sell_exchange, 0.002)
            
            buy_fee = volume * buy_fee_rate
            sell_fee = volume * sell_fee_rate
            
            return buy_fee + sell_fee
            
        except Exception as e:
            logger.error(f"Error estimating trading fees: {e}")
            return volume * 0.002  # Default 0.2% total fees

    async def _estimate_execution_time(self, buy_exchange: str, sell_exchange: str) -> float:
        """Estimate execution time in seconds"""
        try:
            # Base execution times by exchange type
            execution_times = {
                'binance': 2.0,
                'coinbase': 5.0,
                'kraken': 10.0,
                'ftx': 3.0,
                'uniswap': 30.0,     # Blockchain confirmation time
                'pancakeswap': 15.0   # Faster blockchain
            }
            
            buy_time = execution_times.get(buy_exchange, 10.0)
            sell_time = execution_times.get(sell_exchange, 10.0)
            
            # If cross-chain, add bridge time
            if self._is_cross_chain(buy_exchange, sell_exchange):
                return buy_time + sell_time + 300.0  # Add 5 minutes for bridging
            else:
                return max(buy_time, sell_time)  # Parallel execution
                
        except Exception as e:
            logger.error(f"Error estimating execution time: {e}")
            return 60.0  # Default 1 minute

    def _is_cross_chain(self, exchange1: str, exchange2: str) -> bool:
        """Check if arbitrage involves cross-chain transfer"""
        ethereum_exchanges = ['uniswap', 'coinbase', 'kraken']
        bsc_exchanges = ['pancakeswap']
        
        eth1 = exchange1 in ethereum_exchanges
        eth2 = exchange2 in ethereum_exchanges
        bsc1 = exchange1 in bsc_exchanges
        bsc2 = exchange2 in bsc_exchanges
        
        return (eth1 and bsc2) or (bsc1 and eth2)

    async def _calculate_confidence_score(self, symbol: str, buy_exchange: str, sell_exchange: str,
                                        profit_percent: float, execution_time: float) -> float:
        """Calculate confidence score for the arbitrage opportunity"""
        try:
            score = 1.0
            
            # Higher profit = higher confidence
            if profit_percent > 2.0:
                score *= 1.2
            elif profit_percent > 1.0:
                score *= 1.1
            elif profit_percent < 0.5:
                score *= 0.8
            
            # Faster execution = higher confidence
            if execution_time < 30:
                score *= 1.1
            elif execution_time > 300:
                score *= 0.7
            
            # Exchange reliability factor
            reliable_exchanges = ['binance', 'coinbase', 'kraken']
            if buy_exchange in reliable_exchanges and sell_exchange in reliable_exchanges:
                score *= 1.1
            
            # Cross-chain reduces confidence
            if self._is_cross_chain(buy_exchange, sell_exchange):
                score *= 0.8
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.5

    async def _execute_arbitrages(self):
        """Execute profitable arbitrage opportunities"""
        while self.is_running:
            try:
                # Find best opportunities to execute
                best_opportunities = await self._select_best_opportunities()
                
                for opportunity in best_opportunities:
                    if opportunity.confidence_score > 0.7:  # High confidence threshold
                        success = await self._execute_arbitrage(opportunity)
                        if success:
                            self.executed_arbitrages.append(opportunity)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error executing arbitrages: {e}")
                await asyncio.sleep(30)

    async def _select_best_opportunities(self) -> List[ArbitrageOpportunity]:
        """Select best opportunities for execution"""
        try:
            # Get recent opportunities
            recent_opportunities = []
            cutoff_time = datetime.now() - timedelta(minutes=1)
            
            for opp in self.opportunities:
                if opp.timestamp > cutoff_time and opp.net_profit > 100:  # Min $100 profit
                    recent_opportunities.append(opp)
            
            # Sort by net profit
            recent_opportunities.sort(key=lambda x: x.net_profit, reverse=True)
            
            # Return top 3 opportunities
            return recent_opportunities[:3]
            
        except Exception as e:
            logger.error(f"Error selecting opportunities: {e}")
            return []

    async def _execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> bool:
        """Execute a specific arbitrage opportunity"""
        try:
            logger.info(f"🚀 Executing arbitrage: {opportunity.symbol} "
                       f"{opportunity.buy_exchange} -> {opportunity.sell_exchange} "
                       f"Profit: ${opportunity.net_profit:.2f}")
            
            # This would execute actual trades
            # For now, simulate execution
            import random
            
            # Simulate execution time
            await asyncio.sleep(opportunity.execution_time_estimate / 10)  # Scaled for simulation
            
            # Simulate success rate based on confidence
            success_probability = opportunity.confidence_score * 0.9  # 90% max success rate
            success = random.random() < success_probability
            
            if success:
                self.total_profit += opportunity.net_profit
                logger.info(f"✅ Arbitrage executed successfully. Profit: ${opportunity.net_profit:.2f}")
            else:
                logger.warning(f"❌ Arbitrage execution failed for {opportunity.symbol}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
            return False

    async def _update_performance_metrics(self):
        """Update performance metrics"""
        while self.is_running:
            try:
                if len(self.executed_arbitrages) > 0:
                    successful_arbitrages = len(self.executed_arbitrages)
                    total_attempts = successful_arbitrages  # Simplified for simulation
                    
                    self.success_rate = successful_arbitrages / total_attempts if total_attempts > 0 else 0
                    
                    # Calculate average execution time
                    avg_time = sum(arb.execution_time_estimate for arb in self.executed_arbitrages) / len(self.executed_arbitrages)
                    self.average_execution_time = avg_time
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
                await asyncio.sleep(300)

    def get_performance_metrics(self) -> Dict:
        """Get arbitrage engine performance metrics"""
        try:
            recent_opportunities = len([
                opp for opp in self.opportunities
                if opp.timestamp > datetime.now() - timedelta(hours=1)
            ])
            
            recent_executions = len([
                arb for arb in self.executed_arbitrages
                if arb.timestamp > datetime.now() - timedelta(hours=24)
            ])
            
            return {
                'total_profit_usd': self.total_profit,
                'success_rate': self.success_rate,
                'opportunities_last_hour': recent_opportunities,
                'executions_last_24h': recent_executions,
                'average_execution_time': self.average_execution_time,
                'monitored_exchanges': len(self.exchanges),
                'monitored_symbols': len(self.monitored_symbols)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {} 
# backtesting/backtest_engine.py
"""
Comprehensive Backtesting Framework
Simulates trading strategies on historical data with realistic constraints
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging
from collections import defaultdict

import asyncio
from concurrent.futures import ProcessPoolExecutor

# Initialize the process pool executor for parallel backtesting
executor = ProcessPoolExecutor()

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: datetime
    end_date: datetime

    # Realistic constraints

    # Position limits

    # Order constraints

    # Market hours

    # Data settings

@dataclass
class BacktestOrder:
    """Order representation in backtest"""
    order_id: str
    timestamp: datetime
    symbol: str
    option_type: str  # CE/PE
    strike: float
    side: str  # BUY/SELL
    quantity: int
    order_type: str  # MARKET/LIMIT
    limit_price: Optional[float]

@dataclass
class BacktestPosition:
    """Position tracking in backtest"""
    position_id: str
    symbol: str
    option_type: str
    strike: float
    entry_time: datetime
    entry_price: float
    quantity: int
    current_price: float

@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    # Overall metrics
    total_return: float
    total_return_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # days

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float

    # Time metrics
    average_holding_time: timedelta
    trades_per_day: float

    # Strategy breakdown
    strategy_performance: Dict[str, Dict]

    # Daily metrics
    daily_returns: pd.Series
    equity_curve: pd.Series
    drawdown_series: pd.Series

    # Trade log
    trades: List[BacktestPosition]

    # System metrics
    max_concurrent_positions: int
    order_fill_rate: float
    slippage_cost_total: float
    commission_cost_total: float

class BacktestEngine:
    """
    Main backtesting engine
    Simulates realistic market conditions and constraints
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self._market_data_lock = asyncio.Lock()
        self.historical_data = {}
        self.current_time = None
        self.orders_this_second = 0
        self.last_order_second = None
        self.positions = {}
        self.order_history = []
        self.trade_history = []
        self.performance_metrics = {}

    async def load_historical_data(self):
        """Load historical data for all symbols"""
        async with self._market_data_lock:
            try:
                for symbol in self.config.symbols:
                    data = await self._load_symbol_data(symbol)
                    if data is not None:
                        self.historical_data[symbol] = data
                        logger.info(f"Loaded historical data for {symbol}")
            except Exception as e:
                logger.error(f"Error loading historical data: {e}")

    async def _get_market_snapshot(self, timestamp: datetime) -> Dict:
        """Get market data snapshot for a specific timestamp"""
        async with self._market_data_lock:
            snapshot = {}
            for symbol in self.config.symbols:
                if symbol in self.historical_data:
                    data = self.historical_data[symbol]
                    # Get the closest timestamp data
                    closest_idx = data.index.get_indexer([timestamp], method='nearest')[0]
                    snapshot[symbol] = {
                        'timestamp': timestamp,
                        'open': data.iloc[closest_idx]['open'],
                        'high': data.iloc[closest_idx]['high'],
                        'low': data.iloc[closest_idx]['low'],
                        'close': data.iloc[closest_idx]['close'],
                        'volume': data.iloc[closest_idx]['volume']
                    }
            return snapshot

    async def _generate_signals(self, strategy_portfolio, market_data: Dict) -> List[Signal]:
        """Generate trading signals from strategies"""
        all_signals = []

        # Evaluate each strategy
        for name, strategy in strategy_portfolio.strategies.items():
            try:
                signals = await strategy.generate_signals(market_data)
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Error in strategy {name}: {e}")
                continue

        # Apply confluence detection
        enhanced_signals = await strategy_portfolio.strategies['confluence_amplifier'].analyze_signals(all_signals)
        
        # Filter by quality
        qualified_signals = [s for s in enhanced_signals if s.quality_score >= 8.0]
        
        # Sort by quality and return top 5 signals
        return sorted(qualified_signals, key=lambda x: x.quality_score, reverse=True)[:5]

    def _calculate_position_size(self, signal: Signal) -> int:
        """Calculate position size based on signal and risk management"""
        # Base position size (lots)
        if signal.symbol.startswith('NIFTY'):
            lot_size = 60  # New lot size
            base_lots = 2
        else:  # BANKNIFTY
            lot_size = 40  # New lot size
            base_lots = 1

        # Adjust based on signal quality
        quality_multiplier = signal.quality_score / 10

        # Adjust based on strategy allocation
        allocation = signal.strategy.allocation if hasattr(signal, 'strategy') else 0.2

        # Calculate final size
        position_lots = int(base_lots * quality_multiplier * allocation)
        position_lots = max(1, position_lots)  # Minimum 1 lot

        return position_lots * lot_size

    def _can_place_order(self) -> bool:
        """Check if order can be placed (rate limiting)"""
        current_second = self.current_time.replace(microsecond=0)
        if current_second != self.last_order_second:
            self.orders_this_second = 0
            self.last_order_second = current_second
        return self.orders_this_second < self.config.max_orders_per_second

    def _update_order_tracking(self, order: Order):
        """Update order tracking for rate limiting"""
        current_second = self.current_time.replace(microsecond=0)
        if current_second != self.last_order_second:
            self.orders_this_second = 0
            self.last_order_second = current_second
        self.orders_this_second += 1

    async def run_backtest(self, strategy_portfolio) -> BacktestResults:
        """Run backtest with strategy portfolio"""
        logger.info("Starting backtest simulation...")
        # Initialize strategies
        for strategy in strategy_portfolio.strategies.values():
            strategy.reset()

        # Iterate through time periods
        current_date = self.config.start_date
        while current_date <= self.config.end_date:
            # Process trading day
            await self._process_day(current_date)
            # End of day processing
            self._calculate_daily_metrics(current_date)
            # Move to next day
            current_date += timedelta(days=1)

        # Generate results
        results = self._generate_results()
        logger.info("Backtest completed")
        return results

    async def _process_day(self, current_date: datetime):
        """Process a single trading day"""
        # Get market data for the day
        market_data = await self._get_market_snapshot(current_date)
        
        # Update strategies with market data
        for strategy in self.strategies.values():
            await strategy.update_market_data(market_data)
        
        # Generate and process signals
        signals = await self._generate_signals(self.strategies, market_data)
        await self._process_signals(signals)
        
        # Update positions and orders
        await self._update_positions(current_date)
        await self._update_orders(current_date)
        
        # Calculate end of day metrics
        self._calculate_daily_metrics(current_date)

    async def _process_signals(self, signals: List[Signal]):
        """Process signals with realistic constraints"""
        for signal in signals:
            # Check order rate limit
            if not self._can_place_order():
                logger.warning("Order rate limit reached")
                continue

            # Check position limits
            if len(self.positions) >= self.config.max_positions:
                logger.warning("Max positions reached")
                continue

            # Check capital allocation
            position_size = self._calculate_position_size(signal)
            if position_size > self.current_capital * self.config.max_position_size:
                logger.warning("Insufficient capital for position")
                continue

            # Create and queue order
            order = self._create_order(signal, position_size)
            self.pending_orders.append(order)
            self.order_history.append(order)
            
            # Update order tracking
            self._update_order_tracking(order)

    def _process_pending_orders(self, market_data: Dict):
        """Process pending orders with realistic fills"""
        filled_orders = []

        for order in self.pending_orders:
            # Get current price
            option_key = f"{order.symbol}_{order.option_type}_{order.strike}"
            current_price = self._get_option_price(option_key, market_data)
            if current_price is None:
                continue

            # Check if order can be filled
            if order.order_type == "MARKET":
                # Market orders fill immediately with slippage
                fill_price = current_price * (1 + self.config.slippage_percent / 100)
            else:  # LIMIT order
                if current_price <= order.limit_price:
                    fill_price = order.limit_price
                else:
                    continue  # Order not filled

            # Execute order
            order.status = "FILLED"
            order.fill_time = self.current_time
            order.executed_price = fill_price

            # Create position
            position = self._create_position(order)
            self.positions[position.position_id] = position

            # Update capital
            total_cost = (fill_price * order.quantity) + order.commission
            self.current_capital -= total_cost

            filled_orders.append(order)

        # Remove filled orders from pending
        for order in filled_orders:
            self.pending_orders.remove(order)

    def _check_exits(self, current_time: datetime):
        """Check exit conditions for open positions"""
        positions_to_close = []

        for position_id, position in self.positions.items():
            # Get current price
            option_key = f"{position.symbol}_{position.option_type}_{position.strike}"
            current_price = self._get_option_price(option_key, await self._get_market_snapshot(current_time))
            if current_price is None:
                continue

            # Update position metrics
            position.current_price = current_price
            position.pnl = (current_price - position.entry_price) * position.quantity
            position.pnl_percent = (position.pnl / (position.entry_price * position.quantity)) * 100

            # Check exit conditions
            should_exit = False

            # Stop loss (0.6%)
            if position.pnl_percent <= -0.6:
                should_exit = True

            # Profit target (1%)
            if position.pnl_percent >= 1.0:
                should_exit = True

            # Time stop (15 minutes)
            if (current_time - position.entry_time).total_seconds() >= 900:  # 15 minutes
                should_exit = True

            if should_exit:
                positions_to_close.append(position_id)

        # Close positions
        for position_id in positions_to_close:
            self._close_position(position_id)

    def _close_position(self, position_id: str):
        """Close a position"""
        position = self.positions[position_id]
        
        # Set exit details
        position.exit_time = self.current_time
        position.exit_price = position.current_price
        
        # Calculate final P&L with costs
        gross_pnl = (position.exit_price - position.entry_price) * position.quantity
        stt_cost = position.exit_price * position.quantity * self.config.stt_rate
        total_costs = self.config.commission_per_order * 2 + stt_cost  # Entry + exit commission
        
        # Update capital
        self.current_capital += gross_pnl - total_costs
        
        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[position_id]
        
        # Update strategy metrics
        if position.pnl > 0:
            self.strategy_metrics[position.strategy]['wins'] += 1
        else:
            self.strategy_metrics[position.strategy]['losses'] += 1
        
        logger.info(f"Position closed: {position.symbol} P&L: {position.pnl:.2f} ({position.pnl_percent:.2f}%)")

    async def _staggered_exit_sequence(self, current_time: datetime):
        """Implement staggered exit for EOD"""
        # Sort positions by P&L
        sorted_positions = sorted(self.positions.items(), key=lambda x: x[1].pnl_percent)
        
        # Exit based on time windows
        exit_schedule = {
            "15:15": lambda p: p[1].pnl_percent < -0.1,  # Losing positions
            "15:20": lambda p: p[1].pnl_percent > 0.1,   # Profitable positions
            "15:23": lambda p: True                       # All remaining positions
        }
        
        current_time_str = current_time.strftime("%H:%M")
        for exit_time, condition in exit_schedule.items():
            if current_time_str >= exit_time:
                positions_to_close = [pid for pid, pos in sorted_positions if condition(pos) and pid in self.positions]
                for position_id in positions_to_close:
                    if self._can_place_order():
                        self._close_position(position_id)
                        await asyncio.sleep(0.15)  # 150ms between orders

    def _calculate_daily_metrics(self, date: datetime):
        """Calculate end of day metrics"""
        # Calculate daily P&L
        daily_pnl = sum(p.pnl for p in self.closed_positions if p.exit_time.date() == date.date())
        
        # Update equity curve
        self.equity_curve.append({
            'date': date.date(),
            'capital': self.current_capital,
            'pnl': daily_pnl,
            'positions': len(self.positions)
        })

    def _generate_results(self) -> BacktestResults:
        """Generate comprehensive backtest results"""
        # Convert to DataFrames for analysis
        trades_df = pd.DataFrame([vars(p) for p in self.closed_positions])
        equity_df = pd.DataFrame(self.equity_curve)
        
        if trades_df.empty:
            logger.warning("No trades executed during backtest")
            return self._empty_results()
        
        # Calculate returns
        equity_df['returns'] = equity_df['capital'].pct_change()
        
        # Calculate metrics
        total_return = self.current_capital - self.starting_capital
        total_return_percent = (total_return / self.starting_capital) * 100
        
        # Risk metrics
        sharpe_ratio = self._calculate_sharpe_ratio(equity_df['returns'])
        sortino_ratio = self._calculate_sortino_ratio(equity_df['returns'])
        
        # Trade statistics
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0
        profit_factor = (winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())) if len(losing_trades) > 0 else float('inf')
        
        # Strategy breakdown
        strategy_performance = {}
        for strategy, metrics in self.strategy_metrics.items():
            strategy_performance[strategy] = {
                'trades': metrics['trades'],
                'pnl': metrics['pnl'],
                'win_rate': metrics['wins'] / metrics['trades'] if metrics['trades'] > 0 else 0,
                'wins': metrics['wins'],
                'losses': metrics['losses']
            }
        
        # Cost analysis
        total_commission = len(self.order_history) * self.config.commission_per_order
        total_slippage = sum(o.slippage for o in self.order_history if o.slippage)
        
        # Calculate max drawdown
        max_dd, max_dd_duration = self._calculate_max_drawdown(equity_df['capital'])
        
        return BacktestResults(
            total_return=total_return,
            total_return_percent=total_return_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            total_trades=len(trades_df),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
            average_loss=losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
            largest_win=winning_trades['pnl'].max() if len(winning_trades) > 0 else 0,
            largest_loss=losing_trades['pnl'].min() if len(losing_trades) > 0 else 0,
            average_holding_time=pd.Timedelta(trades_df['holding_time'].mean()),
            trades_per_day=len(trades_df) / len(self.daily_pnl),
            strategy_performance=strategy_performance,
            daily_returns=equity_df['returns'],
            equity_curve=equity_df['capital'],
            drawdown_series=self._calculate_drawdown_series(equity_df['capital']),
            trades=self.closed_positions,
            max_concurrent_positions=max(len(ec['positions']) for ec in self.equity_curve),
            order_fill_rate=len([o for o in self.order_history if o.status == 'FILLED']) / len(self.order_history),
            slippage_cost_total=total_slippage,
            commission_cost_total=total_commission
        )

    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate annualized Sharpe ratio"""
        if len(returns) < 2:
            return 0.0

        # Assume 252 trading days
        annualized_return = returns.mean() * 252
        annualized_volatility = returns.std() * np.sqrt(252)
        return annualized_return / annualized_volatility if annualized_volatility != 0 else 0.0

    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(returns) < 2:
            return 0.0

        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')

        # Assume 252 trading days
        annualized_return = returns.mean() * 252
        downside_std = downside_returns.std() * np.sqrt(252)
        return annualized_return / downside_std if downside_std != 0 else 0.0

    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> Tuple[float, int]:
        """Calculate maximum drawdown and duration"""
        peak = equity_curve.expanding(min_periods=1).max()
        drawdown = (equity_curve - peak) / peak

        max_dd = drawdown.min()
        # Calculate duration
        drawdown_start = None
        max_duration = 0
        current_duration = 0

        for i, dd in enumerate(drawdown):
            if dd < 0:
                if drawdown_start is None:
                    drawdown_start = i
                current_duration = i - drawdown_start
            else:
                if drawdown_start is not None:
                    max_duration = max(max_duration, current_duration)
                    drawdown_start = None
                    current_duration = 0

        return abs(max_dd), max_duration

    def _calculate_drawdown_series(self, equity_curve: pd.Series) -> pd.Series:
        """Calculate drawdown series"""
        peak = equity_curve.expanding(min_periods=1).max()
        return (equity_curve - peak) / peak

    def _empty_results(self) -> BacktestResults:
        """Return empty results when no trades executed"""
        return BacktestResults(
            total_return=0,
            total_return_percent=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_drawdown=0,
            max_drawdown_duration=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            profit_factor=0,
            average_win=0,
            average_loss=0,
            largest_win=0,
            largest_loss=0,
            average_holding_time=timedelta(0),
            trades_per_day=0,
            strategy_performance={},
            daily_returns=pd.Series(),
            equity_curve=pd.Series(),
            drawdown_series=pd.Series(),
            trades=[],
            max_concurrent_positions=0,
            order_fill_rate=0,
            slippage_cost_total=0,
            commission_cost_total=0
        )

    async def _load_symbol_data(self, symbol: str) -> pd.DataFrame:
        """Load historical data for symbol"""
        # Implement based on your data source
        # This is a placeholder
        return pd.DataFrame()

    async def _load_options_data(self, symbol: str) -> Dict:
        """Load historical options chain data"""
        # Implement based on your data source
        return {}

    def _get_options_snapshot(self, symbol: str, timestamp: datetime) -> Dict:
        """Get options chain snapshot at timestamp"""
        # Implement based on your options data structure
        return {}

    def _get_option_price(self, option_key: str, market_data: Dict) -> Optional[float]:
        """Get option price from market data"""
        # Implement based on your data structure
        return None

    def _create_order(self, signal, position_size: int) -> BacktestOrder:
        """Create order from signal"""
        return BacktestOrder(
            order_id=f"BT_{datetime.now().timestamp()}",
            timestamp=self.current_time,
            symbol=signal.symbol,
            option_type=signal.option_type,
            strike=signal.strike,
            side="BUY",  # Always buying options
            quantity=position_size,
            order_type="LIMIT" if hasattr(signal, 'limit_price') else "MARKET",
            limit_price=getattr(signal, 'limit_price', None),
            strategy=signal.strategy_name,
            signal_quality=signal.quality_score
        )

    def _create_position(self, order: BacktestOrder) -> BacktestPosition:
        """Create position from filled order"""
        return BacktestPosition(
            position_id=f"POS_{order.order_id}",
            symbol=order.symbol,
            option_type=order.option_type,
            strike=order.strike,
            entry_time=order.fill_time,
            entry_price=order.executed_price,
            quantity=order.quantity,
            current_price=order.executed_price,
            strategy=order.strategy
        )

class BacktestRunner:
    """Run multiple backtests in parallel"""

    async def run_parameter_sweep(self, base_config: BacktestConfig,
                                parameter_grid: Dict,
                                strategy_portfolio) -> Dict:
        """Run parameter sweep across multiple configurations"""
        configs = self._generate_configs(base_config, parameter_grid)
        futures = []

        for config_name, config in configs.items():
            future = executor.submit(
                self._run_single_backtest,
                config,
                strategy_portfolio
            )
            futures.append((config_name, future))
        results = {}

        for config_name, future in futures:
            try:
                result = future.result(timeout=3600)  # 1 hour timeout
                results[config_name] = result
            except Exception as e:
                logger.error(f"Backtest failed for {config_name}: {e}")

        return results

    def _generate_configs(self, base_config: BacktestConfig, parameter_grid: Dict) -> Dict[str, BacktestConfig]:
        """Generate configuration variations"""
        # Implement parameter grid expansion
        return {"base": base_config}

    def _run_single_backtest(self, config: BacktestConfig, strategy_portfolio) -> BacktestResults:
        """Run single backtest (for multiprocessing)"""
        # Create new event loop for process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        engine = BacktestEngine(config)
        # Run backtest
        loop.run_until_complete(engine.load_historical_data())
        results = loop.run_until_complete(engine.run_backtest(strategy_portfolio))
        loop.close()
        return results

    def _update_positions(self, market_data: Dict):
        """Update open positions with current market data"""
        for position_id, position in self.positions.items():
            if position.symbol in market_data:
                current_price = market_data[position.symbol]['close']
                position.current_price = current_price
                position.pnl = (current_price - position.entry_price) * position.quantity
                position.pnl_percent = (position.pnl / (position.entry_price * position.quantity)) * 100

    def _update_metrics(self, current_date: datetime):
        """Update daily metrics"""
        daily_pnl = sum(p.pnl for p in self.positions.values())
        self.daily_pnl[current_date] = daily_pnl
        self.current_capital += daily_pnl

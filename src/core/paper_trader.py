# paper_trading/paper_trader.py
"""
Paper Trading Framework
Simulates live trading with real market data but virtual money
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json
import uuid

import redis
import pandas as pd

from ..brokers.zerodha import ZerodhaIntegration
from ..data.truedata_provider import TrueDataProvider
from ..core.orchestrator import TradingOrchestrator

logger = logging.getLogger(__name__
@ dataclass
class PaperOrder:
    """Virtual order for paper trading"""
    order_id: str
    timestamp: datetime
    symbol: str
    option_type: str
    strike: float
    side: str
    quantity: int
    order_type: str
    limit_price: Optional[float]
    trigger_price: Optional[float]

    # Execution details

    # Metadata

    @ dataclass
    class PaperPosition:
        """Virtual position for paper trading"""
        position_id: str
        symbol: str
        option_type: str
        strike: float
        quantity: int
        entry_price: float
        entry_time: datetime

        # Current state

        # Exit details

        # Risk management

        # Metadata

        @ dataclass
        class PaperAccount:
            """Virtual trading account"""
            account_id: str
            initial_capital: float
            current_capital: float

            # Positions

            # Orders

            # Performance

            # Risk metrics

            # Daily metrics

            class PaperTradingEngine:
                """
                Paper trading engine that simulates real trading
                Uses live market data but executes virtual trades
                """

                def __init__(self, config: Dict):

                    # Initialize components

                    # Paper trading account
                    account_id=str(uuid.uuid4()),
                    initial_capital=config['paper_trading']['initial_capital'],
                    current_capital=config['paper_trading']['initial_capital']

                    # Order execution simulation

                    # Market simulation

                    # Performance tracking

                    async def initialize(self):
                    """Initialize paper trading engine"""
                    logger.info("Initializing paper trading engine..."
                    # Connect to data provider
                    await self.data_provider.connect(
                    # Load account state if exists
                    await self._load_account_state(
                    logger.info(f"Paper trading initialized with capital: ₹{self.account.current_capital:,.2f}"
                    async def place_order(self, order_params: Dict) -> Dict:
                    """Place a virtual order"""
                    # Create paper order
                    order=PaperOrder(
                    order_id=f"PAPER_{uuid.uuid4().hex[:8}}",
                    timestamp=datetime.now(],
                    symbol=order_params['symbol'],
                    option_type=order_params.get('option_type', 'EQ'),
                    strike=order_params.get('strike', 0),
                    side=order_params['side'],
                    quantity=order_params['quantity'],
                    order_type=order_params.get('order_type', 'MARKET'),
                    limit_price=order_params.get('price'),
                    trigger_price=order_params.get('trigger_price'),
                    strategy=order_params.get('strategy', ''),
                    signal_quality=order_params.get('signal_quality', 0),
                    tag=order_params.get('tag', ''

                    # Validate order
                    validation_result=self._validate_order(order
                    if not validation_result['valid']:
                        self.account.order_history.append(order
                    return {
                    'status': 'REJECTED',
                    'order_id': order.order_id,
                    'reason': validation_result['reason'
                    # Add to pending orders
                    self.account.order_history.append(order
                    # Log order placement
                    logger.info(f"Paper order placed: {order.order_id} - {order.symbol} "
                    f"{order.side} {order.quantity} @ {order.order_type}"
                    # Schedule execution
                    asyncio.create_task(self._execute_order(order
                return {
                'status': 'PENDING',
                'order_id': order.order_id,
                'timestamp': order.timestamp.isoformat(

                async def cancel_order(self, order_id: str} -> Dict:
                """Cancel a pending order"""
                if order_id in self.account.pending_orders:
                    order=self.account.pending_orders[order_id
                    del self.account.pending_orders[order_id]

                    logger.info(f"Paper order cancelled: {order_id}"
                return {'status': 'SUCCESS', 'order_id': order_id
            return {'status': 'ERROR', 'message': 'Order not found'
            """Exit a virtual position"""
            if position_id not in self.account.open_positions:
            return {'status': 'ERROR', 'message': 'Position not found'
            position= self.account.open_positions[position_id
            # Create exit order
            exit_order_params= {
            'symbol': position.symbol,
            'option_type': position.option_type,
            'strike': position.strike,
            'side': 'SELL',
            'quantity': position.quantity,
            'order_type': 'MARKET',
            'strategy': position.strategy,
            'tag': f"EXIT_{reason}"

            result= await self.place_order(exit_order_params
        return result

        async def _execute_order(self, order: PaperOrder]:
        """Simulate order execution"""
        # Simulate execution delay
        await asyncio.sleep(self.execution_delay
        # Get current market price
        market_data=await self._get_market_price(order.symbol, order.option_type, order.strike
        if market_data is None:
            del self.account.pending_orders[order.order_id]
        return

        current_price=market_data['ltp']

        # Check if order can be filled
        can_fill=False
        execution_price=current_price

        # Market orders always fill
        can_fill=True
        # Apply slippage
        execution_price=current_price * (1 + self.slippage_percent / 100
        else:
            execution_price=current_price * (1 - self.slippage_percent / 100
            # Check limit price
            can_fill=True
            execution_price=min(order.limit_price, current_price
            can_fill=True
            execution_price=max(order.limit_price, current_price
            # Simulate fill probability
            if can_fill and self.fill_probability < 1.0:
                import random
                can_fill=random.random() < self.fill_probability

                if not can_fill:
                    # Order remains pending
                return

                # Execute order

                # Update account
                # Create new position
                position=PaperPosition(
                position_id=f"POS_{order.order_id}",
                symbol=order.symbol,
                option_type=order.option_type,
                strike=order.strike,
                quantity=order.quantity,
                entry_price=execution_price,
                entry_time=order.execution_time,
                current_price=execution_price,
                strategy=order.strategy,
                order_ids=[order.order_id]

                # Deduct capital
                position_cost=execution_price * order.quantity
                commission=self._calculate_commission(order
                total_cost=position_cost + commission

                if total_cost > self.account.current_capital:
                    else:

                        logger.info(f"Paper position opened: {position.position_id} - "
                        f"{position.symbol} {position.quantity} @ {execution_price:.2f}"
                        else:
                            # Close position
                            # Find matching position
                            matching_position=None
                            for pos_id, pos in self.account.open_positions.items():
                                matching_position=pos
                            break

                            if matching_position:
                                # Calculate P&L
                                exit_value=execution_price * order.quantity
                                entry_value=matching_position.entry_price * order.quantity
                                gross_pnl=exit_value - entry_value

                                # Deduct costs
                                commission=self._calculate_commission(order
                                stt=self._calculate_stt(exit_value
                                net_pnl=gross_pnl - commission - stt

                                # Update position

                                # Update account

                                # Update daily metrics
                                if net_pnl > 0:
                                    else:

                                        # Move to closed positions
                                        self.account.closed_positions.append(matching_position
                                        del self.account.open_positions[matching_position.position_id]

                                        logger.info(f"Paper position closed: {matching_position.position_id} - "
                                        f"P&L: ₹{
                                        net_pnl:.2f} ({
                                        matching_position.pnl_percent:.2f}%)"
                                        # Remove from pending orders
                                        if order.order_id in self.account.pending_orders:
                                            del self.account.pending_orders[order.order_id]

                                            # Log execution
                                            self.execution_log.append({
                                            'timestamp': order.execution_time,
                                            'order_id': order.order_id,
                                            'symbol': order.symbol,
                                            'side': order.side,
                                            'quantity': order.quantity,
                                            'executed_price': execution_price,
                                            'slippage': execution_price - current_price

                                            # Update metrics
                                            await self._update_metrics(
                                            def _validate_order(self, order: PaperOrder) -> Dict:
                                                """Validate order before execution"""
                                                # Check capital
                                                estimated_cost=self._estimate_order_cost(order
                                                if estimated_cost > self.account.current_capital:
                                                return {'valid': False, 'reason': 'Insufficient capital'
                                                # Check position limits
                                            return {'valid': False, 'reason': 'Max positions reached'
                                            # Check daily loss limit
                                            daily_loss_limit= self.config['risk'}['max_daily_loss'] * self.account.initial_capital
                                            if self.account.daily_pnl < -daily_loss_limit:
                                            return {'valid': False, 'reason': 'Daily loss limit reached'
                                        return {'valid': True
                                        def _estimate_order_cost(self, order: PaperOrder) -> float:
                                            """Estimate total cost of order"""
                                            # Get approximate price
                                            if order.limit_price:
                                                price= order.limit_price
                                                else:
                                                    # Use last known price or estimate
                                                    price= 100  # Default estimate

                                                    position_cost= price * order.quantity
                                                    commission= self._calculate_commission(order
                                                return position_cost + commission

                                                def _calculate_commission(self, order: PaperOrder) -> float:
                                                    """Calculate brokerage commission"""
                                                return self.config['costs'}['commission_per_order']

                                                def _calculate_stt(self, value: float) -> float:
                                                    """Calculate Securities Transaction Tax"""
                                                return value * self.config['costs']['stt_rate']

                                                async def _get_market_price(
                                                self, symbol: str, option_type: str, strike: float) -> Optional[Dict]:
                                                """Get current market price for instrument"""
                                                try:
                                                    # Get from data provider
                                                    if option_type in ['CE', 'PE']:
                                                        instrument=f"{symbol}_{strike}_{option_type}"
                                                        else:
                                                            instrument=symbol

                                                            market_data=await self.data_provider.get_quote(instrument
                                                        return market_data

                                                        except Exception as e:
                                                            logger.error(f"Failed to get market price: {e}"
                                                        return None

                                                        async def update_positions(self):
                                                        """Update all open positions with current prices"""
                                                        for position in self.account.open_positions.values():
                                                            market_data=await self._get_market_price(
                                                            position.symbol,
                                                            position.option_type,
                                                            position.strike

                                                            if market_data:

                                                                # Calculate unrealized P&L
                                                                current_value=position.current_price * position.quantity
                                                                entry_value=position.entry_price * position.quantity

                                                                # Update account unrealized P&L
                                                                pos.pnl for pos in self.account.open_positions.values(

                                                                async def _update_metrics(self):
                                                                """Update performance metrics"""
                                                                # Update peak and drawdown
                                                                current_value=self.account.current_capital + self.account.unrealized_pnl

                                                                if current_value > self.account.peak_capital:
                                                                    else:
                                                                        drawdown=(self.account.peak_capital - current_value) /
                                                                        self.account.peak_capital

                                                                        # Store metrics in Redis
                                                                        metrics={
                                                                        'timestamp': datetime.now().isoformat(),
                                                                        'capital': self.account.current_capital,
                                                                        'total_pnl': self.account.total_pnl,
                                                                        'realized_pnl': self.account.realized_pnl,
                                                                        'unrealized_pnl': self.account.unrealized_pnl,
                                                                        'positions': len(self.account.open_positions),
                                                                        'daily_pnl': self.account.daily_pnl,
                                                                        'daily_trades': self.account.daily_trades,
                                                                        'max_drawdown': self.account.max_drawdown,
                                                                        'current_drawdown': self.account.current_drawdown

                                                                        await self.redis.set(
                                                                        'paper_trading:metrics:latest',
                                                                        json.dumps(metrics),

                                                                        # Log performance
                                                                        self.performance_log.append(metrics
                                                                        async def reset_daily_metrics(self):
                                                                        """Reset daily metrics at EOD"""

                                                                        logger.info("Daily metrics reset"
                                                                        async def generate_report(self) -> Dict:
                                                                        """Generate performance report"""
                                                                        if not self.account.closed_positions:
                                                                        return {'message': 'No trades executed yet'
                                                                        # Convert to DataFrame for analysis
                                                                        trades_data= [
                                                                        for pos in self.account.closed_positions:
                                                                            trades_data.append({
                                                                            'symbol': pos.symbol,
                                                                            'entry_time': pos.entry_time,
                                                                            'exit_time': pos.exit_time,
                                                                            'entry_price': pos.entry_price,
                                                                            'exit_price': pos.exit_price,
                                                                            'quantity': pos.quantity,
                                                                            'pnl': pos.pnl,
                                                                            'pnl_percent': pos.pnl_percent,
                                                                            'strategy': pos.strategy,
                                                                            'holding_time': (pos.exit_time - pos.entry_time}.total_seconds(] / 60

                                                                            df= pd.DataFrame(trades_data
                                                                            # Calculate metrics
                                                                            winning_trades=df[df['pnl'] > 0]
                                                                            losing_trades=df[df['pnl'] < 0]

                                                                            report={
                                                                            'account_summary': {
                                                                            'initial_capital': self.account.initial_capital,
                                                                            'current_capital': self.account.current_capital,
                                                                            'total_pnl': self.account.total_pnl,
                                                                            'total_return_percent': (self.account.total_pnl / self.account.initial_capital) * 100,
                                                                            'max_drawdown': self.account.max_drawdown * 100},
                                                                            'trade_statistics': {
                                                                            'total_trades': len(df),
                                                                            'winning_trades': len(winning_trades),
                                                                            'losing_trades': len(losing_trades),
                                                                            'win_rate': len(winning_trades) / len(df) * 100 if len(df) > 0 else 0,
                                                                            'average_win': winning_trades['pnl'}.mean(] if len(winning_trades) > 0 else 0,
                                                                            'average_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
                                                                            'largest_win': winning_trades['pnl'].max() if len(winning_trades) > 0 else 0,
                                                                            'largest_loss': losing_trades['pnl'].min() if len(losing_trades) > 0 else 0,
                                                                            'profit_factor': abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum(
                                                                            'average_holding_time': df['holding_time'].mean(},
                                                                            'strategy_breakdown': self._calculate_strategy_metrics(df),
                                                                            'recent_trades': trades_data[-10:]  # Last 10 trades

                                                                        return report

                                                                        def _calculate_strategy_metrics(self, df: pd.DataFrame) -> Dict:
                                                                            """Calculate metrics by strategy"""
                                                                            strategy_metrics={
                                                                            for strategy in df['strategy'}.unique(]:
                                                                                strategy_df= df[df['strategy'] == strategy]
                                                                                winning= strategy_df[strategy_df['pnl'] > 0]

                                                                                'trades': len(strategy_df),
                                                                                'total_pnl': strategy_df['pnl'].sum(),
                                                                                'win_rate': len(winning) / len(strategy_df) * 100 if len(strategy_df) > 0 else 0,
                                                                                'average_pnl': strategy_df['pnl'].mean(),
                                                                                'best_trade': strategy_df['pnl'].max(),
                                                                                'worst_trade': strategy_df['pnl'].min(

                                                                            return strategy_metrics

                                                                            async def _save_account_state(self):
                                                                            """Save account state for persistence"""
                                                                            state={
                                                                            'account_id': self.account.account_id,
                                                                            'current_capital': self.account.current_capital,
                                                                            'total_pnl': self.account.total_pnl,
                                                                            'realized_pnl': self.account.realized_pnl,
                                                                            'max_drawdown': self.account.max_drawdown,
                                                                            'closed_positions': len(self.account.closed_positions),
                                                                            'timestamp': datetime.now().isoformat(

                                                                            await self.redis.set(
                                                                            f'paper_trading:account:{self.account.account_id}',
                                                                            json.dumps(state

                                                                            async def _load_account_state(self):
                                                                            """Load saved account state"""
                                                                            # Implement if needed for persistence across restarts
                                                                        pass

                                                                        async def shutdown(self):
                                                                        """Shutdown paper trading engine"""
                                                                        logger.info("Shutting down paper trading engine..."
                                                                        # Close all positions
                                                                        position_ids=list(self.account.open_positions.keys(
                                                                        for position_id in position_ids:
                                                                            await self.exit_position(position_id, "Shutdown"
                                                                            # Save final state
                                                                            await self._save_account_state(
                                                                            # Generate final report
                                                                            report=await self.generate_report(
                                                                            class PaperTradingBroker:
                                                                                """
                                                                                Broker interface wrapper for paper trading
                                                                                Implements same interface as real broker for seamless integration
                                                                                """

                                                                                def __init__(self, paper_engine: PaperTradingEngine):

                                                                                    async def connect(self):
                                                                                    """Connect to paper trading engine"""
                                                                                    await self.engine.initialize(
                                                                                    async def place_order(self, order_params: Dict) -> Dict:
                                                                                    """Place order through paper engine"""
                                                                                return await self.engine.place_order(order_params
                                                                                async def cancel_order(self, order_id: str) -> Dict:
                                                                                """Cancel order through paper engine"""
                                                                            return await self.engine.cancel_order(order_id
                                                                            async def get_positions(self) -> List[Dict]:
                                                                            """Get current positions"""
                                                                            positions=[]
                                                                            for pos in self.engine.account.open_positions.values():
                                                                                positions.append({
                                                                                'position_id': pos.position_id,
                                                                                'symbol': pos.symbol,
                                                                                'quantity': pos.quantity,
                                                                                'entry_price': pos.entry_price,
                                                                                'current_price': pos.current_price,
                                                                                'pnl': pos.pnl,
                                                                                'pnl_percent': pos.pnl_percent

                                                                            return positions

                                                                            async def get_orders(self) -> List[Dict}:
                                                                            """Get pending orders"""
                                                                            orders= []
                                                                            for order in self.engine.account.pending_orders.values():
                                                                                orders.append({
                                                                                'order_id': order.order_id,
                                                                                'symbol': order.symbol,
                                                                                'side': order.side,
                                                                                'quantity': order.quantity,
                                                                                'status': order.status,
                                                                                'order_type': order.order_type,
                                                                                'price': order.limit_price

                                                                            return orders

                                                                            async def exit_position(self, position_id: str) -> Dict:
                                                                            """Exit position"""
                                                                        return await self.engine.exit_position(position_id
                                                                        def get_account_summary(self) -> Dict:
                                                                            """Get account summary"""
                                                                            account=self.engine.account
                                                                        return {
                                                                        'capital': account.current_capital,
                                                                        'total_pnl': account.total_pnl,
                                                                        'realized_pnl': account.realized_pnl,
                                                                        'unrealized_pnl': account.unrealized_pnl,
                                                                        'positions': len(account.open_positions),
                                                                        'daily_pnl': account.daily_pnl,
                                                                        'max_drawdown': account.max_drawdown

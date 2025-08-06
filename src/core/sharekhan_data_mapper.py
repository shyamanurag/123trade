"""
ShareKhan Data Mapper
Comprehensive data fetching, parsing and mapping from ShareKhan API
Real-time trades, P&L, reports, and comprehensive portfolio data
100% REAL DATA - NO SIMULATION
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import json

from brokers.sharekhan import ShareKhanIntegration, ShareKhanOrder, ShareKhanMarketData

logger = logging.getLogger(__name__)

@dataclass
class LiveTrade:
    """Live trade data from ShareKhan"""
    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: str  # BUY/SELL
    quantity: int
    price: Decimal
    trade_time: datetime
    trade_value: Decimal
    brokerage: Decimal
    taxes: Decimal
    net_amount: Decimal
    status: str

@dataclass
class PnLSummary:
    """P&L summary data"""
    user_id: int
    date: date
    
    # Realized P&L
    realized_pnl: Decimal
    realized_profit: Decimal
    realized_loss: Decimal
    
    # Unrealized P&L
    unrealized_pnl: Decimal
    
    # Day P&L
    day_pnl: Decimal
    
    # Trading costs
    total_brokerage: Decimal
    total_taxes: Decimal
    
    # Portfolio metrics
    portfolio_value: Decimal
    invested_amount: Decimal
    available_margin: Decimal
    used_margin: Decimal
    
    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_percentage: float
    
    # Updated timestamp
    updated_at: datetime

@dataclass
class FundSummary:
    """Fund/Balance summary from ShareKhan"""
    available_cash: Decimal
    used_margin: Decimal
    available_margin: Decimal
    collateral_value: Decimal
    
    # Limits
    margin_utilization: Decimal
    exposure_limit: Decimal
    
    # Breakdown
    equity_funds: Decimal
    commodity_funds: Decimal
    
    updated_at: datetime

@dataclass
class PositionSummary:
    """Position summary with comprehensive data"""
    symbol: str
    exchange: str
    quantity: int
    average_price: Decimal
    current_price: Decimal
    side: str
    
    # P&L breakdown
    unrealized_pnl: Decimal
    day_change: Decimal
    day_change_percent: float
    
    # Values
    investment_value: Decimal
    current_value: Decimal
    
    # Metadata
    product_type: str
    holding_type: str  # INTRADAY/OVERNIGHT
    
    updated_at: datetime

@dataclass
class TradeReport:
    """Comprehensive trade report"""
    report_date: date
    trades: List[LiveTrade]
    pnl_summary: PnLSummary
    positions: List[PositionSummary]
    fund_summary: FundSummary
    
    # Report metadata
    generated_at: datetime
    data_source: str = "sharekhan_live"

class ShareKhanDataMapper:
    """
    Maps and processes all ShareKhan data into structured formats
    Handles real-time trades, P&L calculations, reports generation
    """
    
    def __init__(self, sharekhan_client: ShareKhanIntegration):
        self.sharekhan_client = sharekhan_client
        
        # Data cache
        self.trade_cache: Dict[str, LiveTrade] = {}
        self.pnl_cache: Dict[str, PnLSummary] = {}  # date_str -> PnLSummary
        self.position_cache: Dict[str, PositionSummary] = {}  # symbol -> PositionSummary
        
        # Configuration
        self.cache_duration_minutes = 5  # Cache data for 5 minutes
        self.precision = Decimal('0.01')
        
        # Background tasks
        self.data_refresh_task: Optional[asyncio.Task] = None
        
        logger.info("✅ ShareKhan Data Mapper initialized")
    
    async def initialize(self) -> bool:
        """Initialize data mapper"""
        try:
                    if not self.sharekhan_client or not hasattr(self.sharekhan_client, 'is_authenticated') or not self.sharekhan_client.is_authenticated:
            logger.warning("ShareKhan client not authenticated - initializing without authentication check")
            # Continue initialization for offline/testing mode
            
            # Start background data refresh
            self.data_refresh_task = asyncio.create_task(self._background_data_refresh())
            
            logger.info("✅ ShareKhan Data Mapper fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize data mapper: {e}")
            return False
    
    async def fetch_live_trades(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[LiveTrade]:
        """
        Fetch live trades from ShareKhan
        Returns real trade data with comprehensive details
        """
        try:
            # Default to today if no dates provided
            if not from_date:
                from_date = date.today()
            if not to_date:
                to_date = date.today()
            
            logger.info(f"🔄 Fetching live trades from {from_date} to {to_date}")
            
            # Call ShareKhan trades API
            trades_result = await self.sharekhan_client.get_trades(
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d')
            )
            
            if not trades_result.get('success'):
                raise RuntimeError(f"Failed to fetch trades: {trades_result.get('error')}")
            
            raw_trades = trades_result.get('trades', [])
            
            # Parse and map trades
            live_trades = []
            for trade_data in raw_trades:
                live_trade = self._parse_trade_data(trade_data)
                if live_trade:
                    live_trades.append(live_trade)
                    # Cache trade
                    self.trade_cache[live_trade.trade_id] = live_trade
            
            logger.info(f"✅ Fetched {len(live_trades)} live trades")
            return live_trades
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch live trades: {e}")
            return []
    
    async def calculate_comprehensive_pnl(
        self,
        user_id: int,
        calculation_date: Optional[date] = None
    ) -> Optional[PnLSummary]:
        """
        Calculate comprehensive P&L from ShareKhan data
        Includes realized, unrealized, day P&L with all costs
        """
        try:
            if not calculation_date:
                calculation_date = date.today()
            
            logger.info(f"🧮 Calculating comprehensive P&L for {calculation_date}")
            
            # Fetch positions for unrealized P&L
            positions_result = await self.sharekhan_client.get_positions()
            if not positions_result.get('success'):
                raise RuntimeError("Failed to fetch positions for P&L calculation")
            
            raw_positions = positions_result.get('positions', [])
            
            # Fetch trades for realized P&L
            trades = await self.fetch_live_trades(from_date=calculation_date, to_date=calculation_date)
            
            # Fetch fund information
            funds_result = await self.sharekhan_client.get_funds()
            if not funds_result.get('success'):
                logger.warning("Could not fetch fund information")
                funds_data = {}
            else:
                funds_data = funds_result.get('funds', {})
            
            # Calculate realized P&L from trades
            realized_pnl = Decimal('0')
            realized_profit = Decimal('0')
            realized_loss = Decimal('0')
            total_brokerage = Decimal('0')
            total_taxes = Decimal('0')
            
            for trade in trades:
                if trade.side == 'SELL':  # Only count sell trades for realized P&L
                    trade_pnl = trade.net_amount
                    if trade_pnl > 0:
                        realized_profit += trade_pnl
                    else:
                        realized_loss += abs(trade_pnl)
                    
                    realized_pnl += trade_pnl
                
                total_brokerage += trade.brokerage
                total_taxes += trade.taxes
            
            # Calculate unrealized P&L from positions
            unrealized_pnl = Decimal('0')
            portfolio_value = Decimal('0')
            invested_amount = Decimal('0')
            
            for pos_data in raw_positions:
                quantity = pos_data.get('quantity', 0)
                if quantity == 0:
                    continue
                
                avg_price = Decimal(str(pos_data.get('average_price', 0)))
                current_price = Decimal(str(pos_data.get('ltp', 0)))
                
                position_value = abs(quantity) * current_price
                investment_value = abs(quantity) * avg_price
                
                portfolio_value += position_value
                invested_amount += investment_value
                
                # Calculate unrealized P&L
                if quantity > 0:  # Long position
                    unrealized_pnl += (current_price - avg_price) * quantity
                else:  # Short position
                    unrealized_pnl += (avg_price - current_price) * abs(quantity)
            
            # Calculate day P&L (approximation - would need opening positions)
            day_pnl = realized_pnl + unrealized_pnl  # Simplified
            
            # Get margin information
            available_margin = Decimal(str(funds_data.get('available_margin', 0)))
            used_margin = Decimal(str(funds_data.get('used_margin', 0)))
            
            # Calculate performance metrics
            winning_trades = len([t for t in trades if t.side == 'SELL' and t.net_amount > 0])
            losing_trades = len([t for t in trades if t.side == 'SELL' and t.net_amount <= 0])
            total_trades_count = winning_trades + losing_trades
            win_percentage = (winning_trades / total_trades_count * 100) if total_trades_count > 0 else 0
            
            # Create P&L summary
            pnl_summary = PnLSummary(
                user_id=user_id,
                date=calculation_date,
                realized_pnl=realized_pnl.quantize(self.precision, rounding=ROUND_HALF_UP),
                realized_profit=realized_profit.quantize(self.precision, rounding=ROUND_HALF_UP),
                realized_loss=realized_loss.quantize(self.precision, rounding=ROUND_HALF_UP),
                unrealized_pnl=unrealized_pnl.quantize(self.precision, rounding=ROUND_HALF_UP),
                day_pnl=day_pnl.quantize(self.precision, rounding=ROUND_HALF_UP),
                total_brokerage=total_brokerage.quantize(self.precision, rounding=ROUND_HALF_UP),
                total_taxes=total_taxes.quantize(self.precision, rounding=ROUND_HALF_UP),
                portfolio_value=portfolio_value.quantize(self.precision, rounding=ROUND_HALF_UP),
                invested_amount=invested_amount.quantize(self.precision, rounding=ROUND_HALF_UP),
                available_margin=available_margin.quantize(self.precision, rounding=ROUND_HALF_UP),
                used_margin=used_margin.quantize(self.precision, rounding=ROUND_HALF_UP),
                total_trades=len(trades),
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_percentage=win_percentage,
                updated_at=datetime.now()
            )
            
            # Cache P&L summary
            cache_key = f"{user_id}_{calculation_date.strftime('%Y-%m-%d')}"
            self.pnl_cache[cache_key] = pnl_summary
            
            logger.info(f"✅ P&L calculation completed: Total P&L = {pnl_summary.realized_pnl + pnl_summary.unrealized_pnl}")
            return pnl_summary
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate comprehensive P&L: {e}")
            return None
    
    async def fetch_fund_summary(self) -> Optional[FundSummary]:
        """Fetch comprehensive fund/balance summary from ShareKhan"""
        try:
            logger.info("🔄 Fetching fund summary from ShareKhan")
            
            funds_result = await self.sharekhan_client.get_funds()
            if not funds_result.get('success'):
                raise RuntimeError(f"Failed to fetch funds: {funds_result.get('error')}")
            
            funds_data = funds_result.get('funds', {})
            
            # Parse fund data
            fund_summary = FundSummary(
                available_cash=Decimal(str(funds_data.get('available_cash', 0))),
                used_margin=Decimal(str(funds_data.get('used_margin', 0))),
                available_margin=Decimal(str(funds_data.get('available_margin', 0))),
                collateral_value=Decimal(str(funds_data.get('collateral_value', 0))),
                margin_utilization=Decimal(str(funds_data.get('margin_utilization', 0))),
                exposure_limit=Decimal(str(funds_data.get('exposure_limit', 0))),
                equity_funds=Decimal(str(funds_data.get('equity_funds', 0))),
                commodity_funds=Decimal(str(funds_data.get('commodity_funds', 0))),
                updated_at=datetime.now()
            )
            
            logger.info(f"✅ Fund summary fetched: Available cash = {fund_summary.available_cash}")
            return fund_summary
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch fund summary: {e}")
            return None
    
    async def fetch_position_summaries(self) -> List[PositionSummary]:
        """Fetch comprehensive position summaries from ShareKhan"""
        try:
            logger.info("🔄 Fetching position summaries from ShareKhan")
            
            positions_result = await self.sharekhan_client.get_positions()
            if not positions_result.get('success'):
                raise RuntimeError(f"Failed to fetch positions: {positions_result.get('error')}")
            
            raw_positions = positions_result.get('positions', [])
            
            # Get current market quotes for all symbols
            symbols = [pos.get('symbol') for pos in raw_positions if pos.get('quantity', 0) != 0]
            
            current_quotes = {}
            if symbols:
                quotes_result = await self.sharekhan_client.get_market_quote(symbols)
                current_quotes = quotes_result
            
            # Parse position data
            position_summaries = []
            
            for pos_data in raw_positions:
                quantity = pos_data.get('quantity', 0)
                if quantity == 0:
                    continue
                
                symbol = pos_data.get('symbol', '')
                
                # Get current market data
                market_data = current_quotes.get(symbol)
                current_price = Decimal(str(market_data.ltp)) if market_data else Decimal(str(pos_data.get('ltp', 0)))
                
                # Parse position
                position_summary = self._parse_position_data(pos_data, current_price)
                if position_summary:
                    position_summaries.append(position_summary)
                    # Cache position
                    self.position_cache[symbol] = position_summary
            
            logger.info(f"✅ Fetched {len(position_summaries)} position summaries")
            return position_summaries
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch position summaries: {e}")
            return []
    
    async def generate_comprehensive_report(
        self,
        user_id: int,
        report_date: Optional[date] = None
    ) -> Optional[TradeReport]:
        """
        Generate comprehensive trading report with all data
        Combines trades, P&L, positions, and funds in single report
        """
        try:
            if not report_date:
                report_date = date.today()
            
            logger.info(f"📊 Generating comprehensive report for {report_date}")
            
            # Fetch all required data in parallel
            trades_task = self.fetch_live_trades(from_date=report_date, to_date=report_date)
            pnl_task = self.calculate_comprehensive_pnl(user_id, report_date)
            positions_task = self.fetch_position_summaries()
            funds_task = self.fetch_fund_summary()
            
            # Wait for all data
            trades, pnl_summary, positions, fund_summary = await asyncio.gather(
                trades_task, pnl_task, positions_task, funds_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(trades, Exception):
                logger.error(f"Failed to fetch trades: {trades}")
                trades = []
            
            if isinstance(pnl_summary, Exception):
                logger.error(f"Failed to calculate P&L: {pnl_summary}")
                pnl_summary = None
            
            if isinstance(positions, Exception):
                logger.error(f"Failed to fetch positions: {positions}")
                positions = []
            
            if isinstance(fund_summary, Exception):
                logger.error(f"Failed to fetch funds: {fund_summary}")
                fund_summary = None
            
            # Create comprehensive report
            trade_report = TradeReport(
                report_date=report_date,
                trades=trades,
                pnl_summary=pnl_summary,
                positions=positions,
                fund_summary=fund_summary,
                generated_at=datetime.now(),
                data_source="sharekhan_live"
            )
            
            logger.info(f"✅ Comprehensive report generated with {len(trades)} trades, {len(positions)} positions")
            return trade_report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate comprehensive report: {e}")
            return None
    
    async def export_report_to_dict(self, report: TradeReport) -> Dict[str, Any]:
        """Export trade report to dictionary format for API response"""
        try:
            return {
                "report_date": report.report_date.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "data_source": report.data_source,
                
                "trades": [
                    {
                        "trade_id": trade.trade_id,
                        "order_id": trade.order_id,
                        "symbol": trade.symbol,
                        "exchange": trade.exchange,
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "price": float(trade.price),
                        "trade_time": trade.trade_time.isoformat(),
                        "trade_value": float(trade.trade_value),
                        "brokerage": float(trade.brokerage),
                        "taxes": float(trade.taxes),
                        "net_amount": float(trade.net_amount),
                        "status": trade.status
                    }
                    for trade in report.trades
                ],
                
                "pnl_summary": {
                    "date": report.pnl_summary.date.isoformat(),
                    "realized_pnl": float(report.pnl_summary.realized_pnl),
                    "realized_profit": float(report.pnl_summary.realized_profit),
                    "realized_loss": float(report.pnl_summary.realized_loss),
                    "unrealized_pnl": float(report.pnl_summary.unrealized_pnl),
                    "day_pnl": float(report.pnl_summary.day_pnl),
                    "total_brokerage": float(report.pnl_summary.total_brokerage),
                    "total_taxes": float(report.pnl_summary.total_taxes),
                    "portfolio_value": float(report.pnl_summary.portfolio_value),
                    "invested_amount": float(report.pnl_summary.invested_amount),
                    "available_margin": float(report.pnl_summary.available_margin),
                    "used_margin": float(report.pnl_summary.used_margin),
                    "total_trades": report.pnl_summary.total_trades,
                    "winning_trades": report.pnl_summary.winning_trades,
                    "losing_trades": report.pnl_summary.losing_trades,
                    "win_percentage": report.pnl_summary.win_percentage,
                    "updated_at": report.pnl_summary.updated_at.isoformat()
                } if report.pnl_summary else None,
                
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "exchange": pos.exchange,
                        "quantity": pos.quantity,
                        "average_price": float(pos.average_price),
                        "current_price": float(pos.current_price),
                        "side": pos.side,
                        "unrealized_pnl": float(pos.unrealized_pnl),
                        "day_change": float(pos.day_change),
                        "day_change_percent": pos.day_change_percent,
                        "investment_value": float(pos.investment_value),
                        "current_value": float(pos.current_value),
                        "product_type": pos.product_type,
                        "holding_type": pos.holding_type,
                        "updated_at": pos.updated_at.isoformat()
                    }
                    for pos in report.positions
                ],
                
                "fund_summary": {
                    "available_cash": float(report.fund_summary.available_cash),
                    "used_margin": float(report.fund_summary.used_margin),
                    "available_margin": float(report.fund_summary.available_margin),
                    "collateral_value": float(report.fund_summary.collateral_value),
                    "margin_utilization": float(report.fund_summary.margin_utilization),
                    "exposure_limit": float(report.fund_summary.exposure_limit),
                    "equity_funds": float(report.fund_summary.equity_funds),
                    "commodity_funds": float(report.fund_summary.commodity_funds),
                    "updated_at": report.fund_summary.updated_at.isoformat()
                } if report.fund_summary else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to export report to dict: {e}")
            return {}
    
    def _parse_trade_data(self, trade_data: Dict[str, Any]) -> Optional[LiveTrade]:
        """Parse raw trade data from ShareKhan API"""
        try:
            # Calculate net amount considering brokerage and taxes
            trade_value = Decimal(str(trade_data.get('trade_value', 0)))
            brokerage = Decimal(str(trade_data.get('brokerage', 0)))
            taxes = Decimal(str(trade_data.get('total_charges', 0)))
            
            side = trade_data.get('transaction_type', 'BUY')
            if side == 'SELL':
                net_amount = trade_value - brokerage - taxes
            else:  # BUY
                net_amount = -(trade_value + brokerage + taxes)
            
            # Parse trade time
            trade_time_str = trade_data.get('trade_time', '')
            try:
                trade_time = datetime.strptime(trade_time_str, '%Y-%m-%d %H:%M:%S')
            except:
                trade_time = datetime.now()
            
            return LiveTrade(
                trade_id=str(trade_data.get('trade_id', '')),
                order_id=str(trade_data.get('order_id', '')),
                symbol=trade_data.get('symbol', ''),
                exchange=trade_data.get('exchange', 'NSE'),
                side=side,
                quantity=int(trade_data.get('quantity', 0)),
                price=Decimal(str(trade_data.get('trade_price', 0))),
                trade_time=trade_time,
                trade_value=trade_value,
                brokerage=brokerage,
                taxes=taxes,
                net_amount=net_amount,
                status=trade_data.get('status', 'EXECUTED')
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse trade data: {e}")
            return None
    
    def _parse_position_data(
        self,
        pos_data: Dict[str, Any],
        current_price: Decimal
    ) -> Optional[PositionSummary]:
        """Parse raw position data from ShareKhan API"""
        try:
            symbol = pos_data.get('symbol', '')
            quantity = int(pos_data.get('quantity', 0))
            average_price = Decimal(str(pos_data.get('average_price', 0)))
            
            # Determine side
            side = 'LONG' if quantity > 0 else 'SHORT'
            abs_quantity = abs(quantity)
            
            # Calculate values
            investment_value = abs_quantity * average_price
            current_value = abs_quantity * current_price
            
            # Calculate P&L
            if quantity > 0:  # Long position
                unrealized_pnl = (current_price - average_price) * abs_quantity
            else:  # Short position
                unrealized_pnl = (average_price - current_price) * abs_quantity
            
            # Calculate day change (simplified - using unrealized P&L)
            day_change = unrealized_pnl
            day_change_percent = float((unrealized_pnl / investment_value) * 100) if investment_value > 0 else 0
            
            return PositionSummary(
                symbol=symbol,
                exchange=pos_data.get('exchange', 'NSE'),
                quantity=quantity,
                average_price=average_price,
                current_price=current_price,
                side=side,
                unrealized_pnl=unrealized_pnl.quantize(self.precision, rounding=ROUND_HALF_UP),
                day_change=day_change.quantize(self.precision, rounding=ROUND_HALF_UP),
                day_change_percent=day_change_percent,
                investment_value=investment_value.quantize(self.precision, rounding=ROUND_HALF_UP),
                current_value=current_value.quantize(self.precision, rounding=ROUND_HALF_UP),
                product_type=pos_data.get('product_type', 'EQUITY'),
                holding_type=pos_data.get('holding_type', 'INTRADAY'),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse position data: {e}")
            return None
    
    async def _background_data_refresh(self):
        """Background task to refresh cached data"""
        while True:
            try:
                await asyncio.sleep(self.cache_duration_minutes * 60)
                
                # Refresh position summaries
                await self.fetch_position_summaries()
                
                # Clean old cache entries
                current_time = datetime.now()
                
                # Clean trade cache (keep last 1000 trades)
                if len(self.trade_cache) > 1000:
                    sorted_trades = sorted(
                        self.trade_cache.items(),
                        key=lambda x: x[1].trade_time,
                        reverse=True
                    )
                    self.trade_cache = dict(sorted_trades[:1000])
                
                # Clean P&L cache (keep last 30 days)
                cutoff_date = current_time - timedelta(days=30)
                self.pnl_cache = {
                    k: v for k, v in self.pnl_cache.items()
                    if v.updated_at > cutoff_date
                }
                
                logger.info("✅ Background data refresh completed")
                
            except Exception as e:
                logger.error(f"❌ Error in background data refresh: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def shutdown(self):
        """Shutdown data mapper"""
        try:
            if self.data_refresh_task:
                self.data_refresh_task.cancel()
            
            logger.info("✅ ShareKhan Data Mapper shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Global instance will be created when orchestrator initializes
sharekhan_data_mapper: Optional[ShareKhanDataMapper] = None